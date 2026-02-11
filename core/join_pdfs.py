from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from pdfrw import PdfReader
from pdfrw.buildxobj import pagexobj
from pdfrw.toreportlab import makerl

import os

# -----------------------
# CONFIG
# -----------------------
INPUT_DIR = r'C:\Users\crivi\HUB\KV-KUS\code\inventory_web\data\testpackingpdf'        # folder with barcode PDFs
OUTPUT_PDF = r"C:\Users\crivi\HUB\KV-KUS\code\inventory_web\data\labels_24.pdf"

COLS = 3
ROWS = 8

LABEL_WIDTH = 63 * mm
LABEL_HEIGHT = 33 * mm

MARGIN_X = 10 * mm
MARGIN_Y = 10 * mm
GAP_X = 2 * mm
GAP_Y = 2 * mm
# -----------------------

c = canvas.Canvas(OUTPUT_PDF, pagesize=A4)
page_width, page_height = A4

pdf_files = sorted(
    f for f in os.listdir(INPUT_DIR)
    if f.lower().endswith(".pdf")
)

for i, filename in enumerate(pdf_files[:24]):
    pdf_path = os.path.join(INPUT_DIR, filename)

    col = i % COLS
    row = i // COLS

    x = MARGIN_X + col * (LABEL_WIDTH + GAP_X)
    y = page_height - MARGIN_Y - (row + 1) * (LABEL_HEIGHT + GAP_Y)

    pdf = PdfReader(pdf_path)
    src_page = pdf.pages[0]

    xobj = pagexobj(src_page)
    rl_obj = makerl(c, xobj)

    src_width = float(xobj.BBox[2])
    src_height = float(xobj.BBox[3])

    scale_x = LABEL_WIDTH / src_width
    scale_y = LABEL_HEIGHT / src_height

    c.saveState()
    c.translate(x, y)
    c.scale(scale_x, scale_y)
    c.doForm(rl_obj)
    c.restoreState()

c.save()

print("✅ labels_24.pdf created successfully")
