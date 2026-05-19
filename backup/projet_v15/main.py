# -*- coding: utf-8 -*-
from kivy.app import App
from kivy.uix.screenmanager import ScreenManager
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.widget import Widget
from kivy.uix.image import Image
from kivy.uix.button import ButtonBehavior, Button
from kivy.graphics import Color, Rectangle
from kivy.utils import get_color_from_hex
from kivy.uix.label import Label # Assure-être d'avoir cet import
from kivy.graphics import Rotate, PushMatrix, PopMatrix
from kivy.uix.screenmanager import Screen
from kivy.animation import Animation
from kivy.clock import Clock
from kivy.metrics import Metrics, dp
from kivy.utils import platform
from kivy.core.window import Window
from kivy.uix.scrollview import ScrollView

import threading
import ssl
import os, requests, yaml, hashlib
import json
import time
import urllib3

from kivy.utils import platform

from constants import LANGUAGES

# Ajoute ceci juste après :
if platform == 'android':
    from android.runnable import run_on_ui_thread
else:
    # Pour éviter une erreur sur PC
    def run_on_ui_thread(func):
        return func

generate_APK= True
#debug_APK= False

if generate_APK:
    Metrics.density = 2  # force un scaling type mobile

# --- AJOUT POUR FORCER LES CERTIFICATS ---
# --- CONFIGURATION SSL ET ENVIRONNEMENT ---
try:
    import certifi
    os.environ['SSL_CERT_FILE'] = certifi.where()
    ca_bundle = certifi.where()
except ImportError:
    ca_bundle = True # Fallback sur les certifs système

if not generate_APK:
    # Configuration PC (Taille et SSL)
    Window.size = (360, 640)
    try:
        # Tente de créer un contexte sécurisé par défaut
        ssl._create_default_https_context = ssl._create_default_context
    except Exception:
        # En cas d'échec critique sur de vieilles machines/OS
        ssl._create_default_https_context = ssl._create_unverified_context

# Tes imports de screens
from ui.screens.home import HomeScreen
from ui.screens.presentation import PresentationScreen
from ui.screens.soirees import SoireesScreen
from ui.screens.restauration import RestaurationScreen
from ui.screens.info import InfoScreen
from ui.screens.settings import SettingsScreen
from ui.screens.about import AboutScreen

from ui.screens.agenda import AgendaScreen
from ui.screens.resultat import ResultatScreen
from ui.screens.classement import ClassementScreen
from ui.screens.effectif import EffectifScreen
from ui.screens.inscription import InscriptionsScreen

def _(key):
    app = App.get_running_app()
    # Langue par défaut
    lang = 'Français'
    if app and hasattr(app, 'config'):
        try:
            lang = app.config.get('User', 'langue')
        except:
            pass
            
    # On récupère le dictionnaire de la langue choisie
    dict_lang = LANGUAGES.get(lang, LANGUAGES['Français'])
    # On renvoie la traduction, ou la clé brute si elle n'existe pas
    return dict_lang.get(key, key)

YELLOW = "#F7EC3F"
BLUE = "#1E3A8A"
config_file_Id_tournoi = "14V5epxHOUIqBDHPOQpTtAIaRRyKeFRLw"
config_file_Id_fcvv = "161ngxPQz66QumHjG_us6qqyAtA0GPX2x"

# On force la couleur de fond de la fenêtre pour éviter le noir
Window.clearcolor = get_color_from_hex(BLUE)

class IconButton(ButtonBehavior, Image):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        with self.canvas.before:
            PushMatrix()
            self.rot = Rotate(angle=0, origin=self.center)
        with self.canvas.after:
            PopMatrix()
        self.bind(pos=self._update_rot_origin, size=self._update_rot_origin)

    def _update_rot_origin(self, *args):
        self.rot.origin = self.center

class MenuRow(ButtonBehavior, BoxLayout):
    def __init__(self, icon_source, text, **kwargs):  
        # 1. AJUSTEMENT DES DIMENSIONS DE LA LIGNE
        h_val = dp(85) if generate_APK else 70  # On passe de 72 à 85dp
        p_val = dp(15) if generate_APK else 10
        super().__init__(
            orientation="horizontal",
            size_hint_y=None,
            height=h_val,
            padding=(dp(20), p_val, dp(10), p_val),
            spacing=dp(25), # Plus d'espace entre l'icône et le texte
            **kwargs
        )
        # 2. L'ICÔNE (Plus grande)
        icon_size = dp(45) if generate_APK else 40 # On passe de 36 à 45dp
        self.add_widget(Image(
            source=icon_source,
            size_hint=(None, None),
            size=(icon_size, icon_size),
            pos_hint={'center_y': 0.5}
        ))
        # 3. RÉCUPÉRATION DES PARAMÈTRES
        app = App.get_running_app()
        is_dark = False
        user_font_size = 20
        if app and hasattr(app, 'config') and app.config.has_section('User'):
            try:
                is_dark = app.config.getboolean('User', 'dark_mode')
                user_font_size = app.config.getint('User', 'font_size_factor')
            except Exception:
                pass
        self.text_color = get_color_from_hex("#F7EC3F") if is_dark else (0.2, 0.2, 0.5, 1)
        # 4. LE LABEL (Plus grand)
        # On ajoute un boost de +4sp au lieu de +2sp
        fs = f"{user_font_size + 4}sp" if generate_APK else f"{user_font_size}sp"
        self.label = Label(
            text=text,
            color=self.text_color,
            font_size=fs,
            bold=True, # Ajout du gras pour plus de visibilité
            halign='left',
            valign='middle',
            size_hint_x=1
        )
        self.label.bind(size=self._update_text_size)
        self.add_widget(self.label)

    def _update_text_size(self, instance, value):
        instance.text_size = (instance.width, None)
        
    def on_press(self):
        self.opacity = 0.6

    def on_release(self):
        self.opacity = 1
        
class SubMenuItem(ButtonBehavior, BoxLayout):
    def __init__(self, text, screen_name, **kwargs):
        super().__init__(orientation="horizontal", size_hint_y=None, height=dp(45), opacity=0, **kwargs)
        self.screen_name = screen_name
        self.padding = [dp(60), 0, 0, 0] 
        # --- RÉCUPÉRATION DE LA TAILLE DE POLICE ---
        app = App.get_running_app()
        user_font_size = 20  # Valeur par défaut
        if app and hasattr(app, 'config') and app.config.has_section('User'):
            try:
                user_font_size = app.config.getint('User', 'font_size_factor')
            except Exception:
                pass
        # Adaptation de la taille de police
        fs = f"{user_font_size - 2}sp" if generate_APK else f"{user_font_size - 4}sp"
        self.label = Label(
            text=text,
            color=(0.4, 0.4, 0.7, 1),
            font_size=fs,
            halign='left',
            valign='middle',
            size_hint_x=1
        )
        self.add_widget(self.label)
        self.bind(size=lambda inst, val: setattr(self.label, 'text_size', (inst.width, None)))

    def on_press(self):
        # Effet visuel au toucher
        self.opacity = 0.5

    def on_release(self):
        # On remet l'opacité à 1 (ou l'opacité cible de l'animation de l'accordéon)
        self.opacity = 1
        
        # ACTION : On change d'écran
        app = App.get_running_app()
        # app.root est l'instance de ton RootLayout
        if app.root:
            app.root.switch_screen(self.screen_name)

class AccordionGroup(BoxLayout):
    def __init__(self, title, icon, sub_items, **kwargs):
        super().__init__(orientation="vertical", size_hint_y=None, **kwargs)
        self.opened = False
        self.sub_widgets = []
        # 1. En-tête principal
        self.header = MenuRow(icon_source=icon, text=title)
        self.header.bind(on_release=self.toggle)
        self.add_widget(self.header)
        # 2. Création et ajout immédiat des sous-onglets (cachés)
        for text, screen in sub_items:
            w = SubMenuItem(text=text, screen_name=screen)
            # On force la taille à 0 et l'opacité à 0 dès le départ
            w.height = 0
            w.opacity = 0
            w.size_hint_y = None # Très important pour pouvoir animer la hauteur
            self.sub_widgets.append(w)
            self.add_widget(w)
        self.height = self.header.height

    def toggle(self, *args):
        self.opened = not self.opened
        # On calcule la hauteur cible pour chaque sous-élément et pour le groupe
        target_height_sub = dp(45) if self.opened else 0
        target_opacity = 1 if self.opened else 0
        target_height_group = self.header.height + (len(self.sub_widgets) * target_height_sub)
        # Animation fluide de la hauteur du groupe total
        Animation(height=target_height_group, d=0.25, t='out_quad').start(self)
        # Animation simultanée de chaque sous-élément
        for w in self.sub_widgets:
            anim = Animation(height=target_height_sub, opacity=target_opacity, d=0.25, t='out_quad')
            anim.start(w)

    def _remove_subs(self):
        if not self.opened:
            for w in self.sub_widgets:
                if w in self.children:
                    self.remove_widget(w)

class RootLayout(FloatLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if generate_APK:
            self.menu_width = int(Window.width * 0.75)
        else:
            self.menu_width = 260
        self.menu_open = False
        # --- 1. L'INTERFACE PRINCIPALE ---
        self.main_ui = BoxLayout(orientation="vertical", size_hint=(1, 1))
        # Top Bar
        if generate_APK:
            self.top_bar = BoxLayout(size_hint_y=None, height = int(Window.height * 0.08))
        else:
            self.top_bar = BoxLayout(size_hint_y=None, height = 50)
        with self.top_bar.canvas.before:
            Color(*get_color_from_hex(YELLOW))
            self.rect = Rectangle(pos=self.top_bar.pos, size=self.top_bar.size)
        self.top_bar.bind(pos=self.update_rects, size=self.update_rects)
        # Bouton Menu
        if generate_APK:
            self.menu_btn = IconButton(
                source="assets/icons/menu.png",
                size_hint=(None, None),
                size=(int(Window.height * 0.06), int(Window.height * 0.06)),
                pos_hint={'center_y': 0.5}
            )
        else:
            self.menu_btn = IconButton(
                source="assets/icons/menu.png",
                size_hint=(None, None),
                size=(40, 40),
                pos_hint={'center_y': 0.5}
            )
        self.menu_btn.bind(on_release=self.open_menu)
        self.top_bar.add_widget(self.menu_btn)
        self.top_bar.add_widget(Widget(size_hint_x=None, width=10))
        # Titre
        self.title_label = Label(
            text=_("home"),
            color=(0.1, 0.1, 0.4, 1),
            font_size='24sp',
            bold=True,
            size_hint_x=1,
            halign='left',
            valign='middle',
            text_size=(self.width, None),
            max_lines=2,
            shorten=False,
        )
        self.title_label.bind(size=lambda inst, val: setattr(inst, 'text_size', (inst.width, None)))
        self.top_bar.add_widget(self.title_label)
        self.top_bar.add_widget(Widget()) 
        # Label MAJ
        self.maj_label = Label(
            text="", 
            color=(0.1, 0.1, 0.4, 1),
            font_size='11sp',
            size_hint_x=None,
            width=0,            # Force la largeur à 0
            size_hint_y=None,   # Ajouté : ne prend pas de place verticale
            height=0,           # Ajouté : force la hauteur à 0
            halign='center',
            valign='middle',
            markup=True,
            opacity=0,          # Invisible
            disabled=True       # Désactivé
        )
        # Dans le __init__, modifiez le bind du maj_label ainsi :
        self.maj_label.bind(size=lambda inst, val: setattr(inst, 'text_size', (val[0], val[1])))
        self.top_bar.add_widget(self.maj_label)
        # Bouton Reload
        if generate_APK:
            reload_size = int(Window.height * 0.06)
        else:
            reload_size = 40
        self.btn_reload = IconButton(
            source="assets/icons/reload.png",
            size_hint=(None, None),
            size=(reload_size, reload_size),
            pos_hint={'center_y': 0.5},
            opacity=0,
            disabled=True
        )
        self.btn_reload.bind(on_release=self.trigger_soirees_reload)
        self.top_bar.add_widget(self.btn_reload)
        self.top_bar.add_widget(Widget(size_hint_x=None, width=10))
        self.main_ui.add_widget(self.top_bar)
        # Screen Manager
        self.sm = ScreenManager()
        self.sm.add_widget(HomeScreen(name="home"))
        self.sm.add_widget(AgendaScreen(name="agenda"))
        self.sm.add_widget(ResultatScreen(name="resultats"))
        self.sm.add_widget(ClassementScreen(name="classements"))
        self.sm.add_widget(EffectifScreen(name="effectifs"))
        self.sm.add_widget(PresentationScreen(name="presentation"))
        self.sm.add_widget(InscriptionsScreen(name="inscriptions"))
        self.sm.add_widget(SoireesScreen(name="soirees"))
        self.sm.add_widget(RestaurationScreen(name="restauration"))
        self.sm.add_widget(InfoScreen(name="info"))
        self.sm.add_widget(SettingsScreen(name="settings"))
        self.sm.add_widget(AboutScreen(name="about"))
        self.main_ui.add_widget(self.sm)
        self.add_widget(self.main_ui)
        # Overlay
        self.overlay = Widget(size_hint=(None, None), size=(0, 0), opacity=0)
        with self.overlay.canvas.before:
            self.overlay_color = Color(0, 0, 0, 0.4)
            self.overlay_rect = Rectangle(pos=self.pos, size=self.size)
        self.add_widget(self.overlay)
        # --- MENU SCROLLABLE ---
        self.menu_scroll = ScrollView(
            size_hint=(None, 1),
            width=self.menu_width,
            x=-self.menu_width,
            do_scroll_x=False,
            bar_width=dp(4)
        )
        self.menu_panel = BoxLayout(
            orientation="vertical", 
            size_hint_y=None,
            width=self.menu_width
        )
        # On lie la hauteur au contenu MAIS avec un minimum égal à la hauteur du ScrollView
        self.menu_panel.bind(minimum_height=self._update_panel_height)
        self.menu_scroll.bind(height=self._update_panel_height) # Important pour les changements d'orientation
        self.menu_scroll.add_widget(self.menu_panel)
        self.add_widget(self.menu_scroll)
        self.menu_built = False
        self.build_menu()
        Clock.schedule_once(lambda dt: self.switch_screen("home"))
    
    def _update_panel_height(self, *args):
        # La hauteur est le maximum entre le contenu et la taille de l'écran
        self.menu_panel.height = max(self.menu_scroll.height, self.menu_panel.minimum_height)

    def update_rects(self, instance, value):
        if instance == self.top_bar:
            self.rect.pos = instance.pos
            self.rect.size = instance.size
        elif instance == self.overlay:
            self.overlay_rect.pos = instance.pos
            self.overlay_rect.size = instance.size
            
    def trigger_soirees_reload(self, instance):
        soirees_screen = self.sm.get_screen("soirees")
        soirees_screen.manual_reload(instance)

    def switch_screen(self, screen_name):
        self.close_menu()
        if self.sm.has_screen(screen_name):
            self.sm.current = screen_name
            self.title_label.text = _(screen_name)
        if screen_name == "soirees":
            # --- RÉAPPARITION DANS SOIRÉES ---
            self.btn_reload.opacity = 1
            self.btn_reload.disabled = False
            self.maj_label.opacity = 1
            self.maj_label.disabled = False
            self.maj_label.width = dp(80)   # On lui redonne sa largeur
            self.maj_label.size_hint_y = 1   # On lui redonne sa place verticale
            # On met un texte par défaut pour qu'il ne soit pas vide au premier clic
            self.maj_label.text = "[size=11sp]MAJ[/size]\n[b]--h--[/b]"
        else:
            # --- DISPARITION TOTALE AILLEURS ---
            self.btn_reload.opacity = 0
            self.btn_reload.disabled = True
            
            self.maj_label.opacity = 0
            self.maj_label.disabled = True
            self.maj_label.width = 0
            self.maj_label.size_hint_y = None
            self.maj_label.height = 0
            self.maj_label.text = ""

    def build_menu(self):
        self.menu_panel.clear_widgets()
        app = App.get_running_app()
        
        is_dark = False
        if app and hasattr(app, 'config'):
            try: is_dark = app.config.getboolean('User', 'dark_mode')
            except: pass
        bg_color = (0.15, 0.15, 0.2, 1) if is_dark else (1, 1, 1, 1)
        self.menu_panel.canvas.before.clear()
        with self.menu_panel.canvas.before:
            Color(*bg_color)
            self.menu_bg = Rectangle(pos=self.menu_panel.pos, size=self.menu_panel.size)
        self.menu_panel.bind(pos=self._update_menu_rect, size=self._update_menu_rect)
        header_img = Image(
            source="assets/menu_top.png",
            size_hint=(1, None),      # Prend toute la largeur, hauteur manuelle
            allow_stretch=True,
            keep_ratio=True
        )
        # On lie la hauteur de l'image à sa largeur réelle pour garder le ratio 1.5
        header_img.bind(width=lambda inst, val: setattr(inst, 'height', val * 0.66))
        self.menu_panel.add_widget(header_img)
        # Accueil
        row_home = MenuRow(icon_source="assets/icons/home.png", text="Accueil")
        row_home.bind(on_release=lambda x: self.switch_screen("home"))
        self.menu_panel.add_widget(row_home)
        # Groupes
        self.menu_panel.add_widget(AccordionGroup(
            title="Equipes", 
            icon="assets/icons/fcvv.png", 
            sub_items=[
                ("Agenda", "agenda"), 
                ("Résultats", "resultats"), 
                ("Classements", "classements"), 
                ("Effectifs", "effectifs")
            ]
        ))
        self.menu_panel.add_widget(AccordionGroup(
            title="Tournoi Vercel", 
            icon="assets/icons/tournoi.png", 
            sub_items=[
                ("Présentation", "presentation"), 
                ("Inscriptions", "inscriptions"), # <-- Ajouté ici
                ("Soirées", "soirees"), 
                ("Restauration", "restauration")
            ]
        ))
        # Autres
        others = [
            ("Info/Contact", "info", "assets/icons/contact.png"),
            ("Paramètres", "settings", "assets/icons/settings.png"),
            ("À Propos", "about", "assets/icons/about.png")
        ]
        for text, screen, icon in others:
            row = MenuRow(icon_source=icon, text=text)
            row.bind(on_release=lambda x, s=screen: self.switch_screen(s))
            self.menu_panel.add_widget(row)
        self.menu_panel.add_widget(Widget(size_hint_y=1)) 
        self.menu_built = True

    def _update_menu_rect(self, instance, value):
        if hasattr(self, 'menu_bg'):
            self.menu_bg.pos = instance.pos
            self.menu_bg.size = instance.size

    def open_menu(self, *args):
        # On ne reconstruit le menu que s'il n'existe pas encore
        # Cela permet de garder l'état (ouvert/fermé) des accordéons
        if not self.menu_built:
            self.build_menu()
        self.menu_open = True
        self.overlay.size_hint = (1, 1)
        self.overlay.pos = self.pos
        self.overlay.size = self.size
        Animation(opacity=1, d=0.2).start(self.overlay)
        Animation(x=0, d=0.25, t='out_quad').start(self.menu_scroll)

    def close_menu(self, *args):
        self.menu_open = False
        Animation(opacity=0, d=0.2).start(self.overlay)
        # On anime le SCROLLVIEW
        anim = Animation(x=-self.menu_width, d=0.25, t='out_quad')
        anim.bind(on_complete=self._disable_overlay)
        anim.start(self.menu_scroll)

    def _disable_overlay(self, *args):
        if not self.menu_open:
            self.overlay.size_hint = (None, None)
            self.overlay.size = (0, 0)

    def on_touch_down(self, touch):
        # On vérifie la collision avec le ScrollView
        if self.menu_open and not self.menu_scroll.collide_point(*touch.pos):
            self.close_menu()
            return True
        return super().on_touch_down(touch)

#===============================================================================
def customize_android_bars():
    if platform == 'android':
        @run_on_ui_thread
        def _set_bars_colors():
            try:
                from jnius import autoclass
                PythonActivity = autoclass('org.kivy.android.PythonActivity')
                Color = autoclass('android.graphics.Color')
                View = autoclass('android.view.View')
                LayoutParams = autoclass('android.view.WindowManager$LayoutParams')
                activity = PythonActivity.mActivity
                window = activity.getWindow()
                # Forcer l'affichage des barres même si Kivy essaie de les cacher
                window.addFlags(LayoutParams.FLAG_DRAWS_SYSTEM_BAR_BACKGROUNDS)
                window.clearFlags(LayoutParams.FLAG_TRANSLUCENT_STATUS)
                window.clearFlags(LayoutParams.FLAG_TRANSLUCENT_NAVIGATION)
                # Couleurs
                window.setStatusBarColor(Color.parseColor("#F7EC3F"))      # Jaune
                window.setNavigationBarColor(Color.parseColor("#1E3A8A"))  # Bleu
                # UI Visibility : On force la visibilité pour éviter le retard d'affichage
                decorView = window.getDecorView()
                # On force les icônes sombres sur la barre de statut (fond jaune)
                vis = View.SYSTEM_UI_FLAG_LIGHT_STATUS_BAR
                # On s'assure que le système ne cache pas les barres
                vis |= View.SYSTEM_UI_FLAG_LAYOUT_STABLE
                decorView.setSystemUiVisibility(vis)
            except Exception as e:
                print(f"[ANDROID] Erreur bars: {e}")
        _set_bars_colors()
#===============================================================================

class MyApp(App):
    # Ces noms DOIVENT correspondre exactement au buildozer.spec
    name = "fcvv" 
    org = "org.fcvv"
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._ = _
        self.generate_APK = (platform == 'android')
        # FORCE le chargement de la config immédiatement pour que _() fonctionne au build
        self.use_kivy_settings = False
        self.config = self.load_config() 
        self.app_config = {}
        self._app_password_hash = ""
        self.debug_mode = False
        
    def get_application_config(self):
        """Force l'emplacement du fichier .ini dans le dossier de données utilisateur"""
        # self.user_data_dir est déjà géré par Kivy/Buildozer
        return os.path.join(self.user_data_dir, 'fcvv.ini')

    def build(self):
        # Assure-toi que RootLayout est bien défini ou importé dans ton fichier
        return RootLayout()

    def on_start(self):
        # 1. Préparation du dossier de données
        if not os.path.exists(self.user_data_dir):
            try:
                os.makedirs(self.user_data_dir, exist_ok=True)
            except Exception as e:
                print(f"Erreur dossier: {e}")
        # 2. UI et Evénements
        Clock.schedule_once(lambda dt: customize_android_bars(), 0)
        Window.bind(on_keyboard=self.on_back_button)
        # 3. Gestion Android 13+
        if platform == 'android':
            # Délai de 1s pour laisser l'app s'initialiser avant la popup de permission
            Clock.schedule_once(lambda dt: self.check_android_permissions(), 1)
        else:
            self.start_network_tasks()

    def check_android_permissions(self):
        if platform != 'android':
            return
        try:
            from android.permissions import request_permissions, Permission
            # On ne garde que les permissions de base si nécessaire 
            # (ici on peut même laisser la liste vide ou retirer l'appel)
            perms = [] 
            def callback(permissions, results):
                # On lance les tâches réseau, mais on ne lance plus le service
                self.start_network_tasks()

            request_permissions(perms, callback)
        except Exception as e:
            print(f"[PERMISSIONS ERROR] {e}")
            self.start_network_tasks()

    def start_background_service(self):
        # Système de notification désactivé
        pass

    def get_file_hash(self, filepath):
        """Calcule le hash SHA256 d'un fichier pour comparaison"""
        if not os.path.exists(filepath):
            return None
        hasher = hashlib.sha256()
        with open(filepath, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hasher.update(chunk)
        return hasher.hexdigest()

    def download_news_images(self):
        """Télécharge les images avec gestion du dictionnaire imbriqué et fallback SSL"""
        # On cherche partout où il pourrait y avoir des news
        news_list = []
        for key in ["fcvv", "tournoi"]:
            found = self.app_config.get(key, {}).get("appli", {}).get("news", [])
            if found:
                news_list.extend(found)
        if not news_list:
            return
        for item in news_list:
            image_url = item.get("image")
            if not image_url or not image_url.startswith("http"):
                continue
            img_hash = hashlib.md5(image_url.encode()).hexdigest()
            filename = f"img_{img_hash}.jpg"
            local_path = os.path.join(self.user_data_dir, filename)
            if not os.path.exists(local_path):
                try:
                    print(f"[IMAGES] Téléchargement : {filename}")
                    try:
                        r = requests.get(image_url, timeout=10, verify=ca_bundle)
                    except:
                        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
                        r = requests.get(image_url, timeout=10, verify=False)
                    if r.status_code == 200:
                        with open(local_path, "wb") as f:
                            f.write(r.content)
                        item["image"] = local_path
                except Exception as e:
                    print(f"[IMAGES ERROR] {e}")
            else:
                # IMPORTANT : On met à jour le chemin dans le dictionnaire 
                # même si le fichier existe déjà, pour que l'UI l'utilise
                item["image"] = local_path
                
    def cleanup_unused_images(self):
        print("[CLEANUP] Vérification des images inutilisées...")
        try:
            needed_images = set()
            
            # 1. Lister toutes les images nécessaires selon la config actuelle
            for key in ["fcvv", "tournoi"]:
                section = self.app_config.get(key, {})
                news_list = section.get("appli", {}).get("news", [])
                
                for item in news_list:
                    img_val = item.get("image")
                    if img_val:
                        # CAS 1 : C'est encore une URL (pas encore téléchargée ou pas encore mutée)
                        if img_val.startswith("http"):
                            img_hash = hashlib.md5(img_val.encode()).hexdigest()
                            needed_images.add(f"img_{img_hash}.jpg")
                        
                        # CAS 2 : C'est déjà un chemin local (ex: C:\Users\...\img_abc123.jpg)
                        elif "img_" in img_val:
                            # On extrait juste le nom du fichier du chemin complet
                            filename = os.path.basename(img_val)
                            needed_images.add(filename)
    
            # --- SÉCURITÉ CRITIQUE ---
            # Si on ne trouve aucune image nécessaire, on arrête tout pour éviter de vider le dossier
            if not needed_images:
                print("[CLEANUP] Alerte : Aucune image trouvée dans la config. Annulation par sécurité.")
                return
    
            data_dir = self.user_data_dir
            if not os.path.exists(data_dir):
                return
    
            # 2. Parcourir les fichiers du dossier pour supprimer les inutiles
            files_in_dir = os.listdir(data_dir)
            deleted_count = 0
            
            for filename in files_in_dir:
                # On ne touche qu'aux fichiers images de l'app (commençant par img_)
                if filename.startswith("img_") and filename.endswith(".jpg"):
                    if filename not in needed_images:
                        file_path = os.path.join(data_dir, filename)
                        try:
                            # Petite pause pour laisser le système relâcher le fichier si besoin
                            os.remove(file_path)
                            print(f"[CLEANUP] Supprimé : {filename}")
                            deleted_count += 1
                        except Exception as e:
                            # Arrive si l'image est actuellement affichée à l'écran (Kivy la verrouille)
                            print(f"[CLEANUP SKIP] Impossible de supprimer {filename} (en cours d'utilisation)")
            
            print(f"[CLEANUP] Terminé. {deleted_count} image(s) supprimée(s).")
    
        except Exception as e:
            print(f"[CLEANUP ERROR] {e}")
                
    def start_network_tasks(self):
        """Déclenche les chargements sans bloquer l'UI"""
        threading.Thread(target=self.safe_load_config, daemon=True).start()

    def load_remote_config(self):
        data_dir = self.user_data_dir
        configs_to_process = [
            ("config_tournoi.yaml", config_file_Id_tournoi, "tournoi"),
            ("config_fcvv.yaml", config_file_Id_fcvv, "fcvv")
        ]
        
        # --- DETECTION PREMIER DEMARRAGE ---
        # On vérifie si AU MOINS UN fichier de config existe déjà
        files_exist = [os.path.exists(os.path.join(data_dir, f)) for f, _, _ in configs_to_process]
        is_first_run = not any(files_exist) 
        if is_first_run:
            print("[CONFIG] Premier démarrage détecté : le nettoyage sera désactivé pour cette session.")
        # ----------------------------------

        if not hasattr(self, 'app_config'):
            self.app_config = {"tournoi": {}, "fcvv": {}}

        # 1. Chargement du cache local (inchangé)
        cache_loaded = False
        for filename, _, key in configs_to_process:
            cache_path = os.path.join(data_dir, filename)
            if os.path.exists(cache_path):
                try:
                    with open(cache_path, "r", encoding='utf-8') as f:
                        self.app_config[key] = yaml.safe_load(f) or {}
                        cache_loaded = True
                except Exception as e: 
                    print(f"Erreur lecture cache {filename}: {e}")

        if cache_loaded:
            self.download_news_images()
            Clock.schedule_once(self._update_home_screen, 0)

        # 2. Vérification des mises à jour sur Drive
        config_changed = False
        for filename, fid, key in configs_to_process:
            cache_path = os.path.join(data_dir, filename)
            download_url = f"https://drive.google.com/uc?export=download&id={fid}"
            try:
                r = None
                try:
                    r = requests.get(download_url, timeout=12, verify=ca_bundle)
                except:
                    urllib3.disable_warnings()
                    r = requests.get(download_url, timeout=12, verify=False)

                if r and r.status_code == 200:
                    new_content = r.content
                    new_hash = hashlib.sha256(new_content).hexdigest()
                    old_hash = self.get_file_hash(cache_path) if os.path.exists(cache_path) else "MISSING"

                    if new_hash != old_hash:
                        with open(cache_path, "wb") as f:
                            f.write(new_content)
                        self.app_config[key] = yaml.safe_load(new_content.decode('utf-8')) or {}
                        config_changed = True
                        print(f"[CONFIG] {filename} mis à jour ou restauré.")
            except Exception as e:
                print(f"[CONFIG ERROR] {filename}: {e}")

        # 3. Finalisation
        if config_changed:
            self.download_news_images()
            
            # --- LOGIQUE DE NETTOYAGE SECURISÉE ---
            # On ne nettoie QUE si ce n'est pas le premier démarrage
            if not is_first_run:
                self.cleanup_unused_images()
            else:
                print("[CLEANUP] Saut du nettoyage (Installation initiale).")
            # --------------------------------------

            if hasattr(self, 'preload_latest_tournament'):
                threading.Thread(target=self.preload_latest_tournament, daemon=True).start()

        Clock.schedule_once(self._update_home_screen, 0.2)

    def preload_latest_tournament(self):
        """
        Télécharge le tournoi par défaut en utilisant la triple sécurité SSL.
        """
        tournois = self.app_config.get("tournois", [])
        if not tournois:
            return
        try:
            # 1. Filtrage numérique des années
            valid_years = []
            for t in tournois:
                y = str(t.get("annee", "")).strip()
                if y.isdigit():
                    valid_years.append(int(y))
            if not valid_years:
                print("[PRELOAD] Aucune année numérique trouvée.")
                return
            # Trouver l'année la plus élevée (ex: 2026)
            latest_year_str = str(max(valid_years))
            # 2. Identifier le premier NOM alphabétique pour cette année
            noms_annee = sorted(list(set([
                str(t.get("nom")).strip() for t in tournois 
                if str(t.get("annee")).strip() == latest_year_str
            ])))
            if not noms_annee:
                return
            nom_cible = noms_annee[0]
            # 3. Recherche de l'entrée correspondante (Priorité au type "save")
            target = next((t for t in tournois if str(t.get("nom")).strip() == nom_cible 
                           and str(t.get("annee")).strip() == latest_year_str 
                           and t.get("type") == "save"), None)
            if not target:
                target = next((t for t in tournois if str(t.get("nom")).strip() == nom_cible 
                               and str(t.get("annee")).strip() == latest_year_str), None)
            # --- VÉRIFICATION DE LA VARIABLE TARGET ---
            if target:
                url_raw = target.get("url", "")
                # Extraction de l'ID Google Drive
                if "id=" in url_raw:
                    file_id = url_raw.split("id=")[-1].split("&")[0]
                else:
                    print("[PRELOAD] URL invalide (pas d'ID trouvé)")
                    return
                ext = "json" if target.get("type") == "save" else "yaml"
                filename = f"tournoi_{file_id}.{ext}"
                local_path = os.path.join(self.user_data_dir, filename)
                # 4. Téléchargement avec Fallback SSL
                if not os.path.exists(local_path):
                    print(f"[PRELOAD] Téléchargement de {nom_cible}...")
                    download_url = f"https://drive.google.com/uc?export=download&id={file_id}"
                    try:
                        # Tentative A : Avec Certifi
                        r = requests.get(download_url, timeout=15, verify=ca_bundle)
                    except (requests.exceptions.SSLError, requests.exceptions.ConnectionError):
                        # Tentative B : Fallback sans vérification
                        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
                        r = requests.get(download_url, timeout=15, verify=False)
                    if r.status_code == 200:
                        with open(local_path, "wb") as f:
                            f.write(r.content)
                        print(f"[PRELOAD] Succès : {filename}")
                else:
                    print(f"[PRELOAD] Cache OK : {nom_cible}")
        except Exception as e:
            # Cette fois, 'target' est défini à l'intérieur du bloc, l'erreur disparaîtra
            print(f"[PRELOAD ERROR] : {e}")
            
    def safe_load_config(self):
        try:
            self.load_remote_config()
        except Exception as e:
            print(f"[FATAL CONFIG ERROR] {e}")

    def _update_home_screen(self, dt):
        if self.root and hasattr(self.root, 'sm'):
            if self.root.sm.has_screen('home'):
                home = self.root.sm.get_screen('home')
                if hasattr(home, 'update_ui_from_config'):
                    home.update_ui_from_config()

    def on_back_button(self, window, key, *args):
        if key == 27: # Touche Retour
            if self.root and self.root.menu_open:
                self.root.close_menu()
                return True
            if self.root and self.root.sm.current != 'home':
                self.root.switch_screen('home')
                return True
        return False

    def update_service_monitoring(self, url, nom):
        """Système de monitoring désactivé"""
        pass
    
    def build_config(self, config):
        config.setdefaults('User', {
            'dark_mode': '0',
            'font_size_factor': '24',
            'langue': 'Français',
            'refresh_interval': '5'
            # 'notifications': '1'  <-- À supprimer ou commenter
        })

    def refresh_ui_theme(self):
        if self.root:
            self.root.build_menu()
            current_screen = self.root.sm.current
            self.root.title_label.text = _(current_screen)

if __name__ == "__main__":
    MyApp().run()
