from config import supabase

def vendre_produit(reference,quantite_vendue,prix_vendu_carton,nom_client, return_msg=False):
    result = supabase.table("produits").select("*").eq("reference", reference).execute()
    produits = result.data  # c’est une liste de dicts

    if not produits:
        return "Produit non trouvé"  # ou message d'erreur

    produit = produits[0]  # prendre le premier élément

    
    if produit["quantite"]< quantite_vendue:
        return " Stock insuffisant "

    # Mise à jour du stock
    nouvelle_quantite = produit["quantite"]- quantite_vendue
    supabase.table("produits").update({"quantite": nouvelle_quantite}).eq("id",produit["id"]).execute()

    # Calcul
    total = quantite_vendue * prix_vendu_carton

     # Génération facture

    # Historique de vente
    supabase.table("ventes").insert({
        "produit_id": produit["id"],
        "reference": produit["reference"],     
        "quantite_vendue": quantite_vendue,
        "prix_vendu_carton": prix_vendu_carton,
        "nom_client": nom_client,
        "total": total,
    }).execute()

    return f"✔ Vente enregistrée ({quantite_vendue} x {reference})"


def supprimer_vente(vente_id):
    # 1️⃣ Récupérer la vente
    result = supabase.table("ventes").select("*").eq("id", vente_id).execute()
    ventes = result.data

    if not ventes:
        return "❌ Vente introuvable."

    vente = ventes[0]
    quantite = vente["quantite_vendue"]
    produit_id = vente["produit_id"]

    # 2️⃣ Récupérer le produit lié
    prod_result = supabase.table("produits").select("*").eq("id", produit_id).execute()
    produits = prod_result.data

    if not produits:
        return "❌ Produit lié introuvable (base incohérente)."

    produit = produits[0]

    # 3️⃣ Restaurer le stock
    nouvelle_quantite = produit["quantite"] + quantite
    supabase.table("produits").update({"quantite": nouvelle_quantite}).eq("id", produit_id).execute()

    # 4️⃣ Supprimer la vente
    supabase.table("ventes").delete().eq("id", vente_id).execute()

    return f"✔ Vente {vente_id} supprimée et stock restauré (+{quantite})."
   