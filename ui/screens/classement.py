# -*- coding: utf-8 -*-
from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView
from kivy.graphics import Color, RoundedRectangle, Rectangle
from kivy.app import App
from kivy.metrics import dp
from kivy.core.window import Window
from kivy.clock import Clock
import json
import hashlib
import threading

# --- SOUS-CLASSES GRAPHIQUES POUR ÉVITER LES LEAKS DE MÉMOIRE (LAMBDA) ---
class StyledTabButton(Button):
    """Bouton d'onglet optimisé avec gestion interne et propre de son canvas."""
    def __init__(self, is_active, **kwargs):
        super().__init__(**kwargs)
        self.background_normal = ''
        self.background_color = (0, 0, 0, 0)
        
        with self.canvas.before:
            self.bg_color = Color(*(0.97, 0.93, 0.25, 1) if is_active else (1, 1, 1, 0.15))
            self.bg_rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(8)])
        self.bind(pos=self._update_rect, size=self._update_rect)

    def _update_rect(self, instance, value):
        self.bg_rect.pos = instance.pos
        self.bg_rect.size = instance.size


class TableRowLayout(GridLayout):
    """Ligne de tableau optimisée évitant l'usage de lambda en boucle."""
    def __init__(self, is_club, **kwargs):
        super().__init__(**kwargs)
        with self.canvas.before:
            Color(*(0.97, 0.93, 0.25, 0.3) if is_club else (1, 1, 1, 0.05))
            self.bg_rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(3)])
        self.bind(pos=self._update_rect, size=self._update_rect)

    def _update_rect(self, instance, value):
        self.bg_rect.pos = instance.pos
        self.bg_rect.size = instance.size


# --- CLASSE PRINCIPALE CLASSEMENT ---
class ClassementScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.current_team_index = 0
        self.last_config_hash = None
        self._is_refreshing = False
        self.KIVY_BLUE = (30/255, 58/255, 138/255, 1)

        self.main_layout = BoxLayout(orientation="vertical")
        with self.main_layout.canvas.before:
            Color(*self.KIVY_BLUE)
            self.rect_bg = Rectangle(pos=self.main_layout.pos, size=self.main_layout.size)
        self.main_layout.bind(pos=self._update_bg, size=self._update_bg)

        # 1. Sélecteur d'équipe (Barre masquée, comportement fluide)
        self.team_scroll = ScrollView(
            size_hint=(1, None), height=dp(85), 
            do_scroll_y=False, bar_width=0, scroll_type=['content']
        )
        self.team_selector = BoxLayout(size_hint_x=None, spacing=dp(10), padding=dp(10))
        self.team_selector.bind(minimum_width=self.team_selector.setter('width'))
        self.team_scroll.add_widget(self.team_selector)
        self.main_layout.add_widget(self.team_scroll)

        # 2. Zone d'infos
        self.info_bar = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(35), padding=[dp(15), 0])
        self.main_layout.add_widget(self.info_bar)

        # 3. Zone Tableau
        self.table_area = BoxLayout(orientation="vertical", size_hint=(1, 1))
        self.main_layout.add_widget(self.table_area)
        
        self.add_widget(self.main_layout)

    def _update_bg(self, instance, value):
        self.rect_bg.pos = instance.pos
        self.rect_bg.size = instance.size

    def on_enter(self):
        self.update_ui_from_config()

    def _check_scroll_limit(self, instance, value):
        """Déclenche le rafraîchissement si on tire le tableau vers le bas"""
        if value > 1.05 and not self._is_refreshing:
            self._is_refreshing = True
            print("[CLASSEMENT] Pull-to-refresh détecté")
            app = App.get_running_app()
            if hasattr(app, 'load_remote_config'):
                threading.Thread(target=self._bg_refresh, args=(app,), daemon=True).start()

    def _bg_refresh(self, app):
        app.load_remote_config()
        # Sécurisation du fil d'exécution : Tout le traitement UI retourne sur le thread principal
        Clock.schedule_once(lambda dt: self._safe_ui_update(), 0.5)

    def _safe_ui_update(self):
        self.update_ui_from_config()
        self._is_refreshing = False  # Le verrou est libéré seulement après la reconstruction complète

    def update_ui_from_config(self, *args):
        app = App.get_running_app()
        if not hasattr(app, "app_config") or not app.app_config:
            return

        f_factor = 24
        if hasattr(app, 'config'):
            try: f_factor = app.config.getint('User', 'font_size_factor')
            except: pass

        all_classements = app.app_config.get("fcvv", {}).get("appli", {}).get("classements", [])
        if not all_classements: 
            return

        # --- GESTION DU HASH ---
        data_to_hash = {
            "data": all_classements,
            "team_idx": self.current_team_index,
            "font": f_factor
        }
        current_hash = hashlib.md5(json.dumps(data_to_hash, sort_keys=True).encode()).hexdigest()

        if current_hash == self.last_config_hash and self.team_selector.children:
            return

        self.last_config_hash = current_hash
        self.team_selector.clear_widgets()

        # Construction propre des onglets sans lambda anonymes orphelins
        for i, class_data in enumerate(all_classements):
            is_active = (i == self.current_team_index)
            nom_equipe = class_data.get("equipe_nom", "Équipe")
            btn_width = max(dp(160), dp(len(nom_equipe) * (f_factor * 0.7)))
            
            btn = StyledTabButton(
                is_active=is_active,
                text=nom_equipe, size_hint=(None, 1), width=btn_width,
                color=(0, 0, 0, 1) if is_active else (1, 1, 1, 1),
                bold=is_active, font_size=f"{f_factor - 1}sp"
            )
            
            # Injection propre de l'index dans le callback d'action
            btn.target_index = i
            btn.bind(on_release=self._on_tab_pressed)
            self.team_selector.add_widget(btn)

        if self.current_team_index < len(all_classements):
            self.render_table(all_classements[self.current_team_index], f_factor)

    def _on_tab_pressed(self, instance):
        self.switch_team(instance.target_index)

    def switch_team(self, index):
        if self.current_team_index != index:
            self.current_team_index = index
            self.update_ui_from_config()

    def render_table(self, data, f_factor):
        self.info_bar.clear_widgets()
        txt_info = f"[b]{data.get('journee', '-')}[/b]  •  MAJ : {data.get('maj', '-')}"
        self.info_bar.add_widget(Label(text=txt_info, markup=True, font_size=f"{f_factor - 5}sp"))

        self.table_area.clear_widgets()
        
        # Masquage de la scrollbar sur mobile pour un rendu plus épuré
        main_scroll = ScrollView(
            size_hint=(1, 1), do_scroll_x=True, do_scroll_y=True,
            bar_width=0, scroll_type=['content']
        )
        main_scroll.bind(scroll_y=self._check_scroll_limit)
        
        col_widths_dp = [40, 180, 45, 35, 35, 35, 35, 35, 40, 40, 35, 45]
        adjusted_widths = [dp(w + (f_factor - 20) * 1.5) for w in col_widths_dp]
        min_table_width = sum(adjusted_widths)

        inner_table = BoxLayout(orientation="vertical", size_hint=(None, None), width=min_table_width)
        inner_table.bind(minimum_height=inner_table.setter('height'))

        # Header
        h_height = dp(45) + dp(f_factor - 20)
        header = GridLayout(cols=12, size_hint=(None, None), height=h_height, width=min_table_width)
        titles = ["Rg", "Equipe", "Pts", "J", "G", "N", "P", "F", "Bp", "Bc", "Pé", "Diff"]
        for i, title in enumerate(titles):
            header.add_widget(Label(
                text=title, bold=True, font_size=f"{f_factor - 7}sp",
                size_hint=(None, None), width=adjusted_widths[i], height=h_height,
                color=(0.97, 0.93, 0.25, 1), halign='center', valign='middle',
                text_size=(adjusted_widths[i], h_height)
            ))
        inner_table.add_widget(header)

        # Lignes (Utilisation du composant de nettoyage TableRowLayout)
        row_height = dp(40) + dp(f_factor - 20)
        for entry in data.get("tableau", []):
            nom_equipe = entry.get("equipe", "")
            is_club = "Vercel" in nom_equipe or "FCVV" in nom_equipe
            
            row = TableRowLayout(is_club=is_club, cols=12, size_hint=(None, None), height=row_height, width=min_table_width)

            fields = ["rang", "equipe", "pts", "j", "g", "n", "p", "f", "bp", "bc", "pe", "diff"]
            for i, field in enumerate(fields):
                valeur = str(entry.get(field, "0"))
                lbl = Label(
                    text=valeur, font_size=f"{f_factor - 7}sp",
                    size_hint=(None, None), width=adjusted_widths[i], height=row_height,
                    color=(1, 1, 0.6, 1) if is_club else (1, 1, 1, 1),
                    bold=is_club, halign='left' if field == "equipe" else 'center',
                    valign='middle', shorten=(field == "equipe"),
                    shorten_from='right', padding=(dp(8), 0)
                )
                lbl.text_size = (adjusted_widths[i], row_height)
                row.add_widget(lbl)
            inner_table.add_widget(row)

        main_scroll.add_widget(inner_table)
        self.table_area.add_widget(main_scroll)