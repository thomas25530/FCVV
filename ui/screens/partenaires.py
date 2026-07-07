# -*- coding: utf-8 -*-
import webbrowser
import os
import threading
import hashlib
import requests
import urllib3
from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.image import Image
from kivy.app import App
from kivy.metrics import dp
from kivy.graphics import Color, Rectangle, RoundedRectangle
from kivy.clock import Clock
from kivy.animation import Animation
from kivy.graphics import Rotate, PushMatrix, PopMatrix

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class ImageButton(ButtonBehavior, Image):
    def __init__(self, **kwargs):
        self.link = kwargs.pop('link', '')
        super().__init__(**kwargs)
        self.opacity = 0 

    def on_release(self):
        if self.link:
            url = self.link if self.link.startswith("http") else "http://" + self.link
            webbrowser.open(url)

class PartenairesScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.current_tab = None
        self.KIVY_BLUE = (30/255, 58/255, 138/255, 1)
        
        with self.canvas.before:
            Color(*self.KIVY_BLUE)
            self.rect_bg = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._update_rect, size=self._update_rect)

        self.main_layout = BoxLayout(orientation='vertical')
        self.add_widget(self.main_layout)
        
        self.tab_scroll = ScrollView(size_hint_y=None, height=dp(85), do_scroll_y=False, bar_width=0)
        self.tab_bar = BoxLayout(size_hint_x=None, spacing=dp(10), padding=dp(10))
        self.tab_bar.bind(minimum_width=self.tab_bar.setter('width'))
        self.tab_scroll.add_widget(self.tab_bar)
        self.main_layout.add_widget(self.tab_scroll)

        self.scroll = ScrollView(bar_width=0)
        self.content_layout = BoxLayout(orientation='vertical', padding=dp(20), spacing=dp(20), size_hint_y=None)
        self.content_layout.bind(minimum_height=self.content_layout.setter('height'))
        self.scroll.add_widget(self.content_layout)
        self.main_layout.add_widget(self.scroll)

    def _update_rect(self, instance, value):
        self.rect_bg.pos = instance.pos
        self.rect_bg.size = instance.size

    def download_and_set_image(self, url, img_widget):
        app = App.get_running_app()
        # Création du dossier cache_images
        cache_dir = os.path.join(app.user_data_dir, "cache_images")
        if not os.path.exists(cache_dir):
            os.makedirs(cache_dir)
            
        url_hash = hashlib.md5(url.encode("utf-8")).hexdigest()
        local_path = os.path.join(cache_dir, f"part_{url_hash}.png")

        if os.path.exists(local_path):
            Clock.schedule_once(lambda dt: self._apply_img(img_widget, local_path), 0)
            return

        def fetch():
            try:
                r = requests.get(url, timeout=10, verify=False)
                if r.status_code == 200:
                    with open(local_path, "wb") as f:
                        f.write(r.content)
                    Clock.schedule_once(lambda dt: self._apply_img(img_widget, local_path), 0)
            except Exception as e:
                print(f"Erreur telechargement: {e}")

        threading.Thread(target=fetch, daemon=True).start()

    def _apply_img(self, widget, path):
        widget.source = path
        widget.reload()
        Animation(opacity=1, duration=0.3).start(widget)

    def update_ui(self):
        app = App.get_running_app()
        # 1. Récupération du facteur de taille
        user_size = app.config.getint('User', 'font_size_factor', fallback=18) if hasattr(app, 'config') else 18
        
        data = app.app_config.get("fcvv", {}).get("appli", {}).get("partenaires", [])
        niveaux_map = {p.get('niveau'): p.get('ordre', 99) for p in data if p.get('niveau')}
        niveaux_tries = sorted(niveaux_map.keys(), key=lambda x: niveaux_map[x])
        if not self.current_tab or self.current_tab not in niveaux_tries:
            self.current_tab = niveaux_tries[0] if niveaux_tries else None

        # Construction des onglets stylisés
        self.tab_bar.clear_widgets()
        for niv in niveaux_tries:
            is_active = (self.current_tab == niv)
            
            # 2. Application de la taille de police dynamique et ajustement de la largeur
            btn = Button(
                text=niv.upper(), 
                size_hint=(None, 1), 
                width=max(dp(160), dp(len(niv) * (user_size * 0.7))), # Largeur dynamique
                font_size=f"{user_size}sp",                            # Taille dynamique
                background_normal='', 
                background_color=(0,0,0,0),
                color=(0,0,0,1) if is_active else (1,1,1,1), 
                bold=is_active
            )
            
            with btn.canvas.before:
                Color(*(0.97, 0.93, 0.25, 1) if is_active else (1, 1, 1, 0.15))
                btn.bg_rect = RoundedRectangle(pos=btn.pos, size=btn.size, radius=[dp(8)])
            
            btn.bind(pos=lambda inst, val: setattr(inst.bg_rect, 'pos', inst.pos),
                     size=lambda inst, val: setattr(inst.bg_rect, 'size', inst.size),
                     on_release=lambda x, t=niv: self.set_tab(t))
            self.tab_bar.add_widget(btn)

        self.content_layout.clear_widgets()
        self.scroll.scroll_y = 1.0
        for p in [p for p in data if p.get('niveau') == self.current_tab]:
            img = ImageButton(link=p.get('lien', ''), size_hint_y=None, height=dp(150), fit_mode="contain")
            self.content_layout.add_widget(img)
            self.download_and_set_image(p.get('logo', ''), img)

    def set_tab(self, tab):
        self.current_tab = tab
        self.update_ui()
        
        Clock.schedule_once(lambda dt: setattr(self.scroll, 'scroll_y', 1.0), 0)
        
    def on_enter(self, *args):
        self.update_ui()