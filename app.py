import streamlit as st
import pandas as pd
import os

from models.produit import afficher_produits, ajouter_produit  # Pour compatibilité, mais tu peux migrer entièrement vers supabase
from models.vente import vendre_produit
from config import supabase  # ton client Supabase
from postgrest.exceptions import APIError
from models.vente import supprimer_vente
from utils.facture import generer_facture




st.set_page_config(page_title="Gestion de Stock", page_icon="📦")
if "panier" not in st.session_state:
    st.session_state.panier = []

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
    if st.button("Ajouter au panier"):

        st.session_state.panier.append({
        "reference": produit["reference"],
        "nom": produit["nom"],
        "prix": prix_vendu_carton,
        "quantite": quantite_vendue,
        "total": prix_vendu_carton * quantite_vendue,
        "client": nom_client  
    })

        st.success("Produit ajouté à la facture ✅")

    if st.session_state.panier:

        st.subheader("🧾 Facture en cours")

        df_panier = pd.DataFrame(st.session_state.panier)
        st.dataframe(df_panier, width='stretch')

        total_facture = df_panier["total"].sum()

        st.write(f"### 💰 Total facture : {int(total_facture):,} FCFA")


    if st.session_state.panier:

        if st.button("✅ Valider la facture"):
           
            lignes_facture = []

            for item in st.session_state.panier:

                vendre_produit(
                    item["reference"],
                    item["quantite"],
                    item["prix"],
                    item["client"]   # <- plus sûr

                )
                
                lignes_facture.append({
                        "reference": item["reference"],
                        "quantite": item["quantite"],
                        "prix": item["prix"],
                        "total": item["total"]
                    })
            facture_path = generer_facture(
            lignes_facture,
            nom_client=st.session_state.panier[0]["client"],
            total=total_facture
)


            st.success("Facture enregistrée avec succès 🎉")
            with open(facture_path, "rb") as f:
                st.download_button(
                label="📄 Télécharger la facture",
                data=f,
                file_name=os.path.basename(facture_path),
                mime="application/pdf"
            )


            # vider le panier
            st.session_state.panier = []


#-----Historique des ventes-------------
elif onglet == "Historique":
    st.subheader("Historique des ventes")

    # 🔹 Récupérer toutes les ventes
    ventes = supabase.table("ventes").select("*").order("date_vente", desc=True).execute().data
    df = pd.DataFrame(ventes)

    if df.empty:
        st.info("Aucune vente enregistrée.")
        st.stop()

    # Nettoyage et conversions
    df['reference'] = df['reference'].fillna('N/A')
    df['nom_client'] = df['nom_client'].fillna('N/A')
    df['total'] = df['total'].astype(float)
    df['prix_vendu_carton'] = df['prix_vendu_carton'].astype(float)
    df['facture_path'] = df['facture_path'].fillna("").astype(str)
    df['date_vente_dt'] = pd.to_datetime(df['date_vente'])
    df['date_vente'] = df['date_vente_dt'].dt.strftime("%d/%m/%Y %H:%M")

    # 🔹 Garder uniquement les ventes validées (avec PDF)
    df_valides = df[df['facture_path'] != ""]

    if df_valides.empty:
        st.info("Aucune facture validée pour l'instant.")
        st.stop()

    # 🔹 Grouper par facture_path
    factures = df_valides.groupby("facture_path", sort=False)

    st.markdown("### 🧾 Factures validées")

    for facture_path, groupe in factures:
        client = groupe["nom_client"].iloc[0]
        date = groupe["date_vente"].iloc[0]
        total_facture = groupe["total"].sum()

        with st.expander(f"🧾 Client : {client} | 💰 {int(total_facture):,} FCFA | 📅 {date}"):

            # 🔹 Tableau des produits pour cette facture
            display_df = groupe[[
                "reference",
                "quantite_vendue",
                "prix_vendu_carton",
                "total"
            ]].copy()

            display_df["prix_vendu_carton"] = display_df["prix_vendu_carton"].apply(lambda x: f"{int(x):,} FCFA")
            display_df["total"] = display_df["total"].apply(lambda x: f"{int(x):,} FCFA")

            st.dataframe(display_df, width='stretch')

            # 🔹 Bouton téléchargement PDF (exactement comme dans Enregistrer une vente)
            if os.path.exists(facture_path):
                with open(facture_path, "rb") as f:
                    st.download_button(
                        "📄 Télécharger la facture",
                        f,
                        file_name=os.path.basename(facture_path),
                        mime="application/pdf",
                        key=facture_path
                    )
            else:
                st.warning("Facture introuvable sur le serveur.")




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
