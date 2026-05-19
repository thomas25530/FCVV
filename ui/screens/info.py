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

# Fonction de traduction locale
def _(key):
    app = App.get_running_app()
    if hasattr(app, '_'):
        return app._(key)
    return key


# --- SÉCURISATION DES BOUTONS DE LIENS (ZÉRO LEAK RAM) ---
class LinkButton(Button):
    """Bouton personnalisé qui stocke son URL sans closure instable."""
    def __init__(self, url, **kwargs):
        super().__init__(**kwargs)
        self.target_url = url
        self.bind(on_release=self._open_link)

    def _open_link(self, instance):
        if self.target_url:
            webbrowser.open(self.target_url)


# --- CLASSE PRINCIPALE INFO ---
class InfoScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        app = App.get_running_app()
        self.is_apk = getattr(app, 'generate_APK', False)
        
        self.KIVY_BLUE = (30/255, 58/255, 138/255, 1)
        self.LIGHT_GRAY = (0.9, 0.9, 0.9, 1)
        self.TEXT_BLACK = (0, 0, 0, 1)

        self.root = BoxLayout(orientation='vertical')
        with self.root.canvas.before:
            Color(*self.KIVY_BLUE)
            self.rect_bg = Rectangle(pos=self.root.pos, size=self.root.size)
        self.root.bind(pos=self._update_bg, size=self._update_bg)

        self.scroll = ScrollView(do_scroll_x=False)
        p_side = dp(20) if self.is_apk else dp(30)
        
        self.scroll_content = BoxLayout(
            orientation='vertical', 
            padding=[p_side, dp(20), p_side, dp(40)], 
            spacing=dp(10), 
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

        # --- SECTION 1 : CLUB FCVV (HAUT) ---
        self.scroll_content.add_widget(self._create_section_title(_('club_fcvv'), user_size + 2))
        
        addr_club = "FC Valdahon Vercel\nRue du Stade\n25800 Valdahon\nTel: +33 3 81 56 24 79"
        self.scroll_content.add_widget(self._create_text_label(addr_club, user_size))
        
        self.scroll_content.add_widget(BoxLayout(size_hint_y=None, height=dp(5)))
        self.scroll_content.add_widget(self._create_link_button(f"f - {_('fb_club')}", "https://www.facebook.com/fcvaldahonvercel/", user_size))
        self.scroll_content.add_widget(self._create_link_button("Instagram", "https://www.instagram.com/fc_valdahon_vercel/", user_size))

        # --- SECTION 2 : LE TOURNOI (MILIEU) ---
        self.scroll_content.add_widget(BoxLayout(size_hint_y=None, height=dp(10)))
        self.scroll_content.add_widget(self._create_section_title(_('the_tournament'), user_size + 2))
        self.scroll_content.add_widget(self._create_link_button(f"f - {_('fb_tournament')}", "https://www.facebook.com/TournoideVercel/", user_size))

        # --- SECTION 3 : ACCÈS AU GYMNASE (BAS) ---
        self.scroll_content.add_widget(BoxLayout(size_hint_y=None, height=dp(10)))
        self.scroll_content.add_widget(self._create_section_title(_('gym_access'), user_size + 2))
        
        addr_gym = "Gymnase\n18 Rue du Stade\n25530 Vercel Villedieu Le Camp"
        self.scroll_content.add_widget(self._create_text_label(addr_gym, user_size))
        
        self.scroll_content.add_widget(BoxLayout(size_hint_y=None, height=dp(5)))
        self.scroll_content.add_widget(self._create_link_button(_('open_maps'), "https://maps.google.com/?q=18+Rue+du+Stade+25530+Vercel", user_size))

    # --- HELPERS DE CRÉATION OPTIMISÉS ---

    def _create_section_title(self, text, size):
        h_val = dp(45) if self.is_apk else dp(30)
        l = Label(
            text=f"[b]{text}[/b]", 
            markup=True, font_size=f"{size+2}sp", color=(1, 0.9, 0, 1),
            size_hint_y=None, height=h_val, 
            halign='center', valign='bottom'
        )
        l.bind(size=lambda inst, val: setattr(inst, 'text_size', val))
        return l

    def _create_text_label(self, text, size):
        # Utilisation du moteur text_size + texture_size natif de Kivy pour calculer la hauteur exacte au pixel près
        l = Label(
            text=text, 
            halign='center', valign='top', 
            font_size=f"{size}sp", 
            size_hint_y=None,
            line_height=1.1
        )
        # 1. On lie la largeur de la zone de rendu de texte à celle du widget
        l.bind(width=lambda inst, width_val: setattr(inst, 'text_size', (width_val, None)))
        # 2. On ajuste dynamiquement la hauteur réelle du widget par rapport à la hauteur générée par sa texture
        l.bind(texture_size=lambda inst, size_val: setattr(inst, 'height', size_val[1] + dp(10)))
        return l

    def _create_link_button(self, text, url, size):
        btn_h = dp(80) if self.is_apk else dp(50)
        return LinkButton(
            url=url,
            text=text,
            size_hint_y=None, height=btn_h,
            background_normal='',
            background_color=self.LIGHT_GRAY,
            color=self.TEXT_BLACK,
            bold=True,
            font_size=f"{size+1}sp"
        )