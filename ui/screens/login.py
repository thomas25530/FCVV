# -*- coding: utf-8 -*-
from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.spinner import Spinner, SpinnerOption
from kivy.uix.popup import Popup
from kivy.app import App
from kivy.metrics import dp

from kivy.uix.checkbox import CheckBox
from kivy.uix.scrollview import ScrollView
import webbrowser

import hashlib
import requests
import os
import yaml
import threading
from kivy.utils import platform
from kivy.clock import Clock

# --- IMPORTS GRAPHIQUES ---
from kivy.graphics import Color, Rectangle, RoundedRectangle, Line


class LargeSpinnerOption(SpinnerOption):
    """Option du menu déroulant (liste ouverte)."""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.height = dp(55)
        self.font_size = '17sp'
        # Désactiver impérativement les textures par défaut Kivy
        self.background_normal = ''
        self.background_down = ''
        self.background_color = (0, 0, 0, 0)
        self.color = (0.1, 0.1, 0.15, 1)

        with self.canvas.before:
            # Fond blanc cassé pour les éléments de la liste
            Color(0.95, 0.95, 0.96, 1)
            self.rect_bg = Rectangle(pos=self.pos, size=self.size)
            # Ligne de séparation grise
            Color(0.8, 0.8, 0.85, 1)
            self.line_sep = Rectangle(pos=self.pos, size=(self.width, dp(1)))

        self.bind(pos=self._update_graphics, size=self._update_graphics)

    def _update_graphics(self, instance, value):
        self.rect_bg.pos = self.pos
        self.rect_bg.size = self.size
        self.line_sep.pos = self.pos
        self.line_sep.size = (self.width, dp(1))


class CustomSpinner(Spinner):
    """Bouton du Spinner principal stylisé en gris clair visible."""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Supprime complètement l'image de fond native de Kivy
        self.background_normal = ''
        self.background_down = ''
        self.background_color = (0, 0, 0, 0) 
        
        # Couleur du texte en sombre pour contraster sur le gris clair
        self.color = (0.1, 0.1, 0.15, 1)
        self.bold = True

        with self.canvas.before:
            # VRAI GRIS CLAIR BIEN VISIBLE (R:0.78, G:0.78, B:0.80)
            Color(0.78, 0.78, 0.80, 1)
            self.bg_rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(12)])
            
            # Contour légèrement plus foncé pour marquer les bords
            Color(0.55, 0.55, 0.60, 1)
            self.border_rect = Line(rounded_rectangle=(self.x, self.y, self.width, self.height, dp(12)), width=1.5)

        self.bind(pos=self._update_shape, size=self._update_shape)

    def _update_shape(self, instance, value):
        self.bg_rect.pos = self.pos
        self.bg_rect.size = self.size
        self.border_rect.rounded_rectangle = (self.x, self.y, self.width, self.height, dp(12))


class LoginScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.layout = BoxLayout(orientation='vertical', padding=dp(20), spacing=dp(15))
        
        # Titre
        self.layout.add_widget(Label(text="Ajouter un accès vestiaire", font_size='22sp', bold=True, size_hint_y=None, height=dp(50)))
        
        # Label d'état
        self.active_label = Label(text="", font_size='18sp', size_hint_y=None, height=dp(40))
        self.layout.add_widget(self.active_label)
        
        # Spinner Personnalisé
        self.layout.add_widget(Label(text="Choisir la catégorie :", font_size='18sp', size_hint_y=None, height=dp(30)))
        self.cat_spinner = CustomSpinner(
            text="Sélectionner une catégorie...", 
            values=[], 
            font_size='17sp', 
            size_hint_y=None, 
            height=dp(55),
            option_cls=LargeSpinnerOption
        )
        self.layout.add_widget(self.cat_spinner)
        
        # TextInput Nom du Parent
        self.layout.add_widget(Label(text="Votre nom :", font_size='18sp', size_hint_y=None, height=dp(30)))
        self.name_input = TextInput(hint_text="Prénom NOM", font_size='18sp', multiline=False, size_hint_y=None, height=dp(60))
        self.layout.add_widget(self.name_input)
        
        app = App.get_running_app()
        if app.config.has_section('User'):
            nom_sauvegarde = app.config.get('User', 'nom_parent', fallback='')
            if nom_sauvegarde:
                self.name_input.text = nom_sauvegarde
        
        self.layout.add_widget(Label(text="Mot de passe :", font_size='18sp', size_hint_y=None, height=dp(30)))
        self.pwd_input = TextInput(hint_text="Entrez le mot de passe", font_size='18sp', password=True, multiline=False, size_hint_y=None, height=dp(60))
        self.layout.add_widget(self.pwd_input)
        
        # Bouton Valider
        btn_valider = Button(text="[b]Valider l'accès[/b]", markup=True, font_size='18sp', size_hint_y=None, height=dp(60))
        btn_valider.bind(on_release=self.check_login)
        self.layout.add_widget(btn_valider)
        
        # Note
        self.layout.add_widget(Label(
            text="La gestion des accès se fait\ndans la page Paramètres.", 
            font_size='16sp', color=(0.7, 0.7, 0.7, 1), italic=True,
            size_hint_y=None, height=dp(60), halign='center'
        ))
        
        # Acceptation CGU
        cgu_layout = BoxLayout(
            orientation='horizontal',
            size_hint_y=None,
            height=dp(70),
            spacing=dp(10)
        )
        
        self.cgu_checkbox = CheckBox(
            size_hint=(None, None),
            size=(dp(30), dp(30)),
            color=(0, 0, 0, 1),
            pos_hint={'center_y': 0.5}
        )

        BOX_SIZE = dp(16)
        with self.cgu_checkbox.canvas.before:
            Color(1, 1, 1, 1)
            self.cgu_checkbox_rect = Rectangle(
                pos=(
                    self.cgu_checkbox.center_x - BOX_SIZE / 2,
                    self.cgu_checkbox.center_y - BOX_SIZE / 2
                ), 
                size=(BOX_SIZE, BOX_SIZE)
            )

        def update_rect(instance, value):
            self.cgu_checkbox_rect.pos = (
                instance.center_x - BOX_SIZE / 2,
                instance.center_y - BOX_SIZE / 2
            )

        self.cgu_checkbox.bind(pos=update_rect, size=update_rect)
        self.cgu_checkbox.bind(active=self.update_cgu_state)
        cgu_layout.add_widget(self.cgu_checkbox)
        
        self.cgu_label = Label(
            text=(
                "J'ai lu et j'accepte les "
                "[ref=cgu][u][color=#FFFF00]Conditions Générales d'Utilisation[/color][/u][/ref]\n"
                "et la "
                "[ref=privacy][u][color=#FFFF00]Politique de confidentialité[/color][/u][/ref] du FCVV."
            ),
            markup=True,
            font_size='14sp',
            halign="left",
            valign="middle"
        )
        self.cgu_label.bind(size=self.cgu_label.setter('text_size'))
        self.cgu_label.bind(on_ref_press=self.open_legal_page)
        cgu_layout.add_widget(self.cgu_label)
        self.layout.add_widget(cgu_layout)
        
        # Bouton Aller au Vestiaire
        btn_go = Button(text="[b]Aller au Vestiaire[/b]", markup=True, font_size='18sp', size_hint_y=None, height=dp(60), background_color=(0, 0.7, 0, 1))
        btn_go.disabled = True
        self.btn_go_vestiaire = btn_go
        
        self.cgu_checkbox.bind(active=self.enable_vestiaire_button)
        btn_go.bind(on_release=self.go_to_vestiaire)
        self.layout.add_widget(btn_go)
        
        self.layout.add_widget(BoxLayout()) 
        self.add_widget(self.layout)
        
    def enable_vestiaire_button(self, checkbox, value):
        self.btn_go_vestiaire.disabled = not value
        
    def update_cgu_state(self, checkbox, value):
        app = App.get_running_app()
        app.config.set('User', 'vestiaire_cgu_accept', '1' if value else '0')
        app.config.write()
            
    def open_legal_page(self, instance, ref):
        url = "https://sites.google.com/view/fcvv-application/conditions-utilisation" if ref == "cgu" else "https://sites.google.com/view/fcvv-application/confidentialite"
        webbrowser.open(url)
    
    def go_to_vestiaire(self, instance):
        app = App.get_running_app()
        accepte = app.config.get('User', 'vestiaire_cgu_accept', fallback='0')
        if accepte != '1':
            self.show_popup("Conditions obligatoires", "Vous devez accepter les CGU avant d'accéder au vestiaire.")
            return

        root = app.root
        if hasattr(root, 'switch_screen'):
            root.switch_screen('vestiaire')
        else:
            print(f"[ERROR] switch_screen introuvable sur {root}.")
    
    def on_pre_enter(self):
        self.pwd_input.text = ""

    def on_enter(self):
        self.pwd_input.text = ""
        app = App.get_running_app()
        if app.authorized_vestiaires:
            self.active_label.text = f"Connecté à : {', '.join(app.authorized_vestiaires)}"
        else:
            self.active_label.text = "Aucune catégorie active."
            
        vestiaires = app.app_config.get("fcvv", {}).get("appli", {}).get("vestiaire", [])
        
        cats = [item.get("categorie") for item in vestiaires if item.get("categorie")]
        # Utilisation de la puce ASCII standard compatible avec 100% des téléphones et ordinateurs
        self.cat_spinner.values = [f"{cat}" for cat in cats]
        
        accepte = app.config.get('User', 'vestiaire_cgu_accept', fallback='0')
        is_accepted = (accepte == '1')
        self.cgu_checkbox.active = is_accepted
        self.btn_go_vestiaire.disabled = not is_accepted
    
    def enregistrer_parent_firebase(self, nom, categorie, joueur_associe=None):
        try:
            payload = {"nom": nom, "categorie": categorie}
            if joueur_associe:
                payload["joueur_associe"] = joueur_associe
            
            is_windows = (platform == 'win')
            r = requests.post("https://fcvv-api.onrender.com/users/register", json=payload, timeout=30, verify=not is_windows)
        except Exception as e:
            print(f"[DEBUG LOGIN] EXCEPTION connexion enregistrement parent : {e}")

    def demander_joueur_associe(self, nom, cat_selectionnee, callback_final):
        app = App.get_running_app()
        vestiaires = app.app_config.get("fcvv", {}).get("appli", {}).get("vestiaire", [])
        cat_item = next((item for item in vestiaires if str(item.get("categorie")).strip().lower() == str(cat_selectionnee).strip().lower()), {})
        path = os.path.join(getattr(app, "user_data_dir", "."), f"data_{cat_selectionnee}.yaml")

        def afficher_popup_selection(liste_joueurs):
            noms_joueurs = sorted([f"{j.get('nom', '').upper()} {j.get('prenom', '')}".strip() for j in liste_joueurs if isinstance(j, dict)])
            
            content = BoxLayout(orientation='vertical', padding=dp(20), spacing=dp(10))
            with content.canvas.before:
                Color(0.95, 0.95, 0.97, 1)
                self_bg = RoundedRectangle(pos=content.pos, size=content.size, radius=[dp(20)])
            content.bind(
                pos=lambda obj, val: setattr(self_bg, 'pos', val),
                size=lambda obj, val: setattr(self_bg, 'size', val)
            )

            lbl_titre_popup = Label(
                text=f"[b]Catégorie : {cat_selectionnee}[/b]\nCochez vos rôles ou vos joueurs :",
                markup=True,
                size_hint_y=None,
                height=dp(50),
                font_size=dp(16),
                color=(0.1, 0.1, 0.15, 1),
                halign="center"
            )
            lbl_titre_popup.bind(size=lbl_titre_popup.setter('text_size'))
            content.add_widget(lbl_titre_popup)
            
            scroll = ScrollView(bar_width=0, size_hint=(1, 1))
            list_layout = BoxLayout(orientation='vertical', spacing=dp(10), size_hint_y=None)
            list_layout.bind(minimum_height=list_layout.setter('height'))
            
            checkboxes_dict = {}
            
            def toggle_bold_label(checkbox, value, label_widget, original_text):
                if value:
                    label_widget.text = f"[b]{original_text}[/b]"
                else:
                    label_widget.text = original_text

            box_coach = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(40), spacing=dp(10))
            chk_coach = CheckBox(size_hint_x=None, width=dp(40), color=(0.2, 0.2, 0.2, 1), pos_hint={'center_y': 0.5})
            
            prenom_utilisateur = nom.strip().split()[0] if nom else "Coach"
            nom_formate = prenom_utilisateur.replace(" ", "_")
            key_coach = f"COACH_{nom_formate}"
            
            checkboxes_dict[key_coach] = chk_coach
            box_coach.add_widget(chk_coach)
            
            lbl_coach = Label(text="COACH / STAFF", markup=True, font_size='16sp', color=(0.2, 0.2, 0.25, 1), halign='left', valign='middle')
            lbl_coach.bind(size=lambda lbl, sz: setattr(lbl, 'text_size', sz))
            chk_coach.bind(active=lambda chk, val: toggle_bold_label(chk, val, lbl_coach, "COACH / STAFF"))
            box_coach.add_widget(lbl_coach)
            list_layout.add_widget(box_coach)
            
            if noms_joueurs:
                for j_nom in noms_joueurs:
                    box_j = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(40), spacing=dp(10))
                    chk = CheckBox(size_hint_x=None, width=dp(40), color=(0.2, 0.2, 0.2, 1), pos_hint={'center_y': 0.5})
                    checkboxes_dict[j_nom] = chk
                    box_j.add_widget(chk)
                    
                    lbl_j = Label(text=j_nom, markup=True, font_size='16sp', color=(0.2, 0.2, 0.25, 1), halign='left', valign='middle')
                    lbl_j.bind(size=lambda lbl, sz: setattr(lbl, 'text_size', sz))
                    chk.bind(active=lambda chk, val, l=lbl_j, t=j_nom: toggle_bold_label(chk, val, l, t))
                    
                    box_j.add_widget(lbl_j)
                    list_layout.add_widget(box_j)
            else:
                box_vide = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(40))
                box_vide.add_widget(Label(text="[i]Aucun joueur dans cette catégorie[/i]", markup=True, font_size='14sp', color=(0.8, 0.2, 0.2, 1)))
                list_layout.add_widget(box_vide)
                
            scroll.add_widget(list_layout)
            content.add_widget(scroll)
            
            btn_valider_liaison = Button(
                text="Valider la sélection", 
                font_size='16sp', 
                size_hint_y=None, 
                height=dp(45),
                background_normal="",
                background_color=(0.15, 0.65, 0.35, 1), 
                color=(1, 1, 1, 1), 
                bold=True
            )
            
            def on_valider(instance):
                selectionnes = [cle for cle, chk in checkboxes_dict.items() if chk.active]
                app = App.get_running_app()
                
                if not selectionnes:
                    self.enregistrer_parent_firebase(nom, cat_selectionnee, joueur_associe=None)
                else:
                    for item_choisi in selectionnes:
                        self.enregistrer_parent_firebase(nom, cat_selectionnee, joueur_associe=item_choisi)
                    
                    if hasattr(app, "set_joueur_associe_pour_cat"):
                        tous_les_choix = ", ".join(selectionnes)
                        app.set_joueur_associe_pour_cat(cat_selectionnee, tous_les_choix)
                    
                popup.dismiss()
                callback_final()
                
            btn_valider_liaison.bind(on_release=on_valider)
            content.add_widget(btn_valider_liaison)
            
            popup = Popup(
                title="", 
                content=content, 
                size_hint=(0.85, 0.7), 
                auto_dismiss=False,
                separator_height=0,
                background="",
                background_color=(0, 0, 0, 0)
            )
            popup.open()

        if cat_item.get("file_id"):
            loading_content = BoxLayout(orientation='vertical', padding=dp(15), spacing=dp(10))
            with loading_content.canvas.before:
                Color(0.95, 0.95, 0.97, 1)
                load_bg = RoundedRectangle(pos=loading_content.pos, size=loading_content.size, radius=[dp(20)])
            loading_content.bind(
                pos=lambda obj, val: setattr(load_bg, 'pos', val),
                size=lambda obj, val: setattr(load_bg, 'size', val)
            )
            
            msg_chargement = "Vérification des mises à jour de l'équipe..." if os.path.exists(path) else "Téléchargement des données de l'équipe..."
            
            loading_content.add_widget(Label(text=msg_chargement, font_size='16sp', color=(0.1, 0.1, 0.15, 1), halign="center"))
            loading_popup = Popup(
                title="", 
                content=loading_content, 
                size_hint=(0.7, 0.3), 
                auto_dismiss=False, 
                separator_height=0, 
                background="",
                background_color=(0, 0, 0, 0)
            )
            loading_popup.open()

            def background_download():
                final_joueurs = []
                try:
                    url = f"https://docs.google.com/uc?id={cat_item.get('file_id')}&export=download"
                    is_windows = (platform == 'win')
                    r = requests.get(url, timeout=10, verify=not is_windows)
                    
                    if r.status_code == 200 and b"<html" not in r.content[:100].lower():
                        new_content = r.content
                        old_content = b""
                        if os.path.exists(path):
                            with open(path, "rb") as f:
                                old_content = f.read()
                        
                        if hashlib.md5(new_content).hexdigest() != hashlib.md5(old_content).hexdigest():
                            print(f"[CONFIG] Changement detecte pour {cat_selectionnee}, mise a jour du fichier local.")
                            with open(path, "wb") as f:
                                f.write(new_content)
                        else:
                            print(f"[CONFIG] Fichier {cat_selectionnee} inchange.")
                    
                    if os.path.exists(path):
                        with open(path, "r", encoding="utf-8") as f:
                            data_yaml = yaml.safe_load(f) or {}
                            final_joueurs = data_yaml.get("tous_les_joueurs", [])
                except Exception as e:
                    print(f"[DEBUG LOGIN] Erreur reseau/telechargement : {e}")
                    if os.path.exists(path):
                        try:
                            with open(path, "r", encoding="utf-8") as f:
                                data_yaml = yaml.safe_load(f) or {}
                                final_joueurs = data_yaml.get("tous_les_joueurs", [])
                        except Exception:
                            pass
                
                if not final_joueurs:
                    final_joueurs = cat_item.get("tous_les_joueurs", [])

                def finish_loading(dt):
                    loading_popup.dismiss()
                    afficher_popup_selection(final_joueurs)
                
                Clock.schedule_once(finish_loading)

            threading.Thread(target=background_download, daemon=True).start()
        else:
            liste_joueurs = cat_item.get("tous_les_joueurs", [])
            if not liste_joueurs and os.path.exists(path):
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        data_yaml = yaml.safe_load(f) or {}
                        liste_joueurs = data_yaml.get("tous_les_joueurs", [])
                except Exception as e:
                    print(f"[DEBUG LOGIN] Erreur lecture YAML local : {e}")
            afficher_popup_selection(liste_joueurs)

    def check_login(self, instance):
        app = App.get_running_app()
        # Nettoyage propre de la puce pour isoler le nom de la catégorie
        cat = self.cat_spinner.text.replace("•", "").strip()
        pwd = self.pwd_input.text.strip()
        nom = self.name_input.text.strip()

        if not nom or not pwd:
            self.show_popup("Erreur", "Veuillez remplir votre nom et le mot de passe.")
            return

        saisie_hash = hashlib.sha256(pwd.encode()).hexdigest()
        vestiaires_cfg = app.app_config.get("fcvv", {}).get("appli", {}).get("vestiaire", [])
        
        super_admin_item = next((item for item in vestiaires_cfg if "password_super_admin_hash" in item), None)
        if super_admin_item and saisie_hash == super_admin_item["password_super_admin_hash"]:
            app.config.set('User', 'nom_parent', nom)
            self.enregistrer_parent_firebase(nom, "TOUTES", joueur_associe="SUPER_ADMIN")
            
            toutes_cats = []
            for item in vestiaires_cfg:
                cat_nom = item.get("categorie")
                if cat_nom:
                    toutes_cats.append(cat_nom)
                    cat_hash = item.get("password_admin_hash") or item.get("password_hash")
                    app.add_authorized_vestiaire(cat_nom, "ADMIN", cat_hash, save=False)
            
            app.authorized_vestiaires = toutes_cats
            app.config.set('User', 'authorized_list', ','.join(toutes_cats))
            app.config.set('User', 'vestiaire_auth', '1')
            app.config.write()
            app.gerer_abonnements_fcm(toutes_cats)
            self.show_popup("Succès", "Mode SUPER_ADMIN : Accès total accordé.")
            return

        if cat == "Sélectionner une catégorie...":
            self.show_popup("Erreur", "Veuillez choisir une catégorie.")
            return

        role = app.check_vestiaire_password(cat, pwd)

        if role:
            def finaliser_connexion():
                app.config.set('User', 'nom_parent', nom)
                app.add_authorized_vestiaire(cat, role, saisie_hash, save=True)
                app.gerer_abonnements_fcm(app.authorized_vestiaires)
                self.show_popup("Succès", f"Accès {role} accordé pour {cat}.")
                self.active_label.text = f"Connecté : {', '.join(app.authorized_vestiaires)}"

            self.demander_joueur_associe(nom, cat, finaliser_connexion)
        else:
            self.show_popup("Erreur", "Mot de passe incorrect.")

    def show_popup(self, title, message):
        content = BoxLayout(orientation='vertical', padding=dp(20), spacing=dp(10))
        with content.canvas.before:
            Color(0.95, 0.95, 0.97, 1)
            pop_bg = RoundedRectangle(pos=content.pos, size=content.size, radius=[dp(20)])
        content.bind(
            pos=lambda obj, val: setattr(pop_bg, 'pos', val),
            size=lambda obj, val: setattr(pop_bg, 'size', val)
        )

        if title:
            lbl_title = Label(text=f"[b]{title}[/b]", markup=True, font_size=dp(18), size_hint_y=None, height=dp(30), color=(0.1, 0.1, 0.15, 1), halign="center")
            content.add_widget(lbl_title)

        content.add_widget(Label(text=message, font_size=dp(16), color=(0.2, 0.2, 0.25, 1), halign="center"))
        
        popup = Popup(
            title="", 
            content=content, 
            size_hint=(0.8, 0.3), 
            separator_height=0, 
            background="",
            background_color=(0, 0, 0, 0)
        )
        popup.open()