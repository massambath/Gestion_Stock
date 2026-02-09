from config import supabase

def vendre_produit(reference, quantite_vendue, prix_vendu_carton, nom_client, facture_path):

    result = supabase.table("produits").select("*").eq("reference", reference).execute()
    produits = result.data

    if not produits:
        return "Produit non trouvé"

    produit = produits[0]

    if produit["quantite"] < quantite_vendue:
        return "Stock insuffisant"

    # 🔥 Mise à jour du stock
    nouvelle_quantite = produit["quantite"] - quantite_vendue
    supabase.table("produits")\
        .update({"quantite": nouvelle_quantite})\
        .eq("id", produit["id"])\
        .execute()

    total = quantite_vendue * prix_vendu_carton

    # 🔥 INSERT AVEC FACTURE
    supabase.table("ventes").insert({
        "produit_id": produit["id"],
        "reference": produit["reference"],
        "quantite_vendue": quantite_vendue,
        "prix_vendu_carton": prix_vendu_carton,
        "nom_client": nom_client,
        "total": total,
        "facture_path": facture_path   # <<<<<<<< CRUCIAL
    }).execute()

    return f"✔ Vente enregistrée ({quantite_vendue} x {reference})"
