import cv2
import numpy as np
import subprocess
import tempfile
import os
import cups
import sys
import configparser
import glob

class Document:
    """
    Represents a PostScript document and handles the conversion to several PNG images (1 per page).
    Extracts document metadata such as title, author, and application.
    """
    def __init__(self, ps_input: bytes):
        """
        Initialize the Document with PostScript input data.

        Parameters:
            ps_input (bytes): The raw PostScript file content (from IPPServer or other source).
        """
        self.ps_input       = ps_input
        self.png_data       = []
        self.title          = None
        self.author         = None
        self.application    = None
        self.convert_ps_to_png()

    def convert_ps_to_png(self):
        """
        Converts the PostScript input to one or more PNG images using Ghostscript.
        Extracts metadata from the PostScript header.
        """
        # Write PostScript data to a temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.ps') as tmp_ps_file:
            tmp_ps_file.write(self.ps_input)
        
        # Create a temporary directory for PNG output
        with tempfile.TemporaryDirectory() as tmp_dir:
            # Use Ghostscript to convert PS to PNG
            subprocess.run([
                "gs", "-q", "-dSAFER", "-dBATCH", "-dNOPAUSE",
                f"-r{300}", "-sDEVICE=png16m",
                f"-sOutputFile={tmp_dir}/page_%03d.png",
                tmp_ps_file.name
            ], check=True)
            
            # Extract document metadata from PostScript header (I do not know if all PS files have the same header, works for me)
            for line in range(20):
                line = self.ps_input.decode().splitlines()[line]
                if line.startswith("%%Title: "):
                    self.title = line[10:-1]
                elif line.startswith("%%For: "):
                    self.author = line[8:-1]
                elif line.startswith("%%Creator: "):
                    self.application = line[12:-1].split(": ")[0]
            
            # Collect all generated PNG files and sort them
            pagges = sorted(glob.glob(f"{tmp_dir}/page_*.png"))
            print(f"Conversion completed. Found {len(pagges)} pages.")
            # Read PNG content into memory
            for page in pagges:
                with open(page, 'rb') as f:
                    self.png_data.append(f.read())
                    
        # Clean up the temporary PostScript file
        os.unlink(tmp_ps_file.name)

    def get_png_data_by_index(self, index):
        """
        Returns PNG image data for a specific page index.

        Parameters:
            index (int): The page index.

        Raises:
            IndexError: If the index is out of range.
        """
        if index < 0 or index >= len(self.png_data):
            raise IndexError("Index out of range")
        return self.png_data[index]

    def get_number_of_pages(self):
        """
        Returns the number of pages in the document.
        """
        return len(self.png_data)

    def get_title(self):
        """
        Returns the document title.
        """
        return self.title

    def get_author(self):
        """
        Returns the document author.
        """
        return self.author

    def get_application(self):
        """
        Returns the application that created the document.
        """
        return self.application

    def to_string(self):
        """
        Returns a string representation of the document metadata and page count.
        """
        return f"-->Title: {self.title}, Author: {self.author}, Application: {self.application}, Pages: {len(self.png_data)}"

class Page:
    """
    Represents a single page and provides methods for label detection and extraction.
    """
    def __init__(self, png_data: bytes):
        """
        Initialize the Page with PNG image data.

        Parameters:
            png_data (bytes): The PNG image data for the whole page, which is separated into label and document sections.
        """
        self.png_data           = png_data
        self.png_image          = cv2.imdecode(np.frombuffer(self.png_data, np.uint8), cv2.IMREAD_UNCHANGED)
        self.label_type         = None
        self.detected_label_box = None
        self.detected_info_box  = None
        
        self.check_rotation()
        self.determine_label_type()
        self.extract_label()
    
    def check_rotation(self):
        """
        Checks the image orientation and rotates to portrait mode if necessary.
        This is kind of useless with the current implementation, it can end up 180° rotated.
        """
        h, w = self.png_image.shape[:2]
        if w > h:
            self.png_image = cv2.rotate(self.png_image, cv2.ROTATE_90_CLOCKWISE)
            print(">Image rotated to portrait mode")

    def determine_label_type(self):
        """
        Determines the label type (e.g., DHL or Amazon) by analyzing the image for cutting lines.
        Sets self.label_type accordingly.
        """
        if self.png_image is None:
            raise ValueError(">No image available to determine label type")
        
        h, w = self.png_image.shape[:2]
        gray = cv2.cvtColor(self.png_image, cv2.COLOR_BGR2GRAY)
        
        # Focus on the middle section of the image where a cutting line might be present
        middle_y = h // 2
        margin = h // 6
        middle_section = gray[middle_y-margin:middle_y+margin, :]
        
        # Apply threshold and detect lines
        _, binary = cv2.threshold(middle_section, 220, 255, cv2.THRESH_BINARY_INV)
        lines = cv2.HoughLinesP(binary, 1, np.pi/180, threshold=50, 
                               minLineLength=w*0.9, maxLineGap=50)
        
        #Check for the horizontal cutting line in the middle section (DHL specific)
        if lines is not None and len(lines) > 0:
            for line in lines:
                x1, y1, x2, y2 = line[0]
                # Check for a horizontal line that covers most of the width
                if abs(y2 - y1) < 2 and abs(x2 - x1) > w * 0.6:
                    print(">DHL label detected")
                    self.cut_line_y = (y1 + y2) // 2
                    self.label_type = "DHL"
                    return
        print(">Amazon label detected") # If we get here, we assume it's an Amazon label
        self.label_type = "Amazon"      # Default to Amazon if no DHL line detected

    def extract_label(self):
        """
        Extracts the label and document regions from the image based on detected lines and label type.
        Sets extracted_label_image and extracted_document_image attributes.
        """
        if self.label_type is None:
            raise ValueError(">Label type not determined, cannot extract content")
        else:
            gray = cv2.cvtColor(self.png_image, cv2.COLOR_BGR2GRAY)
            h, w = self.png_image.shape[:2]
            
            edges = cv2.Canny(gray, 50, 150, apertureSize=3)
            lines = cv2.HoughLinesP(edges, 
                                    rho=1, 
                                    theta=np.pi/180, 
                                    threshold=80,
                                    minLineLength=500, 
                                    maxLineGap=10)
            
            # Create a blank image for drawing lines
            line_image = np.zeros_like(self.png_image)
            
            vertical_lines      = []
            horizontal_lines    = []
            
            if lines is not None:   # Check if any lines were detected and group them into vertical and horizontal lines
                for line in lines:
                    x1, y1, x2, y2 = line[0].tolist()
                    # Detect vertical lines (variation in x is small)
                    if abs(x1 - x2) < 10:
                        vertical_lines.append((y1, y2))
                        cv2.line(line_image, (x1, y1), (x2, y2), (255, 255, 255), 2)
                    # Detect horizontal lines (variation in y is small)
                    if abs(y1 - y2) < 10:
                        horizontal_lines.append((x1, x2))
                        
            if vertical_lines:
                # Sort lines by length to identify label and info sections
                line_lengths = [(abs(y2 - y1), (min(y1,y2), max(y1,y2))) 
                            for y1, y2 in vertical_lines]
                
                sorted_lines    = sorted(line_lengths, key=lambda x: x[0])
                shortest        = sorted_lines[0][1]    # (y_min_label, y_max_label)
                longest         = sorted_lines[-1][1]   # (y_min_info, y_max_info)
                
                if self.label_type == "DHL":
                    # Extract DHL label section --> The continuos line in the label limits the label in y direction, x direction is fixed
                    y_min_label = max(0, shortest[0] - 20)
                    y_max_label = min(h, shortest[1] + 20)
                    self.extracted_label_image = self.png_image[y_min_label:y_max_label, 150:-150]
                    
                    # Extract info section
                    y_min_info = max(0, longest[0] - 50)
                    y_max_info = min(h, longest[1] + 50)
                    self.extracted_document_image = self.png_image[y_min_info:y_max_info, :]
                    
                elif self.label_type == "Amazon":
                    # Extract Amazon label section --> The continuos line in the label limits the label in y direction, x direction is fixed
                    y_min_label = max(0, longest[0] + 5)
                    y_max_label = min(h, longest[1] - 5)
                    self.extracted_label_image      = self.png_image[y_min_label:y_max_label, 370:-570]
                    self.extracted_document_image   = None # Some AMZ labels have no document image, I will implement this later
            else:
                print(">Could not extract content. Format has to be different!")

class PrinterManager:
    """
    Manages printer configuration and sends images to the correct printer.
    """
    _printers = {}

    @classmethod
    def load_printers(cls, config):
        """
        Loads printer configuration from the provided configparser object.

        Parameters:
            config (ConfigParser): The loaded configuration object.
        """
        cls._printers = {'label': None, 'document': None}   # Initialize printers dictionary
        for section in config.sections():                   # Iterate through all sections in the config
            if section.startswith('Printer'):               # Check if the section is a printer configuration
                try:                                        # Get printer type and configuration if available
                    printer_type = config[section]['type'].lower()
                    cls._printers[printer_type] = {
                        'name': config[section]['name'],
                        'format': config[section]['print_format']
                    }
                except KeyError as e:
                    raise ValueError(f"Missing entry in {section}: {e}")

    @classmethod
    def print_image(cls, image_data, printer_type):
        """
        Sends the given image data to the appropriate printer.

        Parameters:
            image_data (bytes): The PNG image data to print.
            printer_type (str): The type of printer to use ('label' or 'document').

        Raises:
            ValueError: If no printer of the given type is configured.
        """
        printer = cls._printers.get(printer_type)
        if not printer:
            raise ValueError(f"No {printer_type} printer configured")

        # Save the image data to a temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as tmp_file:
            tmp_file.write(image_data)
            tmp_file.close()
        
        # Send the file to the printer using CUPS
        connection = cups.Connection()
        connection.printFile(printer['name'], tmp_file.name, "Label", {"media": printer['format'], "copies": "1"})
        os.unlink(tmp_file.name)

if __name__ == "__main__":
    # Load printer configuration from the INI file
    config = configparser.ConfigParser()
    config.read('config.ini')
    PrinterManager.load_printers(config)

    # Read PostScript data from stdin (used by the print server) and create a Document object
    ps_data = sys.stdin.buffer.read()
    document = Document(ps_data)

    # Iterate through all pages of the document
    for page_index in range(document.get_number_of_pages()):
        page_data = document.get_png_data_by_index(page_index)
        page = Page(page_data)
        
        # Print the label image if available
        if page.extracted_label_image is not None:
            label_img = cv2.imencode('.png', page.extracted_label_image)[1].tobytes()
            PrinterManager.print_image(label_img, 'label')
            print(f"Page {page_index+1}: Printjob for label sent to printer")
        
        # Print the document image if available and printing is enabled in config
        if page.extracted_document_image is not None and config['General']['print_documents'] == 'True':
            doc_img = cv2.imencode('.png', page.extracted_document_image)[1].tobytes()
            PrinterManager.print_image(doc_img, 'document')
            print(f"Page {page_index+1}: Printjob for document sent to printer")
