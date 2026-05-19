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
from kivy.clock import Clock

# --- COMPOSANTS OPTIMISÉS POUR ÉVITER LES LEAKS DE MÉMOIRE (LAMBDA) ---
class StyledTabButton(Button):
    """Bouton d'onglet réutilisable avec gestion interne propre de son canvas."""
    def __init__(self, is_active, **kwargs):
        super().__init__(**kwargs)
        self.background_normal = ''
        self.background_color = (0, 0, 0, 0)
        
        with self.canvas.before:
            Color(*(0.97, 0.93, 0.25, 1) if is_active else (1, 1, 1, 0.15))
            self.bg_rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(8)])
        self.bind(pos=self._update_rect, size=self._update_rect)

    def _update_rect(self, instance, value):
        self.bg_rect.pos = instance.pos
        self.bg_rect.size = instance.size


class PlayerRowLayout(GridLayout):
    """Ligne de tableau optimisée gérant dynamiquement la couleur du capitaine."""
    def __init__(self, is_cap, **kwargs):
        super().__init__(**kwargs)
        with self.canvas.before:
            if is_cap:
                Color(0.97, 0.93, 0.25, 0.25)  # Jaune translucide pour le capitaine
            else:
                Color(1, 1, 1, 0.05)           # Ligne standard grise
            
            self.bg_rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(5)])
        self.bind(pos=self._update_rect, size=self._update_rect)

    def _update_rect(self, instance, value):
        self.bg_rect.pos = instance.pos
        self.bg_rect.size = instance.size


# --- CLASSE PRINCIPALE EFFECTIF ---
class EffectifScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.current_team_index = 0
        self.KIVY_BLUE = (30/255, 58/255, 138/255, 1)

        self.main_layout = BoxLayout(orientation="vertical")
        with self.main_layout.canvas.before:
            Color(*self.KIVY_BLUE)
            self.rect_bg = Rectangle(pos=self.main_layout.pos, size=self.main_layout.size)
        self.main_layout.bind(pos=self._update_bg, size=self._update_bg)

        # --- 1. SÉLECTEUR D'ÉQUIPE (STYLE PROPRE) ---
        self.team_scroll = ScrollView(
            size_hint=(1, None), 
            height=dp(85), 
            do_scroll_y=False,
            bar_width=0,
            scroll_type=['content']
        )
        self.team_selector = BoxLayout(size_hint_x=None, spacing=dp(10), padding=dp(10))
        self.team_selector.bind(minimum_width=self.team_selector.setter('width'))
        self.team_scroll.add_widget(self.team_selector)
        self.main_layout.add_widget(self.team_scroll)

        # 2. Zone de contenu pour le tableau
        self.table_area = BoxLayout(orientation="vertical", size_hint=(1, 1))
        self.main_layout.add_widget(self.table_area)
        
        self.add_widget(self.main_layout)

    def _update_bg(self, instance, value):
        self.rect_bg.pos = instance.pos
        self.rect_bg.size = instance.size

    def on_enter(self):
        self.update_ui_from_config()

    def update_ui_from_config(self, *args):
        app = App.get_running_app()
        f_factor = 24
        if hasattr(app, 'config'):
            try: f_factor = app.config.getint('User', 'font_size_factor')
            except: pass

        all_effectifs = app.app_config.get("fcvv", {}).get("appli", {}).get("effectifs", [])
        if not all_effectifs: 
            return

        self.team_selector.clear_widgets()
        for i, eff_data in enumerate(all_effectifs):
            is_active = (i == self.current_team_index)
            nom_equipe = eff_data.get("equipe_nom", "Équipe")
            
            btn_width = max(dp(160), dp(len(nom_equipe) * (f_factor * 0.7)))
            
            btn = StyledTabButton(
                is_active=is_active,
                text=nom_equipe,
                size_hint=(None, 1),
                width=btn_width,
                color=(0, 0, 0, 1) if is_active else (1, 1, 1, 1),
                bold=is_active, 
                font_size=f"{f_factor - 1}sp"
            )
            
            # Injection de l'index sans créer de closure lambda instable
            btn.target_index = i
            btn.bind(on_release=self._on_tab_pressed)
            self.team_selector.add_widget(btn)

        if self.current_team_index < len(all_effectifs):
            self.render_table(all_effectifs[self.current_team_index], f_factor)

    def _on_tab_pressed(self, instance):
        self.switch_team(instance.target_index)

    def switch_team(self, index):
        if self.current_team_index != index:
            self.current_team_index = index
            self.update_ui_from_config()

    def render_table(self, data, f_factor):
        self.table_area.clear_widgets()
        
        # --- AJOUT DU NOM DE L'ENTRAINEUR ---
        nom_coach = data.get("entraineur", "Non renseigné")
        coach_label = Label(
            text=f"Entraîneur : [b]{nom_coach}[/b]",
            markup=True,
            size_hint=(1, None),
            height=dp(40),
            font_size=f"{f_factor - 4}sp",
            color=(1, 1, 1, 0.9),
            halign="center"
        )
        self.table_area.add_widget(coach_label)

        # Scrollview principal du tableau
        main_scroll = ScrollView(
            size_hint=(1, 1), 
            do_scroll_x=True, 
            do_scroll_y=True,
            bar_width=0,
            scroll_type=['content']
        )
        
        # Définition des largeurs de colonnes de base
        base_widths = [45, 180, 110, 85, 40]
        adjusted_widths = [dp(w + (f_factor - 20) * 1.8) for w in base_widths]
        min_needed_width = sum(adjusted_widths)
        
        # Pour une réactivité mobile parfaite, on lie la largeur du tableau à la largeur réelle du layout parent
        total_table_width = max(min_needed_width, self.table_area.width if self.table_area.width > 0 else dp(320))
        
        if total_table_width > min_needed_width:
            adjusted_widths[1] += (total_table_width - min_needed_width)

        inner_table = BoxLayout(orientation="vertical", size_hint=(None, None), width=total_table_width)
        inner_table.bind(minimum_height=inner_table.setter('height'))

        # --- HEADER ---
        h_height = dp(45) + dp(f_factor - 20)
        header = GridLayout(cols=5, size_hint=(None, None), height=h_height, width=total_table_width)
        titles = ["N°", "Joueur", "Né(e) le", "Poste", ""]
        
        for i, title in enumerate(titles):
            header.add_widget(Label(
                text=title, bold=True, font_size=f"{f_factor - 6}sp",
                size_hint_x=None, width=adjusted_widths[i],
                color=(0.97, 0.93, 0.25, 1)
            ))
        inner_table.add_widget(header)

        # --- LISTE DES JOUEURS ---
        row_height = dp(50) + dp(f_factor - 20)
        for j in data.get("joueurs", []):
            is_cap = j.get("capitaine", False)
            
            # Utilisation de la structure graphique épurée sans fuite mémoire
            row = PlayerRowLayout(is_cap=is_cap, cols=5, size_hint=(None, None), height=row_height, width=total_table_width)

            # Colonne N°
            row.add_widget(Label(text=str(j.get("numero", "-")), size_hint_x=None, width=adjusted_widths[0], 
                                 font_size=f"{f_factor - 4}sp", color=(0.97, 0.93, 0.25, 1), bold=True))
            
            # Colonne Nom
            nom_complet = f"{j.get('nom', '').upper()} {j.get('prenom', '')}"
            l_nom = Label(text=nom_complet, size_hint_x=None, width=adjusted_widths[1], 
                          halign='left', valign='middle', font_size=f"{f_factor - 5}sp")
            
            # Liaison propre de la taille de texte à la cellule graphique
            l_nom.text_size = (adjusted_widths[1] - dp(10), row_height)
            row.add_widget(l_nom)
            
            # Colonne Naissance
            row.add_widget(Label(text=j.get("date_naissance", "-"), size_hint_x=None, width=adjusted_widths[2], 
                                 font_size=f"{f_factor - 7}sp"))
            
            # Colonne Poste
            row.add_widget(Label(text=j.get("poste", "-"), size_hint_x=None, width=adjusted_widths[3], 
                                 font_size=f"{f_factor - 8}sp", color=(0.8, 0.8, 0.8, 1)))

            # Colonne Capitaine
            cap_text = "[color=F7EC3F]©[/color]" if is_cap else ""
            row.add_widget(Label(text=cap_text, markup=True, size_hint_x=None, width=adjusted_widths[4], 
                                 font_size=f"{f_factor}sp", bold=True))

            inner_table.add_widget(row)

        main_scroll.add_widget(inner_table)
        self.table_area.add_widget(main_scroll)