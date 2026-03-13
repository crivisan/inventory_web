import csv
import pandas as pd
from pathlib import Path
from . import database

EXPORT_PATH = Path("./data/inventory_export.xlsx")

def export_to_excel():
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

    # Create DataFrame
    df = pd.DataFrame(rows, columns=header)

    # Ensure numeric columns are numeric (important for Excel)
    numeric_cols = [
        "einzelpreis_netto",
        "einzelpreis_brutto",
        "mwst_satz",
        "anzahl",
        "anschaffungsjahr",
    ]

    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # Write to Excel
    df.to_excel(EXPORT_PATH, index=False)

    return EXPORT_PATH

def export_rows_to_excel(rows, filename="inventory_export.xlsx"):

    import pandas as pd
    from pathlib import Path

    EXPORT_PATH = Path(f"./data/{filename}")

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

    df = pd.DataFrame(rows, columns=header)

    numeric_cols = [
        "einzelpreis_netto",
        "einzelpreis_brutto",
        "mwst_satz",
        "anzahl",
        "anschaffungsjahr",
    ]

    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df.to_excel(EXPORT_PATH, index=False)

    return EXPORT_PATH


#EXPORT_PATH = Path("./data/inventory_export.csv")
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
    # Remove double quotes from produktdetails column
    cleaned_rows = []
    for row in rows:
        row = list(row)

        # produktdetails index (based on your header order)
        produktdetails_index = header.index("produktdetails")

        if row[produktdetails_index]:
            row[produktdetails_index] = row[produktdetails_index].replace(',', '.').replace('"', '').replace('-', ' ').replace('(', ' ').replace(')', ' ').replace('\n', ' ').replace(';', '.') #- #( # )

        cleaned_rows.append(row)

    with open(EXPORT_PATH, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f, delimiter=";")
        writer.writerow(header)
        writer.writerows(cleaned_rows)

    return EXPORT_PATH

