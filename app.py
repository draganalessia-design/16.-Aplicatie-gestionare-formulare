import sys
import sqlite3
import os
from datetime import datetime
from flask import Flask, request, redirect, url_for, send_file, abort

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm



TIPURI_VALIDE = {"text", "email", "numar", "data", "select", "textarea", "checkbox", "parola"}


def parseaza_formular(cale_fisier):
    """Citeste fisierul text si intoarce un dict cu titlu, tabel si lista de campuri."""
    with open(cale_fisier, encoding="utf-8") as f:
        continut = f.read()

    blocuri = [b.strip() for b in continut.split("\n\n") if b.strip()]

    formular = {"titlu": "Formular", "tabel": "date_formular", "campuri": []}

    for bloc in blocuri:
        perechi = {}
        for linie in bloc.splitlines():
            linie = linie.strip()
            if not linie or ":" not in linie:
                continue
            cheie, valoare = linie.split(":", 1)
            perechi[cheie.strip().lower()] = valoare.strip()

        if "camp" in perechi:
            camp = {
                "nume": perechi["camp"],
                "eticheta": perechi.get("eticheta", perechi["camp"]),
                "tip": perechi.get("tip", "text"),
                "obligatoriu": perechi.get("obligatoriu", "nu").lower() == "da",
                "optiuni": [o.strip() for o in perechi.get("optiuni", "").split(",") if o.strip()],
            }
            if camp["tip"] not in TIPURI_VALIDE:
                raise ValueError(f"Tip necunoscut '{camp['tip']}' pentru campul '{camp['nume']}'")
            formular["campuri"].append(camp)
        else:
            # bloc de antet (titlu / tabel)
            if "titlu" in perechi:
                formular["titlu"] = perechi["titlu"]
            if "tabel" in perechi:
                formular["tabel"] = perechi["tabel"]

    if not formular["campuri"]:
        raise ValueError("Fisierul de formular nu contine niciun camp ('camp: ...').")

    return formular


if len(sys.argv) < 2:
    print("Utilizare: python app.py <fisier_formular.txt>")
    sys.exit(1)

CALE_SPEC = sys.argv[1]
FORMULAR = parseaza_formular(CALE_SPEC)
NUME_TABEL = FORMULAR["tabel"]
CALE_DB = os.path.splitext(os.path.basename(CALE_SPEC))[0] + ".db"



TIP_SQL = {
    "text": "TEXT",
    "email": "TEXT",
    "parola": "TEXT",
    "numar": "INTEGER",
    "data": "TEXT",
    "select": "TEXT",
    "textarea": "TEXT",
    "checkbox": "INTEGER",
}


def get_conn():
    conn = sqlite3.connect(CALE_DB)
    conn.row_factory = sqlite3.Row
    return conn


def creeaza_tabel():
    coloane = ["id INTEGER PRIMARY KEY AUTOINCREMENT"]
    for camp in FORMULAR["campuri"]:
        coloane.append(f'"{camp["nume"]}" {TIP_SQL[camp["tip"]]}')
    coloane.append("data_completare TEXT")
    sql = f'CREATE TABLE IF NOT EXISTS "{NUME_TABEL}" ({", ".join(coloane)})'
    conn = get_conn()
    conn.execute(sql)
    conn.commit()
    conn.close()


creeaza_tabel()



CSS = """
body { font-family: Arial, sans-serif; background:#f4f6f8; margin:0; padding:40px 0; }
.card { max-width:600px; margin:0 auto; background:#fff; padding:30px 40px;
        border-radius:10px; box-shadow:0 2px 10px rgba(0,0,0,0.08); }
h1 { font-size:22px; color:#222; margin-bottom:25px; }
label { display:block; margin-top:16px; font-weight:bold; color:#333; font-size:14px; }
input[type=text], input[type=email], input[type=number], input[type=date],
input[type=password], select, textarea {
    width:100%; padding:8px 10px; margin-top:6px; border:1px solid #ccc;
    border-radius:6px; font-size:14px; box-sizing:border-box;
}
textarea { min-height:80px; }
.checkbox-row { margin-top:16px; display:flex; align-items:center; gap:8px; }
.checkbox-row label { margin:0; }
button { margin-top:26px; padding:10px 22px; background:#2563eb; color:#fff;
         border:none; border-radius:6px; font-size:15px; cursor:pointer; }
button:hover { background:#1d4ed8; }
.req { color:#dc2626; }
.top-links { max-width:600px; margin:0 auto 14px auto; font-size:14px; }
.top-links a { color:#2563eb; text-decoration:none; margin-right:14px; }
table { max-width:800px; margin:0 auto; background:#fff; border-collapse:collapse; width:100%; }
th, td { padding:8px 12px; border-bottom:1px solid #eee; font-size:14px; text-align:left; }
th { background:#f0f2f5; }
"""


def randeaza_camp(camp, valoare=None):
    """Genereaza codul HTML pentru un singur camp, precompletat daca valoarea este data."""
    nume = camp["nume"]
    eticheta = camp["eticheta"]
    obligatoriu_html = " required" if camp["obligatoriu"] else ""
    steluta = ' <span class="req">*</span>' if camp["obligatoriu"] else ""
    val = "" if valoare is None else str(valoare)

    if camp["tip"] in ("text", "email", "parola"):
        tip_html = {"text": "text", "email": "email", "parola": "password"}[camp["tip"]]
        return (f'<label>{eticheta}{steluta}</label>'
                f'<input type="{tip_html}" name="{nume}" value="{val}"{obligatoriu_html}>')

    if camp["tip"] == "numar":
        return (f'<label>{eticheta}{steluta}</label>'
                f'<input type="number" name="{nume}" value="{val}"{obligatoriu_html}>')

    if camp["tip"] == "data":
        return (f'<label>{eticheta}{steluta}</label>'
                f'<input type="date" name="{nume}" value="{val}"{obligatoriu_html}>')

    if camp["tip"] == "textarea":
        return (f'<label>{eticheta}{steluta}</label>'
                f'<textarea name="{nume}"{obligatoriu_html}>{val}</textarea>')

    if camp["tip"] == "select":
        optiuni_html = ""
        for opt in camp["optiuni"]:
            sel = " selected" if opt == val else ""
            optiuni_html += f'<option value="{opt}"{sel}>{opt}</option>'
        return (f'<label>{eticheta}{steluta}</label>'
                f'<select name="{nume}"{obligatoriu_html}>{optiuni_html}</select>')

    if camp["tip"] == "checkbox":
        checked = " checked" if val in ("1", "True", "true", True) else ""
        return (f'<div class="checkbox-row"><input type="checkbox" name="{nume}" '
                f'value="1"{checked}><label>{eticheta}{steluta}</label></div>')

    return ""


def genereaza_pagina_formular(valori=None, id_inregistrare=None, mesaj=None):
    """valori: dict cu nume_camp -> valoare, folosit pentru precompletare (mod editare)."""
    valori = valori or {}
    campuri_html = "".join(
        randeaza_camp(camp, valori.get(camp["nume"])) for camp in FORMULAR["campuri"]
    )

    actiune = url_for("actualizeaza", id_inregistrare=id_inregistrare) if id_inregistrare else url_for("trimite")
    text_buton = "Actualizeaza" if id_inregistrare else "Trimite"
    mesaj_html = f'<p style="color:green">{mesaj}</p>' if mesaj else ""

    return f"""<!DOCTYPE html>
<html lang="ro">
<head>
<meta charset="UTF-8">
<title>{FORMULAR['titlu']}</title>
<style>{CSS}</style>
</head>
<body>
  <div class="top-links">
    <a href="{url_for('index')}">Formular nou</a>
    <a href="{url_for('lista')}">Vezi toate inregistrarile</a>
  </div>
  <div class="card">
    <h1>{FORMULAR['titlu']}</h1>
    {mesaj_html}
    <form method="post" action="{actiune}">
      {campuri_html}
      <button type="submit">{text_buton}</button>
    </form>
  </div>
</body>
</html>"""


def genereaza_pagina_lista(inregistrari):
    randuri = ""
    for r in inregistrari:
        celule = "".join(f"<td>{r[camp['nume']]}</td>" for camp in FORMULAR["campuri"])
        randuri += (
            f"<tr><td>{r['id']}</td>{celule}"
            f"<td><a href='{url_for('editeaza', id_inregistrare=r['id'])}'>editeaza</a> | "
            f"<a href='{url_for('pdf', id_inregistrare=r['id'])}'>PDF</a></td></tr>"
        )
    antete = "".join(f"<th>{c['eticheta']}</th>" for c in FORMULAR["campuri"])
    return f"""<!DOCTYPE html>
<html lang="ro">
<head><meta charset="UTF-8"><title>Inregistrari</title><style>{CSS}</style></head>
<body>
  <div class="top-links"><a href="{url_for('index')}">Formular nou</a></div>
  <table>
    <tr><th>ID</th>{antete}<th>Actiuni</th></tr>
    {randuri}
  </table>
</body>
</html>"""



def genereaza_pdf(id_inregistrare, camp_valori, cale_iesire):
    c = canvas.Canvas(cale_iesire, pagesize=A4)
    latime, inaltime = A4
    x = 2 * cm
    y = inaltime - 2.5 * cm

    c.setFont("Helvetica-Bold", 16)
    c.drawString(x, y, FORMULAR["titlu"])
    y -= 0.9 * cm

    c.setFont("Helvetica", 10)
    c.drawString(x, y, f"Inregistrare #{id_inregistrare}")
    y -= 1.0 * cm

    c.setFont("Helvetica", 12)
    for camp in FORMULAR["campuri"]:
        valoare = camp_valori.get(camp["nume"])
        if camp["tip"] == "checkbox":
            valoare = "Da" if str(valoare) in ("1", "True", "true") else "Nu"
        if valoare is None:
            valoare = ""
        c.setFont("Helvetica-Bold", 12)
        c.drawString(x, y, f"{camp['eticheta']}:")
        c.setFont("Helvetica", 12)
        c.drawString(x + 9 * cm, y, str(valoare))
        y -= 0.8 * cm
        if y < 2 * cm:
            c.showPage()
            y = inaltime - 2.5 * cm
            c.setFont("Helvetica", 12)

    c.save()




app = Flask(__name__)


@app.route("/")
def index():
    return genereaza_pagina_formular()


@app.route("/trimite", methods=["POST"])
def trimite():
    valori = _citeste_valori_din_request()
    coloane = ", ".join(f'"{c["nume"]}"' for c in FORMULAR["campuri"]) + ", data_completare"
    semne = ", ".join("?" for _ in FORMULAR["campuri"]) + ", ?"
    valori_sql = [valori[c["nume"]] for c in FORMULAR["campuri"]] + [datetime.now().isoformat(timespec="seconds")]

    conn = get_conn()
    conn.execute(f'INSERT INTO "{NUME_TABEL}" ({coloane}) VALUES ({semne})', valori_sql)
    conn.commit()
    conn.close()
    return genereaza_pagina_formular(mesaj="Datele au fost salvate cu succes.")


@app.route("/editeaza/<int:id_inregistrare>")
def editeaza(id_inregistrare):
    conn = get_conn()
    rand = conn.execute(f'SELECT * FROM "{NUME_TABEL}" WHERE id = ?', (id_inregistrare,)).fetchone()
    conn.close()
    if rand is None:
        abort(404)
    valori = {c["nume"]: rand[c["nume"]] for c in FORMULAR["campuri"]}
    return genereaza_pagina_formular(valori=valori, id_inregistrare=id_inregistrare)


@app.route("/actualizeaza/<int:id_inregistrare>", methods=["POST"])
def actualizeaza(id_inregistrare):
    valori = _citeste_valori_din_request()
    set_clauza = ", ".join(f'"{c["nume"]}" = ?' for c in FORMULAR["campuri"])
    valori_sql = [valori[c["nume"]] for c in FORMULAR["campuri"]] + [id_inregistrare]

    conn = get_conn()
    conn.execute(f'UPDATE "{NUME_TABEL}" SET {set_clauza} WHERE id = ?', valori_sql)
    conn.commit()
    conn.close()
    return redirect(url_for("editeaza", id_inregistrare=id_inregistrare))


@app.route("/lista")
def lista():
    conn = get_conn()
    inregistrari = conn.execute(f'SELECT * FROM "{NUME_TABEL}" ORDER BY id DESC').fetchall()
    conn.close()
    return genereaza_pagina_lista(inregistrari)


@app.route("/pdf/<int:id_inregistrare>")
def pdf(id_inregistrare):
    conn = get_conn()
    rand = conn.execute(f'SELECT * FROM "{NUME_TABEL}" WHERE id = ?', (id_inregistrare,)).fetchone()
    conn.close()
    if rand is None:
        abort(404)
    valori = {c["nume"]: rand[c["nume"]] for c in FORMULAR["campuri"]}
    cale_pdf = f"/tmp/inregistrare_{id_inregistrare}.pdf"
    genereaza_pdf(id_inregistrare, valori, cale_pdf)
    return send_file(cale_pdf, as_attachment=True, download_name=f"inregistrare_{id_inregistrare}.pdf")


def _citeste_valori_din_request():
    valori = {}
    for camp in FORMULAR["campuri"]:
        if camp["tip"] == "checkbox":
            valori[camp["nume"]] = 1 if request.form.get(camp["nume"]) else 0
        else:
            valori[camp["nume"]] = request.form.get(camp["nume"], "")
    return valori


if __name__ == "__main__":
    print(f"Formular incarcat: '{FORMULAR['titlu']}' -> tabel '{NUME_TABEL}' in {CALE_DB}")
    print("Deschide http://127.0.0.1:5000/ in browser.")
    app.run(debug=True)
