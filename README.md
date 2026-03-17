# Invoice Tracker

Invoice Tracker is a local Flask web app for scanning invoice items by UPC and tracking counted quantities against expected quantities. Made for work, hence why it only supports RCSS standardized documents. Example invoice included if you wanted to test it out.

Intended to be used via a Zebra handheld scanner.

---

## Features

- Imports invoice data from a PDF
- Hosts a local scanning webpage
- Supports **Add** and **Remove** scan modes
- Tracks:
  - expected quantity (`DRQty`)
  - scanned quantity (`ScanQty`)
  - finalized difference (`ScanQty - DRQty`)
- Keeps a recent scan log
- Saves invoice progress to Excel
- Finalizes results into a separate Excel file

---

## Folder Structure

```text
invoice_tracker/
├─READ ME.pptx
├─ app.py
├─ parser.py
├─ requirements.txt
├─ README.md
├─ input/
├─ data/
└─ output/
