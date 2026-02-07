import streamlit as st
import pandas as pd
import os
from models.produit import afficher_produits, ajouter_produit  # Pour compatibilité, mais tu peux migrer entièrement vers supabase
from models.vente import vendre_produit
from config import supabase  # ton client Supabase
from postgrest.exceptions import APIError
from models.vente import supprimer_vente



st.set_page_config(page_title="Gestion de Stock", page_icon="📦")

st.title("📦 Application de gestion de stock")
st.write("Interface simple pour gérer les produits et enregistrer les ventes")

#------------Onglets---------
onglet = st.sidebar.radio("Navigation", ["Liste des produits", "Ajouter un produit","Enregistrer une vente","Historique","Supprimer une vente","Import Produits"])

#--------Liste des produits----
if onglet == "Liste des produits":
    st.subheader("Liste actuelle des produits")
    # Récupérer les produits depuis Supabase
    data = pd.DataFrame(supabase.table("produits").select("*").execute().data)
    st.dataframe(data, width='stretch')

#-----Ajouter un produit-------
elif onglet == "Ajouter un produit":
    st.subheader("Ajouter un produit")

    reference = st.text_input("Référence du produit")
    nom = st.text_input("Nom du produit")
    categorie = st.text_input("Catégorie")
    prix = st.number_input("Prix carton", min_value=0.0)
    quantite = st.number_input("Quantité", min_value=0)
    
    if st.button("Ajouter"):
        if nom.strip() == "":
            st.error("Veuillez entrer un nom")
        else:
            try:
                supabase.table("produits").insert({
                "reference": reference,
                "nom": nom,
                "categorie": categorie,
                "prix_unitaire": prix,
                "quantite": quantite
            }).execute()
                st.success(f"Produit '{reference}' ajouté!")
            except APIError:
                st.error(f"❌ Impossible d’ajouter : le produit avec la référence '{reference}' existe déjà.")

#-----Vente--------------

elif onglet == "Enregistrer une vente":
    st.subheader("Vendre un produit")

    # 🔹 récupérer produits
    produits = supabase.table("produits").select("*").execute().data
    df = pd.DataFrame(produits)

    if df.empty:
        st.warning("Aucun produit disponible.")
        st.stop()

    # 🔥 garder uniquement ceux en stock
    df = df[df["quantite"] > 0]

    if df.empty:
        st.warning("Tous les produits sont en rupture de stock.")
        st.stop()

    # 🔥 liste déroulante propre
    produit_selectionne = st.selectbox(
        "Choisir un produit",
        df["reference"]
    )

    # récupérer la ligne du produit
    produit = df[df["reference"] == produit_selectionne].iloc[0]

    # affichage infos (UX ++)
    st.write(f"📦 Stock disponible : **{produit['quantite']}**")
    st.write(f"💰 Prix recommandé : **{int(produit['prix_unitaire']):,} FCFA**")

    quantite_vendue = st.number_input(
        "Quantité vendue",
        min_value=1,
        max_value=int(produit["quantite"])  # 🔥 empêche de vendre trop
    )

    prix_vendu_carton = st.number_input(
        "Prix vendu (carton)",
        value=float(produit["prix_unitaire"])  # 🔥 auto-rempli
    )

    nom_client = st.text_input("Nom du client")

    if st.button("Valider la vente"):

        result = vendre_produit(
            produit_selectionne,
            quantite_vendue,
            prix_vendu_carton,
            nom_client,
            return_msg=True
        )

        if isinstance(result, dict):
            st.success(result["message"])

            if "facture_path" in result:
                with open(result["facture_path"], "rb") as f:
                    st.download_button(
                        label="Télécharger la facture",
                        data=f,
                        file_name=os.path.basename(result["facture_path"]),
                        mime="application/pdf"
                    )
        else:
            st.error(result)
