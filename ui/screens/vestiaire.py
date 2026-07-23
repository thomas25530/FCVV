# -*- coding: utf-8 -*-
import os
import sys
import yaml
import requests
import threading
import hashlib
import logging
import json
import webbrowser
from kivy.uix.screenmanager import Screen
from kivy.uix.scrollview import ScrollView
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.widget import Widget
from kivy.graphics import Color, Rectangle, RoundedRectangle
from kivy.clock import Clock
from kivy.app import App
from kivy.metrics import dp, sp
from kivy.animation import Animation
from kivy.core.window import Window
from kivy.core.text import Label as CoreLabel
from datetime import datetime
# Dans le haut de votre fichier vestiaire.py, assurez-vous d'avoir :
from kivy.uix.spinner import Spinner, SpinnerOption
from kivy.uix.textinput import TextInput
from kivy.utils import escape_markup
from kivy.uix.popup import Popup
from kivy.uix.gridlayout import GridLayout
from kivy.uix.checkbox import CheckBox

def get_user_font_size():
    app = App.get_running_app()
    return app.config.getint('User', 'font_size_factor', fallback=18) if hasattr(app, 'config') else 18

class MessageBubble(BoxLayout):
    def __init__(self, msg_data, is_me, show_author=True, est_admin=False, font_size=15, **kwargs):
        super().__init__(orientation='vertical', size_hint_y=None, padding=[0, dp(2)], **kwargs)
        self.bind(minimum_height=self.setter('height'))
        self.padding = [dp(10), 0, dp(60), 0] if is_me else [dp(60), 0, dp(10), 0]

        self.bubble = BoxLayout(orientation='vertical', spacing=dp(4), padding=[dp(12), dp(8)], 
                                size_hint=(None, None))
        
        # Logique de couleur : Admin est prioritaire, puis 'is_me'
        if est_admin:
            bg, name_c = ((0.8, 0.5, 0, 1), (1, 1, 1, 1)) # Fond Orange, Texte Blanc
        elif is_me:
            bg, name_c = ((0.1, 0.55, 1, 1), (0.85, 0.93, 1, 1))
        else:
            bg, name_c = ((0.22, 0.22, 0.22, 1), (1, 0.85, 0.4, 1))
        
        with self.bubble.canvas.before:
            Color(*bg)
            self.bubble.rect = RoundedRectangle(pos=self.bubble.pos, size=self.bubble.size, radius=[dp(16)])
        self.bubble.bind(pos=lambda i, v: setattr(self.bubble.rect, "pos", v), size=lambda i, v: setattr(self.bubble.rect, "size", v))

        # 1. Auteur
        if show_author:
            # Si admin, on ajoute un petit tag visuel si besoin
            auth_text = f"[b]{escape_markup(msg_data.get('auteur',''))}[/b]"
            if est_admin: auth_text = f"[b][!] {auth_text.replace('[b]', '').replace('[/b]', '')}[/b]"
            
            self.author = Label(text=auth_text, markup=True, color=name_c, 
                                font_size=f"{max(10, font_size-3)}sp", size_hint=(None, None))
            self.bubble.add_widget(self.author)

        # 2. Contenu
        self.content = Label(
            text=msg_data.get("contenu", ""), 
            markup=True, 
            font_size=f"{max(10, font_size - 2)}sp", 
            size_hint=(None, None), 
            halign="left", 
            valign="top",
            text_size=(Window.width * 0.85 - dp(40), None)
        )
        self.bubble.add_widget(self.content)
        
        # 3. Timestamp
        dt = datetime.fromisoformat(msg_data.get('timestamp', '').replace('Z', '+00:00')) if msg_data.get('timestamp') else None
        ts_str = dt.strftime("%H:%M") if dt else ""
        self.timestamp = Label(text=f"[color={'FFFFFF' if is_me or est_admin else 'AAAAAA'}]{ts_str}[/color]", 
                               markup=True, size_hint=(None, None), height=dp(15), halign="right")
        self.bubble.add_widget(self.timestamp)

        Clock.schedule_once(self.finalize_layout, 0)
        self.add_widget(self.bubble)

    def finalize_layout(self, *args):
        self.content.text_size = (self.content.text_size[0], None)
        self.content.size = self.content.texture_size
        if hasattr(self, 'author'):
            self.author.size = self.author.texture_size
        self.timestamp.size = self.timestamp.texture_size

        max_content_w = max(self.content.width, self.timestamp.width)
        if hasattr(self, 'author'):
            max_content_w = max(max_content_w, self.author.width)
            
        self.bubble.width = max_content_w + dp(40)
        h_auth = self.author.height if hasattr(self, 'author') else 0
        self.bubble.height = self.content.height + self.timestamp.height + h_auth + dp(30)

class StyledCard(BoxLayout):
    def __init__(self, bg_color=(1, 1, 1, 0.1), **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.padding = dp(15)
        self.spacing = dp(10)
        self.size_hint_y = None
        self.bind(minimum_height=self.setter('height'))
        with self.canvas.before:
            Color(*bg_color)
            self.rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(15),])
        self.bind(pos=self._update_rect, size=self._update_rect)

    def _update_rect(self, *args):
        self.rect.pos = self.pos
        self.rect.size = self.size

class InfoCard(StyledCard):
    def __init__(self, text, **kwargs):
        super().__init__(bg_color=(0.1, 0.3, 0.5, 0.2), **kwargs)
        fs = get_user_font_size()
        
        # Titre de la carte
        self.add_widget(Label(
            text="[b]NOTE DU COACH[/b]", 
            markup=True, 
            font_size=f"{fs}sp", 
            color=(0.97, 0.92, 0.24, 1), 
            size_hint_y=None, 
            height=dp(35)
        ))
        
        # Corps du texte (Correction : ajout de markup=True pour interpréter [i], [b], etc.)
        lbl = Label(
            text=text, 
            markup=True,  # INDISPENSABLE pour que [i] fonctionne
            halign="left", 
            valign="top", 
            font_size=f"{fs-2}sp", 
            size_hint_y=None
        )
        
        # Liaison pour forcer le retour à la ligne automatique (wrap)
        lbl.bind(width=lambda i, w: setattr(i, 'text_size', (w, None)))
        
        # Liaison pour ajuster dynamiquement la hauteur selon le contenu
        lbl.bind(texture_size=lambda i, v: setattr(i, 'height', v[1]))
        
        self.add_widget(lbl)

class ConvocationCard(StyledCard):
    def __init__(self, data, **kwargs):
        super().__init__(bg_color=(0.06, 0.4, 0.3, 0.2), **kwargs)
        fs = get_user_font_size()
        details = BoxLayout(orientation='vertical', spacing=dp(5), size_hint_y=None)
        details.bind(minimum_height=details.setter('height'))

        def create_label(text, font_size, color=(1, 1, 1, 1), height=dp(30)):
            lbl = Label(text=text, markup=True, font_size=f"{font_size}sp", color=color, size_hint_y=None, height=height, halign='left', valign='middle', size_hint_x=1)
            lbl.bind(width=lambda i, w: setattr(i, 'text_size', (w, None)))
            return lbl

        details.add_widget(create_label(text=f"[b]Contre :[/b] {data.get('adversaire', 'À définir')}", font_size=fs))
        details.add_widget(create_label(text=f"[b]Date :[/b] {data.get('date', 'N/C')}", font_size=fs-2))
        details.add_widget(create_label(text=f"[b]RDV :[/b] {data.get('heure_rdv', 'N/C')}",font_size=fs-2,color=(1, 0.7, 0.7, 1)))
        details.add_widget(create_label(text=f"[b]Coup d'envoi :[/b] {data.get('heure_match', 'N/C')}",font_size=fs-2,color=(1, 0.7, 0.7, 1)))
        details.add_widget(create_label(text=f"[b]Lieu :[/b] {data.get('lieu', 'N/C')}", font_size=fs-2))
        details.add_widget(create_label(text=f"[b]Entraîneurs :[/b] {data.get('entraineurs', 'N/C')}", font_size=fs-2))
        self.add_widget(details)

class JoueurItem(BoxLayout):
    def __init__(self, nom, statut="", index=None, couleur_texte=(1, 1, 1, 1), **kwargs):
        super().__init__(**kwargs)

        fs = get_user_font_size()

        self.orientation = "horizontal"
        self.size_hint_y = None
        self.spacing = dp(8)
        self.padding = [dp(10), dp(5)]

        # ==================
        # Numéro
        # ==================
        self.index_label = Label(
            text=f"{index}." if index else "•",
            font_size=f"{fs}sp",
            bold=True,
            color=couleur_texte,
            size_hint=(None, None),
            width=dp(38),
            halign="right"
        )

        self.index_label.bind(
            size=lambda i, s: setattr(i, "text_size", s)
        )

        self.add_widget(self.index_label)

        # ==================
        # Nom
        # ==================
        self.name_label = Label(
            text=nom,
            markup=True,
            font_size=f"{fs}sp",
            color=couleur_texte,
            halign="left",
            valign="top",
            size_hint=(1, None)
        )

        self.name_label.bind(
            width=lambda i, w: setattr(i, "text_size", (w, None))
        )

        self.name_label.bind(
            texture_size=self._sync_layout
        )

        self.add_widget(self.name_label)

        # ==================
        # Statut
        # ==================
        if statut and statut.strip():

            status = Label(
                text=statut,
                color=(0.2, 1, 0.2, 1),
                font_size=f"{fs-2}sp",
                markup=True,
                bold=True,
                size_hint=(None, None),
                width=dp(90),
                halign="right",
                valign="top"
            )

            status.bind(
                size=lambda i, s: setattr(i, "text_size", s)
            )

            self.add_widget(status)

        Clock.schedule_once(lambda dt: self._sync_layout())

    def _sync_layout(self, *args):

        text_h = self.name_label.texture_size[1]
        font_h = self.name_label.font_size

        mono_ligne = text_h < font_h * 1.6

        if mono_ligne:
            row_h = dp(42)
        
            self.index_label.valign = "middle"
            vertical_offset = 0
        
        else:
            row_h = text_h + dp(8)
        
            self.index_label.valign = "top"
        
            # Décalage léger vers le bas
            vertical_offset = dp(5)

        self.height = row_h

        self.name_label.height = row_h

        self.index_label.height = row_h
        self.index_label.text_size = (
            self.index_label.width,
            row_h - vertical_offset
        )

class ChatView(BoxLayout):
    def __init__(self, categorie, screen_instance=None, **kwargs):
        super().__init__(orientation='vertical', spacing=dp(5), **kwargs)
        self.categorie, self.cached_messages, self.limit = categorie, [], 25
        self.last_hash = None
        
        # Récupération sécurisée des données via l'instance de l'écran passée en argument
        cat_data = {}
        if screen_instance:
            cat_data = getattr(screen_instance, '_cache_data', {}).get(self.categorie, {})
        
        app = App.get_running_app()
        self.is_admin_only = cat_data.get('chat_admin_only', False)
        self.user_role = app.get_role_for_cat(self.categorie)
        
        self.scroll = ScrollView(bar_width=0, do_scroll_x=False)
        self.msg_container = BoxLayout(orientation='vertical', size_hint_y=None)
        self.msg_container.bind(minimum_height=self.msg_container.setter("height"))
        
        fs = app.config.getint('User', 'font_size_factor', fallback=18)
        
        # 1. Préparation du label "Aucun message"
        self.empty_label = Label(
            text="Aucun message pour le moment.\nSoyez le premier à écrire !",
            halign="center",
            valign="middle",
            color=(0.7, 0.7, 0.7, 1),
            size_hint_y=None, 
            height=0,
            font_size=f"{fs + 4}sp"
        )
        self.empty_label.bind(size=lambda i, v: setattr(i, 'text_size', (v[0], None)))
        self.msg_container.add_widget(self.empty_label)
        
        self.scroll.add_widget(self.msg_container)
        self.add_widget(self.scroll)

        # 2. Zone de saisie conditionnelle
        if not self.is_admin_only or self.user_role == "ADMIN":
            self.input_box = BoxLayout(size_hint_y=None, height=dp(80), spacing=dp(10), padding=dp(5))
            self.input_field = TextInput(
                hint_text="Message...", 
                multiline=False, 
                font_size=f"{fs + 2}sp",
                padding=[dp(10), dp(10)]
            )
            send_btn = Button(
                text="Envoyer", 
                size_hint_x=0.3, 
                font_size=f"{fs}sp", 
                bold=True
            )
            send_btn.bind(on_release=self.send_message)
            self.input_box.add_widget(self.input_field)
            self.input_box.add_widget(send_btn)
            self.add_widget(self.input_box)
        else:
            # Message informatif pour les non-admins
            self.add_widget(Label(
                text="[color=888888]Chat en mode lecture seule (Staff uniquement)[/color]",
                markup=True,
                size_hint_y=None,
                height=dp(50)
            ))

        self.load_cache()
        self.fetch_messages()
        self.refresh_event = Clock.schedule_interval(self.fetch_messages, 5)

    def scroll_to_bottom(self, *args):
        # On attend que le layout soit calculé pour scroller tout en bas
        Clock.schedule_once(lambda dt: setattr(self.scroll, 'scroll_y', 0), 0.1)

    def render_messages(self, scroll_to_bottom_trigger=True):
        # 1. Nettoyage total du conteneur
        self.msg_container.clear_widgets()
        
        # 2. Gestion de l'état vide
        if not self.cached_messages:
            self.empty_label.height = dp(200)
            self.empty_label.opacity = 1
            self.msg_container.add_widget(self.empty_label)
        else:
            self.empty_label.height = 0
            self.empty_label.opacity = 0
            self.msg_container.add_widget(self.empty_label)

        app = App.get_running_app()
        mon_nom = app.config.get("User", "nom_parent", fallback="Inconnu")
        fs = app.config.getint('User', 'font_size_factor', fallback=15)
        
        # 3. Bouton "Charger plus"
        if len(self.cached_messages) > self.limit:
            btn = Button(text="Charger plus...", size_hint_y=None, height=dp(40))
            btn.bind(on_release=lambda x: self._load_more_and_preserve_scroll())
            self.msg_container.add_widget(btn)

        # 4. Rendu des messages
        last_author = None
        last_date = None
        
        for msg in self.cached_messages[-self.limit:]:
            try:
                msg_ts = msg.get('timestamp', '')
                dt = datetime.fromisoformat(msg_ts.replace('Z', '+00:00'))
                current_date = dt.strftime("%d/%m/%Y")
            except:
                current_date = None

            if current_date and current_date != last_date:
                sep = Label(
                    text=f"[b]{current_date}[/b]", 
                    markup=True, 
                    size_hint_y=None, 
                    height=dp(40), 
                    color=(0.7, 0.7, 0.7, 1)
                )
                self.msg_container.add_widget(sep)
                last_date = current_date

            auteur = msg.get("auteur")
            # Identification si l'expéditeur est admin
            est_admin = msg.get("role") == "ADMIN"
            
            self.msg_container.add_widget(
                MessageBubble(
                    msg, 
                    auteur == mon_nom, 
                    auteur != last_author, 
                    est_admin=est_admin, # Nouveau paramètre à gérer dans MessageBubble
                    font_size=fs
                )
            )
            last_author = auteur
            
        self.msg_container.do_layout()
        
        if scroll_to_bottom_trigger and self.cached_messages:
            self.scroll_to_bottom()

    def _load_more_and_preserve_scroll(self):
        # Sauvegarde de la position (proche du haut, on veut y rester)
        old_scroll = self.scroll.scroll_y
        self.limit += 25
        self.render_messages(scroll_to_bottom_trigger=False)
        Clock.schedule_once(lambda dt: setattr(self.scroll, 'scroll_y', old_scroll), 0.1)

    def fetch_messages(self, *args):
        try:
            r = requests.get(f"https://fcvv-api.onrender.com/chat/{self.categorie}", timeout=5)
            if r.status_code == 200:
                data = r.json()
                new_hash = hashlib.md5(str(data).encode()).hexdigest()
                if new_hash != self.last_hash:
                    self.last_hash = new_hash
                    self.cached_messages = data
                    self.save_cache()
                    self.render_messages(scroll_to_bottom_trigger=True)
        except Exception as e: print(f"Erreur fetch: {e}")

    def save_cache(self):
        with open(self.get_cache_path(), "w", encoding="utf-8") as f:
            json.dump(self.cached_messages[-100:], f)

    def load_cache(self):
        path = self.get_cache_path()
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                self.cached_messages = json.load(f)
                self.render_messages(scroll_to_bottom_trigger=True)

    def send_message(self, *args):
        # Sécurité supplémentaire côté client avant l'envoi
        if self.is_admin_only and self.user_role != "ADMIN":
            return
        text = self.input_field.text.strip()
        if text:
            app = App.get_running_app()
            # On récupère le rôle de l'utilisateur pour cette catégorie
            user_role = app.get_role_for_cat(self.categorie)
            
            # Envoi du message avec le rôle inclus
            requests.post(
                f"https://fcvv-api.onrender.com/chat/{self.categorie}", 
                json={
                    "auteur": self._get_user(), 
                    "contenu": text,
                    "role": user_role
                }
            )
            
            self.input_field.text = ""
            self.fetch_messages()
    def get_cache_path(self): return os.path.join(App.get_running_app().user_data_dir, f"chat_{self.categorie}.json")
    def _get_user(self): return App.get_running_app().config.get("User", "nom_parent", fallback="Inconnu")
    def on_parent(self, *args): 
        if not self.parent and hasattr(self, 'refresh_event') and self.refresh_event: self.refresh_event.cancel()
    def stop_refresh(self):
        """Arrête le rafraîchissement automatique des messages."""
        if hasattr(self, 'refresh_event') and self.refresh_event:
            self.refresh_event.cancel()
            self.refresh_event = None

class VestiaireScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.current_cat = None
        self.current_sub_tab = "INFOS"
        self._cache_data = {} 
        self.KIVY_BLUE = (30/255, 58/255, 138/255, 1)
        self.YELLOW = (247/255, 236/255, 63/255, 1)
        
        with self.canvas.before:
            Color(*self.KIVY_BLUE)
            self.rect_bg = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._update_rect, size=self._update_rect)
        
        self.main_layout = BoxLayout(orientation='vertical')
        self.add_widget(self.main_layout)
        
        # Barre de catégories
        self.cat_scroll = ScrollView(
            size_hint_y=None,
            height=dp(70),
            do_scroll_x=True,
            do_scroll_y=False,
            bar_width=0
        )
        
        self.cat_bar = BoxLayout(
            size_hint_x=None,
            height=dp(70),
            spacing=dp(8),
            padding=[dp(10), dp(10)]
        )
        
        self.cat_bar.bind(minimum_width=self.cat_bar.setter("width"))
        self.cat_scroll.add_widget(self.cat_bar)
        
        # --- MODIFICATION : ScrollView pour les sous-onglets ---
        self.sub_scroll = ScrollView(size_hint_y=None, height=dp(60), do_scroll_x=True, do_scroll_y=False, bar_width=0)
        self.sub_bar = BoxLayout(size_hint_x=None, height=dp(60), spacing=dp(2), padding=[dp(10), dp(5)])
        self.sub_bar.bind(minimum_width=self.sub_bar.setter('width'))
        self.sub_scroll.add_widget(self.sub_bar)
        
        self.scroll_content = ScrollView(bar_width=0)
        
        self.main_layout.add_widget(self.cat_scroll)
        self.main_layout.add_widget(self.sub_scroll)
        self.main_layout.add_widget(self.scroll_content)
        
    def update_ui(self):
        app = App.get_running_app()
        if not hasattr(app, 'authorized_vestiaires') or not app.authorized_vestiaires: return
        if not self.current_cat: self.current_cat = app.authorized_vestiaires[0]
        
        fs = app.config.getint('User', 'font_size_factor', fallback=18)
        
        # --- Rendu des catégories ---
        self.cat_bar.clear_widgets()
        for cat in app.authorized_vestiaires:
            is_active = (self.current_cat == cat)
            role = app.get_role_for_cat(cat)
            display = f"{cat} [size={int((fs+2)*0.7)}sp][color=888888](ADMIN)[/color][/size]" if role == "ADMIN" else cat
            
            btn = Button(text=display, markup=True, size_hint=(None, 1), font_size=f"{fs+2}sp",
                         background_normal='', background_color=(0, 0, 0, 0), bold=True,
                         color=(0, 0, 0, 1) if is_active else (1, 1, 1, 1))
            
            # Correction : largeur adaptative avec minimum pour "gros doigts"
            btn.bind(texture_size=lambda instance, val: setattr(instance, 'width', max(dp(100), val[0] + dp(30))))
            
            with btn.canvas.before:
                Color(0.97, 0.93, 0.25, 1) if is_active else Color(1, 1, 1, 0.15)
                btn.bg = RoundedRectangle(pos=btn.pos, size=btn.size, radius=[dp(8)])
            btn.bind(pos=lambda i, v: setattr(i.bg, 'pos', v), size=lambda i, v: setattr(i.bg, 'size', v))
            btn.bind(on_release=lambda x, c=cat: self.set_category(c))
            self.cat_bar.add_widget(btn)

        # --- Rendu des sous-onglets ---
        self.sub_bar.clear_widgets()
        tabs = ["INFOS", "SONDAGES", "CONVOCS", "CHAT", "SAISON", "EFFECTIF", "DOCS"]
        role_actuel = app.get_role_for_cat(self.current_cat)
        
        for sub in tabs:
            if sub == "EFFECTIF" and role_actuel != "ADMIN": continue
            is_active = (self.current_sub_tab == sub)
            
            btn = Button(text=sub, size_hint=(None, 1), font_size=f"{fs-3}sp",
                         background_normal='', background_color=(0, 0, 0, 0), bold=is_active,
                         color=(0, 0, 0, 1) if is_active else (1, 1, 1, 1))
            
            btn.bind(texture_size=lambda instance, val: setattr(instance, 'width', max(dp(90), val[0] + dp(20))))
            
            with btn.canvas.before:
                Color(0.97, 0.93, 0.25, 1) if is_active else Color(1, 1, 1, 0.1)
                btn.bg = Rectangle(pos=btn.pos, size=btn.size)
            btn.bind(pos=lambda i, v: setattr(i.bg, 'pos', v), size=lambda i, v: setattr(i.bg, 'size', v))
            btn.bind(on_release=lambda x, s=sub: self.set_sub_tab(s))
            self.sub_bar.add_widget(btn)

        if self.current_sub_tab == "EFFECTIF" and role_actuel != "ADMIN": self.current_sub_tab = "INFOS"

        # --- Logique de chargement ---
        data = self._cache_data.get(self.current_cat)
        if data:
            self.fetch_convocations_from_firebase(data) if self.current_sub_tab == "CONVOCS" else self.render_content(data)
        else:
            self.scroll_content.clear_widgets()
            self.scroll_content.add_widget(Label(text="Chargement...", color=(1, 1, 1, 0.5), font_size=f"{fs+4}sp"))
            vest_cfg = app.app_config.get("fcvv", {}).get("appli", {}).get("vestiaire", [])
            cat_info = next((item for item in vest_cfg if item.get("categorie") == self.current_cat), None)
            if cat_info:
                path = os.path.join(app.user_data_dir, f"data_{self.current_cat}.yaml")
                threading.Thread(target=self.verify_and_load, args=(cat_info, path), daemon=True).start()
    
    def fetch_convocations_from_firebase(self, data):
        # Sauvegarde du contexte actuel pour éviter les retours réseau obsolètes
        requested_cat = self.current_cat
        requested_tab = self.current_sub_tab
    
        # Nettoyage IMMÉDIAT → évite le flash du contenu précédent
        self.scroll_content.clear_widgets()
        self.scroll_content.opacity = 1
        self.scroll_content.do_scroll_y = True
    
        fs = get_user_font_size()
    
        loading = Label(
            text="Chargement des convocations...",
            color=(1, 1, 1, 0.6),
            font_size=f"{fs + 2}sp"
        )
    
        self.scroll_content.add_widget(loading)
    
        url = f"https://fcvv-api.onrender.com/convocations/{requested_cat}"
    
        def apply_result(convocations):
            # Si l'utilisateur a changé d'écran entre temps → on ignore
            if (
                requested_cat != self.current_cat or
                requested_tab != self.current_sub_tab or
                self.current_sub_tab != "CONVOCS"
            ):
                return
    
            data["calendrier"] = convocations
            self.render_content(data)
    
        def do_request():
            try:
                r = requests.get(url, timeout=5)
    
                if r.status_code == 200:
                    convocations = r.json()
                else:
                    # 404 ou autre → aucune convocation
                    convocations = {}
    
                Clock.schedule_once(
                    lambda dt: apply_result(convocations),
                    0
                )
    
            except Exception as e:
                print(f"Erreur connexion Firebase : {e}")
    
                Clock.schedule_once(
                    lambda dt: apply_result({}),
                    0
                )
    
        threading.Thread(
            target=do_request,
            daemon=True
        ).start()

    def _get_font_size(self):
        app = App.get_running_app()
        val = app.config.get('User', 'font_size', fallback='14')
        return f"{val}sp" if 'sp' not in val else val

    def _update_rect(self, instance, value):
        self.rect_bg.pos = instance.pos
        self.rect_bg.size = instance.size

    def on_enter(self, *args):
        app = App.get_running_app()
        
        # Si aucune catégorie n'est définie, on tente d'en récupérer une
        if not self.current_cat:
            if app.authorized_vestiaires:
                self.current_cat = app.authorized_vestiaires[0]
            else:
                # Si vraiment rien, on redirige sans supprimer d'options
                app.root.switch_screen('login_vestiaire')
                return

        # Vérification de la validité du hash
        if not app.is_access_still_valid(self.current_cat):
            self.logout_user()
        else:
            self.update_ui()
    
    def logout_user(self):
        """Révoque l'accès local et retourne à l'écran de login en toute sécurité."""
        app = App.get_running_app()
        
        # Sécurisation : On convertit en chaîne si nécessaire pour éviter None
        cat_id = str(self.current_cat) if self.current_cat else None
        
        if not cat_id:
            print("[LOGOUT] Aucune categorie identifiee, forcage vers login.")
        else:
            # 1. Supprimer la catégorie de la liste en mémoire
            if self.current_cat in app.authorized_vestiaires:
                app.authorized_vestiaires.remove(self.current_cat)
            
            # 2. Nettoyer les données persistantes dans .ini
            if app.config.has_section('Roles'):
                # Suppression sécurisée
                if app.config.has_option('Roles', f'{cat_id}_hash'):
                    app.config.remove_option('Roles', f'{cat_id}_hash')
                if app.config.has_option('Roles', cat_id):
                    app.config.remove_option('Roles', cat_id)
                
            app.config.set('User', 'authorized_list', ','.join(app.authorized_vestiaires))
            app.config.write()
        
        # 3. Redirection : utilisez app.root.current ou la méthode de votre RootLayout
        # Vérifiez que le nom de l'écran est bien 'login' dans votre fichier .kv ou setup
        try:
            app.root.switch_screen('login')
        except Exception as e:
            print(f"[ERROR] Impossible de basculer vers 'login': {e}")

    def set_category(self, cat):
        if self.current_cat == cat:
            return

        # 1. VIDER IMMÉDIATEMENT L'INTERFACE pour éviter de voir l'ancien contenu
        self.scroll_content.clear_widgets()
        # 2. RÉINITIALISATION
        self.current_cat = cat
        self.current_sub_tab = "INFOS" # On revient sur l'onglet par défaut
        # 3. Animation de transition
        anim = Animation(opacity=0, duration=0.1)
        
        def on_complete(*args):
            # On met à jour l'UI (qui va recharger les données pour cette nouvelle catégorie)
            self.update_ui()
            # Réapparition
            self.scroll_content.opacity = 0
            anim_in = Animation(opacity=1, duration=0.15)
            anim_in.start(self.scroll_content)
            
        anim.bind(on_complete=on_complete)
        anim.start(self.scroll_content)

    def set_sub_tab(self, sub):
        if self.current_sub_tab == sub:
            return
            
        self.current_sub_tab = sub
        # Transition visuelle : fondu rapide pour la "rupture"
        anim = Animation(opacity=0, duration=0.1)
        
        def on_complete(*args):
            self.update_ui()
            # Fait réapparaître le contenu une fois chargé
            Animation(opacity=1, duration=0.1).start(self.scroll_content)
            
        anim.bind(on_complete=on_complete)
        anim.start(self.scroll_content)

    def verify_and_load(self, cat_info, path):
        url = f"https://docs.google.com/uc?id={cat_info.get('file_id')}&export=download"
        try:
            r = requests.get(url, timeout=10, verify=False)
            if r.status_code == 200:
                new_content = r.content
                if os.path.exists(path):
                    with open(path, 'rb') as f:
                        if hashlib.md5(f.read()).hexdigest() != hashlib.md5(new_content).hexdigest():
                            with open(path, "wb") as f: f.write(new_content)
                else:
                    with open(path, "wb") as f: f.write(new_content)
        except Exception as e:
            logging.error(f"Erreur téléchargement: {e}")
        data = cat_info.copy()
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f: data.update(yaml.safe_load(f) or {})
            except Exception as e:
                logging.error(f"Erreur YAML: {e}")
        self._cache_data[self.current_cat] = data
        Clock.schedule_once(lambda dt: self.render_content(data))

    def render_content(self, data):
        # 1. Nettoyage immédiat et total du conteneur parent
        self.scroll_content.clear_widgets()
        self.scroll_content.scroll_y = 1
        fs = get_user_font_size()
        
        # Helper pour les titres de section
        def SectionTitle(text):
            return Label(text=f"[b]{text}[/b]", markup=True, color=self.YELLOW, 
                         size_hint_y=None, height=dp(45), font_size=f"{fs + 4}sp")

        # Gestion spécifique pour le CHAT (pas de layout vertical ici)
        if self.current_sub_tab == "CHAT":
            self.scroll_content.do_scroll_y = False
            self.scroll_content.add_widget(ChatView(categorie=self.current_cat, screen_instance=self, size_hint=(1, 1)))
            return
        
        # 2. Initialisation du layout avec opacity=0 pour cacher toute construction intermédiaire
        self.scroll_content.do_scroll_y = True
        layout = BoxLayout(orientation='vertical', padding=dp(20), spacing=dp(20), size_hint_y=None, opacity=0)
        layout.bind(minimum_height=layout.setter('height'))
        
        calendrier = data.get('calendrier', {}) if isinstance(data.get('calendrier'), dict) else {}
        
        # 3. Remplissage du layout local
        if self.current_sub_tab == "INFOS":
            vest_data = data.get('espace_vestiaire', {})
            titre = Label(
                text=f"[b]{vest_data.get('titre_bienvenue', 'Espace ' + str(self.current_cat))}[/b]", 
                markup=True, 
                font_size=f"{fs + 6}sp", 
                size_hint_y=None,
                halign='center',  # Centrage horizontal
                valign='middle'   # Centrage vertical
            )
            
            # Le bind crucial pour que le texte sache qu'il doit s'étaler sur toute la largeur disponible
            titre.bind(
                width=lambda i, w: setattr(i, 'text_size', (w, None)), 
                texture_size=lambda i, s: setattr(i, 'height', s[1])
            )
            layout.add_widget(titre)
            layout.add_widget(InfoCard(text=data.get('info', 'Pas de message du coach.')))
            layout.add_widget(SectionTitle("FONCTIONNALITÉS"))
            desc = Label(text=vest_data.get('description', ""), markup=True, font_size=f"{fs}sp", size_hint_y=None)
            desc.bind(width=lambda i, w: setattr(i, 'text_size', (w, None)), texture_size=lambda i, s: setattr(i, 'height', s[1]))
            layout.add_widget(desc)

        elif self.current_sub_tab == "SONDAGES":

            # Contexte actuel pour éviter les retours obsolètes
            requested_cat = self.current_cat
            requested_tab = self.current_sub_tab
        
            loading_box = BoxLayout(
                orientation="vertical",
                size_hint_y=None,
                spacing=dp(20),
                padding=[0, dp(80)]
            )
        
            loading_box.bind(
                minimum_height=loading_box.setter("height")
            )
        
            loading_box.add_widget(
                Label(
                    text="Chargement des sondages...",
                    font_size=f"{fs+2}sp",
                    color=(1, 1, 1, 0.7),
                    size_hint_y=None,
                    height=dp(60)
                )
            )
        
            layout.add_widget(loading_box)
        
            def delayed_fetch(dt):
        
                # sécurité : l'utilisateur a changé d'écran
                if (
                    requested_cat != self.current_cat
                    or requested_tab != self.current_sub_tab
                    or self.current_sub_tab != "SONDAGES"
                ):
                    return
        
                self.fetch_and_show_sondages(layout)
        
            # délai légèrement plus long → laisse render finir
            Clock.schedule_once(delayed_fetch, 0.3)
            
        elif self.current_sub_tab == "CONVOCS":
            role = App.get_running_app().get_role_for_cat(self.current_cat)
            if role == "ADMIN":
                btn_admin = Button(
                    text="[b]Gérer les convocations[/b]", 
                    markup=True, 
                    font_size=f"{fs + 4}sp",
                    size_hint_y=None, 
                    height=dp(50), 
                    background_color=(0.8, 0.5, 0, 1)
                )
                btn_admin.bind(on_release=lambda x: self.ouvrir_gestion_convocations_admin(calendrier))
                layout.add_widget(btn_admin)

            if not calendrier:
                layout.add_widget(Label(
                    text="Aucune convocation.", 
                    italic=True, 
                    size_hint_y=None, 
                    height=dp(50)
                ))
            else:
                for nom_eq, match_info in calendrier.items():
                    layout.add_widget(SectionTitle(nom_eq.upper()))
                    layout.add_widget(ConvocationCard(data=match_info))
                    joueurs = match_info.get('joueurs_convoques', [])
                    
                    if joueurs:
                        layout.add_widget(Label(
                            text="Joueurs convoqués :", 
                            font_size=f"{fs-2}sp", 
                            size_hint_y=None, 
                            height=dp(30)
                        ))
                        # ... dans la section CONVOCS, là où vous faites la boucle :
                        for idx, j in enumerate(joueurs, 1):
                            prenom = j.get("prenom", "")
                            nom = j.get("nom", "")
                            categorie = j.get("categorie", "")
                            est_manuel = j.get("est_manuel", False)
                        
                            if est_manuel:
                                nom_affiche = f"[{categorie}] {nom.upper()} {prenom}".strip()
                                couleur = (1, 0.85, 0.25, 1)   # Jaune
                            else:
                                nom_affiche = f"{nom.upper()} {prenom}".strip()
                                couleur = (1, 1, 1, 1)         # Blanc
                        
                            layout.add_widget(
                                JoueurItem(
                                    nom=nom_affiche,
                                    index=idx,
                                    couleur_texte=couleur
                                )
                            )
        
        elif self.current_sub_tab == "SAISON":
            # On extrait spécifiquement la nouvelle clé
            calendrier_saison = data.get('calendrier_saison', {})
            print(f"DEBUG: Passage dans SAISON. Donnees recues: {calendrier_saison}")
            
            layout.add_widget(SectionTitle("CALENDRIER & CLASSEMENT"))
            
            # Vérification de sécurité sur la bonne clé
            if not calendrier_saison:
                print("DEBUG: 'calendrier_saison' est vide.")
                layout.add_widget(Label(text="Aucune donnée saison trouvée.", italic=True))
            else:
                for nom_eq, infos_eq in calendrier_saison.items():
                    print(f"DEBUG: Traitement de l'equipe : {nom_eq}")
                    
                    # Ajout du titre de l'équipe
                    layout.add_widget(Label(text=f"[b]{nom_eq.upper()}[/b]", markup=True, 
                                            size_hint_y=None, height=dp(40), font_size=f"{fs-2}sp"))
                    
                    # Accès sécurisé au dictionnaire imbriqué
                    liens = infos_eq.get('liens_fff', {})
                    print(f"DEBUG: Liens trouves pour {nom_eq}: {liens}")
                    
                    types_liens = [("Calendrier", 'calendrier'), ("Classement", 'classement')]
                    
                    for label, url_key in types_liens:
                        url = liens.get(url_key)
                        if url and isinstance(url, str) and url.startswith("http"):
                            print(f"DEBUG: Creation bouton {label} avec URL: {url}")
                            btn = Button(text=label, size_hint_y=None, height=dp(50),font_size=f"{fs*0.8}sp")
                            btn.bind(on_release=lambda x, u=url: webbrowser.open(u))
                            layout.add_widget(btn)
                        else:
                            print(f"DEBUG: Aucun lien valide trouve pour {label} (cle: {url_key})")
                        
        elif self.current_sub_tab == "EFFECTIF":
            layout.add_widget(SectionTitle("EFFECTIF COMPLET"))
            
            # Extraction de la liste
            joueurs = data.get('tous_les_joueurs', [])
            
            if not joueurs:
                layout.add_widget(Label(
                    text="Aucun joueur enregistré pour cette catégorie.", 
                    italic=True, 
                    size_hint_y=None, 
                    height=dp(100), 
                    font_size=f"{fs-2}sp",
                    color=(0.7, 0.7, 0.7, 1)
                ))
            else:
                for idx, j in enumerate(joueurs, 1):
                    # Récupération des données avec fallback
                    nom = j.get('nom', '').upper()
                    prenom = j.get('prenom', '')
                    licence = j.get('licence', 'N/C')
                    date_nais = j.get('date_naissance', 'N/C')
                    
                    # Construction du texte avec Markup Kivy
                    infos = (
                        f"{nom} {prenom}\n"
                        f"[size={int(fs*0.8)}sp][color=888888]"
                        f"Né(e) le : {date_nais}\n"
                        f"Licence : {licence}"
                        f"[/color][/size]"
                    )
                    layout.add_widget(JoueurItem(nom=infos, statut="", index=idx))
                    
        elif self.current_sub_tab == "DOCS":
            layout.add_widget(SectionTitle("DOCUMENTS UTILES"))
            
            # Filtrage des documents valides
            docs = [d for d in data.get('documents', []) if d.get('nom')]
            
            if not docs:
                layout.add_widget(Label(
                    text="Aucun document disponible pour le moment.", 
                    italic=True, 
                    size_hint_y=None, 
                    height=dp(100), 
                    font_size=f"{fs-2}sp",
                    color=(0.7, 0.7, 0.7, 1)
                ))
            else:
                for doc in docs:
                    btn = Button(text=doc.get('nom'), size_hint_y=None, height=dp(60),font_size=f"{fs*0.8}sp")
                    url = doc.get('url')
                    if url: 
                        btn.bind(on_release=lambda x, u=url: webbrowser.open(u))
                    else:
                        btn.disabled = True
                        btn.text += " (Lien invalide)"
                    layout.add_widget(btn)
        
        # 4. Ajout final unique au conteneur
        self.scroll_content.add_widget(layout)
        
        # 5. Rendre le layout visible et forcer le rafraîchissement
        layout.opacity = 1
        Clock.schedule_once(lambda dt: self.scroll_content.canvas.ask_update(), 0.1)
 
    def fetch_and_show_sondages(self, layout):

        requested_cat = self.current_cat
        requested_tab = self.current_sub_tab
    
        import threading
    
        def run_request():
    
            try:
                response = requests.get(
                    f"https://fcvv-api.onrender.com/sondages/{requested_cat}",
                    timeout=8
                )
    
                def apply(dt):
    
                    # ignorer si l'utilisateur a changé d'écran
                    if (
                        requested_cat != self.current_cat
                        or requested_tab != self.current_sub_tab
                        or self.current_sub_tab != "SONDAGES"
                    ):
                        return
    
                    self.display_sondages(layout, response)
    
                Clock.schedule_once(apply)
    
            except requests.Timeout:
    
                def show_timeout(dt):
    
                    if (
                        requested_cat != self.current_cat
                        or requested_tab != self.current_sub_tab
                    ):
                        return
    
                    self.show_error(
                        layout,
                        "Le chargement prend plus de temps que prévu."
                    )
    
                Clock.schedule_once(show_timeout)
    
            except Exception as e:
    
                print(f"Erreur sondages : {e}")
    
                def show_error_safe(dt):
    
                    if (
                        requested_cat != self.current_cat
                        or requested_tab != self.current_sub_tab
                    ):
                        return
    
                    self.show_error(
                        layout,
                        "Impossible de charger les sondages."
                    )
    
                Clock.schedule_once(show_error_safe)
    
        threading.Thread(
            target=run_request,
            daemon=True
        ).start()

    def display_sondages(self, layout, response):
        # Nettoyage complet avant d'ajouter les nouveaux widgets
        layout.clear_widgets()
        
        if response.status_code != 200:
            self.show_error(layout, f"Erreur API: {response.status_code}")
            return

        sondages = response.json()
        app = App.get_running_app()
        mon_nom = app.config.get('User', 'nom_parent', fallback='')
        fs = get_user_font_size()
        
        # 2. Bouton ADMIN
        if app.get_role_for_cat(self.current_cat) == "ADMIN":
            btn_admin = Button(text="[b]Gérer les sondages[/b]", markup=True, font_size=f"{fs + 4}sp",size_hint_y=None, height=dp(50), 
                               background_color=(0.8, 0.5, 0, 1), background_normal='')
            btn_admin.bind(on_release=lambda x: self.ouvrir_gestion_admin())
            layout.add_widget(btn_admin)
            layout.add_widget(Widget(size_hint_y=None, height=dp(10)))
        
        if not sondages:
            layout.add_widget(Label(text="Aucun sondage en cours.", font_size=f"{fs}sp"))
        else:
            for sid, info in sondages.items():
                # En-tête
                header_text = (f"[b]{info.get('titre', 'Sans titre')}[/b]\n"
                               f"{info.get('date', 'Date non définie')}\n"
                               f"{info.get('heure', 'Heure non définie')}\n"
                               f"{info.get('lieu', 'Lieu non défini')}")
                header_label = Label(text=header_text, markup=True, halign='center',
                                     font_size=f"{fs}sp", height=dp(120), size_hint_y=None)
                header_label.bind(width=lambda i, w: setattr(i, 'text_size', (w, None)))
                layout.add_widget(header_label)
                
                votes = info.get('votes', {})
                sondage_type = info.get('type', 'dispo')
                mon_choix = votes.get(mon_nom, None)
                
                # Section VOTRE CHOIX
                layout.add_widget(Label(text="--- Votre choix ---", size_hint_y=None, height=dp(30), color=(0.7, 0.7, 0.7, 1)))
                btn_box = BoxLayout(size_hint_y=None, height=dp(60), spacing=dp(10), padding=[dp(5), dp(5)])
                
                choix_liste = ["Présent", "Absent"] if sondage_type == 'dispo' else ["Au Stade", "RDV Direct", "Besoin Trajet"]
                for c in choix_liste:
                    btn = Button(text=c, bold=True, background_normal='', font_size=f"{fs-2}sp")
                    btn.background_color = (0, 0.6, 0.6, 1) if mon_choix == c else (0.2, 0.2, 0.2, 1)
                    btn.bind(on_release=lambda x, s=sid, choice=c: self.envoyer_vote(s, choice))
                    btn_box.add_widget(btn)
                layout.add_widget(btn_box)
                
                # Section ÉTAT
                layout.add_widget(Label(text="--- État des réponses ---", size_hint_y=None, height=dp(30), color=(0.7, 0.7, 0.7, 1)))
                view_box = BoxLayout(size_hint_y=None, height=dp(50), spacing=dp(10), padding=[dp(5), dp(5)])
                
                if sondage_type == 'dispo':
                    presents = [n for n, c in votes.items() if c == "Présent"]
                    absents = [n for n, c in votes.items() if c == "Absent"]
                    view_box.add_widget(Spinner(text=f"Présents ({len(presents)})", values=presents or ["Aucun"], background_color=(0, 0.5, 0, 1), background_normal=''))
                    view_box.add_widget(Spinner(text=f"Absents ({len(absents)})", values=absents or ["Aucun"], background_color=(0.5, 0, 0, 1), background_normal=''))
                elif sondage_type == 'trajet':
                    for opt in ["Au Stade", "RDV Direct", "Besoin Trajet"]:
                        liste = [n for n, c in votes.items() if c == opt]
                        view_box.add_widget(Spinner(text=f"{opt} ({len(liste)})", values=liste or ["Aucun"], background_color=(0, 0.3, 0.6, 1), background_normal='', font_size="10sp"))
                
                layout.add_widget(view_box)
                layout.add_widget(Widget(size_hint_y=None, height=dp(40)))

        # Une fois le layout construit, on met à jour la taille et on rend visible
        layout.height = layout.minimum_height
        layout.opacity = 1

    def show_error(self, layout, message):
        layout.clear_widgets()
        layout.add_widget(Label(text=message))
        layout.opacity = 1

    def envoyer_vote(self, id_match, choix):
        app = App.get_running_app()
        nom_parent = app.config.get('User', 'nom_parent', fallback='')
        
        if not nom_parent or nom_parent.strip() == "":
            print("Erreur : Aucun nom de parent configure.")
            return

        url = f"https://fcvv-api.onrender.com/voter/{self.current_cat}"
        payload = {
            "id_sondage": id_match,
            "nom_parent": nom_parent, 
            "choix": choix
        }
        
        try:
            response = requests.post(url, json=payload, timeout=5)
            if response.status_code == 200:
                self.update_ui() 
            else:
                print(f"Erreur serveur : {response.status_code}")
        except Exception as e:
            print(f"Erreur lors du vote : {e}")
    
    def ouvrir_formulaire_sondage(self, sid=None, sondage_data=None):
        form = BoxLayout(orientation='vertical', spacing=dp(10), padding=dp(10))
        
        # Champs de saisie avec hauteur fixe
        field_height = dp(45)
        t = TextInput(text=sondage_data.get('titre', '') if sondage_data else "", 
                      hint_text="Titre", multiline=False, size_hint_y=None, height=field_height)
        d = TextInput(text=sondage_data.get('date', '') if sondage_data else "", 
                      hint_text="Date (ex: 15/07)", multiline=False, size_hint_y=None, height=field_height)
        h = TextInput(text=sondage_data.get('heure', '') if sondage_data else "", 
                      hint_text="Heure (ex: 14h00)", multiline=False, size_hint_y=None, height=field_height)
        l = TextInput(text=sondage_data.get('lieu', '') if sondage_data else "", 
                      hint_text="Lieu", multiline=False, size_hint_y=None, height=field_height)
        
        # Spinner avec hauteur fixe
        type_spinner = Spinner(text=sondage_data.get('type', 'dispo') if sondage_data else "dispo", 
                               values=["dispo", "trajet"], size_hint_y=None, height=field_height)
        
        # Ajout des champs au formulaire
        for widget in [t, d, h, l, type_spinner]:
            form.add_widget(widget)

        # Boutons Enregistrer et Fermer (Conteneur fixe en bas)
        btn_box = BoxLayout(size_hint_y=None, height=dp(50), spacing=dp(10))
        btn_save = Button(text="Enregistrer", background_color=(0, 0.7, 0, 1))
        btn_close = Button(text="Fermer", background_color=(0.5, 0.5, 0.5, 1))
        
        def on_save(instance):
            data = {
                "titre": t.text, "date": d.text, "heure": h.text, 
                "lieu": l.text, "type": type_spinner.text
            }
            if sid: 
                self.modifier_sondage(sid, data)
            else: 
                self.envoyer_nouveau_sondage(data)
            
            popup_form.dismiss()
            
            if hasattr(self, 'admin_popup'):
                self.admin_popup.dismiss()
                self.ouvrir_gestion_admin()
            
            self.update_ui() 

        btn_save.bind(on_release=on_save)
        btn_close.bind(on_release=lambda x: popup_form.dismiss())
        
        btn_box.add_widget(btn_save)
        btn_box.add_widget(btn_close)
        form.add_widget(btn_box)
            
        popup_form = Popup(title="Édition Sondage", content=form, size_hint=(0.8, 0.6))
        popup_form.open()
    
    def ouvrir_gestion_convocations_admin(self, calendrier):
        content = BoxLayout(orientation='vertical', padding=dp(10), spacing=dp(10))
        
        # Bouton Fermer (en haut pour une sortie rapide)
        btn_close = Button(text="X Fermer", size_hint_y=None, height=dp(40), 
                           background_color=(0.5, 0.5, 0.5, 1))
        btn_close.bind(on_release=lambda x: self.convoc_admin_popup.dismiss())
        content.add_widget(btn_close)

        # Bouton Ajouter (nouveau match)
        btn_add = Button(text="+ Ajouter une équipe/match", size_hint_y=None, height=dp(50), 
                         background_color=(0, 0.7, 0, 1))
        btn_add.bind(on_release=lambda x: self.ouvrir_gestion_convocations("Nouvelle Équipe", {}))
        content.add_widget(btn_add)

        scroll = ScrollView()
        grid = GridLayout(cols=1, size_hint_y=None, spacing=dp(10))
        grid.bind(minimum_height=grid.setter('height'))
        
        for nom_match, match_info in calendrier.items():
            box = BoxLayout(size_hint_y=None, height=dp(50), spacing=dp(5))
            box.add_widget(Label(text=nom_match))
            
            # Bouton Modifier
            btn_edit = Button(text="Modifier", size_hint_x=0.2)
            btn_edit.bind(on_release=lambda x, s=nom_match, i=match_info: self.ouvrir_gestion_convocations(s, i))
            
            # Bouton Supprimer
            btn_del = Button(text="X", size_hint_x=0.1, background_color=(0.8, 0, 0, 1))
            btn_del.bind(on_release=lambda x, s=nom_match: self.supprimer_convocation(s))
            
            box.add_widget(btn_edit)
            box.add_widget(btn_del)
            grid.add_widget(box)

        scroll.add_widget(grid)
        content.add_widget(scroll)
        
        # Popup avec taille définie pour rester lisible et fermable par clic extérieur
        self.convoc_admin_popup = Popup(title="Gestion des Équipes", content=content, size_hint=(0.9, 0.9))
        self.convoc_admin_popup.open()
    
    def ouvrir_gestion_admin(self):
        # 1. On récupère les données à jour avant d'ouvrir la fenêtre
        try:
            r = requests.get(f"https://fcvv-api.onrender.com/sondages/{self.current_cat}", timeout=5)
            sondages = r.json() if r.status_code == 200 else {}
        except:
            sondages = {}

        content = BoxLayout(orientation='vertical', padding=dp(10), spacing=dp(10))
        
        # 2. Bouton Fermer ajouté en haut
        btn_close = Button(text="X Fermer", size_hint_y=None, height=dp(40), 
                           background_color=(0.5, 0.5, 0.5, 1))
        btn_close.bind(on_release=lambda x: self.admin_popup.dismiss())
        content.add_widget(btn_close)

        scroll = ScrollView()
        grid = GridLayout(cols=1, size_hint_y=None, spacing=dp(10))
        grid.bind(minimum_height=grid.setter('height'))
        
        btn_ajout = Button(text="+ Nouveau Sondage", size_hint_y=None, height=dp(50), 
                           background_color=(0, 0.7, 0, 1))
        btn_ajout.bind(on_release=lambda x: self.ouvrir_formulaire_sondage())
        grid.add_widget(btn_ajout)

        for sid, info in sondages.items():
            box = BoxLayout(size_hint_y=None, height=dp(50), spacing=dp(5))
            # Ajout d'une limite de taille pour le label pour éviter les débordements
            lbl = Label(text=info.get('titre', 'Sans titre'))
            lbl.bind(size=lambda i, s: setattr(i, 'text_size', (s[0], None)))
            box.add_widget(lbl)
            
            btn_mod = Button(text="+", size_hint_x=0.2)
            btn_mod.bind(on_release=lambda x, s=sid, i=info: self.ouvrir_formulaire_sondage(s, i))
            
            btn_del = Button(text="X", size_hint_x=0.2, background_color=(0.8, 0, 0, 1))
            btn_del.bind(on_release=lambda x, s=sid: self.supprimer_sondage(s))
            
            box.add_widget(btn_mod)
            box.add_widget(btn_del)
            grid.add_widget(box)

        scroll.add_widget(grid)
        content.add_widget(scroll)
        
        self.admin_popup = Popup(title="Gérer les sondages", content=content, size_hint=(0.9, 0.9))
        self.admin_popup.open()
    
    def get_user_header(self):
        """Récupère le header d'authentification et garantit qu'il n'est pas vide."""
        app = App.get_running_app()
        nom = app.config.get('User', 'nom_parent', fallback='')
        # Si le nom est vide, on retourne un header invalide volontairement
        # pour éviter d'envoyer une requête sans identité
        return {'nom_parent': nom.strip()} if nom.strip() else {'nom_parent': 'anonymous'}

    def envoyer_nouveau_sondage(self, data):
        try:
            url = f"https://fcvv-api.onrender.com/sondages/create/{self.current_cat}"
            headers = self.get_user_header()
            r = requests.post(url, json=data, headers=headers, timeout=5)
            
            if r.status_code == 200:
                self.update_ui()
            else:
                print(f"Erreur creation ({r.status_code}): {r.text}")
        except Exception as e: 
            print(f"Erreur connexion creation: {e}")

    def modifier_sondage(self, sid, data):
        try:
            url = f"https://fcvv-api.onrender.com/sondages/update/{self.current_cat}/{sid}"
            headers = self.get_user_header()
            r = requests.put(url, json=data, headers=headers, timeout=5)
            
            if r.status_code == 200:
                # Ajout important : Fermer la popup si elle existe
                if hasattr(self, 'admin_popup'): 
                    self.admin_popup.dismiss()
                self.update_ui()
            else:
                print(f"Erreur modification ({r.status_code}): {r.text}")
        except Exception as e: 
            print(f"Erreur connexion modification: {e}")
    
    def supprimer_sondage(self, sid):
        try:
            url = f"https://fcvv-api.onrender.com/sondages/delete/{self.current_cat}/{sid}"
            headers = self.get_user_header()
            r = requests.delete(url, headers=headers, timeout=5)
            
            if r.status_code == 200:
                if hasattr(self, 'admin_popup'): 
                    self.admin_popup.dismiss()
                self.update_ui()
            else:
                print(f"Erreur suppression ({r.status_code}): {r.text}")
        except Exception as e: 
            print(f"Erreur connexion suppression: {e}")
    
    def ouvrir_gestion_convocations(self, match_id, match_info):

        content = BoxLayout(orientation='vertical', padding=dp(15), spacing=dp(15))
        # Titre interne
        content.add_widget(Label(text="Informations de la convocation", size_hint_y=None, height=dp(30), bold=True))
        # 1. Champ Nom équipe
        nom_equipe_input = TextInput(
            text=match_id if match_id != "Nouvelle Équipe" else "",
            hint_text="Nom de l'équipe (ex: U11 - Match A)",
            multiline=False, size_hint_y=None, height=dp(40)
        )
        content.add_widget(nom_equipe_input)
        # 2. Formulaire compact (Grid)
        fields_labels = [ "Adversaire", "Date", "Heure RDV", "Heure Match", "Lieu", "Entraineurs" ]
        inputs = {}
        form_grid = GridLayout(cols=2, size_hint_y=None, height=dp(210), spacing=dp(5))

        for label in fields_labels:
            form_grid.add_widget(Label(text=label, size_hint_x=0.3, halign='left'))
            # Correspondance entre les noms d'affichage et les clés du dictionnaire
            key = label.lower()
            key = key.replace("heure rdv", "heure_rdv")
            key = key.replace("heure match", "heure_match")
            key = key.replace(" ", "_")
            # Exemples affichés si le champ est vide
            exemples = {
                "adversaire": "ex : FCSM",
                "date": "ex : 15/09/2026",
                "heure_rdv": "ex : 13h30 à Valdahon ou 14h00 directement",
                "heure_match": "ex : 15h00",
                "lieu": "ex : Stade municipal",
                "entraineurs": "ex : Dupont / Martin"
            }
            ti = TextInput(
                text=match_info.get(key, ""),
                hint_text=exemples.get(key, ""),
                multiline=False,
                size_hint_y=None,
                height=dp(40)
            )
            inputs[label] = ti
            form_grid.add_widget(ti)
        content.add_widget(form_grid)
        # 3. Section Joueurs
        content.add_widget(Label(text="Joueurs :", size_hint_y=None, height=dp(30), bold=True))
        # --- Bloc Ajout Manuel ---
        add_manual_box = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(5))
        cat_input = TextInput(hint_text="Cat", multiline=False, size_hint_x=0.2)
        nom_input = TextInput(hint_text="Prénom Nom", multiline=False)
        # Liste pour stocker les checkboxes (incluant les ajoutés manuellement)
        checkboxes = []

        def ajouter_joueur_manuel(instance):
            nom_complet_saisi = nom_input.text.strip()
            cat = cat_input.text.strip().upper()

            if nom_complet_saisi:
                parts = nom_complet_saisi.split(' ', 1)
                prenom = parts[0]
                nom = parts[1] if len(parts) > 1 else ""
                # Format uniforme : Prénom NOM (Catégorie)
                # On met le NOM en majuscules pour le distinguer
                label_text = f"{prenom} {nom.upper()} ({cat})" if cat else f"{prenom} {nom.upper()}"
                box = BoxLayout(size_hint_y=None, height=dp(40))
                cb = CheckBox(size_hint_x=0.2, active=True)
                cb.nom_joueur = nom
                cb.prenom_joueur = prenom
                cb.categorie = cat
                cb.est_manuel = True
                box.add_widget(cb)
                box.add_widget(Label(text=label_text, halign='left'))
                grid_joueurs.add_widget(box)
                checkboxes.append(cb)
                nom_input.text = ""
                cat_input.text = ""

        btn_add = Button(text="+", size_hint_x=0.15)
        btn_add.bind(on_release=ajouter_joueur_manuel)
        add_manual_box.add_widget(cat_input)
        add_manual_box.add_widget(nom_input)
        add_manual_box.add_widget(btn_add)
        content.add_widget(add_manual_box)
        # --------------------------
        scroll = ScrollView()
        grid_joueurs = GridLayout(cols=1, size_hint_y=None, spacing=dp(2))
        grid_joueurs.bind(minimum_height=grid_joueurs.setter('height'))
        tous_joueurs = self._cache_data.get(self.current_cat, {}).get('tous_les_joueurs', [])
        joueurs_convoques_data = match_info.get('joueurs_convoques', [])
        convoques_noms_complets = [f"{j.get('prenom', '')} {j.get('nom', '')}".strip() for j in joueurs_convoques_data]
        
        for joueur in tous_joueurs:
            box = BoxLayout(size_hint_y=None, height=dp(40))
            prenom = joueur.get('prenom', '')
            nom = joueur.get('nom', '')
            nom_complet = f"{prenom} {nom}".strip()
            cb = CheckBox(size_hint_x=0.2, active=(nom_complet in convoques_noms_complets))
            cb.nom_joueur = nom
            cb.prenom_joueur = prenom
            cb.est_manuel = False # Catégorie par défaut pour les joueurs de la liste
            box.add_widget(cb)
            box.add_widget(Label(text=nom_complet, halign='left'))
            grid_joueurs.add_widget(box)
            checkboxes.append(cb)

        scroll.add_widget(grid_joueurs)
        content.add_widget(scroll)

        # 4. Boutons en bas
        btn_box = BoxLayout(size_hint_y=None, height=dp(50), spacing=dp(10))
        btn_save = Button(text="Enregistrer", background_color=(0, 0.7, 0, 1))
        btn_save.bind(on_release=lambda x: self.sauvegarder_tout_match(nom_equipe_input.text, inputs, checkboxes))
        btn_close = Button(text="Fermer", background_color=(0.5, 0.5, 0.5, 1))
        btn_close.bind(on_release=lambda x: self.convoc_popup.dismiss())

        btn_box.add_widget(btn_save)
        btn_box.add_widget(btn_close)
        content.add_widget(btn_box)
        
        self.convoc_popup = Popup(title=f"Gestion : {match_id}", content=content, size_hint=(0.8, 0.8))
        self.convoc_popup.open()
    
    def sauvegarder_tout_match(self, match_id, fields, checkboxes):
        """
        Sauvegarde les données d'un match et rafraîchit l'interface localement.
        """
        nom_equipe = match_id.strip()
        if not nom_equipe:
            print("Erreur : Le nom de l'equipe est obligatoire.")
            return

        def get_val(item):
            return item.text if hasattr(item, 'text') else item

        # CORRECTION : On extrait maintenant aussi 'categorie' et on marque 'est_manuel'
        # Si 'categorie' n'existe pas sur la checkbox (joueur standard), on prend la catégorie courante
        liste_joueurs = []
        for cb in checkboxes:
            if cb.active:
                joueur_data = {
                    "nom": cb.nom_joueur,
                    "prenom": cb.prenom_joueur,
                    "categorie": getattr(cb, 'categorie', ''),
                    "est_manuel": getattr(cb, 'est_manuel', False)
                }
                liste_joueurs.append(joueur_data)

        data = {
            "adversaire": get_val(fields["Adversaire"]),
            "date": get_val(fields["Date"]),
            "heure_rdv": get_val(fields["Heure RDV"]),
            "heure_match": get_val(fields["Heure Match"]),
            "lieu": get_val(fields["Lieu"]),
            "entraineurs": get_val(fields["Entraineurs"]),
            "joueurs_convoques": liste_joueurs
        }
        
        # 3. Envoi à l'API
        url = f"https://fcvv-api.onrender.com/convocations/update/{self.current_cat}/{nom_equipe}"
        
        try:
            headers = self.get_user_header()
            response = requests.put(url, json=data, headers=headers, timeout=5)
            
            if response.status_code == 200:
                cat_data = self._cache_data.setdefault(self.current_cat, {'calendrier': {}})
                cat_data['calendrier'][nom_equipe] = data
                
                if hasattr(self, 'convoc_popup'):
                    self.convoc_popup.dismiss()
                
                # Mise à jour de l'affichage admin si nécessaire
                if hasattr(self, 'convoc_admin_popup') and self.convoc_admin_popup.parent:
                    self.convoc_admin_popup.dismiss()
                    self.ouvrir_gestion_convocations_admin(cat_data['calendrier'])
                
                self.render_content(cat_data)
            else:
                print(f"Erreur API ({response.status_code}) : {response.text}")
                
        except Exception as e:
            print(f"Erreur connexion : {e}")
    
    def refresh_and_update(self):
        """Force la récupération des données fraîches depuis l'API."""
        # On va chercher les convocations à jour
        url = f"https://fcvv-api.onrender.com/convocations/{self.current_cat}"
        
        def do_refresh():
            try:
                r = requests.get(url, timeout=5)
                if r.status_code == 200:
                    # On met à jour le cache directement
                    data = self._cache_data.get(self.current_cat, {})
                    data['calendrier'] = r.json()
                    self._cache_data[self.current_cat] = data
                    # On met à jour l'UI sur le thread principal
                    Clock.schedule_once(lambda dt: self.render_content(data))
            except Exception as e:
                print(f"Erreur rafraichissement : {e}")
        
        threading.Thread(target=do_refresh, daemon=True).start()
        
    def sauvegarder_convocations(self, sid, checkboxes):
        # On extrait les noms des joueurs dont la case est cochée
        liste_convoques = [{"nom": cb.nom_joueur} for cb in checkboxes if cb.active]
        
        payload = {"joueurs_convoques": liste_convoques}
        url = f"https://fcvv-api.onrender.com/convocations/update/{self.current_cat}/{sid}"
        headers = self.get_user_header()
        
        try:
            r = requests.put(url, json=payload, headers=headers, timeout=5)
            if r.status_code == 200:
                print("Convocations mises a jour avec succes")
                if hasattr(self, 'convoc_popup'):
                    self.convoc_popup.dismiss()
                self.update_ui() # Rafraîchir l'affichage
            else:
                print(f"Erreur sauvegarde : {r.status_code}")
        except Exception as e:
            print(f"Erreur connexion : {e}")
    
    def supprimer_convocation(self, match_id):
        url = f"https://fcvv-api.onrender.com/convocations/delete/{self.current_cat}/{match_id}"
        try:
            requests.delete(url, headers=self.get_user_header(), timeout=5)
            
            # Supprimer du cache local
            if self.current_cat in self._cache_data:
                self._cache_data[self.current_cat]['calendrier'].pop(match_id, None)
            
            # Rafraîchir la popup admin
            self.convoc_admin_popup.dismiss()
            self.ouvrir_gestion_convocations_admin(self._cache_data[self.current_cat]['calendrier'])
            
            # Rafraîchir l'UI principale
            self.update_ui()
        except Exception as e:
            print(f"Erreur suppression : {e}")