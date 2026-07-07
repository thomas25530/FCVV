# -*- coding: utf-8 -*-
import webbrowser
from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.image import Image
from kivy.graphics import Color, Rectangle, RoundedRectangle
from kivy.app import App
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.uix.button import Button
from kivy.uix.widget import Widget
from kivy.effects.scroll import ScrollEffect


class InscriptionsScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        app = App.get_running_app()
        is_apk = getattr(app, 'generate_APK', False)
        self._clock_ev = None
        
        # --- HAUTEUR DE L'IMAGE AGRANDIE ---
        h_val = dp(450) if is_apk else dp(400) 
        
        # 1. ROOT PRINCIPAL
        self.KIVY_BLUE = (30/255, 58/255, 138/255, 1)
        self.container = BoxLayout(orientation="vertical", padding=[dp(10), dp(10), dp(10), dp(10)])
        
        with self.container.canvas.before:
            Color(*self.KIVY_BLUE)
            self.rect_bg = Rectangle(pos=self.container.pos, size=self.container.size)
        self.container.bind(pos=self._update_bg, size=self._update_bg)

        # 2. SCROLLVIEW VERTICAL (Le seul parent nécessaire)
        self.main_scroll = ScrollView(
            size_hint=(1, 1), 
            do_scroll_x=False, 
            do_scroll_y=True,
            bar_width=0
        )
        
        self.scroll_content = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(25))
        self.scroll_content.bind(minimum_height=self.scroll_content.setter('height'))

        # --- IMAGE D'EN-TÊTE ---
        self.img_header = Image(
            source="assets/FCVV.png",
            size_hint=(1, None),
            height=h_val,
            fit_mode="contain",
            pos_hint={'center_x': 0.5}
        )

        # --- TABLEAU ADAPTATIF (Sans Scroll horizontal) ---
        # On utilise size_hint_x=1 pour qu'il s'adapte automatiquement à l'écran
        self.table_container = BoxLayout(
            orientation="vertical", 
            size_hint=(1, None), 
            spacing=dp(2)
        )
        self.table_container.bind(minimum_height=self._update_table_height)

        # --- BOUTON INSCRIPTION ---
        self.inscription_url = ""
        self.inscription_btn = Button(
            text="", markup=True, bold=True,
            color=self.KIVY_BLUE,
            background_normal='', background_color=(0, 0, 0, 0),
            size_hint=(0.85, None), height=dp(65),
            pos_hint={'center_x': 0.5}
        )
        
        with self.inscription_btn.canvas.before:
            self.btn_color = Color(253/255, 224/255, 71/255, 1)
            self.btn_rect = RoundedRectangle(pos=self.inscription_btn.pos, size=self.inscription_btn.size, radius=[dp(14)])
        
        self.inscription_btn.bind(pos=self._update_btn_canvas, size=self._update_btn_canvas)
        self.inscription_btn.bind(on_press=self._on_btn_press, on_release=self._on_btn_release)

        # --- ASSEMBLAGE DIRECT ---
        self.scroll_content.add_widget(self.img_header)
        self.scroll_content.add_widget(self.table_container) # Ajout direct du tableau
        self.scroll_content.add_widget(self.inscription_btn)
        self.scroll_content.add_widget(Widget(size_hint_y=None, height=dp(40)))
        
        self.main_scroll.add_widget(self.scroll_content)
        self.container.add_widget(self.main_scroll)
        self.add_widget(self.container)

    def _update_bg(self, instance, value):
        self.rect_bg.pos = instance.pos
        self.rect_bg.size = instance.size

    def _update_btn_canvas(self, instance, value):
        """ Aligne le RoundedRectangle sur la position physique du bouton """
        self.btn_rect.pos = instance.pos
        self.btn_rect.size = instance.size

    def _on_btn_press(self, instance):
        """ Devient blanc au clic pour donner un retour tactile propre """
        self.btn_color.rgb = (1, 1, 1)

    def _on_btn_release(self, instance):
        """ Repasse au Jaune FCVV et lance la redirection """
        self.btn_color.rgb = (253/255, 224/255, 71/255)
        if self.inscription_url:
            webbrowser.open(self.inscription_url)

    def _update_table_height(self, instance, value):
        """ Met à jour uniquement le conteneur """
        instance.height = value

    def on_pre_enter(self):
        if self._clock_ev:
            Clock.unschedule(self._clock_ev)
        self._clock_ev = Clock.schedule_once(self.update_ui_from_config, 0.1)

    def on_leave(self):
        if self._clock_ev:
            Clock.unschedule(self._clock_ev)
            self._clock_ev = None

    def update_ui_from_config(self, *args):
        self._clock_ev = None
        app = App.get_running_app()
        if not hasattr(app, "app_config") or not app.app_config:
            return

        # CONFIG POLICE ET LANGUE
        lang = "Francais"
        user_font_size = 20
        if hasattr(app, 'config') and app.config.has_section('User'):
            user_font_size = app.config.getint('User', 'font_size_factor')
            lang = app.config.get('User', 'langue')
        
        base_fs = user_font_size - 4
        row_height = dp(user_font_size * 2.5)

        # Ratios de colonnes (pour occuper 100% de l'écran)
        # Total = 1.0 (Tournoi=0.35, Date=0.20, Prix=0.15 chacun)
        ratios = [0.35, 0.20, 0.15, 0.15, 0.15]
        
        # Le conteneur s'adapte à la largeur du parent
        self.table_container.size_hint_x = 1
        self.table_container.width = self.width

        # RÉCUPÉRATION DES DONNÉES
        home_data = app.app_config.get("tournoi", {}).get("appli", {}).get("home", {})
        inscriptions_data = app.app_config.get("tournoi", {}).get("appli", {}).get("inscriptions", {})

        # 1. MISE À JOUR DU TEXTE
        url = home_data.get("inscription_url", "")
        if url:
            self.inscription_url = url
            self.inscription_btn.font_size = f"{user_font_size * 0.8}sp"
            self.inscription_btn.text = (">>> CLICK HERE TO REGISTER <<<" if lang == "English" else ">>> CLIQUEZ ICI POUR VOUS INSCRIRE <<<")
            self.inscription_btn.size_hint_x = 0.85
            self.inscription_btn.height = dp(65)
            self.inscription_btn.opacity = 1
            self.inscription_btn.disabled = False
        else:
            self.inscription_btn.height = 0
            self.inscription_btn.opacity = 0
            self.inscription_btn.disabled = True

        # --- FIX FUITE MÉMOIRE ---
        for row in self.table_container.children:
            if isinstance(row, BoxLayout):
                for cell in row.children:
                    cell.unbind(pos=self._update_cell_rect, size=self._update_cell_rect)
            else:
                row.unbind(pos=self._update_cell_rect, size=self._update_cell_rect)

        # 2. CONSTRUCTION DU TABLEAU
        self.table_container.clear_widgets()
        tarifs = inscriptions_data.get("tarifs", [])

        if tarifs:
            gap = dp(2) 

            # LIGNE 1 : TARIFS
            top_header = BoxLayout(size_hint=(1, None), height=row_height*0.7, spacing=gap)
            top_header.add_widget(Widget(size_hint=(0.55, 1))) # Espace pour les 2 premières colonnes
            t_label = self._create_cell("TARIFS", font_size=base_fs+2, is_header=True, bg_color=(0.9, 0.8, 0, 1))
            t_label.size_hint = (0.45, 1)
            top_header.add_widget(t_label)
            self.table_container.add_widget(top_header)

            # LIGNE 2 : EN-TÊTE
            header_box = BoxLayout(size_hint=(1, None), height=row_height, spacing=gap)
            cols = ["Tournoi", "Date", "1 éq.", "2 éq.", "3 éq."]
            for i, text in enumerate(cols):
                cell = self._create_cell(text, font_size=base_fs, is_header=True)
                cell.size_hint = (ratios[i], 1)
                header_box.add_widget(cell)
            self.table_container.add_widget(header_box)

            # LIGNES DE DONNÉES
            for t in tarifs:
                row = BoxLayout(size_hint=(1, None), height=row_height, spacing=gap)
                vals = [
                    str(t.get("nom", "")), str(t.get("date", "")), 
                    f"{t.get('prix1')}€" if t.get('prix1') else "-",
                    f"{t.get('prix2')}€" if t.get('prix2') else "-",
                    f"{t.get('prix3')}€" if t.get('prix3') else "-"
                ]
                for i, text in enumerate(vals):
                    c = self._create_cell(text, font_size=base_fs)
                    c.size_hint = (ratios[i], 1)
                    row.add_widget(c)
                self.table_container.add_widget(row)

    def _create_cell(self, text, font_size=14, is_header=False, bg_color=None):
        lbl = Label(
            text=text, font_size=f"{font_size}sp", bold=is_header,
            color=(0, 0, 0, 1) if is_header else (1, 1, 1, 1),
            halign='center', valign='middle'
        )
        color = bg_color if bg_color else ((0.97, 0.92, 0.25, 1) if is_header else (1, 1, 1, 0.1))
        with lbl.canvas.before:
            Color(*color)
            lbl.rect = Rectangle(pos=lbl.pos, size=lbl.size)
        lbl.bind(pos=self._update_cell_rect, size=self._update_cell_rect)
        return lbl

    def _update_cell_rect(self, instance, value):
        instance.rect.pos = instance.pos
        instance.rect.size = instance.size