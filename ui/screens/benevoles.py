# -*- coding: utf-8 -*-
import webbrowser
from kivy.clock import Clock
from datetime import datetime
from urllib.parse import urlparse

from kivy.app import App
from kivy.metrics import dp
from kivy.utils import get_color_from_hex
import os

from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.widget import Widget
from kivy.uix.gridlayout import GridLayout

from kivy.graphics import Color, RoundedRectangle
from kivy.utils import platform

from kivy.uix.textinput import TextInput

from core.planning import PlanningScreen

class BenevolesScreen(Screen):
    # ---------------------------------------------------------
    # CONFIGURATION VISUELLE
    # ---------------------------------------------------------
    # Bleu principal de l'application
    COLOR_BACKGROUND = "#1E3A8A"
    COLOR_PRIMARY = "#1E3A8A"
    COLOR_SECONDARY = "#334B78"
    # Jaune utilisé uniquement comme accent
    COLOR_ACCENT = "#F7ED40"
    # Textes
    COLOR_TEXT = "#243B53"
    COLOR_MUTED = "#65758B"
    COLOR_WHITE = "#FFFFFF"
    # Cartes
    COLOR_CARD = "#FFFFFF"
    COLOR_BORDER = "#DCE5F2"
    COLOR_LIGHT_BLUE = "#EAF0FF"
    # Couleurs complémentaires
    COLOR_SUCCESS = "#219653"
    COLOR_WARNING = "#F2994A"
    COLOR_PALE_BLUE = "#DCE8FF"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.current_tab = "accueil"
        self.selected_pole = None
        self.benevoles_data = {}
        self.build_interface()
    # ---------------------------------------------------------
    # CONSTRUCTION DE L'INTERFACE
    # ---------------------------------------------------------
    def build_interface(self):
        self.main_layout = BoxLayout( orientation="vertical",spacing=0, padding=0 )
        # Fond bleu général
        with self.main_layout.canvas.before:
            Color(*get_color_from_hex(self.COLOR_BACKGROUND))
            self.background_rect = RoundedRectangle(
                pos=self.main_layout.pos,
                size=self.main_layout.size,
                radius=[0]
            )
        self.main_layout.bind(pos=self.update_background,size=self.update_background)
        # -----------------------------------------------------
        # NAVIGATION HORIZONTALE DÉFILANTE
        # -----------------------------------------------------
        self.navigation_scroll = ScrollView(
            size_hint=(1, None),
            height=dp(56),
            do_scroll_x=True,
            do_scroll_y=False,
            bar_width=dp(0),
            scroll_type=["bars", "content"]
        )
        self.navigation = BoxLayout(
            orientation="horizontal",
            size_hint=(None, 1),
            width=0,
            padding=[dp(10), dp(5), dp(10), dp(7)],
            spacing=dp(5)
        )
        self.navigation.bind(minimum_width=self.navigation.setter("width"))
        self.tab_buttons = {}
        tabs = [
            ("accueil", "Accueil"),
            ("reunions", "Réunions"),
            ("poles", "Pôles"),
            ("annuaire", "Annuaire"),
            ("planning", "Planning"),
            ("documents", "Documents")
        ]
        for tab_id, tab_title in tabs:
            button = Button(
                text=tab_title,
                font_size="12sp",
                bold=True,
                background_normal="",
                background_down="",
                background_color=get_color_from_hex(
                    self.COLOR_SECONDARY
                ),
                color=get_color_from_hex(self.COLOR_WHITE),
                size_hint=(None, 1),
                width=dp(130)
            )
            button.bind( on_release=lambda instance, t=tab_id: self.change_tab(t) )
            self.tab_buttons[tab_id] = button
            self.navigation.add_widget(button)
        self.navigation_scroll.add_widget(self.navigation)
        self.main_layout.add_widget(self.navigation_scroll)

        # -----------------------------------------------------
        # CONTENU DÉFILANT
        # -----------------------------------------------------
        self.scroll_view = ScrollView( do_scroll_x=False,bar_width=dp(0),scroll_type=["bars", "content"],bar_color=get_color_from_hex(self.COLOR_ACCENT), bar_inactive_color=(1, 1, 1, 0.25))
        self.content = BoxLayout( orientation="vertical", size_hint_y=None, padding=[dp(15), dp(14), dp(15), dp(25)], spacing=dp(14))
        self.content.bind( minimum_height=self.content.setter("height"))
        self.scroll_view.add_widget(self.content)
        self.main_layout.add_widget(self.scroll_view)
        self.add_widget(self.main_layout)
        self.update_tab_buttons()

    def update_background(self, instance, value):
        self.background_rect.pos = instance.pos
        self.background_rect.size = instance.size

    # ---------------------------------------------------------
    # OUTILS GRAPHIQUES
    # ---------------------------------------------------------
    def make_label(
        self,
        text,
        font_size="14sp",
        color=None,
        bold=False,
        height=None,
        halign="left"
    ):
        label = Label(
            text=str(text),
            font_size=font_size,
            color=get_color_from_hex(
                color or self.COLOR_TEXT
            ),
            bold=bold,
            halign=halign,
            valign="middle",
            size_hint_y=None
        )
        # Adapter la largeur du texte à celle du label
        def update_text_width(instance, width):
            instance.text_size = (max(1, width), None)
        label.bind(width=update_text_width)
        # Hauteur automatique selon le nombre de lignes
        if height is None:
            def update_height(instance, texture_size):
                instance.height = max(
                    dp(24),
                    texture_size[1] + dp(8)
                )
            label.bind(texture_size=update_height)
            # Premier calcul
            update_text_width(label, label.width)
            label.texture_update()
            label.height = max(
                dp(24),
                label.texture_size[1] + dp(8)
            )
        else:
            label.height = dp(height)
    
        return label

    def add_spacer(self, height=5):
        self.content.add_widget( Widget(size_hint_y=None,height=dp(height)))

    def clear_content(self):
        self.content.clear_widgets()

    def add_title(self, title, subtitle=None):
        self.content.add_widget(self.make_label( title,font_size="20sp", bold=True, color=self.COLOR_WHITE ))
        if subtitle:
            self.content.add_widget(self.make_label( subtitle, font_size="13sp",color=self.COLOR_PALE_BLUE ))

    def create_card(self, padding=14, spacing=8, color=None):
        card = BoxLayout(
            orientation="vertical",
            size_hint_y=None,
            padding=dp(padding),
            spacing=dp(spacing)
        )
        card.bind(minimum_height=card.setter("height"))
        with card.canvas.before:
            Color(*get_color_from_hex(
                color or self.COLOR_CARD
            ))
            card.background = RoundedRectangle(
                pos=card.pos,
                size=card.size,
                radius=[dp(14)]
            )
        card.bind(
            pos=lambda instance, value:
            setattr(instance.background, "pos", value),
            size=lambda instance, value:
            setattr(instance.background, "size", value)
        )
        return card

    def add_to_card(self, card, text, **kwargs):
        label = self.make_label(text, **kwargs)
        card.add_widget(label)
        return label

    def add_card_button(self, card, title, url, color=None):
        if not url:
            return
        button = Button(
            text=title,
            size_hint_y=None,
            height=dp(40),
            background_normal="",
            background_down="",
            background_color=get_color_from_hex(
                color or self.COLOR_LIGHT_BLUE
            ),
            color=get_color_from_hex(self.COLOR_PRIMARY),
            font_size="13sp",
            bold=True
        )
        button.bind(on_release=lambda instance, link=url:self.open_url(link))
        card.add_widget(button)

    def add_section_title(self, title):
        self.content.add_widget(self.make_label(title, font_size="16sp",bold=True, color=self.COLOR_ACCENT))

    def add_empty_message(self, message):
        card = self.create_card()
        self.add_to_card(card, message, color=self.COLOR_MUTED, font_size="13sp" )
        self.content.add_widget(card)
    # ---------------------------------------------------------
    # CONFIGURATION
    # ---------------------------------------------------------
    def on_enter(self, *args):
        self.update_ui_from_config()

    def get_benevoles_data(self):
        try:
            app = App.get_running_app()
            config = getattr(app, "app_config", {}) or {}
            tournoi = config.get("tournoi", {}) or {}
            appli = tournoi.get("appli", {}) or {}
            return appli.get("benevoles", {}) or {}
        except Exception as error:
            print("[BENEVOLES] Erreur de chargement :",error)
            return {}

    def update_ui_from_config(self):
        self.benevoles_data = self.get_benevoles_data()
        self.selected_pole = None
        self.display_current_tab()

    def display_current_tab(self):
        self.clear_content()
        self.update_tab_buttons()
        if self.current_tab == "accueil":
            self.display_home()
        elif self.current_tab == "reunions":
            self.display_meetings()
        elif self.current_tab == "poles":
            if self.selected_pole:
                self.display_pole_detail(self.selected_pole)
            else:
                self.display_poles()
        elif self.current_tab == "documents":
            self.display_documents()
        elif self.current_tab == "annuaire":
            self.display_annuaire()
        elif self.current_tab == "planning":
            self.display_planning()
    # ---------------------------------------------------------
    # NAVIGATION
    # ---------------------------------------------------------
    def change_tab(self, tab):
        self.current_tab = tab
        self.selected_pole = None
        self.display_current_tab()

    def update_tab_buttons(self):
        for tab_id, button in self.tab_buttons.items():
            if tab_id == self.current_tab:
                # Onglet actif : jaune avec texte bleu
                button.background_color = get_color_from_hex( self.COLOR_ACCENT )
                button.color = get_color_from_hex( self.COLOR_PRIMARY )
            else:
                # Onglet inactif : bleu avec texte blanc
                button.background_color = get_color_from_hex(  self.COLOR_SECONDARY )
                button.color = get_color_from_hex(self.COLOR_WHITE )

    # ---------------------------------------------------------
    # GESTION DES DATES
    # ---------------------------------------------------------
    def parse_datetime(self, meeting):
        if not isinstance(meeting, dict):
            return None
        date_value = meeting.get("date")
        if not date_value:
            return None
        heure = meeting.get("heure")
        # Conversion de la date
        date_text = str(date_value).strip()
        # Conversion éventuelle de l'heure
        heure_text = str(heure).strip() if heure else ""
        formats = []
        if heure_text:
            formats.extend([
                "%Y-%m-%d %H:%M",
                "%d/%m/%Y %H:%M",
                "%Y-%m-%d %H:%M:%S",
            ])
        formats.extend([
            "%Y-%m-%d",
            "%d/%m/%Y",
        ])
        for fmt in formats:
            try:
                if "%H" in fmt:
                    return datetime.strptime(
                        date_text + " " + heure_text,
                        fmt
                    )
                else:
                    return datetime.strptime(date_text, fmt)
            except (ValueError, TypeError):
                continue
        return None
    
    def format_date(self, value):
        if not value:
            return "Date à renseigner"
        date_text = str(value).strip()
        for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
            try:
                parsed = datetime.strptime(date_text, fmt)
                return parsed.strftime("%d/%m/%Y")
            except (ValueError, TypeError):
                continue
        return date_text
    
    def get_sorted_meetings(self):
        meetings = self.benevoles_data.get("reunions", []) or []
        if not isinstance(meetings, list):
            return []
        valid_meetings = [
            meeting for meeting in meetings
            if isinstance(meeting, dict)
        ]
        return sorted(
            valid_meetings,
            key=lambda meeting: (
                self.parse_datetime(meeting) or datetime.max
            )
        )
    
    def get_upcoming_meetings(self):
        now = datetime.now()
        today = now.date()
        upcoming = []
        for meeting in self.get_sorted_meetings():
            meeting_date = self.parse_datetime(meeting)
            if meeting_date is None:
                continue
            # Une réunion sans heure reste à venir pendant toute sa journée.
            if not meeting.get("heure"):
                if meeting_date.date() >= today:
                    upcoming.append(meeting)
            elif meeting_date >= now:
                upcoming.append(meeting)
        return upcoming
    # ---------------------------------------------------------
    # ONGLET ACCUEIL
    # ---------------------------------------------------------
    def display_home(self):
        self.clear_content()
        data = self.benevoles_data or {}
        # -----------------------------------------------------
        # 1. BIENVENUE
        # -----------------------------------------------------
        presentation = data.get("presentation", {}) or {}
        if not isinstance(presentation, dict):
            presentation = {}
        welcome_card = self.create_card( padding=20, spacing=8)
        self.add_to_card(
            welcome_card,
            presentation.get("titre", "Bienvenue !"),
            font_size="22sp",
            color=self.COLOR_PRIMARY,
            bold=True
        )
        self.add_to_card(
            welcome_card,
            presentation.get(
                "message",
                "Bienvenue dans votre espace bénévoles."
            ),
            font_size="15sp",
            color=self.COLOR_TEXT
        )
        self.content.add_widget(welcome_card)
        self.add_spacer(5)
        # -----------------------------------------------------
        # 2. INFORMATIONS IMPORTANTES
        # -----------------------------------------------------
        self.add_section_title("INFORMATIONS IMPORTANTES")
        annonces = data.get("annonces", []) or []
        if not isinstance(annonces, list):
            annonces = []
        annonces_importantes = []
        for annonce in annonces:
            if not isinstance(annonce, dict):
                continue
            if annonce.get("important", False):
                annonces_importantes.append(annonce)
        if annonces_importantes:
            for annonce in annonces_importantes:
                card = self.create_card(
                    padding=15,
                    spacing=6
                )
                self.add_to_card(
                    card,
                    annonce.get("titre", "Information"),
                    font_size="16sp",
                    color=self.COLOR_PRIMARY,
                    bold=True
                )
                message = annonce.get("message", "")
                if message:
                    self.add_to_card(
                        card,
                        message,
                        font_size="14sp",
                        color=self.COLOR_TEXT
                    )
                if annonce.get("date"):
                    self.add_to_card(
                        card,
                        self.format_date(annonce.get("date")),
                        font_size="12sp",
                        color=self.COLOR_MUTED
                    )
                self.content.add_widget(card)
        else:
            self.add_empty_message("Aucune information importante pour le moment.")
        self.add_spacer(5)
        # -----------------------------------------------------
        # 3. PROCHAINS RENDEZ-VOUS
        # -----------------------------------------------------
        self.add_section_title("PROCHAINS RENDEZ-VOUS")
        upcoming = self.get_upcoming_meetings()
        if upcoming:
            for meeting in upcoming[:5]:
                self.display_meeting_card(meeting)
        else:
            self.add_empty_message( "Aucun rendez-vous prévu pour le moment." )
        self.add_spacer(5)
        # Bouton de déconnexion tout en bas de l'accueil
        logout_button = Button(
            text="Se déconnecter",
            size_hint=(1, None),
            height=dp(48),
            background_normal="",
            background_color=get_color_from_hex("#DC2626"),
            color=(1, 1, 1, 1),
            font_size=dp(16),
            bold=True
        )
        logout_button.bind(on_release=self.logout)
        self.content.add_widget(logout_button)
        # Espace de sécurité Android
        self.add_bottom_safe_spacing()
    # ---------------------------------------------------------
    # ONGLET ANNONCES
    # ---------------------------------------------------------
    def get_announcements(self):
        return self.benevoles_data.get(
            "annonces", []
        ) or []

    def display_important_announcements(self):
        announcements = [
            item
            for item in self.get_announcements()
            if item.get("important", False)
        ]
        if not announcements:
            return
        self.add_section_title("Informations importantes")
        for announcement in announcements[:3]:
            card = self.create_card()
            self.add_to_card(
                card,
                announcement.get(
                    "titre",
                    "Information"
                ),
                font_size="15sp",
                bold=True,
                color=self.COLOR_WARNING
            )
            self.add_to_card(card, announcement.get("message", ""),font_size="13sp")
            if announcement.get("date"):
                self.add_to_card(
                    card,
                    self.format_date(
                        announcement.get("date")
                    ),
                    font_size="11sp",
                    color=self.COLOR_MUTED
                )
            self.content.add_widget(card)

    def show_announcements(self):
        self.clear_content()
        self.add_title("Informations","Annonces et consignes destinées aux bénévoles")
        announcements = self.get_announcements()
        if not announcements:
            self.add_empty_message("Aucune information publiée pour le moment.")
            self.add_back_button("accueil")
            return

        for announcement in announcements:
            card = self.create_card()
            self.add_to_card( card,announcement.get("titre", "Information"), font_size="16sp", bold=True)
            self.add_to_card(card,announcement.get("message", ""),font_size="13sp")
            if announcement.get("date"):
                self.add_to_card(
                    card,
                    self.format_date(
                        announcement.get("date")
                    ), font_size="11sp", color=self.COLOR_MUTED)
            self.content.add_widget(card)
        self.add_back_button("accueil")
    # ---------------------------------------------------------
    # ONGLET RÉUNIONS
    # ---------------------------------------------------------
    def display_meetings(self):
        self.add_title( "Réunions", "Retrouve les rendez-vous et les comptes rendus.")
        meetings = self.get_sorted_meetings()
        upcoming = self.get_upcoming_meetings()
        self.add_section_title("Réunions à venir")
        if upcoming:
            for meeting in upcoming:
                self.display_meeting_card(meeting)
        else:
            self.add_empty_message( "Aucune réunion à venir." )
        past = [
            meeting
            for meeting in meetings
            if meeting not in upcoming
        ]
        self.add_section_title("Réunions passées")
        if past:
            for meeting in reversed(past):
                self.display_meeting_card(meeting)
        else:
            self.add_empty_message( "Aucune réunion passée.")
        
        self.add_bottom_safe_spacing()

    def display_meeting_card(self, meeting, add_to_content=False):
        if not isinstance(meeting, dict):
            return None
        card = self.create_card( padding=14, spacing=6)
        self.add_to_card(
            card,
            meeting.get("titre", "Réunion"),
            font_size="16sp",
            bold=True,
            color=self.COLOR_PRIMARY
        )
        date_text = self.format_date(meeting.get("date"))
        heure = meeting.get("heure") or "Heure à définir"
        self.add_to_card(
            card,
            "{} - {}".format(date_text, heure),
            font_size="13sp",
            color=self.COLOR_PRIMARY,
            bold=True
        )
        self.add_to_card(
            card,
            "Lieu : {}".format(
                meeting.get("lieu") or "À définir"
            ),
            font_size="12sp",
            color=self.COLOR_MUTED
        )
        if meeting.get("description"):
            self.add_to_card( card, meeting.get("description"), font_size="13sp", color=self.COLOR_TEXT)
        if meeting.get("pole"):
            self.add_to_card( card, "Pôle : {}".format(meeting.get("pole")), font_size="12sp", color=self.COLOR_MUTED)
        if meeting.get("lien"):
            self.add_card_button(card, "Lien de la réunion", meeting.get("lien") )
        if meeting.get("compte_rendu"):
            self.add_card_button(card, "Consulter le compte rendu",meeting.get("compte_rendu"))
        self.content.add_widget(card)
        return card
    
    # ---------------------------------------------------------
    # ONGLET PÔLES
    # ---------------------------------------------------------
    def display_poles(self):
        self.add_title("Les pôles du tournoi", "Découvre les équipes, leurs missions et leurs référents.")
        poles = self.benevoles_data.get("poles", []) or []
        if not poles:
            self.add_empty_message("Aucun pôle n'est actuellement renseigné.")
            self.add_bottom_safe_spacing()
            return
        self.poles_grid = GridLayout(cols=2, spacing=dp(12), padding=[0, dp(5), 0, dp(10)], size_hint=(1, None))
        self.poles_grid.bind(minimum_height=self.poles_grid.setter("height"))
        cards = []
        for pole in poles:
            if not isinstance(pole, dict):
                continue
            card = self.display_pole_preview(pole)
            card.opacity = 0
            cards.append(card)
            self.poles_grid.add_widget(card)
        if not cards:
            self.add_empty_message("Aucun pôle exploitable n'a été trouvé.")
            self.add_bottom_safe_spacing()
            return
        self.content.add_widget(self.poles_grid)
    
        def update_layout(dt):
            for card in cards:
                card.do_layout()
                for label in card.pole_labels.values():
                    label.texture_update()
            self.align_pole_card_labels(cards)
            for card in cards:
                card.do_layout()
            Clock.schedule_once(equalize_cards, 0.15)
    
        def equalize_cards(dt):
            for card in cards:
                card.do_layout()
            max_height = max(card.minimum_height for card in cards)
            for card in cards:
                card.height = max_height
            Clock.schedule_once(show_cards, 0.15)
    
        def show_cards(dt):
            for card in cards:
                card.opacity = 1
        Clock.schedule_once(update_layout, 0.3)
        self.add_bottom_safe_spacing()
    
    def get_referent_name(self, pole):
        referents = pole.get("referents", [])
        if not referents:
            referent = pole.get("referent", "")
            if isinstance(referent, dict):
                return referent.get("nom", "Référent à renseigner")
            return referent or "Référent à renseigner"
        if isinstance(referents, dict):
            referents = [referents]
        if isinstance(referents, str):
            return referents
        noms = []
        for referent in referents:
            nom = referent.get("nom", "") if isinstance(referent, dict) else str(referent)
            if nom:
                noms.append(nom)
        return ", ".join(noms) if noms else "Référents à renseigner"
    
    def align_pole_card_labels(self, cards):
        for category in ("nom", "description", "referents", "missions", "taches"):
            labels = [card.pole_labels[category] for card in cards if category in card.pole_labels]
            if labels:
                max_height = max(label.height for label in labels)
                for label in labels:
                    label.height = max_height

    def display_pole_preview(self, pole, parent=None):
        card = self.create_card(padding=12, spacing=7)
        card.size_hint = (1, None)
        card.pole_labels = {}
        card.pole_labels["nom"] = self.add_to_card(card, pole.get("nom", "Pôle"), font_size="16sp", bold=True, color=self.COLOR_PRIMARY)
        description = pole.get("description", "")
        if description:
            card.pole_labels["description"] = self.add_to_card(card, description, font_size="12sp", color=self.COLOR_MUTED)
        referents = pole.get("referents", []) or pole.get("referent", [])
        if isinstance(referents, (dict, str)):
            referents = [referents]
        noms = [r.get("nom", "") if isinstance(r, dict) else str(r) for r in referents]
        noms = [nom for nom in noms if nom]
        if noms:
            card.pole_labels["referents"] = self.add_to_card(card, "Référent(s) : " + ", ".join(noms), font_size="11sp", color=self.COLOR_SECONDARY)
        missions = pole.get("missions", []) or []
        if missions:
            card.pole_labels["missions"] = self.add_to_card(card, "{} mission(s)".format(len(missions)), font_size="11sp", color=self.COLOR_MUTED)
        taches = pole.get("taches", []) or []
        if taches:
            terminees = sum(1 for t in taches if isinstance(t, dict) and str(t.get("statut", "")).strip().lower() in ("terminee", "terminée", "termine", "terminé", "faite", "fait", "completed", "done", "true", "1"))
            restantes = len(taches) - terminees
            card.pole_labels["taches"] = self.add_to_card(card, "Tâches : {} terminée(s) / {} à faire".format(terminees, restantes), font_size="11sp", color=self.COLOR_MUTED)
        button = Button(text="Voir la fiche", size_hint_y=None, height=dp(38), background_normal="", background_down="", background_color=get_color_from_hex(self.COLOR_ACCENT), color=get_color_from_hex(self.COLOR_PRIMARY), font_size="11sp", bold=True)
        button.bind(on_release=lambda instance, selected=pole: self.open_pole(selected))
        card.add_widget(button)
        return card

    def open_pole(self, pole):
        self.current_tab = "poles"
        self.selected_pole = pole
        self.display_current_tab()

    def display_pole_detail(self, pole):
        # Retour
        back_button = Button(
            text="‹  Retour aux pôles",
            size_hint_y=None,
            height=dp(38),
            background_normal="",
            background_down="",
            background_color=get_color_from_hex(self.COLOR_ACCENT),
            color=get_color_from_hex(self.COLOR_PRIMARY),
            font_size="13sp",
            bold=True
        )
        back_button.bind( on_release=lambda instance: self.back_to_poles())
        self.content.add_widget(back_button)
        # Présentation du pôle
        card = self.create_card(padding=18,spacing=8, color=self.COLOR_SECONDARY )
        self.add_to_card(card, pole.get("nom", "Pôle"),font_size="21sp", bold=True,color=self.COLOR_WHITE)
        self.add_to_card(card,pole.get("description", ""),font_size="13sp",color=self.COLOR_PALE_BLUE )
        self.content.add_widget(card)
        # ---------------------------------------------------------
        # RÉFÉRENTS DU PÔLE
        # ---------------------------------------------------------
        self.add_section_title("Les référents du pôle")
        referents = pole.get("referents", []) or []
        # Compatibilité avec l'ancien format YAML
        if not referents:
            old_referent = pole.get("referent", "")
            if old_referent:
                referents = [old_referent]
        # Normalisation des formats dict et str
        if isinstance(referents, (dict, str)):
            referents = [referents]
        if referents:
            for referent in referents:
                # Une nouvelle carte pour chaque référent
                referent_card = self.create_card(padding=14,spacing=8)
                if isinstance(referent, dict):
                    nom = referent.get("nom", "Nom du responsable")
                    telephone = referent.get("telephone", "")
                    email = referent.get("email", "")
                    self.add_to_card(
                        referent_card,
                        nom,
                        font_size="16sp",
                        bold=True,
                        color=self.COLOR_PRIMARY
                    )
                    if telephone:
                        self.add_card_button(
                            referent_card,
                            "Appeler : {}".format(telephone),
                            "tel:" + str(telephone),color="#16A34A"
                        )
                    if email:
                        self.add_card_button(
                            referent_card,
                            "Envoyer un email",
                            "mailto:" + str(email),color="#6B7280"
                        )
                else:
                    self.add_to_card(referent_card,str(referent),font_size="14sp")
                # Ajout une seule fois dans le contenu
                self.content.add_widget(referent_card)
        else:
            self.add_empty_message( "Aucun référent renseigné pour ce pôle." )
        # ---------------------------------------------------------
        # MISSIONS
        # ---------------------------------------------------------
        self.add_section_title("Ses missions")
        missions = pole.get("missions", []) or []
        if missions:
            mission_card = self.create_card()
            for mission in missions:
                if isinstance(mission, dict):
                    mission_text = mission.get("titre", "")
                else:
                    mission_text = str(mission)
                self.add_to_card(
                    mission_card,
                    "• " + mission_text,
                    font_size="13sp"
                )
            self.content.add_widget(mission_card)
        else:
            self.add_empty_message( "Les missions de ce pôle seront bientôt renseignées." )
        # ---------------------------------------------------------
        # MEMBRES
        # ---------------------------------------------------------
        members = pole.get("membres", []) or []
        if members:
            self.add_section_title("Les membres")
            members_card = self.create_card()
            for member in members:
                if isinstance(member, dict):
                    member_name = member.get("nom", "")
                    member_role = member.get("role", "")
                    text = member_name
                    if member_role:
                        text += " – " + member_role
                else:
                    text = str(member)
                self.add_to_card(
                    members_card,
                    "• " + text,
                    font_size="13sp"
                )
            self.content.add_widget(members_card)
        # --------------------------------------------------------
        # TÂCHES
        # ---------------------------------------------------------
        tasks = pole.get("taches", []) or []
        if tasks:
            self.add_section_title("Tâches et organisation")
            tasks_card = self.create_card(padding=12, spacing=8)
            for task in tasks:
                if isinstance(task, dict):
                    task_title = task.get("titre", "Tâche")
                    task_status = str(task.get("statut", "")).strip().lower()
                    completion_date = task.get("date_completion", "")
                    is_completed = task_status in ("terminee", "terminée", "termine", "terminé", "faite", "fait", "completed", "done", "true", "1")
                else:
                    task_title = str(task)
                    is_completed = False
                    completion_date = ""
                task_row = BoxLayout(orientation="horizontal", size_hint_y=None, spacing=dp(8), padding=[0, dp(4), 0, dp(4)])
                task_label = self.make_label(task_title, font_size="13sp", color=self.COLOR_TEXT)
                task_label.size_hint_x = 1
                task_label.halign = "left"
                task_label.valign = "middle"
                task_row.add_widget(task_label)
                if is_completed:
                    status_text = "✓ Terminée"
                    if completion_date:
                        status_text += " (" + str(completion_date) + ")"
                    status_label = self.make_label(status_text, font_size="10sp", color="#16A34A", bold=True)
                    status_label.font_name = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "assets", "fonts", "DejaVuSans.ttf")
                    status_label.size_hint_x = None
                    status_label.width = dp(150)
                    status_label.text_size = (None, None)
                    status_label.halign = "right"
                    status_label.valign = "middle"
                    task_row.add_widget(status_label)
                task_row.bind(minimum_height=task_row.setter("height"))
                tasks_card.add_widget(task_row)
            self.content.add_widget(tasks_card)
        # ---------------------------------------------------------
        # DOCUMENTS DU PÔLE
        # ---------------------------------------------------------
        self.add_section_title("Documents associés")
        documents = pole.get("documents", []) or []
        if documents:
            self.display_document_list(documents)
        else:
            self.add_empty_message( "Aucun document associé à ce pôle.")
        # ---------------------------------------------------------
        # PROCHAINE RÉUNION
        # ---------------------------------------------------------
        next_meeting = pole.get("prochaine_reunion", "")
        if next_meeting:
            self.add_section_title("Prochaine réunion")
            meeting_card = self.create_card()
            self.add_to_card( meeting_card,str(next_meeting), font_size="14sp")
            self.content.add_widget(meeting_card)
        # Espace de sécurité en bas de page
        self.add_bottom_safe_spacing()

    def back_to_poles(self):
        self.selected_pole = None
        self.display_current_tab()
    # ---------------------------------------------------------
    # ONGLET DOCUMENTS
    # ---------------------------------------------------------
    def display_documents(self):
        self.add_title( "Documents", "Tous les documents utiles à l'organisation du tournoi.")
        documents = self.benevoles_data.get(
            "documents", []
        ) or []
        self.add_section_title("Documents généraux")
        if documents:
            self.display_document_list(documents)
        else:
            self.add_empty_message("Aucun document général disponible.")
        self.add_section_title("Documents des pôles")
        poles = self.benevoles_data.get("poles", []) or []
        has_pole_documents = False
        for pole in poles:
            pole_documents = pole.get(
                "documents", []
            ) or []
            if not pole_documents:
                continue
            has_pole_documents = True
            self.content.add_widget(self.make_label(
                pole.get("nom", "Pôle"),
                font_size="15sp",
                bold=True,
                color=self.COLOR_WHITE
            ))
            self.display_document_list(pole_documents)
        if not has_pole_documents:
            self.add_empty_message("Aucun document associé aux pôles.")
        self.add_bottom_safe_spacing()

    def display_document_list(self, documents):
        for document in documents:
            if isinstance(document, str):
                document = {"nom": document,"url": ""}
            card = self.create_card(padding=12, spacing=5)
            # Nom du document
            nom_document = (
                document.get("nom")
                or document.get("titre")
                or "Document"
            )
            self.add_to_card( card, nom_document, font_size="14sp",bold=True,color=self.COLOR_PRIMARY)
            # Description
            if document.get("description"):
                self.add_to_card(card,document.get("description"),font_size="12sp",color=self.COLOR_MUTED)
            # Catégorie
            if document.get("categorie"):
                self.add_to_card(card,"Catégorie : " + str(document.get("categorie")),font_size="11sp",color=self.COLOR_MUTED )
            # Document important en rouge
            if document.get("important", False):
                self.add_to_card(
                    card,
                    "Document important",
                    font_size="11sp",
                    bold=True,
                    color="#DC2626"
                )
            # Lien
            url = document.get("url", "")
            if url:
                self.add_card_button(card,"Ouvrir le document",url)
            else:
                self.add_to_card(card,"Lien à renseigner",font_size="11sp",color=self.COLOR_MUTED)
            self.content.add_widget(card)
    # ---------------------------------------------------------
    # NAVIGATION RETOUR
    # ---------------------------------------------------------
    def add_back_button(self, destination):
        button = Button(text="Retour",size_hint_y=None,height=dp(42),background_normal="",background_down="",background_color=get_color_from_hex( self.COLOR_ACCENT),
            color=get_color_from_hex(
                self.COLOR_PRIMARY
            ), bold=True)
        button.bind(on_release=lambda instance:self.change_tab(destination))
        self.content.add_widget(button)
    # ---------------------------------------------------------
    # AUTHENTIFICATION
    # ---------------------------------------------------------
    def on_pre_enter(self, *args):
        app = App.get_running_app()
        authenticated = app.config.get(
            "Benevoles",
            "authenticated",
            fallback="0"
        ) == "1"
        if not authenticated:
            if app.root and hasattr(app.root, "switch_screen"):
                app.root.switch_screen("login_benevoles")

    def add_bottom_safe_spacing(self):
        """
        Ajoute un espace invisible en bas du contenu
        pour éviter que les éléments soient masqués
        par les zones tactiles Android.
        """
        self.content.add_widget(
            Widget(size_hint_y=None, height=dp(50))
        )
    
    def logout(self, instance=None):
        app = App.get_running_app()
        if not app.config.has_section("Benevoles"):
            app.config.add_section("Benevoles")
        app.config.set("Benevoles","authenticated","0")
        app.config.set("Benevoles", "credentials_hash", "" )
        app.config.write()
        if app.root and hasattr(app.root, "switch_screen"):
            app.root.switch_screen("login_benevoles")
    # ---------------------------------------------------------
    # OUVERTURE DES LIENS
    # ---------------------------------------------------------
    def open_url(self, url):
        if not url:
            return
        url = str(url).strip()
        try:
            parsed = urlparse(url)
            scheme = parsed.scheme.lower()
            if scheme not in ("http", "https", "mailto", "tel"):
                print("[BENEVOLES] Type de lien non autorise :", url)
                return
            if scheme == "tel":
                import re
                numero = re.sub(r"[^\d+]", "", parsed.path)
                if not numero:
                    print("[BENEVOLES] Numero invalide.")
                    return
                if platform == "android":
                    from jnius import autoclass
                    Intent = autoclass("android.content.Intent")
                    Uri = autoclass("android.net.Uri")
                    PythonActivity = autoclass("org.kivy.android.PythonActivity")
                    intent = Intent(Intent.ACTION_DIAL,Uri.parse("tel:" + numero))
                    PythonActivity.mActivity.startActivity(intent)
                elif platform == "ios":
                    from pyobjus import autoclass
                    UIApplication = autoclass("UIApplication")
                    NSURL = autoclass("NSURL")
                    nsurl = NSURL.URLWithString_("tel:" + numero)
                    if nsurl is None:
                        print("[BENEVOLES] Numero invalide :", numero)
                        return
                    app_instance = UIApplication.sharedApplication()
                    app_instance.openURL_options_completionHandler_( nsurl, None, None )
                else:
                    webbrowser.open("tel:" + numero)
                return
            if scheme in ("http", "https") and not parsed.netloc:
                print("[BENEVOLES] URL invalide :", url)
                return
            if platform == "ios":
                from pyobjus import autoclass
                UIApplication = autoclass("UIApplication")
                NSURL = autoclass("NSURL")
                nsurl = NSURL.URLWithString_(url)
                if nsurl is None:
                    print("[BENEVOLES] URL invalide :", url)
                    return
                app_instance = UIApplication.sharedApplication()
                app_instance.openURL_options_completionHandler_( nsurl, None, None)
            else:
                webbrowser.open(url)
        except Exception as error:
            print("[BENEVOLES] Impossible d'ouvrir le lien :", error)
    # ---------------------------------------------------------
    # ANNUAIRE DES CONTACTS
    # ---------------------------------------------------------
    def sort_annuaire(self, contacts):
        """Trie les contacts par fonction par ordre alphabétique."""
        return sorted(
            contacts,
            key=lambda contact: str(
                contact.get("fonction", "") or ""
            ).strip().casefold()
        )
    
    def display_annuaire(self):
        self.add_title(
            "Annuaire des contacts",
            "Retrouve facilement les prestataires et interlocuteurs du tournoi."
        )
        contacts = self.benevoles_data.get("annuaire", []) or []
        if not isinstance(contacts, list):
            contacts = []
        # Champ de recherche
        search_card = self.create_card(padding=12, spacing=7)
        self.add_to_card(search_card,"Rechercher un contact",font_size="14sp", bold=True,color=self.COLOR_PRIMARY)
        self.annuaire_search_input = TextInput(
            hint_text="Nom, prénom, fonction, entreprise, téléphone...",
            multiline=False,
            size_hint_y=None,
            height=dp(46),
            font_size="14sp",
            padding=[dp(10), dp(12)],
            background_normal="",
            background_active="",
            background_color=get_color_from_hex(self.COLOR_LIGHT_BLUE),
            foreground_color=get_color_from_hex(self.COLOR_TEXT),
            hint_text_color=get_color_from_hex(self.COLOR_MUTED),
            cursor_color=get_color_from_hex(self.COLOR_PRIMARY)
        )
        search_card.add_widget(self.annuaire_search_input)
        self.content.add_widget(search_card)
        # Compteur de résultats
        self.annuaire_count_label = self.make_label( "",font_size="12sp",color=self.COLOR_PALE_BLUE)
        self.content.add_widget(self.annuaire_count_label)
        # Conteneur des résultats
        self.annuaire_results = BoxLayout(orientation="vertical",size_hint_y=None, spacing=dp(10))
        self.annuaire_results.bind(minimum_height=self.annuaire_results.setter("height"))
        self.content.add_widget(self.annuaire_results)
        # Recherche instantanée
        self.annuaire_search_input.bind(text=self.filter_annuaire)
        self.filter_annuaire(self.annuaire_search_input, "")
        self.add_bottom_safe_spacing()
    
    def filter_annuaire(self, instance, search_text):
        """Filtre les contacts selon les mots recherchés."""
        self.annuaire_results.clear_widgets()
        contacts = self.benevoles_data.get("annuaire", []) or []
        if not isinstance(contacts, list):
            contacts = []
        search_text = str(search_text).strip().lower()
        filtered_contacts = []
        for contact in contacts:
            if not isinstance(contact, dict):
                continue
            searchable_fields = [
                contact.get("fonction", ""),
                contact.get("entreprise", ""),
                contact.get("nom", ""),
                contact.get("prenom", ""),
                contact.get("telephone", ""),
                contact.get("adresse", ""),
                contact.get("email", "")
            ]
            searchable_text = " ".join( str(value) for value in searchable_fields if value).lower()
            if search_text in searchable_text:
                filtered_contacts.append(contact)
        # Tri alphabétique par fonction
        filtered_contacts = self.sort_annuaire(filtered_contacts)
        self.annuaire_count_label.text = ("{} contact(s) trouvé(s)".format(len(filtered_contacts)))
        if not filtered_contacts:
            card = self.create_card()
            message = (
                "Aucun contact ne correspond à ta recherche."
                if search_text
                else "Aucun contact n'est encore renseigné dans l'annuaire."
            )
            self.add_to_card(card,message,font_size="13sp",color=self.COLOR_MUTED)
            self.annuaire_results.add_widget(card)
            return
        # Affichage des contacts
        for contact in filtered_contacts:
            self.display_contact_card(contact,parent=self.annuaire_results)
    
    def display_contact_card(self, contact, parent=None):
        """Affiche une fiche de contact."""
        if parent is None:
            parent = self.content
        card = self.create_card(padding=14, spacing=7)
        # Fonction
        fonction = contact.get("fonction", "Contact")
        self.add_to_card(card, fonction, font_size="16sp", bold=True,color=self.COLOR_PRIMARY)
        # Entreprise
        entreprise = contact.get("entreprise", "")
        if entreprise:
            self.add_to_card( card, entreprise, font_size="13sp",bold=True,color=self.COLOR_SECONDARY)
        # Nom et prénom
        nom = " ".join(
            str(value).strip()
            for value in [
                contact.get("prenom", ""),
                contact.get("nom", "")
            ]
            if value
        )
        if nom:
            self.add_to_card( card, "Contact : {}".format(nom),font_size="13sp" )
        # Adresse
        adresse = contact.get("adresse", "")
        if adresse:
            self.add_to_card( card,"Adresse : {}".format(adresse),font_size="12sp", color=self.COLOR_MUTED)
        # Téléphone
        telephone = contact.get("telephone", "")
        if telephone:
            self.add_card_button(card,"Appeler : {}".format(telephone),"tel:" + str(telephone).replace(" ", ""),color="#16A34A" )
        # Email
        email = contact.get("email", "")
        if email:
            self.add_card_button( card,"Envoyer un email","mailto:" + str(email),color="#6B7280")
        parent.add_widget(card)
    # ---------------------------------------------------------
    # PLANNING
    # ---------------------------------------------------------
    def display_planning(self):
        self.add_title("Planning","Retrouve les affectations des bénévoles par journée et par tournoi.")
        # benevoles_data correspond déjà à tournoi > appli > benevoles.
        sheet_url = (self.benevoles_data.get("planning_google_sheet", "")
            if isinstance(self.benevoles_data, dict)
            else ""
        )
        planning_view = PlanningScreen(sheet_url=sheet_url)
        self.content.add_widget(planning_view)
        self.add_bottom_safe_spacing()
