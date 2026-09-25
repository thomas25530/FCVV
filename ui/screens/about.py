# -*- coding: utf-8 -*-
import webbrowser
import os
import threading
import requests
import urllib3
import hashlib
from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.image import Image
from kivy.uix.scrollview import ScrollView
from kivy.graphics import Color, Rectangle
from kivy.app import App
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.utils import platform
from kivy.uix.behaviors import ButtonBehavior
from kivy.animation import Animation
from kivy.uix.button import Button

CURRENT_VERSION_ANDROID = "2026.1.1.1"
CURRENT_VERSION_IOS = "2026.1.1.0"

URL_CGU = "https://sites.google.com/view/fcvv-application/conditions-utilisation"
URL_CONFIDENTIALITE = "https://sites.google.com/view/fcvv-application/confidentialite"

def _(key):
    app = App.get_running_app()
    return app._(key) if hasattr(app, '_') else key

class ClickableImage(ButtonBehavior, Image):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.url = None
    
    def on_release(self):
        if self.url:
            webbrowser.open(self.url)

class AboutScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.is_mobile = (platform in ('android', 'ios'))
        self.KIVY_BLUE = (30/255, 58/255, 138/255, 1)
        padding_val = dp(20) if self.is_mobile else dp(30)
        self.root = BoxLayout(orientation='vertical', padding=[padding_val, dp(10), padding_val, dp(10)])
        with self.root.canvas.before:
            Color(*self.KIVY_BLUE)
            self.rect_bg = Rectangle(pos=self.root.pos, size=self.root.size)
        self.root.bind(pos=self._update_bg, size=self._update_bg)
        self.scroll = ScrollView(size_hint=(1, 1), do_scroll_x=False, bar_width=0, scroll_type=['content'])
        self.scroll_content = BoxLayout(orientation='vertical', size_hint_y=None, spacing=dp(25))
        self.scroll_content.bind(minimum_height=self.scroll_content.setter('height'))
        self.intro_label = Label(markup=True, halign='center', size_hint_y=None)
        self.intro_label.bind(width=lambda s, w: s.setter('text_size')(s, (w, None)))
        self.intro_label.bind(texture_size=lambda s, z: s.setter('height')(s, z[1]))
        img_h = dp(300) if self.is_mobile else dp(220)
        self.img_offert = ClickableImage(size_hint=(1, None), height=img_h, fit_mode="contain", opacity=0)
        self.info_list = BoxLayout(orientation='vertical', spacing=dp(15), size_hint_y=None)
        self.info_list.bind(minimum_height=self.info_list.setter('height'))
        self.scroll_content.add_widget(self.intro_label)
        self.scroll_content.add_widget(self.img_offert)
        self.scroll_content.add_widget(self.info_list)
        self.scroll_content.add_widget(BoxLayout(size_hint_y=None, height=dp(40)))
        self.scroll.add_widget(self.scroll_content)
        self.root.add_widget(self.scroll)
        self.add_widget(self.root)

    def _update_bg(self, instance, value):
        self.rect_bg.pos = instance.pos
        self.rect_bg.size = instance.size

    def on_enter(self):
        self.update_ui_from_config()
    
    def open_url(self, url):
        webbrowser.open(url)

    def bind_label(self, lbl):
        lbl.bind(width=lambda s, w: s.setter('text_size')(s, (w, None)))
        lbl.bind(texture_size=lambda s, z: s.setter('height')(s, z[1]))

    def update_ui_from_config(self, *args):
        app = App.get_running_app()
        if not hasattr(app, 'app_config') or not app.app_config:
            Clock.schedule_once(self.update_ui_from_config, 0.5)
            return
            
        about_data = app.app_config.get("fcvv", {}).get("appli", {}).get("about", {})
        lang = app.config.get('User', 'langue') if app.config.has_section('User') else "Francais"
        user_size = int(app.config.get('User', 'font_size_factor', fallback=20)) if app.config.has_section('User') else 20
        
        if platform == 'ios':
            current_version = CURRENT_VERSION_IOS
            version_key = 'version_ios'
        else:
            current_version = CURRENT_VERSION_ANDROID
            version_key = 'version_android'

        # 1. Intro
        intro = about_data.get('intro_text_en' if lang == 'English' else 'intro_text') or _('about_intro')
        if "Cette application" in intro and "\n" not in intro:
            intro = intro.replace("Cette application", "Cette application\n")
        
        self.intro_label.text = f"[b]{intro}[/b]"
        self.intro_label.font_size = f"{user_size + (4 if self.is_mobile else 2)}sp"
        
        # 2. Logo
        self.img_offert.url = about_data.get("sponsor_url")
        path = about_data.get("logo_partenaire", "./assets/default_logo.png")
        if path.startswith("http"):
            threading.Thread(target=self.download_external_image, args=(path,), daemon=True).start()
        else:
            self.img_offert.source = path
            self.img_offert.opacity = 1
            
        # 3. Traitement des versions
        self.info_list.clear_widgets()
        
        remote_version = str(about_data.get(version_key, current_version)).strip()
        current_version_clean = str(current_version).strip()
        
        # Affiche uniquement "Version actuelle"
        lbl_curr = Label(
            text=f"[color=bbbbbb]Version actuelle :[/color] [b]{current_version_clean}[/b]", 
            markup=True, font_size=f"{user_size + 2}sp", halign='center', size_hint_y=None
        )
        self.bind_label(lbl_curr)
        self.info_list.add_widget(lbl_curr)
        
        # Message rouge si différente du YAML
        if remote_version and current_version_clean != remote_version:
            lbl_alert = Label(
                text=f"[color=FF4500][b]Une mise à jour est nécessaire ({remote_version})[/b][/color]", 
                markup=True, font_size=f"{user_size + 2}sp", halign='center', size_hint_y=None
            )
            self.bind_label(lbl_alert)
            self.info_list.add_widget(lbl_alert)

        # 4. Autres détails (en ignorant tout libellé de version résiduel)
        for item in about_data.get("details", []):
            label_text = str(item.get('label', '')).strip().lower()
            if label_text in ('version', 'version actuelle', 'version android', 'version ios'):
                continue
                
            name = item.get('label_en' if lang == 'English' else 'label', '')
            val = item.get("value", "")
            
            lbl = Label(
                text=f"[color=bbbbbb]{name} :[/color] [b]{val}[/b]", 
                markup=True, font_size=f"{user_size + 2}sp", halign='center', size_hint_y=None
            )
            self.bind_label(lbl)
            self.info_list.add_widget(lbl)
            
        # 5. Documents légaux
        lbl_update = Label(
            text="[color=bbbbbb]Documents légaux mis à jour le :[/color] [b]22 juillet 2026[/b]",
            markup=True,
            font_size=f"{user_size}sp",
            halign='center',
            size_hint_y=None
        )
        self.bind_label(lbl_update)
        self.info_list.add_widget(lbl_update)
        
        lbl_legal = Label(
            text="[b]Documents légaux[/b]",
            markup=True,
            font_size=f"{user_size + 4}sp",
            halign='center',
            size_hint_y=None,
            height=dp(40)
        )
        self.info_list.add_widget(lbl_legal)

        btn_cgu = Button(
            text="Conditions Générales d'Utilisation",
            font_size=f"{user_size + 2}sp",
            size_hint_y=None,
            height=dp(60),
            background_color=(0.2, 0.5, 1, 1)
        )
        btn_cgu.bind(on_release=lambda x: self.open_url(URL_CGU))
        self.info_list.add_widget(btn_cgu)

        btn_conf = Button(
            text="Politique de confidentialité",
            font_size=f"{user_size + 2}sp",
            size_hint_y=None,
            height=dp(60),
            background_color=(0.2, 0.5, 1, 1)
        )
        btn_conf.bind(on_release=lambda x: self.open_url(URL_CONFIDENTIALITE))
        self.info_list.add_widget(btn_conf)

    def download_external_image(self, url):
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        app = App.get_running_app()
        url_hash = hashlib.md5(url.encode("utf-8")).hexdigest()
        temp_path = os.path.join(
            app.user_data_dir,
            f"sponsor_{url_hash}.png"
        )
        if os.path.exists(temp_path):
            Clock.schedule_once(lambda dt: self._apply_image(temp_path), 0)
            return
        try:
            r = requests.get(url, timeout=10, verify=False)
            if r.status_code == 200:
                with open(temp_path, "wb") as f:
                    f.write(r.content)
                Clock.schedule_once(
                    lambda dt: self._apply_image(temp_path),
                    0
                )
        except Exception as e:
            print(f"[ABOUT IMAGE ERROR] {e}")

    def _apply_image(self, path):
        self.img_offert.source = path
        self.img_offert.reload()
        Animation(opacity=1, duration=0.5).start(self.img_offert)