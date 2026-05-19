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

        # --- 1. SÉLECTEUR D'ÉQUIPE (STYLE HARMONISÉ) ---
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
        if not all_effectifs: return

        self.team_selector.clear_widgets()
        for i, eff_data in enumerate(all_effectifs):
            is_active = (i == self.current_team_index)
            nom_equipe = eff_data.get("equipe_nom", "Équipe")
            
            # Calcul de largeur dynamique identique aux autres écrans
            btn_width = max(dp(160), dp(len(nom_equipe) * (f_factor * 0.7)))
            
            btn = Button(
                text=nom_equipe,
                size_hint=(None, 1),
                width=btn_width,
                background_normal='',
                background_color=(0, 0, 0, 0), # Transparent
                color=(0, 0, 0, 1) if is_active else (1, 1, 1, 1),
                bold=is_active, 
                font_size=f"{f_factor - 1}sp"
            )
            
            with btn.canvas.before:
                Color(*(0.97, 0.93, 0.25, 1) if is_active else (1, 1, 1, 0.15))
                btn.bg_rect = RoundedRectangle(pos=btn.pos, size=btn.size, radius=[dp(8)])
            
            btn.bind(pos=lambda inst, val: setattr(inst.bg_rect, 'pos', inst.pos),
                     size=lambda inst, val: setattr(inst.bg_rect, 'size', inst.size))

            btn.bind(on_release=lambda x, idx=i: self.switch_team(idx))
            self.team_selector.add_widget(btn)

        if self.current_team_index < len(all_effectifs):
            self.render_table(all_effectifs[self.current_team_index], f_factor)

    def switch_team(self, index):
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
        # ------------------------------------

        main_scroll = ScrollView(
            size_hint=(1, 1), 
            do_scroll_x=True, 
            do_scroll_y=True,
            bar_width=0,
            scroll_type=['content']
        )
        
        # ... (le reste du code de render_table demeure identique)
        
        # Définition des largeurs de colonnes
        base_widths = [45, 180, 110, 85, 40]
        adjusted_widths = [dp(w + (f_factor - 20) * 1.8) for w in base_widths]
        
        # Calcul pour remplir l'écran si le tableau est trop petit
        min_needed_width = sum(adjusted_widths)
        total_table_width = max(min_needed_width, Window.width)
        
        # On ajuste la colonne Nom (index 1) pour combler le vide si nécessaire
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
                color=(0.97, 0.93, 0.25, 1) # Titre en jaune
            ))
        inner_table.add_widget(header)

        # --- LISTE DES JOUEURS ---
        row_height = dp(50) + dp(f_factor - 20)
        for j in data.get("joueurs", []):
            row = GridLayout(cols=5, size_hint=(None, None), height=row_height, width=total_table_width)
            is_cap = j.get("capitaine", False)
            
            with row.canvas.before:
                if is_cap:
                    Color(0.97, 0.93, 0.25, 0.25) # Jaune pour le capitaine
                else:
                    Color(1, 1, 1, 0.05) # Ligne standard
                
                row.bg_rect = RoundedRectangle(pos=row.pos, size=row.size, radius=[dp(5)])
            
            row.bind(pos=lambda inst, val: setattr(inst.bg_rect, 'pos', inst.pos),
                     size=lambda inst, val: setattr(inst.bg_rect, 'size', inst.size))

            # Colonne N°
            row.add_widget(Label(text=str(j.get("numero", "-")), size_hint_x=None, width=adjusted_widths[0], 
                                 font_size=f"{f_factor - 4}sp", color=(0.97, 0.93, 0.25, 1), bold=True))
            
            # Colonne Nom
            nom_complet = f"{j.get('nom', '').upper()} {j.get('prenom', '')}"
            l_nom = Label(text=nom_complet, size_hint_x=None, width=adjusted_widths[1], 
                          halign='left', valign='middle', font_size=f"{f_factor - 5}sp")
            l_nom.bind(size=lambda s, w: s.setter('text_size')(s, (s.width - dp(10), None)))
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