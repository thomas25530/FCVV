# -*- coding: utf-8 -*-
import threading
from datetime import datetime, timedelta
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
from kivy.uix.textinput import TextInput
from kivy.uix.dropdown import DropDown
from kivy.clock import mainthread

import os
from pathlib import Path
from kivy.app import App

def obtenir_dossier_documents():
    if platform == "android":
        try:
            from plyer import storagepath
            dossier = os.path.join(storagepath.get_downloads_dir(),"FCVV")
            os.makedirs(dossier, exist_ok=True)
            print("DOSSIER PDF =", dossier)
            return dossier
        except Exception:
            pass
    elif platform == "ios":
        app = App.get_running_app()
        return app.user_data_dir
    try:
        from plyer import storagepath
        d = storagepath.get_documents_dir()
        if d:
            return d
    except Exception:
        pass
    return os.path.expanduser("~/Documents")


def generer_pdf_convocation(match_info, tous_les_joueurs=None):
    # ============================================================
    # SECURITE
    # ============================================================

    print("--- [DEBUG EXTREME] Entree dans generer_pdf_convocation ---")

    try:
        import os
        import sys

        from fpdf import FPDF

        from kivy.app import App
        from kivy.utils import platform
        from kivy.clock import Clock

        print("[DEBUG] Imports reussis avec succes !")

    except Exception as import_error:
        print(
            f"[CRASH IMPORT] Erreur lors des imports : "
            f"{type(import_error).__name__}: {import_error}"
        )

        try:
            sys.stdout.flush()
        except Exception:
            pass

        return

    print("[DEBUG] Debut de la fonction generer_pdf_convocation")

    # ============================================================
    # DONNEES
    # ============================================================

    tous_les_joueurs = tous_les_joueurs or []

    def txt(value, max_length=60):
        return (
            str(value or "-")
            .replace("\n", " ")
            .strip()[:max_length]
        )

    # ============================================================
    # LICENCES
    # ============================================================

    licences = {}

    for joueur_data in tous_les_joueurs:

        if isinstance(joueur_data, dict):

            nom = txt(
                joueur_data.get("nom"),
                40
            ).upper()

            prenom = txt(
                joueur_data.get("prenom"),
                30
            ).capitalize()

            licence = txt(
                joueur_data.get("licence")
                or joueur_data.get("num_licence")
                or joueur_data.get("numero_licence"),
                25
            )

            licences[
                f"{nom} {prenom}".upper()
            ] = licence

    # ============================================================
    # FICHIER DE SORTIE
    # ============================================================

    dossier = obtenir_dossier_documents()

    os.makedirs(
        dossier,
        exist_ok=True
    )

    titre = txt(
        match_info.get("titre"),
        50
    )

    def safe_filename(value):
        return (
            "".join(
                char
                for char in str(value)
                if char.isalnum() or char in " _-"
            ).strip()
            or "Match"
        )

    chemin = os.path.join(
        dossier,
        f"Convocation_"
        f"{safe_filename(titre)}_"
        f"{safe_filename(match_info.get('date', 'date'))}.pdf"
    )

    print(
        f"[DEBUG] Chemin du PDF cible : {chemin}"
    )

    # ============================================================
    # RECHERCHE DES ASSETS
    # ============================================================

    bases = []

    for base_candidate in (
        os.path.dirname(__file__),
        getattr(
            App.get_running_app(),
            "directory",
            ""
        ),
        os.getcwd(),
        getattr(
            sys,
            "_MEIPASS",
            ""
        ),
    ):

        if base_candidate:

            bases.append(
                os.path.abspath(
                    base_candidate
                )
            )

    def asset(asset_name):

        visited = set()

        for base in bases:

            while base not in visited:

                visited.add(base)

                asset_path = os.path.join(
                    base,
                    "assets",
                    asset_name
                )

                if os.path.isfile(asset_path):
                    return asset_path

                parent = os.path.dirname(base)

                if parent == base:
                    break

                base = parent

        return None

    font = asset(
        "fonts/DejaVuSans.ttf"
    )

    bold = asset(
        "fonts/DejaVuSans-Bold.ttf"
    )

    logo = asset(
        "logo.png"
    )

    print(
        f"[DEBUG] Police normale : {font}"
    )

    print(
        f"[DEBUG] Police bold : {bold}"
    )

    print(
        f"[DEBUG] Logo : {logo}"
    )

    if not font or not bold:

        print(
            "[DEBUG] ERREUR : "
            "Polices DejaVu introuvables !"
        )

        raise FileNotFoundError(
            "Polices DejaVu introuvables dans assets/fonts/"
        )

    # ============================================================
    # CONSTRUCTION DU PDF
    # ============================================================

    try:

        print(
            "[DEBUG] Debut de la construction "
            "du PDF avec FPDF..."
        )

        pdf = FPDF(
            "P",
            "mm",
            "A4"
        )

        pdf.set_margins(
            10,
            10,
            10
        )

        pdf.set_auto_page_break(
            True,
            12
        )

        pdf.add_font(
            "DejaVu",
            "",
            font
        )

        pdf.add_font(
            "DejaVu",
            "B",
            bold
        )

        pdf.add_page()

        # ========================================================
        # SECTIONS
        # ========================================================

        def section(section_title):

            pdf.ln(3)

            pdf.set_font(
                "DejaVu",
                "B",
                12
            )

            pdf.set_text_color(
                45,
                106,
                79
            )

            pdf.cell(
                0,
                7,
                txt(section_title, 60)
            )

            pdf.ln(7)

        # ========================================================
        # EN-TETE
        # ========================================================

        pdf.set_text_color(
            27,
            67,
            50
        )

        pdf.set_font(
            "DejaVu",
            "B",
            17
        )

        # --------------------------------------------------------
        # LOGO
        # --------------------------------------------------------

        if logo:

            try:

                print(
                    f"[DEBUG] Ajout du logo : {logo}"
                )

                # Test Pillow uniquement pour diagnostic.
                try:

                    from PIL import Image

                    print(
                        "[DEBUG] Pillow importe avec succes."
                    )

                    test_image = Image.open(
                        logo
                    )

                    print(
                        "[DEBUG] Logo lisible : "
                        f"format={test_image.format}, "
                        f"size={test_image.size}, "
                        f"mode={test_image.mode}"
                    )

                    test_image.close()

                except Exception as pillow_error:

                    print(
                        "[DEBUG] ERREUR Pillow lors "
                        f"du test du logo : "
                        f"{type(pillow_error).__name__}: "
                        f"{pillow_error}"
                    )

                # Ajout réel du logo dans le PDF.
                pdf.image(
                    logo,
                    10,
                    10,
                    23,
                    23
                )

                pdf.set_xy(
                    38,
                    16
                )

                print(
                    "[DEBUG] Logo ajoute avec succes."
                )

            except Exception as logo_error:

                print(
                    "[DEBUG] ERREUR ajout logo : "
                    f"{type(logo_error).__name__}: "
                    f"{logo_error}"
                )

                import traceback

                traceback.print_exc()

                # On continue sans logo.
                pdf.set_xy(
                    10,
                    16
                )

        else:

            print(
                "[DEBUG] Logo introuvable, "
                "generation sans logo."
            )

        pdf.cell(
            0,
            10,
            txt(titre, 60).upper(),
            align="C"
        )

        pdf.ln(17)

        # ========================================================
        # INFORMATIONS DU MATCH
        # ========================================================

        section(
            "Details du Match"
        )

        infos = [
            (
                "Adversaire :",
                match_info.get("adversaire"),
                "Date :",
                match_info.get("date")
            ),
            (
                "RDV Valdahon :",
                match_info.get("heure_rdv"),
                "Sur Place :",
                match_info.get("heure_sur_place")
            ),
            (
                "Coup d'envoi :",
                match_info.get("heure_coup_envoi"),
                "Lieu :",
                match_info.get("lieu")
            )
        ]

        widths = [
            34,
            50,
            34,
            52
        ]

        for row in infos:

            for index, value in enumerate(row):

                pdf.set_font(
                    "DejaVu",
                    "B" if index in (0, 2) else "",
                    8
                )

                pdf.set_fill_color(
                    248,
                    249,
                    250
                )

                pdf.set_draw_color(
                    225,
                    228,
                    230
                )

                pdf.cell(
                    widths[index],
                    8,
                    txt(value, 35),
                    border=1,
                    fill=True
                )

            pdf.ln()

        # ========================================================
        # ENTRAINEURS
        # ========================================================

        entraineurs = [
            entraineur.strip()
            for entraineur in str(
                match_info.get(
                    "entraineurs",
                    ""
                )
            ).split(",")
            if entraineur.strip()
        ]

        coachs = []

        for entraineur in entraineurs:

            morceaux = entraineur.split()

            if len(morceaux) > 1:

                nom_entraineur = (
                    " ".join(
                        morceaux[:-1]
                    ).upper()
                )

                prenom_entraineur = (
                    morceaux[-1].capitalize()
                )

            else:

                nom_entraineur = (
                    entraineur.upper()
                )

                prenom_entraineur = ""

            licence_entraineur = licences.get(
                f"{nom_entraineur} "
                f"{prenom_entraineur}".upper(),
                "-"
            )

            if licence_entraineur != "-":

                coachs.append(
                    f"{entraineur} "
                    f"(Licence : {licence_entraineur})"
                )

            else:

                coachs.append(
                    entraineur
                )

        pdf.set_font(
            "DejaVu",
            "B",
            8
        )

        pdf.set_fill_color(
            248,
            249,
            250
        )

        pdf.cell(
            34,
            8,
            "Entraineur(s) :",
            border=1,
            fill=True
        )

        pdf.set_font(
            "DejaVu",
            "",
            8
        )

        pdf.multi_cell(
            136,
            8,
            txt(
                ", ".join(coachs) or "-",
                120
            ),
            border=1,
            fill=True
        )

        # ========================================================
        # NOTES
        # ========================================================

        notes = txt(
            match_info.get("notes"),
            500
        )

        if notes != "-":

            pdf.ln(2)

            pdf.set_font(
                "DejaVu",
                "B",
                8
            )

            pdf.cell(
                0,
                6,
                "Notes :"
            )

            pdf.ln(5)

            pdf.set_font(
                "DejaVu",
                "",
                8
            )

            pdf.multi_cell(
                0,
                5,
                notes
            )

        # ========================================================
        # JOUEURS
        # ========================================================

        joueurs = match_info.get(
            "joueurs_convoques",
            []
        )

        if (
            match_info.get(
                "activer_convocation"
            )
            and joueurs
        ):

            section(
                f"Joueurs Convoques "
                f"({len(joueurs)})"
            )

            headers = [
                "#",
                "Nom",
                "Prenom",
                "Categorie",
                "N Licence"
            ]

            widths = [
                9,
                39,
                39,
                31,
                42
            ]

            pdf.set_font(
                "DejaVu",
                "B",
                8
            )

            pdf.set_text_color(
                255,
                255,
                255
            )

            pdf.set_fill_color(
                45,
                106,
                79
            )

            for index, header in enumerate(headers):

                pdf.cell(
                    widths[index],
                    8,
                    header,
                    border=1,
                    align="C",
                    fill=True
                )

            pdf.ln()

            for index, joueur in enumerate(
                joueurs,
                1
            ):

                if isinstance(
                    joueur,
                    dict
                ):

                    nom = txt(
                        joueur.get("nom"),
                        40
                    ).upper()

                    prenom = txt(
                        joueur.get("prenom"),
                        25
                    ).capitalize()

                    categorie = txt(
                        joueur.get(
                            "categorie_joueur"
                        )
                        or joueur.get(
                            "categorie"
                        ),
                        18
                    ).upper()

                else:

                    joueur_parts = txt(
                        joueur,
                        60
                    ).split()

                    if len(joueur_parts) > 1:

                        nom = " ".join(
                            joueur_parts[:-1]
                        ).upper()

                        prenom = (
                            joueur_parts[-1]
                            .capitalize()
                        )

                    else:

                        nom = (
                            joueur_parts[0].upper()
                            if joueur_parts
                            else "-"
                        )

                        prenom = ""

                    categorie = "-"

                licence_joueur = licences.get(
                    f"{nom} {prenom}".upper(),
                    "-"
                )

                row = [
                    index,
                    nom,
                    prenom,
                    categorie,
                    licence_joueur
                ]

                pdf.set_text_color(
                    43,
                    43,
                    43
                )

                if index % 2 == 0:

                    pdf.set_fill_color(
                        241,
                        245,
                        242
                    )

                else:

                    pdf.set_fill_color(
                        255,
                        255,
                        255
                    )

                for column_index, value in enumerate(row):

                    pdf.cell(
                        widths[column_index],
                        7,
                        txt(value, 35),
                        border=1,
                        align=(
                            "C"
                            if column_index == 0
                            else "L"
                        ),
                        fill=True
                    )

                pdf.ln()

        # ========================================================
        # SAUVEGARDE
        # ========================================================

        pdf.output(
            chemin
        )

        print(
            "[DEBUG] Succes : PDF cree sur le disque -> "
            f"{chemin}"
        )

        # Vérification supplémentaire
        if os.path.isfile(chemin):

            taille_pdf = os.path.getsize(
                chemin
            )

            print(
                "[DEBUG] Verification PDF : "
                f"{taille_pdf} octets"
            )

        else:

            print(
                "[DEBUG] ATTENTION : "
                "pdf.output() termine mais "
                "le fichier n'existe pas."
            )

    except Exception as pdf_error:

        print(
            "[DEBUG] ERREUR lors de la generation "
            "du PDF FPDF : "
            f"{type(pdf_error).__name__}: "
            f"{pdf_error}"
        )

        import traceback

        traceback.print_exc()

        raise

    # ============================================================
    # OUVERTURE / PARTAGE SELON LA PLATEFORME
    # ============================================================

    if platform == "win":

        try:

            os.startfile(
                chemin
            )

        except Exception as windows_error:

            print(
                "[DEBUG] Ouverture PDF impossible : "
                f"{windows_error}"
            )

    elif platform == "android":

        print(
            f"PDF enregistre dans le stockage : "
            f"{chemin}"
        )

    elif platform == "ios":

        print(
            "[DEBUG] Planification du partage "
            "iOS via Clock..."
        )

        Clock.schedule_once(
            lambda dt: _partager_pdf_ios(chemin),
            0
        )

    return chemin



@mainthread
def _partager_pdf_ios(chemin):
    """Affiche la feuille de partage iOS pour un PDF."""

    print("=" * 60)
    print("[IOS SHARE] Debut")
    print("=" * 60)

    try:
        import os
        import traceback

        from pyobjus import autoclass

        # =====================================================
        # VERIFICATION PDF
        # =====================================================

        if not os.path.isfile(chemin):
            print(f"[IOS SHARE] PDF introuvable : {chemin}")
            return

        taille = os.path.getsize(chemin)

        print(f"[IOS SHARE] PDF = {chemin}")
        print(f"[IOS SHARE] Taille = {taille}")

        if taille <= 0:
            print("[IOS SHARE] PDF vide")
            return

        # =====================================================
        # CLASSES IOS
        # =====================================================

        NSURL = autoclass("NSURL")
        UIApplication = autoclass("UIApplication")
        UIActivityViewController = autoclass(
            "UIActivityViewController"
        )
        NSMutableArray = autoclass("NSMutableArray")

        # =====================================================
        # URL DU PDF
        # =====================================================

        file_url = NSURL.fileURLWithPath_(chemin)

        if not file_url:
            print("[IOS SHARE] Impossible de creer NSURL")
            return

        print("[IOS SHARE] NSURL OK")

        # =====================================================
        # TABLEAU DES ELEMENTS A PARTAGER
        # =====================================================

        activity_items = NSMutableArray.alloc().init()
        activity_items.addObject_(file_url)

        print("[IOS SHARE] Activity items OK")

        # =====================================================
        # CONTROLEUR DE PARTAGE
        # =====================================================

        activity_vc = (
            UIActivityViewController
            .alloc()
            .initWithActivityItems_applicationActivities_(
                activity_items,
                None
            )
        )

        if not activity_vc:
            print("[IOS SHARE] Impossible de creer UIActivityViewController")
            return

        print("[IOS SHARE] UIActivityViewController OK")

        # =====================================================
        # APPLICATION
        # =====================================================

        app = UIApplication.sharedApplication()

        if not app:
            print("[IOS SHARE] UIApplication introuvable")
            return

        print("[IOS SHARE] UIApplication OK")

        # =====================================================
        # FENETRE
        # =====================================================

        window = None

        try:
            windows = app.windows()

            if windows:
                count = windows.count()

                print(f"[IOS SHARE] Nombre fenetres = {count}")

                for i in range(count):
                    candidate = windows.objectAtIndex_(i)

                    if candidate:
                        window = candidate
                        print(
                            f"[IOS SHARE] Fenetre selectionnee index={i}"
                        )
                        break

        except Exception as e:
            print(
                f"[IOS SHARE] Erreur windows() : "
                f"{type(e).__name__}: {e}"
            )

        if not window:
            try:
                window = app.keyWindow()
                print("[IOS SHARE] keyWindow utilisee")
            except Exception as e:
                print(
                    f"[IOS SHARE] keyWindow erreur : "
                    f"{type(e).__name__}: {e}"
                )

        if not window:
            print("[IOS SHARE] Aucune UIWindow")
            return

        print("[IOS SHARE] UIWindow OK")
        print(f"[IOS SHARE] window = {window}")

        # =====================================================
        # ROOT VIEW CONTROLLER
        # =====================================================

        root_vc = window.rootViewController()

        if not root_vc:
            print("[IOS SHARE] rootViewController absent")
            return

        print("[IOS SHARE] rootViewController OK")
        print(f"[IOS SHARE] root_vc = {root_vc}")

        # =====================================================
        # CONTROLEUR LE PLUS HAUT
        # =====================================================

        presenter = root_vc

        try:
            while True:
                presented = presenter.presentedViewController()

                if not presented:
                    break

                presenter = presented

        except Exception as e:
            print(
                f"[IOS SHARE] presentedViewController erreur : "
                f"{type(e).__name__}: {e}"
            )

        print("[IOS SHARE] Presenter OK")

        # =====================================================
        # IPAD
        # =====================================================

        try:
            popover = (
                activity_vc
                .popoverPresentationController()
            )

            if popover:
                view = presenter.view()

                if view:
                    popover.setSourceView_(view)

                    try:
                        popover.setSourceRect_(
                            view.bounds()
                        )
                    except Exception:
                        pass

                    print("[IOS SHARE] Popover configure")
        except Exception as e:
            print(
                f"[IOS SHARE] Popover erreur : "
                f"{type(e).__name__}: {e}"
            )

        # =====================================================
        # AFFICHAGE
        # =====================================================

        print("[IOS SHARE] Presentation...")

        presenter.presentViewController_animated_completion_(
            activity_vc,
            True,
            None
        )

        print("[IOS SHARE] Feuille de partage affichee")

    except Exception as e:
        import traceback

        print(
            f"[IOS SHARE] ERREUR : "
            f"{type(e).__name__}: {e}"
        )

        traceback.print_exc()

    print("=" * 60)
    print("[IOS SHARE] Fin")
    print("=" * 60)

class DateTextInput(TextInput):
    def insert_text(self, substring, from_undo=False):
        # On filtre pour ne garder que les chiffres
        chiffres_entres = "".join(c for c in substring if c.isdigit())
        if not chiffres_entres:
            return
        # On récupère les chiffres déjà présents
        chiffres_actuels = "".join(c for c in self.text if c.isdigit())
        # Maximum 8 chiffres : JJMMAAAA
        tous_les_chiffres = (chiffres_actuels + chiffres_entres)[:8]
        # Formatage JJ/MM/AAAA
        formate = ""
        for i, c in enumerate(tous_les_chiffres):
            formate += c
            if i == 1 or i == 3:
                formate += "/"
        self.text = formate
        self.cursor = (len(formate), 0)

class EventManager:
    @staticmethod
    def on_date_text(instance, value):
        if getattr(instance, "_en_cours_de_formatage", False):
            return
        # Nettoyage : uniquement les chiffres (max 8)
        chiffres = "".join(c for c in value if c.isdigit())[:8]
        # Construction dynamique du format JJ/MM/AAAA au fil de la frappe
        formate = ""
        for i, c in enumerate(chiffres):
            if i == 2 or i == 4:
                formate += "/"
            formate += c
        if formate != value:
            instance._en_cours_de_formatage = True
            instance.text = formate
            # On positionne le curseur juste après le texte qu'on vient de formater
            instance.cursor = (len(formate), 0)
            instance._en_cours_de_formatage = False

    @staticmethod
    def ouvrir_formulaire(screen_instance, match_id="", match_info=None):
        if match_info is None:
            match_info = {}
        if match_id and match_id != "Nouvel événement" and match_id != "Nouvel evenement":
            cat_data = getattr(screen_instance, "_cache_data", {}).get(screen_instance.current_cat, {})
            calendrier = cat_data.get("calendrier", {})
            if match_id in calendrier:
                match_info = calendrier[match_id]
                
        match_info_match = match_info.copy()
        match_info_entrainement = match_info.copy()
        match_info_evenement = match_info.copy()
    
        content = BoxLayout(orientation="vertical", padding=dp(15), spacing=dp(10))
        with content.canvas.before:
            Color(0.95, 0.95, 0.97, 1)
            self_bg = RoundedRectangle(pos=content.pos, size=content.size, radius=[dp(15)])
        content.bind(pos=lambda obj, val: setattr(self_bg, 'pos', val),
                     size=lambda obj, val: setattr(self_bg, 'size', val))
    
        lbl_titre_popup = Label(
            text="[b]Édition de l'événement[/b]",
            markup=True,
            size_hint_y=None,
            height=dp(35),
            font_size=dp(18),
            color=(0.1, 0.1, 0.15, 1),
            halign="center"
        )
        # 1. Le Titre du popup
        content.add_widget(lbl_titre_popup)
        
        # 2. Le bouton d'enregistrement unique tout en haut
        btn_save = Button(
            text="Enregistrer",
            size_hint_y=None,
            height=dp(45),
            background_normal="",
            background_color=(0.15, 0.65, 0.35, 1),
            color=(1, 1, 1, 1),
            bold=True
        )
        content.add_widget(btn_save)

        # 3. La barre des onglets (MATCH, ENTRAINEMENT, EVENEMENT)        
        tab_layout = BoxLayout(size_hint_y=None, height=dp(45), spacing=dp(5))
        tabs = ["MATCH", "ENTRAINEMENT", "EVENEMENT"]
        current_type = match_info.get("type", "MATCH").upper()
        if current_type not in tabs:
            current_type = "MATCH"
        tab_buttons = {}
        
        for t in tabs:
            btn_tab = Button(text=t, background_normal="", bold=True)
            btn_tab.bind(on_release=lambda btn, mode=t: rafraichir_formulaire(mode))
            tab_buttons[t] = btn_tab
            tab_layout.add_widget(btn_tab)
            
        content.add_widget(tab_layout)

        # 4. Le conteneur dynamique pour le formulaire (qui contient le ScrollView)
        dynamic_container = BoxLayout(orientation="vertical", size_hint=(1, 1))
        content.add_widget(dynamic_container)
        
        popup_ref = []

        def rafraichir_formulaire(t):
            nonlocal current_type
            current_type = t
            for k, btn in tab_buttons.items():
                if k == t:
                    btn.background_color = (0.2, 0.6, 0.3, 1)
                    btn.color = (1, 1, 1, 1)
                else:
                    btn.background_color = (0.85, 0.85, 0.88, 1)
                    btn.color = (0.3, 0.3, 0.3, 1)
                
            dynamic_container.clear_widgets()

            # Nettoyage des anciens binds du bouton global
            if hasattr(btn_save, '_current_callback'):
                btn_save.unbind(on_release=btn_save._current_callback)
            
            if current_type == "MATCH":
                btn_save.text = "Enregistrer le match"
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
    
                form_box.add_widget(Label(text="Date", size_hint_y=None, height=dp(25), halign="left", color=(0.2, 0.2, 0.25, 1)))
                ti_date = DateTextInput(
                    text=str(match_info.get("date", "")),
                    multiline=False,
                    size_hint_y=None,
                    height=dp(40),
                    background_color=(1, 1, 1, 1),
                    foreground_color=(0.1, 0.1, 0.1, 1),
                    cursor_color=(0.1, 0.1, 0.1, 1),
                    hint_text="JJ/MM/AAAA"
                )
                form_box.add_widget(ti_date)
                
                ti_heure_rdv = add_field("Heure du RDV (ex: 13:30)", match_info_match.get("heure_rdv", ""))
                ti_heure_sur_place = add_field("Convocation sur place (ex: 14:15)", match_info_match.get("heure_sur_place", ""))
                ti_heure_coup = add_field("Heure du coup d'envoi (ex: 15:00)", match_info_match.get("heure_coup_envoi", ""))
                ti_lieu = add_field("Lieu (Domicile / Extérieur)", match_info_match.get("lieu", ""))
                
                cat_data = screen_instance._cache_data.get(screen_instance.current_cat, {})
                liste_joueurs = cat_data.get("tous_les_joueurs", [])
                groupes_yaml = cat_data.get("groupes", {})
    
                dirigeants = [
                    f"{j.get('nom', '').strip().upper()} {j.get('prenom', '').strip().capitalize()}".strip()
                    for j in liste_joueurs
                    if str(j.get("poste", "")).strip().lower() == "dirigeant" or str(j.get("statut", "")).strip().lower() == "dirigeant"
                ]
                dirigeants = sorted(list(set(filter(None, dirigeants))))
    
                form_box.add_widget(Label(text="Entraîneurs présents", size_hint_y=None, height=dp(25), halign="left", color=(0.2, 0.2, 0.25, 1)))
                box_entraineurs = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(5))
                
                ti_entraineurs = TextInput(
                    text=str(match_info_match.get("entraineurs", "")),
                    multiline=False,
                    size_hint_y=None,
                    height=dp(40),
                    background_color=(1, 1, 1, 1),
                    foreground_color=(0.1, 0.1, 0.1, 1),
                    cursor_color=(0.1, 0.1, 0.1, 1)
                )
                box_entraineurs.add_widget(ti_entraineurs)
    
                if dirigeants:
                    dropdown_dir = DropDown()
                    for dir_nom in dirigeants:
                        btn_dir = Button(text=dir_nom, size_hint_y=None, height=dp(35), background_normal="", background_color=(0.9, 0.9, 0.9, 1), color=(0.1, 0.1, 0.1, 1))
                        def fit_text(b):
                            actuel = ti_entraineurs.text.strip()
                            if actuel:
                                if b.text not in actuel:
                                    ti_entraineurs.text = f"{actuel}, {b.text}"
                            else:
                                ti_entraineurs.text = b.text
                            dropdown_dir.dismiss()
                        btn_dir.bind(on_release=fit_text)
                        dropdown_dir.add_widget(btn_dir)
    
                    btn_select_dir = Button(
                        text="> Choisir",
                        size_hint_x=None,
                        width=dp(150),
                        background_normal="",
                        background_color=(0.2, 0.6, 0.3, 1),
                        color=(1, 1, 1, 1),
                        bold=True
                    )
                    btn_select_dir.bind(on_release=dropdown_dir.open)
                    box_entraineurs.add_widget(btn_select_dir)
    
                form_box.add_widget(box_entraineurs)
    
                form_box.add_widget(Label(text="Notes / Informations complémentaires", size_hint_y=None, height=dp(25), halign="left", color=(0.2, 0.2, 0.25, 1)))
                ti_notes = TextInput(
                    text=str(match_info.get("notes", "")),
                    multiline=True,
                    size_hint_y=None,
                    height=dp(80),
                    background_color=(1, 1, 1, 1),
                    foreground_color=(0.1, 0.1, 0.1, 1),
                    cursor_color=(0.1, 0.1, 0.1, 1)
                )
                form_box.add_widget(ti_notes)
    
                form_box.add_widget(Label(text="[b]Sondages & Options[/b]", markup=True, size_hint_y=None, height=dp(30), color=(0.15, 0.45, 0.25, 1)))
                
                # --- NOUVELLE OPTION : EXPORTER PDF ---
                box_exporter_pdf = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(10))
                chk_exporter_pdf = CheckBox(active=False, size_hint_x=None, width=dp(40), color=(0.2, 0.2, 0.2, 1))
                box_exporter_pdf.add_widget(chk_exporter_pdf)
                
                if platform == "android":
                    texte_export_pdf = "Générer le PDF dans Download/FCVV"
                elif platform == "ios":
                    texte_export_pdf = "Générer et partager le PDF"
                else:
                    texte_export_pdf = "Générer le PDF dans Documents"
                
                box_exporter_pdf.add_widget(Label(text=texte_export_pdf,halign="left",color=(0.2, 0.2, 0.25, 1)))
                form_box.add_widget(box_exporter_pdf)
                
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
    
                container_joueurs_section = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(5))
                container_joueurs_section.bind(minimum_height=container_joueurs_section.setter('height'))
                form_box.add_widget(container_joueurs_section)
    
                checkboxes_joueurs = []
    
                def actualiser_section_joueurs(checkbox, value):
                    container_joueurs_section.clear_widgets()
                    checkboxes_joueurs.clear()
                    
                    if value:
                        lbl_compteur = Label(
                            text="[b]--- Liste des Joueurs Convoqués (Sélectionnés : 0) ---[/b]", 
                            markup=True, size_hint_y=None, height=dp(30), color=(0.15, 0.45, 0.25, 1)
                        )
                        container_joueurs_section.add_widget(lbl_compteur)
    
                        def mettre_a_jour_compteur(*args):
                            nb_coches = sum(1 for cb in checkboxes_joueurs if cb.active)
                            lbl_compteur.text = f"[b]--- Liste des Joueurs Convoqués (Sélectionnés : {nb_coches}) ---[/b]"
    
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
                                    joueurs_du_groupe = groupes_yaml[texte_selectionne]
                                    joueurs_groupe_lower = [j.strip().lower() for j in joueurs_du_groupe]
    
                                    for cb in checkboxes_joueurs:
                                        nom_cb = getattr(cb, 'nom_joueur', "").strip().lower()
                                        prenom_cb = getattr(cb, 'prenom_joueur', "").strip().lower()
                                        format_1 = f"{nom_cb} {prenom_cb}".strip()
                                        format_2 = f"{prenom_cb} {nom_cb}".strip()
                                        
                                        cb.active = any(
                                            (format_1 in j or j in format_1) or (format_2 in j or j in format_2)
                                            for j in joueurs_groupe_lower
                                        )
    
                            spinner_groupes.bind(text=sur_changement_groupe)
                            box_groupe.add_widget(spinner_groupes)
                            container_joueurs_section.add_widget(box_groupe)
    
                        joueurs_layout = GridLayout(cols=1, size_hint_y=None, spacing=dp(5))
                        joueurs_layout.bind(minimum_height=joueurs_layout.setter('height'))
    
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
    
                                nom_affiche = f"{nom} {prenom}".strip()
                                label_text_brut = f"{nom_affiche} ({cat})" if cat else nom_affiche
    
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
                                nom_affiche = f"{nom} {prenom}".strip()
                                label_text = f"{nom_affiche} ({cat})" if cat else nom_affiche
    
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
                            cat_joueur = joueur.get('categorie', '').strip()
                            nom_complet = f"{nom} {prenom}".strip()
                            
                            if any(cb.nom_joueur == nom and cb.prenom_joueur == prenom for cb in checkboxes_joueurs if getattr(cb, 'est_manuel', False)):
                                continue
    
                            texte_affichage = f"{nom_complet} ({cat_joueur})" if cat_joueur else nom_complet
    
                            row = BoxLayout(size_hint_y=None, height=dp(35), spacing=dp(10))
                            chk_j = CheckBox(active=(nom_complet in noms_deja_convoques), size_hint_x=None, width=dp(40), color=(0.2, 0.2, 0.2, 1))
                            chk_j.nom_joueur = nom
                            chk_j.prenom_joueur = prenom
                            chk_j.categorie = cat_joueur
                            chk_j.est_manuel = False
                            
                            lbl_j = Label(
                                text=f"[b]{texte_affichage}[/b]" if chk_j.active else texte_affichage,
                                markup=True,
                                halign="left",
                                color=(0.2, 0.2, 0.25, 1)
                            )
    
                            def update_label_style(cb, value, label_widget=lbl_j, texte_brut=texte_affichage):
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
                
                def save_match(x):
                    print("\n" + "=" * 80)
                    print("[SAVE] CLIC SUR 'Enregistrer le match'")
                    print(f"[SAVE] platform = {platform}")
                    print(f"[SAVE] match_id = {match_id!r}")
                    print(f"[SAVE] current_cat = {screen_instance.current_cat!r}")
                    print("=" * 80)
                
                    date_val = ti_date.text.strip()
                
                    print(f"[SAVE] Date saisie = {date_val!r}")
                
                    try:
                        datetime.strptime(date_val, "%d/%m/%Y")
                        print("[SAVE] Date valide")
                    except ValueError:
                        print("[SAVE] Date invalide -> ouverture popup erreur")
                
                        p_err = Popup(
                            title="Erreur de format",
                            content=Label(
                                text="Format de date invalide !\nVeuillez utiliser le format JJ/MM/AAAA",
                                color=(0.2, 0.2, 0.2, 1),
                                halign="center"
                            ),
                            size_hint=(0.7, 0.3),
                            separator_height=0
                        )
                
                        p_err.open()
                        return
                
                    calendrier_actuel = (
                        screen_instance._cache_data
                        .get(screen_instance.current_cat, {})
                        .get("calendrier", {})
                    )
                
                    est_une_modification = bool(match_id) and match_id in calendrier_actuel
                
                    print(f"[SAVE] est_une_modification = {est_une_modification}")
                    print(f"[SAVE] calendrier contient match_id = {match_id in calendrier_actuel}")
                
                    def executer_sauvegarde(commit_message=""):
                
                        print("\n" + "-" * 80)
                        print("[EXEC] >>> ENTREE executer_sauvegarde()")
                        print(f"[EXEC] platform = {platform}")
                        print(f"[EXEC] commit_message = {commit_message!r}")
                        print("-" * 80)
                
                        joueurs_convoques = []
                
                        print(f"[EXEC] chk_convocation.active = {chk_convocation.active}")
                        print(f"[EXEC] Nombre checkboxes = {len(checkboxes_joueurs)}")
                
                        if chk_convocation.active:
                
                            for cb in checkboxes_joueurs:
                                if cb.active:
                
                                    nom = getattr(cb, "nom_joueur", "").strip().upper()
                                    prenom = getattr(cb, "prenom_joueur", "").strip()
                                    cat_equipe = screen_instance.current_cat
                                    cat_joueur = getattr(cb, "categorie", "").strip().upper()
                                    est_manuel = getattr(cb, "est_manuel", False)
                
                                    print(
                                        f"[EXEC] Joueur selectionne: "
                                        f"{nom} {prenom} | "
                                        f"cat={cat_joueur} | "
                                        f"manuel={est_manuel}"
                                    )
                
                                    if est_manuel or cat_equipe:
                                        joueurs_convoques.append({
                                            "nom": nom,
                                            "prenom": prenom,
                                            "categorie": cat_equipe,
                                            "categorie_joueur": cat_joueur,
                                            "est_manuel": est_manuel
                                        })
                                    else:
                                        nom_complet = f"{nom} {prenom}".strip()
                
                                        if nom_complet:
                                            joueurs_convoques.append(nom_complet)
                
                        print(
                            f"[EXEC] Nombre joueurs_convoques = "
                            f"{len(joueurs_convoques)}"
                        )
                
                        maintenant_str = datetime.now().strftime("%d/%m/%Y à %H:%M")
                
                        match_info_match.update({
                            "type": "MATCH",
                            "titre": ti_titre.text.strip(),
                            "adversaire": ti_adversaire.text.strip(),
                            "date": date_val,
                            "heure_rdv": ti_heure_rdv.text.strip(),
                            "heure_sur_place": ti_heure_sur_place.text.strip(),
                            "heure_coup_envoi": ti_heure_coup.text.strip(),
                            "lieu": ti_lieu.text.strip(),
                            "entraineurs": ti_entraineurs.text.strip(),
                            "notes": ti_notes.text.strip(),
                            "sondage_classique": chk_sondage_classique.active,
                            "sondage_trajet": chk_sondage_trajet.active,
                            "activer_convocation": chk_convocation.active,
                            "joueurs_convoques": joueurs_convoques,
                            "dernier_commit": commit_message,
                            "timestamp_action": maintenant_str,
                            "est_modification": est_une_modification
                        })
                
                        print("[EXEC] match_info_match construit")
                        print(f"[EXEC] titre = {match_info_match.get('titre')!r}")
                        print(f"[EXEC] adversaire = {match_info_match.get('adversaire')!r}")
                        print(f"[EXEC] date = {match_info_match.get('date')!r}")
                        print(f"[EXEC] commit = {match_info_match.get('dernier_commit')!r}")
                
                        # ---------------------------------------------------------
                        # PDF
                        # ---------------------------------------------------------
                
                        print(
                            f"[PDF] chk_exporter_pdf.active = "
                            f"{chk_exporter_pdf.active}"
                        )
                
                        if chk_exporter_pdf.active:
                            print("[PDF] Debut generation PDF")
                
                            try:
                                generer_pdf_convocation(
                                    match_info_match,
                                    liste_joueurs
                                )
                
                                print("[PDF] Generation PDF terminee")
                
                            except Exception as e_pdf:
                                print(
                                    f"[PDF] ERREUR generation PDF : "
                                    f"{type(e_pdf).__name__}: {e_pdf}"
                                )
                
                        # ---------------------------------------------------------
                        # KEY
                        # ---------------------------------------------------------
                
                        if est_une_modification:
                            key = match_id
                
                            print(f"[EXEC] Modification -> key = {key!r}")
                
                        else:
                            adv_clean = (
                                ti_adversaire.text
                                .strip()
                                .replace(" ", "_")
                                .lower()
                                or "inconnu"
                            )
                
                            date_clean = date_val.replace("/", "-")
                
                            heure_clean = (
                                ti_heure_rdv.text
                                .strip()
                                .replace(":", "h")
                                or "00h00"
                            )
                
                            key = (
                                f"match_{adv_clean}_"
                                f"{date_clean}_"
                                f"{heure_clean}"
                            )
                
                            print(f"[EXEC] Creation -> key = {key!r}")
                
                        # ---------------------------------------------------------
                        # CACHE LOCAL
                        # ---------------------------------------------------------
                
                        data = screen_instance._cache_data.get(
                            screen_instance.current_cat,
                            {}
                        )
                
                        if "calendrier" not in data:
                            print("[CACHE] calendrier absent -> creation")
                            data["calendrier"] = {}
                
                        if est_une_modification and match_id in data["calendrier"]:
                
                            if match_id != key:
                
                                print(
                                    f"[CACHE] Suppression ancienne cle : "
                                    f"{match_id!r}"
                                )
                
                                data["calendrier"].pop(
                                    match_id,
                                    None
                                )
                
                        data["calendrier"][key] = match_info_match
                
                        print("[CACHE] evenement enregistre dans le cache")
                        print(f"[CACHE] key = {key!r}")
                        print(
                            f"[CACHE] Nombre evenements = "
                            f"{len(data['calendrier'])}"
                        )
                
                        # ---------------------------------------------------------
                        # URL API
                        # ---------------------------------------------------------
                
                        url = (
                            "https://fcvv-api.onrender.com/"
                            f"convocations/update/"
                            f"{screen_instance.current_cat}/"
                            f"{key}"
                        )
                
                        print("\n[API] URL PUT :")
                        print(url)
                
                        # ---------------------------------------------------------
                        # API THREAD
                        # ---------------------------------------------------------
                
                        def do_api_save():
                
                            print("\n" + "=" * 80)
                            print("[THREAD API] DeMARRAGE")
                            print(f"[THREAD API] platform = {platform}")
                            print(f"[THREAD API] key = {key!r}")
                            print("=" * 80)
                
                            try:
                
                                headers = (
                                    screen_instance.get_user_header()
                                    if hasattr(screen_instance, "get_user_header")
                                    else {}
                                )
                
                                print(
                                    f"[THREAD API] headers presents = "
                                    f"{bool(headers)}"
                                )
                
                                if headers:
                                    print(
                                        f"[THREAD API] header keys = "
                                        f"{list(headers.keys())}"
                                    )
                
                                is_windows = (platform == "win")
                
                                # -------------------------------------------------
                                # PUT
                                # -------------------------------------------------
                
                                print("[PUT] Envoi de la requete...")
                
                                response = requests.put(
                                    url,
                                    json=match_info_match,
                                    headers=headers,
                                    timeout=10,
                                    verify=not is_windows
                                )
                
                                print(
                                    f"[PUT] status_code = "
                                    f"{response.status_code}"
                                )
                
                                print(
                                    f"[PUT] response = "
                                    f"{response.text[:1000]!r}"
                                )
                
                                response.raise_for_status()
                
                                print("[PUT] PUT reussi")
                
                                # -------------------------------------------------
                                # POST HISTORIQUE
                                # -------------------------------------------------
                
                                stats_url = (
                                    "https://fcvv-api.onrender.com/"
                                    f"stats/historique/evenement/"
                                    f"{screen_instance.current_cat}/"
                                    f"{key}"
                                )
                
                                print("\n[POST] URL historique :")
                                print(stats_url)
                
                                response_stats = requests.post(
                                    stats_url,
                                    headers=headers,
                                    timeout=10,
                                    verify=not is_windows
                                )
                
                                print(
                                    f"[POST] status_code = "
                                    f"{response_stats.status_code}"
                                )
                
                                print(
                                    f"[POST] response = "
                                    f"{response_stats.text[:1000]!r}"
                                )
                
                                response_stats.raise_for_status()
                
                                print("[POST] POST historique reussi")
                
                                # -------------------------------------------------
                                # REFRESH UI
                                # -------------------------------------------------
                
                                print(
                                    "[API] Programmation de "
                                    "fetch_convocations_from_firebase()"
                                )
                
                                Clock.schedule_once(
                                    lambda dt: (
                                        print(
                                            "[CLOCK] Execution "
                                            "fetch_convocations_from_firebase()"
                                        ),
                                        screen_instance.fetch_convocations_from_firebase(
                                            data
                                        )
                                    )
                                )
                
                                print("[THREAD API] FIN NORMALE")
                
                            except Exception as e:
                
                                print("\n" + "!" * 80)
                                print("[THREAD API] ERREUR")
                                print(f"type = {type(e).__name__}")
                                print(f"message = {e}")
                                print("!" * 80)
                
                                Clock.schedule_once(
                                    lambda dt: (
                                        print("[CLOCK] update_ui() après erreur API"),
                                        screen_instance.update_ui()
                                    )
                                )
                
                        # ---------------------------------------------------------
                        # DÉMARRAGE THREAD
                        # ---------------------------------------------------------
                
                        print("[THREAD] Creation du thread API")
                
                        thread = threading.Thread(
                            target=do_api_save,
                            daemon=True
                        )
                
                        thread.start()
                
                        print(
                            f"[THREAD] Thread demarre : "
                            f"{thread.name}"
                        )
                
                        # ---------------------------------------------------------
                        # FERMETURE POPUP PRINCIPALE
                        # ---------------------------------------------------------
                
                        print(
                            f"[POPUP MAIN] popup_ref = {popup_ref!r}"
                        )
                
                        if popup_ref:
                
                            print(
                                "[POPUP MAIN] Appel popup_ref[0].dismiss()"
                            )
                
                            try:
                                print("[POPUP MAIN] popup_ref[0] =", popup_ref[0])
                                print("[POPUP MAIN] is_open =", popup_ref[0]._is_open)
                                popup_ref[0].dismiss()

                                print("[POPUP MAIN] dismiss terminé")
                                print("[POPUP MAIN] is_open apres =", popup_ref[0]._is_open)
                
                                print(
                                    "[POPUP MAIN] dismiss() appele"
                                )
                
                            except Exception as e_popup:
                
                                print(
                                    f"[POPUP MAIN] ERREUR dismiss : "
                                    f"{type(e_popup).__name__}: {e_popup}"
                                )
                
                        else:
                
                            print(
                                "[POPUP MAIN] popup_ref est VIDE !"
                            )
                
                        print("[EXEC] <<< SORTIE executer_sauvegarde()")
                
                    # =============================================================
                    # MODIFICATION
                    # =============================================================
                
                    if est_une_modification:
                
                        print("\n" + "=" * 80)
                        print("[COMMIT] MODE MODIFICATION")
                        print("[COMMIT] Creation popup 'Motif de modification'")
                        print("=" * 80)
                
                        content_commit = BoxLayout(
                            orientation="vertical",
                            padding=dp(15),
                            spacing=dp(10)
                        )
                
                        ti_commit = TextInput(
                            hint_text="Ex: Modification de l'heure du RDV",
                            multiline=False,
                            size_hint_y=None,
                            height=dp(40),
                            background_color=(1, 1, 1, 1),
                            foreground_color=(0.1, 0.1, 0.1, 1),
                            cursor_color=(0.1, 0.1, 0.1, 1)
                        )
                
                        content_commit.add_widget(ti_commit)
                
                        btn_valider_commit = Button(
                            text="Confirmer l'enregistrement",
                            size_hint_y=None,
                            height=dp(45),
                            background_normal="",
                            background_color=(0.15, 0.65, 0.35, 1),
                            color=(1, 1, 1, 1),
                            bold=True
                        )
                
                        content_commit.add_widget(
                            btn_valider_commit
                        )
                
                        content_commit.add_widget(
                            Label(
                                text="[b]Note de modification (optionnel)[/b]",
                                markup=True,
                                size_hint_y=None,
                                height=dp(30),
                                color=(0.15, 0.45, 0.25, 1)
                            )
                        )
                
                        content_commit.add_widget(
                            Widget()
                        )
                
                        popup_commit = Popup(
                            title="Motif de modification",
                            content=content_commit,
                            size_hint=(0.8, 0.4),
                            separator_height=0,
                            auto_dismiss=False
                        )
                
                        # ---------------------------------------------------------
                        # DEBUG POPUP COMMIT
                        # ---------------------------------------------------------
                
                        def debug_popup_open(*args):
                            print("[POPUP COMMIT] on_open")
                
                        def debug_popup_dismiss(*args):
                            print("[POPUP COMMIT] on_dismiss")
                            print("[POPUP COMMIT] dismiss declenche")
                
                        def debug_popup_touch_down(instance, touch):
                            print(
                                "[POPUP COMMIT] touch_down "
                                f"pos={touch.pos}"
                            )
                
                        popup_commit.bind(
                            on_open=debug_popup_open,
                            on_dismiss=debug_popup_dismiss
                        )
                
                        # ---------------------------------------------------------
                        # CLIC CONFIRMATION
                        # ---------------------------------------------------------
                
                        def valider_avec_commit(instance):
                            print("[COMMIT BUTTON] CLIC SUR CONFIRMER")
                        
                            msg = ti_commit.text.strip()
                            print("[COMMIT BUTTON] msg =", repr(msg))
                        
                            # Important sur iOS :
                            # retirer le focus du TextInput avant de fermer le Popup.
                            ti_commit.focus = False
                        
                            def fermer_popup_et_sauvegarder(dt):
                                print("[COMMIT BUTTON] Fermeture popup_commit")
                        
                                if popup_commit and popup_commit._is_open:
                                    popup_commit.dismiss()
                                if popup_ref and popup_ref[0] and popup_ref[0]._is_open:
                                    popup_ref[0].dismiss()
                        
                                def lancer_sauvegarde(dt2):
                                    print("[CLOCK COMMIT] Lancement executer_sauvegarde")
                                    executer_sauvegarde(msg)
                        
                                Clock.schedule_once(lancer_sauvegarde, 0.15)
                        
                            # Laisser iOS terminer la gestion du clavier virtuel
                            Clock.schedule_once(fermer_popup_et_sauvegarder, 0.3)

                
                        btn_valider_commit.bind(on_release=valider_avec_commit)
                        print("[COMMIT] Ouverture popup_commit")
                        popup_commit.open()
                
                        print(
                            "[COMMIT] popup_commit.open() termine"
                        )
                
                    # =============================================================
                    # NOUVEL ÉVÉNEMENT
                    # =============================================================
                
                    else:
                
                        print("\n" + "=" * 80)
                        print("[SAVE] MODE CReATION")
                        print("[SAVE] Appel executer_sauvegarde() direct")
                        print("=" * 80)
                
                        executer_sauvegarde(
                            "Création de l'événement"
                        )

    
                btn_save._current_callback = save_match
                btn_save.bind(on_release=save_match)

            elif current_type == "ENTRAINEMENT":
                btn_save.text = "Enregistrer l'entraînement"
                form_scroll = ScrollView(bar_width=0, size_hint=(1, 1))
                form_box = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(10), padding=dp(5))
                form_box.bind(minimum_height=form_box.setter("height"))

                def add_field(label_text, default_val=""):
                    form_box.add_widget(Label(text=label_text, size_hint_y=None, height=dp(25), halign="left", color=(0.2, 0.2, 0.25, 1)))
                    ti = TextInput(text=str(default_val), multiline=False, size_hint_y=None, height=dp(40), background_color=(1, 1, 1, 1), foreground_color=(0.1, 0.1, 0.1, 1), cursor_color=(0.1, 0.1, 0.1, 1))
                    form_box.add_widget(ti)
                    return ti

                ti_titre = add_field("Titre de l'entraînement", match_info_entrainement.get("titre", ""))
                
                # --- CHAMP DATE INSTANTANÉ ---
                form_box.add_widget(Label(text="Date", size_hint_y=None, height=dp(25), halign="left", color=(0.2, 0.2, 0.25, 1)))
                ti_date_debut = DateTextInput(
                    text=str(match_info_entrainement.get("date", "")),
                    multiline=False,
                    size_hint_y=None,
                    height=dp(40),
                    background_color=(1, 1, 1, 1),
                    foreground_color=(0.1, 0.1, 0.1, 1),
                    cursor_color=(0.1, 0.1, 0.1, 1),
                    hint_text="JJ/MM/AAAA"
                )
                form_box.add_widget(ti_date_debut)
                
                ti_heure = add_field("Heure (ex: 19:30)", match_info_entrainement.get("heure", match_info_entrainement.get("heure_rdv", "")))
                ti_lieu = add_field("Lieu", match_info_entrainement.get("lieu", ""))

                form_box.add_widget(Label(text="Notes / Informations complémentaires", size_hint_y=None, height=dp(25), halign="left", color=(0.2, 0.2, 0.25, 1)))
                ti_notes = TextInput(
                    text=str(match_info_entrainement.get("notes", "")),
                    multiline=True,              # Permet d'aller à la ligne et d'écrire de longs textes
                    size_hint_y=None,
                    height=dp(80),               # Hauteur plus confortable (environ 3 lignes)
                    background_color=(1, 1, 1, 1),
                    foreground_color=(0.1, 0.1, 0.1, 1),
                    cursor_color=(0.1, 0.1, 0.1, 1)
                )
                form_box.add_widget(ti_notes)

                # --- SONDAGE DE PRÉSENCE ---
                sondage_box = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(40), spacing=dp(10))
                chk_sondage = CheckBox(active=match_info_entrainement.get("sondage_actif", True), size_hint_x=None, width=dp(40), color=(0.2, 0.2, 0.2, 1))
                sondage_box.add_widget(chk_sondage)
                sondage_box.add_widget(Label(text="Activer un sondage de présence requis", color=(0.2, 0.2, 0.25, 1), halign="left"))
                
                form_box.add_widget(sondage_box)

                # --- BLOC RÉCURRENCE ---
                calendrier_actuel = screen_instance._cache_data.get(screen_instance.current_cat, {}).get("calendrier", {})
                est_une_modification = bool(match_id) and match_id in calendrier_actuel

                # On masque la récurrence si on est en train de modifier un entraînement existant
                chk_recurrent = CheckBox(active=False, size_hint_x=None, width=dp(40), color=(0.2, 0.2, 0.2, 1))
                ti_date_fin = None
                sp_frequence = None

                if not est_une_modification:
                    box_recurrent = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(10))
                    box_recurrent.add_widget(chk_recurrent)
                    box_recurrent.add_widget(Label(text="Événement récurrent", halign="left", color=(0.2, 0.2, 0.25, 1)))
                    form_box.add_widget(box_recurrent)

                    container_recurrence = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(10))
                    container_recurrence.bind(minimum_height=container_recurrence.setter('height'))
                    form_box.add_widget(container_recurrence)

                    def toggle_recurrence(cb, active):
                        nonlocal ti_date_fin, sp_frequence
                        container_recurrence.clear_widgets()
                        if active:
                            container_recurrence.add_widget(Label(text="Date de fin (Format JJ/MM/AAAA)", size_hint_y=None, height=dp(25), halign="left", color=(0.2, 0.2, 0.25, 1)))
                            
                            # Utilisation de DateTextInput ici
                            ti_date_fin = DateTextInput(
                                hint_text="ex: 30/06/2026", 
                                multiline=False, 
                                size_hint_y=None, 
                                height=dp(40), 
                                background_color=(1, 1, 1, 1), 
                                foreground_color=(0.1, 0.1, 0.1, 1), 
                                cursor_color=(0.1, 0.1, 0.1, 1)
                            )
                            container_recurrence.add_widget(ti_date_fin)

                            container_recurrence.add_widget(Label(text="Type de récurrence", size_hint_y=None, height=dp(25), halign="left", color=(0.2, 0.2, 0.25, 1)))
                            sp_frequence = Spinner(
                                text="Hebdomadaire",
                                values=["Hebdomadaire", "Mensuel"],
                                size_hint_y=None,
                                height=dp(40),
                                background_normal="",
                                background_color=(0.15, 0.65, 0.35, 1),
                                color=(1, 1, 1, 1)
                            )
                            container_recurrence.add_widget(sp_frequence)
                        else:
                            ti_date_fin = None
                            sp_frequence = None

                    chk_recurrent.bind(active=toggle_recurrence)

                form_scroll.add_widget(form_box)
                dynamic_container.add_widget(form_scroll)
                
                def save_entrainement(x):
                    date_deb_str = ti_date_debut.text.strip()
                    try:
                        d_debut = datetime.strptime(date_deb_str, "%d/%m/%Y")
                    except ValueError:
                        p_err = Popup(title="Erreur de format", content=Label(text="Format de date de début invalide !\nVeuillez utiliser le format JJ/MM/AAAA", color=(0.2, 0.2, 0.2, 1), halign="center"), size_hint=(0.7, 0.3), separator_height=0)
                        p_err.open()
                        return

                    # Vérification des dates en cas de récurrence
                    dates_a_creer = [d_debut]
                    if chk_recurrent.active:
                        if not ti_date_fin or not ti_date_fin.text.strip():
                            p_err = Popup(title="Champ manquant", content=Label(text="Veuillez renseigner une date de fin !", color=(0.2, 0.2, 0.2, 1), halign="center"), size_hint=(0.7, 0.3), separator_height=0)
                            p_err.open()
                            return
                        try:
                            d_fin = datetime.strptime(ti_date_fin.text.strip(), "%d/%m/%Y")
                        except ValueError:
                            p_err = Popup(title="Erreur de format", content=Label(text="Format de date de fin invalide !", color=(0.2, 0.2, 0.2, 1), halign="center"), size_hint=(0.7, 0.3), separator_height=0)
                            p_err.open()
                            return

                        if d_fin <= d_debut:
                            p_err = Popup(title="Erreur de date", content=Label(text="La date de fin doit être postérieure à la date de début !", color=(0.2, 0.2, 0.2, 1), halign="center"), size_hint=(0.7, 0.3), separator_height=0)
                            p_err.open()
                            return

                        # Génération des dates
                        dates_a_creer = []
                        curr = d_debut
                        freq = sp_frequence.text if sp_frequence else "Hebdomadaire"

                        while curr <= d_fin:
                            dates_a_creer.append(curr)
                            if freq == "Hebdomadaire":
                                curr += timedelta(days=7)
                            elif freq == "Mensuel":
                                # Ajout d'un mois approximatif en conservant le même jour
                                month = curr.month % 12 + 1
                                year = curr.year + (curr.month // 12)
                                day = min(curr.day, 28) # Sécurité pour les fin de mois
                                curr = datetime(year, month, day)

                    def executer_sauvegarde(commit_message=""):
                        maintenant_str = datetime.now().strftime("%d/%m/%Y à %H:%M")
                        data = screen_instance._cache_data.get(screen_instance.current_cat, {})
                        if "calendrier" not in data:
                            data["calendrier"] = {}

                        payload_batch = {}

                        for d in dates_a_creer:
                            d_str = d.strftime("%d/%m/%Y")
                            date_clean = d_str.replace("/", "-")
                            heure_clean = ti_heure.text.strip().replace(":", "h") or "00h00"

                            info_entrainement = match_info_entrainement.copy()
                            info_entrainement.update({
                                "type": "ENTRAINEMENT",
                                "titre": ti_titre.text.strip(),
                                "date": d_str,
                                "heure": ti_heure.text.strip(),
                                "lieu": ti_lieu.text.strip(),
                                "notes": ti_notes.text.strip(),
                                "sondage_actif": chk_sondage.active,
                                "dernier_commit": commit_message,
                                "timestamp_action": maintenant_str,
                                "est_modification": est_une_modification
                            })

                            key = match_id if est_une_modification else f"entrainement_{date_clean}_{heure_clean}"
                            
                            if est_une_modification and match_id in data["calendrier"] and match_id != key:
                                data["calendrier"].pop(match_id, None)

                            data["calendrier"][key] = info_entrainement
                            payload_batch[key] = info_entrainement

                        # URL Batch pour récurrence (création unique si non récurrent)
                        is_batch = len(payload_batch) > 1
                        if is_batch:
                            url = f"https://fcvv-api.onrender.com/convocations/batch-update/{screen_instance.current_cat}"
                        else:
                            single_key = list(payload_batch.keys())[0]
                            url = f"https://fcvv-api.onrender.com/convocations/update/{screen_instance.current_cat}/{single_key}"

                        def do_api_save():
                            try:
                                headers = screen_instance.get_user_header() if hasattr(screen_instance, "get_user_header") else {}
                                is_windows = (platform == 'win')
                        
                                if is_batch:
                                    url = f"https://fcvv-api.onrender.com/convocations/batch-update/{screen_instance.current_cat}"
                                    json_payload = {"evenements": list(payload_batch.values())}
                                else:
                                    single_key = list(payload_batch.keys())[0]
                                    url = f"https://fcvv-api.onrender.com/convocations/update/{screen_instance.current_cat}/{single_key}"
                                    json_payload = list(payload_batch.values())[0]
                        
                                requests.put(url, json=json_payload, headers=headers, timeout=15, verify=not is_windows)
                                requests.post(
                                    f"https://fcvv-api.onrender.com/stats/historique/evenement/"
                                    f"{screen_instance.current_cat}/{key}",
                                    headers=headers,
                                    timeout=10,
                                    verify=not is_windows
                                )
                                Clock.schedule_once(lambda dt: screen_instance.fetch_convocations_from_firebase(data))
                            except Exception as e:
                                print(f"Erreur sauvegarde entrainement API : {e}")
                                Clock.schedule_once(lambda dt: screen_instance.update_ui())

                        threading.Thread(target=do_api_save, daemon=True).start()
                        if popup_ref:
                            popup_ref[0].dismiss()

                    if est_une_modification:
                        content_commit = BoxLayout(orientation='vertical', padding=dp(15), spacing=dp(10))
                        ti_commit = TextInput(hint_text="Ex: Modification de l'heure", multiline=False, size_hint_y=None, height=dp(40), background_color=(1, 1, 1, 1), foreground_color=(0.1, 0.1, 0.1, 1), cursor_color=(0.1, 0.1, 0.1, 1))
                        content_commit.add_widget(ti_commit)
                        
                        btn_valider_commit = Button(text="Confirmer l'enregistrement", size_hint_y=None, height=dp(45), background_normal="", background_color=(0.15, 0.65, 0.35, 1), color=(1, 1, 1, 1), bold=True)
                        content_commit.add_widget(btn_valider_commit)
                        content_commit.add_widget(Label(text="[b]Motif de la modification[/b]", markup=True, size_hint_y=None, height=dp(30), color=(0.15, 0.45, 0.25, 1)))
                        content_commit.add_widget(Widget())
                        
                        popup_commit = Popup(title="Modification", content=content_commit, size_hint=(0.8, 0.4), separator_height=0)
                        
                        # ---------------------------------------------------------
                        # CLIC CONFIRMATION
                        # ---------------------------------------------------------
                
                        def valider_avec_commit(instance):
                            print("[COMMIT BUTTON] CLIC SUR CONFIRMER")
                        
                            msg = ti_commit.text.strip()
                            print("[COMMIT BUTTON] msg =", repr(msg))
                        
                            # Important sur iOS :
                            # retirer le focus du TextInput avant de fermer le Popup.
                            ti_commit.focus = False
                        
                            def fermer_popup_et_sauvegarder(dt):
                                print("[COMMIT BUTTON] Fermeture popup_commit")
                        
                                if popup_commit._is_open:
                                    popup_commit.dismiss()
                        
                                def lancer_sauvegarde(dt2):
                                    print("[CLOCK COMMIT] Lancement executer_sauvegarde")
                                    executer_sauvegarde(msg)
                        
                                Clock.schedule_once(lancer_sauvegarde, 0.15)
                        
                            # Laisser iOS terminer la gestion du clavier virtuel
                            Clock.schedule_once(fermer_popup_et_sauvegarder, 0.15)
                            
                        btn_valider_commit.bind(on_release=valider_avec_commit)
                        popup_commit.open()
                    else:
                        executer_sauvegarde("Création d'entraînement récurrent" if chk_recurrent.active else "Création de l'entraînement")

                btn_save._current_callback = save_entrainement
                btn_save.bind(on_release=save_entrainement)

            # --- ONGLET EVENEMENT ---
            else:
                btn_save.text = "Enregistrer l'événement"
                form_scroll = ScrollView(bar_width=0, size_hint=(1, 1))
                form_box = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(10), padding=dp(5))
                form_box.bind(minimum_height=form_box.setter("height"))

                def add_field(label_text, default_val=""):
                    form_box.add_widget(Label(text=label_text, size_hint_y=None, height=dp(25), halign="left", color=(0.2, 0.2, 0.25, 1)))
                    ti = TextInput(text=str(default_val), multiline=False, size_hint_y=None, height=dp(40), background_color=(1, 1, 1, 1), foreground_color=(0.1, 0.1, 0.1, 1), cursor_color=(0.1, 0.1, 0.1, 1))
                    form_box.add_widget(ti)
                    return ti

                ti_titre = add_field("Titre de l'événement", match_info_evenement.get("titre", ""))
                
                # --- CHAMP DATE INSTANTANÉ ---
                form_box.add_widget(Label(text="Date", size_hint_y=None, height=dp(25), halign="left", color=(0.2, 0.2, 0.25, 1)))
                ti_date = DateTextInput(
                    text=str(match_info_evenement.get("date", "")),
                    multiline=False,
                    size_hint_y=None,
                    height=dp(40),
                    background_color=(1, 1, 1, 1),
                    foreground_color=(0.1, 0.1, 0.1, 1),
                    cursor_color=(0.1, 0.1, 0.1, 1),
                    hint_text="JJ/MM/AAAA"
                )
                form_box.add_widget(ti_date)
                
                ti_heure = add_field("Heure", match_info_evenement.get("heure", ""))
                ti_lieu = add_field("Lieu", match_info_evenement.get("lieu", ""))

                form_box.add_widget(Label(text="Notes / Informations complémentaires", size_hint_y=None, height=dp(25), halign="left", color=(0.2, 0.2, 0.25, 1)))
                ti_notes = TextInput(
                    text=str(match_info_evenement.get("notes", "")),
                    multiline=True,              # Permet d'aller à la ligne et d'écrire de longs textes
                    size_hint_y=None,
                    height=dp(80),               # Hauteur plus confortable (environ 3 lignes)
                    background_color=(1, 1, 1, 1),
                    foreground_color=(0.1, 0.1, 0.1, 1),
                    cursor_color=(0.1, 0.1, 0.1, 1)
                )
                form_box.add_widget(ti_notes)

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
                            "notes": ti_notes.text.strip(),
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
                        
                        # ---------------------------------------------------------
                        # CLIC CONFIRMATION
                        # ---------------------------------------------------------
                
                        def valider_avec_commit(instance):
                            print("[COMMIT BUTTON] CLIC SUR CONFIRMER")
                        
                            msg = ti_commit.text.strip()
                            print("[COMMIT BUTTON] msg =", repr(msg))
                        
                            # Important sur iOS :
                            # retirer le focus du TextInput avant de fermer le Popup.
                            ti_commit.focus = False
                        
                            def fermer_popup_et_sauvegarder(dt):
                                print("[COMMIT BUTTON] Fermeture popup_commit")
                        
                                if popup_commit._is_open:
                                    popup_commit.dismiss()
                        
                                def lancer_sauvegarde(dt2):
                                    print("[CLOCK COMMIT] Lancement executer_sauvegarde")
                                    executer_sauvegarde(msg)
                        
                                Clock.schedule_once(lancer_sauvegarde, 0.15)
                        
                            # Laisser iOS terminer la gestion du clavier virtuel
                            Clock.schedule_once(fermer_popup_et_sauvegarder, 0.15)
                            
                        btn_valider_commit.bind(on_release=valider_avec_commit)
                        popup_commit.open()
                    else:
                        executer_sauvegarde("Création de l'événement")

                btn_save._current_callback = save_evenement
                btn_save.bind(on_release=save_evenement)

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
