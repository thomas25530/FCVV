# -*- coding: utf-8 -*-
"""
Écran de consultation des stocks des bénévoles.
Google Sheets attendu :
- Articles
- Mouvements
Le classeur doit être partagé en lecture avec toute personne disposant du lien.
Organisation :
1. Vue d'ensemble : indicateurs et alertes.
2. Articles : stocks disponibles par catégorie.
3. Distributions : quantités distribuées par pôle.
"""
import re
import ssl
import threading
import urllib.request
import webbrowser
import zipfile
import xml.etree.ElementTree as ET

from collections import defaultdict
from io import BytesIO

try:
    import certifi
except ImportError:
    certifi = None

from kivy.clock import Clock
from kivy.metrics import dp
from kivy.utils import get_color_from_hex
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.widget import Widget
from kivy.utils import platform

# =============================================================
# LECTEUR XLSX
# =============================================================
class _XlsxReader:
    """
    Lecteur XLSX minimaliste.
    Lit les noms des feuilles, les cellules texte et numériques,
    les chaînes partagées et les valeurs calculées des formules.
    """
    NS_REL = (
        "http://schemas.openxmlformats.org/"
        "officeDocument/2006/relationships"
    )
    
    def __init__(self, file_bytes):
        self.archive = zipfile.ZipFile(BytesIO(file_bytes), "r")
        self.shared_strings = self._read_shared_strings()
        self.sheets = self._read_sheet_names()

    @staticmethod
    def _local_name(tag):
        return tag.split("}")[-1]

    def _find_child(self, element, name):
        for child in element:
            if self._local_name(child.tag) == name:
                return child
        return None

    def _read_shared_strings(self):
        path = "xl/sharedStrings.xml"
        if path not in self.archive.namelist():
            return []
        root = ET.fromstring(self.archive.read(path))
        values = []
        for item in root:
            if self._local_name(item.tag) != "si":
                continue
            text_parts = []
            for element in item.iter():
                if self._local_name(element.tag) == "t":
                    text_parts.append(element.text or "")
            values.append("".join(text_parts))
        return values

    def _read_sheet_names(self):
        workbook_path = "xl/workbook.xml"
        rels_path = "xl/_rels/workbook.xml.rels"
        workbook_root = ET.fromstring(self.archive.read(workbook_path) )
        rels_root = ET.fromstring( self.archive.read(rels_path))
        relationships = {}
        for rel in rels_root:
            if self._local_name(rel.tag) != "Relationship":
                continue
            relationships[rel.attrib.get("Id")] = (rel.attrib.get("Target"))
        sheets = {}
        for sheet in workbook_root.iter():
            if self._local_name(sheet.tag) != "sheet":
                continue
            name = sheet.attrib.get("name", "")
            rel_id = sheet.attrib.get("{%s}id" % self.NS_REL)
            target = relationships.get(rel_id)
            if not target:
                continue
            if target.startswith("/"):
                path = target.lstrip("/")
            elif target.startswith("xl/"):
                path = target
            else:
                path = "xl/" + target
            parts = []
            for part in path.split("/"):
                if part == "..":
                    if parts:
                        parts.pop()
                elif part and part != ".":
                    parts.append(part)
            sheets[name] = "/".join(parts)
        return sheets

    @staticmethod
    def _column_index(cell_reference):
        letters = re.match(r"[A-Z]+", cell_reference or "")
        if not letters:
            return None
        result = 0
        for char in letters.group(0):
            result = (
                result * 26
                + ord(char) - ord("A") + 1
            )
        return result - 1

    def _read_cell_value(self, cell):
        cell_type = cell.attrib.get("t", "")
        value_element = self._find_child(cell, "v")
        if cell_type == "inlineStr":
            inline = self._find_child(cell, "is")
            if inline is None:
                return ""
            return "".join(
                element.text or ""
                for element in inline.iter()
                if self._local_name(element.tag) == "t"
            )
        if value_element is None or value_element.text is None:
            return None
        value = value_element.text
        if cell_type == "s":
            try:
                return self.shared_strings[int(value)]
            except (ValueError, IndexError):
                return ""
        if cell_type in ("str", "e"):
            return value
        try:
            number = float(value)
            if number.is_integer():
                return int(number)
            return number
        except (ValueError, TypeError):
            return value

    def read_sheet(self, sheet_name):
        path = self.sheets.get(sheet_name)
        if not path or path not in self.archive.namelist():
            return []
        root = ET.fromstring(self.archive.read(path))
        rows = []
        for row_element in root.iter():
            if self._local_name(row_element.tag) != "row":
                continue
            row_values = {}
            for cell in row_element:
                if self._local_name(cell.tag) != "c":
                    continue
                reference = cell.attrib.get("r", "")
                column = self._column_index(reference)
                if column is None:
                    continue
                row_values[column] = self._read_cell_value(cell)
            if not row_values:
                continue
            max_column = max(row_values.keys())
            row = [None] * (max_column + 1)
            for column, value in row_values.items():
                row[column] = value
            rows.append(row)
        return rows
# =============================================================
# ÉCRAN DE STOCK
# =============================================================
class StockScreen(BoxLayout):
    # ---------------------------------------------------------
    # COULEURS
    # ---------------------------------------------------------
    COLOR_PRIMARY = "#1E3A8A"
    COLOR_SECONDARY = "#334B78"
    COLOR_ACCENT = "#F7ED40"

    COLOR_TEXT = "#243B53"
    COLOR_MUTED = "#65758B"
    COLOR_WHITE = "#FFFFFF"

    COLOR_CARD = "#FFFFFF"
    COLOR_BORDER = "#DCE5F2"
    COLOR_LIGHT_BLUE = "#EAF0FF"

    COLOR_SUCCESS = "#219653"
    COLOR_WARNING = "#F2994A"
    COLOR_DANGER = "#DC2626"

    COLOR_TAB_INACTIVE = "#EAF0FF"
    # ---------------------------------------------------------
    # INITIALISATION
    # ---------------------------------------------------------
    def __init__( self,sheet_url="",fixed_container=None, **kwargs):
        super().__init__(orientation="vertical",spacing=dp(10),size_hint_y=None,**kwargs)
        self.sheet_url = str(sheet_url or "").strip()
        self.fixed_container = fixed_container
        self.is_active = True
        self.is_loading = False
        self.articles = []
        self.movements = []
        self.last_refresh_success = False
        # Onglet sélectionné par défaut.
        self.current_tab = "overview"
        self.bind(minimum_height=self.setter("height") )
        # Zone de contenu.
        self.body = BoxLayout(orientation="vertical",spacing=dp(10),size_hint_y=None)
        self.body.bind(minimum_height=self.body.setter("height"))
        self.add_widget(self.body)
        # Boutons fixes dans le conteneur parent.
        self._build_fixed_controls()
        self._show_loading()
        Clock.schedule_once(lambda dt: self.refresh(), 0.2)
    # ---------------------------------------------------------
    # OUTILS GRAPHIQUES
    # ---------------------------------------------------------
    @staticmethod
    def _color(value):
        return get_color_from_hex(value)

    def get_sp(self, value):
        return "{}sp".format(value)

    def make_label( self,text,font_size=14,color=None,bold=False,height=None,halign="left"):
        label = Label(
            text=str(text),
            font_size=self.get_sp(font_size),
            color=self._color(color or self.COLOR_TEXT),
            bold=bold,
            halign=halign,
            valign="middle",
            size_hint_y=None
        )
        label.bind(
            width=lambda instance, width: setattr(
                instance,
                "text_size",
                (max(1, width), None)
            )
        )
        if height is None:
            def update_height(instance, texture_size):
                instance.height = max(dp(24),texture_size[1] + dp(8))
            label.bind(texture_size=update_height)
            label.texture_update()
            label.height = max( dp(24),label.texture_size[1] + dp(8))
        else:
            label.height = dp(height)
        return label

    def create_card(self,padding=14,spacing=7, color=None):
        card = BoxLayout(orientation="vertical",size_hint_y=None, padding=dp(padding),spacing=dp(spacing))
        card.bind(minimum_height=card.setter("height"))
        with card.canvas.before:
            from kivy.graphics import Color, RoundedRectangle
            Color(*self._color(color or self.COLOR_CARD))
            card.background = RoundedRectangle(pos=card.pos, size=card.size, radius=[dp(14)])
        card.bind(
            pos=lambda instance, value: setattr(
                instance.background,
                "pos",
                value
            ),
            size=lambda instance, value: setattr(
                instance.background,
                "size",
                value
            )
        )
        return card

    def add_to_card(self,card,text, font_size=13, color=None,bold=False):
        label = self.make_label(text, font_size=font_size, color=color, bold=bold)
        card.add_widget(label)
        return label

    def add_section_title(self, text):
        self.body.add_widget(self.make_label(text,font_size=16,color=self.COLOR_PRIMARY,bold=True))

    def add_category_title(self, category):
        """Ajoute un titre de catégorie bien visible."""
        title = BoxLayout(orientation="vertical",size_hint_y=None,height=dp(42),padding=[dp(12), dp(5)])
        with title.canvas.before:
            from kivy.graphics import Color, RoundedRectangle
            Color(*self._color(self.COLOR_PRIMARY))
            title.background = RoundedRectangle( pos=title.pos,size=title.size, radius=[dp(8)])
        title.bind(
            pos=lambda instance, value: setattr(
                instance.background, "pos", value
            ),
            size=lambda instance, value: setattr(
                instance.background, "size", value
            )
        )
        label = self.make_label(category.upper(),font_size=15,color=self.COLOR_WHITE,bold=True,height=dp(32))
        title.add_widget(label)
        self.body.add_widget(title)
    
    def add_empty_message(self, text):
        card = self.create_card()
        self.add_to_card( card, text, font_size=13,color=self.COLOR_MUTED )
        self.body.add_widget(card)
    # ---------------------------------------------------------
    # NAVIGATION : TROIS ONGLETS
    # ---------------------------------------------------------

    def _build_tabs(self):
        self.tabs_bar.clear_widgets()
        self.tab_buttons = {}
        tabs = [
            ("overview", "Vue d'ensemble"),
            ("articles", "Articles"),
            ("distributions", "Distributions")
        ]
        for tab_id, label in tabs:
            button = Button(
                text=label,
                size_hint_x=1,
                size_hint_y=1,
                height=dp(44),
                font_size=self.get_sp(11),
                bold=True,
                background_normal="",
                background_down="",
                background_color=self._color(
                    self.COLOR_TAB_INACTIVE
                ),
                color=self._color(self.COLOR_PRIMARY)
            )
            button.bind( on_release=lambda instance, selected=tab_id: self.change_tab(selected))
            self.tabs_bar.add_widget(button)
            self.tab_buttons[tab_id] = button
        self._update_tab_buttons()

    def _update_tab_buttons(self):
        for tab_id, button in self.tab_buttons.items():
            if tab_id == self.current_tab:
                button.background_color = self._color(self.COLOR_PRIMARY)
                button.color = self._color(self.COLOR_WHITE)
            else:
                button.background_color = self._color( self.COLOR_TAB_INACTIVE)
                button.color = self._color(self.COLOR_PRIMARY)

    def change_tab(self, tab):
        if tab not in ("overview","articles","distributions"):
            return
        self.current_tab = tab
        self._update_tab_buttons()
        if self.last_refresh_success:
            self.display_stock()
    # ---------------------------------------------------------
    # BOUTONS FIXES
    # ---------------------------------------------------------
    def _build_fixed_controls(self):
        if self.fixed_container is None:
            return
        buttons_row = BoxLayout(orientation="horizontal",size_hint_y=None,height=dp(42),spacing=dp(8))
        manage_button = Button(
            text="Gérer le stock",
            size_hint=(0.5, 1),
            background_normal="",
            background_down="",
            background_color=self._color(self.COLOR_ACCENT),
            color=self._color(self.COLOR_PRIMARY),
            font_size=self.get_sp(13),
            bold=True
        )
        manage_button.bind(on_release=lambda instance: self.open_google_sheet())
        refresh_button = Button(
            text="Actualiser",
            size_hint=(0.5, 1),
            background_normal="",
            background_down="",
            background_color=self._color(self.COLOR_LIGHT_BLUE),
            color=self._color(self.COLOR_PRIMARY),
            font_size=self.get_sp(13),
            bold=True
        )
        refresh_button.bind(on_release=lambda instance: self.refresh())
        buttons_row.add_widget(manage_button)
        buttons_row.add_widget(refresh_button)
    
        self.fixed_container.add_widget(buttons_row)
    
        self.tabs_bar = BoxLayout(
            orientation="horizontal",
            spacing=dp(5),
            size_hint_y=None,
            height=dp(44)
        )
    
        self._build_tabs()
    
        self.fixed_container.add_widget(self.tabs_bar)
    
        self.manage_button = manage_button
        self.refresh_button = refresh_button

    def open_google_sheet(self):
        if not self.sheet_url:
            self._set_status( "L'adresse du Google Sheet n'est pas renseignée." )
            return
        try:
            webbrowser.open(self.sheet_url)
        except Exception as error:
            print("[STOCK] Impossible d'ouvrir le Google Sheet :", error)
    # ---------------------------------------------------------
    # ÉTATS DE L'ÉCRAN
    # ---------------------------------------------------------
    def _clear_body(self):
        self.body.clear_widgets()
        self.body.height = 0
        self.body.minimum_height = 0

    def _show_loading(self):
        self._clear_body()
    
        loading_container = BoxLayout( orientation="vertical",size_hint_y=None, height=dp(90), padding=[dp(10), dp(15)],spacing=dp(5))
        loading_label = self.make_label(
            "Chargement des données du stock...",
            font_size=14,
            color=self.COLOR_MUTED,
            bold=True,
            halign="center",
            height=dp(35)
        )
        loading_container.add_widget(loading_label)
        self.body.add_widget(loading_container)

    def _set_status(self, message):
        self._clear_body()
        card = self.create_card()
        self.add_to_card(card,message, font_size=13,color=self.COLOR_MUTED)
        self.body.add_widget(card)

    def deactivate(self):
        """
        Empêche un chargement terminé en arrière-plan de modifier
        un écran qui n'est plus affiché.
        """
        self.is_active = False

    # ---------------------------------------------------------
    # TÉLÉCHARGEMENT GOOGLE SHEETS
    # ---------------------------------------------------------
    def _extract_sheet_id(self):
        match = re.search(r"/spreadsheets/d/([a-zA-Z0-9_-]+)",self.sheet_url)
        if match:
            return match.group(1)
        return None

    def _download_xlsx(self):
        sheet_id = self._extract_sheet_id()
        if not sheet_id:
            raise ValueError("L'adresse du Google Sheet semble incorrecte.")
        url = (
            "https://docs.google.com/spreadsheets/d/"
            + sheet_id
            + "/export?format=xlsx"
        )
        request = urllib.request.Request( url,headers={"User-Agent": "Mozilla/5.0" })
        if platform == "win":
            ssl_context = ssl.create_default_context()
        else:
            ssl_context = ssl.create_default_context(cafile=certifi.where())
        with urllib.request.urlopen(request,timeout=30, context=ssl_context) as response:
            data = response.read()
        if not data:
            raise ValueError("Le fichier téléchargé est vide.")
        if not data.startswith(b"PK"):
            raise ValueError(
                "Google n'a pas renvoyé un fichier XLSX. "
                "Vérifie le partage du document."
            )
        return data
    # ---------------------------------------------------------
    # ACTUALISATION
    # ---------------------------------------------------------

    def refresh(self):
        if self.is_loading:
            return
        if not self.sheet_url:
            self._set_status("Aucun Google Sheet de stock n'est configuré." )
            return
        self.is_loading = True
        if hasattr(self, "refresh_button"):
            self.refresh_button.text = "Chargement..."
        self._show_loading()
        thread = threading.Thread(target=self._refresh_worker,daemon=True)
        thread.start()

    def _refresh_worker(self):
        try:
            file_bytes = self._download_xlsx()
            reader = _XlsxReader(file_bytes)
            articles_rows = reader.read_sheet("Articles")
            movements_rows = reader.read_sheet("Mouvements")
            articles = self._parse_articles(articles_rows)
            movements = self._parse_movements(movements_rows)
            result = {"articles": articles,"movements": movements,"error": None }
        except Exception as error:
            print("[STOCK] Erreur de chargement :", error)
            result = {
                "articles": [],
                "movements": [],
                "error": str(error)
            }
        Clock.schedule_once(lambda dt: self._finish_refresh(result), 0)

    def _finish_refresh(self, result):
        self.is_loading = False
        if hasattr(self, "refresh_button"):
            self.refresh_button.text = "Actualiser"
        if not self.is_active:
            return
        if result["error"]:
            self.last_refresh_success = False
            self._set_status(
                "Impossible de charger le stock.\n\n"
                + result["error"]
                + "\n\nVérifie que le Google Sheet est partagé "
                "en lecture avec toute personne disposant du lien."
            )
            return
        self.articles = result["articles"]
        self.movements = result["movements"]
        self.last_refresh_success = True
        self.display_stock()
    # ---------------------------------------------------------
    # OUTILS DE LECTURE
    # ---------------------------------------------------------
    @staticmethod
    def _get_cell(row, index, default=None):
        if index < len(row):
            value = row[index]
            if value is not None:
                return value
        return default

    @staticmethod
    def _to_float(value, default=0):
        if value is None or value == "":
            return default
        if isinstance(value, (int, float)):
            return float(value)
        text = str(value).strip()
        text = text.replace("\u00a0", "").replace(" ", "")
        text = text.replace(",", ".")
        try:
            return float(text)
        except (ValueError, TypeError):
            return default

    @staticmethod
    def _to_text(value, default=""):
        if value is None:
            return default
        return str(value).strip()
    # ---------------------------------------------------------
    # LECTURE DES ARTICLES
    # ---------------------------------------------------------
    def _parse_articles(self, rows):
        if not rows:
            return []
        articles = []
        for row in rows[1:]:
            reference = self._to_text(self._get_cell(row, 0))
            designation = self._to_text(self._get_cell(row, 1))
            if not reference and not designation:
                continue
            article = {
                "reference": reference,
                "designation": designation or "Article sans nom",
                "categorie": self._to_text(
                    self._get_cell(row, 2),
                    "Autre"
                ) or "Autre",
                "unite": self._to_text(
                    self._get_cell(row, 3),
                    "unité"
                ) or "unité",
                "stock_initial": self._to_float(self._get_cell(row, 4)),

                "seuil_alerte": self._to_float(self._get_cell(row, 8)),
                "emplacement": self._to_text( self._get_cell(row, 9)),
                "entrees": 0,
                "sorties": 0,
                "stock_disponible": 0
            }
            articles.append(article)
        return articles
    # ---------------------------------------------------------
    # LECTURE DES MOUVEMENTS
    # ---------------------------------------------------------
    def _parse_movements(self, rows):
        if not rows:
            return []
        movements = []
        for row in rows[1:]:
            reference = self._to_text(self._get_cell(row, 1))
            movement_type = self._to_text( self._get_cell(row, 2))
            if not reference or not movement_type:
                continue
            movement = {
                "date": self._format_sheet_date( self._get_cell(row, 0)),
                "reference": reference,
                "type": movement_type,
                # Désignation facultative conservée en mémoire,
                # mais elle ne sert pas à créer les cartes.
                "designation": self._to_text(self._get_cell(row, 3) ),
                "pole": self._to_text(
                    self._get_cell(row, 4),
                    "À définir"
                ) or "À définir",
                "responsable": self._to_text( self._get_cell(row, 5)),
                "quantite": self._to_float(self._get_cell(row, 6)),
                "commentaire": self._to_text(self._get_cell(row, 8)),
                "periode": self._to_text(self._get_cell(row, 9))
            }
            movements.append(movement)
        return movements

    @staticmethod
    def _format_sheet_date(value):
        if value is None or value == "":
            return ""
        if isinstance(value, (int, float)):
            try:
                from datetime import datetime, timedelta
                date_value = datetime(1899, 12, 30) + timedelta( days=float(value))
                return date_value.strftime("%d/%m/%Y")
            except Exception:
                return str(value)
        return str(value).strip()
    # ---------------------------------------------------------
    # CALCUL DES STOCKS
    # ---------------------------------------------------------
    def calculate_stock(self):
        """
        Recalcule les entrées et sorties à partir des mouvements.
        Entrées :
        - Entrée
        - Correction +
        Sorties :
        - Distribution
        - Perte
        - Correction -
        """
        movements_by_reference = defaultdict(list)
        for movement in self.movements:
            movements_by_reference[
                movement["reference"]
            ].append(movement)
        for article in self.articles:
            reference = article["reference"]
            entries = 0
            exits = 0
            for movement in movements_by_reference.get(
                reference,
                []
            ):
                movement_type = ( movement["type"].strip().casefold())
                quantity = movement["quantite"]
                if movement_type in (
                    "entrée",
                    "entree",
                    "correction +"
                ):
                    entries += quantity
                elif movement_type in (
                    "distribution",
                    "perte",
                    "correction -"
                ):
                    exits += quantity
            available = (
                article["stock_initial"]
                + entries
                - exits
            )
            article["entrees"] = entries
            article["sorties"] = exits
            article["stock_disponible"] = available
        return movements_by_reference
    # ---------------------------------------------------------
    # AFFICHAGE PRINCIPAL
    # ---------------------------------------------------------
    def display_stock(self):
        self._clear_body()
        if not self.articles:
            self.add_empty_message("Aucun article n'est renseigné dans la feuille Articles.")
            return
        movements_by_reference = self.calculate_stock()
        if self.current_tab == "overview":
            self.display_overview()
        elif self.current_tab == "articles":
            self.display_articles_by_category( movements_by_reference )
        elif self.current_tab == "distributions":
            self.display_pole_distributions()
        # Espacement en bas de l'écran.
        self.body.add_widget(Widget(size_hint_y=None, height=dp(25)))
    # ---------------------------------------------------------
    # ONGLET 1 : VUE D'ENSEMBLE
    # ---------------------------------------------------------
    def display_overview(self):
        self.display_summary()
        self.display_alerts()

    def display_summary(self):
        total_articles = len(self.articles)
        alert_count = sum(
            1
            for article in self.articles
            if article["stock_disponible"] <= article["seuil_alerte"]
        )
        movement_count = len(self.movements)
        card = self.create_card(padding=14,spacing=8,color=self.COLOR_LIGHT_BLUE)
        self.add_to_card( card,"ÉTAT DU STOCK", font_size=15,color=self.COLOR_PRIMARY, bold=True )
        self.add_to_card( card,"Références articles : {}".format(total_articles), font_size=13)
        self.add_to_card(
            card,
            "Articles sous le seuil d'alerte : {}".format(alert_count),
            font_size=13,
            color=(
                self.COLOR_DANGER
                if alert_count
                else self.COLOR_SUCCESS
            ),
            bold=True
        )
        self.add_to_card( card,"Mouvements enregistrés : {}".format(movement_count),font_size=13)
        self.body.add_widget(card)
    # ---------------------------------------------------------
    # ALERTES
    # ---------------------------------------------------------
    def display_alerts(self):
        alerts = [
            article
            for article in self.articles
            if article["stock_disponible"] <= article["seuil_alerte"]
        ]
        self.add_section_title("ALERTES DE STOCK")
        if not alerts:
            self.add_empty_message("Aucun article n'a atteint son seuil d'alerte.")
            return
        for article in alerts:
            card = self.create_card(padding=12, spacing=5)
            self.add_to_card(
                card,
                article["designation"],
                font_size=14,
                color=self.COLOR_DANGER,
                bold=True
            )
            self.add_to_card(
                card,
                "Disponible : {} {}".format(
                    self._format_quantity(
                        article["stock_disponible"]
                    ),
                    article["unite"]
                ),
                font_size=13,
                bold=True
            )
            self.add_to_card(
                card,
                "Seuil d'alerte : {} {}".format(
                    self._format_quantity(
                        article["seuil_alerte"]
                    ),
                    article["unite"]
                ),
                font_size=12,
                color=self.COLOR_MUTED
            )
            self.body.add_widget(card)
    # ---------------------------------------------------------
    # ONGLET 2 : ARTICLES PAR CATÉGORIE
    # ---------------------------------------------------------
    def display_articles_by_category(self, movements_by_reference):
        self.add_section_title("STOCK DISPONIBLE PAR CATÉGORIE")
        # Texte explicatif en blanc et en gras.
        self.body.add_widget(
            self.make_label(
                "Retrouvez ici les quantités disponibles pour chaque article.",
                font_size=14,
                bold=True,
                color=self.COLOR_WHITE
            )
        )
        categories = defaultdict(list)
        for article in self.articles:
            categories[article["categorie"]].append(article)
        for category in sorted(
            categories.keys(),
            key=lambda value: value.casefold()
        ):
            # Titre distinct pour chaque catégorie.
            self.add_category_title(category)
            for article in sorted(
                categories[category],
                key=lambda item: item["designation"].casefold()
            ):
                self.display_article_card(article)

    def display_article_card(self, article):
        card = self.create_card(padding=13,spacing=6)
        stock = article["stock_disponible"]
        threshold = article["seuil_alerte"]
        stock_color = (self.COLOR_DANGER
            if stock <= threshold
            else self.COLOR_SUCCESS
        )
        self.add_to_card(card, article["designation"],font_size=15,color=self.COLOR_PRIMARY, bold=True)
        self.add_to_card(
            card,
            "Référence : {}".format(
                article["reference"] or "Non renseignée"
            ),
            font_size=11,
            color=self.COLOR_MUTED
        )
        self.add_to_card(
            card,
            "Disponible : {} {}".format(
                self._format_quantity(stock),
                article["unite"]
            ),
            font_size=14,
            color=stock_color,
            bold=True
        )
        self.add_to_card(
            card,
            "Stock initial : {} {}".format(
                self._format_quantity(
                    article["stock_initial"]
                ),
                article["unite"]
            ),
            font_size=11,
            color=self.COLOR_MUTED
        )
        self.add_to_card(
            card,
            "Entrées : {}  |  Sorties : {}".format(
                self._format_quantity(article["entrees"]),
                self._format_quantity(article["sorties"])
            ),
            font_size=11,
            color=self.COLOR_MUTED
        )
        if article["emplacement"]:
            self.add_to_card( card, "Emplacement : " + article["emplacement"],font_size=11,color=self.COLOR_MUTED)
        self.body.add_widget(card)
    # ---------------------------------------------------------
    # ONGLET 3 : DISTRIBUTIONS PAR PÔLE
    # ---------------------------------------------------------
    def display_pole_distributions(self):
        distributions = defaultdict(
            lambda: defaultdict(float)
        )
        units_by_reference = {
            article["reference"]: article["unite"]
            for article in self.articles
        }
        names_by_reference = {
            article["reference"]: article["designation"]
            for article in self.articles
        }
        for movement in self.movements:
            if (
                movement["type"].strip().casefold()
                != "distribution"
            ):
                continue
            pole = movement["pole"]
            reference = movement["reference"]
            distributions[pole][reference] += ( movement["quantite"])
        self.add_section_title("RÉPARTITION DES DISTRIBUTIONS PAR PÔLE")
        self.body.add_widget(
            self.make_label(
                "Retrouvez les quantités d'articles distribuées "
                "à chaque pôle.",
                font_size=14,
                bold=True,
                color=self.COLOR_WHITE
            )
        )
        if not distributions:
            self.add_empty_message( "Aucune distribution n'a encore été enregistrée.")
            return
        for pole in sorted(
            distributions.keys(),
            key=lambda value: value.casefold()
        ):
            card = self.create_card(padding=13,spacing=7)
            self.add_to_card( card,"Pôle bénéficiaire : " + pole, font_size=15,color=self.COLOR_PRIMARY,bold=True)
            for reference in sorted(
                distributions[pole].keys(),
                key=lambda value: names_by_reference.get(
                    value,
                    value
                ).casefold()
            ):
                designation = names_by_reference.get(reference,reference)
                unit = units_by_reference.get(reference, "unité")
                quantity = distributions[pole][reference]
                self.add_to_card(
                    card,
                    "• {} : {} {}".format(
                        designation,
                        self._format_quantity(quantity),
                        unit
                    ),
                    font_size=12
                )
            self.body.add_widget(card)
    # ---------------------------------------------------------
    # FORMATTAGE
    # ---------------------------------------------------------
    @staticmethod
    def _format_quantity(value):
        try:
            number = float(value)
            if number.is_integer():
                return str(int(number))
            return (
                "{:.2f}".format(number)
                .rstrip("0")
                .rstrip(".")
                .replace(".", ",")
            )
        except (ValueError, TypeError):
            return str(value)
