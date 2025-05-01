# Label Auto-Resizer & Printer (DHL/Amazon Return Labels)

This Python tool enables **automatic detection, cropping, resizing, and printing of shipping labels** (currently DHL/Amazon) directly from documents received via a virtual printer (IPPServer). It is optimized for German DHL and amazon return labels with consistent layouts.

This version uses line detection instead of fixed values. Furthermore it allows you to print documents with multiple pages.

## Features

- **Automatic detection** of DHL/Amazon labels using line detection and simple geometric features
- **Dual printer support** – one for labels, one for additional documents (e.g., A4 filing)
- **Temporary file handling** No residual files on disk
- **CUPS integration** for printer management, therefore not directly usable on windows systems
- **Ghostscript-based conversion** from PostScript to PNG

## Configuration (`config.ini`)

### [General] Section

| Parameter         | Default | Description                                   |
|-------------------|---------|-----------------------------------------------|
| `print_documents` | False   | Whether to print additional document info     |

### Printer Sections
-->Name convention: Section has to start with the keyword "Printer", the rest of the name doesn't mater, because the program only uses it's types
| Section           | Parameter      | Example           | Description                         |
|-------------------|---------------|-------------------|-------------------------------------|
| `[Printer_Label]` | `name`        | _PM_241           | CUPS Name of my label printer       |
|                   | `print_format`| Custom.4x6in      | Print format for label printer      |
|                   | `type`        | label             | Must be `label` for labels          |
| `[Printer_A4]`    | `name`        | Samsung_ML_2160   | Name of my document printer         |
|                   | `print_format`| A4                | Print format for document printer   |
|                   | `type`        | document          | Must be `document` for documents    |

## How It Works

1. **PostScript Input:**  
   The IPPServer receives a print job as a PostScript file from any application.

2. **Conversion:**  
   The script converts the PostScript file to PNG images (one per page) using Ghostscript, storing them as temporary files.

3. **Label Type Detection:**  
   Each page image is analyzed to determine if it is a DHL or Amazon label, based on simple geometric features (e.g., a horizontal cut line for DHL).

4. **Cropping and Extraction:**  
   The script extracts the label and (if present) the additional document section from each page, using logic defined in the code and parameters from the config.
   Currently document info is only extracted for DHL labels. AMZ labels are kind of tricky, because some offer additional info, others don't.

5. **Printing:**  
   - The label section is always sent to a printer defined as `label` type.
   - If `print_documents = True` in `[General]` and a document section was extracted, it is sent to a printer of type `document`.

6. **Cleanup:**  
   All intermediate files are handled as temporary files and deleted after use.

## Requirements

- **Python 3.7+**
- **[IPPServer](https://github.com/istopwg/ippsample)** (for virtual print jobs)
- **[Ghostscript](https://www.ghostscript.com/)** (for PS to PNG conversion)
- **[OpenCV](https://opencv.org/)** (`pip install opencv-python`)
- **[pycups](https://pypi.org/project/pycups/)** (`pip install pycups`)
- **configparser** (part of Python standard library)
- **CUPS (Common UNIX Printing System)** (pre-installed on macOS and most Linux distributions)

## Installation

1. **Clone IPPServer** and place your Python script in the main folder.
2. **Install dependencies** ```pip install -r requirements.txt```

## How to run the program

Start the IPPServer and configure it to use the Python script as the print backend:
```python -m ippserver --port 1234 run ./LabelPrinter.py```