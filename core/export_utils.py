import csv
from pathlib import Path
from . import database

EXPORT_PATH = Path("./data/inventory_export.csv")

def export_to_csv():
    rows = database.get_all_products()

    header = [
        "code",
        "projekt",
        "gemeinde",
        "einsatzort",
        "kategorie",
        "produkt",
        "produktdetails",
        "serialnummer",
        "kv_id",
        "einzelpreis_netto",
        "einzelpreis_brutto",
        "mwst_satz",
        "anzahl",
        "elo_nummer",
        "geliefert_am",
        "lieferumfang",
        "funktionspruefung",
        "notiz",
        "getestet_am",
        "getestet_von",
        "hersteller",
        "anschaffungsjahr",
        "bestellt_am",
        "uebergeben_am",
        "bemerkungen",
        "erstellt_von",
        "geaendert_von",
    ]

    with open(EXPORT_PATH, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows)

    return EXPORT_PATH

