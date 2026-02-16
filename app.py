from flask import (
    Flask, render_template, request, redirect, url_for, flash, send_file
)
import os
from core import database, label_printer, export_utils, user_utils, utils
import json
from pathlib import Path

from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
import io
import datetime


app = Flask(__name__)
app.secret_key = "landlieben-secret"
app.config["UPLOAD_FOLDER"] = "data"
app.config["DB_PATH"] = os.path.join("data", "inventory.db")
login_manager = LoginManager(app)
login_manager.login_view = "login"
data_path = Path("./data/gemeinden.json")

# ---------------------------------------------------------
# Home page
# ---------------------------------------------------------
@app.route("/")
@login_required
def index():
    return render_template("index.html")



# ---------------------------------------------------------
# User Login
# ---------------------------------------------------------
class User(UserMixin):
    def __init__(self, id, username, role):
        self.id = id
        self.username = username
        self.role = role

@login_manager.user_loader
def load_user(user_id):
    conn = database.get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, username, role FROM users WHERE id=?", (user_id,))
    row = cur.fetchone()
    conn.close()
    return User(*row) if row else None

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        user = user_utils.verify_user(username, password)
        if user:
            login_user(User(user[0], user[1], user[3]))
            flash("Erfolgreich eingeloggt.", "success")
            return redirect(url_for("index"))
        else:
            flash("Ungültige Anmeldedaten.", "danger")
    return render_template("login.html")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Abgemeldet.", "info")
    return redirect(url_for("login"))



# ---------------------------------------------------------
# Verwaltung – Add new product
# ---------------------------------------------------------
@app.route("/verwaltung", methods=["GET", "POST"])
def verwaltung():
    from core import database, label_printer, utils

    einsatzorte = database.get_options("einsatzorte")
    hersteller = database.get_options("hersteller")
    gemeinden = database.get_all_gemeinden()

    if request.method == "POST":
        form = request.form

        # --- Load abbreviation ---
        with open(data_path, "r", encoding="utf-8") as f:
            gdata = json.load(f)

        abbr = (
            gdata["Gemeinden"].get(form["gemeinde"])
            or gdata["VGs"].get(form["gemeinde"])
        )

        if not abbr:
            flash("Keine Abkürzung für die ausgewählte Gemeinde gefunden.", "danger")
            return redirect(url_for("verwaltung"))

        gemeinde = form["gemeinde"]
        dt = datetime.date.today()

        purchase_date = form.get("bestellt_am") or dt.isoformat()
        code = utils.generate_code(abbr, purchase_date)

        # ---------------- VAT + PRICE ----------------
        einzelpreis_netto = float(form.get("preis_netto") or 0) or None
        einzelpreis_brutto = float(form.get("preis_brutto") or 0) or None

        mwst_raw = form.get("mwst_satz")

        if mwst_raw == "custom":
            mwst_satz = float(form.get("mwst_custom") or 0)
        else:
            mwst_satz = float(mwst_raw or 19)

        einzelpreis_netto, einzelpreis_brutto = utils.calculate_prices(
            einzelpreis_netto,
            einzelpreis_brutto,
            mwst_satz
        )

        # ---------------- CATEGORY ----------------
        is_verbrauch = False  # optional if you removed checkbox
        kategorie = utils.assign_category(einzelpreis_netto or 0, is_verbrauch)

        # ---------------- DATA DICT ----------------
        data = dict(
            code=code,
            projekt=form.get("projekt"),
            gemeinde=gemeinde,
            einsatzort=form.get("einsatzort"),
            kategorie=int(kategorie) if kategorie else None,
            produkt=form.get("produkt"),
            produktdetails=form.get("produktdetails"),
            serialnummer=form.get("serialnummer"),
            kv_id=form.get("kv_id"),
            einzelpreis_netto=einzelpreis_netto,
            einzelpreis_brutto=einzelpreis_brutto,
            mwst_satz=mwst_satz,
            anzahl=int(form.get("anzahl", 1)),
            elo_nummer=form.get("elo_nummer"),
            geliefert_am=form.get("geliefert_am") or None,
            lieferumfang=form.get("lieferumfang"),
            funktionspruefung=form.get("funktionspruefung"),
            notiz=form.get("notiz"),
            getestet_am=form.get("getestet_am"),
            getestet_von=form.get("getestet_von"),
            hersteller=form.get("hersteller"),
            anschaffungsjahr=purchase_date[:4] if purchase_date else None,
            bestellt_am=purchase_date,
            uebergeben_am=form.get("uebergeben_am") or None,
            bemerkungen=form.get("bemerkungen"),
            erstellt_von=current_user.username,
            geaendert_von=current_user.username,
        )

        # ---------------- SAVE DROPDOWN OPTIONS ----------------
        if form.get("einsatzort"):
            database.add_option("einsatzorte", form.get("einsatzort"))

        if form.get("hersteller"):
            database.add_option("hersteller", form.get("hersteller"))

        # ---------------- SAVE PRODUCT ----------------
        database.add_product_safe(**data)

        label_text = f"Land-lieben: {gemeinde} - {data['projekt']}"
        #label_printer.make_pdf_label(code, label_text)

        flash(f"Produkt '{data['produkt']}' hinzugefügt.", "success")
        return redirect(url_for("verwaltung"))

    products = database.get_all_products()

    return render_template(
        "verwaltung.html",
        einsatzorte=einsatzorte,
        hersteller=hersteller,
        gemeinden=gemeinden,
        products=products,
    )





# ---------------------------------------------------------
# Tabelle – View all products
# ---------------------------------------------------------
@app.route("/tabelle")
def tabelle():
    products = database.get_all_products()
    return render_template("tabelle.html", products=products)

from flask import jsonify, request

@app.route("/save_table", methods=["POST"])
def save_table():
    data = request.get_json()
    updates = data.get("updates", [])

    conn = database.get_connection()
    cur = conn.cursor()

    changed = 0

    for row in updates:
        code = row.get("code")
        if not code:
            continue

        # Fetch current DB state
        cur.execute("SELECT * FROM inventory WHERE code=?", (code,))
        existing = cur.fetchone()
        if not existing:
            continue

        # Build new values tuple (EXACT schema order except code & erstellt_von)
        new_values = (
            row.get("projekt"),
            row.get("gemeinde"),
            row.get("einsatzort"),
            row.get("kategorie"),
            row.get("produkt"),
            row.get("produktdetails"),
            row.get("serialnummer"),
            row.get("kv_id"),
            row.get("einzelpreis_netto"),
            row.get("einzelpreis_brutto"),
            row.get("mwst_satz"),
            row.get("anzahl"),
            row.get("elo_nummer"),
            row.get("geliefert_am"),
            row.get("lieferumfang"),
            row.get("funktionspruefung"),
            row.get("notiz"),
            row.get("getestet_am"),
            row.get("getestet_von"),
            row.get("hersteller"),
            row.get("anschaffungsjahr"),
            row.get("bestellt_am"),
            row.get("uebergeben_am"),
            row.get("bemerkungen"),
            current_user.username,  # geaendert_von
            code
        )

        cur.execute("""
            UPDATE inventory SET
                projekt=?,
                gemeinde=?,
                einsatzort=?,
                kategorie=?,
                produkt=?,
                produktdetails=?,
                serialnummer=?,
                kv_id=?,
                einzelpreis_netto=?,
                einzelpreis_brutto=?,
                mwst_satz=?,
                anzahl=?,
                elo_nummer=?,
                geliefert_am=?,
                lieferumfang=?,
                funktionspruefung=?,
                notiz=?,
                getestet_am=?,
                getestet_von=?,
                hersteller=?,
                anschaffungsjahr=?,
                bestellt_am=?,
                uebergeben_am=?,
                bemerkungen=?,
                geaendert_von=?
            WHERE code=?
        """, new_values)

        changed += 1

    conn.commit()
    conn.close()
    return jsonify({"message": f"{changed} Zeile(n) aktualisiert."})



@app.route("/delete_rows", methods=["POST"])
def delete_rows():
    data = request.get_json()
    ids = data.get("ids", [])
    print(ids)
    if not ids:
        return jsonify({"message": "Keine IDs angegeben."})

    conn = database.get_connection()
    cur = conn.cursor()
    for pid in ids:
        cur.execute("DELETE FROM inventory WHERE code=?", (pid,))
    conn.commit()
    conn.close()
    return jsonify({"message": f"{len(ids)} Zeile(n) gelöscht."})

@app.route("/print_selected", methods=["POST"])
def print_selected():
    data = request.get_json()
    ids = data.get("ids", [])

    if not ids:
        return jsonify({"message": "Keine IDs angegeben."})

    conn = database.get_connection()
    cur = conn.cursor()

    cur.execute(
        f"SELECT * FROM inventory WHERE code IN ({','.join(['?'] * len(ids))})",
        ids
    )
    rows = cur.fetchall()
    conn.close()

    if not rows:
        return jsonify({"message": "Keine Produkte gefunden."})

    output_dir = Path("data/temp_labels")
    output_dir.mkdir(parents=True, exist_ok=True)

    pdf_paths = []

    for p in rows:
        code = p[0]  # assuming code is first column

        pdf_path = label_printer.make_pdf_label(
            code_text=code,
            output_dir=output_dir,
            label_text=code  # 👈 important
        )

        pdf_paths.append(pdf_path)

    # Merge into one PDF
    final_pdf_path = output_dir / "merged_labels.pdf"
    label_printer.merge_pdfs(pdf_paths, final_pdf_path)

    return send_file(
        final_pdf_path,
        mimetype="application/pdf",
        as_attachment=True,
        download_name="Etiketten_Landlieben.pdf"
    )




@app.route("/berichte")
def berichte():
    return render_template("berichte.html")


# ---------------------------------------------------------
# Scan – Barcode lookup
# ---------------------------------------------------------
@app.route("/scan", methods=["GET", "POST"])
def scan():
    item = None
    if request.method == "POST":
        code = request.form["code"].strip()
        item = database.get_product_by_code(code)
        if not item:
            flash("Kein Produkt mit diesem Code gefunden.", "danger")
        else:
            flash("Produkt gefunden!", "success")
    return render_template("scan.html", item=item)


# ---------------------------------------------------------
# Export – CSV download
# ---------------------------------------------------------
@app.route("/export")
def export_csv():
    path = export_utils.export_to_csv()
    return send_file(path, as_attachment=True)





# ---------------------------------------------------------
# Run local server
# ---------------------------------------------------------
if __name__ == "__main__":
    app.run(debug=True, port=9090)
