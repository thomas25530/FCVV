# -*- coding: utf-8 -*-
from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.graphics import Color, RoundedRectangle
from kivy.app import App
from kivy.metrics import dp
from kivy.clock import Clock
import json
import hashlib
import threading
from kivy.uix.image import Image
from kivy.graphics import PushMatrix, PopMatrix, Rotate
from kivy.uix.floatlayout import FloatLayout

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
        size_large = f"{f_factor + 2}sp"
        # Ajustement de la hauteur de la carte selon la police
        self.height = dp(130) 
        with self.canvas.before:
            Color(1, 1, 1, 0.07) 
            self.bg_rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(10)])
        self.bind(pos=self._update_rect, size=self._update_rect)
        # 1. Niveau et Date/Heure
        info = f"[color=F7EC3F][b]{match_data.get('niveau', '')}[/b][/color]  •  {match_data.get('date', '')} à {match_data.get('heure', '')}"
        lbl_info = Label(
            text=info, markup=True, font_size=size_small, size_hint_y=None, height=dp(25), 
            halign='left'
        )
        # Liaison dynamique à la largeur de la carte plutôt qu'à la fenêtre globale (Évite les coupures)
        self.bind(width=lambda s, w: setattr(lbl_info, 'text_size', (w * 0.95, None)))
        self.add_widget(lbl_info)
        # 2. Le Match
        teams = f"{match_data.get('equipeA', '')}   [color=888888]vs[/color]   {match_data.get('equipeB', '')}"
        self.add_widget(Label(
            text=f"[b]{teams}[/b]", markup=True, font_size=size_large, size_hint_y=None, 
            height=dp(35), halign='center'
        ))
        # 3. Le Lieu
        lbl_lieu = Label(
            text=f"[i]{match_data.get('lieu', '')}[/i]", markup=True, color=(0.7, 0.7, 0.7, 1), 
            font_size=size_small, size_hint_y=None, height=dp(25), 
            halign='left'
        )
        self.bind(width=lambda s, w: setattr(lbl_lieu, 'text_size', (w * 0.95, None)))
        self.add_widget(lbl_lieu)
        
    def _update_rect(self, instance, value):
        self.bg_rect.pos = instance.pos
        self.bg_rect.size = instance.size

# --- CLASSE PRINCIPALE AGENDA ---
class AgendaScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.last_config_hash = None
        self.KIVY_BLUE = (30/255, 58/255, 138/255, 1)
        # 1. Conteneur principal (FloatLayout pour permettre la superposition)
        self.main_layout = FloatLayout()
        self.add_widget(self.main_layout)
        # 2. Layout de base (le fond bleu)
        self.layout = BoxLayout(orientation="vertical")
        with self.layout.canvas.before:
            Color(*self.KIVY_BLUE)
            self.rect_bg = RoundedRectangle(pos=self.layout.pos, size=self.layout.size)
        self.layout.bind(pos=self._update_bg, size=self._update_bg)
        self.main_layout.add_widget(self.layout)
        # 3. Zone de défilement
        self.scroll = ScrollView(
            size_hint=(1, 1), 
            do_scroll_x=False,
            bar_width=0,
            scroll_type=['content']
        )
        self.container = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(12), padding=[dp(15), dp(20)])
        self.container.bind(minimum_height=self.container.setter('height'))
        self.scroll.add_widget(self.container)
        self.layout.add_widget(self.scroll)
        # 4. LOADER (Ajouté en dernier au main_layout pour être au-dessus du fond bleu)
        self.main_loader = Image(
            source="assets/icons/loading_wheel.png", 
            size_hint=(None, None),
            size=(dp(50), dp(50)), 
            pos_hint={'center_x': 0.5, 'top': 0.8}, 
            opacity=0
        )
        with self.main_loader.canvas.before:
            PushMatrix()
            self.main_rot = Rotate(angle=0)
        with self.main_loader.canvas.after:
            PopMatrix()
        self.main_loader.bind(center=lambda inst, val: setattr(self.main_rot, 'origin', inst.center))
        self.main_layout.add_widget(self.main_loader)
        self.scroll.bind(scroll_y=self._check_scroll_limit)

    def _update_bg(self, instance, value):
        self.rect_bg.pos = instance.pos
        self.rect_bg.size = instance.size
    
    def _rotate_loader(self, dt):
        self.main_rot.angle -= 6 # Vitesse de rotation

    def show_loader(self, show):
        if show:
            self.main_loader.opacity = 1
            Clock.unschedule(self._rotate_loader)
            Clock.schedule_interval(self._rotate_loader, 1/60)
        else:
            self.main_loader.opacity = 0
            Clock.unschedule(self._rotate_loader)

    def on_enter(self):
        """Rafraîchit l'affichage à chaque fois qu'on arrive sur l'onglet"""
        self.update_ui_from_config()

    def _check_scroll_limit(self, instance, value):
        # Sur mobile, un étirement (over-scroll) vers le haut pousse la valeur au-dessus de 1.0
        if value > 1.05: 
            if not hasattr(self, '_is_refreshing') or not self._is_refreshing:
                self._is_refreshing = True
                print("[AGENDA] Pull-to-refresh detecte !")
                self.manual_refresh()
    
    def manual_refresh(self):
        self.show_loader(True) # Affiche la roue
        app = App.get_running_app()
        if hasattr(app, 'load_remote_config'):
            def run_refresh():
                app.load_remote_config()
                Clock.schedule_once(lambda dt: self.finish_refresh(), 0.5)
            threading.Thread(target=run_refresh, daemon=True).start()
    
    def finish_refresh(self):
        self.update_ui_from_config()
        self.show_loader(False) # Masque la roue
        self._is_refreshing = False

    def update_ui_from_config(self, *args):
        app = App.get_running_app()
        if not hasattr(app, "app_config") or not app.app_config:
            return

        # 1. RÉCUPÉRATION DATA
        fcvv_data = app.app_config.get("fcvv", {})
        appli_data = fcvv_data.get("appli", {})
        agenda_data = appli_data.get("agenda", {})
        saison = appli_data.get("saison", {})
        
        f_factor = 20
        if hasattr(app, 'config') and app.config.has_section('User'):
            try: f_factor = app.config.getint('User', 'font_size_factor')
            except: pass

        # 2. CALCUL DU HASH
        data_str = json.dumps({"a": agenda_data, "s": saison}, sort_keys=True) + str(f_factor)
        current_hash = hashlib.md5(data_str.encode()).hexdigest()

        # 3. VÉRIFICATION DU CHANGEMENT
        if current_hash == self.last_config_hash and self.container.children:
            return False

        self.last_config_hash = current_hash
        self.container.clear_widgets()

        # 4. RECONSTRUCTION AVEC FILTRAGE DES DONNÉES VIDES
        categories = agenda_data.get("categories", [])
        if not agenda_data or not categories:
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
            markup=True, font_size=f"{f_factor + 6}sp", 
            color=(0.97, 0.93, 0.25, 1),
            size_hint_y=None, height=dp(70)
        ))

        # Boucle sur les Catégories
        for cat in categories:
            # On récupère les sous-catégories valides uniquement
            valid_subs = []
            for sub in cat.get("sous_categories", []):
                # On filtre les matchs : on garde seulement ceux qui ont A et B
                valid_matches = [m for m in sub.get("matchs", []) 
                                if m.get("equipeA") and m.get("equipeB")]
                
                if valid_matches:
                    sub['valid_matches'] = valid_matches
                    valid_subs.append(sub)
            
            # Si aucune sous-catégorie n'a de matchs valides, on ignore cette catégorie
            if not valid_subs:
                continue

            # Ajout du label Catégorie
            cat_lbl = Label(
                text=f"[b]{cat.get('nom', '').upper()}[/b]", 
                markup=True, font_size=f"{f_factor + 4}sp", 
                size_hint_y=None, height=dp(55), halign='left', valign='middle'
            )
            cat_lbl.bind(width=lambda inst, w: setattr(inst, 'text_size', (w * 0.95, None)))
            self.container.add_widget(cat_lbl)

            # Boucle sur les Sous-Catégories filtrées
            for sub in valid_subs:
                sub_lbl = Label(
                    text=f"Section {sub.get('nom', '')}", 
                    markup=True, font_size=f"{f_factor - 2}sp", 
                    color=(0.97, 0.93, 0.25, 1),
                    size_hint_y=None, height=dp(35), halign='left', valign='middle'
                )
                sub_lbl.bind(width=lambda inst, w: setattr(inst, 'text_size', (w * 0.95, None)))
                self.container.add_widget(sub_lbl)

                # Affichage des Matchs filtrés
                for match in sub['valid_matches']:
                    self.container.add_widget(MatchCard(match_data=match))
                
                self.container.add_widget(BoxLayout(size_hint_y=None, height=dp(15)))
        
        return True