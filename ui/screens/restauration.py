# -*- coding: utf-8 -*-
import threading
import hashlib
import json
from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView
from kivy.uix.image import Image
from kivy.clock import Clock
from kivy.app import App
from kivy.graphics import Color, Rectangle, RoundedRectangle, PushMatrix, PopMatrix, Rotate
from kivy.metrics import dp
from kivy.uix.widget import Widget
from kivy.core.window import Window

class RestaurationScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.last_config_hash = None
        self._is_refreshing = False
        self._is_updating = False  # VERROU POUR STOPPER LA BOUCLE
        self.current_tab = "boissons" 
        self.KIVY_BLUE = (30/255, 58/255, 138/255, 1)
        self.YELLOW = (247/255, 236/255, 63/255, 1)
        
        with self.canvas.before:
            Color(*self.KIVY_BLUE)
            self.rect_bg = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._update_rect, size=self._update_rect)

        self.root_layout = FloatLayout()
        self.add_widget(self.root_layout)

        self.main_layout = BoxLayout(orientation='vertical')
        self.root_layout.add_widget(self.main_layout)
        
        self.tab_bar = BoxLayout(size_hint_y=None, height=dp(85), spacing=dp(10), padding=dp(10))
        self.main_layout.add_widget(self.tab_bar)

        self.scroll = ScrollView(do_scroll_x=False, bar_width=0, always_overscroll=True, scroll_type=['content', 'bars'])
        self.scroll.bind(scroll_y=self._check_scroll_limit)
        
        self.content_layout = BoxLayout(orientation='vertical', padding=dp(20), spacing=dp(10), size_hint_y=None)
        
        # On lie la hauteur au contenu, mais on protège contre les boucles
        self.content_layout.bind(minimum_height=self._safe_update_height)
        
        self.scroll.add_widget(self.content_layout)
        self.main_layout.add_widget(self.scroll)

        self.main_loader = Image(source="assets/icons/loading_wheel.png", size_hint=(None, None), size=(dp(50), dp(50)), pos_hint={'center_x': 0.5, 'top': 0.85}, opacity=0)
        with self.main_loader.canvas.before:
            PushMatrix()
            self.main_rot = Rotate(angle=0)
        with self.main_loader.canvas.after:
            PopMatrix()
        self.main_loader.bind(center=lambda inst, val: setattr(self.main_rot, 'origin', inst.center))
        self.root_layout.add_widget(self.main_loader)

    def _safe_update_height(self, instance, value):
        """ Force la hauteur pour le scroll sans redéclencher d'événements inutiles """
        min_required = self.scroll.height + dp(10)
        new_height = max(value, min_required)
        if self.content_layout.height != new_height:
            self.content_layout.height = new_height

    def _update_rect(self, instance, value):
        self.rect_bg.pos = instance.pos
        self.rect_bg.size = instance.size

    def _update_btn_rect(self, instance, value):
        if hasattr(instance, 'bg_rect'):
            instance.bg_rect.pos = instance.pos
            instance.bg_rect.size = instance.size

    def _update_label_text_size(self, instance, value):
        instance.text_size = (value[0], value[1])

    def _rotate_loader(self, dt):
        self.main_rot.angle -= 6

    def show_loader(self, show):
        if show:
            self.main_loader.opacity = 1
            Clock.unschedule(self._rotate_loader)
            Clock.schedule_interval(self._rotate_loader, 1/60)
        else:
            self.main_loader.opacity = 0
            Clock.unschedule(self._rotate_loader)

    def _check_scroll_limit(self, instance, value):
        if value > 1.05 and not self._is_refreshing:
            self._is_refreshing = True
            self.manual_refresh()

    def manual_refresh(self):
        self.show_loader(True)
        app = App.get_running_app()
        if hasattr(app, 'load_remote_config'):
            def run_refresh():
                app.load_remote_config()
                Clock.schedule_once(lambda dt: self.finish_refresh(), 0.5)
            threading.Thread(target=run_refresh, daemon=True).start()
        else:
            self.finish_refresh()

    def finish_refresh(self):
        self.update_ui_from_config()
        self.show_loader(False)
        self._is_refreshing = False
        self.scroll.scroll_y = 1.0

    def create_section_title(self, text, user_size):
        return Label(text=f"[b]{text.upper()}[/b]", markup=True, font_size=f"{user_size + 2}sp", color=self.YELLOW,
                     size_hint_y=None, height=dp(50) + dp(user_size - 18), halign='left', text_size=(Window.width * 0.9, None))

    def create_item_row(self, name, price, is_sold_out, deposit, user_size):
        app = App.get_running_app()
        tr = app._ if hasattr(app, '_') else lambda x: x
        has_deposit = deposit is not None and str(deposit).strip() not in ["", "0"]
        row = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(65 if has_deposit else 45) + dp(user_size - 18), padding=[0, dp(5)])
        
        display = f"[b]{name}[/b]" + (f"    [color=ff0000]({tr('sold_out')})[/color]" if is_sold_out else "")
        if has_deposit: display += f"\n[size={int(user_size*0.8)}sp][color=aaaaaa]{tr('deposit')}: {deposit} Jtn[/color][/size]"
            
        l1 = Label(text=display, markup=True, font_size=f"{user_size}sp", halign='left', valign='top', size_hint_x=0.75)
        l1.bind(size=self._update_label_text_size)
        l2 = Label(text=f"{price} Jtn", markup=True, font_size=f"{user_size}sp", halign='right', valign='top', size_hint_x=0.25, color=(0.9, 0.9, 0.9, 1))
        l2.bind(size=self._update_label_text_size)
        row.add_widget(l1); row.add_widget(l2)
        return row

    def switch_tab(self, tab_name):
        if self.current_tab != tab_name:
            self.current_tab = tab_name
            self.update_ui_from_config()

    def on_enter(self):
        self.update_ui_from_config()

    def update_ui_from_config(self, *args):
        if self._is_updating: return
        self._is_updating = True 
        
        app = App.get_running_app()
        if not hasattr(app, 'app_config') or not app.app_config:
            self._is_updating = False
            return

        tr = app._ if hasattr(app, '_') else lambda x: x
        lang = app.config.get('User', 'langue') if hasattr(app, 'config') else 'Francais'
        user_size = app.config.getint('User', 'font_size_factor', fallback=18) if hasattr(app, 'config') else 18
        restau_data = app.app_config.get("tournoi", {}).get("appli", {}).get("restauration", {})
        
        current_hash = hashlib.md5(json.dumps({"d": restau_data, "t": self.current_tab, "l": lang, "s": user_size}, sort_keys=True).encode()).hexdigest()
        if current_hash == self.last_config_hash:
            self._is_updating = False
            return
        self.last_config_hash = current_hash

        for btn in self.tab_bar.children: btn.unbind(pos=self._update_btn_rect, size=self._update_btn_rect)
        self.tab_bar.clear_widgets()
        for child in self.content_layout.children:
            if isinstance(child, BoxLayout):
                for rc in child.children: rc.unbind(size=self._update_label_text_size)
        self.content_layout.clear_widgets()

        # Construction onglets
        for tid, tlabel in [("boissons", tr("tab_boissons")), ("nourriture", tr("tab_nourriture"))]:
            is_active = (self.current_tab == tid)
            btn = Button(text=tlabel, size_hint=(None, 1), width=max(dp(160), dp(len(tlabel)*(user_size*0.75))), background_normal='', background_color=(0,0,0,0), color=(0,0,0,1) if is_active else (1,1,1,1), bold=is_active, font_size=f"{user_size}sp")
            with btn.canvas.before:
                Color(*(0.97, 0.93, 0.25, 1) if is_active else (1, 1, 1, 0.15))
                btn.bg_rect = RoundedRectangle(pos=btn.pos, size=btn.size, radius=[dp(8)])
            btn.bind(pos=self._update_btn_rect, size=self._update_btn_rect, on_release=lambda x, t=tid: self.switch_tab(t))
            self.tab_bar.add_widget(btn)

        # Construction sections
        def fill(title, items):
            if not items: return
            self.content_layout.add_widget(self.create_section_title(title, user_size))
            for i in items:
                name = i.get('nom_en') if lang == 'English' and 'nom_en' in i else i.get('nom', '???')
                self.content_layout.add_widget(self.create_item_row(name, str(i.get("prix", "0")), i.get('epuise', False), i.get('consigne'), user_size))
            self.content_layout.add_widget(Widget(size_hint_y=None, height=dp(15)))

        d = restau_data.get("boissons" if self.current_tab=="boissons" else "nourriture", {})
        
        # DÉFINITION DE LA LISTE KEYS ICI
        keys = ["avec_alcool", "sans_alcool"] if self.current_tab == "boissons" else ["sale", "sucre"]
        
        map_titres = {
            "avec_alcool": "title_alcool",
            "sans_alcool": "title_soft",
            "sale": "title_sale",
            "sucre": "title_sucre"
        }
        
        for k in keys:
            cle_trad = map_titres.get(k, f"title_{k}") 
            fill(tr(cle_trad), d.get(k, []))
        
        self.content_layout.add_widget(Widget(size_hint_y=1))
        self._is_updating = False