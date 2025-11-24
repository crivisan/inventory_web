import csv
from pathlib import Path
from . import database

EXPORT_PATH = Path("./data/inventory_export.csv")

def export_to_csv():
    rows = database.get_all_products()
    header = ["id","code","gemeinde","einsatzort","kategorie","produkttyp","produktdetails",
              "anzahl","hersteller","lieferant","shop_link","preis_netto","preis_brutto",
              "bezahlt","bestellt_am","geliefert_am","uebergeben_am","projekt","bemerkungen"]
    with open(EXPORT_PATH, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows)
    return EXPORT_PATH
