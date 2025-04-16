#!/opt/anaconda3/envs/feliggs/bin/python3
import subprocess
import sys
import os
import tempfile
import cv2
import numpy as np
from PIL import Image, ImageOps
import cups
import io
import configparser

class Label:
    def __init__(self, ps_data=None, config_path="config.ini"):
        """
        Initialize the Label object, load configuration, and process the label if PostScript data is provided.

        Args:
            ps_data (bytes, optional): The PostScript data to process.
            config_path (str, optional): Path to the configuration file.
        """
        # Load configuration from file
        self.config = configparser.ConfigParser()
        self.config.read(config_path)
        
        self.ps_data = ps_data                   # PostScript data
        self.label_type = None                   # Detected label type (DHL, Amazon)
        
        # Image attributes
        self.original_image = None               # Full original image
        self.label_image = None                  # Cropped label image
        self.additional_image = None             # Cropped additional info image
                
        # DPI setting from config
        self.dpi = self.config.getint('General', 'dpi')
        
        # Automatically process if PostScript data is provided
        if ps_data:
            self.process()
    
    def process(self):
        """
        Complete processing pipeline: convert PS to image, detect label type, extract contents, and resize.
        """
        self.convert_ps_to_image()
        self.determine_label_type()
        self.extract_contents()
        self.resize_all()
    
    def convert_ps_to_image(self):
        """
        Convert PostScript data to a temporary PNG image and load it into memory.
        Temporary files are deleted after use.
        """
        with tempfile.NamedTemporaryFile(delete=False, suffix=".ps") as tmp_ps:
            tmp_ps.write(self.ps_data)
            tmp_ps_path = tmp_ps.name

        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_png:
            tmp_png_path = tmp_png.name

        try:
            subprocess.run([
                "gs",
                "-dSAFER",
                "-dBATCH",
                "-dNOPAUSE",
                f"-r{self.dpi}",
                "-sDEVICE=png16m",
                f"-sOutputFile={tmp_png_path}",
                tmp_ps_path
            ], check=True)

            # Load the image from the temporary PNG file
            self.original_image = cv2.imread(tmp_png_path)
            if self.original_image is None:
                raise RuntimeError("Failed to load PNG image after conversion.")

        except Exception as e:
            print(f"Error: Conversion from PS to PNG failed: {e}")
            raise
        finally:    
            os.unlink(tmp_ps_path)  # Clean up temporary files
            os.unlink(tmp_png_path)

    def determine_label_type(self):
        """
        Determine the label type (currently only DHL, Amazon) based on visual features in the image.
        Sets self.label_type accordingly.
        """
        if self.original_image is None:
            raise ValueError("No image available to determine label type")
            
        h, w = self.original_image.shape[:2]                            # Get the height and width of the image
        gray = cv2.cvtColor(self.original_image, cv2.COLOR_BGR2GRAY)    # Convert the image to grayscale
        
        # Focus on the middle section of the image where a cutting line might be present
        middle_y = h // 2
        margin = h // 6
        middle_section = gray[middle_y-margin:middle_y+margin, :]
        
        # Apply threshold and detect lines
        _, binary = cv2.threshold(middle_section, 220, 255, cv2.THRESH_BINARY_INV)
        lines = cv2.HoughLinesP(binary, 1, np.pi/180, threshold=50, 
                               minLineLength=w*0.9, maxLineGap=50)
        
        if lines is not None and len(lines) > 0:
            for line in lines:
                x1, y1, x2, y2 = line[0]
                if abs(y2 - y1) < 10 and abs(x2 - x1) > w * 0.6:
                    print(">DHL label detected")
                    self.label_type = "DHL"
                    return
        
        print(">Amazon label detected - no cutting line found")
        self.label_type = "Amazon"  # Default to Amazon if no DHL line detected, more label types in the future
    
    def extract_contents(self):
        """
        Extract the label and additional information regions from the image,
        using cropping parameters from the config file for the detected label type.
        """
        if self.original_image is None or self.label_type is None:
            raise ValueError("Image or label type not available")
            
        h, w = self.original_image.shape[:2]
        section = self.label_type

        # Extract label region using config parameters
        label_start_y = int(h * self.config.getfloat(section, 'label_start_y'))
        label_end_y   = int(h * self.config.getfloat(section, 'label_end_y'))
        
        label_start_x = int(w * self.config.getfloat(section, 'label_start_x'))
        label_end_x   = int(w * self.config.getfloat(section, 'label_end_x'))
        
        self.label_image = self.original_image[label_start_y:label_end_y, label_start_x:label_end_x]

        # Extract additional info region if parameters exist (Amazon and DHL both have additional info, already implemented for future use)
        if all(self.config.has_option(section, opt) for opt in ['info_start_y', 'info_end_y', 'info_start_x', 'info_end_x']):
            info_start_y = int(h * self.config.getfloat(section, 'info_start_y'))
            info_end_y   = int(h * self.config.getfloat(section, 'info_end_y'))
            info_start_x = int(w * self.config.getfloat(section, 'info_start_x'))
            info_end_x   = int(w * self.config.getfloat(section, 'info_end_x'))
            self.additional_image = self.original_image[info_start_y:info_end_y, info_start_x:info_end_x]
        else:
            self.additional_image = None
    
    def resize_all(self):
        """
        Resize the label and additional info images to the target size defined in the config,
        maintaining aspect ratio and centering on a white background.
        """
        self.label_image = self.resize(self.label_image)
        if self.additional_image is not None:
            self.additional_image = self.resize(self.additional_image)
    
    def resize(self, current_image):
        """
        Resize the given image to the configured label size (e.g., 4x6 inches) at the specified DPI,
        maintaining aspect ratio and centering the image on a white background.

        Args:
            current_image (np.ndarray): The image to resize.

        Returns:
            np.ndarray: The resized image as a numpy array.
        """
        
        # Get target size from config parameters
        label_width     = self.config.getint('General', 'label_width')
        label_height    = self.config.getint('General', 'label_height')
        target_size = (int(label_height * self.dpi), int(label_width * self.dpi))
        
        h, w = current_image.shape[:2]
        aspect = w / h
        
        # Calculate new dimensions. Only tested for 4x6 labels
        if aspect > 1.5:
            new_width = int(label_height * self.dpi)
            new_height = int(new_width / aspect)
            if new_height > int(label_width * self.dpi):
                new_height = int(label_width * self.dpi)
                new_width = int(new_height * aspect)
        else:
            new_height = int(label_width * self.dpi)
            new_width = int(new_height * aspect)
            if new_width > int(label_height * self.dpi):
                new_width = int(label_height * self.dpi)
                new_height = int(new_width / aspect)
        
        pil_img = Image.fromarray(current_image)
        resized = pil_img.resize((new_width, new_height), Image.LANCZOS)
        
        background = Image.new('RGB', target_size, (255, 255, 255))
        
        offset = ((target_size[0] - new_width) // 2,
                (target_size[1] - new_height) // 2)
        background.paste(resized, offset)
        
        return np.array(background)

    def save_contents(self, label_path="label.png", info_path="additional_info.png"):
        """
        Save the generated label and additional info images to disk.

        Args:
            label_path (str): Path to save the label image.
            info_path (str): Path to save the additional info image.
        """
        if self.label_image is not None:
            cv2.imwrite(label_path, self.label_image)
        
        if self.additional_image is not None:
            cv2.imwrite(info_path, self.additional_image)

    def send_to_printer(self, image, printer_name):
        """
        Print the given image using a temporary file and the specified printer.
        The temporary file is deleted after printing.

        Args:
            image (np.ndarray): The image to print.
            printer_name (str): The printer to use. If None, uses the default printer from config.
        """
        if printer_name is None:
            printer_name = self.config.get('General', 'default_printer')
            
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            temp_path = tmp.name
            cv2.imwrite(temp_path, image)
        try:
            conn = cups.Connection()
            conn.printFile(printer_name, temp_path, "Label", {"media": "Custom.4x6in", "copies": "1"})
        finally:
            os.unlink(temp_path)

    def print_all(self):
        """
        Print all images (label and additional info) using temporary files.
        Printer names and print options are read from the config file.
        """
        label_type = self.label_type    # Determine label type, because each label has its own printer for additional info
        print_additional_info = self.config.getboolean(label_type, 'print_additional_info', fallback=True)

        if self.label_image is not None:
            printer = self.config.get('General', 'default_printer')
            self.send_to_printer(self.label_image, printer_name=None)  # Use standard option (label printer)
            print(">Label printed successfully on printer:", printer)

        if self.additional_image is not None and print_additional_info:
            # Get printer name for additional info from config if available
            printer = self.config.get(label_type, 'additional_info_printer', fallback=None)
            self.send_to_printer(self.additional_image, printer_name=printer)
            print(">Additional information printed successfully on printer:", printer)
        else:
            print(">Printing of additional information is deactivated. Skipped printing.")

if __name__ == "__main__":
    ps_data = sys.stdin.buffer.read()   # Read PostScript data from stdin
    label   = Label(ps_data)            # Initialize Label object with PostScript data
    label.print_all()                   # Print the label and additional information
    
    #Optionally use the save function to save the images or implement further processing