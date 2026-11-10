# -*- coding: utf-8 -*-
"""
Planning des bénévoles depuis un Google Sheets public.

Le classeur est téléchargé au format XLSX (tous les onglets) puis lu avec
la bibliothèque standard Python. Aucune clé API ni dépendance Google n'est
nécessaire. Le document doit être partagé en lecture avec "Toute personne
disposant du lien".

Intégration dans BenevolesScreen :
    from planning import PlanningScreen

    # Ajouter ("planning", "Planning") à la liste des onglets.
    # Ajouter dans display_current_tab :
    # elif self.current_tab == "planning":
    #     self.display_planning()

    # Puis ajouter la méthode display_planning indiquée dans
    # INTEGRATION_PLANNING.md.
"""

import io
import re
import threading
import urllib.request
import urllib.parse
import zipfile
import xml.etree.ElementTree as ET
import ssl
import certifi

from datetime import datetime, date, timedelta
from collections import defaultdict

from kivy.clock import Clock
from kivy.metrics import dp
from kivy.utils import get_color_from_hex
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.widget import Widget
from kivy.utils import platform

from core.planning_stats import PlanningStats


# Espaces de noms OOXML utilisés dans un fichier XLSX.
_NS_MAIN = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
_NS_REL_DOC = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
_NS_REL_PKG = "http://schemas.openxmlformats.org/package/2006/relationships"


def _local_name(tag):
    return tag.rsplit("}", 1)[-1]


def _normalise(value):
    value = str(value or "").strip().lower()
    value = value.replace("é", "e").replace("è", "e").replace("ê", "e")
    value = value.replace("à", "a").replace("ù", "u").replace("ç", "c")
    value = value.replace("ô", "o").replace("î", "i").replace("ï", "i")
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return " ".join(value.split())


def _parse_date(value):
    """Convertit les dates texte courantes et les numéros de série Excel."""
    if value is None or str(value).strip() == "":
        return None

    if isinstance(value, (int, float)):
        try:
            # Système de dates Excel 1900.
            return (datetime(1899, 12, 30) + timedelta(days=float(value))).date()
        except (ValueError, OverflowError):
            return None

    text = str(value).strip()
    # Google Sheets exporte souvent les cellules de date sous forme
    # de numéro de série Excel, y compris dans les métadonnées.
    if re.fullmatch(r"\d+(?:\.\d+)?", text):
        try:
            return (datetime(1899, 12, 30) + timedelta(days=float(text))).date()
        except (ValueError, OverflowError):
            pass

    for fmt in (
        "%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y",
        "%Y/%m/%d", "%d/%m/%y",
    ):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            pass

    # Date éventuellement intégrée dans le nom d'onglet.
    match = re.search(r"(\d{1,2})[./_-](\d{1,2})[./_-](\d{2,4})", text)
    if match:
        day, month, year = map(int, match.groups())
        if year < 100:
            year += 2000
        try:
            return date(year, month, day)
        except ValueError:
            pass

    match = re.search(r"(20\d{2})[./_-](\d{1,2})[./_-](\d{1,2})", text)
    if match:
        try:
            return date(*map(int, match.groups()))
        except ValueError:
            pass
    return None

def _split_people(value):
    """Accepte plusieurs bénévoles dans une cellule."""
    if not value:
        return []
    if isinstance(value, list):
        return [str(x).strip() for x in value if str(x).strip()]
    parts = re.split(r"[\n;,]+", str(value))
    return [part.strip(" •-\t") for part in parts if part.strip(" •-\t")]

def _cell_column(cell_ref):
    letters = re.match(r"([A-Z]+)", cell_ref or "")
    if not letters:
        return 0
    number = 0
    for char in letters.group(1):
        number = number * 26 + ord(char) - 64
    return number - 1

class _XlsxReader:
    """Lecteur XLSX minimal basé sur zipfile et ElementTree."""

    def __init__(self, content):
        self.archive = zipfile.ZipFile(io.BytesIO(content))
        self.shared_strings = self._read_shared_strings()
        self.sheets = self._read_sheet_map()

    def _xml(self, path):
        return ET.fromstring(self.archive.read(path))

    def _read_shared_strings(self):
        path = "xl/sharedStrings.xml"
        if path not in self.archive.namelist():
            return []
        root = self._xml(path)
        values = []
        for item in root.findall(".//{%s}si" % _NS_MAIN):
            values.append("".join(
                node.text or "" for node in item.findall(".//{%s}t" % _NS_MAIN)
            ))
        return values

    def _read_sheet_map(self):
        workbook = self._xml("xl/workbook.xml")
        rels = self._xml("xl/_rels/workbook.xml.rels")
        targets = {}
        for rel in rels:
            targets[rel.attrib.get("Id")] = rel.attrib.get("Target", "")

        result = []
        sheets_node = workbook.find("{%s}sheets" % _NS_MAIN)
        if sheets_node is None:
            return result

        for sheet in sheets_node:
            name = sheet.attrib.get("name", "")
            rel_id = sheet.attrib.get("{%s}id" % _NS_REL_DOC)
            target = targets.get(rel_id, "")
            if not target:
                continue
            if target.startswith("/"):
                path = target.lstrip("/")
            elif target.startswith("xl/"):
                path = target
            else:
                path = "xl/" + target
            path = re.sub(r"(^|/)\\./", r"\1", path)
            result.append((name, path))
        return result

    def _cell_value(self, cell):
        cell_type = cell.attrib.get("t")
        value_node = cell.find("{%s}v" % _NS_MAIN)

        if cell_type == "inlineStr":
            return "".join(
                node.text or "" for node in cell.findall(".//{%s}t" % _NS_MAIN)
            )
        if value_node is None or value_node.text is None:
            return ""

        value = value_node.text
        if cell_type == "s":
            try:
                return self.shared_strings[int(value)]
            except (ValueError, IndexError):
                return ""
        if cell_type == "b":
            return value == "1"
        return value

    def read_sheet(self, path):
        root = self._xml(path)
        sheet_data = root.find(".//{%s}sheetData" % _NS_MAIN)
        rows = []
        if sheet_data is None:
            return rows

        for row_node in sheet_data.findall("{%s}row" % _NS_MAIN):
            row_values = []
            for cell in row_node.findall("{%s}c" % _NS_MAIN):
                col = _cell_column(cell.attrib.get("r", ""))
                while len(row_values) <= col:
                    row_values.append("")
                row_values[col] = self._cell_value(cell)
            rows.append(row_values)
        return rows

    def all_sheets(self):
        return [(name, self.read_sheet(path)) for name, path in self.sheets]

class PlanningScreen(BoxLayout):
    """
    Vue Planning intégrée dans BenevolesScreen.content.
    Ce composant n'est volontairement pas un Screen Kivy indépendant :
    BenevolesScreen possède déjà sa navigation interne et son ScrollView.
    """
    COLOR_PRIMARY = "#1E3A8A"
    COLOR_SECONDARY = "#334B78"
    COLOR_ACCENT = "#F7ED40"
    COLOR_TEXT = "#243B53"
    COLOR_MUTED = "#65758B"
    COLOR_WHITE = "#FFFFFF"
    COLOR_BORDER = "#DCE5F2"
    COLOR_LIGHT_BLUE = "#EAF0FF"
    COLOR_SUCCESS = "#219653"
    COLOR_WARNING = "#F2994A"
    
    # Adaptation de l'interface pour iOS
    IS_IOS = platform == "ios"

    UI_SCALE = 1.25 if IS_IOS else 1.0
    FONT_SCALE = 1.30 if IS_IOS else 1.0

    def _dp(self, value):
        """Adapte les dimensions de l'interface selon la plateforme."""
        return dp(value * self.UI_SCALE)

    def _sp(self, value):
        """Adapte la taille des textes selon la plateforme."""
        return "{}sp".format(value * self.FONT_SCALE)

    def __init__(self, sheet_url="", **kwargs):
        super().__init__(orientation="vertical", size_hint_y=None, **kwargs)
        self.bind(minimum_height=self.setter("height"))
        self.sheet_url = str(sheet_url or "").strip()
        self.days = {}
        self.selected_day = None
        self.selected_tournament = None
        self.loading = False
        self._build_header()
        self.body = BoxLayout(orientation="vertical",size_hint_y=None,spacing=self._dp(12))
        self.body.bind(minimum_height=self.body.setter("height"))
        self.add_widget(self.body)
        if self.sheet_url:
            Clock.schedule_once(lambda _dt: self.refresh(), 0)
        else:
            self._show_message(
                "Lien Google Sheets manquant",
                "Ajoute la clé 'planning_google_sheet' dans "
                "tournoi > appli > benevoles dans la configuration."
            )
    # ------------------------- Interface -------------------------
    def _label(self, text, size=14, color=None, bold=False):
        label = Label(text=str(text or ""),size_hint_y=None,height=self._dp(max(25, size * 1.8)),font_size=self._sp(size),color=get_color_from_hex(color or self.COLOR_TEXT), bold=bold,halign="left", valign="middle", )
        label.bind(width=lambda obj, width: setattr(obj, "text_size", (width, None)))
        label.bind(texture_size=lambda obj, value: setattr(obj,"height", max(self._dp(25), value[1] + self._dp(8))))
        return label

    def _button(self, text, callback, primary=True):
        button = Button(
            text=text,
            size_hint_y=None,
            height=self._dp(42),
            background_normal="",
            background_down="",
            background_color=get_color_from_hex(
                self.COLOR_ACCENT if primary else self.COLOR_LIGHT_BLUE
            ),
            color=get_color_from_hex(self.COLOR_PRIMARY),
            bold=True,
            font_size=self._sp(13),
        )
        button.bind(on_release=lambda _instance: callback())
        return button

    def _card(self, title=None, subtitle=None):
        card = BoxLayout(orientation="vertical",size_hint_y=None, padding=self._dp(14), spacing=self._dp(7))
        card.bind(minimum_height=card.setter("height"))
        with card.canvas.before:
            from kivy.graphics import Color, RoundedRectangle
            Color(*get_color_from_hex("#FFFFFF"))
            card._background = RoundedRectangle( pos=card.pos,size=card.size,radius=[self._dp(14)])
        card.bind(pos=lambda obj, value: setattr(obj._background, "pos", value),size=lambda obj, value: setattr(obj._background, "size", value ) )
        if title:
            card.add_widget(self._label(title, 16, self.COLOR_PRIMARY, True))
        if subtitle:
            card.add_widget(self._label(subtitle, 12, self.COLOR_MUTED))
        return card

    def _build_header(self):
        header = BoxLayout(orientation="horizontal",size_hint_y=None,height=self._dp(48),spacing=self._dp(6))
        refresh_btn = self._button("Actualiser",self.refresh,primary=True)
        stats_btn = self._button( "Stats", self.display_stats, primary=True)
        header.add_widget(refresh_btn)
        header.add_widget(stats_btn)
        self.add_widget(header)
        self.status_label = self._label("Chargement du planning…",12, self.COLOR_WHITE)
        self.add_widget(self.status_label)
        
    def _show_message(self, title, message):
        self.body.clear_widgets()
        card = self._card(title, message)
        self.body.add_widget(card)
    # ------------------------- Google Sheets -------------------------
    @staticmethod
    def _xlsx_export_url(url):
        match = re.search(r"/spreadsheets/d/([a-zA-Z0-9_-]+)", url)
        if not match:
            raise ValueError("Le lien fourni ne ressemble pas à un lien Google Sheets.")
        spreadsheet_id = match.group(1)
        return (
            "https://docs.google.com/spreadsheets/d/{}/export?format=xlsx"
            .format(spreadsheet_id)
        )

    def refresh(self):
        if self.loading:
            return
        if not self.sheet_url:
            self._show_message("Configuration incomplète", "Aucun lien Google Sheets n'est configuré.")
            return
        self.loading = True
        self.status_label.text = "Mise à jour du planning…"
        thread = threading.Thread(target=self._download_worker, daemon=True)
        thread.start()

    def _download_worker(self):
        try:
            export_url = self._xlsx_export_url(self.sheet_url)
            request = urllib.request.Request(export_url, headers={"User-Agent": "Mozilla/5.0 (compatible; BenevolesPlanning/1.0)"})
            # Utilisation d'un bundle de certificats CA fiable
            context = ssl.create_default_context( cafile=certifi.where())
            with urllib.request.urlopen(
                request,
                timeout=25,
                context=context
            ) as response:
                content = response.read()
            reader = _XlsxReader(content)
            parsed = self._parse_workbook(reader.all_sheets())
            Clock.schedule_once(lambda _dt: self._on_loaded(parsed, None), 0)
        except Exception as error:
            message = str(error)
            Clock.schedule_once(lambda _dt, msg=message: self._on_loaded(None, msg), 0)

    def _on_loaded(self, parsed, error):
        self.loading = False
        if error:
            self.status_label.text = "Impossible de charger le planning."
            self._show_message(
                "Erreur de chargement",
                "{}\n\nVérifie que le Google Sheet est partagé en lecture "
                "avec « Toute personne disposant du lien » et que l'URL est correcte."
                .format(error)
            )
            return
        self.days = parsed
        self.selected_day = None
        self.selected_tournament = None
        self.status_label.text = "Planning actualisé — {} journée(s) trouvée(s).".format(len(self.days))
        self.display_calendar()
    # ------------------------- Analyse des feuilles -------------------------
    def _parse_workbook(self, sheets):
        tournaments = []
        infos_by_date = {}
        # Première passe : feuilles Planning.
        for sheet_name, rows in sheets:
            normalized_name = _normalise(sheet_name)
            if "planning" not in normalized_name:
                continue
            tournament = self._parse_planning_sheet(sheet_name, rows)
            if tournament:
                tournaments.append(tournament)
        # Deuxième passe : feuilles Infos, associées à la date de leur nom.
        for sheet_name, rows in sheets:
            if "info" not in _normalise(sheet_name):
                continue
            sheet_date = self._date_from_sheet_name(sheet_name)
            infos = self._parse_info_sheet(rows)
            if sheet_date:
                infos_by_date.setdefault(
                    sheet_date.isoformat(), []
                ).extend(infos)
        grouped = defaultdict(list)
        for tournament in tournaments:
            day_key = tournament["date"].isoformat()
            tournament["infos_jour"] = infos_by_date.get(day_key, [])
            grouped[day_key].append(tournament)
        for day_key, tournaments in grouped.items():
            for tournament in tournaments:
                print(
                    "[PLANNING] Tournoi =",
                    tournament["nom"],
                    "infos_jour =",
                    tournament.get("infos_jour")
                )
        
        return dict(sorted(grouped.items(), key=lambda item: item[0]))

    def _date_from_sheet_name(self, name):
        # Exemple : "08/01/2027 - Planning",
        # "2027-01-08 - Infos" ou "08012027 - Infos".
        parsed = _parse_date(name)
        if parsed:
            return parsed
        # Format compact : 08012027
        match = re.search(r"(\d{2})(\d{2})(\d{4})", name)
        if match:
            try:
                day, month, year = map(int, match.groups())
                return date(year, month, day)
            except ValueError:
                pass
        # Format partiel : 08/01, 08-01, 08_01...
        match = re.search(r"(\d{1,2})[./_-](\d{1,2})(?!\d)", name)
        if match:
            try:
                return date(
                    datetime.now().year,
                    int(match.group(2)),
                    int(match.group(1))
                )
            except ValueError:
                pass
        return None

    def _parse_planning_sheet(self, sheet_name, rows):
        metadata = {}
        header_index = None
        headers = []
        aliases = {
            "poste": (
                "poste",
                "postes",
                "mission",
                "fonction",
            ),
            "creneau": (
                "creneau horaire",
                "creneau",
                "horaire",
                "horaires",
            ),
            "nom": (
                "nom",
            ),
            "prenom": (
                "prenom",
                "prénom",
            ),
            "telephone": (
                "telephone",
                "téléphone",
                "tel",
                "tel.",
                "portable",
            ),
            "referent": (
                "referent",
                "référent",
            ),
            "notes": (
                "contact note",
                "contact / note",
                "contact",
                "notes",
                "consignes",
            ),
        }
        def identify_header(row):
            normalized = [_normalise(value) for value in row]
            found = {}
            for key, names in aliases.items():
                for index, value in enumerate(normalized):
                    if value in names:
                        found[key] = index
                        break
            return found if (
                "poste" in found
                and "nom" in found
                and "prenom" in found
            ) else None
        for index, row in enumerate(rows):
            # Métadonnées en haut de feuille sous forme clé / valeur.
            if len(row) >= 2 and str(row[0]).strip():
                metadata[_normalise(row[0])] = str(row[1]).strip()
            found = identify_header(row)
            if found:
                header_index = index
                headers = found
                break
        if header_index is None:
            return None
        date_value = (
            metadata.get("date")
            or metadata.get("date du tournoi")
            or metadata.get("journee")
            or self._date_from_sheet_name(sheet_name)
        )
        parsed_date = _parse_date(date_value) or self._date_from_sheet_name(sheet_name)
        if not parsed_date:
            return None
        title = (
            metadata.get("nom du tournoi")
            or metadata.get("tournoi")
            or metadata.get("nom")
        )
        if not title:
            title = re.sub(r"\s*[-–]\s*planning\s*$", "", sheet_name, flags=re.I).strip()
            title = title or "Tournoi"
        tournament = {
            "date": parsed_date,
            "nom": title,
            "convocation": metadata.get("heure de convocation", metadata.get("convocation", "")),
            "debut": metadata.get("heure de debut", metadata.get("debut", "")),
            "fin": metadata.get("heure de fin", metadata.get("fin", "")),
            "responsable_jour": metadata.get("responsable du jour", metadata.get("responsable", "")),
            "telephone_responsable": metadata.get("telephone du responsable", metadata.get("telephone responsable", "")),
            "postes": [],
        }
        current_post = ""
        for row in rows[header_index + 1:]:
            if not row or not any(str(cell).strip() for cell in row):
                continue
            def get_value(key):
                col = headers.get(key)
                return row[col] if col is not None and col < len(row) else ""
            post = str(get_value("poste") or "").strip()
            if post:
                current_post = post
            if not current_post:
                continue
            slot = str(get_value("creneau") or "").strip()
            nom = str(get_value("nom") or "").strip()
            prenom = str(get_value("prenom") or "").strip()
            telephone = str(get_value("telephone") or "").strip()
            referent = _normalise(
                get_value("referent")
            ) in (
                "oui",
                "yes",
                "true",
                "1",
                "x"
            )
            notes = str(get_value("notes") or "").strip()
            if not (nom or prenom):
                continue
            tournament["postes"].append({
                "poste": current_post,
                "creneau": slot,
                "nom": nom,
                "prenom": prenom,
                "telephone": telephone,
                "referent": referent,
                "notes": notes,
            })
        return tournament

    def _parse_info_sheet(self, rows):
        infos = []
        for row in rows:
            if not row:
                continue
            key = str(row[0]).strip() if len(row) > 0 else ""
            value = str(row[1]).strip() if len(row) > 1 else ""
            if key and value:
                infos.append((key, value))
        return infos
    # ------------------------- Affichage calendrier -------------------------
    @staticmethod
    def _french_date(value):
        weekdays = (
            "lundi", "mardi", "mercredi", "jeudi",
            "vendredi", "samedi", "dimanche"
        )
        months = (
            "janvier", "février", "mars", "avril", "mai", "juin",
            "juillet", "août", "septembre", "octobre", "novembre", "décembre"
        )
        return "{} {} {} {}".format( weekdays[value.weekday()], value.day, months[value.month - 1], value.year)

    def display_calendar(self):
        self.body.clear_widgets()
        self.selected_day = None
        self.selected_tournament = None
        if not self.days:
            self.body.add_widget(self._card(
                "Aucune journée trouvée",
                "Aucun onglet « [Date] - Planning » exploitable n'a été détecté."
            ))
            return
        for day_key, tournaments in self.days.items():
            parsed = datetime.strptime(day_key, "%Y-%m-%d").date()
            day_label = self._french_date(parsed)
            total_people = set()
            for tournament in tournaments:
                for post in tournament["postes"]:
                    total_people.add(
                        (
                            post["nom"],
                            post["prenom"]
                        )
                    )
            card = self._card(
                day_label.capitalize(),
                "{} tournoi(s)  •  {} bénévole(s) identifié(s)".format(
                    len(tournaments), len(total_people)
                )
            )
            for tournament in tournaments:
                debut = tournament.get("debut", "").strip()
                fin = tournament.get("fin", "").strip()
                horaires = ""
                if debut and fin:
                    horaires = f" ({debut} - {fin})"
                elif debut:
                    horaires = f" ({debut})"
                elif fin:
                    horaires = f" ({fin})"
                card.add_widget(
                    self._label(
                        f"• {tournament['nom']}{horaires}",
                        13,
                        self.COLOR_SECONDARY
                    )
                )
            card.add_widget(self._button("Voir les tournois de cette journée",lambda key=day_key: self.open_day(key)))
            self.body.add_widget(card)
        self.body.add_widget(Widget(size_hint_y=None, height=self._dp(18)))

    def open_day(self, day_key):
        self.selected_day = day_key
        tournaments = self.days.get(day_key, [])
        if len(tournaments) == 1:
            self.open_tournament(tournaments[0])
            return
        self.body.clear_widgets()
        parsed = datetime.strptime(day_key, "%Y-%m-%d").date()
        self.body.add_widget(self._button("‹ Retour au calendrier", self.display_calendar, False))
        self.body.add_widget(self._label(
            parsed.strftime("%d/%m/%Y") + " — Choisis un tournoi",
            18, self.COLOR_WHITE, True
        ))
        for tournament in tournaments:
            people = {
                (
                    post["nom"],
                    post["prenom"]
                )
                for post in tournament["postes"]
            }
            card = self._card(
                tournament["nom"],
                "{} poste(s) • {} bénévole(s)".format(
                    len(tournament["postes"]), len(people)
                )
            )
            card.add_widget(self._button("Consulter ce tournoi",lambda selected=tournament: self.open_tournament(selected)))
            self.body.add_widget(card)

    def open_tournament(self, tournament):
        self.selected_tournament = tournament
        self.body.clear_widgets()
        self.body.add_widget(self._button(
            "‹ Retour aux journées",
            self.display_calendar,
            False
        ))
        if self.selected_day and len(self.days.get(self.selected_day, [])) > 1:
            self.body.add_widget(self._button(
                "‹ Choisir un autre tournoi de cette journée",
                lambda: self.open_day(self.selected_day),
                False
            ))
        self.body.add_widget(self._label(tournament["nom"], 21, self.COLOR_WHITE, True))
        self.body.add_widget(self._label(tournament["date"].strftime("%d/%m/%Y"), 13, self.COLOR_WHITE))
        # ==========================================================
        # Vue d'ensemble
        # ==========================================================
        people = {
            (p["nom"], p["prenom"])
            for p in tournament["postes"]
        }
        required_posts = (
            "Buvette",
            "Snack",
            "Frites",
            "Caisse / Jeton",
            "Arbitrage",
            "Table de Marque"
        )
        overview = self._card("Vue d'ensemble")
        # --------------------------------------------------
        # Statistiques
        # --------------------------------------------------
        nb_postes = len(
            set(
                p["poste"]
                for p in tournament["postes"]
                if p["poste"].strip()
            )
        )
        # --------------------------------------------------
        # Horaires
        # --------------------------------------------------
        horaires = []
        if tournament.get("convocation"):
            horaires.append(
                "Convocation : {}".format(
                    tournament["convocation"]
                )
            )
        if tournament.get("debut"):
            horaires.append(
                "Début : {}".format(
                    tournament["debut"]
                )
            )
        if tournament.get("fin"):
            horaires.append(
                "Fin : {}".format(
                    tournament["fin"]
                )
            )
        for texte in horaires:
            overview.add_widget(
                self._label(
                    texte,
                    13,
                    self.COLOR_TEXT
                )
            )
        # -------------------------------------------------
        # Responsable
        # -------------------------------------------------
        if tournament.get("responsable_jour"):
            overview.add_widget(
                self._label(
                    "Responsable : {}".format(
                        tournament["responsable_jour"]
                    ),
                    13
                )
            )
        if tournament.get("telephone_responsable"):
            overview.add_widget(
                self._label(
                    "Téléphone : {}".format(
                        tournament["telephone_responsable"]
                    ),
                    13
                )
            )
        # --------------------------------------------------
        # Postes critiques
        # --------------------------------------------------
        overview.add_widget(
            self._label(
                "Postes indispensables",
                14,
                self.COLOR_PRIMARY,
                True
            )
        )
        covered = 0
        for required_post in required_posts:
            nb = sum(
                1
                for p in tournament["postes"]
                if p["poste"].strip().lower()
                == required_post.lower()
            )
            is_ok = nb > 0
            if is_ok:
                covered += 1
            overview.add_widget(
                self._label(
                    "{} : {} bénévole(s)".format(
                        required_post,
                        nb
                    ),
                    13,
                    self.COLOR_SUCCESS if is_ok else "#E53935",
                    True
                )
            )
        overview.add_widget(
            self._label(
                "{} / {} postes critiques couverts".format(
                    covered,
                    len(required_posts)
                ),
                14,
                self.COLOR_SUCCESS
                if covered == len(required_posts)
                else "#E53935",
                True
            )
        )
        self.body.add_widget(overview)
        self.body.add_widget(self._label("Postes et affectations - Détails", 17, self.COLOR_ACCENT, True))
        if not tournament["postes"]:
            self.body.add_widget(self._card(
                "Aucun poste renseigné",
                "Le tableau a été détecté, mais aucune ligne d'affectation n'a été trouvée."
            ))
        # Regroupe les bénévoles par poste.
        grouped = defaultdict(list)
        for assignment in tournament["postes"]:
            grouped[assignment["poste"]].append(assignment)
        for post_name, assignments in grouped.items():
            assignments.sort(
                key=lambda row: (
                    row["creneau"],
                    not row["referent"],
                    row["nom"].lower(),
                    row["prenom"].lower(),
                )
            )
            card = self._card(post_name)
            current_slot = None
            index = 0
            for assignment in assignments:
                # Nouveau créneau
                if assignment["creneau"] != current_slot:
                    current_slot = assignment["creneau"]
                    index = 1
                    if current_slot:
                        card.add_widget(
                            self._label(
                                f"Créneau : {current_slot}",
                                13,
                                self.COLOR_PRIMARY,
                                True
                            )
                        )
                else:
                    index += 1
                texte = (
                    f"{index}. "
                    f"{assignment['prenom']} "
                    f"{assignment['nom']}"
                )
                if assignment["telephone"]:
                    texte += f" - {assignment['telephone']}"
                if assignment["notes"]:
                    texte += f" - {assignment['notes']}"
                card.add_widget(
                    self._label(
                        texte,
                        13,
                        "#000000" if assignment["referent"] else self.COLOR_TEXT,
                        assignment["referent"]   # gras si référent
                    )
                )
            self.body.add_widget(card)
        day_infos = tournament.get("infos_jour", [])
        if day_infos:
            self.body.add_widget(self._label( "Informations supplémentaires", 17,self.COLOR_ACCENT, True))
            for titre, contenu in day_infos:
                card = self._card()
                card.add_widget(self._label( titre,14, self.COLOR_PRIMARY, True))
                card.add_widget( self._label( contenu, 13,self.COLOR_TEXT ))
                self.body.add_widget(card)
        self.body.add_widget(Widget(size_hint_y=None, height=self._dp(20)))
    # ------------------------- Affichage stats -------------------------
    def display_stats(self):
        stats = PlanningStats.build(self.days)
        self.body.clear_widgets()
        self.body.add_widget(self._button("‹ Retour",self.display_calendar,False ))
        self.body.add_widget(self._label("Statistiques",20, self.COLOR_WHITE,True ))
        # ==========================================================
        # Vue d'ensemble
        # ==========================================================
        card = self._card("Vue d'ensemble")
        card.add_widget(
            self._label(
                f"{stats['tournois']} tournois • "
                f"{stats['jours']} journées",
                14,
                self.COLOR_PRIMARY,
                True
            )
        )
        card.add_widget(self._label(f"{stats['benevoles']} affectations"))
        card.add_widget(self._label( f"{stats['benevoles_uniques']} bénévoles uniques" ))
        card.add_widget(self._label( f"{stats['referents']} référents"))
        card.add_widget(self._label( f"{stats['postes']} postes") )
        card.add_widget(self._label(f"{stats['creneaux']} créneaux"))
        self.body.add_widget(card)
        # ==========================================================
        # Contrôle qualité
        # ==========================================================
        card = self._card("Contrôle qualité")
        card.add_widget(
            self._label(
                f"Téléphones manquants : "
                f"{len(stats['telephones_manquants'])}",
                13,
                self.COLOR_WARNING
                if stats["telephones_manquants"]
                else self.COLOR_SUCCESS,
                True
            )
        )
        card.add_widget(
            self._label(
                f"Notes manquantes : "
                f"{len(stats['notes_manquantes'])}",
                13
            )
        )
        card.add_widget(
            self._label(
                f"Postes sans référent : "
                f"{len(stats['postes_sans_referent'])}",
                13,
                self.COLOR_WARNING
                if stats["postes_sans_referent"]
                else self.COLOR_SUCCESS,
                True
            )
        )
        self.body.add_widget(card)
        # ==========================================================
        # Top tournois
        # ==========================================================
        if stats["tournois_stats"]:
            card = self._card("Top 10 des tournois les plus chargés")
            for rank, (nom, total) in enumerate( list(stats["tournois_stats"].items())[:10], start=1):
                card.add_widget( self._label( f"{rank}. {nom} ({total} bénévoles)" ))
            self.body.add_widget(card)
        # ==========================================================
        # Top postes
        # ==========================================================
        if stats["postes_stats"]:
            card = self._card( "Top 10 des postes les plus sollicités" )
    
            for rank, (poste, total) in enumerate(list(stats["postes_stats"].items())[:10],start=1):
                card.add_widget(self._label( f"{rank}. {poste} ({total})"))
            self.body.add_widget(card)
        # ==========================================================
        # Postes sans référent
        # ==========================================================
        if stats["postes_sans_referent"]:
            card = self._card("Postes sans référent")
            for poste in stats["postes_sans_referent"]:
                card.add_widget( self._label(  f"• {poste}", 13,self.COLOR_WARNING, True))
            self.body.add_widget(card)
        # ==========================================================
        # Téléphones manquants
        # ==========================================================
        if stats["telephones_manquants"]:
            card = self._card("Téléphones manquants" )
            for benevole in stats["telephones_manquants"][:20]:
                texte = (
                    f"{benevole['prenom']} "
                    f"{benevole['nom']} "
                    f"({benevole['tournoi']})"
                )
                card.add_widget(self._label(texte,13))
            reste = ( len(stats["telephones_manquants"])  - 20 )
            if reste > 0:
                card.add_widget(self._label(f"... et {reste} autres",12, self.COLOR_MUTED))
            self.body.add_widget(card)
        # ==========================================================
        # Référents
        # ==========================================================
        if stats["referents_liste"]:
            card = self._card(f"Référents ({len(stats['referents_liste'])})")
            for referent in stats[ "referents_liste"][:20]:
                texte = (
                    f"{referent['prenom']} "
                    f"{referent['nom']} - "
                    f"{', '.join(referent['postes'])}"
                )
                card.add_widget(self._label(texte,13))
            reste = (len(stats["referents_liste"]) - 20)
            if reste > 0:
                card.add_widget(
                    self._label(
                        f"... et {reste} autres",
                        12,
                        self.COLOR_MUTED
                    )
                )
            self.body.add_widget(card)
        self.body.add_widget( Widget(size_hint_y=None,height=self._dp(20)))
