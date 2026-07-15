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


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Utilizare: python3 app.py <fisier_formular.txt>")
        sys.exit(1)

    formular = parseaza_formular(sys.argv[1])

    # afisam ce am citit, ca sa verificam ca parsarea e corecta
    print("Titlu formular:", formular["titlu"])
    print("Tabel in baza de date:", formular["tabel"])
    print("Numar campuri:", len(formular["campuri"]))
    print()
    for camp in formular["campuri"]:
        print(f"- {camp['nume']:15s} | tip={camp['tip']:10s} | obligatoriu={camp['obligatoriu']} | eticheta='{camp['eticheta']}'")
        if camp["optiuni"]:
            print(f"    optiuni: {camp['optiuni']}")
