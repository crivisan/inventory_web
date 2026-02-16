from pathlib import Path
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.graphics.barcode import code128
from PyPDF2 import PdfMerger
LABEL_DIR = Path("./data/labels")
LABEL_DIR.mkdir(parents=True, exist_ok=True)

def make_pdf_label(
    code_text,
    output_dir,
    label_text="LandLieben",
    width_mm=22,
    height_mm=6,
):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    file_path = output_dir / f"{code_text}.pdf"
    c = canvas.Canvas(str(file_path), pagesize=(width_mm * mm, height_mm * mm))

    bc = code128.Code128(
        code_text,
        barWidth=0.1 * mm,
        barHeight=height_mm * 0.4 * mm,
    )

    x = (width_mm * mm - bc.width) / 2
    y = (height_mm * mm - bc.height) / 2
    bc.drawOn(c, x, y)

    text_to_show = label_text or code_text
    c.setFont("Helvetica", 3)
    text_width = c.stringWidth(text_to_show, "Helvetica", 3)
    c.drawString((width_mm * mm - text_width) / 2, y - 1 * mm, text_to_show)

    c.showPage()
    c.save()

    return file_path


def merge_pdfs(pdf_paths, output_file):
    merger = PdfMerger()

    for pdf in pdf_paths:
        merger.append(str(pdf))

    output_file = Path(output_file)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    merger.write(str(output_file))
    merger.close()

    return output_file

