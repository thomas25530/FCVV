# -*- coding: utf-8 -*-
import webbrowser
from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.image import Image
from kivy.uix.scrollview import ScrollView
from kivy.graphics import Color, Rectangle
from kivy.app import App
from kivy.clock import Clock
from kivy.metrics import dp
import os

# On définit ou on importe la fonction de traduction
def _(key):
    app = App.get_running_app()
    # Utilisation de la méthode de l'app si disponible pour éviter les imports circulaires
    if hasattr(app, '_'):
        return app._(key)
    return key

class ClickableImage(Image):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.url = None

    def on_touch_down(self, touch):
        if touch.is_mouse_scrolling: 
            return False
        if self.collide_point(*touch.pos):
            if self.url:
                webbrowser.open(self.url)
            return True
        return super().on_touch_down(touch)

class AboutScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # 1. RÉCUPÉRATION DE LA PLATEFORME
        app = App.get_running_app()
        self.is_apk = getattr(app, 'generate_APK', False)
        
        self.KIVY_BLUE = (30/255, 58/255, 138/255, 1)
        
        # Ajustement du padding selon la plateforme
        padding_val = dp(20) if self.is_apk else dp(30)
        self.root = BoxLayout(orientation='vertical', padding=[padding_val, dp(10), padding_val, dp(10)])
        
        with self.root.canvas.before:
            Color(*self.KIVY_BLUE)
            self.rect_bg = Rectangle(pos=self.root.pos, size=self.root.size)
        self.root.bind(pos=self._update_bg, size=self._update_bg)

        self.scroll = ScrollView(size_hint=(1, 1), do_scroll_x=False)
        self.scroll_content = BoxLayout(orientation='vertical', size_hint_y=None, spacing=dp(25))
        self.scroll_content.bind(minimum_height=self.scroll_content.setter('height'))

        # Intro Label
        self.intro_label = Label(
            text="", 
            markup=True, halign='center', 
            size_hint_y=None
        )
        self.intro_label.bind(width=lambda s, w: s.setter('text_size')(s, (w, None)))
        self.intro_label.bind(texture_size=lambda s, z: s.setter('height')(s, z[1]))
        
        # Image Partenaire (Plus grande sur APK)
        img_h = dp(300) if self.is_apk else dp(220)
        self.img_offert = ClickableImage(
            source="", 
            size_hint=(1, None), height=img_h, 
            allow_stretch=True, keep_ratio=True,
            nocache=True 
        )

        self.info_list = BoxLayout(orientation='vertical', spacing=dp(15), size_hint_y=None)
        self.info_list.bind(minimum_height=self.info_list.setter('height'))

        self.scroll_content.add_widget(self.intro_label)
        self.scroll_content.add_widget(self.img_offert)
        self.scroll_content.add_widget(self.info_list)
        self.scroll_content.add_widget(BoxLayout(size_hint_y=None, height=dp(40))) # Espace final
        
        self.scroll.add_widget(self.scroll_content)
        self.root.add_widget(self.scroll)
        self.add_widget(self.root)

    def _update_bg(self, instance, value):
        self.rect_bg.pos = instance.pos
        self.rect_bg.size = instance.size

    def on_enter(self):
        self.update_ui_from_config()

    def update_ui_from_config(self, *args):
        app = App.get_running_app()
        
        if hasattr(app, 'app_config') and app.app_config:
            # On descend d'abord dans 'tournoi', puis dans 'appli', puis dans 'about'
            about_data = app.app_config.get("fcvv", {}).get("appli", {}).get("about", {})
            
            lang = "Français"
            user_size = 20
            if hasattr(app, 'config') and app.config.has_section('User'):
                lang = app.config.get('User', 'langue')
                user_size = int(app.config.get('User', 'font_size_factor', fallback=20))

            # 1. Texte d'introduction
            intro = about_data.get('intro_text_en' if lang == 'English' else 'intro_text')
            if not intro:
                intro = _('about_intro')
                
            self.intro_label.text = f"[b]{intro}[/b]"
            # On booste un peu la taille sur APK
            self.intro_label.font_size = f"{user_size + (4 if self.is_apk else 2)}sp"
            
            # 2. Image et lien
            self.img_offert.url = about_data.get("sponsor_url")
            path = about_data.get("logo_partenaire", "./assets/default_logo.png")
            
            if path.startswith("http"):
                self.download_external_image(path)
            else:
                self.img_offert.source = path
                self.img_offert.reload()
            
            # 3. Liste d'informations
            self.info_list.clear_widgets()
            details = about_data.get("details", [])
            
            for item in details:
                name = item.get('label_en' if lang == 'English' else 'label', '')
                val = item.get("value", "")
                
                # On utilise une taille de police plus lisible sur mobile
                lbl_size = user_size + (2 if self.is_apk else 0)
                
                lbl = Label(
                    text=f"[color=bbbbbb]{name} :[/color] [b]{val}[/b]",
                    markup=True, font_size=f"{lbl_size}sp", halign='center',
                    size_hint_y=None
                )
                lbl.bind(width=lambda s, w: s.setter('text_size')(s, (w, None)))
                lbl.bind(texture_size=lambda s, z: s.setter('height')(s, z[1]))
                self.info_list.add_widget(lbl)
            
            return True
        else:
            Clock.schedule_once(self.update_ui_from_config, 0.5)
            return False

    def download_external_image(self, url):
        from kivy.network.urlrequest import UrlRequest
        app = App.get_running_app()
        filename = "sponsor_cache.png"
        temp_path = os.path.join(app.user_data_dir, filename)
        
        if os.path.exists(temp_path):
            self.img_offert.source = temp_path
            self.img_offert.reload()

        def on_success(request, result):
            content_type = request.resp_headers.get('Content-Type', '').lower()
            if "image" in content_type or "octet-stream" in content_type:
                try:
                    with open(temp_path, 'wb') as f:
                        f.write(result)
                    self.img_offert.source = temp_path
                    self.img_offert.reload()
                except Exception as e:
                    print(f"Error writing image: {e}")

        UrlRequest(url, on_success=on_success, req_headers={'User-Agent': 'Mozilla/5.0'})