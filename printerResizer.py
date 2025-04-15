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

def convert_ps_to_image(ps_data, dpi=300):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".ps") as tmp:    # Create a temporary file from the PS bytestream
        tmp.write(ps_data)
        tmp_path = tmp.name
    
    try:    # Convert the temporary PS file to PNG using Ghostscript
        subprocess.run([
            "gs",
            "-dSAFER",
            "-dBATCH",
            "-dNOPAUSE",
            f"-r{dpi}",
            "-sDEVICE=png16m",
            f"-sOutputFile=./output.png",
            tmp_path
        ], check=True)
    except:
        print(f"Error: Conversion from PS to PNG failed.")
        sys.exit(1)
    finally:
        os.unlink(tmp_path)  # Delete the temporary PS file

def determine_label_type(img):
    #There are different labels label types, we first need to determine which type the label is
    #This program supports 2 label types at the moment: DHL Labels (directly created using DHL website/app) and Amazon return labels
    #DHL label has a continuous line in the middle of the page (y-direction), which is a cut line --> Everything below is irrelevant, everything above is the label
    #Amazon label has a dotted border around the label itself
    
    #Check which label type the provided image is  
    h, w = img.shape[:2] # Get the height and width of the image
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) # Convert the image to grayscale

    # Focus on the middle section of the image where cutting line should be
    middle_y = h // 2
    margin = h // 6  # Search within 1/6 of image height around the middle
    
    # Extract the middle section
    middle_section = gray[middle_y-margin:middle_y+margin, :]
    
    # Apply binary threshold to highlight lines
    _, binary = cv2.threshold(middle_section, 220, 255, cv2.THRESH_BINARY_INV)
    
    # Use Hough Line Transform to detect continuous lines
    lines = cv2.HoughLinesP(binary, 1, np.pi/180, threshold=50, 
                           minLineLength=w*0.9, maxLineGap=50)  # Increased minLineLength and reduced maxLineGap
    
    if lines is not None and len(lines) > 0:
        # Check for significant horizontal lines
        for line in lines:
            x1, y1, x2, y2 = line[0]
            # Check if line is horizontal (y values are close)
            if abs(y2 - y1) < 10:  # Stricter horizontal check
                # Check if line is long enough (must be very long for continuous lines)
                if abs(x2 - x1) > w * 0.6:  # Increased length requirement
                    print("DHL label detected - found horizontal cutting line")
                    return "DHL"

    print("Amazon label detected - no cutting line found")
    return "Other"    # If no continuous line is found, the provided image is assumed as an Amazon label

def extract_label(label_type, img):
    h, w = img.shape[:2] # Get the height and width of the image
    if label_type == "DHL":
        print("No extraction implemented yet!")
    elif label_type == "Other":
        # Since we know the format of the document, we can simply cut off the unwanted regions in y-direction from top and bottom
        new_height = int(h * 0.5)  # Keep only the central part of the image
        
        # Calculate the starting and ending coordinates (values seem random but I tried to find the precise values)
        start_y = int(h * 0.343)    # Start from 34,3% of the height
        end_y   = int(h * 0.627)    # End at 62,7% of the height

        start_x = int(w * 0.15)     # Start from 15% of the width
        end_x   = int(w * 0.77)     # End at 77% of the width
        
        label = img[start_y:end_y, start_x:end_x] # Crop the image to reveal the extracted label
        return label        
    else:
        print("Unknown label type. No extraction implemented.")
        return None
    
def resize_to_4x6(img, dpi=300):
    #TODO: Check orientation of the image and rotate it if necessary --> Not neccesary for now, because we assume we know the label format anyway
    target_size = (int(6*dpi), int(4*dpi))  # 4x6 inches in pixels
    pil_img = Image.fromarray(img)          # Convert the image to PIL format
    fitted_label = ImageOps.fit(pil_img, target_size, method=Image.LANCZOS) # Resize the image to fit the target size of 4x6 inches
    return np.array(fitted_label)           # Convert back to numpy array

def print_image(print_file):
    cv2.imwrite("label.png", print_file)  # Save the image to a file
    conn = cups.Connection()               # Connect to the CUPS server
    printers = conn.getPrinters()         # Get the list of printers
    printer_name = "_PM_241"
    conn.printFile(printer_name, "label.png", "Label", {"media": "Custom.4x6in", "copies": "1"})        
    
def list_printers():
    conn = cups.Connection()               # Connect to the CUPS server
    printers = conn.getPrinters()         # Get the list of printers
    print("Available printers:")
    for printer in printers:
        print(f" - {printer}")

if __name__ == "__main__":
    ps_data = sys.stdin.buffer.read()
    convert_ps_to_image(ps_data)
    
    img         = cv2.imread("output.png")      # Read the converted PNG image
    label_type  = determine_label_type(img)     # Determine the label type
    label       = extract_label(label_type, img)# Extract the label from the image
    
    if label is not None:
        resized_label = resize_to_4x6(label)  # Resize the label to 4x6 inches
        cv2.imwrite("output_resized.png", resized_label)
        cv2.imwrite("output.png", label)  # Save the extracted label as a PNG file
        print_image(resized_label)  # Print the resized label
    else:
        print("No label extracted.")   
        sys.exit(1)
         
    print("Fertig! Die PNG-Datei wurde gespeichert.")