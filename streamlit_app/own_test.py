import streamlit as st
from PIL import Image, ImageOps
import tensorflow as tf
import keras
import os
import numpy as np
import pandas as pd
import time
import cv2
os.environ["KERAS_BACKEND"] = "tensorflow"

from custom_functions import make_gradcam_heatmap, save_and_display_gradcam
from keras.layers import Conv2D
from tensorflow.keras.preprocessing.image import img_to_array, array_to_img
from keras.models import load_model

#modele prédiction COVID
model_densenet = tf.keras.models.load_model(r"C:\Users\kiri_\Downloads\DenseNet201_finetuned_0_95_20epochs.h5")
model_vgg = tf.keras.models.load_model(r"C:\Users\kiri_\Downloads\VGG16_finetuned.h5")
#modèle de tri
model_tri = tf.keras.models.load_model(r"C:\Users\kiri_\Downloads\filtermodel.h5")
model = None

def show_test():

    # Style des onglets
    st.markdown("""
        <style>
            .stTabs [data-baseweb="tab-list"] {
                display: flex;
                gap: 10px;
            }

            .stTabs [data-baseweb="tab"] {
                padding: 10px 15px;
                border: 1px solid transparent;
                border-radius: 5px 5px 0 0;
                background-color: transparent;
                cursor: pointer;
                transition: all 0.3s ease;
            }

            .stTabs [data-baseweb="tab"]:hover {
                background-color: #8f8d9b;
            }

            .stTabs [aria-selected="true"] {
                background-color:  #57546a;
                border-color: #ccc;
                border-bottom-color: transparent;
            }
        </style>""", unsafe_allow_html = True)

    tab1, tab2, tab3 = st.tabs(["👀 Analyse de la GRAD-CAM", "🚀 Réaliser des prédictions", "⚖️ Qualités et limites"])

    with tab1:
        st.header("Analyse de la GRAD-CAM")

        col1, col2 = st.columns([0.6, 0.4])

        with col1:
            st.markdown('''
            Le GRAD-CAM est une technique de visualisation : elle est utile pour comprendre quelles parties d'une image donnée ont conduit un réseau de neurones convolutifs à sa décision finale de classification.

            Elle est utile pour déboguer le processus de décision d'un algorithme, en particulier dans le cas d'une erreur de classification.

            Cette technique provient d'une catégorie plus générale de procédés appelée visualisation de __Class Activation Map__ (CAM).

            Elle consiste à produire des heatmaps représentant les classes d'activation sur les images d'entrée. Une __class activation heatmap__ est associée à une classe de sortie spécifique.

            Ces classes sont calculées pour chaque pixel d'une image d'entrée, indiquant l'importance de chaque pixel par rapport à la classe considérée.

            Par exemple, si une image est utilisée dans un convnet chiens/chats, la visualisation CAM permet de générer une carte thermique pour la classe « chat », indiquant à quel point les différentes parties de l'image ressemblent à un chat, et également une carte thermique pour la classe « chien », indiquant à quel point les parties de l'image ressemblent à un chien.
                        ''')

        with col2:
            gradcam = Image.open('images\illustration_gradcam.jpeg')
            st.image(gradcam, use_column_width = True, caption = "Illustration de la feature-map sur une image de chien")

    with tab2:
        st.header("Réaliser des prédictions")
        # Configuration initiale de l'état de session
        if 'model_selected' not in st.session_state:
            st.session_state.model_selected = None
        if 'model_loaded' not in st.session_state:
            st.session_state.model_loaded = None

        col1, col2, col3 = st.columns([0.3, 0.4, 0.3])

        with col1:
            st.session_state.model_selected = st.selectbox(
                "Quel modèle utiliser ?",
                ("DenseNet201", "VGG16"),
                index=None,
                placeholder="Choisissez un modèle..."
            )
            if st.session_state.model_selected == "DenseNet201":
                st.write("Modèle le plus performant, mais aussi le plus lourd.")
                st.session_state.model_loaded = 'DenseNet201'
            elif st.session_state.model_selected == "VGG16":
                st.write("Modèle le plus équilibré.")
                st.session_state.model_loaded = 'VGG16'

        with col2:
            if st.session_state.model_selected == "DenseNet201" and st.session_state.model_loaded == 'DenseNet201':
                with st.spinner('Chargement du modèle DenseNet201...'):
                    model = model_densenet
                    st.success('👏 Modèle DenseNet201 chargé et prêt à prédire !')
            elif st.session_state.model_selected == "VGG16" and st.session_state.model_loaded == 'VGG16':
                with st.spinner('Chargement du modèle VGG16...'):
                    model = model_vgg
                    st.success('👏 Modèle VGG16 chargé et prêt à prédire !')

        with col3:
            if st.button('Réinitialiser le modèle', type = 'primary'):
                keys_to_delete = ['model_selected', 'model_loaded', 'file_uploaded']
                for key in keys_to_delete:
                    if key in st.session_state:
                        del st.session_state[key]
                        st.experimental_rerun()

        st.header("", divider = 'gray')

        col1, col2 = st.columns([0.6, 0.4])

        with col1:
            file_container = st.empty()
            uploaded_file = file_container.file_uploader("", type=['png', 'jpg', 'jpeg'])

        if uploaded_file and st.session_state.model_selected is not None:
            with col2:
                st.write('')
                st.write('')
                #original = Image.open(uploaded_file)
                bar_progress = 0
                my_bar = st.progress(bar_progress, text = "Ouverture de l'image...")
                time.sleep(0.5)
                bar_progress = 10
                my_bar.progress(bar_progress, text = "Réalisation du preprocessing...")
        
        if (uploaded_file is not None) and (st.session_state.model_selected is not None):

            file_bytes = np.asarray(bytearray(uploaded_file.read()), dtype=np.uint8)
            image = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
            resized_image = cv2.resize(image, (224, 224))
            resized_image = resized_image/255
            to_predict = np.expand_dims(resized_image, axis=0)
            tri_image = model_tri.predict(to_predict)

            if tri_image <= 0.5:



                # Ouvrir l'image téléchargée
                original = Image.open(uploaded_file)        

                # Image traitée
                gray_image = original.convert('L')
                channelized = gray_image.convert("RGB")
                resized = channelized.resize((224, 224))
                img_normalized = np.array(resized) / 255.0  # Convertir l'image en array et normaliser entre 0 et 1
                img_normalized -= np.array([0.485, 0.456, 0.406])  # Soustraction de la moyenne par canal
                img_normalized /= np.array([0.229, 0.224, 0.225])  # Division par l'écart-type par canal
                img_normalized = img_normalized.reshape(-1, 224, 224, 3)  # Remodeler pour correspondre aux attentes du modèle (batch_size, height, width, channels
                
                bar_progress = 30
                my_bar.progress(bar_progress, text = "Estimation des prédictions...")
                time.sleep(0.5)
                predictions = model.predict(img_normalized)
                bar_progress = 70
                my_bar.progress(bar_progress, text = "Génération de la GRAD-CAM...")
                time.sleep(0.5)
                    
                col1, col2, col3 = st.columns([0.3, 0.4, 0.3])

                def normalize_display_image(img_normalized):
                    img_display = (img_normalized * np.array([0.229, 0.224, 0.225])) + np.array([0.485, 0.456, 0.406])
                    img_display = np.clip(img_display, 0, 1)
                    img_display = (img_display * 255).astype(np.uint8)
                    return img_display

                if original.width > 500:
                    width = 500
                else:
                    width = original.width

                with col1:
                    st.subheader("Image originale")
                    st.image(original, use_column_width = False, width = width, clamp = True)
                    st.warning("Image redimensionnée pour des raisons d'affichage.", icon = "⚠️") if original.width > 500 else None

                with col2:
                    st.subheader("Image traitée")
                    st.image(img_normalized, use_column_width = False, clamp = True)

                with col3:
                    st.subheader("GRAD-CAM")
                    # Préparation de l'image pour GRAD-CAM sans dimension de batch
                    heatm_img = np.squeeze(img_normalized)

                    last_conv_layer_name = None
                    for layer in reversed(model.layers):
                        if isinstance(layer, keras.layers.Conv2D):  # Assure-toi que c'est bien keras.layers.Conv2D
                            last_conv_layer_name = layer.name
                            break

                    # Générer la heatmap à partir du modèle et de l'image traitée
                    heatmap = make_gradcam_heatmap(np.expand_dims(heatm_img, axis = 0), model, last_conv_layer_name)

                    # Préparation de l'image pour l'affichage de la superposition GRAD-CAM
                    img_display = normalize_display_image(heatm_img)  # Convertir l'image normalisée en image affichable
                    grad_img = save_and_display_gradcam(img_display, heatmap)  # Utilise l'image affichable ici
                    bar_progress = 100
                    my_bar.progress(bar_progress, text = "Exécution terminée")
                    time.sleep(0.5)
                    st.image(grad_img, use_column_width=False, clamp=True)
                
                class_names = {0 : 'COVID',
                            1 : 'Lung_Opacity',
                            2 : 'Normal',
                            3 : 'Viral Pneumonia'}
                df_predictions = pd.DataFrame(predictions)
                df_predictions = df_predictions.rename(columns = class_names)
                df_predictions_sorted = df_predictions.sort_values(by = 0, axis = 1, ascending = False)
                df_transposed = df_predictions_sorted.T
                table_html = df_transposed.to_html(header = False, index = True)

                classe_predite_indice = np.argmax(predictions)
                nom_classe_predite = class_names[classe_predite_indice]
                probabilite_predite = np.max(predictions)
                probabilite_predite = "{:.4f}".format(probabilite_predite)

                col1, col2, col3 = st.columns([0.3, 0.3, 0.4])

                with col1:
                    # Afficher la classe prédite et sa probabilité
                    st.markdown("Tableau des probabilités estimées :")
                    st.write(table_html, unsafe_allow_html = True)
                
                with col2:
                    st.markdown(
                        f"""
                        <div style='border-radius: 5px; border: 2px solid #d6d6d6; padding: 10px; max-width: 400px; background-color: rgba(255, 255, 255, 0.2);'>
                            <div style='display: flex; justify-content: space-around;'>
                                <div>
                                    <p style='font-size: 20px; text-align: center; margin: 0;'>Classe prédite</p>
                                    <p style='font-size: 30px; text-align: center; margin: 0;'>{nom_classe_predite}</p>
                                </div>
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
                    st.write("")
                    percent_predit = float(probabilite_predite) * 100
                    st.markdown(
                        f"""
                        <div style='border-radius: 5px; border: 2px solid #d6d6d6; padding: 10px; max-width: 400px; background-color: rgba(255, 255, 255, 0.2);'>
                            <div style='display: flex; justify-content: space-around;'>
                                <div>
                                    <p style='font-size: 20px; text-align: center; margin: 0;'>Confiance de la prédiction</p>
                                    <p style='font-size: 30px; text-align: center; margin: 0;'>{percent_predit} %</p>
                                </div>
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

                with col3:
                    if float(probabilite_predite) > 0.90:
                        st.markdown(f"Avec une probabilité de {probabilite_predite}, il est **certain** que cette radiographie illustre un cas {nom_classe_predite}. Attention cependant, cette prédiction est à prendre en compte seulement si l'image s'agit bien d'une radiographie conforme.")
                    elif float(probabilite_predite) > 0.75:
                        st.markdown(f"Avec une probabilité de {probabilite_predite}, il est **probable** que cette radiographie illustre un cas {nom_classe_predite}. Attention cependant, cette prédiction est à prendre en compte seulement si l'image s'agit bien d'une radiographie conforme.")
                    elif float(probabilite_predite) > 0.5:
                        st.markdown(f"Avec une probabilité de {probabilite_predite}, il est **possible** que cette radiographie illustre un cas {nom_classe_predite}. Attention cependant, cette prédiction est à prendre en compte seulement si l'image s'agit bien d'une radiographie conforme.")
                    elif float(probabilite_predite) <= 0.5:
                        st.markdown(f"Avec une probabilité de {probabilite_predite}, il **n'est pas prudent de dire** que cette radiographie illustre un cas {nom_classe_predite}. Il est possible que l'image ne soit pas adaptée au modèle.")

            else:  
                st.warning("L'image fournie ne semble pas être une radiographie")
                st.image(uploaded_file, caption = "Image fournie")

        else:
            # Message affiché tant qu'aucune image n'est téléchargée
            st.warning("Veuillez télécharger une image pour commencer l'analyse.", icon = "⚠️")

    with tab3:
        st.header("Résumé des modèles")

        col1, col2 = st.columns([0.5, 0.5])

        with col1:
            st.subheader("Avantages")
            st.markdown('''
                ✔️ Performances de prédictions équilibrées et satisfaisantes pour les différentes classes.

                ✔️ Modèle réactif et léger à mettre en place, applicable à toutes les radiographies pulmonaires standards.

                ✔️ Sensibilité et spécificité élevées, en particulier pour les classes COVID (0.96) et Normal (0.91).

                ✔️ Equilibre contrôlé dans l'entrainement du modèle, réduisant le risque de data drift.
                        ''')

        with col2:
            st.subheader("Inconvénients")
            st.markdown('''
                ❌ Bien qu'efficace, les modèles peuvent encore être optimisés en visant la qualité des images et la sélection des jeux d'entrainement.

                ❌ Les GRADCAM montrent encore des features "non pertinentes" pour certaines images avec de nombreux artefacts.

                ❌ Bien que les métriques utilisés pour sélectionner les modèles soient complémentaires et pertinentes, personnaliser des métriques de perte permettraient d'améliorer d'autant plus les performances du modèle.

                ❌ Le modèle ne fait pasl a différence entre une radiographie et un autre type d'image.
                        ''')