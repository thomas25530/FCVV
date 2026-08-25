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
from kivy.animation import Animation
from kivy.clock import Clock
from kivy.metrics import Metrics, dp
from kivy.utils import platform
from kivy.core.window import Window
from kivy.uix.scrollview import ScrollView

from kivy.clock import mainthread
from kivy.uix.label import Label
from kivy.uix.popup import Popup

import threading
import ssl
import os, hashlib
#import urllib3
from datetime import datetime, timedelta

from constants import LANGUAGES

from kivy.utils import platform

# Bloc conditionnel pour éviter l'erreur "Unable to find JAVA_HOME" sur Windows
if platform == 'android':
    from jnius import autoclass, PythonJavaClass, java_method

    class OnCompleteListener(PythonJavaClass):
        __javainterfaces__ = ['com/google/android/gms/tasks/OnCompleteListener']
        
        def __init__(self, callback=None):
            super().__init__()
            self.callback = callback

        @java_method('(Lcom/google/android/gms/tasks/Task;)V')
        def onComplete(self, task):
            if task.isSuccessful():
                token = task.getResult()
                print(f"[FCM SUCCESS] Token recupere : {token}")
            else:
                print("[FCM ERROR] Echec de la recuperation du token")
else:
    # Simule la classe pour ne pas casser le code sur Windows
    class OnCompleteListener:
        def __init__(self, callback=None):
            pass

# Ajoute ceci juste après :
if platform == 'android':
    from android.runnable import run_on_ui_thread
else:
    # Pour éviter une erreur sur PC
    def run_on_ui_thread(func):
        return func

is_mobile = (platform == 'android' or platform == 'ios')

if is_mobile:
    Metrics.density = 2  # force un scaling type mobile

# --- AJOUT POUR FORCER LES CERTIFICATS ---
# --- CONFIGURATION SSL ET ENVIRONNEMENT ---
try:
    import certifi
    os.environ['SSL_CERT_FILE'] = certifi.where()
    ca_bundle = certifi.where()
except ImportError:
    ca_bundle = True # Fallback sur les certifs système

if not is_mobile:
    # Configuration PC (Taille et SSL)
    Window.size = (360, 640)
    try:
        # Tente de créer un contexte sécurisé par défaut
        ssl._create_default_https_context = ssl._create_default_context
    except Exception:
        # En cas d'échec critique sur de vieilles machines/OS
        ssl._create_default_https_context = ssl._create_unverified_context


def _(key):
    app = App.get_running_app()
    # Langue par défaut
    lang = 'Francais'
    if app and hasattr(app, 'config'):
        try:
            lang = app.config.get('User', 'langue')
        except:
            pass
            
    # On récupère le dictionnaire de la langue choisie
    dict_lang = LANGUAGES.get(lang, LANGUAGES['Francais'])
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
        h_val = dp(85) if is_mobile else 70  # On passe de 72 à 85dp
        p_val = dp(15) if is_mobile else 10
        super().__init__(
            orientation="horizontal",
            size_hint_y=None,
            height=h_val,
            padding=(dp(20), p_val, dp(10), p_val),
            spacing=dp(25), # Plus d'espace entre l'icône et le texte
            **kwargs
        )
        # 2. L'ICÔNE (Plus grande)
        icon_size = dp(45) if is_mobile else 40 # On passe de 36 à 45dp
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
        fs = f"{user_font_size + 4}sp" if is_mobile else f"{user_font_size}sp"
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
        fs = f"{user_font_size - 2}sp" if is_mobile else f"{user_font_size - 4}sp"
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

class MenuSeparator(Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.size_hint_y = None
        self.height = dp(2)
        with self.canvas.before:
            self.color = Color(0.8, 0.8, 0.8, 1)
            self.rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._update_rect, size=self._update_rect)

    def _update_rect(self, *args):
        self.rect.pos = self.pos
        self.rect.size = self.size
        
class RootLayout(FloatLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if is_mobile:
            self.menu_width = int(Window.width * 0.75)
        else:
            self.menu_width = 260
        self.menu_open = False
        # --- 1. L'INTERFACE PRINCIPALE ---
        self.main_ui = BoxLayout(orientation="vertical", size_hint=(1, 1))
        # Top Bar
        if is_mobile:
            self.top_bar = BoxLayout(size_hint_y=None, height = int(Window.height * 0.08))
        else:
            self.top_bar = BoxLayout(size_hint_y=None, height = 50)
        with self.top_bar.canvas.before:
            Color(*get_color_from_hex(YELLOW))
            self.rect = Rectangle(pos=self.top_bar.pos, size=self.top_bar.size)
        self.top_bar.bind(pos=self.update_rects, size=self.update_rects)
        # Bouton Menu
        if is_mobile:
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
        if is_mobile:
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
        # Dictionnaire pour le Lazy Loading
        self.screen_map = {
            "home": ("ui.screens.home", "HomeScreen"),
            "agenda": ("ui.screens.agenda", "AgendaScreen"),
            "resultats": ("ui.screens.resultat", "ResultatScreen"),
            "classements": ("ui.screens.classement", "ClassementScreen"),
            "effectifs": ("ui.screens.effectif", "EffectifScreen"),
            "organigramme": ("ui.screens.organigramme", "OrganigrammeScreen"),
            "divers": ("ui.screens.divers", "DiversScreen"),
            "presentation": ("ui.screens.presentation", "PresentationScreen"),
            "inscriptions": ("ui.screens.inscription", "InscriptionsScreen"),
            "soirees": ("ui.screens.soirees", "SoireesScreen"),
            "restauration": ("ui.screens.restauration", "RestaurationScreen"),
            "boutique": ("ui.screens.boutique", "BoutiqueScreen"),
            "partenaires": ("ui.screens.partenaires", "PartenairesScreen"),
            "info": ("ui.screens.info", "InfoScreen"),
            "settings": ("ui.screens.settings", "SettingsScreen"),
            "about": ("ui.screens.about", "AboutScreen"),
            "login_vestiaire": ("ui.screens.login", "LoginScreen"),
            "vestiaire": ("ui.screens.vestiaire", "VestiaireScreen"),
        }
        self.sm = ScreenManager()
        Clock.schedule_once(
            lambda dt: self.load_initial_screen(),
            0
        )
        #from ui.screens.home import HomeScreen
        #self.sm.add_widget(HomeScreen(name="home"))
        
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
            bar_width=0
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
        #self.build_menu()
        #Clock.schedule_once(lambda dt: self.switch_screen("home"))
        
    def load_initial_screen(self):
        from ui.screens.home import HomeScreen
    
        self.sm.add_widget(
            HomeScreen(name="home")
        )
    
        self.sm.current = "home"

    def afficher_popup_flottante(self, titre, message):
        """
        Affiche la popup par-dessus l'interface actuelle de manière thread-safe.
        """
        from core.NotificationManager import afficher_popup_notification
        # S'assure que l'affichage se fait bien sur le thread principal de Kivy
        Clock.schedule_once(lambda dt: afficher_popup_notification(titre, message), 0)
    
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
        
        # 1. Logique de redirection vers le login si vestiaire vide
        if screen_name == "vestiaire":
            app = App.get_running_app()
            if not app.authorized_vestiaires:
                screen_name = "login_vestiaire"
        
        # 2. Chargement dynamique si l'écran n'existe pas
        if not self.sm.has_screen(screen_name):
            if screen_name in self.screen_map:
                try:
                    module_path, class_name = self.screen_map[screen_name]
                    # Import dynamique
                    module = __import__(module_path, fromlist=[class_name])
                    screen_class = getattr(module, class_name)
                    # Ajout au ScreenManager
                    self.sm.add_widget(screen_class(name=screen_name))
                except Exception as e:
                    print(f"[ERROR] Impossible de charger l'ecran {screen_name}: {e}")
                    return
            else:
                print(f"[ERROR] L'ecran {screen_name} n'est pas dans screen_map.")
                return
        
        # 3. Maintenant on est sûr que l'écran existe
        self.sm.current = screen_name
        self.title_label.text = _(screen_name)
        
        # Gestion visuelle spécifique
        if screen_name == "soirees":
            self.btn_reload.opacity = 1
            self.btn_reload.disabled = False
            self.maj_label.opacity = 1
            self.maj_label.disabled = False
            self.maj_label.width = dp(80)
            self.maj_label.size_hint_y = 1
            self.maj_label.text = "[size=11sp]MAJ[/size]\n[b]--h--[/b]"
        else:
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
            fit_mode="contain"        # Remplace avantageusement allow_stretch et keep_ratio
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
            title="Club", 
            icon="assets/icons/fcvv.png", 
            sub_items=[
                ("Agenda", "agenda"), 
                ("Résultats", "resultats"), 
                ("Classements", "classements"), 
                ("Effectifs", "effectifs"),
                ("Organigramme", "organigramme"),
                ("Divers", "divers")
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
            ("Boutique", "boutique", "assets/icons/boutique.png"),
            ("Info/Contact", "info", "assets/icons/contact.png"),
            ("Partenaires", "partenaires", "assets/icons/partenaires.png"),
            ("Paramètres", "settings", "assets/icons/settings.png"),
            ("À Propos", "about", "assets/icons/about.png")
        ]
        for text, screen, icon in others:
            row = MenuRow(icon_source=icon, text=text)
            row.bind(on_release=lambda x, s=screen: self.switch_screen(s))
            self.menu_panel.add_widget(row)
            
        # --- NOUVEAU : Séparateur ---
        self.menu_panel.add_widget(MenuSeparator())
        # ----------------------------

        # Mon Vestiaire (accès direct, séparé)
        row_vestiaire = MenuRow(icon_source="assets/icons/vestiaire.png", text="Mon Vestiaire")
        row_vestiaire.bind(on_release=lambda x: self.switch_screen("vestiaire"))
        self.menu_panel.add_widget(row_vestiaire)
        
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
            Clock.schedule_once(lambda dt: self.build_menu(), 0)
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
    # Sécurité absolue pour iOS et PC
    if platform != 'android':
        return

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
            window.addFlags(LayoutParams.FLAG_DRAWS_SYSTEM_BAR_BACKGROUNDS)
            window.clearFlags(LayoutParams.FLAG_TRANSLUCENT_STATUS)
            window.clearFlags(LayoutParams.FLAG_TRANSLUCENT_NAVIGATION)
            window.setStatusBarColor(Color.parseColor("#F7EC3F"))      # Jaune
            window.setNavigationBarColor(Color.parseColor("#1E3A8A"))  # Bleu
            decorView = window.getDecorView()
            vis = View.SYSTEM_UI_FLAG_LIGHT_STATUS_BAR
            vis |= View.SYSTEM_UI_FLAG_LAYOUT_STABLE
            decorView.setSystemUiVisibility(vis)
        except Exception as e:
            print(f"[ANDROID] Erreur bars: {e}")
            
    _set_bars_colors()
#===============================================================================


class MyApp(App):
    name = "fcvv" 
    org = "org.fcvv"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._ = _
        self.use_kivy_settings = False
        self.config = self.load_config() 
        self.app_config = {}
        self.is_fetching_remote = False
        self.images_currently_downloading = set()
        self.last_config_hash = ""
        self.authorized_vestiaires = []
        self.cache_images_dir = os.path.join(self.user_data_dir, "cache_images")
        
        self.notifier = None

    def get_application_config(self):
        return os.path.join(self.user_data_dir, 'fcvv.ini')

    def build(self):
        return RootLayout()
    
    def clean_key(self, text):
        # Enlève les accents et remplace espaces par underscores
        import unicodedata
        return unicodedata.normalize('NFKD', text).encode('ASCII', 'ignore').decode('ASCII').replace(' ', '_')
    
    def add_authorized_vestiaire(self, category_name, role, password_hash, save=True):
        """
        Ajoute une catégorie et stocke le rôle + hash pour la persistance.
        :param save: Booléen pour autoriser ou non l'écriture immédiate sur le disque.
        """
        # 1. Assurer l'existence des sections nécessaires (sécurité)
        if not self.config.has_section('Roles'):
            self.config.add_section('Roles')
        if not self.config.has_section('User'):
            self.config.add_section('User')
        
        # 2. Mise à jour de la liste en mémoire (évite les doublons)
        if category_name not in self.authorized_vestiaires:
            self.authorized_vestiaires.append(category_name)
        
        # 3. Sauvegarde sécurisée (Rôle + Hash)
        self.set_vestiaire_role(category_name, role)
        
        # Puis dans add_authorized_vestiaire :
        key = self.clean_key(category_name)
        self.config.set('Roles', f'{key}_hash', password_hash)
        
        # 4. Mise à jour des paramètres globaux
        self.config.set('User', 'authorized_list', ','.join(self.authorized_vestiaires))
        self.config.set('User', 'vestiaire_auth', '1')
        
        # 5. Persistance sur disque conditionnelle
        if save:
            try:
                self.config.write()
                print(f"[AUTH] {category_name} ajoutee et sauvegardee avec role {role}")
            except Exception as e:
                print(f"[ERROR] Impossible d'ecrire la configuration : {e}")
        else:
            print(f"[AUTH] {category_name} ajoutee en memoire (sauvegarde differee)")
    
    def is_access_still_valid(self, cat):
        # Récupère le hash stocké localement
        stored_hash = self.config.get('Roles', f'{cat}_hash', fallback='')
        
        # Récupère le hash actuel depuis votre config/API
        vestiaires = self.app_config.get("fcvv", {}).get("appli", {}).get("vestiaire", [])
        current_info = next((item for item in vestiaires if item.get("categorie") == cat), None)
        
        if not current_info: return False
        
        # Si le hash stocké est égal à l'un des deux hashs officiels, l'accès est valide
        return stored_hash in [current_info.get("password_hash"), current_info.get("password_admin_hash")]

    def check_vestiaire_password(self, category_name, password):
        """Vérifie le mot de passe et retourne le rôle ('ADMIN' ou 'USER') si valide."""
        import hashlib
        
        # Récupération de la liste des vestiaires
        vestiaires = self.app_config.get("fcvv", {}).get("appli", {}).get("vestiaire", [])
        
        # Hash du mot de passe fourni
        entered_hash = hashlib.sha256(password.encode()).hexdigest()
        
        for item in vestiaires:
            if item.get("categorie") == category_name:
                # 1. Vérification ADMIN (Priorité haute)
                if entered_hash == item.get("password_admin_hash"):
                    return "ADMIN"
                
                # 2. Vérification STANDARD
                elif entered_hash == item.get("password_hash"):
                    return "USER"
                    
        return None
    
    def is_auth_still_valid(self, category_name):
        """Vérifie si la catégorie existe toujours dans la config distante."""
        vestiaires = self.app_config.get("fcvv", {}).get("appli", {}).get("vestiaire", [])
        return any(item.get("categorie") == category_name for item in vestiaires)

    def verify_and_clean_auths(self, *args):
        if not self.app_config: return
        vestiaires = self.app_config.get("fcvv", {}).get("appli", {}).get("vestiaire", [])
        
        valid_auths = []
        needs_update = False

        for cat in self.authorized_vestiaires:
            remote_item = next((item for item in vestiaires if item.get("categorie") == cat), None)
            # Lecture du hash depuis la section [Roles]
            local_hash = self.config.get('Roles', f'{cat}_hash', fallback="")
            
            # Condition : catégorie existe ET hash correspond (soit standard soit admin)
            if remote_item and local_hash in [remote_item.get("password_hash"), remote_item.get("password_admin_hash")]:
                valid_auths.append(cat)
            else:
                needs_update = True

        if needs_update:
            self.authorized_vestiaires = valid_auths
            if not valid_auths:
                self.config.set('User', 'vestiaire_auth', '0')
            self.config.write()

    def build_config(self, config):
        # Configuration des paramètres utilisateur
        config.setdefaults('User', {
            'dark_mode': '0',
            'font_size_factor': '24',
            'langue': 'Francais',
            'refresh_interval': '5',
            'news_period': '15',
            'vestiaire_auth': '0',
            'authorized_list': '',
            'nom_parent': '',
            'vestiaire_cgu_accept': '0'
        })
        
        # Initialisation de la section 'Roles' pour éviter les erreurs lors du premier démarrage
        config.setdefaults('Roles', {})
        
    def set_vestiaire_role(self, cat, role):
        """Sauvegarde le rôle (ADMIN/USER) pour une catégorie donnée dans le fichier config."""
        # On vérifie si la section 'Roles' existe, sinon on la crée
        if not self.config.has_section('Roles'):
            self.config.add_section('Roles')
        
        # Sauvegarde du rôle
        self.config.set('Roles', cat, role)
        # Écriture effective dans le fichier .ini
        self.config.write()
        print(f"[DEBUG] Role '{role}' sauvegarde pour la categorie '{cat}'.")
        
    def set_joueur_associe_pour_cat(self, cat, nom_joueur):
        """Sauvegarde le joueur ou les rôles associés pour une catégorie donnée dans le fichier config."""
        if not self.config.has_section('Roles'):
            self.config.add_section('Roles')
        
        # On normalise la catégorie en minuscules pour correspondre au format du fichier .ini
        cat_key = f"{cat.lower()}_joueur"
        self.config.set('Roles', cat_key, str(nom_joueur))
        self.config.write()
        print(f"[DEBUG] elements associes '{nom_joueur}' sauvegardes pour la categorie '{cat}'.")

    def get_joueur_associe_pour_cat(self, cat):
        """Récupère le joueur associé stocké localement pour la catégorie."""
        if self.config.has_section('Roles') and self.config.has_option('Roles', f'{cat}_joueur'):
            return self.config.get('Roles', f'{cat}_joueur')
        return ""
    
    def rafraichir_donnees(self):
        try:
            # Supposons que ton RootLayout stocke le ScreenManager dans une variable 'sm' ou 'screen_manager'
            # Adapte 'sm' selon le nom de l'attribut dans ton RootLayout
            screen_manager = getattr(self.root, 'sm', None) or getattr(self.root, 'screen_manager', None)
            
            if screen_manager and hasattr(screen_manager, 'current'):
                current_screen = screen_manager.get_screen(screen_manager.current)
                if hasattr(current_screen, 'rafraichir'):
                    current_screen.rafraichir()
                elif hasattr(current_screen, 'charger_donnees'):
                    current_screen.charger_donnees()
            else:
                print("[ATTENTION] Impossible de trouver le ScreenManager dans le RootLayout.")
        except Exception as e:
            print(f"[ERREUR] echec du rafraichissement : {e}")

    def get_role_for_cat(self, cat):
        """Récupère le rôle stocké pour la catégorie. Retourne 'USER' par défaut."""
        if self.config.has_section('Roles'):
            # Utilisation de has_option pour éviter une erreur si la clé n'existe pas
            if self.config.has_option('Roles', cat):
                return self.config.get('Roles', cat)
        
        # Retourne 'USER' par défaut si aucune configuration n'est trouvée
        return "USER"

    def on_start(self):
        threading.Thread(target=self.warmup_server, daemon=True).start()
    
        auth_str = self.config.get("User", "authorized_list", fallback="")
        self.authorized_vestiaires = [c.strip() for c in auth_str.split(",") if c.strip()]
    
        if platform in ("android", "ios"):
            from core.NotificationManager import get_notification_manager
            self.notifier = get_notification_manager()
            if self.notifier:
                try:
                    self.notifier.request_permissions()
                    self.notifier.init_service()
                    Clock.schedule_once(
                        lambda dt: self.notifier.subscribe_to_topic("TournoiVercel"), 5.0
                    )
                    if self.authorized_vestiaires:
                        Clock.schedule_once(
                            lambda dt: self.gerer_abonnements_fcm(self.authorized_vestiaires), 8.0
                        )
                except Exception as e:
                    print(f"[FCM ERROR] Initialisation : {e}")
        else:
            print("[FCM TRACE] Desktop : FCM ignore")
    
        if platform == "android" and "customize_android_bars" in globals():
            Clock.schedule_once(lambda dt: customize_android_bars(), 1)
    
        try:
            os.makedirs(self.cache_images_dir, exist_ok=True)
        except Exception:
            pass
    
        from kivy.core.window import Window
        Window.softinput_mode = "below_target"
        Window.bind(on_keyboard=self.on_back_button)
        Clock.schedule_once(lambda dt: self.start_network_tasks(), 1)
    
        if platform in ("android", "ios"):
            Clock.schedule_once(
                lambda dt: self.verifier_redirection_notification(),
                2.0
            )
    
    
    def on_resume(self):
        if platform == "android":
            Clock.schedule_once(
                lambda dt: self.verifier_redirection_notification_android(), 0.3
            )
        return True
    
    
    def verifier_redirection_notification(self):
        """
        Vérifie si l'application a été ouverte depuis une notification.
        """
    
        if platform == "android":
            self.verifier_redirection_notification_android()
    
        elif platform == "ios":
            self.verifier_redirection_notification_ios()
    
    
    def verifier_redirection_notification_ios(self):
        """
        Vérifie si l'application iOS a été ouverte depuis une notification.
    
        Les données sont enregistrées côté Objective-C dans NSUserDefaults
        lorsqu'une notification est reçue / sélectionnée.
    
        Après traitement réussi, les données sont supprimées.
        """
    
        if platform != "ios":
            return
    
        try:
            from pyobjus import autoclass
    
            NSUserDefaults = autoclass("NSUserDefaults")
            defaults = NSUserDefaults.standardUserDefaults()
    
            print("[iOS] Verification notification en attente...")
    
            # ---------------------------------------------------------
            # Vérification présence notification
            # ---------------------------------------------------------
    
            pending = defaults.objectForKey_("FCVV_NOTIFICATION_PENDING")
    
            if not pending:
                print("[iOS] Aucune notification en attente")
                return
    
            print("[iOS] Notification en attente detectee")
    
            # ---------------------------------------------------------
            # Récupération des données
            # ---------------------------------------------------------
    
            titre = defaults.stringForKey_(
                "FCVV_NOTIFICATION_TITLE"
            )
    
            message = defaults.stringForKey_(
                "FCVV_NOTIFICATION_BODY"
            )
    
            categorie = defaults.stringForKey_(
                "FCVV_NOTIFICATION_TOPIC"
            )
    
            match_id = defaults.stringForKey_(
                "FCVV_NOTIFICATION_MATCH_ID"
            )
    
            notif_type = defaults.stringForKey_(
                "FCVV_NOTIFICATION_TYPE"
            )
    
            # ---------------------------------------------------------
            # Valeurs par défaut
            # ---------------------------------------------------------
    
            titre = titre or ""
            message = message or ""
            categorie = categorie or ""
            match_id = match_id or ""
            notif_type = notif_type or ""
    
            # ---------------------------------------------------------
            # Logs
            # ---------------------------------------------------------
    
            print("[iOS] ===== NOTIFICATION EN ATTENTE =====")
            print("[iOS] titre      =", titre)
            print("[iOS] message    =", message)
            print("[iOS] categorie  =", categorie)
            print("[iOS] match_id   =", match_id)
            print("[iOS] notif_type =", notif_type)
    
            # ---------------------------------------------------------
            # Détermination de la destination
            # ---------------------------------------------------------
    
            nt = notif_type.strip().lower()
    
            # Notification destinée à l'accueil
            if nt in ("manual", "home") or not categorie:
    
                print("[iOS] Redirection vers HOME")
    
                Clock.schedule_once(
                    lambda dt: self.executer_redirection_home(),
                    0.5
                )
    
            # Notification destinée à un vestiaire
            else:
    
                print(
                    f"[iOS] Redirection vers VESTIAIRE : "
                    f"{categorie!r}"
                )
    
                Clock.schedule_once(
                    lambda dt: self.executer_redirection_vestiaire(
                        categorie,
                        match_id if match_id else None,
                        notif_type if notif_type else None
                    ),
                    0.5
                )
    
            # ---------------------------------------------------------
            # Nettoyage
            #
            # On nettoie après avoir programmé la redirection.
            # ---------------------------------------------------------
    
            defaults.removeObjectForKey_(
                "FCVV_NOTIFICATION_PENDING"
            )
    
            defaults.removeObjectForKey_(
                "FCVV_NOTIFICATION_TITLE"
            )
    
            defaults.removeObjectForKey_(
                "FCVV_NOTIFICATION_BODY"
            )
    
            defaults.removeObjectForKey_(
                "FCVV_NOTIFICATION_TOPIC"
            )
    
            defaults.removeObjectForKey_(
                "FCVV_NOTIFICATION_MATCH_ID"
            )
    
            defaults.removeObjectForKey_(
                "FCVV_NOTIFICATION_TYPE"
            )
    
            defaults.synchronize()
    
            print(
                "[iOS] Notification supprimee de NSUserDefaults"
            )
    
        except Exception as e:
            print(
                "[iOS] Erreur "
                "verifier_redirection_notification_ios:",
                repr(e)
            )
    
    
    def verifier_redirection_notification_android(self):
        if platform != "android":
            return
    
        try:
            PythonActivity = autoclass("org.kivy.android.PythonActivity")
            activity = PythonActivity.mActivity
            intent = activity.getIntent()
    
            open_page = intent.getStringExtra("open_page")
            categorie = intent.getStringExtra("categorie")
            match_id = intent.getStringExtra("match_id")
            notif_type = (
                intent.getStringExtra("notif_type")
                or intent.getStringExtra("type")
            )
    
            if open_page == "home" or notif_type in ("manual", "home"):
                Clock.schedule_once(lambda dt: self.executer_redirection_home(), 0.5)
            elif open_page == "vestiaire" and categorie:
                Clock.schedule_once(
                    lambda dt: self.executer_redirection_vestiaire(
                        categorie, match_id, notif_type
                    ),
                    0.5,
                )
    
            if open_page or categorie or notif_type:
                for key in ("open_page", "categorie", "match_id", "notif_type", "type"):
                    if intent.hasExtra(key):
                        intent.removeExtra(key)
                activity.setIntent(intent)
    
        except Exception as e:
            print(f"[FCM ERROR] Lecture Intent : {e}")
    
    
    def executer_redirection_home(self):
        try:
            if not self.root:
                print("[FCM REDIRECT] RootLayout introuvable")
                return
    
            if hasattr(self.root, "switch_screen"):
                self.root.switch_screen("home")
            elif hasattr(self.root, "sm"):
                self.root.sm.current = "home"
            else:
                print("[FCM REDIRECT] ScreenManager introuvable")
                return
    
        except Exception as e:
            print(f"[FCM REDIRECT ERROR] Home : {e}")
    
    
    def executer_redirection_vestiaire(self, categorie, match_id=None, notif_type=None):
        try:
            if not self.root or not hasattr(self.root, "sm"):
                print("[FCM REDIRECT] ScreenManager introuvable")
                return
    
            nt = (notif_type or "").strip().lower()
            sous_onglet = (
                "MESSAGES" if nt in ("chat", "message", "messages", "nouveau_message")
                else "CALENDRIER" if nt in (
                    "evenement", "événement", "event",
                    "creation_evenement", "evenement_creation"
                )
                else "NOTIFICATIONS"
            )
    
            if hasattr(self.root, "switch_screen"):
                self.root.switch_screen("vestiaire")
            else:
                self.root.sm.current = "vestiaire"
    
            screen = self.root.sm.get_screen("vestiaire")
    
            def charger(dt):
                screen.charger_categorie(categorie, sous_onglet=sous_onglet)
    
            Clock.schedule_once(charger, 0.2)
    
            if match_id and hasattr(screen, "ouvrir_match"):
                Clock.schedule_once(
                    lambda dt: (
                        print(f"[FCM TRACE] >>> ouvrir_match {match_id!r}"),
                        screen.ouvrir_match(match_id),
                        print("[FCM TRACE] <<< ouvrir_match")
                    ),
                    0.5,
                )
    
        except Exception as e:
            print(f"[FCM REDIRECT ERROR] Vestiaire : {e}")

    def get_local_image_path(self, url):
        """Optimise : Evite os.listdir(). Teste directement les extensions courantes."""
        img_hash = hashlib.md5(url.encode()).hexdigest()
        for ext in ['jpg', 'jpeg', 'png']:
            path = os.path.join(self.cache_images_dir, f"img_{img_hash}.{ext}")
            if os.path.exists(path):
                return path
        return None

    def download_news_images(self):
        """Telecharge les images uniquement si necessaire."""
        import requests
        try: news_period = int(self.config.get('User', 'news_period'))
        except: news_period = 15
        
        date_limite = datetime.now() - timedelta(days=news_period)
        news_list = []
        for key in ["fcvv", "tournoi"]:
            found = self.app_config.get(key, {}).get("appli", {}).get("news", [])
            if found: news_list.extend(found)
            
        if not news_list: return

        session = requests.Session()
        for item in news_list:
            try:
                actu_date = datetime.strptime(item.get("date", "").strip(), "%d/%m/%Y")
                if actu_date < date_limite: continue
            except: pass
            urls = item.get("images") or item.get("image") or []
            if isinstance(urls, str): urls = [urls]
            # Suppression des doublons d'URL a la volee
            unique_urls = list(dict.fromkeys([u for u in urls if u]))
            local_paths = []
            for url in unique_urls:
                if not url.startswith("http"):
                    local_paths.append(url)
                    continue   
                img_hash = hashlib.md5(url.encode()).hexdigest()
                ext = url.split('.')[-1].split('?')[0].lower()
                ext = ext if ext in ['jpg', 'jpeg', 'png'] else 'jpg'
                filename = f"img_{img_hash}.{ext}"
                local_path = os.path.join(self.cache_images_dir, filename)
                if os.path.exists(local_path):
                    local_paths.append(local_path)
                else:
                    if url in self.images_currently_downloading:
                        print(f"[IMAGES SKIP] Deja en cours de telechargement (memoire) : {filename}")
                        local_paths.append(local_path)
                        continue
                    try:
                        self.images_currently_downloading.add(url)
                        print(f"[IMAGES] Telechargement : {filename}")
                        r = session.get(url, timeout=10, verify=False)
                        if r.status_code == 200:
                            with open(local_path, "wb") as f: f.write(r.content)
                            local_paths.append(local_path)
                        else:
                            local_paths.append(url)
                    except Exception as e:
                        print(f"[IMAGES ERROR] {e}")
                        local_paths.append(url)
                    finally:
                        self.images_currently_downloading.discard(url)
            if "images" in item or isinstance(item.get("images"), list):
                item["images"] = local_paths
            else:
                item["image"] = local_paths[0] if local_paths else ""

    def cleanup_unused_images(self):
        """Nettoyage en tache de fond leger."""
        print("[CLEANUP] Verification des images inutilisees...")
        try:
            needed_hashes = set()
            for key in ["fcvv", "tournoi"]:
                news_list = self.app_config.get(key, {}).get("appli", {}).get("news", [])
                for item in news_list:
                    img_vals = item.get("images") or item.get("image") or []
                    if isinstance(img_vals, str): img_vals = [img_vals]
                    for iv in img_vals:
                        if not iv: continue
                        if iv.startswith("http"):
                            needed_hashes.add(hashlib.md5(iv.encode()).hexdigest())
                        elif "img_" in iv:
                            needed_hashes.add(os.path.basename(iv)[4:].split(".")[0])             
            if not needed_hashes:
                print("[CLEANUP] Alerte : Aucune image trouvee dans la config. Annulation par securite.")
                return
            deleted_count = 0
            for filename in os.listdir(self.cache_images_dir):
                if not filename.startswith("img_"): continue
                hash_part = filename[4:].split(".")[0]
                if hash_part not in needed_hashes:
                    try: 
                        os.remove(os.path.join(self.cache_images_dir, filename))
                        print(f"[CLEANUP] Supprime : {filename}")
                        deleted_count += 1
                    except: 
                        print(f"[CLEANUP SKIP] Impossible de supprimer {filename}")
            print(f"[CLEANUP] Termine. {deleted_count} image(s) supprimee(s).")
        except Exception as e:
            print(f"[CLEANUP ERROR] {e}")

    def start_network_tasks(self):
        if getattr(self, 'is_fetching_remote', False): 
            print("[CONFIG] Flag reseau deja actif. Annulation du doublon.")
            return
        self.is_fetching_remote = True
        threading.Thread(target=self.load_remote_config, daemon=True).start()

    def load_remote_config(self):
        """Optimise : Telecharge intelligemment et ne chaine les preloads que si necessaire."""
        import yaml
        import requests
        
        self.is_fetching_remote = True
        
        try:
            data_dir = self.user_data_dir
            configs = [
                ("config_tournoi.yaml", config_file_Id_tournoi, "tournoi"),
                ("config_fcvv.yaml", config_file_Id_fcvv, "fcvv"),
            ]
            is_first_run = not any(os.path.exists(os.path.join(data_dir, f[0])) for f in configs)
            
            # 1. Chargement rapide du cache local existant
            cached_data = {}
            for filename, _, key in configs:
                cache_path = os.path.join(data_dir, filename)
                if os.path.exists(cache_path):
                    try:
                        with open(cache_path, "r", encoding="utf-8") as f:
                            cached_data[key] = yaml.safe_load(f) or {}
                    except Exception as e:
                        print(f"[CACHE ERROR] {filename}: {e}")
            if cached_data: self.app_config.update(cached_data)
            
            # 2. Requêtes réseau
            session = requests.Session()
            tournoi_changed = False
            fcvv_changed = False
            updated_data = {}
            
            for filename, fid, key in configs:
                cache_path = os.path.join(data_dir, filename)
                url = f"https://docs.google.com/uc?id={fid}&export=download"
                print(f"[CONFIG] Verification {filename}...")
                try:
                    response = session.get(url, headers={"User-Agent": "Mozilla"}, timeout=10, verify=False)
                    if response.status_code != 200:
                        print(f"[CONFIG ERROR] HTTP {response.status_code} pour {filename}")
                        continue
                    content = response.content
                    if b"<html" in content[:100].lower():
                        print(f"[CONFIG ERROR] HTML recu pour {filename}")
                        continue
                    
                    # Comparaison directe en mémoire
                    old_content = b""
                    if os.path.exists(cache_path):
                        with open(cache_path, "rb") as f: old_content = f.read()
                    
                    if hashlib.sha256(content).hexdigest() != hashlib.sha256(old_content).hexdigest():
                        with open(cache_path, "wb") as f: f.write(content)
                        updated_data[key] = yaml.safe_load(content.decode("utf-8")) or {}
                        if key == "tournoi": tournoi_changed = True
                        if key == "fcvv": fcvv_changed = True
                    else:
                        print(f"[CONFIG] {filename} inchange.")
                except Exception as e:
                    print(f"[CONFIG ERROR] {filename}: {e}")

            # 3. Application ciblee des changements
            def finalize(dt):
                try:
                    if fcvv_changed or tournoi_changed:
                        self.app_config.update(updated_data)
                    
                    if self.app_config:
                        self.verify_and_clean_auths()

                    if fcvv_changed:
                        threading.Thread(target=self.download_news_images, daemon=True).start()
                        if not is_first_run: 
                            threading.Thread(target=self.cleanup_unused_images, daemon=True).start()    
                    
                    if tournoi_changed and hasattr(self, "preload_latest_tournament"):
                        threading.Thread(target=self.preload_latest_tournament, daemon=True).start()
                    
                    if hasattr(self, "_update_home_screen"):
                        Clock.schedule_once(self._update_home_screen, 0.1)
                finally:
                    self.is_fetching_remote = False

            Clock.schedule_once(finalize, 0)

        except Exception as e:
            print(f"[CONFIG FATAL ERROR] {e}")
            self.is_fetching_remote = False

    def on_back_button(self, window, key, *args):
        if key == 27: 
            if self.root and getattr(self.root, 'menu_open', False):
                self.root.close_menu()
                return True
            if self.root and hasattr(self.root, 'sm') and self.root.sm.current != 'home':
                self.root.switch_screen('home')
                return True
        return False
        
    def preload_latest_tournament(self, target_url=None):
        """Telecharge le tournoi cible de maniere isolee."""
        import requests
        tournois = self.app_config.get("tournoi", {}).get("tournois", [])
        if not tournois and not target_url: return
        try:
            if target_url:
                file_id = target_url.split("id=")[-1].split("&")[0]
                nom_cible = "selectionne"
            else:
                valid_years = [int(t.get("annee")) for t in tournois if str(t.get("annee", "")).strip().isdigit()]
                if not valid_years: return
                latest_year_str = str(max(valid_years))
                noms_annee = sorted(list(set([str(t.get("nom")).strip() for t in tournois if str(t.get("annee")).strip() == latest_year_str])))
                if not noms_annee: return
                nom_cible = noms_annee[0]
                target = next((t for t in tournois if str(t.get("nom")).strip() == nom_cible and str(t.get("annee")).strip() == latest_year_str and t.get("type") == "save"), None)
                if not target: target = next((t for t in tournois if str(t.get("nom")).strip() == nom_cible and str(t.get("annee")).strip() == latest_year_str), None)
                if not target: return
                file_id = target.get("url", "").split("id=")[-1].split("&")[0]
            download_url = f"https://drive.google.com/uc?export=download&id={file_id}"
            print(f"[PRELOAD] Telechargement de {nom_cible}...")
            r = requests.get(download_url, timeout=15, verify=False)
            if r.status_code == 200:
                ext = "json" if r.content.strip().startswith(b"{") else "yaml"
                filename = f"tournoi_{file_id}.{ext}"
                local_path = os.path.join(self.user_data_dir, filename)
                with open(local_path, "wb") as f: f.write(r.content)
                print(f"[PRELOAD] Succes : {filename} sauvegarde.")
                if target_url: Clock.schedule_once(self._update_home_screen, 0)
            else:
                print(f"[PRELOAD] Echec telechargement, code: {r.status_code}")
        except Exception as e:
            print(f"[PRELOAD ERROR] : {e}")

    def _update_home_screen(self, dt):
        if not self.root or not hasattr(self.root, 'sm') or not self.root.sm.has_screen('home'): return
        home = self.root.sm.get_screen('home')
        news_data = self.app_config.get("fcvv", {}).get("appli", {}).get("news", [])
        current_hash = hashlib.md5(str(news_data).encode()).hexdigest()
        if current_hash != self.last_config_hash:
            print(f"[UI] Changement detecte ! Nouveau hash: {current_hash[:8]}")
            self.last_config_hash = current_hash
            Clock.schedule_once(lambda dt: home.update_ui_from_config(force=True), 0.1)
        else:
            print("[UI] Aucun changement dans les donnees, rafraichissement ignore.")
    
    def refresh_ui_theme(self):
        if self.root:
            if hasattr(self.root, 'build_menu'):
                self.root.build_menu()
            if hasattr(self.root, 'sm') and hasattr(self.root, 'title_label'):
                current_screen = self.root.sm.current
                self.root.title_label.text = self._(current_screen)
    
    def gerer_abonnements_fcm(self, nouvelles_categories, anciennes_categories=None):
        from kivy.clock import Clock
        
        # On délègue l'exécution à _execute_fcm_subscription
        # Le délai est conservé pour garantir que l'initialisation du manager est terminée
        Clock.schedule_once(lambda dt: self._execute_fcm_subscription(nouvelles_categories, anciennes_categories), 3.0)
    
    @mainthread
    def afficher_alerte_push(self, titre, message):
        """
        Déclenche l'affichage d'une alerte en temps réel par-dessus l'écran actuel.
        """
        from core.NotificationManager import afficher_popup_notification
        try:
            # Si le RootLayout a une méthode dédiée, on la privilégie, 
            # sinon on appelle directement la popup Kivy
            if self.root and hasattr(self.root, 'afficher_popup_flottante'):
                self.root.afficher_popup_flottante(titre, message)
            else:
                afficher_popup_notification(titre=titre, corps=message)
            print(f"[POPUP UI] Alerte en temps reel affichee : {titre}")
        except Exception as e:
            print(f"[POPUP ERROR] Impossible d'afficher l'alerte : {e}")

    def _execute_fcm_subscription(self, nouvelles, anciennes=None):
        if getattr(self, 'notifier', None) is None:
            return
        from kivy.clock import Clock
        
        # On vérifie que le manager existe bien
        if not hasattr(self, 'notifier') or self.notifier is None:
            print("[FCM ERROR] NotificationManager non initialise.")
            return

        def do_fcm_work(*args):
            try:
                # 1. Lecture config sécurisée si nécessaire
                if anciennes is None:
                    anciennes_str = self.config.get('User', 'authorized_list', fallback='')
                    anciennes_utilisees = [c.strip() for c in anciennes_str.split(',') if c.strip()]
                else:
                    anciennes_utilisees = anciennes

                print(f"[FCM DEBUG] Synchro : {nouvelles} | Anciennes : {anciennes_utilisees}")

                # 2. Désabonnement (Le différentiel est crucial)
                for cat in anciennes_utilisees:
                    if cat not in nouvelles:
                        print(f"[FCM] Desabonnement : {cat}")
                        self.notifier.unsubscribe_from_topic(cat)

                # 3. ABONNEMENT FORCÉ
                # Le manager (Android ou iOS) gère l'idempotence
                for cat in nouvelles:
                    print(f"[FCM] Abonnement force : {cat}")
                    self.notifier.subscribe_to_topic(cat)
                
                # 4. Global
                self.notifier.subscribe_to_topic("TournoiVercel")
                print("[FCM] Synchro terminee via NotificationManager")

            except Exception:
                print("[FCM ERROR] Erreur lors de la synchro FCM")

        # On déclenche sur le thread principal
        Clock.schedule_once(do_fcm_work, 0.5)
    
    def warmup_server(self):
        """Reveille le serveur API Render en arriere-plan."""
        import requests
        from kivy.utils import platform  # Garantit l'import du composant Kivy
    
        url = "https://fcvv-api.onrender.com/" 
        try:
            print("[WARMUP] Ping de reveil envoye au serveur...")
            # Kivy définit 'platform' comme une chaîne ("win", "android", "ios", etc.)
            is_windows = (platform == 'win')
            
            response = requests.get(url, timeout=35, verify=not is_windows)
            if response.status_code == 200:
                print("[WARMUP] Serveur Render eveille et pret !")
            else:
                print(f"[WARMUP] Reponse serveur avec statut : {response.status_code}")
        except Exception as e:
            print(f"[WARMUP] Attente de demarrage ou indisponibilite : {e}")

if __name__ == "__main__":
    MyApp().run()