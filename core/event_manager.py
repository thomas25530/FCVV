# -*- coding: utf-8 -*-
import threading
from datetime import datetime
import requests
from kivy.utils import platform
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.checkbox import CheckBox
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.uix.spinner import Spinner
from kivy.uix.textinput import TextInput
from kivy.uix.widget import Widget
from kivy.graphics import Color, RoundedRectangle


class EventManager:

    @staticmethod
    def ouvrir_formulaire(screen_instance, match_id="", match_info=None):

        if match_info is None:
            match_info = {}

        # SÉCURITÉ : Si le dictionnaire reçu est partiel ou vide (ex: depuis la liste), on va le chercher complet dans le cache
        if match_id and match_id != "Nouvel événement" and match_id != "Nouvel evenement":
            cat_data = getattr(screen_instance, "_cache_data", {}).get(screen_instance.current_cat, {})
            calendrier = cat_data.get("calendrier", {})
            if match_id in calendrier:
                match_info = calendrier[match_id]

        # COPIE PROFONDE pour que chaque onglet possède ses propres données isolées en mémoire
        match_info_match = match_info.copy()
        match_info_entrainement = match_info.copy()
        match_info_evenement = match_info.copy()

        # --- CONTENEUR PRINCIPAL AVEC FOND CLAIR ---
        content = BoxLayout(orientation="vertical", padding=dp(15), spacing=dp(10))
        with content.canvas.before:
            Color(0.95, 0.95, 0.97, 1)  # Fond clair uniforme
            self_bg = RoundedRectangle(pos=content.pos, size=content.size, radius=[dp(15)])
        content.bind(pos=lambda obj, val: setattr(self_bg, 'pos', val),
                     size=lambda obj, val: setattr(self_bg, 'size', val))

        # En-tête du formulaire (Titre sombre et contrasté)
        lbl_titre_popup = Label(
            text="[b]Édition de l'événement[/b]",
            markup=True,
            size_hint_y=None,
            height=dp(35),
            font_size=dp(18),
            color=(0.1, 0.1, 0.15, 1),
            halign="center"
        )
        content.add_widget(lbl_titre_popup)

        tab_layout = BoxLayout(size_hint_y=None, height=dp(45), spacing=dp(5))
        tabs = ["MATCH", "ENTRAINEMENT", "EVENEMENT"]
        
        current_type = match_info.get("type", "MATCH").upper()
        if current_type not in tabs:
            current_type = "MATCH"

        tab_buttons = {}
        dynamic_container = BoxLayout(orientation="vertical", size_hint=(1, 1))
        popup_ref = []  # Liste mutable pour stocker la référence de la popup

        def rafraichir_formulaire(t):
            nonlocal current_type
            current_type = t
            for k, btn in tab_buttons.items():
                if k == t:
                    btn.background_color = (0.2, 0.6, 0.3, 1)  # Vert actif
                    btn.color = (1, 1, 1, 1)
                else:
                    btn.background_color = (0.85, 0.85, 0.88, 1)  # Gris clair inactif
                    btn.color = (0.3, 0.3, 0.3, 1)
                
            dynamic_container.clear_widgets()
            
            # --- ONGLET MATCH ---
            if current_type == "MATCH":
                form_scroll = ScrollView(size_hint=(1, 1), bar_width=0)
                form_box = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(10), padding=dp(5))
                form_box.bind(minimum_height=form_box.setter("height"))

                def add_field(label_text, default_val=""):
                    form_box.add_widget(Label(text=label_text, size_hint_y=None, height=dp(25), halign="left", color=(0.2, 0.2, 0.25, 1)))
                    ti = TextInput(text=str(default_val), multiline=False, size_hint_y=None, height=dp(40), background_color=(1, 1, 1, 1), foreground_color=(0.1, 0.1, 0.1, 1), cursor_color=(0.1, 0.1, 0.1, 1))
                    form_box.add_widget(ti)
                    return ti

                ti_titre = add_field("Titre du match", match_info_match.get("titre", ""))
                ti_adversaire = add_field("Adversaire", match_info_match.get("adversaire", ""))
                ti_date = add_field("Date (Format JJ/MM/AAAA)", match_info_match.get("date", ""))
                ti_heure_rdv = add_field("Heure du RDV (ex: 13:30)", match_info_match.get("heure_rdv", ""))
                ti_heure_coup = add_field("Heure du coup d'envoi (ex: 15:00)", match_info_match.get("heure_coup_envoi", ""))
                ti_lieu = add_field("Lieu (Domicile / Extérieur)", match_info_match.get("lieu", ""))
                ti_entraineurs = add_field("Entraîneurs présents", match_info_match.get("entraineurs", ""))

                form_box.add_widget(Label(text="[b]Sondages[/b]", markup=True, size_hint_y=None, height=dp(30), color=(0.15, 0.45, 0.25, 1)))
                
                box_sondage_classique = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(10))
                chk_sondage_classique = CheckBox(active=match_info_match.get("sondage_classique", True), size_hint_x=None, width=dp(40), color=(0.2, 0.2, 0.2, 1))
                box_sondage_classique.add_widget(chk_sondage_classique)
                box_sondage_classique.add_widget(Label(text="Activer Sondage Présent / Absent", halign="left", color=(0.2, 0.2, 0.25, 1)))
                form_box.add_widget(box_sondage_classique)

                box_sondage_trajet = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(10))
                chk_sondage_trajet = CheckBox(active=match_info_match.get("sondage_trajet", False), size_hint_x=None, width=dp(40), color=(0.2, 0.2, 0.2, 1))
                box_sondage_trajet.add_widget(chk_sondage_trajet)
                box_sondage_trajet.add_widget(Label(text="Activer Sondage Trajet", halign="left", color=(0.2, 0.2, 0.25, 1)))
                form_box.add_widget(box_sondage_trajet)

                form_box.add_widget(Label(text="[b]Convocations[/b]", markup=True, size_hint_y=None, height=dp(30), color=(0.15, 0.45, 0.25, 1)))
                
                box_convocation = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(10))
                chk_convocation = CheckBox(active=match_info_match.get("activer_convocation", False), size_hint_x=None, width=dp(40), color=(0.2, 0.2, 0.2, 1))
                box_convocation.add_widget(chk_convocation)
                box_convocation.add_widget(Label(text="Activer les convocations pour ce match", halign="left", color=(0.2, 0.2, 0.25, 1)))
                form_box.add_widget(box_convocation)

                # --- CONTENEUR DYNAMIQUE POUR LA LISTE DES JOUEURS & COMPTEUR ---
                container_joueurs_section = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(5))
                container_joueurs_section.bind(minimum_height=container_joueurs_section.setter('height'))
                form_box.add_widget(container_joueurs_section)

                cat_data = screen_instance._cache_data.get(screen_instance.current_cat, {})
                liste_joueurs = cat_data.get("tous_les_joueurs", [])
                groupes_yaml = cat_data.get("groupes", {})

                checkboxes_joueurs = []

                def actualiser_section_joueurs(checkbox, value):
                    container_joueurs_section.clear_widgets()
                    checkboxes_joueurs.clear()
                    
                    if value:  # Uniquement si "Activer les convocations" est coché
                        lbl_compteur = Label(
                            text="[b]--- Liste des Joueurs Convoqués (Sélectionnés : 0) ---[/b]", 
                            markup=True, size_hint_y=None, height=dp(30), color=(0.15, 0.45, 0.25, 1)
                        )
                        container_joueurs_section.add_widget(lbl_compteur)

                        def mettre_a_jour_compteur(*args):
                            nb_coches = sum(1 for cb in checkboxes_joueurs if cb.active)
                            lbl_compteur.text = f"[b]--- Liste des Joueurs Convoqués (Sélectionnés : {nb_coches}) ---[/b]"

                        # --- SÉLECTEUR DE GROUPE (DEPUIS LE YAML) ---
                        if groupes_yaml:
                            box_groupe = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(10))
                            box_groupe.add_widget(Label(text="Modèle de groupe :", size_hint_x=None, width=dp(130), halign="left", color=(0.2, 0.2, 0.25, 1)))

                            noms_groupes = ["Sélectionner un groupe..."] + list(groupes_yaml.keys())
                            spinner_groupes = Spinner(
                                text="Sélectionner un groupe...",
                                values=noms_groupes,
                                size_hint_x=1,
                                background_normal="",
                                background_color=(0.15, 0.65, 0.35, 1),
                                color=(1, 1, 1, 1)
                            )

                            def sur_changement_groupe(spinner, texte_selectionne):
                                if texte_selectionne in groupes_yaml:
                                    joueurs_du_groupe = groupes_yaml[texte_selectionne]  # Liste de chaînes ex: ["COULOT Quentin", ...]
                                    
                                    # Normalisation de la liste du groupe pour un matching facile (en minuscules)
                                    joueurs_groupe_lower = [j.strip().lower() for j in joueurs_du_groupe]

                                    for cb in checkboxes_joueurs:
                                        nom_cb = getattr(cb, 'nom_joueur', "").strip().lower()
                                        prenom_cb = getattr(cb, 'prenom_joueur', "").strip().lower()
                                        
                                        # Formats possibles dans l'application
                                        format_1 = f"{nom_cb} {prenom_cb}".strip()         # ex: "coulot quentin"
                                        format_2 = f"{prenom_cb} {nom_cb}".strip()         # ex: "quentin coulot"
                                        
                                        # On vérifie si l'un des formats correspond à une entrée du groupe YAML
                                        correspondance = any(
                                            (format_1 in j or j in format_1) or (format_2 in j or j in format_2)
                                            for j in joueurs_groupe_lower
                                        )
                                        
                                        cb.active = correspondance

                            spinner_groupes.bind(text=sur_changement_groupe)
                            box_groupe.add_widget(spinner_groupes)
                            container_joueurs_section.add_widget(box_groupe)

                        joueurs_layout = GridLayout(cols=1, size_hint_y=None, spacing=dp(5))
                        joueurs_layout.bind(minimum_height=joueurs_layout.setter('height'))

                        # --- AJOUT MANUEL RAPIDE ---
                        container_joueurs_section.add_widget(
                            Label(
                                text="Ajout manuel rapide :",
                                size_hint_y=None,
                                height=dp(25),
                                halign="left",
                                font_size=dp(13),
                                color=(0.3, 0.3, 0.35, 1),
                            )
                        )

                        add_manual_box = BoxLayout(size_hint_y=None, height=dp(35), spacing=dp(5))
                        cat_input = TextInput(hint_text="Cat", multiline=False, size_hint_x=0.25, background_color=(1, 1, 1, 1), foreground_color=(0.1, 0.1, 0.1, 1), cursor_color=(0.1, 0.1, 0.1, 1))
                        nom_input = TextInput(hint_text="Nom Prénom", multiline=False, background_color=(1, 1, 1, 1), foreground_color=(0.1, 0.1, 0.1, 1), cursor_color=(0.1, 0.1, 0.1, 1))

                        def ajouter_joueur_manuel(instance):
                            nom_complet_saisi = nom_input.text.strip()
                            cat = cat_input.text.strip().upper()

                            if nom_complet_saisi:
                                parts = nom_complet_saisi.split(" ", 1)
                                nom = parts[0].upper()
                                prenom = parts[1].capitalize() if len(parts) > 1 else ""

                                label_text_brut = f"[{cat}] {nom} {prenom}".strip() if cat else f"{nom} {prenom}".strip()

                                row = BoxLayout(size_hint_y=None, height=dp(35), spacing=dp(10))
                                cb = CheckBox(size_hint_x=None, width=dp(40), active=True, color=(0.2, 0.2, 0.2, 1))
                                cb.nom_joueur = nom
                                cb.prenom_joueur = prenom
                                cb.categorie = cat
                                cb.est_manuel = True

                                lbl_manuel = Label(
                                    text=f"[b]{label_text_brut}[/b]",
                                    markup=True,
                                    halign="left",
                                    color=(0.2, 0.2, 0.25, 1)
                                )

                                def update_manual_style(checkbox, value, label_widget=lbl_manuel, texte_brut=label_text_brut):
                                    label_widget.text = f"[b]{texte_brut}[/b]" if value else texte_brut
                                    mettre_a_jour_compteur()

                                cb.bind(active=update_manual_style)

                                row.add_widget(cb)
                                row.add_widget(lbl_manuel)

                                joueurs_layout.add_widget(row, index=len(joueurs_layout.children))
                                checkboxes_joueurs.insert(0, cb)

                                nom_input.text = ""
                                cat_input.text = ""
                                mettre_a_jour_compteur()

                        btn_add = Button(text="+", size_hint_x=0.15, background_normal="", background_color=(0.2, 0.6, 0.3, 1), color=(1, 1, 1, 1), bold=True)
                        btn_add.bind(on_release=ajouter_joueur_manuel)
                        add_manual_box.add_widget(cat_input)
                        add_manual_box.add_widget(nom_input)
                        add_manual_box.add_widget(btn_add)

                        container_joueurs_section.add_widget(add_manual_box)

                        joueurs_deja_convoques = match_info_match.get("joueurs_convoques", [])
                        noms_deja_convoques = []
                        for j in joueurs_deja_convoques:
                            if isinstance(j, dict):
                                noms_deja_convoques.append(f"{j.get('nom', '').upper()} {j.get('prenom', '')}".strip())
                            else:
                                noms_deja_convoques.append(str(j).strip())

                        for joueur in joueurs_deja_convoques:
                            if isinstance(joueur, dict) and joueur.get("est_manuel", False):
                                nom = joueur.get('nom', '').upper()
                                prenom = joueur.get('prenom', '')
                                cat = joueur.get('categorie', '').upper()
                                label_text = f"[{cat}] {nom} {prenom}".strip() if cat else f"{nom} {prenom}".strip()

                                row = BoxLayout(size_hint_y=None, height=dp(35), spacing=dp(10))
                                cb = CheckBox(size_hint_x=None, width=dp(40), active=True, color=(0.2, 0.2, 0.2, 1))
                                cb.nom_joueur = nom
                                cb.prenom_joueur = prenom
                                cb.categorie = cat
                                cb.est_manuel = True
                                cb.bind(active=mettre_a_jour_compteur)

                                row.add_widget(cb)
                                row.add_widget(Label(text=label_text, halign="left", color=(0.2, 0.2, 0.25, 1)))
                                joueurs_layout.add_widget(row)
                                checkboxes_joueurs.append(cb)

                        joueurs_tries = sorted(
                            liste_joueurs,
                            key=lambda j: (
                                j.get("nom", "").strip().upper(),
                                j.get("prenom", "").strip().upper(),
                            ),
                        )

                        for joueur in joueurs_tries:
                            nom = joueur.get('nom', '').strip().upper()
                            prenom = joueur.get('prenom', '').strip()
                            nom_complet = f"{nom} {prenom}".strip()
                            
                            if any(cb.nom_joueur == nom and cb.prenom_joueur == prenom for cb in checkboxes_joueurs if getattr(cb, 'est_manuel', False)):
                                continue

                            row = BoxLayout(size_hint_y=None, height=dp(35), spacing=dp(10))
                            chk_j = CheckBox(active=(nom_complet in noms_deja_convoques), size_hint_x=None, width=dp(40), color=(0.2, 0.2, 0.2, 1))
                            chk_j.nom_joueur = nom
                            chk_j.prenom_joueur = prenom
                            chk_j.est_manuel = False
                            
                            lbl_j = Label(
                                text=f"[b]{nom_complet}[/b]" if chk_j.active else nom_complet,
                                markup=True,
                                halign="left",
                                color=(0.2, 0.2, 0.25, 1)
                            )

                            def update_label_style(cb, value, label_widget=lbl_j, texte_brut=nom_complet):
                                label_widget.text = f"[b]{texte_brut}[/b]" if value else texte_brut
                                mettre_a_jour_compteur()

                            chk_j.bind(active=update_label_style)
                            
                            checkboxes_joueurs.append(chk_j)
                            row.add_widget(chk_j)
                            row.add_widget(lbl_j)
                            joueurs_layout.add_widget(row)

                        container_joueurs_section.add_widget(joueurs_layout)
                        mettre_a_jour_compteur()

                chk_convocation.bind(active=actualiser_section_joueurs)
                actualiser_section_joueurs(chk_convocation, chk_convocation.active)

                form_scroll.add_widget(form_box)
                dynamic_container.add_widget(form_scroll)

                btn_save = Button(text="Enregistrer le match", size_hint_y=None, height=dp(45), background_normal="", background_color=(0.15, 0.65, 0.35, 1), color=(1, 1, 1, 1), bold=True)
                
                def save_match(x):
                    date_val = ti_date.text.strip()
                    try:
                        datetime.strptime(date_val, "%d/%m/%Y")
                    except ValueError:
                        p_err = Popup(title="Erreur de format", content=Label(text="Format de date invalide !\nVeuillez utiliser le format JJ/MM/AAAA", color=(0.2, 0.2, 0.2, 1), halign="center"), size_hint=(0.7, 0.3), separator_height=0)
                        p_err.open()
                        return

                    calendrier_actuel = screen_instance._cache_data.get(screen_instance.current_cat, {}).get("calendrier", {})
                    est_une_modification = bool(match_id) and match_id in calendrier_actuel

                    def executer_sauvegarde(commit_message=""):
                        joueurs_convoques = []
                        for cb in checkboxes_joueurs:
                            if cb.active:
                                joueurs_convoques.append({
                                    "nom": getattr(cb, "nom_joueur", "").strip().upper(),
                                    "prenom": getattr(cb, "prenom_joueur", "").strip(),
                                    "categorie": getattr(cb, "categorie", "").strip().upper(),
                                    "est_manuel": getattr(cb, "est_manuel", False)
                                }) if chk_convocation.active else None

                        maintenant_str = datetime.now().strftime("%d/%m/%Y à %H:%M")
                        match_info_match.update({
                            "type": "MATCH",
                            "titre": ti_titre.text.strip(),
                            "adversaire": ti_adversaire.text.strip(),
                            "date": date_val,
                            "heure_rdv": ti_heure_rdv.text.strip(),
                            "heure_coup_envoi": ti_heure_coup.text.strip(),
                            "lieu": ti_lieu.text.strip(),
                            "entraineurs": ti_entraineurs.text.strip(),
                            "sondage_classique": chk_sondage_classique.active,
                            "sondage_trajet": chk_sondage_trajet.active,
                            "activer_convocation": chk_convocation.active,
                            "joueurs_convoques": joueurs_convoques,
                            "dernier_commit": commit_message,
                            "timestamp_action": maintenant_str,
                            "est_modification": est_une_modification
                        })

                        if est_une_modification:
                            key = match_id
                        else:
                            adv_clean = ti_adversaire.text.strip().replace(" ", "_").lower() or "inconnu"
                            date_clean = date_val.replace("/", "-")
                            heure_clean = ti_heure_rdv.text.strip().replace(":", "h") or "00h00"
                            key = f"match_{adv_clean}_{date_clean}_{heure_clean}"
                        
                        data = screen_instance._cache_data.get(screen_instance.current_cat, {})
                        if "calendrier" not in data:
                            data["calendrier"] = {}
                        
                        if est_une_modification and match_id in data["calendrier"]:
                            if match_id != key:
                                data["calendrier"].pop(match_id, None)

                        data["calendrier"][key] = match_info_match
                        
                        url = f"https://fcvv-api.onrender.com/convocations/update/{screen_instance.current_cat}/{key}"
                        
                        def do_api_save():
                            try:
                                headers = screen_instance.get_user_header() if hasattr(screen_instance, "get_user_header") else {}
                                is_windows = (platform == 'win')
                                requests.put(url, json=match_info_match, headers=headers, timeout=10, verify=not is_windows)
                                Clock.schedule_once(lambda dt: screen_instance.fetch_convocations_from_firebase(data))
                            except Exception as e:
                                print(f"Erreur sauvegarde match API : {e}")
                                Clock.schedule_once(lambda dt: screen_instance.update_ui())

                        threading.Thread(target=do_api_save, daemon=True).start()
                        if popup_ref:
                            popup_ref[0].dismiss()

                    if est_une_modification:
                        content_commit = BoxLayout(orientation='vertical', padding=dp(15), spacing=dp(10))
                        
                        # 1. Le champ de saisie en premier (tout en haut)
                        ti_commit = TextInput(hint_text="Ex: Modification de l'heure du RDV", multiline=False, size_hint_y=None, height=dp(40), background_color=(1, 1, 1, 1), foreground_color=(0.1, 0.1, 0.1, 1), cursor_color=(0.1, 0.1, 0.1, 1))
                        content_commit.add_widget(ti_commit)
                        
                        # 2. Le bouton juste en dessous du champ
                        btn_valider_commit = Button(text="Confirmer l'enregistrement", size_hint_y=None, height=dp(45), background_normal="", background_color=(0.15, 0.65, 0.35, 1), color=(1, 1, 1, 1), bold=True)
                        content_commit.add_widget(btn_valider_commit)
                        
                        # 3. Le label explicatif placé après
                        content_commit.add_widget(Label(text="[b]Note de modification (optionnel)[/b]", markup=True, size_hint_y=None, height=dp(30), color=(0.15, 0.45, 0.25, 1)))
                        
                        content_commit.add_widget(Widget())
                        
                        # Titre de la popup propre
                        popup_commit = Popup(title="Motif de modification", content=content_commit, size_hint=(0.8, 0.4), separator_height=0)
                        
                        def valider_avec_commit(instance):
                            msg = ti_commit.text.strip() or "Mise à jour de l'événement"
                            popup_commit.dismiss()
                            executer_sauvegarde(msg)
                            
                        btn_valider_commit.bind(on_release=valider_avec_commit)
                        popup_commit.open()
                    else:
                        executer_sauvegarde("Création de l'événement")

                btn_save.bind(on_release=save_match)
                dynamic_container.add_widget(btn_save)

            # --- ONGLET ENTRAINEMENT ---
            elif current_type == "ENTRAINEMENT":
                form_scroll = ScrollView(bar_width=0, size_hint=(1, 1))
                form_box = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(10), padding=dp(5))
                form_box.bind(minimum_height=form_box.setter("height"))

                def add_field(label_text, default_val=""):
                    form_box.add_widget(Label(text=label_text, size_hint_y=None, height=dp(25), halign="left", color=(0.2, 0.2, 0.25, 1)))
                    ti = TextInput(text=str(default_val), multiline=False, size_hint_y=None, height=dp(40), background_color=(1, 1, 1, 1), foreground_color=(0.1, 0.1, 0.1, 1), cursor_color=(0.1, 0.1, 0.1, 1))
                    form_box.add_widget(ti)
                    return ti

                ti_titre = add_field("Titre de l'entraînement", match_info_entrainement.get("titre", ""))
                ti_date = add_field("Date (Format JJ/MM/AAAA)", match_info_entrainement.get("date", ""))
                ti_heure = add_field("Heure (ex: 19:30)", match_info_entrainement.get("heure", match_info_entrainement.get("heure_rdv", "")))
                ti_lieu = add_field("Lieu", match_info_entrainement.get("lieu", ""))

                sondage_box = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(40), spacing=dp(10))
                sondage_box.add_widget(Label(text="Activer un sondage de présence requis", color=(0.2, 0.2, 0.25, 1), halign="left"))
                chk_sondage = CheckBox(active=match_info_entrainement.get("sondage_actif", True), size_hint_x=None, width=dp(40), color=(0.2, 0.2, 0.2, 1))
                sondage_box.add_widget(chk_sondage)
                form_box.add_widget(sondage_box)

                form_scroll.add_widget(form_box)
                dynamic_container.add_widget(form_scroll)

                btn_save = Button(text="Enregistrer l'entraînement", size_hint_y=None, height=dp(45), background_normal="", background_color=(0.15, 0.65, 0.35, 1), color=(1, 1, 1, 1), bold=True)
                
                def save_entrainement(x):
                    date_val = ti_date.text.strip()
                    try:
                        datetime.strptime(date_val, "%d/%m/%Y")
                    except ValueError:
                        p_err = Popup(title="Erreur de format", content=Label(text="Format de date invalide !\nVeuillez utiliser le format JJ/MM/AAAA", color=(0.2, 0.2, 0.2, 1), halign="center"), size_hint=(0.7, 0.3), separator_height=0)
                        p_err.open()
                        return

                    calendrier_actuel = screen_instance._cache_data.get(screen_instance.current_cat, {}).get("calendrier", {})
                    est_une_modification = bool(match_id) and match_id in calendrier_actuel

                    def executer_sauvegarde(commit_message=""):
                        maintenant_str = datetime.now().strftime("%d/%m/%Y à %H:%M")
                        match_info_entrainement.update({
                            "type": "ENTRAINEMENT",
                            "titre": ti_titre.text.strip(),
                            "date": date_val,
                            "heure": ti_heure.text.strip(),
                            "lieu": ti_lieu.text.strip(),
                            "sondage_actif": chk_sondage.active,
                            "dernier_commit": commit_message,
                            "timestamp_action": maintenant_str,
                            "est_modification": est_une_modification
                        })

                        if est_une_modification:
                            key = match_id
                        else:
                            date_clean = date_val.replace("/", "-")
                            heure_clean = ti_heure.text.strip().replace(":", "h") or "00h00"
                            key = f"entrainement_{date_clean}_{heure_clean}"
                        
                        data = screen_instance._cache_data.get(screen_instance.current_cat, {})
                        if "calendrier" not in data:
                            data["calendrier"] = {}
                        
                        if est_une_modification and match_id in data["calendrier"]:
                            if match_id != key:
                                data["calendrier"].pop(match_id, None)

                        data["calendrier"][key] = match_info_entrainement
                        
                        url = f"https://fcvv-api.onrender.com/convocations/update/{screen_instance.current_cat}/{key}"
                        
                        def do_api_save():
                            try:
                                headers = screen_instance.get_user_header() if hasattr(screen_instance, "get_user_header") else {}
                                is_windows = (platform == 'win')
                                requests.put(url, json=match_info_entrainement, headers=headers, timeout=10, verify=not is_windows)
                                Clock.schedule_once(lambda dt: screen_instance.fetch_convocations_from_firebase(data))
                            except Exception as e:
                                print(f"Erreur sauvegarde entrainement API : {e}")
                                Clock.schedule_once(lambda dt: screen_instance.update_ui())

                        threading.Thread(target=do_api_save, daemon=True).start()
                        if popup_ref:
                            popup_ref[0].dismiss()

                    if est_une_modification:
                        content_commit = BoxLayout(orientation='vertical', padding=dp(15), spacing=dp(10))
                        
                        # 1. Le champ de saisie en premier (tout en haut)
                        ti_commit = TextInput(hint_text="Ex: Modification de l'heure", multiline=False, size_hint_y=None, height=dp(40), background_color=(1, 1, 1, 1), foreground_color=(0.1, 0.1, 0.1, 1), cursor_color=(0.1, 0.1, 0.1, 1))
                        content_commit.add_widget(ti_commit)
                        
                        # 2. Le bouton juste en dessous du champ
                        btn_valider_commit = Button(text="Confirmer l'enregistrement", size_hint_y=None, height=dp(45), background_normal="", background_color=(0.15, 0.65, 0.35, 1), color=(1, 1, 1, 1), bold=True)
                        content_commit.add_widget(btn_valider_commit)
                        
                        # 3. Le label explicatif placé en bas (optionnel)
                        content_commit.add_widget(Label(text="[b]Motif de la modification[/b]", markup=True, size_hint_y=None, height=dp(30), color=(0.15, 0.45, 0.25, 1)))
                        
                        
                        content_commit.add_widget(Widget())
                        
                        # Titre de la popup épuré (plus de "Git Commit")
                        popup_commit = Popup(title="Modification", content=content_commit, size_hint=(0.8, 0.4), separator_height=0)
                        
                        def valider_avec_commit(instance):
                            msg = ti_commit.text.strip() or "Mise à jour de l'entraînement"
                            popup_commit.dismiss()
                            executer_sauvegarde(msg)
                            
                        btn_valider_commit.bind(on_release=valider_avec_commit)
                        popup_commit.open()
                    else:
                        executer_sauvegarde("Création de l'entraînement")

                btn_save.bind(on_release=save_entrainement)
                dynamic_container.add_widget(btn_save)

            # --- ONGLET EVENEMENT ---
            else:
                form_scroll = ScrollView(bar_width=0, size_hint=(1, 1))
                form_box = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(10), padding=dp(5))
                form_box.bind(minimum_height=form_box.setter("height"))

                def add_field(label_text, default_val=""):
                    form_box.add_widget(Label(text=label_text, size_hint_y=None, height=dp(25), halign="left", color=(0.2, 0.2, 0.25, 1)))
                    ti = TextInput(text=str(default_val), multiline=False, size_hint_y=None, height=dp(40), background_color=(1, 1, 1, 1), foreground_color=(0.1, 0.1, 0.1, 1), cursor_color=(0.1, 0.1, 0.1, 1))
                    form_box.add_widget(ti)
                    return ti

                ti_titre = add_field("Titre de l'événement", match_info_evenement.get("titre", ""))
                ti_date = add_field("Date (Format JJ/MM/AAAA)", match_info_evenement.get("date", ""))
                ti_heure = add_field("Heure", match_info_evenement.get("heure", ""))
                ti_lieu = add_field("Lieu", match_info_evenement.get("lieu", ""))

                form_box.add_widget(Label(text="[b]Sondages[/b]", markup=True, size_hint_y=None, height=dp(30), color=(0.15, 0.45, 0.25, 1)))

                type_sondage_actuel = match_info_evenement.get("type_sondage", "classique")
                sondage_actif_actuel = match_info_evenement.get("sondage_actif", True)

                box_sondage_classique = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(10))
                chk_sondage_classique = CheckBox(active=(type_sondage_actuel == "classique" and sondage_actif_actuel), size_hint_x=None, width=dp(40), color=(0.2, 0.2, 0.2, 1))
                box_sondage_classique.add_widget(chk_sondage_classique)
                box_sondage_classique.add_widget(Label(text="Activer Sondage Classique (Présent / Absent)", halign="left", color=(0.2, 0.2, 0.25, 1)))
                form_box.add_widget(box_sondage_classique)

                box_sondage_multiple = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(10))
                chk_sondage_multiple = CheckBox(active=(type_sondage_actuel == "multiple" and sondage_actif_actuel), size_hint_x=None, width=dp(40), color=(0.2, 0.2, 0.2, 1))
                box_sondage_multiple.add_widget(chk_sondage_multiple)
                box_sondage_multiple.add_widget(Label(text="Activer Sondage Choix Multiples", halign="left", color=(0.2, 0.2, 0.25, 1)))
                form_box.add_widget(box_sondage_multiple)

                container_options_multiple = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(5))
                container_options_multiple.bind(minimum_height=container_options_multiple.setter('height'))
                form_box.add_widget(container_options_multiple)

                ti_titre_multiple = None
                ti_options_multiple = None
                
                # Verrou anti-réentrance pour bloquer les événements cascades lors du décochage automatique
                en_cours_de_mise_a_jour = False

                def actualiser_options_multiple(checkbox, value):
                    nonlocal ti_titre_multiple, ti_options_multiple, en_cours_de_mise_a_jour
                    if en_cours_de_mise_a_jour:
                        return

                    en_cours_de_mise_a_jour = True
                    try:
                        # 1. Gestion de l'exclusivité des cases
                        if checkbox == chk_sondage_multiple and value:
                            chk_sondage_classique.active = False
                        elif checkbox == chk_sondage_classique and value:
                            chk_sondage_multiple.active = False

                        # 2. Réinitialisation et reconstruction unique
                        container_options_multiple.clear_widgets()
                        
                        if chk_sondage_multiple.active:
                            container_options_multiple.add_widget(Label(
                                text="Titre personnalisé du sondage (ex: Nombre de places)",
                                size_hint_y=None, height=dp(25), halign="left", font_size=dp(12), color=(0.3, 0.3, 0.35, 1)
                            ))
                            defaut_titre = match_info_evenement.get("titre_sondage_multiple", "Votre Choix")
                            ti_titre_multiple = TextInput(
                                text=defaut_titre, multiline=False, size_hint_y=None, height=dp(40),
                                background_color=(1, 1, 1, 1), foreground_color=(0.1, 0.1, 0.1, 1), cursor_color=(0.1, 0.1, 0.1, 1)
                            )
                            container_options_multiple.add_widget(ti_titre_multiple)

                            container_options_multiple.add_widget(Label(
                                text="Options de réponse (séparées par des virgules, ex: 1, 2, 3, 4, 5)",
                                size_hint_y=None, height=dp(25), halign="left", font_size=dp(12), color=(0.3, 0.3, 0.35, 1)
                            ))
                            defaut_opts = ", ".join(match_info_evenement.get("options_sondage", ["1", "2", "3", "4", "5"]))
                            ti_options_multiple = TextInput(
                                text=defaut_opts, multiline=False, size_hint_y=None, height=dp(40),
                                background_color=(1, 1, 1, 1), foreground_color=(0.1, 0.1, 0.1, 1), cursor_color=(0.1, 0.1, 0.1, 1)
                            )
                            container_options_multiple.add_widget(ti_options_multiple)
                        else:
                            ti_titre_multiple = None
                            ti_options_multiple = None
                    finally:
                        en_cours_de_mise_a_jour = False

                # Activation des événements et rendu initial propre
                chk_sondage_multiple.bind(active=actualiser_options_multiple)
                chk_sondage_classique.bind(active=actualiser_options_multiple)
                actualiser_options_multiple(None, None)

                form_scroll.add_widget(form_box)
                dynamic_container.add_widget(form_scroll)

                btn_save = Button(text="Enregistrer l'événement", size_hint_y=None, height=dp(45), background_normal="", background_color=(0.15, 0.65, 0.35, 1), color=(1, 1, 1, 1), bold=True)
                
                def save_evenement(x):
                    date_val = ti_date.text.strip()
                    try:
                        datetime.strptime(date_val, "%d/%m/%Y")
                    except ValueError:
                        p_err = Popup(title="Erreur de format", content=Label(text="Format de date invalide !\nVeuillez utiliser le format JJ/MM/AAAA", color=(0.2, 0.2, 0.2, 1), halign="center"), size_hint=(0.7, 0.3), separator_height=0)
                        p_err.open()
                        return

                    calendrier_actuel = screen_instance._cache_data.get(screen_instance.current_cat, {}).get("calendrier", {})
                    est_une_modification = bool(match_id) and match_id in calendrier_actuel

                    def executer_sauvegarde(commit_message=""):
                        maintenant_str = datetime.now().strftime("%d/%m/%Y à %H:%M")
                        
                        if chk_sondage_multiple.active:
                            type_sondage = "multiple"
                            sondage_actif = True
                        elif chk_sondage_classique.active:
                            type_sondage = "classique"
                            sondage_actif = True
                        else:
                            type_sondage = "classique"
                            sondage_actif = False

                        options_sondage = []
                        if type_sondage == "multiple" and ti_options_multiple:
                            options_sondage = [opt.strip() for opt in ti_options_multiple.text.split(",") if opt.strip()]
                            if not options_sondage:
                                options_sondage = ["1", "2", "3", "4", "5"]

                        titre_sondage_multiple = "Votre Choix"
                        if type_sondage == "multiple" and ti_titre_multiple:
                            titre_sondage_multiple = ti_titre_multiple.text.strip() or "Votre Choix"

                        match_info_evenement.update({
                            "type": "EVENEMENT",
                            "titre": ti_titre.text.strip(),
                            "date": date_val,
                            "heure": ti_heure.text.strip(),
                            "lieu": ti_lieu.text.strip(),
                            "sondage_actif": sondage_actif,
                            "type_sondage": type_sondage,
                            "titre_sondage_multiple": titre_sondage_multiple,
                            "options_sondage": options_sondage,
                            "dernier_commit": commit_message,
                            "timestamp_action": maintenant_str,
                            "est_modification": est_une_modification
                        })

                        if est_une_modification:
                            key = match_id
                        else:
                            date_clean = date_val.replace("/", "-")
                            key = f"evenement_{date_clean}"
                        
                        data = screen_instance._cache_data.get(screen_instance.current_cat, {})
                        if "calendrier" not in data:
                            data["calendrier"] = {}
                        
                        if est_une_modification and match_id in data["calendrier"]:
                            if match_id != key:
                                data["calendrier"].pop(match_id, None)

                        data["calendrier"][key] = match_info_evenement
                        
                        url = f"https://fcvv-api.onrender.com/convocations/update/{screen_instance.current_cat}/{key}"
                        
                        def do_api_save():
                            try:
                                headers = screen_instance.get_user_header() if hasattr(screen_instance, "get_user_header") else {}
                                is_windows = (platform == 'win')
                                requests.put(url, json=match_info_evenement, headers=headers, timeout=10, verify=not is_windows)
                                Clock.schedule_once(lambda dt: screen_instance.fetch_convocations_from_firebase(data))
                            except Exception as e:
                                print(f"Erreur sauvegarde evenement API : {e}")
                                Clock.schedule_once(lambda dt: screen_instance.update_ui())

                        threading.Thread(target=do_api_save, daemon=True).start()
                        if popup_ref:
                            popup_ref[0].dismiss()

                    if est_une_modification:
                        content_commit = BoxLayout(orientation='vertical', padding=dp(15), spacing=dp(10))
                        
                        # 1. Champ de saisie tout en haut
                        ti_commit = TextInput(hint_text="Ex: Modification de l'événement", multiline=False, size_hint_y=None, height=dp(40), background_color=(1, 1, 1, 1), foreground_color=(0.1, 0.1, 0.1, 1), cursor_color=(0.1, 0.1, 0.1, 1))
                        content_commit.add_widget(ti_commit)
                        
                        # 2. Bouton de confirmation juste en dessous
                        btn_valider_commit = Button(text="Confirmer l'enregistrement", size_hint_y=None, height=dp(45), background_normal="", background_color=(0.15, 0.65, 0.35, 1), color=(1, 1, 1, 1), bold=True)
                        content_commit.add_widget(btn_valider_commit)
                        
                        # 3. Label explicatif placé en dessous
                        content_commit.add_widget(Label(text="[b]Motif de la modification[/b]", markup=True, size_hint_y=None, height=dp(30), color=(0.15, 0.45, 0.25, 1)))
                        
                        content_commit.add_widget(Widget())
                        
                        popup_commit = Popup(title="Modification", content=content_commit, size_hint=(0.8, 0.4), separator_height=0)
                        
                        def valider_avec_commit(instance):
                            msg = ti_commit.text.strip() or "Mise à jour de l'événement"
                            popup_commit.dismiss()
                            executer_sauvegarde(msg)
                            
                        btn_valider_commit.bind(on_release=valider_avec_commit)
                        popup_commit.open()
                    else:
                        executer_sauvegarde("Création de l'événement")

                btn_save.bind(on_release=save_evenement)
                dynamic_container.add_widget(btn_save)

        # Création des boutons d'onglets supérieurs
        for t in tabs:
            btn = Button(
                text=t.capitalize(),
                bold=True,
                background_normal="",
                background_color=(0.2, 0.6, 0.3, 1) if t == current_type else (0.85, 0.85, 0.88, 1),
                color=(1, 1, 1, 1) if t == current_type else (0.3, 0.3, 0.3, 1)
            )
            btn.bind(on_release=lambda x, tab=t: rafraichir_formulaire(tab))
            tab_buttons[t] = btn
            tab_layout.add_widget(btn)

        content.add_widget(tab_layout)
        content.add_widget(dynamic_container)

        # --- PARAMÉTRAGE DE LA POPUP ---
        popup = Popup(
            title="", 
            title_size=0, 
            content=content, 
            size_hint=(0.92, 0.88), 
            separator_height=0,
            background=""
        )
        popup.background_color = (0, 0, 0, 0.6)  # Fond assombri derrière la popup
        
        popup_ref.append(popup)
        rafraichir_formulaire(current_type)
        popup.open()