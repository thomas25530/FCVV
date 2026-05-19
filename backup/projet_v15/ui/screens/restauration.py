# -*- coding: utf-8 -*-
import threading
import hashlib
import json
from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView
from kivy.clock import Clock
from kivy.app import App
from kivy.graphics import Color, Rectangle, RoundedRectangle
from kivy.metrics import dp
from kivy.uix.widget import Widget
from kivy.core.window import Window

class RestaurationScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.last_config_hash = None
        self._is_refreshing = False
        self.current_tab = "boissons" 
        self.KIVY_BLUE = (30/255, 58/255, 138/255, 1)
        self.YELLOW = (247/255, 236/255, 63/255, 1)
        
        with self.canvas.before:
            Color(*self.KIVY_BLUE)
            self.rect_bg = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._update_rect, size=self._update_rect)

        self.main_layout = BoxLayout(orientation='vertical')
        
        # 1. SÉLECTEUR D'ONGLETS
        self.tab_bar = BoxLayout(size_hint_y=None, height=dp(85), spacing=dp(10), padding=dp(10))
        self.main_layout.add_widget(self.tab_bar)

        # 2. ZONE DE CONTENU (avec bind pour Pull-to-refresh)
        # --- Dans votre __init__ ---
        # Remplacez la création du scroll par ceci :
        
        self.scroll = ScrollView(
            do_scroll_x=False,
            always_overscroll=True,  # Force l'effet de rebond même si le contenu est petit
            scroll_type=['content', 'bars'] # Améliore la réactivité sur mobile
        )
        self.scroll.bind(scroll_y=self._check_scroll_limit)
        
        self.content_layout = BoxLayout(orientation='vertical', padding=dp(20), spacing=dp(10), size_hint_y=None)
        self.content_layout.bind(minimum_height=self.content_layout.setter('height'))
        self.scroll.add_widget(self.content_layout)
        
        self.main_layout.add_widget(self.scroll)
        self.add_widget(self.main_layout)

    def _update_rect(self, instance, value):
        self.rect_bg.pos = instance.pos
        self.rect_bg.size = instance.size

    def _check_scroll_limit(self, instance, value):
        """Déclenche le refresh si on tire vers le bas (> 1.1)"""
        if value > 1.1 and not self._is_refreshing:
            self._is_refreshing = True
            app = App.get_running_app()
            if hasattr(app, 'load_remote_config'):
                threading.Thread(target=self._bg_refresh, args=(app,), daemon=True).start()

    def _bg_refresh(self, app):
        app.load_remote_config()
        # Petit délai pour laisser l'animation de l'utilisateur se terminer
        Clock.schedule_once(lambda dt: self.update_ui_from_config(), 0.5)

    def create_section_title(self, text, user_size):
        h_title = dp(50) + dp(user_size - 18)
        return Label(
            text=f"[b]{text.upper()}[/b]", 
            markup=True, font_size=f"{user_size + 2}sp", color=self.YELLOW,
            size_hint_y=None, height=h_title, halign='left', 
            text_size=(Window.width * 0.9, None)
        )

    def create_item_row(self, name, price, is_sold_out, deposit, user_size):
        app = App.get_running_app()
        tr = app._ if hasattr(app, '_') else lambda x: x
        has_deposit = deposit is not None and str(deposit).strip() not in ["", "0"]
        
        base_h = dp(65) if has_deposit else dp(45)
        h_row = base_h + dp(user_size - 18)
        
        row = BoxLayout(orientation='horizontal', size_hint_y=None, height=h_row, padding=[0, dp(5)])
        
        display_name = f"[b]{name}[/b]"
        if is_sold_out:
            display_name += f"   [color=ff0000]({tr('sold_out')})[/color]"
        if has_deposit:
            display_name += f"\n[size={int(user_size*0.8)}sp][color=aaaaaa]{tr('deposit')}: {deposit} Jtn[/color][/size]"
            
        name_label = Label(text=display_name, markup=True, font_size=f"{user_size}sp", halign='left', valign='top', size_hint_x=0.75)
        name_label.bind(size=lambda s, v: setattr(s, 'text_size', (v[0], v[1])))
        
        price_label = Label(text=f"{price} Jtn", markup=True, font_size=f"{user_size}sp", halign='right', valign='top', size_hint_x=0.25, color=(0.9, 0.9, 0.9, 1))
        price_label.bind(size=lambda s, v: setattr(s, 'text_size', (v[0], v[1])))
        
        row.add_widget(name_label)
        row.add_widget(price_label)
        return row

    def switch_tab(self, tab_name):
        if self.current_tab != tab_name:
            self.current_tab = tab_name
            self.update_ui_from_config()

    def on_enter(self):
        self.update_ui_from_config()

    def update_ui_from_config(self, *args):
        app = App.get_running_app()
        if not hasattr(app, 'app_config') or not app.app_config:
            self._is_refreshing = False
            return

        tr = app._ if hasattr(app, '_') else lambda x: x
        lang = app.config.get('User', 'langue') if hasattr(app, 'config') else 'Français'
        user_size = app.config.getint('User', 'font_size_factor', fallback=18) if hasattr(app, 'config') else 18

        # --- GESTION DU HASH ---
        # On hash la data + l'onglet + la langue + la taille de police
        restau_data = app.app_config.get("tournoi", {}).get("appli", {}).get("restauration", {})
        data_bundle = {
            "data": restau_data,
            "tab": self.current_tab,
            "lang": lang,
            "size": user_size
        }
        current_hash = hashlib.md5(json.dumps(data_bundle, sort_keys=True).encode()).hexdigest()

        if current_hash == self.last_config_hash and self.content_layout.children:
            self._is_refreshing = False
            return

        self.last_config_hash = current_hash

        # --- MISE À JOUR DES ONGLETS ---
        self.tab_bar.clear_widgets()
        tabs = [("boissons", tr("tab_boissons")), ("nourriture", tr("tab_nourriture"))]
        
        for tid, tlabel in tabs:
            is_active = (self.current_tab == tid)
            btn_width = max(dp(160), dp(len(tlabel) * (user_size * 0.75)))
            
            btn = Button(
                text=tlabel, size_hint=(None, 1), width=btn_width,
                background_normal='', background_color=(0, 0, 0, 0),
                color=(0, 0, 0, 1) if is_active else (1, 1, 1, 1),
                bold=is_active, font_size=f"{user_size}sp"
            )
            
            with btn.canvas.before:
                Color(*(0.97, 0.93, 0.25, 1) if is_active else (1, 1, 1, 0.15))
                btn.bg_rect = RoundedRectangle(pos=btn.pos, size=btn.size, radius=[dp(8)])
            
            btn.bind(pos=lambda inst, val: setattr(inst.bg_rect, 'pos', inst.pos),
                     size=lambda inst, val: setattr(inst.bg_rect, 'size', inst.size))
            
            btn.bind(on_release=lambda x, t=tid: self.switch_tab(t))
            self.tab_bar.add_widget(btn)

        # --- RECONSTRUCTION DU CONTENU ---
        self.content_layout.clear_widgets()

        def fill_section(section_title, items_list):
            if not items_list: return
            self.content_layout.add_widget(self.create_section_title(section_title, user_size))
            for item in items_list:
                name = item.get('nom_en') if lang == 'English' and 'nom_en' in item else item.get('nom', '???')
                self.content_layout.add_widget(self.create_item_row(
                    name, str(item.get("prix", "0")), item.get('epuise', False), item.get('consigne'), user_size
                ))
            self.content_layout.add_widget(Widget(size_hint_y=None, height=dp(15)))

        if self.current_tab == "boissons":
            b_data = restau_data.get("boissons", {})
            fill_section(tr("title_alcool"), b_data.get("avec_alcool", []))
            fill_section(tr("title_soft"), b_data.get("sans_alcool", []))
        else:
            n_data = restau_data.get("nourriture", {})
            fill_section(tr("title_sale"), n_data.get("sale", []))
            fill_section(tr("title_sucre"), n_data.get("sucre", []))
            
        self._is_refreshing = False