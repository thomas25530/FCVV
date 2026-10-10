# -*- coding: utf-8 -*-
import threading
import hashlib
import os
import urllib3
import requests
import json
from datetime import datetime, timedelta
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
from kivy.uix.widget import Widget
from constants import LANGUAGES
# Désactivation des warnings de sécurité pour les images
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def get_local_image_path(url, app):
    img_hash = hashlib.md5(url.encode()).hexdigest()

    for f in os.listdir(app.cache_images_dir):
        if f.startswith(f"img_{img_hash}"):
            return os.path.join(app.cache_images_dir, f)
    return None

def get_user_font_size():
    app = App.get_running_app()
    if app and hasattr(app, 'config') and app.config.has_section('User'):
        try:
            return app.config.getint('User', 'font_size_factor')
        except:
            pass
    return 18

class ImagePreview(ModalView):
    def __init__(self, img_sources, index=0, **kwargs):
        super().__init__(**kwargs)
        self.background = ""
        self.background_color = (0, 0, 0, 0.95)
        self.size_hint = (1, 1)
        layout = FloatLayout()
        self.carousel = Carousel(direction='right', loop=True)
        # --------------------------------------------------------
        # FONCTION DE VÉRIFICATION DU ZOOM
        # --------------------------------------------------------
        def get_current_scatter():
            slide = self.carousel.current_slide
            if not slide:
                return None
            for child in slide.children:
                if isinstance(child, Scatter):
                    return child
            return None
        # --------------------------------------------------------
        # GESTION DU CAROUSEL vs SCATTER (Zoom & Double Tap)
        # --------------------------------------------------------
        orig_on_touch_down = self.carousel.on_touch_down
        orig_on_touch_move = self.carousel.on_touch_move

        def custom_carousel_touch_down(touch):
            scatter = get_current_scatter()
            if scatter and scatter.collide_point(*touch.pos):
                if touch.is_double_tap:
                    anim = Animation(scale=1, pos=(0, 0), duration=0.3, t='out_quad')
                    anim.start(scatter)
                    return True  
            return orig_on_touch_down(touch)

        def custom_carousel_touch_move(touch):
            scatter = get_current_scatter()
            if scatter:
                if scatter.scale > 1.001:
                    scatter.do_translation = True
                    if scatter.collide_point(*touch.pos):
                        scatter.on_touch_move(touch)
                    return True  
                else:
                    scatter.do_translation = False  
            return orig_on_touch_move(touch)

        self.carousel.on_touch_down = custom_carousel_touch_down
        self.carousel.on_touch_move = custom_carousel_touch_move
        # --------------------------------------------------------
        # NORMALISATION & FILTRE ANTI-DOUBLONS
        # --------------------------------------------------------
        if isinstance(img_sources, str):
            img_sources = [img_sources]
        # Filtre unique qui conserve l'ordre d'origine
        img_sources = list(dict.fromkeys([src for src in img_sources if src]))
        # Ajustement de sécurité pour l'index au cas où la liste a rétréci
        if index >= len(img_sources):
            index = max(0, len(img_sources) - 1)
        # ----------------------------
        # BUILD SLIDES
        # ----------------------------
        for src in img_sources:
            container = FloatLayout(size_hint=(1, 1))
            scatter = Scatter(
                do_rotation=False,
                do_translation=False,  # Initialisé à False pour éviter le bug au premier contact
                auto_bring_to_front=False,
                scale_min=1,
                size_hint=(None, None)
            )
            app = App.get_running_app()
            local_path = src
            if isinstance(src, str) and "http" in src:
                local_path = get_local_image_path(src, app)
            
            is_local = local_path and os.path.exists(local_path)
            if is_local:
                full_img = Image(
                    source = local_path if is_local else src,
                    fit_mode="contain",
                    size_hint=(None, None),
                    opacity=1  # déjà dispo → pas de fade / pas de loader
                )
            else:
                full_img = AsyncImage(
                    source = local_path if is_local else src,
                    fit_mode="contain",
                    size_hint=(None, None),
                    opacity=0,
                    anim_delay=-1
                )
            # ----------------------------
            # LOADER (Repris exactement de ton ancien code)
            # ----------------------------
            loader = Image(
                source=os.path.join(
                    App.get_running_app().directory,
                    "assets",
                    "icons",
                    "loading_wheel.png"
                ),
                size_hint=(None, None),
                size=(dp(60), dp(60)),
                pos_hint={"center_x": 0.5, "center_y": 0.5}
            )
            # rotation origin fix
            loader.rot = Rotate(angle=0)
            with loader.canvas.before:
                PushMatrix()
                loader.canvas.add(loader.rot)
            with loader.canvas.after:
                PopMatrix()
            def update_origin(*_):
                loader.rot.origin = loader.center
            loader.bind(pos=update_origin, size=update_origin)
            # ----------------------------
            # ANIMATION PROPRE (Ton ancienne logique intacte)
            # ----------------------------
            loader._spin_anim = Animation(angle=360, duration=0.8)
            loader._spin_anim += Animation(angle=0, duration=0)
            loader._spin_anim.repeat = True
            if not is_local:
                loader._spin_anim.start(loader.rot)
            else:
                loader.opacity = 0  # masqué immédiatement si local
            def stop_loader(l):
                if hasattr(l, "_spin_anim"):
                    l._spin_anim.cancel(l.rot)
            # ----------------------------
            # RESIZE SYNC
            # ----------------------------
            def resize_trigger(instance, size, s=scatter, i=full_img):
                # On ne réinitialise la taille que si l'image n'est pas zoomée
                if s.scale <= 1.001:
                    s.size = instance.size
                    s.pos = (0, 0)
                    i.size = instance.size
                    i.pos = (0, 0)
            container.bind(size=resize_trigger)
            # ----------------------------
            # IMAGE LOADED CALLBACK
            # ----------------------------
            def image_loaded(instance, texture, img=full_img, ld=loader):
                if isinstance(img, AsyncImage) and texture:
                    Animation(opacity=1, duration=0.2).start(img)
                    stop_loader(ld)
                    if ld.parent:
                        ld.parent.remove_widget(ld)
            full_img.bind(texture=image_loaded)
            scatter.add_widget(full_img)
            container.add_widget(scatter)
            container.add_widget(loader)
            self.carousel.add_widget(container)
        # ----------------------------
        # INIT POSITION
        # ----------------------------
        self.carousel.index = index
        layout.add_widget(self.carousel)
        # ----------------------------
        # CLOSE BUTTON
        # ----------------------------
        # ----------------------------
        # CLOSE BUTTON
        # ----------------------------
        close_btn = Button(
            text="[b]X[/b]",
            markup=True,
            size_hint=(None, None),
            size=(dp(50), dp(50)),  # Bouton un peu plus large/haut pour un meilleur confort tactile
            pos_hint={'top': 0.94, 'right': 0.95},  # Descendu de 0.99 à 0.94 et légèrement décalé du bord droit (0.99 -> 0.95)
            background_normal='',
            background_color=(0.2, 0.2, 0.2, 0.85),  # Fond gris foncé un peu plus opaque pour mieux contraster
            color=(1, 1, 1, 1),  # Texte en blanc pur pour une visibilité maximale
            font_size='22sp'
        )
        close_btn.bind(on_release=lambda x: self.dismiss())
        layout.add_widget(close_btn)
        self.add_widget(layout)

class GalleryBadge(Label):
    def __init__(self, count, **kwargs):
        super().__init__(
            text=f"+{count}", bold=True, font_size='14sp', color=(0, 0, 0, 1),
            size_hint=(None, None), size=(dp(35), dp(35)), **kwargs
        )
        with self.canvas.before:
            Color(0.85, 0.85, 0.85, 0.85) 
            self.bg_rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(5)])
        self.bind(pos=self._update_rect, size=self._update_rect)

    def _update_rect(self, instance, value):
        self.bg_rect.pos = instance.pos
        self.bg_rect.size = instance.size

class MonthSeparator(Label):
    def __init__(self, month_text, **kwargs):
        super().__init__(**kwargs)
        self.text = f"[b]{month_text}[/b]"
        self.markup = True
        self.color = (0.9, 0.9, 0.9, 1)  # Texte clair contrastant avec le fond KIVY_BLUE
        self.font_size = "20sp"
        self.size_hint_y = None
        self.height = dp(55)
        self.halign = 'left'
        self.valign = 'bottom'
        # Force le texte à occuper toute la largeur disponible pour s'aligner correctement à gauche
        self.bind(width=lambda s, w: setattr(s, 'text_size', (w, None)))
        
# --- FIL D'ACTUALITÉS : CARTE INDIVIDUELLE AVEC DEBUG INTEGRÉ ---
class NewsCard(BoxLayout):
    def __init__(self, title, date, description, images=None, **kwargs):
        self._check_events = []
        self.card_title = title
        self.card_date = date
        self.active = True  # Flag pour la sécurité des threads
        # --------------------------------------------------------
        # NORMALISATION & FILTRE ANTI-DOUBLONS (Conserve l'ordre)
        # --------------------------------------------------------
        if isinstance(images, str):
            raw_list = [images]
        elif isinstance(images, list):
            raw_list = list(images)
        else:
            raw_list = []
        # Nettoyage des doublons et des chaînes vides/None
        self.image_list = list(dict.fromkeys([src for src in raw_list if src]))
        super().__init__(orientation="vertical", size_hint_y=None, spacing=dp(10), padding=dp(15), **kwargs)
        # Gestion des polices
        app = App.get_running_app()
        user_font_size = 18  
        if app and hasattr(app, 'config') and app.config.has_section('User'):
            try: user_font_size = app.config.getint('User', 'font_size_factor')
            except: pass
        with self.canvas.before:
            Color(1, 1, 1, 1) 
            self.bg_rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(10)])
        self.bind(pos=self._update_rect, size=self._update_rect)
        # UI Elements
        title_label = Label(text=f"[b]{title}[/b]", markup=True, color=(0.1, 0.1, 0.3, 1), font_size=f"{user_font_size}sp", size_hint_y=None, halign='left', valign='middle')
        title_label.bind(width=lambda s, w: s.setter('text_size')(s, (w, None)))
        title_label.bind(texture_size=lambda s, z: s.setter('height')(s, z[1]))
        self.add_widget(title_label)
        date_label = Label(text=f"({date})", color=(0.5, 0.5, 0.5, 1), font_size=f"{user_font_size - 6}sp", size_hint_y=None, height=dp(20), halign='left', valign='middle')
        date_label.bind(width=lambda s, w: setattr(s, 'text_size', (w, None)))
        self.add_widget(date_label)
        desc_label = Label(text=description, color=(0.2, 0.2, 0.2, 1), font_size=f"{user_font_size - 3}sp", size_hint_y=None, halign='justify', markup=True)
        desc_label.bind(width=lambda s, w: s.setter('text_size')(s, (w, None)))
        desc_label.bind(texture_size=lambda s, z: s.setter('height')(s, z[1]))
        self.add_widget(desc_label)
        # La media_zone se base maintenant sur la liste nettoyée
        if self.image_list:
            media_zone = self._build_media_zone()
            if media_zone:
                self.add_widget(media_zone)
        self.bind(minimum_height=self.setter('height'))
        self.has_reached_end = False
        self._last_known_font_size = get_user_font_size()
        
    def on_parent(self, instance, value):
        if value is None:
            self.active = False
            for event in self._check_events:
                Clock.unschedule(event)
            self._check_events = []

    def _build_media_zone(self):
        if not self.image_list:
            return None
        carousel = Carousel(direction='right', loop=True, size_hint=(None, None), size=(dp(320), dp(220)))
        carousel.ignore_perpendicular_swipes = True
        carousel.move_threshold = dp(30)
        carousel.pos_hint = {'center_x': 0.5}
        app = App.get_running_app()
        total_images = len(self.image_list)
        for url in self.image_list:
            if not url:
                continue
            container = FloatLayout()
            container.bind(on_touch_up=self._on_image_touch)
            # 1. Image principale (masquée par défaut)
            img = Image(fit_mode="contain", opacity=0, size_hint=(1, 1))
            container.add_widget(img)
            # --- CORRECTION CRITIQUE : CAS OÙ L'URL EST DÉJÀ UN CHEMIN LOCAL ---
            if os.path.exists(url) and os.path.isfile(url):
                img.source = url
                img.opacity = 1
                img.reload()
                if total_images > 1:
                    badge = GalleryBadge(count=total_images - 1)
                    badge.pos_hint = {'right': 0.95, 'top': 0.95}
                    container.add_widget(badge)
                carousel.add_widget(container)
                continue # On passe directement à l'image suivante, pas de téléchargement !
            # 2. Préparation du Loader visuel si c'est bien une URL distante
            loader = Image(
                source=os.path.join(app.directory, "assets", "icons", "loading_wheel.png"),
                size_hint=(None, None), size=(dp(40), dp(40)),
                pos_hint={'center_x': 0.5, 'center_y': 0.5}
            )
            with loader.canvas.before:
                PushMatrix()
                loader.rot = Rotate(angle=0)
            with loader.canvas.after:
                PopMatrix()
                
            def update_rot_origin(*args, l=loader):
                l.rot.origin = l.center
            loader.bind(pos=update_rot_origin, size=update_rot_origin)
            
            def init_rot(dt, l=loader):
                l.rot.origin = l.center
            Clock.schedule_once(init_rot, 0.1)
            
            def spin_loader(dt, l=loader, card=self):
                if not l.parent or not card.active or not card.parent:
                    return False 
                l.rot.angle -= dt * 180
                return True
            # 3. Logique d'aiguillage Cache VS Réseau (pour les vraies URL)
            url_hash = hashlib.md5(url.encode()).hexdigest()
            local_path = os.path.join(app.cache_images_dir, f"img_{url_hash}.jpg")
            if os.path.exists(local_path):
                # CAS 1 : IMAGE DÉJÀ TÉLÉCHARGÉE
                img.source = local_path
                img.opacity = 1
                img.reload()
                if total_images > 1:
                    badge = GalleryBadge(count=total_images - 1)
                    badge.pos_hint = {'right': 0.95, 'top': 0.95}
                    container.add_widget(badge)
            else:
                # L'image n'est pas sur le disque, on ajoute le loader visuel
                container.add_widget(loader)
                loader.spin_event = Clock.schedule_interval(spin_loader, 1/30)
                # --- CORRECTION DU VERROU SYNCHRONISÉ ---
                if url in app.images_currently_downloading:
                    # CAS 2 : UNE AUTRE CARTE OU LE CENTRAL TÉLÉCHARGE DÉJÀ CETTE IMAGE !
                    def watch_file_appearance(dt, path=local_path, target_img=img, target_loader=loader):
                        if not self.active or not self.parent:
                            return False # Stop si la vue a changé
                        if os.path.exists(path):
                            self._on_download_complete(target_img, target_loader, path)
                            return False # Stopper l'écouteur
                        return True # Continuer à écouter
                    Clock.schedule_interval(watch_file_appearance, 0.2)
                else:
                    # CAS 3 : L'IMAGE N'EST PAS EN TRAIN D'ÊTRE TÉLÉCHARGÉE -> On s'en occupe
                    app.images_currently_downloading.add(url) # On pose le verrou global synchronisé
                    def request_download(target_url, path, target_img, target_loader):
                        try:
                            if not target_url.startswith(('http://', 'https://')):
                                print(f"[Alerte] URL invalide : {target_url}")
                                return
                            r = requests.get(target_url, timeout=10, verify=False)
                            if r.status_code == 200:
                                with open(path, 'wb') as f:
                                    f.write(r.content)
                                Clock.schedule_once(lambda dt: self._on_download_complete(target_img, target_loader, path))
                        except Exception as e:
                            print(f"Erreur telechargement : {e}")
                        finally:
                            # LIBÉRATION DU VERROU SYNCHRONISÉ quoi qu'il arrive
                            app.images_currently_downloading.discard(target_url)
                    threading.Thread(
                        target=request_download,
                        args=(url, local_path, img, loader),
                        daemon=True
                    ).start()
            carousel.add_widget(container)
        return carousel

    def _on_download_complete(self, img, loader, path):
        if not self.active: 
            return
        # Arrêt sécurisé du thread d'animation de la roue attaché au loader
        if hasattr(loader, 'spin_event'):
            Clock.unschedule(loader.spin_event)
            
        def finalize(dt):
            if not os.path.exists(path):
                print(f"Erreur : Fichier introuvable a {path}")
                return
            img.source = path
            img.reload()
            img.texture_update()
            img.opacity = 1
            if loader.parent:
                loader.parent.remove_widget(loader)
            if len(self.image_list) > 1 and img.parent:
                badge_exists = any(isinstance(child, GalleryBadge) for child in img.parent.children)
                if not badge_exists:
                    badge = GalleryBadge(count=len(self.image_list) - 1)
                    badge.pos_hint = {'right': 0.95, 'top': 0.95}
                    img.parent.add_widget(badge)
        Clock.schedule_once(finalize, 0.05)

    def _on_image_touch(self, instance, touch):
        if not instance.collide_point(*touch.pos):
            return False
        if abs(touch.dy) > dp(10):
            return False
        if abs(touch.dx) < dp(10) and abs(touch.dy) < dp(10):
            ImagePreview(img_sources=self.image_list).open()
            return True
        return False

    def _update_rect(self, instance, value):
        self.bg_rect.pos = instance.pos
        self.bg_rect.size = instance.size

class HomeScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # 1. États
        self.last_config_hash = None
        self.is_generating = False
        self.is_updating = False
        self.is_fetching_remote = False
        self._generation_token = 0
        # SUPPRESSON MECANISME PULL TO REFRESH
        #self._is_refreshing = False 
        self.KIVY_BLUE = (30/255, 58/255, 138/255, 1)
        self.current_max_days = self._get_step_days()
        self.filtered_news_cache = []   
        self.displayed_titles_set = set() 
        self.has_reached_end = False
        self._last_known_font_size = get_user_font_size()
        # 2. Structure principale
        self.main_layout = FloatLayout() 
        self.container = BoxLayout(orientation="vertical")
        with self.container.canvas.before:
            Color(*self.KIVY_BLUE)
            self.rect_bg = Rectangle(pos=self.container.pos, size=self.container.size)
        self.container.bind(pos=self._update_bg, size=self._update_bg)
        # 3. Création du ScrollView
        self.scroll = ScrollView(
            size_hint=(1, 1),
            do_scroll_x=False,
            bar_width=0,
            scroll_type=['content'],
            always_overscroll=True
        )
        self.scroll.scroll_distance = dp(20)
        self.scroll_content = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(20), padding=[0, dp(20), 0, dp(100)])
        self.scroll_content.bind(minimum_height=self.scroll_content.setter('height'))
        # SUPPRESSON MECANISME PULL TO REFRESH
        #self.scroll.effect_y.bind(overscroll=self._check_refresh)
        self.banner = Image(source="assets/banniere.png", size_hint=(1, None), height=dp(200), fit_mode="contain")
        self.banner.bind(width=lambda inst, val: setattr(inst, 'height', val *  0.39375))
        self.scroll_content.add_widget(self.banner)
        self.news_layout = BoxLayout(
            orientation="vertical", 
            size_hint_y=None, 
            spacing=dp(20), 
            padding=[dp(15), dp(10), dp(15), 0]
        )
        self.news_layout.bind(minimum_height=self.news_layout.setter('height'))
        self.scroll_content.add_widget(self.news_layout)
        self.footer_layout = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(15), padding=[0, dp(10), 0, dp(20)])
        self.footer_layout.bind(minimum_height=self.footer_layout.setter('height'))
        # Gestion dynamique de la police utilisateur
        app = App.get_running_app()
        user_font_size = 18
        if app and hasattr(app, 'config') and app.config.has_section('User'):
            try: user_font_size = app.config.getint('User', 'font_size_factor')
            except: pass
        self.no_news_label = Label(text="Aucune actualité.", size_hint_y=None, height=dp(30), opacity=0)
        self.period_status_label = Label(text="", size_hint_y=None, height=dp(35), font_size="18sp")
        self.more_btn = Button(
            text="Plus d'actualités", 
            size_hint=(None, None), 
            size=(dp(260), dp(55)), 
            pos_hint={'center_x': 0.5},
            font_size="18sp",
            bold=True
        )
        self.more_btn.bind(on_release=self.load_next_period)
        self.footer_layout.add_widget(self.no_news_label)
        self.footer_layout.add_widget(self.period_status_label)
        self.footer_layout.add_widget(self.more_btn)
        self.spacer = Widget(size_hint_y=None, height=dp(100))
        self.footer_layout.add_widget(self.spacer)
        self.scroll_content.add_widget(self.footer_layout)
        self.scroll.add_widget(self.scroll_content)
        self.container.add_widget(self.scroll)
        # Loader
        self.main_loader = Image(source="assets/icons/loading_wheel.png", size_hint=(None, None), size=(dp(50), dp(50)), pos_hint={'center_x': 0.5, 'top': 0.98}, opacity=0)
        with self.main_loader.canvas.before:
            PushMatrix()
            self.main_rot = Rotate(angle=0)
        with self.main_loader.canvas.after:
            PopMatrix()
        self.main_loader.bind(center=lambda inst, val: setattr(self.main_rot, 'origin', inst.center))
        self.main_layout.add_widget(self.container)
        self.main_layout.add_widget(self.main_loader)
        self.add_widget(self.main_layout)
    # SUPPRESSON MECANISME PULL TO REFRESH
#===============================================================================
#     def _check_refresh(self, *args):
#         if self._is_refreshing:
#             return
#         overscroll = self.scroll.effect_y.overscroll
#         if overscroll < -dp(70):
#             self._is_refreshing = True
#             self.manual_refresh()
# 
#     def manual_refresh(self):
#         self.show_main_loader(True)
#         def run_refresh():
#             app = App.get_running_app()
#             if hasattr(app, 'load_remote_config'):
#                 app.load_remote_config()
#             Clock.schedule_once(lambda dt: self.finish_refresh(), 0.5)
#         threading.Thread(target=run_refresh, daemon=True).start()
#     
#     def finish_refresh(self):
#         print(
#             f"[REFRESH FINISH] "
#             f"children={len(self.news_layout.children)} | "
#             f"is_updating={self.is_updating} | "
#             f"is_generating={self.is_generating}"
#         )
#         updated = self.update_ui_from_config(force=False)
#         if not updated:
#             self.show_main_loader(False)
#         self._is_refreshing = False
#===============================================================================
        
    def show_main_loader(self, show):
        self.main_loader.opacity = 1 if show else 0
        if show: Clock.schedule_interval(self._rotate_loader, 1/30)
        else: Clock.unschedule(self._rotate_loader)

    def _rotate_loader(self, dt): 
        self.main_rot.angle -= 6
    
    def force_stop_loader(self, dt):
        if self.main_loader.opacity > 0: self.show_main_loader(False)

    def _get_step_days(self):
        app = App.get_running_app()
        if app and hasattr(app, 'config') and app.config.has_section('User'):
            try: return app.config.getint('User', 'news_period')
            except: pass
        return 15 

    def load_next_period(self, instance):
        if (self.is_generating or self.is_updating or self.has_reached_end):
            return
        old_signature = self._build_news_signature(self.filtered_news_cache)
        self.current_max_days += self._get_step_days()
        self.show_main_loader(True)
        self.is_generating = True
        app = App.get_running_app()
        def background_period_check():
            try:
                if hasattr(app, 'load_remote_config'): 
                    #app.load_remote_config()
                    print(f"[DEBUG] Simple elargissement du filtre de date sur les donnees deja telechargees et en memoire")
                    
            finally:
                raw_news = app.app_config.get("fcvv", {}).get("appli", {}).get("news", []) if hasattr(app, "app_config") else []
                self._filter_news_by_date(raw_news)
                new_signature = self._build_news_signature(self.filtered_news_cache)
                if new_signature == old_signature:
                    Clock.schedule_once(lambda dt: self._finish_no_new_period(), 0)
                    return
                # Génération des nouvelles cartes sans effacer l'existant
                Clock.schedule_once(lambda dt: self._generate_news_ui(clear_all=False), 0.1)
        threading.Thread(target=background_period_check, daemon=True).start()
        
    def _finish_no_new_period(self):
        self.is_generating = False
        self.show_main_loader(False)
        self.period_status_label.text = f"Période affichée : {self.current_max_days} derniers jours"
        # CORRECTION : Même s'il n'y a pas de nouvelles actus à ajouter dans la période supérieure, 
        # la signature de base a changé (car la liste filtrée intègre virtuellement la plage temporelle). 
        # On synchronise le hash pour pérenniser le verrou.
        self.last_config_hash = self._build_news_signature(self.filtered_news_cache)
        if self.has_reached_end:
            self.more_btn.disabled = True
            self.more_btn.text = "Fin des actualités"

    def _update_bg(self, instance, value):
        self.rect_bg.pos = instance.pos
        self.rect_bg.size = instance.size
        
    def update_ui_from_config(self, *args, force=False):
        
        if self.is_updating:
            return False
        app = App.get_running_app()
        has_config = hasattr(app, "app_config") and bool(app.app_config)
        if not has_config:
            Clock.schedule_once(lambda dt: self.update_ui_from_config(force=force), 0.5)
            return False
        # --- MISE À JOUR DYNAMIQUE DES POLICES DU FOOTER ---
        current_font_size = get_user_font_size()
        self.no_news_label.font_size = f"{current_font_size - 2}sp"
        self.period_status_label.font_size = f"{current_font_size}sp"
        self.more_btn.font_size = f"{current_font_size}sp"
        # --- CORRECTION 1 : Récupérer le réglage utilisateur actuel ---
        configured_step = self._get_step_days()
        period_changed = False
        if self.current_max_days == 0 or (force and self.current_max_days != configured_step):
            self.current_max_days = configured_step
            period_changed = True
        fcvv_data = app.app_config.get("fcvv", {})
        news_list = fcvv_data.get("appli", {}).get("news", [])
        self._filter_news_by_date(news_list)
        current_hash = self._build_news_signature(self.filtered_news_cache)
        num_children = len(self.news_layout.children)
        # --- CORRECTION 2 : ANTI-FLASH INTELLIGENT ---
        # Si la police a changé, on force le rechargement même si le hash des actus est identique
        font_size_changed = getattr(self, '_last_known_font_size', 18) != current_font_size
        if font_size_changed:
            self._last_known_font_size = current_font_size
            force = True
        if current_hash == getattr(self, 'last_config_hash', None) and num_children > 0 and not period_changed and not force:
            self.is_updating = False
            self.show_main_loader(False)
            return False
        self.is_updating = True
        # Un seul token créé pour cette génération
        self._generation_token += 1
        generation_token = self._generation_token
        self.show_main_loader(True)
        def start_generation(dt):
            # La demande a peut-être été remplacée entre-temps
            if generation_token != self._generation_token:
                return
            try:
                self._generate_news_ui(clear_all=True,generation_token=generation_token)
            except Exception as e:
                print(f"[UI GENERATION ERROR] {e}")
                self._finish_news_generation(generation_token)
        Clock.schedule_once(start_generation, 0.1)
        return True
    
    def _check_data_changes(self, dt=None):
        """Compare les données actuelles avec celles affichées.
        Ajoute des logs détaillés et réessaie si une opération est en cours.
        """
        try:
            # ---------------------------------------------------------
            # 1. Vérifier l'application
            # ---------------------------------------------------------
            app = App.get_running_app()
            if not app:
                print("[HOME CHECK][ERREUR] App.get_running_app() retourne None")
                return
            if getattr(app, "is_fetching_remote", False):
                Clock.schedule_once(self._check_data_changes, 0.5)
                return
            app_config = getattr(app, "app_config", None)
            if not app_config:
                Clock.schedule_once(self._check_data_changes, 0.5)
                return
            if self.is_updating or self.is_generating:
                Clock.schedule_once(self._check_data_changes, 0.5)
                return
            configured_step = self._get_step_days()
            current_font_size = get_user_font_size()
            period_changed = self.current_max_days != configured_step
            font_changed = (
                getattr(self, "_last_known_font_size", None)
                != current_font_size
            )
            if period_changed:
                self.current_max_days = configured_step
            if font_changed:
                self._last_known_font_size = current_font_size
            news_list = (app_config.get("fcvv", {}).get("appli", {}).get("news", []))
            if not isinstance(news_list, (list, tuple)):
                return
            previous_cache_count = len(getattr(self, "filtered_news_cache", []))
            self._filter_news_by_date(news_list)
            filtered_count = len(self.filtered_news_cache)
            current_hash = self._build_news_signature(self.filtered_news_cache)
            hash_changed = current_hash != self.last_config_hash
            force_update = (period_changed or font_changed or hash_changed)
            if len(self.news_layout.children) == 0:
                force_update = True
            if force_update:
                self.show_main_loader(True)
                result = self.update_ui_from_config(force=True)
            else:
                self.show_main_loader(False)
        except Exception as exc:
            import traceback
            traceback.print_exc()
        finally:
            print("[HOME CHECK] <<< FIN DE LA VERIFICATION")
    
    def _build_news_signature(self, news_list):
        if not news_list:
            return "empty"
    
        stable_data = []
        for item in news_list:
            if isinstance(item, dict):
                # On ne conserve que les champs stables/textuels de chaque news
                stable_data.append({
                    "id": str(item.get("id") or item.get("title") or ""),
                    "date": str(item.get("date") or ""),
                    "title": str(item.get("title") or ""),
                    "summary": str(item.get("summary") or item.get("content") or ""),
                    "description": str(item.get("description") or ""),
                    "images": item.get("images") or item.get("image") or [],
                    "type": str(item.get("type") or "")
                })
    
        return hashlib.md5(json.dumps(stable_data, sort_keys=True).encode("utf-8")).hexdigest()
    
    def on_enter(self, *args):
        """Vérifie les mises à jour à l'entrée sur Home."""
        print("[HOME LIFECYCLE] on_enter")
        app = App.get_running_app()
        if app is None:
            print("[HOME LIFECYCLE] Application indisponible")
            return
        if len(self.news_layout.children) == 0:
            self.show_main_loader(True)
        # Si un téléchargement réseau est déjà en cours, on ne fait rien pour éviter les doublons
        if getattr(app, "is_fetching_remote", False):
            print("[HOME LIFECYCLE] Telechargement reseau deja en cours.")
            return
        Clock.schedule_once(self._check_data_changes, 0.2)
        # Et on lance la vérification réseau en arrière-plan au cas où le serveur a changé entre-temps
        app.start_network_tasks()
    
    def on_resume(self, *args):
        """Vérifie les actualités au retour au premier plan."""
        print("[HOME] Retour au premier plan")
        # On délègue à _check_data_changes qui gère déjà les états d'attente (is_fetching_remote, etc.)
        Clock.schedule_once(self._check_data_changes, 0.5)
    
    def _finish_news_generation(self, generation_token=None, dt=None):
        """Termine uniquement la génération active."""
        if generation_token is None:
            print("[GEN FINISH] Token absent : finalisation ignoree")
            return
        if generation_token != self._generation_token:
            print(f"[GEN FINISH IGNORED] token={generation_token} | active={self._generation_token}")
            return
        generation_hash = getattr(self, "_active_generation_hash", None)
        self.is_generating = False
        self.is_updating = False
        self.show_main_loader(False)
        self.period_status_label.text = (f"Période affichée : {self.current_max_days} derniers jours")
        self.more_btn.disabled = self.has_reached_end
        self.more_btn.text = (
            "Fin des actualités"
            if self.has_reached_end
            else "Plus d'actualités"
        )
        self.no_news_label.opacity = (1 if len(self.news_layout.children) == 0 else 0)
        if generation_hash is not None:
            self.last_config_hash = generation_hash
    
    # ================= FUSION UNIQUE ET NETTOYAGE =================
    def _generate_news_ui(self, clear_all=True, generation_token=None):
        # Pour les appels qui ne viennent pas de update_ui_from_config,
        # notamment load_next_period, créer un nouveau token.
        if generation_token is None:
            self._generation_token += 1
            generation_token = self._generation_token
        # Refuser toute génération devenue obsolète
        elif generation_token != self._generation_token:
            return
        Clock.unschedule(self.force_stop_loader)
        # ============================================================
        # DEBUG : IDENTIFIANT UNIQUE DE GENERATION
        # ============================================================
        self._debug_generation_id = getattr(self, '_debug_generation_id', 0) + 1
        generation_id = self._debug_generation_id
        # Figer les actualités utilisées pour cette génération
        generation_news = list(self.filtered_news_cache)
        # Calculer leur signature une seule fois
        generation_hash = self._build_news_signature(generation_news)
        self._active_generation_hash = generation_hash
        # ============================================================
        self.is_generating = True
        if clear_all:
            self.news_layout.clear_widgets()
            self.displayed_titles_set = set()
            self._last_section_period = None
        seen = set()
        queue = []
        # ============================================================
        # PREPARATION DE LA QUEUE
        # ============================================================
        for item in generation_news:
            if not isinstance(item, dict):
                print(f"[UI WARNING] Actualite invalide ignoree : {item!r}")
                continue
            try:
                key = hashlib.md5(f"{item.get('title','')}{item.get('date','')}".encode()).hexdigest()
                if (key not in seen and key not in self.displayed_titles_set):
                    seen.add(key)
                    queue.append((key, item))
            except Exception as e:
                print(f"[UI ERROR] Preparation d'une actualite impossible : {e}")
        # ============================================================
        if not queue:
            self._finish_news_generation(generation_token)
            return
        self.no_news_label.opacity = 0
        # ============================================================
        # RECUPERATION DYNAMIQUE DE LA LANGUE ET DES MOIS
        # ============================================================
        app = App.get_running_app()
        current_lang = getattr(app,'current_language','Francais')
        month_names = LANGUAGES.get(current_lang,{}).get('months',LANGUAGES.get('Francais',{}).get('months',{}))
        # ============================================================
        # GENERATION DES CARTES
        # ============================================================
        def process_next_card(dt):
            if generation_token != self._generation_token: 
                return False
            # ========================================================
            if not queue or not self.is_generating:
                self._finish_news_generation(generation_token)
                return False
            # =======================================================
            # GENERATION D'UNE CARTE
            # ========================================================
            key, item = queue.pop(0)
            self.displayed_titles_set.add(key)
            try:
                # ----------------------------------------------------
                # LOGIQUE D'INJECTION DU TITRE DE MOIS
                # ----------------------------------------------------
                item_date = self._parse_date(item.get("date", ""))
                if item_date != datetime.min:
                    month_str = month_names.get(item_date.month,"")
                    period_title = (f"{month_str} {item_date.year}")
                    if (getattr(self,'_last_section_period',None) != period_title):
                        self._last_section_period = period_title
                        separator = MonthSeparator(month_text=period_title,padding=[dp(5), dp(10)])
                        self.news_layout.add_widget(separator)
                # ----------------------------------------------------
                # CREATION DE LA CARTE
                # ----------------------------------------------------
                card = NewsCard(title=item.get("title", ""),date=item.get("date", ""),description=item.get("description", ""),images=item.get("images") or item.get("image", []))
                self.news_layout.add_widget(card)
            except Exception as e:
                print(f"[UI ERROR] Generation carte #{generation_id} : {e}")
            return True
        # ============================================================
        # LANCEMENT DU CALLBACK
        # ============================================================
        def safe_process_next_card(dt):
            if generation_token != self._generation_token:
                return False
            try:
                result = process_next_card(dt)
                # La génération est terminée.
                if result is False:
                    return False
                return True
            except Exception as e:
                self._finish_news_generation(generation_token)
                return False
        Clock.schedule_interval(safe_process_next_card, 1 / 50)

    def _filter_news_by_date(self, raw_news_list):
        self.has_reached_end = False
        now = datetime.now()
        limit_date = now - timedelta(days=self.current_max_days)
        self.filtered_news_cache = []
        oldest_date = now
        valid_dates_found = False
        for item in raw_news_list:
            item_date = self._parse_date(item.get("date", ""))
            if item_date != datetime.min:
                valid_dates_found = True
                if item_date < oldest_date: oldest_date = item_date
                if item_date >= limit_date: self.filtered_news_cache.append(item)
        if valid_dates_found and limit_date < oldest_date:
            self.has_reached_end = True

    def _parse_date(self, date_str):
        try: return datetime.strptime(date_str.strip(), "%d/%m/%Y")
        except: return datetime.min
