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

from kivy.uix.floatlayout import FloatLayout 
from kivy.uix.image import Image
from kivy.graphics import PushMatrix, PopMatrix, Rotate

# --- COMPOSANT LIGNE DE RÉSULTAT (Format 3 Colonnes Fixes avec Espacements Corrigés) ---
class ResultRow(BoxLayout):
    def __init__(self, match_data, **kwargs):
        super().__init__(orientation="vertical", size_hint_y=None, spacing=dp(5), padding=dp(15), **kwargs)
        
        app = App.get_running_app()
        f_factor = app.config.getint('User', 'font_size_factor') if hasattr(app, 'config') else 20
        
        size_small = f"{f_factor - 4}sp"
        size_large = f"{f_factor + 2}sp"
        
        self.buteurs = match_data.get('buteurs', "")
        
        base_h = dp(90) if self.buteurs else dp(70)
        self.height = base_h + dp(f_factor - 20) * 2

        # --- CADRE BLEU CLAIR ---
        with self.canvas.before:
            Color(1, 1, 1, 0.07) 
            self.bg_rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(10)])
        self.bind(pos=self._update_rect, size=self._update_rect)

        # --- RECALCUL DYNAMIQUE DE L'ISSUE ---
        try:
            scoreA = int(match_data.get('scoreA', 0))
            scoreB = int(match_data.get('scoreB', 0))
        except (ValueError, TypeError):
            scoreA, scoreB = 0, 0

        equipeA_nom = match_data.get('equipeA', '').upper()
        equipeB_nom = match_data.get('equipeB', '').upper()
        
        if scoreA > scoreB:
            res_brut = "V"
        elif scoreA < scoreB:
            res_brut = "D"
        else:
            res_brut = "N"

        fcvv_detecte_en_B = "FCVV" in equipeB_nom or "VALDAHON" in equipeB_nom or "VERCEL" in equipeB_nom
        
        if fcvv_detecte_en_B:
            if res_brut == "V": issue = "D"
            elif res_brut == "D": issue = "V"
            else: issue = "N"
        else:
            issue = res_brut

        colors = {"V": (0.1, 0.8, 0.1, 1), "D": (0.8, 0.1, 0.1, 1), "N": (0.6, 0.6, 0.6, 1)}
        res_color = colors.get(issue, (1, 1, 1, 1))

        # --- STRUCTURE PRINCIPALE EN 3 COLONNES DISTINCTES ---
        main_line = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(35) + dp(f_factor-20))
        
        # COLONNE 1 : Équipe A
        lbl_equipeA = Label(
            text=f"[b]{match_data.get('equipeA', '')}[/b]", 
            markup=True, 
            halign='right', 
            valign='middle',
            font_size=size_large,
            shorten=True,
            shorten_from='right',
            padding=[0, 0, dp(10), 0]  # <--- Correction ici : [gauche, haut, droite, bas]
        )
        self.bind(width=lambda inst, w: setattr(lbl_equipeA, 'text_size', (w * 0.36, None)))
        main_line.add_widget(lbl_equipeA)
        
        # COLONNE 2 : Le Score Central (Élargi à 80dp pour aérer)
        score_text = f"[color=F7EC3F]{scoreA}[/color] - [color=F7EC3F]{scoreB}[/color]"
        lbl_score = Label(
            text=f"[b]{score_text}[/b]",
            markup=True,
            size_hint_x=None,
            width=dp(80),
            font_size=size_large,
            halign='center',
            valign='middle'
        )
        lbl_score.bind(width=lambda inst, w: setattr(lbl_score, 'text_size', (w, None)))
        main_line.add_widget(lbl_score)
        
        # COLONNE 3 : Équipe B
        lbl_equipeB = Label(
            text=f"[b]{match_data.get('equipeB', '')}[/b]", 
            markup=True, 
            halign='left', 
            valign='middle',
            font_size=size_large,
            shorten=True,
            shorten_from='right',
            padding=[dp(10), 0, 0, 0]  # <--- Correction ici : [gauche, haut, droite, bas]
        )
        self.bind(width=lambda inst, w: setattr(lbl_equipeB, 'text_size', (w * 0.32, None)))
        main_line.add_widget(lbl_equipeB)
        
        # BLOC FINAL : L'issue (V/D/N)
        lbl_issue = Label(
            text=issue, 
            size_hint_x=None, 
            width=dp(35), 
            color=res_color, 
            bold=True, 
            font_size=f"{f_factor}sp", 
            halign='center', 
            valign='middle'
        )
        lbl_issue.bind(width=lambda inst, w: setattr(lbl_issue, 'text_size', (w, None)))
        main_line.add_widget(lbl_issue)
        
        self.add_widget(main_line)
        
        # Section des buteurs
        if self.buteurs:
            lbl_buteurs = Label(
                text=f"[i]({self.buteurs})[/i]", markup=True, color=(0.7, 0.7, 0.7, 1),
                font_size=size_small, halign='center', valign='middle',
                size_hint_y=None, height=dp(20) + dp(f_factor-20)
            )
            self.bind(width=lambda inst, w: setattr(lbl_buteurs, 'text_size', (w * 0.95, None)))
            self.add_widget(lbl_buteurs)

    def _update_rect(self, instance, value):
        self.bg_rect.pos = instance.pos
        self.bg_rect.size = instance.size


# --- ÉCRAN DES RÉSULTATS ---
class ResultatScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.last_config_hash = None
        self._is_refreshing = False
        self.KIVY_BLUE = (30/255, 58/255, 138/255, 1)
        
        self.main_layout = FloatLayout()
        self.add_widget(self.main_layout)
        
        self.layout = BoxLayout(orientation="vertical")
        with self.layout.canvas.before:
            Color(*self.KIVY_BLUE)
            self.rect_bg = RoundedRectangle(pos=self.layout.pos, size=self.layout.size)
        self.layout.bind(pos=self._update_bg, size=self._update_bg)
        self.main_layout.add_widget(self.layout)
        
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
        
        self.scroll = ScrollView(size_hint=(1, 1), do_scroll_x=False, bar_width=0, scroll_type=['content'])
        self.container = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(12), padding=[dp(15), dp(20)])
        self.container.bind(minimum_height=self.container.setter('height'))
        self.scroll.add_widget(self.container)
        self.layout.add_widget(self.scroll)
        self.scroll.bind(scroll_y=self._check_scroll_limit)

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
            self.show_loader(True)
            app = App.get_running_app()
            if hasattr(app, 'load_remote_config'):
                threading.Thread(target=self._bg_refresh, args=(app,), daemon=True).start()

    def _bg_refresh(self, app):
        app.load_remote_config()
        Clock.schedule_once(self._clock_ui_update, 0.5)

    def _clock_ui_update(self, dt):
        self.update_ui_from_config()
        self.show_loader(False)

    def _update_bg(self, instance, value):
        self.rect_bg.pos = instance.pos
        self.rect_bg.size = instance.size

    def on_enter(self):
        self.update_ui_from_config()

    def update_ui_from_config(self, *args):
        app = App.get_running_app()
        if not hasattr(app, "app_config") or not app.app_config:
            self._is_refreshing = False
            return
            
        appli_data = app.app_config.get("fcvv", {}).get("appli", {})
        res_data = appli_data.get("resultats", {})
        saison = appli_data.get("saison", {})
        
        f_factor = 20
        if hasattr(app, 'config'):
            try: f_factor = app.config.getint('User', 'font_size_factor')
            except: pass
            
        # 2. CALCUL DU HASH
        data_str = json.dumps({"r": res_data, "s": saison}, sort_keys=True) + str(f_factor)
        current_hash = hashlib.md5(data_str.encode()).hexdigest()
        
        # 3. VÉRIFICATION DU CHANGEMENT
        if current_hash == self.last_config_hash and self.container.children:
            self._is_refreshing = False
            return
            
        self.last_config_hash = current_hash 
        self.container.clear_widgets()
        
        # 4. RECONSTRUCTION AVEC FILTRAGE
        categories = res_data.get("categories", [])
        if not res_data or not categories:
            self._is_refreshing = False
            return
            
        # Titre Date du Weekend
        self.container.add_widget(Label(
            text=f"[b]WEEKEND DU {res_data.get('date_weekend', '').upper()}[/b]",
            markup=True, font_size=f"{f_factor + 6}sp", color=(0.97, 0.93, 0.25, 1),
            size_hint_y=None, height=dp(70)
        ))
        
        for cat in categories:
            # On pré-filtre les sous-catégories qui contiennent des matchs valides
            valid_subs = []
            for sub in cat.get("sous_categories", []):
                # Filtrage : On garde le match si equipeA, equipeB, scoreA et scoreB sont valides
                valid_matches = [
                    m for m in sub.get("matchs", []) 
                    if m.get("equipeA") and m.get("equipeB") and 
                    m.get("scoreA") is not None and m.get("scoreB") is not None
                ]
                
                if valid_matches:
                    sub_copy = sub.copy()
                    sub_copy['matchs'] = valid_matches
                    valid_subs.append(sub_copy)
            
            # Si aucune sous-catégorie n'est valide pour cette catégorie, on passe à la suivante
            if not valid_subs:
                continue

            # Affichage catégorie
            cat_lbl = Label(
                text=f"[b]{cat.get('nom', '').upper()}[/b]", markup=True,
                font_size=f"{f_factor + 4}sp", size_hint_y=None, height=dp(55), 
                halign='left', valign='middle'
            )
            cat_lbl.bind(width=lambda inst, w: setattr(inst, 'text_size', (w * 0.95, None)))
            self.container.add_widget(cat_lbl)
            
            # Affichage sous-catégories filtrées
            for sub in valid_subs:
                sub_lbl = Label(
                    text=f"Section {sub.get('nom', '')}", 
                    markup=True,
                    font_size=f"{f_factor - 2}sp",
                    color=(0.97, 0.93, 0.25, 1),
                    size_hint_y=None, height=dp(35), halign='left', valign='middle'
                )
                sub_lbl.bind(width=lambda inst, w: setattr(inst, 'text_size', (w * 0.95, None)))
                self.container.add_widget(sub_lbl)
                
                # Affichage des matchs filtrés
                for match in sub.get("matchs", []):
                    self.container.add_widget(ResultRow(match))
                
                self.container.add_widget(BoxLayout(size_hint_y=None, height=dp(15)))
                
        self._is_refreshing = False