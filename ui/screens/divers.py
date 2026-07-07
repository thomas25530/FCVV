# -*- coding: utf-8 -*-
import webbrowser
from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView
from kivy.clock import Clock
from kivy.app import App
from kivy.graphics import Color, Rectangle, RoundedRectangle
from kivy.metrics import dp
from kivy.effects.scroll import ScrollEffect

class StageCard(BoxLayout):
    """Carte d'information pour les stages, basée sur le layout NewsCard."""
    def __init__(self, stage_data, **kwargs):
        super().__init__(orientation="vertical", size_hint_y=None, spacing=dp(12), padding=dp(15), **kwargs)
        
        # Récupération des préférences utilisateur
        app = App.get_running_app()
        user_font_size = 18
        if app and hasattr(app, 'config') and app.config.has_section('User'):
            try: user_font_size = app.config.getint('User', 'font_size_factor')
            except: pass
            
        # Fond blanc arrondi
        with self.canvas.before:
            Color(1, 1, 1, 1)
            self.bg_rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(12)])
        self.bind(pos=self._update_rect, size=self._update_rect)
        
        # 1. TITRE DU STAGE
        self.add_widget(Label(
            text=f"[b]{stage_data.get('nom', 'Stage')}[/b]", markup=True, color=(30/255, 58/255, 138/255, 1),
            font_size=f"{user_font_size + 2}sp", size_hint_y=None, height=dp(35), halign='left'
        ))
        self.children[-1].bind(width=lambda s, w: setattr(s, 'text_size', (w, None)))

        # 2. DATES PAR CATÉGORIE (Gestion dynamique)
        dates_box = BoxLayout(orientation='vertical', size_hint_y=None, spacing=dp(2))
        
        for key, label_text in [('dates_u7_u9', 'U7 / U9'), ('dates_u11_u13', 'U11 / U13')]:
            val = stage_data.get(key)
            if val:
                lbl = Label(text=f"• [b]{label_text} :[/b] {val}", 
                            markup=True, color=(0.3, 0.3, 0.3, 1), font_size=f"{user_font_size - 2}sp", 
                            size_hint_y=None, height=dp(22), halign='left')
                lbl.bind(width=lambda s, w: setattr(s, 'text_size', (w, None)))
                dates_box.add_widget(lbl)
        
        if len(dates_box.children) > 0:
            dates_box.height = len(dates_box.children) * dp(22)
            self.add_widget(dates_box)

        # 3. INFOS LOGISTIQUES (Gestion dynamique)
        logistics = [
            ("Public", stage_data.get('public')),
            ("Programme", stage_data.get('programme')),
            ("Repas", stage_data.get('repas')),
            ("Tarif", stage_data.get('tarif'))
        ]
        
        for label_key, value in logistics:
            if value:
                lbl = Label(
                    text=f"[b]{label_key} :[/b] {value}", markup=True, color=(0.2, 0.2, 0.2, 1),
                    font_size=f"{user_font_size - 3}sp", size_hint_y=None, halign='left'
                )
                lbl.bind(width=lambda s, w: s.setter('text_size')(s, (w, None)))
                lbl.bind(texture_size=lambda s, z: s.setter('height')(s, z[1]))
                self.add_widget(lbl)

        # 4. ZONE D'ACTIONS
        btn_box = BoxLayout(size_hint_y=None, height=dp(55), spacing=dp(10), padding=[0, dp(10), 0, 0])
        
        # Bouton Inscription
        btn_form = Button(text="S'INSCRIRE", bold=True, size_hint_x=0.6, background_normal='', 
                          background_color=(34/255, 197/255, 94/255, 1))
        btn_form.target_url = stage_data.get('form_url', '')
        btn_form.bind(on_release=lambda x: webbrowser.open(x.target_url) if x.target_url else None)
        btn_box.add_widget(btn_form)

        # Bouton Planning PDF
        planning_url = stage_data.get('planning_url')
        if planning_url:
            btn_pdf = Button(text="PLANNING", bold=True, size_hint_x=0.4, 
                             background_normal='', background_color=(0.5, 0.5, 0.5, 1))
            btn_pdf.bind(on_release=lambda x: webbrowser.open(planning_url))
            btn_box.add_widget(btn_pdf)

        self.add_widget(btn_box)
        self.bind(minimum_height=self.setter('height'))

    def _update_rect(self, instance, value):
        self.bg_rect.pos = instance.pos
        self.bg_rect.size = instance.size


class DiversScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.KIVY_BLUE = (30/255, 58/255, 138/255, 1)
        self.current_tab = "stages"
        self._clock_ev = None
        
        with self.canvas.before:
            Color(*self.KIVY_BLUE)
            self.rect_bg = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._update_bg, size=self._update_bg)

        self.main_layout = BoxLayout(orientation='vertical')
        self.tab_bar = BoxLayout(size_hint_y=None, height=dp(85), spacing=dp(10), padding=dp(10))
        self.main_layout.add_widget(self.tab_bar)

        self.scroll = ScrollView(do_scroll_x=False, do_scroll_y=True, bar_width=0, effect_cls=ScrollEffect)
        self.content_layout = BoxLayout(orientation='vertical', padding=[dp(20), dp(10)], spacing=dp(20), size_hint_y=None)
        self.content_layout.bind(minimum_height=self.content_layout.setter('height'))
        
        self.scroll.add_widget(self.content_layout)
        self.main_layout.add_widget(self.scroll)
        self.add_widget(self.main_layout)

    def _update_bg(self, instance, value):
        self.rect_bg.pos = instance.pos
        self.rect_bg.size = instance.size

    def _update_btn_rect(self, instance, value):
        if hasattr(instance, 'bg_rect'):
            instance.bg_rect.pos = instance.pos
            instance.bg_rect.size = instance.size

    def on_enter(self):
        self.update_ui_from_config()

    def _on_tab_released(self, instance):
        self.current_tab = instance.target_tab
        self.update_ui_from_config()

    def update_ui_from_config(self, *args):
        if self._clock_ev: Clock.unschedule(self._clock_ev)
        app = App.get_running_app()
        tr = app._ if hasattr(app, '_') else lambda x: x
        
        # Récupération de la taille de police définie dans le .ini
        user_size = app.config.getint('User', 'font_size_factor', fallback=18) if hasattr(app, 'config') else 18
        
        self.tab_bar.clear_widgets()
        self.content_layout.clear_widgets()

        if not hasattr(app, 'app_config') or not app.app_config.get("fcvv"):
            self._clock_ev = Clock.schedule_once(self.update_ui_from_config, 0.5)
            return

        fcvv_root = app.app_config.get("fcvv", {})
        divers_data = fcvv_root.get("appli", {}).get("divers", {})
        
        # Onglets avec taille de police et largeur dynamiques
        tabs = [("stages", "Stages"), ("docs", tr("documents"))]
        for tab_id, tab_label in tabs:
            is_active = (self.current_tab == tab_id)
            
            # Calcul de la largeur dynamique (inspiré de RestaurationScreen)
            btn_width = max(dp(160), dp(len(tab_label) * (user_size * 0.75)))
            
            btn = Button(
                text=tab_label, 
                size_hint=(None, 1), 
                width=btn_width,
                font_size=f"{user_size}sp", # Application de la taille
                background_normal='', 
                background_color=(0,0,0,0),
                color=(0,0,0,1) if is_active else (1,1,1,1), 
                bold=is_active
            )
            
            with btn.canvas.before:
                Color(*(0.97, 0.93, 0.25, 1) if is_active else (1, 1, 1, 0.15))
                btn.bg_rect = RoundedRectangle(pos=btn.pos, size=btn.size, radius=[dp(8)])
            
            btn.bind(pos=self._update_btn_rect, size=self._update_btn_rect)
            btn.target_tab = tab_id
            btn.bind(on_release=self._on_tab_released)
            self.tab_bar.add_widget(btn)

        # Affichage du contenu
        if self.current_tab == "stages":
            stages = divers_data.get("stages", [])
            if not stages:
                self.content_layout.add_widget(Label(text=tr("no_stages_available"), size_hint_y=None, height=dp(100)))
            else:
                for s in stages:
                    self.content_layout.add_widget(StageCard(stage_data=s))
        else: # Onglet Documents
            docs = divers_data.get("documents", [])
            if not docs:
                self.content_layout.add_widget(Label(text=tr("no_docs"), size_hint_y=None, height=dp(100)))
            else:
                for doc in docs:
                    nom = doc.get("nom")
                    url = doc.get("url")
                    
                    if nom and url:
                        btn = Button(
                            text=nom, 
                            size_hint_y=None, height=dp(60),
                            font_size=f"{user_size}sp", # Application de la taille aux boutons docs
                            background_normal='', 
                            background_color=(0.9, 0.9, 0.9, 1), 
                            color=(0, 0, 0, 1)
                        )
                        btn.target_url = url
                        btn.bind(on_release=lambda instance: webbrowser.open(instance.target_url))
                        self.content_layout.add_widget(btn)