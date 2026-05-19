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

# --- COMPOSANT "CARTE DE MATCH" ---
class MatchCard(BoxLayout):
    def __init__(self, match_data, **kwargs):
        super().__init__(orientation="vertical", size_hint_y=None, spacing=dp(5), padding=dp(15), **kwargs)
        
        # --- RÉCUPÉRATION DYNAMIQUE DE LA POLICE ---
        app = App.get_running_app()
        f_factor = 20 # Valeur par défaut
        if hasattr(app, 'config'):
            f_factor = app.config.getint('User', 'font_size_factor')

        # Calcul des tailles proportionnelles
        size_small = f"{f_factor - 4}sp"
        size_medium = f"{f_factor}sp"
        size_large = f"{f_factor + 2}sp"

        # Ajustement de la hauteur de la carte selon la police
        self.height = dp(130) # Augmenté de 115 à 130 pour le confort
        
        with self.canvas.before:
            Color(1, 1, 1, 0.07) 
            self.bg_rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(10)])
        self.bind(pos=self._update_rect, size=self._update_rect)

        # 1. Niveau et Date/Heure
        info = f"[color=F7EC3F][b]{match_data.get('niveau', '')}[/b][/color]  •  {match_data.get('date', '')} à {match_data.get('heure', '')}"
        self.add_widget(Label(
            text=info, markup=True, font_size=size_small, size_hint_y=None, height=dp(25), 
            halign='left', text_size=(Window.width * 0.85, None)
        ))

        # 2. Le Match
        teams = f"{match_data.get('equipeA', '')}   [color=888888]vs[/color]   {match_data.get('equipeB', '')}"
        self.add_widget(Label(
            text=f"[b]{teams}[/b]", markup=True, font_size=size_large, size_hint_y=None, 
            height=dp(35), halign='center'
        ))

        # 3. Le Lieu
        self.add_widget(Label(
            text=f"[i]{match_data.get('lieu', '')}[/i]", markup=True, color=(0.7, 0.7, 0.7, 1), 
            font_size=size_small, size_hint_y=None, height=dp(25), 
            halign='left', text_size=(Window.width * 0.85, None)
        ))

    def _update_rect(self, instance, value):
        self.bg_rect.pos = instance.pos
        self.bg_rect.size = instance.size

# --- CLASSE PRINCIPALE AGENDA ---
class AgendaScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.last_config_hash = None
        self.KIVY_BLUE = (30/255, 58/255, 138/255, 1)

        # Layout de base
        self.layout = BoxLayout(orientation="vertical")
        with self.layout.canvas.before:
            Color(*self.KIVY_BLUE)
            self.rect_bg = RoundedRectangle(pos=self.layout.pos, size=self.layout.size)
        self.layout.bind(pos=self._update_bg, size=self._update_bg)

        # Zone de défilement
        self.scroll = ScrollView(size_hint=(1, 1), do_scroll_x=False)
        self.container = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(12), padding=[dp(15), dp(20)])
        self.container.bind(minimum_height=self.container.setter('height'))

        self.scroll.add_widget(self.container)
        self.layout.add_widget(self.scroll)
        self.add_widget(self.layout)
        
        self.scroll.bind(scroll_y=self._check_scroll_limit)

    def _update_bg(self, instance, value):
        self.rect_bg.pos = instance.pos
        self.rect_bg.size = instance.size

    def on_enter(self):
        """Rafraîchit l'affichage à chaque fois qu'on arrive sur l'onglet"""
        self.update_ui_from_config()

    def _check_scroll_limit(self, instance, value):
        # On affiche la valeur pour débugger
        # print(f"Valeur scroll_y: {value}") 
        
        if value > 1.05: # Plus sensible que 1.1
            # On vérifie si on n'est pas déjà en train de rafraîchir 
            # pour éviter de lancer 50 threads d'un coup
            if not hasattr(self, '_is_refreshing') or not self._is_refreshing:
                self._is_refreshing = True
                print("[AGENDA] Pull-to-refresh détecté !")
                self.manual_refresh()
    
    def manual_refresh(self):
        app = App.get_running_app()
        if hasattr(app, 'load_remote_config'):
            def run_refresh():
                app.load_remote_config()
                Clock.schedule_once(lambda dt: self.finish_refresh(), 0.5)
            
            threading.Thread(target=run_refresh, daemon=True).start()
    
    def finish_refresh(self):
        self.update_ui_from_config()
        self._is_refreshing = False # On libère le verrou

    def update_ui_from_config(self, *args):
        app = App.get_running_app()
        if not hasattr(app, "app_config") or not app.app_config:
            return

        # 1. RÉCUPÉRATION DES DONNÉES
        fcvv_data = app.app_config.get("fcvv", {})
        agenda_data = fcvv_data.get("appli", {}).get("agenda", {})

        # 2. CALCUL DU HASH (Contenu + Facteur de police)
        # On inclut la police dans le hash pour forcer le refresh si elle change
        f_factor = 20
        if hasattr(app, 'config') and app.config.has_section('User'):
            try: f_factor = app.config.getint('User', 'font_size_factor')
            except: pass

        data_str = json.dumps(agenda_data, sort_keys=True) + str(f_factor)
        current_hash = hashlib.md5(data_str.encode()).hexdigest()

        # 3. VÉRIFICATION DU CHANGEMENT
        # Si le hash est le même et qu'on a déjà des widgets, on ne fait rien
        if current_hash == self.last_config_hash and self.container.children:
            print("[AGENDA] Hash identique, pas de reconstruction.")
            return False

        print("[AGENDA] Changement détecté ou premier chargement : Reconstruction...")
        self.last_config_hash = current_hash

        # 4. RECONSTRUCTION DE L'INTERFACE
        self.container.clear_widgets()

        if not agenda_data:
            self.container.add_widget(Label(
                text="Aucun match programmé", 
                color=(1, 1, 1, 0.5), 
                font_size=f"{f_factor}sp",
                size_hint_y=None, height=dp(100)
            ))
            return True

        # Titre Date du Weekend
        self.container.add_widget(Label(
            text=f"[b]{agenda_data.get('date_weekend', '').upper()}[/b]",
            markup=True, 
            font_size=f"{f_factor + 6}sp", 
            color=(0.97, 0.93, 0.25, 1),
            size_hint_y=None, height=dp(70)
        ))

        # Boucle sur les Catégories
        for cat in agenda_data.get("categories", []):
            self.container.add_widget(Label(
                text=f"[b]{cat.get('nom', '').upper()}[/b]", 
                markup=True,
                font_size=f"{f_factor + 4}sp", 
                size_hint_y=None, height=dp(55), 
                halign='left', text_size=(Window.width * 0.9, None)
            ))

            # Boucle sur les Sous-Catégories
            for sub in cat.get("sous_categories", []):
                self.container.add_widget(Label(
                    text=f"[color=CCCCCC]Section {sub.get('nom', '')}[/color]", 
                    markup=True,
                    font_size=f"{f_factor - 2}sp", 
                    size_hint_y=None, height=dp(35), 
                    halign='left', text_size=(Window.width * 0.9, None)
                ))

                # Affichage des Matchs
                for match in sub.get("matchs", []):
                    self.container.add_widget(MatchCard(match_data=match))
                
                # Espace de respiration
                self.container.add_widget(BoxLayout(size_hint_y=None, height=dp(15)))

        return True