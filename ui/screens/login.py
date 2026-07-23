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
from kivy.core.clipboard import Clipboard
import webbrowser

import hashlib
import requests

class LargeSpinnerOption(SpinnerOption):
    """Classe personnalisée pour un menu déroulant adapté aux doigts."""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.height = dp(70)
        self.font_size = '20sp'

class LoginScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.layout = BoxLayout(orientation='vertical', padding=dp(20), spacing=dp(15))
        
        # Titre
        self.layout.add_widget(Label(text="Ajouter un accès vestiaire", font_size='22sp', bold=True, size_hint_y=None, height=dp(50)))
        
        # Label d'état
        self.active_label = Label(text="", font_size='18sp', size_hint_y=None, height=dp(40))
        self.layout.add_widget(self.active_label)
        
        # Spinner
        self.layout.add_widget(Label(text="Choisir la catégorie :", font_size='18sp', size_hint_y=None, height=dp(30)))
        self.cat_spinner = Spinner(
            text="Sélectionner...", 
            values=[], 
            font_size='18sp', 
            size_hint_y=None, 
            height=dp(60),
            option_cls=LargeSpinnerOption
        )
        self.layout.add_widget(self.cat_spinner)
        
        # TextInput
        # TextInput Nom du Parent
        self.layout.add_widget(Label(text="Votre nom :", font_size='18sp', size_hint_y=None, height=dp(30)))
        self.name_input = TextInput(hint_text="Prénom NOM", font_size='18sp', multiline=False, size_hint_y=None, height=dp(60))
        self.layout.add_widget(self.name_input)
        
        # Pré-remplir avec la valeur existante dans le fichier .ini
        # Pré-remplir avec la valeur existante dans le fichier .ini
        app = App.get_running_app()
        # On vérifie si la section existe pour éviter une erreur
        if app.config.has_section('User'):
            nom_sauvegarde = app.config.get('User', 'nom_parent', fallback='')
            if nom_sauvegarde:
                self.name_input.text = nom_sauvegarde
        
        self.layout.add_widget(Label(text="Mot de passe :", font_size='18sp', size_hint_y=None, height=dp(30)))
        self.pwd_input = TextInput(hint_text="Entrez le mot de passe", font_size='18sp', password=True, multiline=False, size_hint_y=None, height=dp(60))
        self.layout.add_widget(self.pwd_input)
        
        # Bouton Valider en GRAS
        btn_valider = Button(text="[b]Valider l'accès[/b]", markup=True, font_size='18sp', size_hint_y=None, height=dp(60))
        btn_valider.bind(on_release=self.check_login)
        self.layout.add_widget(btn_valider)
        
        # Note
        self.layout.add_widget(Label(
            text="La gestion des accès se fait\ndans la page Paramètres.", 
            font_size='16sp', color=(0.7, 0.7, 0.7, 1), italic=True,
            size_hint_y=None, height=dp(60), halign='center'
        ))
        
        #############################################################################
        # Acceptation CGU / Politique confidentialité
        cgu_layout = BoxLayout(
            orientation='horizontal',
            size_hint_y=None,
            height=dp(70),
            spacing=dp(10)
        )
        
        self.cgu_checkbox = CheckBox(
            size_hint=(None, None),
            size=(dp(40), dp(40))
        )
        
        self.cgu_checkbox.bind(
            active=self.update_cgu_state
        )
        
        cgu_layout.add_widget(self.cgu_checkbox)
        
        
        self.cgu_label = Label(
            text=(
                "J'ai lu et j'accepte les "
                "[ref=cgu][u]Conditions Générales d'Utilisation[/u][/ref]\n"
                "et la "
                "[ref=privacy][u]Politique de confidentialité[/u][/ref]\n"
                "du FCVV."
            ),
            markup=True,
            font_size='14sp',
            halign="left",
            valign="middle"
        )
        
        self.cgu_label.bind(
            size=self.cgu_label.setter('text_size')
        )
        
        self.cgu_label.bind(
            on_ref_press=self.open_legal_page
        )
        
        cgu_layout.add_widget(self.cgu_label)
        
        self.layout.add_widget(cgu_layout)
        
        #########################################################################
        
        # Bouton Aller au Vestiaire en GRAS
        btn_go = Button(text="[b]Aller au Vestiaire[/b]", markup=True, font_size='18sp', size_hint_y=None, height=dp(60), background_color=(0, 0.7, 0, 1))
        btn_go.disabled = True

        self.btn_go_vestiaire = btn_go
        
        self.cgu_checkbox.bind(
            active=self.enable_vestiaire_button
        )
        btn_go.bind(on_release=self.go_to_vestiaire)
        self.layout.add_widget(btn_go)
        
        # Ressort pour remonter le tout
        self.layout.add_widget(BoxLayout()) 
        
        self.add_widget(self.layout)
        
    def enable_vestiaire_button(self, checkbox, value):
        self.btn_go_vestiaire.disabled = not value
        
    def update_cgu_state(self, checkbox, value):
        app = App.get_running_app()
    
        app.config.set(
            'User',
            'vestiaire_cgu_accept',
            '1' if value else '0'
        )
    
        app.config.write()
            
    def open_legal_page(self, instance, ref):

        if ref == "cgu":
    
            url = "https://sites.google.com/view/fcvv-application/conditions-utilisation"
    
        elif ref == "privacy":
    
            url = "https://sites.google.com/view/fcvv-application/confidentialite"
    
        else:
            return
    
        webbrowser.open(url)
    
    def go_to_vestiaire(self, instance):

        app = App.get_running_app()

        # Vérification acceptation CGU
        accepte = app.config.get(
            'User',
            'vestiaire_cgu_accept',
            fallback='0'
        )

        if accepte != '1':
            self.show_popup(
                "Conditions obligatoires",
                "Vous devez accepter les CGU et la politique de confidentialité\navant d'accéder au vestiaire."
            )
            return

        root = app.root

        if hasattr(root, 'switch_screen'):
            root.switch_screen('vestiaire')
        else:
            print(f"[ERROR] switch_screen introuvable sur {root}.")
    
    def on_pre_enter(self):
        # Le texte est effacé avant même que l'utilisateur ne voie l'écran
        self.pwd_input.text = ""

    def on_enter(self):
        self.pwd_input.text = ""
        app = App.get_running_app()
        if app.authorized_vestiaires:
            self.active_label.text = f"Connecté à : {', '.join(app.authorized_vestiaires)}"
        else:
            self.active_label.text = "Aucune catégorie active."
            
        vestiaires = app.app_config.get("fcvv", {}).get("appli", {}).get("vestiaire", [])
        self.cat_spinner.values = [item.get("categorie") for item in vestiaires if item.get("categorie")]
        
        # Restaurer l'état d'acceptation CGU
        accepte = app.config.get(
            'User',
            'vestiaire_cgu_accept',
            fallback='0'
        )

        self.cgu_checkbox.active = (accepte == '1')
    
    def enregistrer_parent_firebase(self, nom):
        try:
            r = requests.post(
                f"https://fcvv-api.onrender.com/users/register",
                json={
                    "nom": nom
                },
                timeout=5
            )
            if r.status_code == 200:
                print(f"Parent enregistre : {r.json()}")
            else:
                print(
                    f"Erreur enregistrement parent : "
                    f"{r.status_code} {r.text}"
                )
        except Exception as e:
            print(f"Erreur connexion enregistrement parent : {e}")

    def check_login(self, instance):
        app = App.get_running_app()
        cat = self.cat_spinner.text
        pwd = self.pwd_input.text.strip()
        nom = self.name_input.text.strip()
        nom = " ".join(nom.upper().split())
        
        if not nom or not pwd:
            self.show_popup("Erreur", "Veuillez remplir votre nom et le mot de passe.")
            return

        # Calcul du hash de la saisie
        saisie_hash = hashlib.sha256(pwd.encode()).hexdigest()
        
        # Récupération de la config globale (pour trouver le hash du super admin)
        vestiaires_cfg = app.app_config.get("fcvv", {}).get("appli", {}).get("vestiaire", [])
        
        # --- 1. Vérification SUPER_ADMIN ---
        super_admin_item = next((item for item in vestiaires_cfg if "password_super_admin_hash" in item), None)
        
        if super_admin_item and saisie_hash == super_admin_item["password_super_admin_hash"]:
            app.config.set('User', 'nom_parent', nom)
            self.enregistrer_parent_firebase(nom)
            
            # Récupérer TOUTES les catégories valides dans le YAML
            toutes_cats = []
            for item in vestiaires_cfg:
                cat_nom = item.get("categorie")
                if cat_nom:
                    toutes_cats.append(cat_nom)
                    
                    # RÉCUPÉRATION DU HASH RÉEL DE LA CATÉGORIE
                    # On cherche le hash admin dans l'objet catégorie spécifique
                    cat_hash = item.get("password_admin_hash") or item.get("password_hash")
                    
                    # On enregistre avec le VRAI hash de la catégorie
                    app.add_authorized_vestiaire(cat_nom, "ADMIN", cat_hash, save=False)
            
            # Mise à jour finale
            app.authorized_vestiaires = toutes_cats
            app.config.set('User', 'authorized_list', ','.join(toutes_cats))
            app.config.set('User', 'vestiaire_auth', '1')
            app.config.write()
            
            app.gerer_abonnements_fcm(toutes_cats)
            self.show_popup("Succès", "Mode SUPER_ADMIN : Accès total accordé.")
            return

        # 2. TEST STANDARD (Si pas Super Admin)
        if cat == "Sélectionner...":
            self.show_popup("Erreur", "Veuillez choisir une catégorie.")
            return

        role = app.check_vestiaire_password(cat, pwd)
        if role:
            app.config.set('User', 'nom_parent', nom)
            self.enregistrer_parent_firebase(nom)
            app.add_authorized_vestiaire(cat, role, saisie_hash, save=True)
            app.gerer_abonnements_fcm(app.authorized_vestiaires)
            
            self.show_popup("Succès", f"Accès {role} accordé pour {cat}.")
            self.active_label.text = f"Connecté : {', '.join(app.authorized_vestiaires)}"
        else:
            self.show_popup("Erreur", "Mot de passe incorrect.")

    def show_popup(self, title, message):
        # On définit un Label avec une police plus grande
        content_label = Label(text=message, font_size='18sp')
        
        # On crée le popup avec ce contenu
        popup = Popup(
            title=title, 
            content=content_label, 
            size_hint=(0.8, 0.3)
        )
        popup.open()