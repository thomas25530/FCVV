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
from kivy.core.window import Window

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
        if app and hasattr(app, 'config') and app.config.has_section('User'):
            nom_sauvegarde = app.config.get('User', 'nom_parent', fallback='')
            if nom_sauvegarde:
                self.name_input.text = nom_sauvegarde
        # TextInput Mot de passe
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
        if not app:
            return

        accepte = app.config.get('User', 'vestiaire_cgu_accept', fallback='0')
        if accepte != '1':
            self.show_popup("Conditions obligatoires", "Vous devez accepter les CGU avant d'accéder au vestiaire.")
            return

        root = app.root
        if not root:
            return

        # 1. Reconstruire le menu latéral pour intégrer la nouvelle catégorie
        if hasattr(root, 'rebuild_menu'):
            root.rebuild_menu()

        # 2. Rafraîchir l'écran du vestiaire s'il existe déjà dans le ScreenManager
        if hasattr(root, 'sm') and root.sm.has_screen('vestiaire'):
            vestiaire_screen = root.sm.get_screen('vestiaire')
            if hasattr(vestiaire_screen, 'update_ui'):
                vestiaire_screen.update_ui()
            elif hasattr(vestiaire_screen, 'build_tabs'):
                vestiaire_screen.build_tabs()

        # 3. Effectuer la redirection
        if hasattr(root, 'switch_screen'):
            root.switch_screen('vestiaire')
        else:
            print(f"[ERROR] switch_screen introuvable sur {root}.")

    def reset_name_input(self):
        try:
            self.name_input.focus = False
            self.name_input.disabled = False
            self.name_input.readonly = False
            self.name_input.text = ""
            self.name_input.cursor = (0, 0)
        except Exception as e:
            print(f"[RESET ERROR] reset_name_input : {e}")
    
    def on_pre_enter(self):
        app = App.get_running_app()
        self.name_input.focus = False
        self.name_input.disabled = False
        self.name_input.readonly = False
        self.name_input.text = ""
        if hasattr(app, "config"):
            app.config.read(app.config.filename)
        nom_existant = app.config.get("User", "nom_parent", fallback="").strip() if app.config.has_section("User") else ""
        if nom_existant:
            self.name_input.text = nom_existant
            self.name_input.readonly = True
            self.name_input.disabled = True

    def on_enter(self):
        app = App.get_running_app()
        self.pwd_input.text = ""
        self.pwd_input.focus = False

        # 1. Charger les catégories disponibles
        vestiaires = app.app_config.get("fcvv", {}).get("appli", {}).get("vestiaire", [])
        cats = [str(item.get("categorie")) for item in vestiaires if item.get("categorie")]
        self.cat_spinner.values = cats

        # 2. Vérifier si une catégorie spécifique a été pré-sélectionnée (ex: depuis le menu)
        target_cat = getattr(self, "target_category", None)
        if target_cat and target_cat in cats:
            self.cat_spinner.text = target_cat
            self.target_category = None  # Réinitialiser après utilisation
        else:
            self.cat_spinner.text = "Sélectionner une catégorie..."

        # 3. État des vestiaires connectés
        if app.authorized_vestiaires:
            self.active_label.text = f"Connecté à : {', '.join(app.authorized_vestiaires)}"
        else:
            self.active_label.text = "Aucune catégorie active."

        # 4. État du bouton et CGU
        is_accepted = (app.config.get("User", "vestiaire_cgu_accept", fallback="0") == "1")
        self.cgu_checkbox.active = is_accepted
        self.btn_go_vestiaire.disabled = not is_accepted

    def set_category(self, cat_name):
        """Méthode appelée depuis RootLayout.switch_screen pour forcer la catégorie."""
        self.target_category = cat_name
        if hasattr(self, 'cat_spinner'):
            self.cat_spinner.text = cat_name

    def enregistrer_parent_firebase(
        self,
        nom,
        categorie,
        liste_joueurs_associes,
        callback_reussite,
        demande_admin=False
    ):
        """
        Envoie UNE SEULE demande d'inscription à l'API Render.
    
        IMPORTANT :
        - aucune modification du .ini ici avant la réponse serveur ;
        - le callback_reussite() n'est appelé QUE si HTTP 200 ;
        - le choix des joueurs est également enregistré localement
          uniquement après HTTP 200.
        """
        def _thread_register():
            is_windows = (platform == "win")
            url = "https://fcvv-api.onrender.com/users/register"
            # Nettoyage de la liste des joueurs
            joueurs_associes = [
                str(j).strip()
                for j in (liste_joueurs_associes or [])
                if str(j).strip()
            ]
            app = App.get_running_app()
            fcm_token = None
            try:
                if getattr(app, "notifier", None):
                    fcm_token = app.notifier.get_fcm_token()
                if fcm_token:
                    print(
                        f"[FCM REGISTER] Token recupere : "
                        f"{str(fcm_token)[:25]}..."
                    )
                else:
                    print("[FCM REGISTER] Token FCM pas encore disponible.")
            except Exception as e:
                print(f"[FCM REGISTER ERROR] Recuperation token : {e}")
            payload = {
                "nom": nom,
                "categorie": categorie,
                "joueurs_associes": joueurs_associes,
                "demande_admin": demande_admin,
                "fcm_token": fcm_token
            }
            print(
                f"[REGISTER] Envoi API unique : "
                f"nom={nom}, "
                f"categorie={categorie}, "
                f"joueurs={joueurs_associes}"
            )
            succes = False
            usurpation = False
            erreur_api = None
            try:
                r = requests.post(url,json=payload,timeout=15,verify=not is_windows)
                # ======================================================
                # 🔴 USURPATION D'IDENTITÉ
                # ======================================================
                if r.status_code == 403:
                    try:
                        data = r.json()
                    except Exception:
                        data = {}
                    detail = data.get("detail", "")
                    if detail == "USURPATION_IDENTITE":
                        usurpation = True
                        print(
                            f"[SECURITE] USURPATION D'IDENTITE : "
                            f"parent={nom}, "
                            f"categorie={categorie}"
                        )
                    else:
                        erreur_api = (f"Accès refusé par le serveur : {detail}")
                # ======================================================
                # 🔴 ANCIEN CAS HTTP 409
                # ======================================================
                elif r.status_code == 409:
                    usurpation = True
                    print(
                        f"[REGISTER] Doublon HTTP 409 : "
                        f"parent={nom}, "
                        f"categorie={categorie}"
                    )
                # ==================================================
                # 🟢 SUCCÈS
                # ======================================================
                elif r.status_code == 200:
                    succes = True
                    print(
                        f"[REGISTER] Demande acceptee : "
                        f"parent={nom}, "
                        f"categorie={categorie}, "
                        f"joueurs={joueurs_associes}"
                    )
                # ======================================================
                # 🟠 AUTRE ERREUR
                # ======================================================
                else:
                    erreur_api = (f"Erreur serveur HTTP {r.status_code}")
                    print(
                        f"[REGISTER ERROR] "
                        f"{erreur_api} : {r.text}"
                    )
            except Exception as e:
                erreur_api = (f"Impossible de contacter le serveur : {e}")
                print(
                    f"[REGISTER ERROR] "
                    f"Echec reseau vers l'API : {e}"
                )
            # ==========================================================
            # RETOUR SUR LE THREAD PRINCIPAL KIVY
            # ==========================================================
            def _apres_appel(dt):
                # ------------------------------------------------------
                # 🔴 USURPATION / DOUBLON
                # ------------------------------------------------------
                if usurpation:
                    self.show_popup(
                        "Demande refusée",
                        "Vous êtes déjà connecté(e)s "
                        "à cette catégorie.\n\n"
                        "Pour modifier vos joueurs, "
                        "déconnectez-vous d'abord."
                    )
                    return
                # ------------------------------------------------------
                # 🟠 ERREUR
                # ------------------------------------------------------
                if erreur_api:
                    self.show_popup(
                        "Erreur",
                        erreur_api
                    )
                    return
                # ------------------------------------------------------
                # 🟢 SUCCÈS HTTP 200
                # ------------------------------------------------------
                if succes:
                    # ==================================================
                    # IMPORTANT :
                    # C'EST LE SEUL ENDROIT où l'on écrit maintenant
                    # le choix des joueurs dans le .ini.
                    # ==================================================
                    app = App.get_running_app()
                    if joueurs_associes and hasattr(
                        app,
                        "set_joueur_associe_pour_cat"
                    ):
                        joueurs_str = ", ".join(joueurs_associes)
                        app.set_joueur_associe_pour_cat(categorie,joueurs_str)
                    # ==================================================
                    # Ensuite seulement :
                    # callback qui écrit le rôle ATTENTE dans le .ini
                    # ==================================================
                    callback_reussite()
                    self.show_popup(
                        "Demande transmise !",
                        "Votre inscription a bien été enregistrée.\n\n"
                        "Votre compte est en attente de validation "
                        "par un responsable de la catégorie."
                    )
                    return
                # ------------------------------------------------------
                # ⚠️ CAS INATTENDU
                # ------------------------------------------------------
                self.show_popup(
                    "Erreur",
                    "La demande n'a pas pu être enregistrée."
                )
            Clock.schedule_once(_apres_appel)
        threading.Thread(target=_thread_register,daemon=True).start()
        
    def synchroniser_token_fcm(self):
        app = App.get_running_app()
        # ==========================================================
        # RÉCUPÉRATION DU NOM
        # ==========================================================
        if not app.config.has_section("User"):
            print("[FCM TOKEN] Section User absente.")
            return
        nom = app.config.get("User","nom_parent",fallback="").strip()
        if not nom:
            print("[FCM TOKEN] Aucun utilisateur connecte.")
            return
        # ==========================================================
        # RÉCUPÉRATION DU TOKEN
        # ==========================================================
        try:
            if not getattr(app, "notifier", None):
                print("[FCM TOKEN] NotificationManager absent.")
                return
            fcm_token = app.notifier.get_fcm_token()
        except Exception as e:
            print(
                f"[FCM TOKEN ERROR] "
                f"Recuperation token : {e}"
            )
            return
        if not fcm_token:
            print("[FCM TOKEN] Token pas encore disponible.")
            return
    
        print(
            f"[FCM TOKEN] Token pret pour synchronisation : "
            f"{str(fcm_token)[:25]}..."
        )
        # ==========================================================
        # ENVOI AU BACKEND
        # ==========================================================
        def _thread_sync():
            url = (
                "https://fcvv-api.onrender.com"
                "/users/fcm-token"
            )
            payload = {"nom": nom,"fcm_token": fcm_token}
            try:
                r = requests.post(url,json=payload,timeout=15)
            except Exception as e:
                print(
                    f"[FCM TOKEN ERROR] "
                    f"Erreur synchronisation : {e}"
                )
        threading.Thread(target=_thread_sync,daemon=True).start()

    def demander_joueur_associe(self, nom, cat_selectionnee, callback_final,demande_admin=False):
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
                text=(
                    f"[b]Catégorie : {cat_selectionnee}[/b]\n"
                    "Cochez vos rôles ou vos joueurs :"
                ),
                markup=True,
                size_hint_y=None,
                height=dp(70),
                font_size=dp(19),
                color=(0.1, 0.1, 0.15, 1),
                halign="center",
                valign="middle"
            )
            lbl_titre_popup.bind(size=lbl_titre_popup.setter("text_size"))
            content.add_widget(lbl_titre_popup)
            scroll = ScrollView(bar_width=0, size_hint=(1, 1))
            list_layout = BoxLayout(orientation='vertical', spacing=dp(10), size_hint_y=None)
            list_layout.bind(minimum_height=list_layout.setter('height'))
            checkboxes_dict = {}
            def toggle_bold_label(checkbox, value, label_widget, original_text):
                label_widget.text = f"[b]{original_text}[/b]" if value else original_text
            box_coach = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(50), spacing=dp(10))
            chk_coach = CheckBox(size_hint_x=None, width=dp(40), color=(0.2, 0.2, 0.2, 1), pos_hint={'center_y': 0.5})
            prenom_utilisateur = nom.strip().split()[0] if nom else "Coach"
            nom_formate = prenom_utilisateur.replace(" ", "_")
            key_coach = f"COACH_{nom_formate}"
            checkboxes_dict[key_coach] = chk_coach
            box_coach.add_widget(chk_coach)
            lbl_coach = Label(text="COACH / STAFF", markup=True, font_size=dp(18), color=(0.2, 0.2, 0.25, 1), halign='left', valign='middle')
            lbl_coach.bind(size=lambda lbl, sz: setattr(lbl, 'text_size', sz))
            chk_coach.bind(active=lambda chk, val: toggle_bold_label(chk, val, lbl_coach, "COACH / STAFF"))
            box_coach.add_widget(lbl_coach)
            list_layout.add_widget(box_coach)
            
            if noms_joueurs:
                for j_nom in noms_joueurs:
                    box_j = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(50), spacing=dp(10))
                    chk = CheckBox(size_hint_x=None, width=dp(40), color=(0.2, 0.2, 0.2, 1), pos_hint={'center_y': 0.5})
                    checkboxes_dict[j_nom] = chk
                    box_j.add_widget(chk)
                    lbl_j = Label(text=j_nom, markup=True, font_size=dp(18), color=(0.2, 0.2, 0.25, 1), halign='left', valign='middle')
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
                font_size=dp(18),
                size_hint_y=None,
                height=dp(55),
                background_normal="",
                background_color=(0.15, 0.65, 0.35, 1),
                color=(1, 1, 1, 1),
                bold=True
            )
            
            def on_valider(instance):
                selectionnes = [
                    cle
                    for cle, chk in checkboxes_dict.items()
                    if chk.active
                ]
                app = App.get_running_app()
                # Fermer la popup de sélection
                popup.dismiss()
                # ==========================================================
                # IMPORTANT :
                # NE PAS écrire le .ini ici.
                #
                # La sélection est seulement envoyée au serveur.
                # Le .ini sera modifié UNIQUEMENT après HTTP 200.
                # ==========================================================
                self.enregistrer_parent_firebase(
                    nom=nom,
                    categorie=cat_selectionnee,
                    liste_joueurs_associes=selectionnes,
                    callback_reussite=callback_final,
                    demande_admin=demande_admin
                )
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
            msg_chargement = "Vérification des mises à jour..." if os.path.exists(path) else "Téléchargement de l'équipe..."
            loading_label = Label(
                text=msg_chargement,
                font_size=dp(20),
                bold=True,
                color=(0.1, 0.1, 0.15, 1),
                halign="center",
                valign="middle"
            )
            loading_label.bind(size=loading_label.setter("text_size"))
            loading_content.add_widget(loading_label)
            loading_popup = Popup(
                title="",
                content=loading_content,
                size_hint=(0.85, None),
                height=dp(200),
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
                            with open(path, "wb") as f:
                                f.write(new_content)
                    
                    if os.path.exists(path):
                        with open(path, "r", encoding="utf-8") as f:
                            data_yaml = yaml.safe_load(f) or {}
                            final_joueurs = data_yaml.get("tous_les_joueurs", [])
                except Exception as e:
                    print(f"[DOWNLOAD ERROR] : {e}")
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
                    print(f"[YAML ERROR] : {e}")
            afficher_popup_selection(liste_joueurs)

    def check_login(self, instance):
        app = App.get_running_app()
        cat = self.cat_spinner.text.replace("•", "").strip()
        pwd = self.pwd_input.text.strip()
        nom_enregistre = app.config.get('User', 'nom_parent', fallback='').strip() if app.config.has_section('User') else ''
        nom = nom_enregistre if nom_enregistre else self.name_input.text.strip()
        if not nom or not pwd:
            self.show_popup("Erreur", "Veuillez remplir votre nom et le mot de passe.")
            return
        saisie_hash = hashlib.sha256(pwd.encode()).hexdigest()
        vestiaires_cfg = app.app_config.get("fcvv", {}).get("appli", {}).get("vestiaire", [])
        # 1. CAS SUPER_ADMIN
        super_admin_item = next((item for item in vestiaires_cfg if "password_super_admin_hash" in item), None)
        if super_admin_item and saisie_hash == super_admin_item["password_super_admin_hash"]:
            app.config.set('User', 'nom_parent', nom)
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
            
            # --- AJOUT : Reconstruire le menu latéral ---
            if hasattr(app.root, 'rebuild_menu'):
                app.root.rebuild_menu()
            # Inscription Super Admin sur l'API (non-bloquante)
            self.enregistrer_parent_firebase(
                nom=nom,
                categorie="TOUTES",
                liste_joueurs_associes=["SUPER_ADMIN"],
                callback_reussite=lambda: None
            )
            self.active_label.text = f"Connecté : {', '.join(app.authorized_vestiaires)}"
            return
        if cat == "Sélectionner une catégorie...":
            self.show_popup("Erreur", "Veuillez choisir une catégorie.")
            return
        # 2. VÉRIFICATION MOT DE PASSE CATEGORIE
        role_mot_de_passe = app.check_vestiaire_password(cat, pwd)
        if role_mot_de_passe:
            # Le mot de passe utilisé détermine le type de demande.
            # Le rôle local reste ATTENTE jusqu'à validation.
            demande_admin = (role_mot_de_passe == "ADMIN")
            role_initial = "ATTENTE"
            def finaliser_connexion_locale():
                app.config.set('User', 'nom_parent', nom)
                # La demande reste ATTENTE jusqu'à validation
                app.add_authorized_vestiaire(
                    cat,
                    role_initial,
                    saisie_hash,
                    save=True
                )
                app.gerer_abonnements_fcm(app.authorized_vestiaires)
                
                # --- AJOUT : Reconstruire le menu latéral ---
                if hasattr(app.root, 'rebuild_menu'):
                    app.root.rebuild_menu()
                    
                Clock.schedule_once(lambda dt: self.synchroniser_token_fcm(),5.0)
                self.active_label.text = (f"Connecté : {', '.join(app.authorized_vestiaires)}")
            # Ouverture de la popup pour sélectionner l'association aux joueurs
            self.demander_joueur_associe(nom, cat, finaliser_connexion_locale,demande_admin)
        else:
            self.show_popup("Erreur", "Mot de passe incorrect.")

    def show_popup(self, title, message):
        content = BoxLayout(
            orientation="vertical",
            padding=(dp(25), dp(20)),
            spacing=dp(15)
        )
        with content.canvas.before:
            Color(0.95, 0.95, 0.97, 1)
            pop_bg = RoundedRectangle(
                pos=content.pos,
                size=content.size,
                radius=[dp(20)]
            )
        content.bind(
            pos=lambda obj, val: setattr(pop_bg, "pos", val),
            size=lambda obj, val: setattr(pop_bg, "size", val)
        )
        # ==========================================================
        # TITRE
        # ==========================================================
        lbl_title = None
        if title:
            lbl_title = Label(
                text=f"[b]{title}[/b]",
                markup=True,
                font_size=dp(22),
                size_hint_y=None,
                color=(0.1, 0.1, 0.15, 1),
                halign="center",
                valign="middle",
                padding=(dp(5), dp(5))
            )
            # Largeur disponible pour calculer les retours à la ligne
            lbl_title.bind(
                width=lambda instance, value: setattr(
                    instance,
                    "text_size",
                    (value - dp(10), None)
                )
            )
            # Hauteur automatique selon le texte
            lbl_title.bind(
                texture_size=lambda instance, value: setattr(
                    instance,
                    "height",
                    max(dp(50), value[1] + dp(10))
                )
            )
            content.add_widget(lbl_title)
        # ==========================================================
        # MESSAGE
        # ==========================================================
        lbl_message = Label(
            text=message,
            font_size=dp(18),
            color=(0.2, 0.2, 0.25, 1),
            halign="center",
            valign="middle",
            size_hint_y=None,
            padding=(dp(10), dp(10))
        )
        def update_message_text_size(instance, width):
            instance.text_size = (
                max(dp(100), width - dp(20)),
                None
            )
        lbl_message.bind(width=update_message_text_size)
        # Hauteur automatique selon le nombre de lignes
        def update_message_height(instance, texture_size):
            instance.height = max(
                dp(60),
                texture_size[1] + dp(20)
            )
        lbl_message.bind(texture_size=update_message_height)
        content.add_widget(lbl_message)
        # ==========================================================
        # POPUP
        # ==========================================================
        popup = Popup(
            title="",
            content=content,
            size_hint_x=0.85,
            size_hint_y=None,
            height=dp(320),
            separator_height=0,
            background="",
            background_color=(0, 0, 0, 0),
            auto_dismiss=True
        )
        # ==========================================================
        # CALCUL AUTOMATIQUE DE LA HAUTEUR
        # ==========================================================
        def ajuster_hauteur(*args):
            # Hauteur réellement nécessaire au contenu
            hauteur = dp(40)
            if lbl_title:
                hauteur += lbl_title.height
            hauteur += lbl_message.height
            # Espacement supplémentaire
            hauteur += dp(35)
            # Toujours suffisamment grand pour les messages
            hauteur = max(hauteur, dp(280))
            # Ne jamais dépasser l'écran
            hauteur_max = Window.height * 0.80
            hauteur = min(hauteur, hauteur_max)
            popup.height = hauteur
        # Recalcul lorsque le texte change
        lbl_message.bind(height=ajuster_hauteur)
        if lbl_title:
            lbl_title.bind(
                height=ajuster_hauteur
            )
        # Important : attendre que Kivy ait calculé les textures
        Clock.schedule_once(lambda dt: ajuster_hauteur(),0)
        popup.open()
        # Deuxième calcul après affichage
        Clock.schedule_once(lambda dt: ajuster_hauteur(),0.05)