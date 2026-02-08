import datetime
import os
from reportlab.pdfgen import canvas

FACTURE_DIR = "factures"
os.makedirs(FACTURE_DIR, exist_ok=True)


def generer_facture(lignes, nom_client, total):

    date_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"facture_{nom_client}_{date_str}.pdf"
    filepath = os.path.join(FACTURE_DIR, filename)

    c = canvas.Canvas(filepath)
    c.setFont("Helvetica", 14)

    y = 750

    c.drawString(100, y, "FACTURE")
    y -= 40

    c.drawString(100, y, f"Client : {nom_client}")
    y -= 30

    c.drawString(100, y, f"Date : {datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    y -= 40

    c.drawString(100, y, "Produits :")
    y -= 20

    c.setFont("Helvetica", 11)

    for ligne in lignes:

        texte = f"{ligne['reference']} | Qté: {ligne['quantite']} | Prix: {ligne['prix']} CFA | Total: {ligne['total']} CFA"

        c.drawString(100, y, texte)
        y -= 20

        # évite d'écrire hors page
        if y < 100:
            c.showPage()
            c.setFont("Helvetica", 11)
            y = 750

    y -= 20
    c.setFont("Helvetica-Bold", 12)
    c.drawString(100, y, f"TOTAL FACTURE : {total} CFA")

    c.save()

    return filepath
