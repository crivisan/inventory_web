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
        print('DATE TODAY: ', dt)
    year_month = dt.strftime("%y%m")

    # count existing codes for this Gemeinde and month
    conn = database.get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT COUNT(*) FROM inventory WHERE code LIKE ?",
        (f"LL-{abbr.upper()}-{year_month}-%",),
    )
    count = cur.fetchone()[0]
    conn.close()

    seq = count + 1
    return f"LL-{abbr.upper()}-{year_month}-{seq:04d}"



def assign_category(preis_netto: float, is_verbrauch: bool = False) -> int:
    """
    Returns category type:
    1 = > 1000 €
    2 = 50–1000 €
    3 = < 50 €
    4 = Verbrauchsmaterial (manual)
    """
    if is_verbrauch:
        return 4
    if preis_netto > 1000:
        return 1
    if preis_netto >= 50:
        return 2
    return 3


def calculate_prices(preis_netto, preis_brutto, mwst_satz):
    """
    Returns (netto, brutto)
    - If one value is missing, it is calculated
    - If both are given, they are returned unchanged
    """
    mwst = (mwst_satz or 0) / 100

    if preis_netto and not preis_brutto:
        preis_brutto = round(preis_netto * (1 + mwst), 2)

    elif preis_brutto and not preis_netto:
        preis_netto = round(preis_brutto / (1 + mwst), 2)

    return preis_netto, preis_brutto
