from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List

import pandas as pd
import pdfplumber


ITEM_ROW_RE = re.compile(
    r"""
    ^\s*
    (?P<line>\d{1,3}(?:,\d{3})*)          # line number
    \s+
    (?P<upc>\d{12,14})                    # UPC code
    \s+
    (?P<article>\d{8})                    # article number
    \s+
    (?P<desc>.*?)                          # description (possibly partial)
    \s+
    (?P<pack>\d+)                         # pack count
    \s+
    (?P<size>\d+x[\w.]+)                 # size, e.g. 24x473.000ML
    \s+
    (?P<ord>\d+)                          # ordered quantity
    \s+
    (?P<dr>\d+)                           # DR quantity
    (?:\s+\d{2,3})?                      # optional error code
    \s*$
    """,
    re.VERBOSE,
)

STOP_MARKERS = (
    "INVOICE SUMMARY BY DEPARTMENT",
    "SHORT SUMMARY",
)

SKIP_PREFIXES = (
    "Page ",
    "Loblaws Inc.",
    "D061 DC Caledon Airport Rd",
    "12203 Airport Rd",
    "Caledon ON ",
    "Invoice",
    "Invoice Number :",
    "Customer :",
    "Invoice Date :",
    "DEPARTMENT:",
    "Line",
    "No.",
    "UPC Code Article Number Description Pack Size Ord",
    "Qty",
    "DR",
    "Err",
    "Code",
    "Unit",
    "Cost",
    "Extended",
    "Tax Retail",
    "Price",
    "GPM",
    "(%)",
    "PR",
    "Department Total",
)


@dataclass
class InvoiceItem:
    upc: str
    desc: str
    dr_qty: int
    scan_qty: int = 0

    def to_record(self) -> dict:
        return {
            "UPC": self.upc,
            "Desc": self.desc.strip(),
            "DRQty": self.dr_qty,
            "ScanQty": self.scan_qty,
        }


class InvoiceParseError(Exception):
    pass



def _should_skip(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return True
    if stripped.startswith(SKIP_PREFIXES):
        return True
    if re.fullmatch(r"\d+\s+\d+", stripped):
        return True
    return False



def _normalize_description(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()



def parse_invoice_pdf(pdf_path: str | Path) -> List[InvoiceItem]:
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    items: list[InvoiceItem] = []
    current: InvoiceItem | None = None

    with pdfplumber.open(str(pdf_path)) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            for raw_line in text.splitlines():
                line = raw_line.strip()

                if any(marker in line for marker in STOP_MARKERS):
                    if current is not None:
                        current.desc = _normalize_description(current.desc)
                        items.append(current)
                        current = None
                    return items

                if _should_skip(line):
                    continue

                match = ITEM_ROW_RE.match(line)
                if match:
                    if current is not None:
                        current.desc = _normalize_description(current.desc)
                        items.append(current)
                    current = InvoiceItem(
                        upc=match.group("upc"),
                        desc=match.group("desc"),
                        dr_qty=int(match.group("dr")),
                    )
                elif current is not None:
                    current.desc = f"{current.desc} {line}".strip()

    if current is not None:
        current.desc = _normalize_description(current.desc)
        items.append(current)

    if not items:
        raise InvoiceParseError(
            "No invoice rows were found. Confirm the PDF matches the expected Loblaws invoice layout."
        )

    return items



def write_invoice_excel(items: Iterable[InvoiceItem], output_path: str | Path) -> Path:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    df = pd.DataFrame([item.to_record() for item in items], columns=["UPC", "Desc", "DRQty", "ScanQty"])
    df.to_excel(output_path, index=False)
    return output_path



def convert_pdf_to_excel(pdf_path: str | Path, output_path: str | Path) -> tuple[Path, int]:
    items = parse_invoice_pdf(pdf_path)
    destination = write_invoice_excel(items, output_path)
    return destination, len(items)


if __name__ == "__main__":
    base_dir = Path(__file__).resolve().parent
    pdf_file = base_dir / "input" / "Form.pdf"
    excel_file = base_dir / "data" / "invoice.xlsx"
    saved_path, count = convert_pdf_to_excel(pdf_file, excel_file)
    print(f"Converted {count} rows to {saved_path}")
