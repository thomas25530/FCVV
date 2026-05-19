# -*- coding: utf-8 -*-
from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.image import Image
from kivy.graphics import Color, Rectangle
from kivy.app import App
from kivy.clock import Clock
from kivy.metrics import dp
import webbrowser
from kivy.uix.button import Button
from kivy.uix.widget import Widget

class InscriptionsScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        app = App.get_running_app()
        is_apk = getattr(app, 'generate_APK', False)
        
        # --- HAUTEUR DE L'IMAGE AGRANDIE ---
        h_val = dp(450) if is_apk else dp(400) 
        
        # 1. ROOT PRINCIPAL
        self.KIVY_BLUE = (30/255, 58/255, 138/255, 1)
        # Padding lat�ral r�duit � 5dp pour laisser l'image s'�taler
        self.container = BoxLayout(orientation="vertical", padding=[dp(5), dp(10), dp(5), dp(10)])
        
        with self.container.canvas.before:
            Color(*self.KIVY_BLUE)
            self.rect_bg = Rectangle(pos=self.container.pos, size=self.container.size)
        self.container.bind(pos=self._update_bg, size=self._update_bg)

        # 2. SCROLLVIEW VERTICAL
        # do_scroll_y=True est explicite ici
        self.main_scroll = ScrollView(size_hint=(1, 1), do_scroll_x=False, do_scroll_y=True)
        
        # Le contenu du scroll : size_hint_y=None est CRUCIAL
        self.scroll_content = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(25))
        self.scroll_content.bind(minimum_height=self.scroll_content.setter('height'))

        # --- IMAGE D'EN-T�TE ---
        self.img_header = Image(
            source="assets/FCVV.png",
            size_hint=(1, None),
            height=h_val,
            allow_stretch=True,
            keep_ratio=True,
            pos_hint={'center_x': 0.5}
        )

        # --- BOUTON INSCRIPTION ---
        self.inscription_url = ""
        self.inscription_btn = Button(
            text="", markup=True, color=(1, 1, 0, 1),
            background_normal='', background_color=(0, 0, 0, 0),
            size_hint_y=None, height=dp(60)
        )
        self.inscription_btn.bind(on_release=self._on_inscription_click)

        # --- TABLEAU AVEC SCROLL HORIZONTAL ---
        self.h_scroll = ScrollView(
            size_hint=(1, None), 
            do_scroll_y=False, 
            bar_width=0,
            scroll_type=['content']
        )
        
        self.table_container = BoxLayout(orientation="vertical", size_hint=(None, None), spacing=dp(2))
        self.table_container.bind(minimum_height=self._update_table_height)
        self.h_scroll.add_widget(self.table_container)

        # --- ASSEMBLAGE ---
        self.scroll_content.add_widget(self.img_header)
        self.scroll_content.add_widget(self.inscription_btn)
        self.scroll_content.add_widget(self.h_scroll)
        
        # Espace de s�curit� en bas pour faciliter le scroll final
        self.scroll_content.add_widget(Widget(size_hint_y=None, height=dp(40)))
        
        self.main_scroll.add_widget(self.scroll_content)
        self.container.add_widget(self.main_scroll)
        self.add_widget(self.container)

    def _update_bg(self, instance, value):
        self.rect_bg.pos = instance.pos
        self.rect_bg.size = instance.size

    def _update_table_height(self, instance, value):
        """ Met à jour la hauteur du conteneur horizontal et notifie le scroll vertical """
        instance.height = value
        self.h_scroll.height = value + dp(15)
        # On force le layout parent � recalculer sa hauteur totale
        self.scroll_content.do_layout()

    def on_pre_enter(self):
        Clock.schedule_once(self.update_ui_from_config, 0.1)

    def update_ui_from_config(self, *args):
        app = App.get_running_app()
        if not hasattr(app, "app_config") or not app.app_config:
            return

        # CONFIG POLICE ET LANGUE
        lang = "Fran�ais"
        user_font_size = 20
        if hasattr(app, 'config') and app.config.has_section('User'):
            user_font_size = app.config.getint('User', 'font_size_factor')
            lang = app.config.get('User', 'langue')
        
        base_fs = user_font_size - 4
        row_height = dp(user_font_size * 2.5)

        # Largeurs de colonnes
        col_unit = dp(user_font_size * 3.5) 
        col_tournoi = col_unit * 2.5
        col_date = col_unit * 1.5
        col_prix = col_unit * 1.2
        
        total_table_width = col_tournoi + col_date + (col_prix * 3)
        self.table_container.width = total_table_width

        # R�CUP�RATION DES DONN�ES
        home_data = app.app_config.get("tournoi", {}).get("appli", {}).get("home", {})
        inscriptions_data = app.app_config.get("tournoi", {}).get("appli", {}).get("inscriptions", {})

        # 1. BOUTON INSCRIPTION
        url = home_data.get("inscription_url", "")
        if url:
            self.inscription_url = url
            self.inscription_btn.font_size = f"{user_font_size * 0.8}sp"
            self.inscription_btn.text = (
                "[u][b]*** CLICK HERE FOR ONLINE REGISTRATION ***[/b][/u]" 
                if lang == "English" 
                else "[u][b]*** CLIQUEZ ICI POUR L'INSCRIPTION EN LIGNE ***[/b][/u]"
            )
            self.inscription_btn.height = dp(70)
            self.inscription_btn.opacity = 1
            self.inscription_btn.disabled = False
        else:
            self.inscription_btn.height = 0
            self.inscription_btn.opacity = 0
            self.inscription_btn.disabled = True

        # 2. CONSTRUCTION DU TABLEAU
        self.table_container.clear_widgets()
        tarifs = inscriptions_data.get("tarifs", [])

        if tarifs:
            gap = dp(2) 

            # LIGNE 1 : TARIFS (CHAPEAU)
            top_header = BoxLayout(size_hint=(None, None), height=row_height*0.7, width=total_table_width, spacing=gap)
            spacer_w = col_tournoi + gap + col_date
            top_header.add_widget(Widget(size_hint=(None, 1), width=spacer_w))
            
            tarif_label_w = col_prix + gap + col_prix + gap + col_prix
            t_label = self._create_cell("TARIFS", font_size=base_fs+2, is_header=True, bg_color=(0.9, 0.8, 0, 1))
            t_label.size_hint = (None, 1)
            t_label.width = tarif_label_w
            top_header.add_widget(t_label)
            self.table_container.add_widget(top_header)

            # LIGNE 2 : EN-T�TE COLONNES
            header_box = BoxLayout(size_hint=(None, None), height=row_height, width=total_table_width, spacing=gap)
            cols = [("Tournoi", col_tournoi), ("Date", col_date), ("1 éq.", col_prix), ("2 éq.", col_prix), ("3 éq.", col_prix)]
            for text, w in cols:
                cell = self._create_cell(text, font_size=base_fs, is_header=True)
                cell.size_hint = (None, 1)
                cell.width = w
                header_box.add_widget(cell)
            self.table_container.add_widget(header_box)

            # LIGNES DE DONN�ES
            for t in tarifs:
                row = BoxLayout(size_hint=(None, None), height=row_height, width=total_table_width, spacing=gap)
                vals = [
                    (str(t.get("nom", "")), col_tournoi), 
                    (str(t.get("date", "")), col_date), 
                    (f"{t.get('prix1')}€" if t.get('prix1') else "-", col_prix), 
                    (f"{t.get('prix2')}€" if t.get('prix2') else "-", col_prix), 
                    (f"{t.get('prix3')}€" if t.get('prix3') else "-", col_prix)
                ]
                for text, w in vals:
                    c = self._create_cell(text, font_size=base_fs)
                    c.size_hint = (None, 1)
                    c.width = w
                    row.add_widget(c)
                self.table_container.add_widget(row)
        
        # Rafra�chissement final du scroll
        Clock.schedule_once(lambda dt: self.main_scroll.update_from_scroll(), 0.2)

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

    def _on_inscription_click(self, instance):
        if self.inscription_url:
            webbrowser.open(self.inscription_url)