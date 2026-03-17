from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd
from flask import Flask, flash, redirect, render_template, request, url_for

from parser import InvoiceParseError, convert_pdf_to_excel


app = Flask(__name__)
app.secret_key = "invoice-tracker-secret"

BASE_DIR = Path(__file__).resolve().parent
INPUT_DIR = BASE_DIR / "input"
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "output"
INVOICE_FILE = DATA_DIR / "invoice.xlsx"
FINAL_FILE = DATA_DIR / "finalized_invoice.xlsx"

invoice_list: list[dict] = []
scan_log: list[dict] = []



def ensure_directories() -> None:
    INPUT_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


#convert value into an int, if it cannot, return 0.
def to_int(value, default: int = 0) -> int:
    try:
        if value is None or value == "":
            return default
        return int(value)
    except (ValueError, TypeError):
        return default

#grabs pdf file from input, returns excel of invoice
def import_pdf() -> tuple[Path, int]:
    pdf_path = next(INPUT_DIR.glob("*.pdf"), None)

    if pdf_path is None:
        raise FileNotFoundError(f"No PDF found in {INPUT_DIR}")

    return convert_pdf_to_excel(pdf_path, INVOICE_FILE)

#load excel invoice into global invoice_list list
def load_invoice() -> None:
    global invoice_list
    ensure_directories()

    if not INVOICE_FILE.exists():
        import_pdf()

    records = pd.read_excel(INVOICE_FILE).fillna("").to_dict(orient="records")

    for item in records:
        item["UPC"] = str(item.get("UPC", "")).strip()
        item["Desc"] = str(item.get("Desc", "")).strip()
        item["DRQty"] = to_int(item.get("DRQty", 0))
        item["ScanQty"] = to_int(item.get("ScanQty", 0))

    invoice_list = records

#update and save working invoice excel file
def save_progress() -> None:
    pd.DataFrame(invoice_list, columns=["UPC", "Desc", "DRQty", "ScanQty"]).to_excel(INVOICE_FILE, index=False)

#creat final excel file
def save_final_file() -> None:
    final_records = []
    for item in invoice_list:
        row = dict(item)
        row["Difference"] = to_int(row.get("ScanQty", 0)) - to_int(row.get("DRQty", 0))
        final_records.append(row)

    pd.DataFrame(final_records).to_excel(FINAL_FILE, index=False)

#may or may not work, test on an actual invoice.!!!!!!!!!!!!!!!
def candidate_upcs(upc: str) -> set[str]:
    upc = "".join(ch for ch in str(upc).strip() if ch.isdigit())
    candidates = set()

    if not upc:
        return candidates

    # Full code as written
    candidates.add(upc)

    # Remove final check digit
    if len(upc) >= 2:
        candidates.add(upc[:-1])

    # Special case for 14-digit invoice UPC:
    # Zebra may send digits 3 through 13 (drop first 2 and final check digit)
    if len(upc) == 14:
        candidates.add(upc[2:-1])

    return candidates

#takes scan_upc and compares to every record in invoice_list
def find_item_by_upc(scan_upc: str):
    scan_upc = "".join(ch for ch in str(scan_upc).strip() if ch.isdigit())

    for item in invoice_list:
        if scan_upc in candidate_upcs(item["UPC"]):
            return item

    return None

#scanlog, log of 15 most recent operations.
def log_scan(action: str, upc: str, message: str) -> None:
    scan_log.insert(
        0,
        {
            "time": datetime.now().strftime("%H:%M:%S"),
            "action": action,
            "upc": upc,
            "message": message,
        },
    )
    if len(scan_log) > 15:
        scan_log.pop()

#dashboard_stats, an item is matched if expected QTY == scanned QTY
def get_dashboard_stats() -> dict:
    total_items = len(invoice_list)
    total_expected = sum(to_int(item.get("DRQty", 0)) for item in invoice_list)
    total_scanned = sum(to_int(item.get("ScanQty", 0)) for item in invoice_list)
    matched_items = sum(1 for item in invoice_list if to_int(item.get("ScanQty", 0)) == to_int(item.get("DRQty", 0)))
    return {
        "total_items": total_items,
        "total_expected": total_expected,
        "total_scanned": total_scanned,
        "matched_items": matched_items,
    }


#Gets data needed to render page, sends it to index.html
@app.route("/", methods=["GET"])
def index():
    last_item = None
    last_upc = request.args.get("last_upc", "").strip()
    if last_upc:
        last_item = find_item_by_upc(last_upc)

    stats = get_dashboard_stats()
    return render_template(
        "index.html",
        last_item=last_item,
        last_upc=last_upc,
        scan_log=scan_log,
        pdf_name=(INVOICE_FILE.name if INVOICE_FILE.exists() else "No PDF found"),
        invoice_file=(INVOICE_FILE.name if INVOICE_FILE.exists() else "No invoice loaded"),
        **stats,
    )


@app.route("/scan", methods=["POST"])
def scan():
    upc = request.form.get("upc", "").strip()
    action = request.form.get("action", "add").strip()

    if not upc:
        flash("No UPC entered.")
        return redirect(url_for("index"))

    item = find_item_by_upc(upc)
    if item is None:
        flash(f"UPC not found: {upc}")
        log_scan(action, upc, "UPC not found")
        return redirect(url_for("index", last_upc=upc))

    if action == "remove":
        item["ScanQty"] = max(0, to_int(item.get("ScanQty", 0)) - 1)
        message = f"Removed 1 from {item['Desc']}. ScanQty = {item['ScanQty']}"
    else:
        item["ScanQty"] = to_int(item.get("ScanQty", 0)) + 1
        message = f"Added 1 to {item['Desc']}. ScanQty = {item['ScanQty']}"

    flash(message)
    log_scan(action, upc, message)
    return redirect(url_for("index", last_upc=upc))


@app.route("/finalize", methods=["POST"])
def finalize():
    save_final_file()
    flash(f"Finalized file saved as {FINAL_FILE.name}")
    return redirect(url_for("index"))


@app.route("/save", methods=["POST"])
def save_excel():
    save_progress()
    flash("Invoice progress saved.")
    return redirect(url_for("index"))


@app.route("/reload-pdf", methods=["POST"])
def reload_pdf():
    global invoice_list
    try:
        pdf_path, count = import_pdf()
        if INVOICE_FILE.exists():
            INVOICE_FILE.unlink()
        load_invoice()
        flash(f"Imported {count} rows from {pdf_path.name}")
    except (FileNotFoundError, InvoiceParseError, ValueError) as exc:
        flash(f"PDF import failed: {exc}")
    return redirect(url_for("index"))

def print_startup_banner() -> None:
    line = "=" * 72
    sub = "-" * 72

    print()
    print(line)
    print(" " * 20 + "INVOICE TRACKER")
    print(line)
    print("Welcome.")
    print("This program converts a PDF invoice into an excel invoice file,")
    print("hosts a local scanning webpage, and tracks scanned quantities.")
    print(sub)
    print("FOLDERS")
    print(f"  input/   -> place invoice PDFs here")
    print(f"  data/    -> excel invoice files are stored here")
    print(f"  output/  -> optional exported files")
    print(sub)
    print("HOW TO USE")
    print("  1) STARTING A NEW INVOICE")
    print("     - Put the new invoice PDF into input/")
    print("     - Remove old files from data/, and output/ if you do NOT want to resume")
    print()
    print("  2) CONTINUING AN EXISTING INVOICE")
    print("     - Leave invoice.xlsx in data/")
    print("     - The program will resume from that file if it exists")
    print()
    print("  3) SCANNING")
    print("     - Open the webpage,(second address), on the Zebra")
    print("     - Scan UPCs into the input box")
    print("     - Use Add for normal scanning")
    print("     - Use Remove to undo a mistaken scan")
    print()
    print("  4) FINALIZING")
    print("     - Use the Finalize button in the webpage")
    print("     - A finalized Excel file will be written with Difference column")
    print(sub)
    print("NOTES")
    print("  - Keep only the invoice PDF you want to use in input/ whenever possible")
    print("  - If the webpage freezes, press 'control' and 'c' at the same time")
    print("  - Do not open files while the server is using them")
    print(sub)
    print(line)
    print()

if __name__ == "__main__":
    ensure_directories()
    
    print_startup_banner()
    input("\nPress 'Enter' when ready to proceed.")

    try:
        load_invoice()
    except (FileNotFoundError, InvoiceParseError, ValueError) as exc:
        print(f"Startup warning: {exc}")
    app.run(host="0.0.0.0", port=5000, debug=False)

