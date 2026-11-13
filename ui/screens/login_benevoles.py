
# -*- coding: utf-8 -*-

import hashlib
import hmac

from kivy.app import App
from kivy.metrics import dp
from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.graphics import Color, Rectangle, RoundedRectangle
from kivy.utils import get_color_from_hex
from kivy.utils import platform
from datetime import datetime, timezone

class BenevolesLoginScreen(Screen):
    # --------------------------------------------------
    # COULEURS DE L'APPLICATION
    # --------------------------------------------------
    COLOR_BLUE = "#1E3A8A"
    COLOR_YELLOW = "#F7ED40"
    COLOR_WHITE = "#FFFFFF"
    COLOR_TEXT = "#243B53"
    COLOR_MUTED = "#8293A5"
    COLOR_ERROR = "#C0392B"
    COLOR_INPUT = "#F4F6FA"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.build_interface()
    # --------------------------------------------------
    # INTERFACE
    # --------------------------------------------------
    def build_interface(self):
        # Fond général bleu
        with self.canvas.before:
            Color(*get_color_from_hex(self.COLOR_BLUE))
            self.bg_rect = Rectangle(pos=self.pos,size=self.size)
        self.bind(pos=self._update_bg,size=self._update_bg)
        # Conteneur central
        anchor = AnchorLayout(anchor_x="center",anchor_y="top",padding=[dp(20), dp(20), dp(20), dp(10)])
        # Carte blanche
        card = BoxLayout( orientation="vertical",   padding=[dp(24), dp(20), dp(24), dp(24)], spacing=dp(12), size_hint=(0.9, None), height=dp(430))
        with card.canvas.before:
            Color(*get_color_from_hex(self.COLOR_WHITE))
            card.bg_rect = RoundedRectangle(pos=card.pos,size=card.size,radius=[dp(20)])
        card.bind( pos=self._update_card, size=self._update_card)
        accent = WidgetSpacer(size_hint=(1, None),  height=dp(5))
        with accent.canvas.before:
            Color(*get_color_from_hex(self.COLOR_YELLOW))
            accent.bg_rect = RoundedRectangle(
                pos=accent.pos,
                size=accent.size,
                radius=[dp(3)]
            )
        accent.bind(pos=self._update_card,size=self._update_card)
        card.add_widget(accent)
        # Titre
        card.add_widget(Label(
            text="[b]ESPACE BÉNÉVOLES[/b]",
            markup=True,
            font_size="14sp",
            color=get_color_from_hex(self.COLOR_BLUE),
            size_hint_y=None,
            height=dp(30)
        ))
        card.add_widget(Label(
            text="[b]Bienvenue ![/b]",
            markup=True,
            font_size="27sp",
            color=get_color_from_hex(self.COLOR_TEXT),
            size_hint_y=None,
            height=dp(45)
        ))
        subtitle = Label(
            text="Connecte-toi pour accéder à l’espace bénévole",
            font_size=dp(14),
            color=get_color_from_hex(self.COLOR_MUTED),
            halign="center",
            valign="middle",
            size_hint=(1, None),
            height=dp(45)
        )
        subtitle.bind(width=lambda instance, width: setattr(instance, "text_size", (width, None)))
        card.add_widget(subtitle)
        # Identifiant
        self.login_input = TextInput(
            hint_text="Identifiant",
            multiline=False,
            size_hint_y=None,
            height=dp(48),
            font_size="15sp",
            padding=[dp(14), dp(12)],
            background_normal="",
            background_active="",
            background_color=get_color_from_hex(self.COLOR_INPUT),
            foreground_color=get_color_from_hex(self.COLOR_TEXT),
            cursor_color=get_color_from_hex(self.COLOR_BLUE)
        )
        card.add_widget(self.login_input)
        # Mot de passe
        self.password_input = TextInput(
            hint_text="Mot de passe",
            password=True,
            multiline=False,
            size_hint_y=None,
            height=dp(48),
            font_size="15sp",
            padding=[dp(14), dp(12)],
            background_normal="",
            background_active="",
            background_color=get_color_from_hex(self.COLOR_INPUT),
            foreground_color=get_color_from_hex(self.COLOR_TEXT),
            cursor_color=get_color_from_hex(self.COLOR_BLUE)
        )
        self.password_input.bind(on_text_validate=self.check_login)
        card.add_widget(self.password_input)
        # Bouton de connexion jaune
        login_button = Button(
            text="[b]SE CONNECTER[/b]",
            markup=True,
            size_hint_y=None,
            height=dp(50),
            background_normal="",
            background_down="",
            background_color=(0, 0, 0, 0),
            color=get_color_from_hex(self.COLOR_BLUE),
            font_size="15sp",
            bold=True
        )
        with login_button.canvas.before:
            Color(*get_color_from_hex(self.COLOR_YELLOW))
            login_button.bg_rect = RoundedRectangle(pos=login_button.pos,size=login_button.size,radius=[dp(10)])
        login_button.bind(pos=self._update_card,size=self._update_card, on_release=self.check_login)
        card.add_widget(login_button)
        # Message d'erreur
        self.error_label = Label(text="",font_size="12sp",color=get_color_from_hex(self.COLOR_ERROR),size_hint_y=None,height=dp(30),halign="center",valign="middle" )
        card.add_widget(self.error_label)
        card.add_widget(WidgetSpacer())
        anchor.add_widget(card)
        self.add_widget(anchor)
    # --------------------------------------------------
    # MISE À JOUR DES FONDS
    # --------------------------------------------------
    def _update_bg(self, instance, value):
        self.bg_rect.pos = instance.pos
        self.bg_rect.size = instance.size

    def _update_card(self, instance, value):
        if hasattr(instance, "bg_rect"):
            instance.bg_rect.pos = instance.pos
            instance.bg_rect.size = instance.size
    # --------------------------------------------------
    # RÉCUPÉRATION DE LA CONFIGURATION YAML
    # Même chemin que PresentationScreen
    # --------------------------------------------------
    def get_access_config(self):
        app = App.get_running_app()
        tournoi_root = app.app_config.get("tournoi", {})
        appli_data = tournoi_root.get("appli", {})
        benevoles_data = appli_data.get("benevoles", {})
        access_data = benevoles_data.get("acces", {})
        return access_data
    # --------------------------------------------------
    # MÉMORISATION ET CONTRÔLE DE L'AUTHENTIFICATION
    # --------------------------------------------------
    def get_current_credentials_hash(self):
        access = self.get_access_config()
        login = str(access.get("login", "")).strip()
        password_hash = str( access.get("password_hash", "")).strip().lower()
        if not login or not password_hash:
            return ""
        # Empreinte de l'identifiant et du hash du mot de passe
        credentials = f"{login.casefold()}:{password_hash}"
        return hashlib.sha256(credentials.encode("utf-8")).hexdigest()
    
    def is_authenticated(self):
        app = App.get_running_app()
        authenticated = app.config.get("Benevoles", "authenticated",fallback="0")
        saved_credentials = app.config.get("Benevoles", "credentials_hash", fallback="")
        current_credentials = self.get_current_credentials_hash()
        # Vérification de la connexion et des identifiants
        if (
            authenticated == "1"
            and saved_credentials
            and current_credentials
            and hmac.compare_digest(
                saved_credentials,
                current_credentials
            )
        ):
            return True
        # Si les identifiants ont changé, on invalide la connexion
        self.save_authentication(False)
        return False
    
    def save_authentication(self, authenticated):
        app = App.get_running_app()
        if not app.config.has_section("Benevoles"):
            app.config.add_section("Benevoles")
        app.config.set(
            "Benevoles",
            "authenticated",
            "1" if authenticated else "0"
        )
        if authenticated:
            credentials_hash = self.get_current_credentials_hash()
            app.config.set("Benevoles","credentials_hash",credentials_hash)
            # Date et heure de la connexion bénévole
            date_connexion = datetime.now(timezone.utc).isoformat()
            app.config.set( "Benevoles","date_connexion", date_connexion)
            print(
                "[BENEVOLES LOGIN] Date de connexion enregistree : "
                + date_connexion
            )
        else:
            app.config.set("Benevoles","credentials_hash","")
        app.config.write()
    # --------------------------------------------------
    # AUTHENTIFICATION
    # --------------------------------------------------
    def check_login(self, instance=None):
        login = self.login_input.text.strip()
        password = self.password_input.text
        if not login or not password:
            self.error_label.text = ("Veuillez renseigner les deux champs.")
            return
        access = self.get_access_config()
        configured_login = str( access.get("login", "")).strip()
        configured_hash = str(access.get("password_hash", "")).strip().lower()
        if not configured_login or not configured_hash:
            self.error_label.text = ("Les identifiants ne sont pas configurés.")
            print("[BENEVOLES LOGIN] Configuration absente.")
            return
        password_hash = hashlib.sha256(password.encode("utf-8")).hexdigest()
        login_ok = hmac.compare_digest(login.casefold(), configured_login.casefold())
        password_ok = hmac.compare_digest(password_hash,configured_hash)
        if login_ok and password_ok:
            self.save_authentication(True)
            app = App.get_running_app()
            # ======================================
            # Abonnement FCM catégorie Bénévole
            # ======================================
            try:
                if (hasattr(app, "notifier") and app.notifier and platform in ("android", "ios")):
                    print("[FCM BENEVOLES] Abonnement au topic Benevole")
                    app.notifier.subscribe_to_topic("Benevole")
            except Exception as e:
                print(f"[FCM BENEVOLES] Erreur abonnement : {e}")
            self.password_input.text = ""
            self.error_label.text = ""
            if app.root and hasattr(app.root, "switch_screen"):
                app.root.switch_screen("benevoles")
        else:
            self.password_input.text = ""
            self.error_label.text = ("Identifiant ou mot de passe incorrect.")

    # --------------------------------------------------
    # REDIRECTION
    # --------------------------------------------------
    def on_pre_enter(self, *args):
        if self.is_authenticated():
            app = App.get_running_app()
            try:
                if (hasattr(app, "notifier") and app.notifier and platform in ("android", "ios")):
                    print("[FCM BENEVOLES] Reabonnement automatique")
                    app.notifier.subscribe_to_topic("Benevole")
            except Exception as e:
                print(f"[FCM BENEVOLES] Erreur : {e}")
            if app.root and hasattr(app.root, "switch_screen"):
                app.root.switch_screen("benevoles")

    def on_enter(self, *args):
        self.password_input.text = ""
        self.error_label.text = ""
        
    # --------------------------------------------------
    # DÉCONNEXION
    # --------------------------------------------------
    def logout(self, *args):
        self.save_authentication(False)
        app = App.get_running_app()
        try:
            if hasattr(app, "notifier") and app.notifier and platform in ("android", "ios"):
                # 1. Désabonnement du topic global des bénévoles
                print("[FCM BENEVOLES] Desabonnement du topic Benevole")
                app.notifier.unsubscribe_from_topic("Benevole")
                # 2. Vérification et désabonnement du topic d'exclusion si un prénom était enregistré
                if app.config.has_section("Benevoles") and app.config.has_option("Benevoles", "prenom_chat"):
                    prenom = app.config.get("Benevoles", "prenom_chat").strip()
                    if prenom:
                        prenom_clean = prenom.strip().replace(" ", "_").lower()
                        topic_exclusion = f"Benevole_exclure_{prenom_clean}"
                        print(f"[FCM BENEVOLES] Desabonnement du topic d'exclusion : {topic_exclusion}")
                        app.notifier.unsubscribe_from_topic(topic_exclusion)
        except Exception as e:
            print(f"[FCM BENEVOLES] Erreur desabonnement : {e}")
        if app.root and hasattr(app.root, "switch_screen"):
            app.root.switch_screen("login_benevoles")

# Petit espaceur vertical
class WidgetSpacer(BoxLayout):
    pass
