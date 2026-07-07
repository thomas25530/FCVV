# -*- coding: utf-8 -*-
import webbrowser
import os
import threading
import hashlib
import requests
import urllib3
from kivy.app import App
from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.image import Image
from kivy.uix.scrollview import ScrollView
from kivy.uix.spinner import Spinner
from kivy.graphics import Color, RoundedRectangle
from kivy.metrics import dp, sp
from kivy.clock import Clock
from kivy.animation import Animation
from kivy.uix.popup import Popup
from kivy.uix.spinner import SpinnerOption

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class CustomSpinnerOption(SpinnerOption):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.height = dp(60) # Augmentez cette valeur pour la hauteur des boutons

class ProductCard(BoxLayout):
    def __init__(self, name, prod_type, price, image_url, description, user_size, **kwargs):
        super().__init__(orientation="vertical", size_hint_y=None, spacing=dp(10), padding=dp(15), **kwargs)
        self.bind(minimum_height=self.setter('height'))
        
        with self.canvas.before:
            Color(1, 1, 1, 1)
            self.bg_rect = RoundedRectangle(radius=[dp(10)])
        self.bind(pos=self._update_rect, size=self._update_rect)

        header_zone = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(100), spacing=dp(10))
        
        self.img_btn = Button(size_hint=(None, None), size=(dp(100), dp(100)), background_normal='', background_color=(0,0,0,0))
        self.img_widget = Image(pos=self.img_btn.pos, size=self.img_btn.size, fit_mode="cover", opacity=0)
        self.img_btn.add_widget(self.img_widget)
        self.img_btn.bind(on_release=self.show_full_image)
        self.img_btn.bind(pos=lambda *args: setattr(self.img_widget, 'pos', self.img_btn.pos))
        header_zone.add_widget(self.img_btn)
        
        info_zone = BoxLayout(orientation="vertical", spacing=dp(2))
        info_zone.add_widget(Label(text=f"[b]{name}[/b]", font_size=f"{user_size}sp", markup=True, color=(0,0,0,1), halign='left', valign='middle'))
        info_zone.add_widget(Label(text=prod_type, font_size=f"{user_size-2}sp", color=(0.5,0.5,0.5,1), halign='left', valign='middle'))
        info_zone.add_widget(Label(text=f"[color=1E3A8A][b]{price} €[/b][/color]", font_size=f"{user_size}sp", markup=True, halign='left', valign='middle'))
        header_zone.add_widget(info_zone)
        
        self.add_widget(header_zone)

        self.desc_label = Label(text=description, font_size=f"{user_size-2}sp", color=(0.2,0.2,0.2,1), size_hint_y=None, halign='left', valign='top',markup=True)
        self.desc_label.bind(
            width=lambda inst, w: setattr(inst, 'text_size', (w, None)),
            texture_size=lambda inst, size: setattr(inst, 'height', size[1])
        )
        self.add_widget(self.desc_label)

        if image_url:
            self.download_and_set_image(image_url, self.img_widget)

    def show_full_image(self, *args):
        content = BoxLayout(orientation='vertical', padding=dp(10))
        full_img = Image(source=self.img_widget.source, fit_mode="contain")
        close_btn = Button(text="Fermer", size_hint_y=None, height=dp(50))
        content.add_widget(full_img)
        content.add_widget(close_btn)
        popup = Popup(title="Aperçu", content=content, size_hint=(0.9, 0.9))
        close_btn.bind(on_release=popup.dismiss)
        popup.open()

    def _update_rect(self, instance, value):
        self.bg_rect.pos = instance.pos
        self.bg_rect.size = instance.size

    def download_and_set_image(self, url, img_widget):
        app = App.get_running_app()
        cache_dir = os.path.join(app.user_data_dir, "cache_images")
        if not os.path.exists(cache_dir): os.makedirs(cache_dir)
        url_hash = hashlib.md5(url.encode("utf-8")).hexdigest()
        local_path = os.path.join(cache_dir, f"prod_{url_hash}.png")
        if os.path.exists(local_path):
            Clock.schedule_once(lambda dt: self._apply_img(img_widget, local_path), 0)
            return
        def fetch():
            try:
                r = requests.get(url, timeout=10, verify=False)
                if r.status_code == 200:
                    with open(local_path, "wb") as f: f.write(r.content)
                    Clock.schedule_once(lambda dt: self._apply_img(img_widget, local_path), 0)
            except Exception as e: print(f"Erreur image: {e}")
        threading.Thread(target=fetch, daemon=True).start()

    def _apply_img(self, widget, path):
        widget.source = path
        widget.reload()
        Animation(opacity=1, duration=0.3).start(widget)

class BoutiqueScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        app = App.get_running_app()
        self.all_products = [] 
        self.current_limit = 10 
        self.boutique_url = "https://votre-site-boutique.com"
        
        self.main_layout = BoxLayout(orientation="vertical", padding=dp(15), spacing=dp(10))
        self.lbl_title = Label(text="Bienvenue sur notre boutique", bold=True, size_hint_y=None, height=dp(50))
        self.main_layout.add_widget(self.lbl_title)
        
        self.user_font_size = app.config.getint('User', 'font_size_factor', fallback=18)
        
        self.btn_link = Button(
            text=">>> CLIQUEZ ICI POUR COMMANDER <<<", 
            markup=True, bold=True, color=(30/255, 58/255, 138/255, 1), 
            background_normal='', background_color=(0, 0, 0, 0), 
            size_hint=(0.9, None), height=dp(65), pos_hint={'center_x': 0.5}
        )
        
        with self.btn_link.canvas.before:
            self.btn_color = Color(253/255, 224/255, 71/255, 1)
            self.btn_rect = RoundedRectangle(pos=self.btn_link.pos, size=self.btn_link.size, radius=[dp(14)])
        self.btn_link.bind(pos=self._update_btn_rect, size=self._update_btn_rect)
        self.btn_link.bind(on_release=lambda x: webbrowser.open(self.boutique_url))
        self.main_layout.add_widget(self.btn_link)
        
        self.lbl_afficher = Label(text="Afficher :", size_hint_y=None, height=dp(30), halign='left', color=(1, 1, 1, 1))
        self.main_layout.add_widget(self.lbl_afficher)
        
        self.filter = Spinner(text='Tous les produits', values=('Tous les produits',), size_hint_y=None, height=dp(50), option_cls=CustomSpinnerOption)
        self.filter.bind(text=self.on_filter_change)
        self.main_layout.add_widget(self.filter)
        
        # Label de comptage
        self.lbl_counter = Label(text="", size_hint_y=None, height=dp(40), color=(1, 1, 1, 1), halign='center', valign='middle')
        self.lbl_counter.bind(size=lambda inst, val: setattr(inst, 'text_size', val))
        
        self.scroll = ScrollView(bar_width=0)
        self.products_container = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(15))
        self.products_container.bind(minimum_height=self.products_container.setter('height'))
        
        self.btn_more = Button(text="Afficher plus de produits", size_hint=(0.8, None), height=dp(50), pos_hint={'center_x': 0.5}, background_color=(0.2, 0.2, 0.2, 1))
        self.btn_more.bind(on_release=self.load_more)
        
        self.scroll.add_widget(self.products_container)
        self.main_layout.add_widget(self.scroll)
        self.add_widget(self.main_layout)

    def on_enter(self, *args):
        app = App.get_running_app()
        self.user_size = app.config.getint('User', 'font_size_factor', fallback=18)
        self.btn_link.font_size = f"{self.user_size * 0.8}sp"
        self.lbl_title.font_size = f"{self.user_size + 4}sp"
        self.lbl_afficher.font_size = f"{self.user_size - 2}sp"
        self.filter.font_size = f"{self.user_size}sp"
        self.btn_more.font_size = f"{self.user_size}sp"
        self.lbl_counter.font_size = f"{self.user_size - 2}sp"
        Clock.schedule_once(lambda dt: self.load_products(), 0.1)

    def _update_btn_rect(self, instance, value):
        self.btn_rect.pos = instance.pos
        self.btn_rect.size = instance.size

    def load_products(self):
        app = App.get_running_app()
        data = app.app_config.get("fcvv", {}).get("appli", {}).get("boutique", {})
        self.boutique_url = data.get("url_externe", self.boutique_url)
        self.all_products = data.get('produits', [])
        types_disponibles = sorted(list(set(p.get('type') for p in self.all_products if p.get('type'))))
        self.filter.values = ['Tous les produits'] + types_disponibles
        self.display_products(self.all_products)

    def display_products(self, product_list, reset_limit=True):
        if reset_limit: self.current_limit = 10
        self.products_container.clear_widgets()
        
        subset = product_list[:self.current_limit]
        for p in subset:
            prix_val = float(p.get('prix', 0))
            card = ProductCard(
                name=p.get('nom', 'Produit'), prod_type=p.get('type', 'Divers'), 
                price=f"{prix_val:.2f}".replace('.', ','), image_url=p.get('image_url', ''), 
                description=p.get('description', ''), user_size=self.user_size
            )
            self.products_container.add_widget(card)
        
        if len(product_list) > self.current_limit:
            self.lbl_counter.text = f"{self.current_limit} / {len(product_list)} produits affichés"
            self.products_container.add_widget(self.lbl_counter)
            self.products_container.add_widget(self.btn_more)
        elif len(product_list) > 0:
            self.lbl_counter.text = f"{len(product_list)} / {len(product_list)} produits affichés"
            self.products_container.add_widget(self.lbl_counter)

    def load_more(self, *args):
        old_text = self.btn_more.text
        self.btn_more.text = "Chargement en cours..."
        self.btn_more.disabled = True
        
        def reset_btn(dt):
            self.btn_more.text = old_text
            self.btn_more.disabled = False
            
        self.current_limit += 10
        Clock.schedule_once(lambda dt: self.perform_load(), 0.1)
        Clock.schedule_once(reset_btn, 0.5)

    def perform_load(self):
        self.on_filter_change(self.filter, self.filter.text)

    def on_filter_change(self, spinner, text):
        if text == 'Tous les produits': filtered = self.all_products
        else: filtered = [p for p in self.all_products if p.get('type') == text]
        self.display_products(filtered, reset_limit=False)