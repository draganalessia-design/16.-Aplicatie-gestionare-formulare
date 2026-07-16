import sys

TIPURI_VALIDE = {"text", "email", "numar", "data", "select", "textarea", "checkbox", "parola"}


def parseaza_formular(cale_fisier):

    with open(cale_fisier, encoding="utf-8") as f:
        continut = f.read()

    # blocurile sunt separate prin linie goala
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
            # e un bloc care descrie un camp din formular
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
            # e blocul de antet (titlu / tabel)
            if "titlu" in perechi:
                formular["titlu"] = perechi["titlu"]
            if "tabel" in perechi:
                formular["tabel"] = perechi["tabel"]

    if not formular["campuri"]:
        raise ValueError("Fisierul de formular nu contine niciun camp ('camp: ...').")

    return formular

CSS = """
body { font-family: Arial, sans-serif; background:#f4f6f8; margin:0; padding:40px 0; }
.card { max-width:600px; margin:0 auto; background:#fff; padding:30px 40px;
        border-radius:10px; box-shadow:0 2px 10px rgba(0,0,0,0.08); }
h1 { font-size:22px; color:#222; margin-bottom:25px; }
label { display:block; margin-top:16px; font-weight:bold; color:#333; font-size:14px; }
input, select, textarea {
    width:100%; padding:8px 10px; margin-top:6px; border:1px solid #ccc;
    border-radius:6px; font-size:14px; box-sizing:border-box;
}
textarea { min-height:80px; }
.checkbox-row { margin-top:16px; display:flex; align-items:center; gap:8px; }
.checkbox-row label { margin:0; }
button { margin-top:26px; padding:10px 22px; background:#2563eb; color:#fff;
         border:none; border-radius:6px; font-size:15px; cursor:pointer; }
.req { color:#dc2626; }
"""


def randeaza_camp(camp):
    """Genereaza codul HTML pentru un singur camp din formular."""
    nume = camp["nume"]
    eticheta = camp["eticheta"]
    obligatoriu_html = " required" if camp["obligatoriu"] else ""
    steluta = ' <span class="req">*</span>' if camp["obligatoriu"] else ""

    if camp["tip"] in ("text", "email", "parola"):
        tip_html = {"text": "text", "email": "email", "parola": "password"}[camp["tip"]]
        return f'<label>{eticheta}{steluta}</label><input type="{tip_html}" name="{nume}"{obligatoriu_html}>'

    if camp["tip"] == "numar":
        return f'<label>{eticheta}{steluta}</label><input type="number" name="{nume}"{obligatoriu_html}>'

    if camp["tip"] == "data":
        return f'<label>{eticheta}{steluta}</label><input type="date" name="{nume}"{obligatoriu_html}>'

    if camp["tip"] == "textarea":
        return f'<label>{eticheta}{steluta}</label><textarea name="{nume}"{obligatoriu_html}></textarea>'

    if camp["tip"] == "select":
        optiuni_html = "".join(f'<option value="{o}">{o}</option>' for o in camp["optiuni"])
        return f'<label>{eticheta}{steluta}</label><select name="{nume}"{obligatoriu_html}>{optiuni_html}</select>'

    if camp["tip"] == "checkbox":
        return (f'<div class="checkbox-row"><input type="checkbox" name="{nume}" value="1">'
                f'<label>{eticheta}{steluta}</label></div>')

    return ""


def genereaza_pagina_formular(formular):
    """Asambleaza pagina HTML completa, pornind de la dictionarul formularului."""
    campuri_html = "".join(randeaza_camp(camp) for camp in formular["campuri"])

    return f"""<!DOCTYPE html>
<html lang="ro">
<head>
<meta charset="UTF-8">
<title>{formular['titlu']}</title>
<style>{CSS}</style>
</head>
<body>
  <div class="card">
    <h1>{formular['titlu']}</h1>
    <form>
      {campuri_html}
      <button type="submit">Trimite</button>
    </form>
  </div>
</body>
</html>"""


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Utilizare: python3 app.py <fisier_formular.txt>")
        sys.exit(1)

    # Pasul 1: Parsam formularul 
    formular = parseaza_formular(sys.argv[1])
    
    # Afisam detalii in consola pentru verificare
    print("Titlu formular:", formular["titlu"])
    print("Tabel in baza de date:", formular["tabel"])
    print("Numar campuri:", len(formular["campuri"]))
    print()

    for camp in formular["campuri"]:
        print(f"- {camp['nume']:15s} | tip={camp['tip']:10s} | obligatoriu={camp['obligatoriu']} | eticheta='{camp['eticheta']}'")
        if camp["optiuni"]:
            print(f"    optiuni: {camp['optiuni']}")
    print()


    # Pasul 2: Generam pagina HTML din descriere 
    html = genereaza_pagina_formular(formular)


    # Pasul 3: Salvam codul HTML generat intr-un fisier local
    with open("pagina_generata.html", "w", encoding="utf-8") as f:
        f.write(html)

    print("Pagina a fost generata cu succes: pagina_generata.html")
    print("Poti deschide manual fisierul in browser pentru a vedea cum arata! Fisierul HTML se afla in folderul curent!")