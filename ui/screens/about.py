# -*- coding: utf-8 -*-
import webbrowser
from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.image import Image
from kivy.uix.scrollview import ScrollView
from kivy.graphics import Color, Rectangle
from kivy.app import App
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.utils import platform  # <-- Ajouté pour détecter iOS/Android
import os
import threading  # <-- Ajouté pour le téléchargement asynchrone sécurisé

# On définit ou on importe la fonction de traduction
def _(key):
    app = App.get_running_app()
    if hasattr(app, '_'):
        return app._(key)
    return key

class ClickableImage(Image):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.url = None

    def on_touch_down(self, touch):
        if touch.is_mouse_scrolling: 
            return False
        if self.collide_point(*touch.pos):
            if self.url:
                webbrowser.open(self.url)
            return True
        return super().on_touch_down(touch)

class AboutScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # 1. RÉCUPÉRATION DE LA PLATEFORME (Adapté iOS/Android)
        self.is_mobile = (platform == 'android' or platform == 'ios')
        
        self.KIVY_BLUE = (30/255, 58/255, 138/255, 1)
        
        # Ajustement du padding selon la plateforme
        padding_val = dp(20) if self.is_mobile else dp(30)
        self.root = BoxLayout(orientation='vertical', padding=[padding_val, dp(10), padding_val, dp(10)])
        
        with self.root.canvas.before:
            Color(*self.KIVY_BLUE)
            self.rect_bg = Rectangle(pos=self.root.pos, size=self.root.size)
        self.root.bind(pos=self._update_bg, size=self._update_bg)

        self.scroll = ScrollView(
            size_hint=(1, 1), 
            do_scroll_x=False,
            bar_width=0,            # Rend la barre de défilement invisible
            scroll_type=['content'] # Le défilement se fait uniquement en glissant le doigt sur le contenu
        )
        self.scroll_content = BoxLayout(orientation='vertical', size_hint_y=None, spacing=dp(25))
        self.scroll_content.bind(minimum_height=self.scroll_content.setter('height'))

        # Intro Label
        self.intro_label = Label(
            text="", 
            markup=True, halign='center', 
            size_hint_y=None
        )
        self.intro_label.bind(width=lambda s, w: s.setter('text_size')(s, (w, None)))
        self.intro_label.bind(texture_size=lambda s, z: s.setter('height')(s, z[1]))
        
        # Image Partenaire (Plus grande sur mobile)
        img_h = dp(300) if self.is_mobile else dp(220)
        self.img_offert = ClickableImage(
            source="", 
            size_hint=(1, None), height=img_h, 
            allow_stretch=True, keep_ratio=True,
            nocache=True 
        )

        self.info_list = BoxLayout(orientation='vertical', spacing=dp(15), size_hint_y=None)
        self.info_list.bind(minimum_height=self.info_list.setter('height'))

        self.scroll_content.add_widget(self.intro_label)
        self.scroll_content.add_widget(self.img_offert)
        self.scroll_content.add_widget(self.info_list)
        self.scroll_content.add_widget(BoxLayout(size_hint_y=None, height=dp(40))) # Espace final
        
        self.scroll.add_widget(self.scroll_content)
        self.root.add_widget(self.scroll)
        self.add_widget(self.root)

    def _update_bg(self, instance, value):
        self.rect_bg.pos = instance.pos
        self.rect_bg.size = instance.size

    def on_enter(self):
        self.update_ui_from_config()

    def update_ui_from_config(self, *args):
        app = App.get_running_app()
        
        if hasattr(app, 'app_config') and app.app_config:
            about_data = app.app_config.get("fcvv", {}).get("appli", {}).get("about", {})
            
            lang = "Français"
            user_size = 20
            if hasattr(app, 'config') and app.config.has_section('User'):
                lang = app.config.get('User', 'langue')
                user_size = int(app.config.get('User', 'font_size_factor', fallback=20))

            # 1. Texte d'introduction
            intro = about_data.get('intro_text_en' if lang == 'English' else 'intro_text')
            if not intro:
                intro = _('about_intro')
                
            self.intro_label.text = f"[b]{intro}[/b]"
            self.intro_label.font_size = f"{user_size + (4 if self.is_mobile else 2)}sp"
            
            # 2. Image et lien
            self.img_offert.url = about_data.get("sponsor_url")
            path = about_data.get("logo_partenaire", "./assets/default_logo.png")
            
            if path.startswith("http"):
                # Lancement du téléchargement sécurisé en tâche de fond
                threading.Thread(target=self.download_external_image, args=(path,), daemon=True).start()
            else:
                self.img_offert.source = path
                self.img_offert.reload()
            
            # 3. Liste d'informations
            self.info_list.clear_widgets()
            details = about_data.get("details", [])
            
            for item in details:
                name = item.get('label_en' if lang == 'English' else 'label', '')
                val = item.get("value", "")
                
                lbl_size = user_size + (2 if self.is_mobile else 0)
                
                lbl = Label(
                    text=f"[color=bbbbbb]{name} :[/color] [b]{val}[/b]",
                    markup=True, font_size=f"{lbl_size}sp", halign='center',
                    size_hint_y=None
                )
                lbl.bind(width=lambda s, w: s.setter('text_size')(s, (w, None)))
                lbl.bind(texture_size=lambda s, z: s.setter('height')(s, z[1]))
                self.info_list.add_widget(lbl)
            
            return True
        else:
            Clock.schedule_once(self.update_ui_from_config, 0.5)
            return False

    def download_external_image(self, url):
        """Téléchargement via requests avec gestion du double fallback SSL (Robuste sur iOS)"""
        import requests
        import urllib3
        app = App.get_running_app()
        filename = "sponsor_cache.png"
        temp_path = os.path.join(app.user_data_dir, filename)
        
        # On charge d'abord le cache s'il existe pour ne pas laisser l'écran vide
        if os.path.exists(temp_path) and self.img_offert.source != temp_path:
            Clock.schedule_once(lambda dt: self._apply_cached_image(temp_path), 0)

        # Récupération du faisceau de certificats de l'application s'il existe
        ca_bundle = getattr(app, 'ca_bundle', True)

        try:
            r = None
            try:
                r = requests.get(url, timeout=10, verify=ca_bundle)
            except Exception:
                urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
                r = requests.get(url, timeout=10, verify=False)

            if r and r.status_code == 200:
                with open(temp_path, 'wb') as f:
                    f.write(r.content)
                # On applique la nouvelle image sur le thread principal de Kivy
                Clock.schedule_once(lambda dt: self._apply_cached_image(temp_path), 0)
        except Exception as e:
            print(f"[ABOUT IMAGE ERROR] {e}")

    def _apply_cached_image(self, path):
        """Méthode thread-safe appelée uniquement sur l'UI thread"""
        self.img_offert.source = path
        self.img_offert.reload()