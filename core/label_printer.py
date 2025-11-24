from pathlib import Path
from reportlab.lib.units import mm
from reportlab.graphics.barcode import code128
from reportlab.pdfgen import canvas
from . import database
import os

LABEL_DIR = Path("./data/labels")
LABEL_DIR.mkdir(parents=True, exist_ok=True)


def make_pdf_label(code_text, label_text=None, width_mm=22, height_mm=6):
    """
    Create one PDF label (vector barcode + optional text) for thermal printers.
    Default size: 40x30 mm (Phomemo M110).
    """
    file_name = f"{code_text}.pdf"
    path = LABEL_DIR / file_name
    c = canvas.Canvas(str(path), pagesize=(width_mm * mm, height_mm * mm))

    # --- draw barcode ---
    bc = code128.Code128(code_text, barWidth=0.1 * mm,
                         barHeight=height_mm * 0.4 * mm)
    x = (width_mm * mm - bc.width) / 2
    y = (height_mm * mm - bc.height) / 2
    bc.drawOn(c, x, y)

    # --- draw text below barcode ---
    text_to_show = code_text#label_text or code_text
    c.setFont("Helvetica", 3)
    text_width = c.stringWidth(text_to_show, "Helvetica", 3)
    c.drawString((width_mm * mm - text_width) / 1.5, y - 1 * mm, text_to_show)

    c.showPage()
    c.save()
    return path


def open_label_folder():
    """Open the folder with generated PDF labels."""
    try:
        os.startfile(LABEL_DIR)
    except Exception:
        print(f"Labels saved under: {LABEL_DIR}")


def generate_label_for_product(product):
    """
    Create one label PDF for a single DB product entry.
    """
    code = product[1]
    gemeinde = product[2]
    projekt = product[17] or ""
    label_text = f"Land-lieben: {gemeinde} - {projekt}" if projekt else f"Land-lieben: {gemeinde}"
    return make_pdf_label(code, label_text)


def generate_labels(products):
    """Generate PDF labels for a list of DB products."""
    created = []
    for p in products:
        created.append(generate_label_for_product(p))
    open_label_folder()
    return created


def generate_all_labels():
    """Generate labels for all DB records."""
    all_products = database.get_all_products()
    return generate_labels(all_products)
