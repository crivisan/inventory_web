from flask import (
    Flask, render_template, request, redirect, url_for, flash, send_file
)
import os
from core import database, label_printer, export_utils
import json
from pathlib import Path

from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from core import user_utils
import io
import zipfile


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

    # --- Load dropdown data ---
    einsatzorte = database.get_options("einsatzort")
    kategorien = database.get_options("kategorie")
    produkttypen = database.get_options("produkttyp")
    hersteller = database.get_options("hersteller")
    lieferanten = database.get_options("lieferant")
    gemeinden = database.get_all_gemeinden() 

    if request.method == "POST":
        form = request.form
        with open(data_path, "r", encoding="utf-8") as f:
            gdata = json.load(f)
        abbr = (gdata["Gemeinden"].get(form["gemeinde"])
            or gdata["VGs"].get(form["gemeinde"])
                )
        if not abbr:
            flash("Keine Abkürzung für die ausgewählte Gemeinde gefunden.", "danger")
            return redirect(url_for("verwaltung"))
        gemeinde = form["gemeinde"]
        purchase_date = form["bestellt"] or "2025-01-01"
        code = utils.generate_code(abbr, purchase_date)

        data = dict(
            code=code,
            gemeinde=gemeinde,
            einsatzort=form["einsatzort"],
            kategorie=form["kategorie"],
            produkttyp=form["produkttyp"],
            produktdetails=form["produktdetails"],
            anzahl=int(form.get("anzahl", 1)),
            hersteller=form["hersteller"],
            lieferant=form["lieferant"],
            shop_link=form["shop_link"],
            preis_netto=float(form["preis_netto"] or 0),
            preis_brutto=float(form["preis_brutto"] or 0),
            bezahlt="Ja" if "bezahlt" in form else "Nein",
            bestellt_am=purchase_date,
            geliefert_am=form.get("geliefert") or "2025-01-01",
            uebergeben_am=form.get("uebergeben") or "2025-01-01",
            projekt=form["projekt"],
            bemerkungen=form["bemerkungen"],
            erstellt_von=current_user.username,
            geaendert_von=current_user.username,
        )

        # Save dropdown options
        for f in ["einsatzort", "kategorie", "produkttyp", "hersteller", "lieferant"]:
            database.add_option(f, form[f])

        # Save product
        data["erstellt_von"] = current_user.username
        database.add_product_safe(**data)
        label_text = f"Land-lieben: {gemeinde} - {data['projekt']}"
        label_printer.make_pdf_label(code, label_text)

        flash(f"Produkt '{data['produkttyp']}' hinzugefügt.", "success")
        return redirect(url_for("verwaltung"))

    # --- show form with existing entries preview ---
    products = database.get_all_products()
    return render_template(
        "verwaltung.html",
        einsatzorte=einsatzorte,
        kategorien=kategorien,
        produkttypen=produkttypen,
        hersteller=hersteller,
        lieferanten=lieferanten,
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
        # we expect row to be a list of table values
        if not row or len(row) < 19:
            continue

        product_id = row[0]
        # Fetch current DB state for this product
        cur.execute("SELECT * FROM products WHERE id=?", (product_id,))
        existing = cur.fetchone()
        if not existing:
            continue

        # Only update if something actually changed
        current_values = tuple(existing[1:19])
        new_values = tuple(row[1:19])
        if current_values != new_values:
            cur.execute("""
                UPDATE products SET
                    code=?, gemeinde=?, einsatzort=?, kategorie=?, produkttyp=?, produktdetails=?, anzahl=?,
                    hersteller=?, lieferant=?, shop_link=?, preis_netto=?, preis_brutto=?, bezahlt=?,
                    bestellt_am=?, geliefert_am=?, uebergeben_am=?, projekt=?, bemerkungen=?, 
                    geaendert_von=?
                WHERE id=?
            """, (
                *new_values,
                current_user.username,
                product_id
            ))
            changed += 1

    conn.commit()
    conn.close()
    return jsonify({"message": f"{changed} Zeile(n) aktualisiert."})


@app.route("/delete_rows", methods=["POST"])
def delete_rows():
    data = request.get_json()
    ids = data.get("ids", [])
    if not ids:
        return jsonify({"message": "Keine IDs angegeben."})

    conn = database.get_connection()
    cur = conn.cursor()
    for pid in ids:
        cur.execute("DELETE FROM products WHERE id=?", (pid,))
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
        f"SELECT * FROM products WHERE id IN ({','.join(['?'] * len(ids))})",
        ids
    )
    rows = cur.fetchall()
    conn.close()

    # Create ZIP archive in memory
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as zipf:
        for p in rows:
            label_text = f"Land-lieben: {p[2]} - {p[17]}"
            filepath = label_printer.make_pdf_label(p[1], label_text)
            zipf.write(filepath, arcname=os.path.basename(filepath))
    zip_buffer.seek(0)

    # Send ZIP for download
    return send_file(
        zip_buffer,
        mimetype="application/zip",
        as_attachment=True,
        download_name="Etiketten_Landlieben.zip"
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
# Print – Generate barcode labels
# ---------------------------------------------------------
@app.route("/print", methods=["GET", "POST"])
def print_labels():
    if request.method == "POST":
        products = database.get_all_products()
        for p in products:
            label_text = f"Land-lieben: {p[2]} - {p[17]}"
            label_printer.make_pdf_label(p[1], label_text)
        flash("Etiketten wurden generiert. Ordner wurde geöffnet.", "success")
    return render_template("print.html")


# ---------------------------------------------------------
# Run local server
# ---------------------------------------------------------
if __name__ == "__main__":
    app.run(debug=True, port=9090)
