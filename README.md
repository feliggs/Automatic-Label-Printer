# Label Auto-Resizer & Printer (DHL/Amazon Return Labels)

This Python tool enables **automatic detection, cropping, resizing, and printing of shipping labels** (for now only DHL and Amazon return labels) directly from A4 documents received via a virtual printer (IPPServer).

It saves time and effort by eliminating manual cropping and ensures perfect prints on label printers (4x6 inch, format can be adjusted).

## Example Label

The labels I used and tested look like this (DHL germany / Amazon returns). Since I do not use other shipping providers, I do not have any labels (and a need). I am going to add other label types in the future, this requires some advanced detection, the detection process right now is really basic.

![DHL label](/example_labels/example_dhl.png)
![Amazon label](/example_labels/example_amazon.png)

---

## Features

- **Automatic detection** of DHL and Amazon return labels
- **Automatic cropping** of the relevant area
- **Resizing** to 4x6 inch (300 dpi) for label printers
- **Direct printing** to a real printer via CUPS
- **Integration with IPPServer**: acts as a virtual network printer
- **Tested on macOS, should work on Linux-based systems too** (not Windows, due to CUPS dependency)
- **Simple, robust approach**: assumes label structure is consistent

## How It Works

1. **IPPServer** receives a print job (PostScript file) from any application.
2. The script:
   - Converts the PS file to PNG using Ghostscript
   - Detects the label type (DHL or Amazon return)
   - Crops the label
   - Resizes the label to 4x6 inch (1200x1800 px at 300 dpi)
   - Sends the result to your real label printer via CUPS

## Requirements

- Python 3.7+
- [IPPServer](https://github.com/istopwg/ippsample) (for virtual printer)
- [Ghostscript](https://www.ghostscript.com/) (for PS to PNG conversion)
- [OpenCV](https://opencv.org/) (`pip install opencv-python`)
- [Pillow](https://python-pillow.org/) (`pip install pillow`)
- [pycups](https://pypi.org/project/pycups/) (`pip install pycups`)
- CUPS (Common UNIX Printing System, pre-installed on macOS and most Linux distros)

## Installation

1. **Clone IPPServer** and place `printerResizer.py` in the main folder.
2. **Install dependencies**:

## How to run the program

Simply start the IPPServer using `python -m ippserver --port 1234 run ./printerResizer.py`.
Every file the IPPServer receives is directly transmitted to the python script.
