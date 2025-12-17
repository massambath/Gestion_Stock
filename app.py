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

    reference = st.text_input("Référence du produit vendu")
    quantite_vendue = st.number_input("Quantité vendue", min_value=1)
    prix_vendu_carton = st.number_input("Prix vendu (carton)", min_value=0.0)
    nom_client = st.text_input("Nom du client")

    if st.button("Valider la vente"):
        result = vendre_produit(reference, quantite_vendue, prix_vendu_carton, nom_client, return_msg=True)
        
        if isinstance(result, dict):
            st.success(result["message"])
        else:
            st.error(result)

        # Bouton de téléchargement facture si générée
        if "facture_path" in result:
            with open(result["facture_path"], "rb") as f:
                st.download_button(
                    label ="Télécharger la facture",
                    data=f,
                    file_name=os.path.basename(result["facture_path"]),
                    mime="application/pdf"
                )

#-----Historique des ventes-------------
elif onglet == "Historique":
    st.subheader("Historique des ventes")
    
    ventes = supabase.table("ventes").select("*").order("date_vente", desc=True).execute().data
    df = pd.DataFrame(ventes)

    if df.empty:
        st.info("Aucune vente enregistrée.")
    else:
        # Nettoyage et formatage
        df['reference'] = df['reference'].fillna('N/A')
        df['nom_client'] = df['nom_client'].fillna('N/A')
        df['prix_vendu_carton'] = df['prix_vendu_carton'].apply(lambda x: f"{int(x):,} FCFA" if x else "0 FCFA")
        df['total'] = df['total'].apply(lambda x: f"{int(x):,} FCFA" if x else "0 FCFA")
        df['date_vente'] = pd.to_datetime(df['date_vente']).dt.strftime("%d/%m/%Y %H:%M")

        # Affichage ligne par ligne avec colonnes pour “tableau”
        st.markdown("### Tableau des ventes")
        header_cols = st.columns([1,1,1,1,1,1,1,1])
        headers = ["ID", "Réf", "Client", "Qté", "Prix", "Total", "Date", "Facture", "Supprimer"]
        for col, h in zip(header_cols, headers):
            col.markdown(f"**{h}**")

        for index, row in df.iterrows():
            cols = st.columns([0.5,1,1,1,1,1,1,1,1])  # ID plus petit
            cols[0].write(row['id'])  # Affichage ID pour référence
            cols[1].write(row['reference'])
            cols[2].write(row['nom_client'])
            cols[3].write(row['quantite_vendue'])
            cols[4].write(row['prix_vendu_carton'])
            cols[5].write(row['total'])
            cols[6].write(row['date_vente'])
            
            # Bouton facture
            facture_path = row.get('facture_path')
            if facture_path and os.path.exists(facture_path):
                with open(facture_path, 'rb') as f:
                    cols[7].download_button(
                        label="Télécharger",
                        data=f,
                        file_name=os.path.basename(facture_path),
                        mime="application/pdf",
                        key=f"download_{index}"
                    )
            else:
                cols[7].write("N/A")

#------Supprimer Ventes----------------------#
elif onglet == "Supprimer une vente":
    st.subheader("Supprimer une vente")
    
    # Récupération des ventes
    ventes = supabase.table("ventes").select("*").order("date_vente", desc=True).execute().data
    df = pd.DataFrame(ventes)
    
    if df.empty:
        st.info("Aucune vente à supprimer.")
    else:
        # Selectbox pour choisir la vente
        vente_a_supprimer = st.selectbox(
            "Sélectionner la vente à supprimer",
            df.apply(lambda row: f"{row['id']} | {row['reference']} | {row['nom_client']} | Qté: {row['quantite_vendue']}", axis=1),
            key="vente_delete"
        )

        # Bouton Supprimer
        if st.button("Supprimer la vente sélectionnée"):
            vente_id = int(vente_a_supprimer.split(" | ")[0])
            from models.vente import supprimer_vente
            msg = supprimer_vente(vente_id)
            st.success(msg)

            # Recharger les ventes après suppression
            ventes = supabase.table("ventes").select("*").order("date_vente", desc=True).execute().data
            df = pd.DataFrame(ventes)


        # 🔹 Nouvelle version sans experimental_rerun
        # On peut juste redessiner le selectbox et le message
        if df.empty:
            st.info("Toutes les ventes ont été supprimées.")
        else:
            st.write("Sélectionnez une vente pour la supprimer ci-dessus.")

#---------------Importer Produits----------------------#
elif onglet == "Import Produits":
    st.subheader("Importer des produits depuis Excel")

    fichier = st.file_uploader(
        "Choisir le fichier Excel (.xlsx)",
        type=["xlsx"]
    )

    if fichier:
        df = pd.read_excel(fichier)

        # NORMALISATION
        df.columns = df.columns.str.strip().str.lower()

        st.write("Aperçu du fichier :")
        st.dataframe(df)

        colonnes_requises = [
            "reference", "nom", "categorie",
            "prix_unitaire", "quantite"
        ]

        if not all(col in df.columns for col in colonnes_requises):
            st.error(f"❌ Colonnes attendues : {colonnes_requises}")
            st.warning(f"Colonnes trouvées : {list(df.columns)}")
        else:
            if st.button("Importer dans la base"):
                try:
                    data = df[colonnes_requises].to_dict(orient="records")
                    supabase.table("produits").insert(data).execute()
                    st.success(f"✅ {len(data)} produits importés avec succès")
                    st.experimental_rerun()

                except Exception as e:
                    st.error(f"Erreur lors de l'import : {e}")
