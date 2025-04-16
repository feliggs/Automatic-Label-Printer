# Label Auto-Resizer & Printer (DHL/Amazon Return Labels)

This simple Python tool enables **automatic detection, cropping, resizing, and printing of shipping labels** (currently only DHL/Amazon) directly from documents received via a virtual printer (IPPServer). Designed for German labels with consistent layouts. Advanced detection is omitted because the software in my application runs on very limited hardware and needs to be as fast as possible.

## Features

- **Automatic detection** of DHL/Amazon labels using basic layout features
- **Configurable cropping** via INI file for different label types
- **Temporary file handling** - no residual files on disk
- **Dual printer support** - labels vs. additional info (e.g., A4 filing)
- **CUPS integration** for physical printer management
- **Ghostscript-based conversion** from PostScript to PNG

---

## Configuration (`config.ini`)

### [General] Section
| Parameter         | Default | Description                                  |
|-------------------|---------|----------------------------------------------|
| `dpi`             | 300     | Output resolution for resizing               |
| `label_width`     | 4       | Label width in inches                        |
| `label_height`    | 6       | Label height in inches                       |
| `default_printer` | _PM_241 | Primary label printer (4x6, my printer model)|

### Label Sections ([DHL]/[Amazon])
| Parameter                   | Example | Description                                  |
|-----------------------------|---------|----------------------------------------------|
| `label_start_y`             | 0.1     | Top crop position (percentage of height)     |
| `label_end_y`               | 0.43    | Bottom crop position                         |
| `label_start_x`             | 0.06    | Left crop position (percentage of width)     |
| `label_end_x`               | 0.95    | Right crop position                          |
| `print_additional_info`     | 0       | Enable/disable additional info printing      |
| `additional_info_printer`   | HP_Office | Printer for documentation copies (A4)       |


## How It Works

## Core Assumptions

- **Known Document Layouts:**  
  The tool is designed to work with standardized DHL and Amazon return labels. It assumes that the structure and proportions of these labels remain consistent.

- **Simple Detection Logic:**  
  Complex detection mechanisms are deliberately avoided because the software runs on low-powered hardware, where speed and efficiency are prioritized.

- **No OCR or Advanced Image Analysis:**  
  The script does not use OCR or rotation handling. It expects the label to be as provided by DHL/Amazon (see examples).

## Processing Workflow

1. **PostScript Input:**  
   The virtual printer (IPPServer) receives a print job as a PostScript file from any application.

2. **Conversion:**  
   The script converts the PostScript file to a PNG image using Ghostscript, storing the result in a temporary file. IPPServer has it's own implementation of directly transferring PDF files but I didn' t have success with that.

3. **Label Type Detection:**  
   The script analyzes the PNG image to determine whether it is a DHL or Amazon return label, based on simple geometric features (e.g., a horizontal cut line for DHL).

4. **Cropping:**  
   Using cropping parameters defined in the configuration file (`config.ini`), the relevant label area (and optionally an additional info area) is extracted from the image.

5. **Resizing:**  
   The cropped label is resized to the target format (default: 4x6 inches at 300 dpi), maintaining aspect ratio and centering it on a white background.

6. **Printing:**  
   The processed label (and, if enabled, additional info) is sent to the configured printer(s) using CUPS. All intermediate files are handled as temporary files and deleted after use.

## Configuration and Extensibility

- **All cropping and printing parameters are set in `config.ini`.**  
  You can add new label types by creating new sections in the config file and specifying the cropping coordinates and printer options.

- **Default printer:**  
  The `[General]` section's `default_printer` is used for label printing.  
  For additional info (e.g., for archiving on A4), set `print_additional_info = 1` and specify `additional_info_printer` in the relevant label section.

- **Flexible label support:**  
  To support new label types, simply add a new section in the config file with the required cropping and printing parameters - Afterwards implement your visual detection inside of the `determine_label_type` method.

## Requirements

- **Python 3.7+**
- **[IPPServer](https://github.com/istopwg/ippsample)**  
  Used as a virtual network printer to receive print jobs as PostScript files.
- **[Ghostscript](https://www.ghostscript.com/)**  
  Required for converting PostScript files to PNG images.
- **[OpenCV](https://opencv.org/)**  
  For image processing and manipulation.  
  Install with: `pip install opencv-python`
- **[Pillow](https://python-pillow.org/)**  
  For advanced image resizing and handling.  
  Install with: `pip install pillow`
- **[pycups](https://pypi.org/project/pycups/)**  
  Python bindings for CUPS, used to send print jobs to physical printers.  
  Install with: `pip install pycups`
- **CUPS (Common UNIX Printing System)**  
  Needed for printer management and job submission.  
  Pre-installed on macOS and most Linux distributions.
- **configparser**  
  For reading configuration files (`config.ini`).  
  This is part of the Python standard library, no extra installation needed.

**Note:**  
This tool is designed for UNIX-like systems (macOS, Linux) due to its reliance on CUPS and IPPServer.  
Windows is not supported. Only tested on MacOS.


## Installation

1. **Clone IPPServer** and place `printerResizer.py` in the main folder.
2. **Install dependencies using `requirements.txt`**:


## How to run the program

Simply start the IPPServer using `python -m ippserver --port 1234 run ./printerResizer.py`.
Every file the IPPServer receives is directly transmitted to the python script.