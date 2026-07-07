# -*- coding: utf-8 -*-
import webbrowser
from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView
from kivy.graphics import Color, Rectangle
from kivy.app import App
from kivy.metrics import dp
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.image import Image
from kivy.uix.widget import Widget

def _(key):
    app = App.get_running_app()
    if hasattr(app, '_'):
        return app._(key)
    return key

# --- CLASSE ICONBUTTON SANS FOND (TRANSPARENTE) ---
class IconButton(ButtonBehavior, Image):
    """Bouton image simple sans fond."""
    def __init__(self, url, source, **kwargs):
        super().__init__(**kwargs)
        self.source = source
        self.target_url = url
    
    def on_release(self):
        if self.target_url:
            webbrowser.open(self.target_url)

# --- CLASSE PRINCIPALE INFO ---
class InfoScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        self.KIVY_BLUE = (30/255, 58/255, 138/255, 1)
        self.LIGHT_GRAY = (0.9, 0.9, 0.9, 1)
        self.TEXT_BLACK = (0, 0, 0, 1)

        self.root = BoxLayout(orientation='vertical')
        with self.root.canvas.before:
            Color(*self.KIVY_BLUE)
            self.rect_bg = Rectangle(pos=self.root.pos, size=self.root.size)
        self.root.bind(pos=self._update_bg, size=self._update_bg)

        self.scroll = ScrollView(do_scroll_x=False)
        p_side = dp(25) 
        
        self.scroll_content = BoxLayout(
            orientation='vertical', 
            padding=[p_side, dp(20), p_side, dp(40)], 
            spacing=dp(15),  # Légèrement augmenté pour l'aération globale
            size_hint_y=None
        )
        self.scroll_content.bind(minimum_height=self.scroll_content.setter('height'))

        self.scroll.add_widget(self.scroll_content)
        self.root.add_widget(self.scroll)
        self.add_widget(self.root)

    def _update_bg(self, instance, value):
        self.rect_bg.pos = instance.pos
        self.rect_bg.size = instance.size

    def on_enter(self):
        self.rebuild_ui()

    def rebuild_ui(self):
        self.scroll_content.clear_widgets()
        app = App.get_running_app()
        user_size = 20
        if hasattr(app, 'config') and app.config.has_section('User'):
            user_size = int(app.config.get('User', 'font_size_factor', fallback=20))

        # --- SECTION 1 : CLUB FCVV ---
        self.scroll_content.add_widget(self._create_section_title(_('club_fcvv'), user_size + 2))
        addr_club = "FC Valdahon Vercel\nRue du Stade\n25800 Valdahon\nTel: +33 3 81 56 24 79"
        self.scroll_content.add_widget(self._create_text_label(addr_club, user_size))
        
        # Social Icons - Taille dp(80) et espacement dp(40) pour le confort
        social_box = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(90), spacing=dp(40))
        social_box.add_widget(Widget())
        social_box.add_widget(IconButton(url="https://www.facebook.com/fcvaldahonvercel/", source="assets/icons/facebook.png", size_hint=(None, None), size=(dp(80), dp(80))))
        social_box.add_widget(IconButton(url="https://www.instagram.com/fc_valdahon_vercel/", source="assets/icons/instagram.png", size_hint=(None, None), size=(dp(80), dp(80))))
        social_box.add_widget(Widget())
        self.scroll_content.add_widget(social_box)

        # --- SECTION 2 : LE TOURNOI ---
        self.scroll_content.add_widget(BoxLayout(size_hint_y=None, height=dp(15)))
        self.scroll_content.add_widget(self._create_section_title(_('the_tournament'), user_size + 2))
        # Icône Facebook Tournoi agrandie à dp(80)
        fb_tournoi = IconButton(url="https://www.facebook.com/TournoideVercel/", source="assets/icons/facebook.png", size_hint=(None, None), size=(dp(80), dp(80)))
        fb_tournoi.pos_hint = {'center_x': 0.5}
        self.scroll_content.add_widget(fb_tournoi)

        # --- SECTION 3 : ACCÈS AU GYMNASE ---
        self.scroll_content.add_widget(BoxLayout(size_hint_y=None, height=dp(15)))
        self.scroll_content.add_widget(self._create_section_title(_('gym_access'), user_size + 2))
        addr_gym = "Gymnase\n18 Rue du Stade\n25530 Vercel Villedieu Le Camp"
        self.scroll_content.add_widget(self._create_text_label(addr_gym, user_size))
        
        # Icône Google Maps agrandie à dp(80)
        maps_icon = IconButton(url="https://www.google.com/maps/search/?api=1&query=Gymnase+18+Rue+du+Stade+25530+Vercel+Villedieu+Le+Camp", source="assets/icons/google_maps.png", size_hint=(None, None), size=(dp(80), dp(80)))
        maps_icon.pos_hint = {'center_x': 0.5}
        self.scroll_content.add_widget(maps_icon)

    def _create_section_title(self, text, size):
        l = Label(
            text=f"[b]{text}[/b]", 
            markup=True, font_size=f"{size+2}sp", color=(1, 0.9, 0, 1),
            size_hint_y=None, height=dp(45),
            halign='center', valign='bottom'
        )
        l.bind(size=lambda inst, val: setattr(inst, 'text_size', val))
        return l

    def _create_text_label(self, text, size):
        l = Label(
            text=text, 
            halign='center', valign='top', 
            font_size=f"{size}sp", 
            size_hint_y=None,
            line_height=1.1
        )
        l.bind(width=lambda inst, width_val: setattr(inst, 'text_size', (width_val, None)))
        l.bind(texture_size=lambda inst, size_val: setattr(inst, 'height', size_val[1] + dp(10)))
        return l

    def _create_link_button(self, text, url, size):
        return LinkButton(
            url=url,
            text=text,
            size_hint_y=None, 
            height=dp(60),
            background_normal='',
            background_color=self.LIGHT_GRAY,
            color=self.TEXT_BLACK,
            bold=True,
            font_size=f"{size+1}sp"
        )