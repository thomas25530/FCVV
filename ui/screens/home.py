# -*- coding: utf-8 -*-
import threading
import hashlib
import os
from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.image import AsyncImage, Image
from kivy.uix.scrollview import ScrollView
from kivy.graphics import Color, Rectangle, PushMatrix, PopMatrix, Rotate, RoundedRectangle
from kivy.app import App
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.animation import Animation
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.modalview import ModalView
from kivy.uix.carousel import Carousel
from kivy.uix.scatter import Scatter
from kivy.uix.button import Button
from kivy.uix.stencilview import StencilView


# --- COMPOSANT COMPORTEMENTAL : APERÇU NETTOYÉ ET RE-DIMENSIONNABLE ---
class ImagePreview(ModalView):
    def __init__(self, img_sources, index=0, **kwargs):
        super().__init__(**kwargs)
        self.background = ""
        self.background_color = (0, 0, 0, 0.95)
        self.size_hint = (1, 1)

        layout = FloatLayout()
        self.carousel = Carousel(direction='right', loop=True)
        
        # Logique de détection du zoom pour bloquer le swipe du carousel
        def is_current_view_zoomed():
            if not self.carousel.current_slide:
                return False
            for child in self.carousel.current_slide.children:
                if isinstance(child, Scatter):
                    return child.scale > 1
            return False

        orig_on_touch_move = self.carousel.on_touch_move
        self.carousel.on_touch_move = lambda touch: False if is_current_view_zoomed() else orig_on_touch_move(touch)

        if isinstance(img_sources, str):
            img_sources = [img_sources]

        for src in img_sources:
            container = StencilView(size_hint=(1, 1))
            
            scatter = Scatter(
                do_rotation=False, 
                size_hint=(None, None),
                auto_bring_to_front=False,
                scale_min=1
            )
            
            full_img = AsyncImage(
                source=src,
                allow_stretch=True,
                keep_ratio=True,
                size_hint=(None, None)
            )
            
            # CONFIGURATION DE L'ANCRE (Fix du bug de la boucle)
            # En mettant "s=scatter" et "i=full_img", on verrouille ces composants précis pour ce tour de boucle
            def resize_trigger(instance_container, current_size, s=scatter, i=full_img):
                s.size = current_size
                i.size = current_size
                s.pos = (0, 0)

            container.bind(size=resize_trigger)
            
            # Double tap pour reset le zoom
            def custom_on_touch_down(inst, touch):
                if touch.is_double_tap:
                    anim = Animation(scale=1, pos=(0, 0), duration=0.3, t='out_quad')
                    anim.start(inst)
                    return True
                return Scatter.on_touch_down(inst, touch)

            scatter.bind(on_touch_down=custom_on_touch_down)
            scatter.bind(scale=lambda instance, value: setattr(self.carousel, 'ignore_child_horizontally', value > 1))

            scatter.add_widget(full_img)
            container.add_widget(scatter)
            self.carousel.add_widget(container)

        self.carousel.index = index
        layout.add_widget(self.carousel)

        # Bouton Fermer
        close_btn = Button(
            text="[b]X[/b]", markup=True,
            size_hint=(None, None), size=(dp(60), dp(60)),
            pos_hint={'top': 0.99, 'right': 0.99},
            background_normal='',
            background_color=(0, 0, 0, 0.7),
            color=(1, 1, 1, 1),
            font_size='24sp'
        )
        close_btn.bind(on_release=lambda x: self.dismiss())
        layout.add_widget(close_btn)
        self.add_widget(layout)


# --- SOUS-CLASSE OPTIMISÉE POUR LE BADGE (ZÉRO FUITE RAM) ---
class GalleryBadge(Label):
    """Badge numérique gérant graphiquement son arrière-plan sans recréer d'objets à la volée."""
    def __init__(self, count, **kwargs):
        super().__init__(
            text=f"+{count}", bold=True, font_size='14sp', color=(0, 0, 0, 1),
            size_hint=(None, None), size=(dp(35), dp(35)), **kwargs
        )
        with self.canvas.before:
            Color(0.85, 0.85, 0.85, 0.85) # Gris clair translucide stable
            self.bg_rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(5)])
        self.bind(pos=self._update_rect, size=self._update_rect)

    def _update_rect(self, instance, value):
        self.bg_rect.pos = instance.pos
        self.bg_rect.size = instance.size


# --- FIL D'ACTUALITÉS : CARTE INDIVIDUELLE ---
class NewsCard(BoxLayout):
    def __init__(self, title, date, description, images=None, **kwargs):
        # S'assurer que self.image_list est toujours une liste propre
        if isinstance(images, str):
            self.image_list = [images]
        elif isinstance(images, list):
            self.image_list = images
        else:
            self.image_list = []

        super().__init__(orientation="vertical", size_hint_y=None, spacing=dp(10), padding=dp(15), **kwargs)
        
        app = App.get_running_app()
        user_font_size = 18  
        if app and hasattr(app, 'config') and app.config.has_section('User'):
            try: user_font_size = app.config.getint('User', 'font_size_factor')
            except: pass
        
        with self.canvas.before:
            Color(1, 1, 1, 1) 
            self.bg_rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(10)])
        self.bind(pos=self._update_rect, size=self._update_rect)

        # --- TEXTES ---
        self.add_widget(Label(
            text=f"[b]{title}[/b]", markup=True, color=(0.1, 0.1, 0.3, 1),
            font_size=f"{user_font_size}sp", size_hint_y=None, height=dp(30),
            halign='left', valign='middle'
        ))
        self.children[-1].bind(width=lambda s, w: setattr(s, 'text_size', (w, None)))

        self.add_widget(Label(
            text=f"({date})", color=(0.5, 0.5, 0.5, 1),
            font_size=f"{user_font_size - 6}sp", size_hint_y=None, height=dp(20),
            halign='left', valign='middle'
        ))
        self.children[-1].bind(width=lambda s, w: setattr(s, 'text_size', (w, None)))

        desc_label = Label(
            text=description, color=(0.2, 0.2, 0.2, 1),
            font_size=f"{user_font_size - 3}sp", size_hint_y=None,
            halign='justify', markup=True
        )
        desc_label.bind(width=lambda s, w: s.setter('text_size')(s, (w, None)))
        desc_label.bind(texture_size=lambda s, z: s.setter('height')(s, z[1]))
        self.add_widget(desc_label)

        # --- ZONE MÉDIA ---
        if self.image_list:
            main_img_url = self.image_list[0]
            is_local = os.path.exists(main_img_url)
            img_container = FloatLayout(size_hint=(1, None), height=dp(220))
            
            # Correction ici : Utilisation de pos_hint pour forcer le centrage de l'image dans son conteneur
            img_class = Image if is_local else AsyncImage
            img = img_class(
                source=main_img_url, 
                size_hint=(1, 1), 
                pos_hint={'center_x': 0.5, 'center_y': 0.5}, # Centrage parfait
                allow_stretch=True, 
                keep_ratio=True, 
                opacity=1 if is_local else 0
            )
            
            img.bind(on_touch_down=self._on_image_touch)
            img_container.add_widget(img)

            # Restauration complète du badge s'il y a plus d'une image
            if len(self.image_list) > 1:
                badge = GalleryBadge(count=len(self.image_list) - 1, pos_hint={'right': 0.98, 'y': 0.05})
                img_container.add_widget(badge)

            # Loader de chargement
            if not is_local:
                loader = Image(source="assets/icons/loading_wheel.png", size_hint=(None, None), size=(dp(40), dp(40)), pos_hint={'center_x': 0.5, 'center_y': 0.5})
                with loader.canvas.before:
                    PushMatrix()
                    loader.rot = Rotate(angle=0)
                with loader.canvas.after:
                    PopMatrix()
                
                loader.bind(center=lambda ins, val: setattr(ins.rot, 'origin', ins.center))
                anim = Animation(angle=-360, duration=1.5, t='linear')
                anim.repeat = True
                anim.start(loader.rot)
                
                def on_loaded(*args):
                    anim.stop(loader.rot)
                    Animation(opacity=0, duration=0.2).start(loader)
                    Animation(opacity=1, duration=0.3).start(img)
                img.bind(on_load=on_loaded)
                img_container.add_widget(loader)

            self.add_widget(img_container)
        
        self.bind(minimum_height=self.setter('height'))

    def _on_image_touch(self, instance, touch):
        if instance.collide_point(*touch.pos) and not touch.is_mouse_scrolling:
            if abs(touch.dx) < dp(5) and abs(touch.dy) < dp(5):
                ImagePreview(img_sources=self.image_list).open()
                return True
        return False

    def _update_rect(self, instance, value):
        self.bg_rect.pos = instance.pos
        self.bg_rect.size = instance.size


# --- ÉCRAN ACCUEIL PRINCIPAL ---
class HomeScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.last_config_hash = None
        self.is_generating = False
        self.KIVY_BLUE = (30/255, 58/255, 138/255, 1)

        self.main_layout = FloatLayout() 
        self.container = BoxLayout(orientation="vertical")
        with self.container.canvas.before:
            Color(*self.KIVY_BLUE)
            self.rect_bg = Rectangle(pos=self.container.pos, size=self.container.size)
        self.container.bind(pos=self._update_bg, size=self._update_bg)

        self.scroll = ScrollView(size_hint=(1, 1), do_scroll_x=False, bar_width=0)
        self.scroll_content = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(20), padding=[0, 0, 0, dp(10)])
        self.scroll_content.bind(minimum_height=self.scroll_content.setter('height'))

        self.banner = Image(source="assets/banniere.png", size_hint=(1, None), height=dp(200), allow_stretch=True, keep_ratio=True)
        self.banner.bind(width=lambda inst, val: setattr(inst, 'height', val * 0.5625))
        self.scroll_content.add_widget(self.banner)

        self.news_layout = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(20), padding=[dp(15), 0, dp(15), 0])
        self.news_layout.bind(minimum_height=self.news_layout.setter('height'))
        self.scroll_content.add_widget(self.news_layout)

        self.scroll.add_widget(self.scroll_content)
        self.container.add_widget(self.scroll)
        
        self.main_loader = Image(
            source="assets/icons/loading_wheel.png", size_hint=(None, None),
            size=(dp(50), dp(50)), pos_hint={'center_x': 0.5, 'top': 0.8}, opacity=0
        )
        with self.main_loader.canvas.before:
            PushMatrix()
            self.main_rot = Rotate(angle=0)
        with self.main_loader.canvas.after:
            PopMatrix()
            
        self.main_loader.bind(center=lambda inst, val: setattr(self.main_rot, 'origin', inst.center))

        self.main_layout.add_widget(self.container)
        self.main_layout.add_widget(self.main_loader)
        self.add_widget(self.main_layout)
        
        self.scroll.bind(on_scroll_stop=self._check_refresh)
    
    def _check_refresh(self, instance, touch):
        if instance.scroll_y > 1.1 and not self.is_generating:
            self.manual_refresh()

    def manual_refresh(self):
        app = App.get_running_app()
        self.show_main_loader(True)
        
        def background_refresh():
            if hasattr(app, 'load_remote_config'):
                app.load_remote_config()
                Clock.schedule_once(lambda dt: self.update_ui_from_config(), 0.5)

        threading.Thread(target=background_refresh, daemon=True).start()

    def _update_bg(self, instance, value):
        self.rect_bg.pos = instance.pos
        self.rect_bg.size = instance.size

    def _rotate_loader(self, dt):
        self.main_rot.angle -= 6

    def show_main_loader(self, show):
        if show:
            if self.main_loader.opacity == 0:
                self.main_loader.opacity = 1
                Clock.unschedule(self._rotate_loader)
                Clock.schedule_interval(self._rotate_loader, 1/60)
        else:
            self.main_loader.opacity = 0
            Clock.unschedule(self._rotate_loader)

    def on_enter(self):
        app = App.get_running_app()
        fcvv_data = app.app_config.get("fcvv", {}) if hasattr(app, "app_config") else {}
        news_list = fcvv_data.get("appli", {}).get("news", [])
        text_content = "".join([f"{n.get('title')}{n.get('description')}{n.get('images')}{n.get('image')}" for n in news_list])
        current_hash = hashlib.md5(text_content.encode()).hexdigest()

        if current_hash == self.last_config_hash and self.news_layout.children:
            Clock.schedule_once(self._delayed_init, 0.2)
        else:
            self.show_main_loader(True)
            Clock.schedule_once(self._delayed_init, 0.8)

    def _delayed_init(self, dt):
        app = App.get_running_app()
        self.update_ui_from_config()

        def background_check():
            if hasattr(app, 'load_remote_config'):
                app.load_remote_config()
                Clock.schedule_once(lambda dt: self.update_ui_from_config(), 1.2)
        
        threading.Thread(target=background_check, daemon=True).start()

    def update_ui_from_config(self, *args):
        app = App.get_running_app()
        if self.is_generating or not hasattr(app, "app_config") or not app.app_config:
            return False

        fcvv_data = app.app_config.get("fcvv", {})
        news_list = fcvv_data.get("appli", {}).get("news", [])
        
        text_content = "".join([f"{n.get('title')}{n.get('description')}{n.get('images')}{n.get('image')}" for n in news_list])
        current_hash = hashlib.md5(text_content.encode()).hexdigest()

        if current_hash == self.last_config_hash:
            if not self.is_generating:
                self.show_main_loader(False)
            return False

        self.last_config_hash = current_hash
        self.show_main_loader(True)
        Clock.schedule_once(lambda dt: self._clear_and_start(news_list), 0.5)
        return True

    def _clear_and_start(self, news_list):
        self.news_layout.clear_widgets()
        self.is_generating = True
        Clock.schedule_once(lambda dt: self._start_gradual_gen(news_list), 0.2)

    def _start_gradual_gen(self, news_list):
        items_to_add = list(news_list)

        def add_next_card(dt):
            if not items_to_add:
                self.is_generating = False
                Clock.schedule_once(lambda d: self.show_main_loader(False), 0.5)
                return False
        
            item = items_to_add.pop(0)
            card = NewsCard(
                title=item.get("title", ""),
                date=item.get("date", ""),
                description=item.get("description", ""),
                images=item.get("images") or item.get("image")
            )
            self.news_layout.add_widget(card)
            Clock.schedule_once(add_next_card, 0.3)

        add_next_card(0)