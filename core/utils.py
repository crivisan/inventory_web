import datetime
from . import database

def generate_code(abbr: str, purchase_date: str) -> str:
    """
    Generate LL-ABR-YYMM-#### style code.
    YYMM comes from purchase_date (yyyy-mm-dd),
    counter resets per Gemeinde+month.
    """
    # parse purchase_date -> YYMM
    try:
        dt = datetime.datetime.strptime(purchase_date, "%Y-%m-%d")
    except Exception:
        dt = datetime.date.today()
    year_month = dt.strftime("%y%m")

    # count existing codes for this Gemeinde and month
    conn = database.get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT COUNT(*) FROM products WHERE code LIKE ?",
        (f"LL-{abbr.upper()}-{year_month}-%",),
    )
    count = cur.fetchone()[0]
    conn.close()

    seq = count + 1
    return f"LL-{abbr.upper()}-{year_month}-{seq:04d}"

