# Invoice Tracker

Invoice Tracker is a local Flask web app for scanning invoice items by UPC and tracking counted quantities against expected quantities.

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
