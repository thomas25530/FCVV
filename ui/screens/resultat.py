# -*- coding: utf-8 -*-
from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.graphics import Color, RoundedRectangle
from kivy.app import App
from kivy.metrics import dp
from kivy.core.window import Window
from kivy.clock import Clock
import json
import hashlib
import threading

# --- COMPOSANT LIGNE DE RÉSULTAT ---
class ResultRow(BoxLayout):
    def __init__(self, match_data, **kwargs):
        super().__init__(orientation="vertical", size_hint_y=None, padding=[dp(10), dp(5)], **kwargs)
        
        app = App.get_running_app()
        f_factor = app.config.getint('User', 'font_size_factor') if hasattr(app, 'config') else 20

        self.buteurs = match_data.get('buteurs', "")
        base_h = dp(60) if self.buteurs else dp(45)
        self.height = base_h + dp(f_factor - 18) * 2 

        issue = match_data.get('issue', 'N').upper()
        colors = {"V": (0.1, 0.8, 0.1, 1), "D": (0.8, 0.1, 0.1, 1), "N": (0.6, 0.6, 0.6, 1)}
        res_color = colors.get(issue, (1, 1, 1, 1))

        main_line = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(35) + dp(f_factor-20))
        
        teams_txt = f"{match_data.get('equipeA', '')} - {match_data.get('equipeB', '')}"
        main_line.add_widget(Label(
            text=teams_txt, halign='left', font_size=f"{f_factor - 2}sp",
            text_size=(Window.width * 0.55, None)
        ))

        score_txt = f"{match_data.get('scoreA', '0')} - {match_data.get('scoreB', '0')}"
        main_line.add_widget(Label(
            text=f"[b]{score_txt}[/b]", markup=True, size_hint_x=None, width=dp(70), 
            font_size=f"{f_factor}sp"
        ))

        main_line.add_widget(Label(
            text=issue, size_hint_x=None, width=dp(35), color=res_color, 
            bold=True, font_size=f"{f_factor}sp"
        ))

        self.add_widget(main_line)

        if self.buteurs:
            self.add_widget(Label(
                text=f"[i]({self.buteurs})[/i]", markup=True, color=(0.7, 0.7, 0.7, 1),
                font_size=f"{f_factor - 5}sp", halign='center',
                size_hint_y=None, height=dp(20) + dp(f_factor-20),
                text_size=(Window.width * 0.8, None)
            ))


# --- ÉCRAN DES RÉSULTATS ---
class ResultatScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.last_config_hash = None
        self._is_refreshing = False
        self.KIVY_BLUE = (30/255, 58/255, 138/255, 1)

        self.layout = BoxLayout(orientation="vertical")
        with self.layout.canvas.before:
            Color(*self.KIVY_BLUE)
            self.rect_bg = RoundedRectangle(pos=self.layout.pos, size=self.layout.size)
        self.layout.bind(pos=self._update_bg, size=self._update_bg)

        self.scroll = ScrollView(size_hint=(1, 1), do_scroll_x=False)
        self.container = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(10), padding=dp(15))
        self.container.bind(minimum_height=self.container.setter('height'))

        self.scroll.add_widget(self.container)
        self.layout.add_widget(self.scroll)
        self.add_widget(self.layout)

        # Bind pour le Pull-to-refresh
        self.scroll.bind(scroll_y=self._check_scroll_limit)

    def _update_bg(self, instance, value):
        self.rect_bg.pos = instance.pos
        self.rect_bg.size = instance.size

    def on_enter(self):
        self.update_ui_from_config()

    def _check_scroll_limit(self, instance, value):
        """Déclenche le refresh si on tire vers le bas"""
        if value > 1.08 and not self._is_refreshing:
            self._is_refreshing = True
            print("[RESULTATS] Refresh manuel lancé")
            app = App.get_running_app()
            if hasattr(app, 'load_remote_config'):
                threading.Thread(target=self._bg_refresh, args=(app,), daemon=True).start()

    def _bg_refresh(self, app):
        app.load_remote_config()
        # FIX FUITE MÉMOIRE : Remplacement du lambda instable par un callback nommé
        Clock.schedule_once(self._clock_ui_update, 0.5)

    def _clock_ui_update(self, dt):
        self.update_ui_from_config()

    def update_ui_from_config(self, *args):
        app = App.get_running_app()
        if not hasattr(app, "app_config") or not app.app_config:
            self._is_refreshing = False
            return

        # 1. RÉCUPÉRATION DATA & POLICE
        res_data = app.app_config.get("fcvv", {}).get("appli", {}).get("resultats", {})
        f_factor = 20
        if hasattr(app, 'config'):
            try: f_factor = app.config.getint('User', 'font_size_factor')
            except: pass

        # 2. VÉRIFICATION DU HASH
        data_str = json.dumps(res_data, sort_keys=True) + str(f_factor)
        current_hash = hashlib.md5(data_str.encode()).hexdigest()

        if current_hash == self.last_config_hash and self.container.children:
            self._is_refreshing = False
            return

        # 3. RECONSTRUCTION
        self.last_config_hash = current_hash

        # FIX FUITE MÉMOIRE : Nettoyage itératif en amont du clear_widgets pour casser les arbres de références
        for child in list(self.container.children):
            if isinstance(child, ResultRow):
                child.clear_widgets()
        self.container.clear_widgets()

        if not res_data:
            self._is_refreshing = False
            return

        # Date du weekend
        self.container.add_widget(Label(
            text=f"[b]WEEKEND DU {res_data.get('date_weekend', '').upper()}[/b]",
            markup=True, font_size=f"{f_factor + 4}sp", color=(0.97, 0.93, 0.25, 1),
            size_hint_y=None, height=dp(60)
        ))

        for cat in res_data.get("categories", []):
            self.container.add_widget(Label(
                text=f"[b]{cat.get('nom', '').upper()}[/b]", markup=True,
                font_size=f"{f_factor + 2}sp", size_hint_y=None, height=dp(45), 
                halign='left', text_size=(Window.width*0.9, None)
            ))

            for sub in cat.get("sous_categories", []):
                self.container.add_widget(Label(
                    text=f"  {sub.get('nom', '')}", color=(0.8, 0.8, 0.8, 1),
                    font_size=f"{f_factor - 2}sp",
                    size_hint_y=None, height=dp(30), halign='left', text_size=(Window.width*0.9, None)
                ))

                for match in sub.get("matchs", []):
                    self.container.add_widget(ResultRow(match))
                
                self.container.add_widget(BoxLayout(size_hint_y=None, height=dp(10)))
        
        self._is_refreshing = False