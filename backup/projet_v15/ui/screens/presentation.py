# -*- coding: utf-8 -*-
import webbrowser
from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.image import Image
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView
from kivy.clock import Clock
from kivy.app import App
from kivy.graphics import Color, Rectangle, PushMatrix, PopMatrix, Rotate, RoundedRectangle
from kivy.metrics import dp
from kivy.animation import Animation
from kivy.properties import NumericProperty

class LoadingSpinner(Image):
    angle = NumericProperty(0)
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.source = "assets/icons/loading_wheel.png" 
        self.size_hint = (None, None)
        self.size = (dp(50), dp(50))
        self.pos_hint = {'center_x': 0.5}
        with self.canvas.before:
            PushMatrix()
            self.rot = Rotate(angle=0, origin=self.center)
        with self.canvas.after:
            PopMatrix()
        self.bind(pos=self._update_rotate_origin, size=self._update_rotate_origin)
        self.anim = Animation(angle=-360, duration=1.5)
        self.anim.repeat = True
        self.anim.start(self)

    def _update_rotate_origin(self, *args):
        self.rot.origin = self.center

    def on_angle(self, item, value):
        self.rot.angle = value

class PresentationScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        app = App.get_running_app()
        self.is_apk = getattr(app, 'generate_APK', False)
        self.KIVY_BLUE = (30/255, 58/255, 138/255, 1)
        self.current_tab = "presse"  
        
        with self.canvas.before:
            Color(*self.KIVY_BLUE)
            self.rect_bg = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._update_bg, size=self._update_bg)

        self.main_layout = BoxLayout(orientation='vertical')
        
        # --- 1. SÉLECTEUR D'ONGLETS (AJUSTÉ POUR GROS DOIGTS) ---
        # Hauteur fixée à 85dp pour la cohérence avec les autres écrans
        self.tab_bar = BoxLayout(size_hint_y=None, height=dp(85), spacing=dp(10), padding=dp(10))
        self.main_layout.add_widget(self.tab_bar)

        # 2. CONTENEUR DE CONTENU
        self.scroll = ScrollView(do_scroll_x=False)
        self.content_layout = BoxLayout(orientation='vertical', padding=[dp(20), dp(10)], spacing=dp(15), size_hint_y=None)
        self.content_layout.bind(minimum_height=self.content_layout.setter('height'))
        
        self.scroll.add_widget(self.content_layout)
        self.main_layout.add_widget(self.scroll)
        
        self.img_header = Image(source="assets/logo_pres.png", size_hint=(1, None), height=dp(220), allow_stretch=True, keep_ratio=True)
        self.label_presse = Label(text="", color=(1, 1, 1, 1), halign='justify', valign='top', size_hint_y=None, markup=True)
        self.label_presse.bind(width=lambda s, w: s.setter('text_size')(s, (w, None)))
        self.label_presse.bind(texture_size=lambda s, z: s.setter('height')(s, z[1]))
        
        self.spinner = LoadingSpinner()
        
        self.add_widget(self.main_layout)

    def _update_bg(self, instance, value):
        self.rect_bg.pos = instance.pos
        self.rect_bg.size = instance.size

    def on_enter(self):
        self.update_ui_from_config()

    def switch_tab(self, tab_name):
        self.current_tab = tab_name
        self.update_ui_from_config()

    def update_ui_from_config(self, *args):
        app = App.get_running_app()
        tr = app._ if hasattr(app, '_') else lambda x: x
        lang = app.config.get('User', 'langue') if hasattr(app, 'config') else 'Français'
        
        # 1. Récupération de la taille de police
        f_factor = 20
        if hasattr(app, 'config'):
            try: f_factor = app.config.getint('User', 'font_size_factor')
            except: pass

        # 2. Rafraîchissement de la barre d'onglets (Harmonisée à 85dp)
        self.tab_bar.clear_widgets()
        self.tab_bar.height = dp(85)
        self.tab_bar.spacing = dp(10)
        self.tab_bar.padding = dp(10)
        
        tabs = [("presse", tr("press_kit")), ("docs", tr("documents"))]
        
        for tab_id, tab_label in tabs:
            is_active = (self.current_tab == tab_id)
            
            # Calcul de largeur dynamique identique aux autres écrans
            btn_width = max(dp(160), dp(len(tab_label) * (f_factor * 0.7)))
            
            btn = Button(
                text=tab_label,
                size_hint=(None, 1), # Prend toute la hauteur de la barre (85dp)
                width=btn_width,
                background_normal='',
                background_color=(0, 0, 0, 0), # On met le bouton invisible pour voir le RoundedRectangle derrière
                color=(0, 0, 0, 1) if is_active else (1, 1, 1, 1),
                bold=is_active,
                font_size=f"{f_factor - 1}sp"
            )
            
            # Dessin du fond arrondi (Strictement identique à EffectifScreen)
            with btn.canvas.before:
                Color(*(0.97, 0.93, 0.25, 1) if is_active else (1, 1, 1, 0.15))
                btn.bg_rect = RoundedRectangle(pos=btn.pos, size=btn.size, radius=[dp(8)])
            
            # Mise à jour auto de la forme si le bouton bouge ou change de taille
            btn.bind(pos=lambda inst, val: setattr(inst.bg_rect, 'pos', inst.pos),
                     size=lambda inst, val: setattr(inst.bg_rect, 'size', inst.size))
            
            btn.bind(on_release=lambda x, tid=tab_id: self.switch_tab(tid))
            self.tab_bar.add_widget(btn)

        # 3. Mise à jour du contenu
        self.content_layout.clear_widgets()
        
        # Sécurité chargement config
        if not hasattr(app, 'app_config') or not app.app_config.get("tournoi"):
            self.content_layout.add_widget(self.spinner)
            Clock.schedule_once(self.update_ui_from_config, 0.5)
            return

        tournoi_root = app.app_config.get("tournoi", {})
        pres_data = tournoi_root.get("appli", {}).get("presentation", {})

        if self.current_tab == "presse":
            # Affichage Dossier de Presse
            self.content_layout.add_widget(self.img_header)
            msg_key = 'dossier_presse_en' if lang == 'English' else 'dossier_presse'
            new_text = pres_data.get(msg_key, pres_data.get('dossier_presse', ''))
            
            self.label_presse.font_size = f"{f_factor}sp"
            self.label_presse.text = new_text
            self.content_layout.add_widget(self.label_presse)

        else:
            # Affichage Liste des Documents
            docs = pres_data.get("documents", [])
            if not docs:
                no_doc_txt = tr("no_docs") if hasattr(app, '_') else "Aucun document"
                self.content_layout.add_widget(Label(text=no_doc_txt, size_hint_y=None, height=dp(100), font_size=f"{f_factor}sp"))
            else:
                for doc in docs:
                    name_key = 'nom_en' if lang == 'English' else 'nom'
                    btn_name = doc.get(name_key, doc.get("nom", "Document"))
                    btn_url = doc.get("url", "")
                    
                    # Boutons PDF confortables (Hauteur augmentée)
                    btn_height = dp(80) + dp(f_factor - 20)
                    
                    pdf_btn = Button(
                        text=f"{btn_name} (PDF)",
                        size_hint_y=None, height=btn_height,
                        background_normal='',
                        background_color=(0.9, 0.9, 0.9, 1),
                        color=(0, 0, 0, 1),
                        bold=True,
                        font_size=f"{f_factor - 1}sp"
                    )
                    pdf_btn.bind(on_release=lambda x, url=btn_url: self.open_custom_pdf(url))
                    self.content_layout.add_widget(pdf_btn)

    def open_custom_pdf(self, url):
        if url and url.startswith("http"):
            webbrowser.open(url)