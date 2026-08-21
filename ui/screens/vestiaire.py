# -*- coding: utf-8 -*-
from datetime import datetime
import hashlib
import json
import logging
import os
from kivy.utils import platform
import sys
import threading
import webbrowser
from kivy.animation import Animation
from kivy.app import App
from kivy.clock import Clock
from kivy.core.text import Label as CoreLabel
from kivy.core.window import Window
from kivy.graphics import Color, Rectangle, RoundedRectangle
from kivy.uix.image import AsyncImage
from kivy.metrics import dp, sp
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.checkbox import CheckBox
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.screenmanager import Screen
from kivy.uix.scrollview import ScrollView
from kivy.uix.spinner import Spinner, SpinnerOption
from kivy.uix.textinput import TextInput
from kivy.uix.widget import Widget
from kivy.utils import escape_markup
from kivy.uix.image import Image
import requests
import yaml

from core.calendrier_view import EventCard
from core.event_manager import EventManager

def get_user_font_size():
    app = App.get_running_app()
    return (
        app.config.getint('User', 'font_size_factor', fallback=18)
        if hasattr(app, 'config')
        else 18
    )


# ==============================================================================
# BUBBLE & CHAT VIEW
# ==============================================================================


class MessageBubble(BoxLayout):

    def __init__(
        self,
        msg_data,
        is_me,
        show_author=True,
        est_admin=False,
        font_size=15,
        **kwargs,
    ):
        super().__init__(
            orientation="vertical",
            size_hint_y=None,
            padding=[0, dp(2)],
            **kwargs,
        )
        self.bind(minimum_height=self.setter("height"))
        self.padding = (
            [dp(10), 0, dp(60), 0] if is_me else [dp(60), 0, dp(10), 0]
        )

        self.bubble = BoxLayout(
            orientation="vertical",
            spacing=dp(4),
            padding=[dp(12), dp(8)],
            size_hint=(None, None),
        )

        if est_admin:
            bg, name_c = ((0.8, 0.5, 0, 1), (1, 1, 1, 1))
        elif is_me:
            bg, name_c = ((0.1, 0.55, 1, 1), (0.85, 0.93, 1, 1))
        else:
            bg, name_c = ((0.22, 0.22, 0.22, 1), (1, 0.85, 0.4, 1))

        with self.bubble.canvas.before:
            Color(*bg)
            self.bubble.rect = RoundedRectangle(
                pos=self.bubble.pos, size=self.bubble.size, radius=[dp(16)]
            )
        self.bubble.bind(
            pos=lambda i, v: setattr(self.bubble.rect, "pos", v),
            size=lambda i, v: setattr(self.bubble.rect, "size", v),
        )

        if show_author:
            auth_text = f"[b]{escape_markup(msg_data.get('auteur', ''))}[/b]"
            if est_admin:
                auth_text = f"[b][!] {auth_text.replace('[b]', '').replace('[/b]', '')}[/b]"

            self.author = Label(
                text=auth_text,
                markup=True,
                color=name_c,
                font_size=f"{max(10, font_size - 3)}sp",
                size_hint=(None, None),
            )
            self.bubble.add_widget(self.author)

        self.content = Label(
            text=msg_data.get("contenu", ""),
            markup=True,
            font_size=f"{max(10, font_size - 2)}sp",
            size_hint=(None, None),
            halign="left",
            valign="top",
            text_size=(Window.width * 0.7 - dp(40), None),
        )
        self.bubble.add_widget(self.content)

        ts_raw = msg_data.get("timestamp", "")
        ts_str = ""

        if ts_raw:
            try:
                dt = datetime.fromisoformat(ts_raw.replace("Z", "+00:00"))
                dt_local = dt.astimezone()
                ts_str = dt_local.strftime("%H:%M")
            except Exception as e:
                print(f"Erreur de parsing date: {e}")

        self.timestamp = Label(
            text=(
                f"[color={'FFFFFF' if is_me or est_admin else 'AAAAAA'}]{ts_str}[/color]"
            ),
            markup=True,
            size_hint=(None, None),
            height=dp(15),
            halign="right",
        )
        self.bubble.add_widget(self.timestamp)

        Clock.schedule_once(self.finalize_layout, 0)
        self.add_widget(self.bubble)

    def finalize_layout(self, *args):
        self.content.text_size = (self.content.text_size[0], None)
        self.content.size = self.content.texture_size
        if hasattr(self, "author"):
            self.author.size = self.author.texture_size
        self.timestamp.size = self.timestamp.texture_size

        max_content_w = max(self.content.width, self.timestamp.width)
        if hasattr(self, "author"):
            max_content_w = max(max_content_w, self.author.width)

        self.bubble.width = max_content_w + dp(30)
        h_auth = self.author.height if hasattr(self, "author") else 0
        self.bubble.height = (
            self.content.height + self.timestamp.height + h_auth + dp(25)
        )


class ChatView(BoxLayout):

    def __init__(self, categorie, screen_instance=None, **kwargs):
        super().__init__(orientation="vertical", spacing=dp(5), **kwargs)
        self.categorie, self.cached_messages, self.limit = categorie, [], 25
        self.last_hash = None
        
        self.opacity = 0

        cat_data = {}
        if screen_instance:
            cat_data = getattr(screen_instance, "_cache_data", {}).get(
                self.categorie, {}
            )

        app = App.get_running_app()
        self.is_admin_only = cat_data.get("chat_admin_only", False)
        self.user_role = (
            app.get_role_for_cat(self.categorie)
            if hasattr(app, "get_role_for_cat")
            else "PARENT"
        )

        self.scroll = ScrollView(bar_width=0, do_scroll_x=False)
        self.msg_container = BoxLayout(
            orientation="vertical", size_hint_y=None
        )
        self.msg_container.bind(
            minimum_height=self.msg_container.setter("height")
        )

        fs = (
            app.config.getint("User", "font_size_factor", fallback=18)
            if hasattr(app, "config")
            else 18
        )

        self.empty_label = Label(
            text="Aucun message pour le moment.\nSoyez le premier à écrire !",
            halign="center",
            valign="middle",
            color=(0.7, 0.7, 0.7, 1),
            size_hint_y=None,
            height=0,
            font_size=f"{fs + 4}sp",
        )
        self.empty_label.bind(
            size=lambda i, v: setattr(i, "text_size", (v[0], None))
        )
        self.msg_container.add_widget(self.empty_label)

        self.scroll.add_widget(self.msg_container)
        self.add_widget(self.scroll)

        if not self.is_admin_only or self.user_role == "ADMIN":
            self.input_box = BoxLayout(
                size_hint_y=None, height=dp(50), spacing=dp(10), padding=dp(5)
            )

            self.input_field = TextInput(
                hint_text="Message...",
                multiline=True,
                size_hint_y=None,
                height=dp(40),
                font_size=f"{fs + 2}sp",
                padding=[dp(10), dp(8)],
            )

            def ajuster_hauteur(instance, min_height):
                nouvelle_hauteur = max(dp(40), min(min_height, dp(220)))
                instance.height = nouvelle_hauteur
                self.input_box.height = nouvelle_hauteur + dp(10)

            self.input_field.bind(minimum_height=ajuster_hauteur)

            send_btn = Button(
                text="Envoyer",
                size_hint_x=0.25,
                font_size=f"{fs}sp",
                bold=True,
            )
            send_btn.bind(on_release=self.send_message)

            self.input_box.add_widget(self.input_field)
            self.input_box.add_widget(send_btn)
            self.add_widget(self.input_box)
        else:
            self.add_widget(
                Label(
                    text=(
                        "[color=888888]Chat en mode lecture seule (Staff"
                        " uniquement)[/color]"
                    ),
                    markup=True,
                    size_hint_y=None,
                    height=dp(50),
                )
            )

        # 1. Chargement immédiat du cache local (silencieux et instantané)
        self.load_cache()
        
        # 2. Appel Firebase en arrière-plan sans perturber l'affichage initial
        self.fetch_messages()
        self.refresh_event = Clock.schedule_interval(self.fetch_messages, 5)

    def scroll_smart_position(self, *args):
        self.msg_container.canvas.ask_update()
        
        def _adjust_scroll(dt):
            content_height = self.msg_container.height
            viewport_height = self.scroll.height
            
            if content_height <= viewport_height:
                self.scroll.scroll_y = 1
            else:
                self.scroll.scroll_y = 0

        Clock.schedule_once(_adjust_scroll, 0.05)
        Clock.schedule_once(_adjust_scroll, 0.15)

    def render_messages(self, scroll_trigger=True):
        self.msg_container.clear_widgets()

        if not self.cached_messages:
            self.empty_label.height = dp(200)
            self.empty_label.opacity = 1
            self.msg_container.add_widget(self.empty_label)
        else:
            self.empty_label.height = 0
            self.empty_label.opacity = 0
            self.msg_container.add_widget(self.empty_label)

        app = App.get_running_app()
        mon_nom = (
            app.config.get("User", "nom_parent", fallback="Inconnu")
            if hasattr(app, "config")
            else "Inconnu"
        )
        fs = (
            app.config.getint("User", "font_size_factor", fallback=15)
            if hasattr(app, "config")
            else 15
        )

        if len(self.cached_messages) > self.limit:
            btn = Button(
                text="Charger plus...", size_hint_y=None, height=dp(40)
            )
            btn.bind(
                on_release=lambda x: self._load_more_and_preserve_scroll()
            )
            self.msg_container.add_widget(btn)

        last_author = None
        last_date = None

        for msg in self.cached_messages[-self.limit :]:
            try:
                msg_ts = msg.get("timestamp", "")
                dt = datetime.fromisoformat(
                    msg_ts.replace("Z", "+00:00")
                ).astimezone()
                current_date = dt.strftime("%d/%m/%Y")
            except Exception:
                current_date = None

            if current_date and current_date != last_date:
                sep = Label(
                    text=f"[b]{current_date}[/b]",
                    markup=True,
                    size_hint_y=None,
                    height=dp(40),
                    color=(0.7, 0.7, 0.7, 1),
                )
                self.msg_container.add_widget(sep)
                last_date = current_date

            auteur = msg.get("auteur")
            est_admin = msg.get("role") == "ADMIN"

            self.msg_container.add_widget(
                MessageBubble(
                    msg,
                    auteur == mon_nom,
                    auteur != last_author,
                    est_admin=est_admin,
                    font_size=fs,
                )
            )
            last_author = auteur

        self.msg_container.do_layout()

        if scroll_trigger:
            self.scroll_smart_position()

        # Révélation unique et fluide de la vue après le premier rendu complet
        if self.opacity == 0:
            Clock.schedule_once(lambda dt: setattr(self, "opacity", 1), 0.1)

    def _load_more_and_preserve_scroll(self):
        old_scroll = self.scroll.scroll_y
        self.limit += 25
        self.render_messages(scroll_trigger=False)
        Clock.schedule_once(
            lambda dt: setattr(self.scroll, "scroll_y", old_scroll), 0.1
        )

    def fetch_messages(self, *args):
        threading.Thread(
            target=self._fetch_messages_thread, daemon=True
        ).start()

    def _fetch_messages_thread(self):
        try:
            mon_nom = self._get_user()
            headers = {"nom_parent": mon_nom}
            
            is_windows = (platform == 'win')
            r = requests.get(f"https://fcvv-api.onrender.com/chat/{self.categorie}",headers=headers,timeout=10,verify=not is_windows)

            if r.status_code == 200:
                data = r.json()
                new_hash = hashlib.md5(str(data).encode()).hexdigest()
                
                # On ne met à jour et re-rend l'interface QUE si le contenu a changé par rapport au cache
                if new_hash != self.last_hash:
                    self.last_hash = new_hash
                    self.cached_messages = data
                    self.save_cache()
                    
                    # Si l'utilisateur est en train de lire du contenu ancien (scroll plus haut), 
                    # on évite de le téléporter de force en bas, d'où scroll_trigger=False si on veut préserver, 
                    # ou true si on est tout en bas. Ici on met un rafraîchissement doux.
                    is_at_bottom = self.scroll.scroll_y <= 0.05
                    Clock.schedule_once(
                        lambda dt: self.render_messages(scroll_trigger=is_at_bottom)
                    )
        except Exception as e:
            print(f"Erreur fetch: {e}")

    def save_cache(self):
        try:
            with open(self.get_cache_path(), "w", encoding="utf-8") as f:
                json.dump(self.cached_messages[-100:], f)
        except Exception as e:
            print(f"Erreur sauvegarde cache: {e}")

    def load_cache(self):
        path = self.get_cache_path()
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    self.cached_messages = json.load(f)
                    self.last_hash = hashlib.md5(str(self.cached_messages).encode()).hexdigest()
                    self.render_messages(scroll_trigger=True)
            except Exception as e:
                print(f"Erreur lecture cache: {e}")

    def send_message(self, *args):
        if self.is_admin_only and self.user_role != "ADMIN":
            return
        text = self.input_field.text.strip()
        if text:
            app = App.get_running_app()
            user_role = (
                app.get_role_for_cat(self.categorie)
                if hasattr(app, "get_role_for_cat")
                else "PARENT"
            )
            mon_nom = self._get_user()
            threading.Thread(
                target=self._send_message_thread,
                args=(mon_nom, text, user_role),
                daemon=True,
            ).start()
            self.input_field.text = ""
            self.input_field.height = dp(40)
            self.input_box.height = dp(50)

    def _send_message_thread(self, mon_nom, text, user_role):
        try:
            headers = {"nom_parent": mon_nom}
            is_windows = (platform == 'win')
            requests.post(f"https://fcvv-api.onrender.com/chat/{self.categorie}",headers=headers,json={"auteur": mon_nom, "contenu": text, "role": user_role},timeout=10,verify=not is_windows)
            Clock.schedule_once(lambda dt: self.fetch_messages())
        except Exception as e:
            print(f"Erreur envoi message: {e}")

    def get_cache_path(self):
        app = App.get_running_app()
        data_dir = app.user_data_dir if hasattr(app, "user_data_dir") else "."
        return os.path.join(data_dir, f"chat_{self.categorie}.json")

    def _get_user(self):
        app = App.get_running_app()
        return (
            app.config.get("User", "nom_parent", fallback="Inconnu")
            if hasattr(app, "config")
            else "Inconnu"
        )

    def on_parent(self, *args):
        if (
            not self.parent
            and hasattr(self, "refresh_event")
            and self.refresh_event
        ):
            self.refresh_event.cancel()


# ==============================================================================
# CARDS & ITEMS (Façon SportEasy)
# ==============================================================================


class StyledCard(BoxLayout):

    def __init__(self, bg_color=(1, 1, 1, 0.1), **kwargs):
        super().__init__(**kwargs)
        self.orientation = "vertical"
        self.padding = dp(15)
        self.spacing = dp(10)
        self.size_hint_y = None
        self.bind(minimum_height=self.setter("height"))
        with self.canvas.before:
            Color(*bg_color)
            self.rect = RoundedRectangle(
                pos=self.pos, size=self.size, radius=[dp(15)]
            )
        self.bind(pos=self._update_rect, size=self._update_rect)

    def _update_rect(self, *args):
        self.rect.pos = self.pos
        self.rect.size = self.size


class InfoCard(StyledCard):

    def __init__(self, text, **kwargs):
        super().__init__(bg_color=(0.1, 0.3, 0.5, 0.2), **kwargs)
        fs = get_user_font_size()

        self.add_widget(
            Label(
                text="[b]NOTE DU COACH[/b]",
                markup=True,
                font_size=f"{fs}sp",
                color=(0.97, 0.92, 0.24, 1),
                size_hint_y=None,
                height=dp(35),
            )
        )

        lbl = Label(
            text=text,
            markup=True,
            halign="left",
            valign="top",
            font_size=f"{fs-2}sp",
            size_hint_y=None,
        )
        lbl.bind(width=lambda i, w: setattr(i, "text_size", (w, None)))
        lbl.bind(texture_size=lambda i, v: setattr(i, "height", v[1]))
        self.add_widget(lbl)

class JoueurItem(BoxLayout):

    def __init__(
        self, nom, statut="", index=None, couleur_texte=(1, 1, 1, 1), **kwargs
    ):
        super().__init__(**kwargs)
        fs = get_user_font_size()
        self.orientation = "horizontal"
        self.size_hint_y = None
        self.spacing = dp(8)
        self.padding = [dp(10), dp(5)]

        self.index_label = Label(
            text=f"{index}." if index else "•",
            font_size=f"{fs}sp",
            bold=True,
            color=couleur_texte,
            size_hint=(None, None),
            width=dp(38),
            halign="right",
        )
        self.index_label.bind(size=lambda i, s: setattr(i, "text_size", s))
        self.add_widget(self.index_label)

        self.name_label = Label(
            text=nom,
            markup=True,
            font_size=f"{fs}sp",
            color=couleur_texte,
            halign="left",
            valign="top",
            size_hint=(1, None),
        )
        self.name_label.bind(
            width=lambda i, w: setattr(i, "text_size", (w, None))
        )
        self.name_label.bind(texture_size=self._sync_layout)
        self.add_widget(self.name_label)

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
                valign="top",
            )
            status.bind(size=lambda i, s: setattr(i, "text_size", s))
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
            vertical_offset = dp(5)

        self.height = row_h
        self.name_label.height = row_h
        self.index_label.height = row_h
        self.index_label.text_size = (
            self.index_label.width,
            row_h - vertical_offset,
        )


class JoueurCardItem(BoxLayout):
    def __init__(self, joueur_data, index=None, callback_clic=None, **kwargs):
        super().__init__(**kwargs)
        try:
            fs = get_user_font_size()
        except NameError:
            fs = 14
            
        self.orientation = "horizontal"
        self.size_hint_y = None
        self.spacing = dp(10)
        self.padding = [dp(12), dp(10)]
        
        self.joueur_data = joueur_data
        self.callback_clic = callback_clic

        # Fond de la carte
        with self.canvas.before:
            Color(0.96, 0.96, 0.98, 1)
            self.bg_rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(10)])
        self.bind(pos=lambda obj, val: setattr(self.bg_rect, 'pos', val),
                  size=lambda obj, val: setattr(self.bg_rect, 'size', val))

        # Numéro / Index
        self.index_label = Label(
            text=f"{index}." if index else "•",
            font_size=f"{fs}sp",
            bold=True,
            color=(0.3, 0.3, 0.35, 1),
            size_hint=(None, None),
            width=dp(42),
            halign="right",
            valign="middle",
            shorten=False,
            mipmap=True
        )
        self.index_label.bind(size=lambda i, s: setattr(i, "text_size", s))
        self.add_widget(self.index_label)

        # Photo de profil avec gestion du cache local
        photo_url = joueur_data.get('photo_url') or joueur_data.get('photo', '')
        initial_source = 'assets/default_user.png'
        
        if photo_url and photo_url.startswith("http"):
            app = App.get_running_app()
            cache_dir = os.path.join(app.user_data_dir, "joueur_cache")
            url_hash = hashlib.md5(photo_url.encode("utf-8")).hexdigest()
            local_path = os.path.join(cache_dir, f"joueur_{url_hash}.png")
            
            if os.path.exists(local_path) and os.path.getsize(local_path) > 0:
                initial_source = local_path

        self.avatar = Image(
            source=initial_source, 
            size_hint=(None, None), 
            size=(dp(45), dp(45)),
            fit_mode="contain"
        )
        
        avatar_container = BoxLayout(size_hint=(None, None), size=(dp(45), dp(45)), pos_hint={"center_y": 0.5})
        avatar_container.add_widget(self.avatar)
        self.add_widget(avatar_container)

        if photo_url and photo_url.startswith("http") and initial_source == 'assets/default_user.png':
            self.load_joueur_image(photo_url)

        # Informations principales
        nom_complet = f"{joueur_data.get('nom', '').upper()} {joueur_data.get('prenom', '')}"
        licence = joueur_data.get('licence', 'N/C')
        date_nais = joueur_data.get('date_naissance') or joueur_data.get('naissance') or 'N/C'
        
        texte_infos = (
            f"[b][color=1a1a24]{nom_complet}[/color][/b]\n"
            f"[size={int(fs*0.75)}sp][color=666670]Licence : {licence}\nNé(e) le : {date_nais}[/color][/size]"
        )

        self.name_label = Label(
            text=texte_infos,
            markup=True,
            font_size=f"{fs*0.9}sp",
            halign="left",
            valign="middle",
            size_hint=(1, None)
        )
        self.name_label.bind(width=lambda i, w: setattr(i, "text_size", (w, None)))
        self.name_label.bind(texture_size=self._sync_layout)
        self.add_widget(self.name_label)

        # Flèche indicative
        arrow_label = Label(
            text=">",
            font_size=f"{fs}sp",
            bold=True,
            color=(0.6, 0.6, 0.65, 1),
            size_hint=(None, None),
            size=(dp(25), dp(40)),
            halign="center",
            valign="middle"
        )
        arrow_label.bind(size=lambda i, s: setattr(i, "text_size", s))
        self.add_widget(arrow_label)

    def load_joueur_image(self, url):
        """Télécharge l'image de manière asynchrone si elle n'est pas en cache."""
        app = App.get_running_app()
        cache_dir = os.path.join(app.user_data_dir, "joueur_cache")
        if not os.path.exists(cache_dir):
            os.makedirs(cache_dir, exist_ok=True)
            
        url_hash = hashlib.md5(url.encode("utf-8")).hexdigest()
        local_path = os.path.join(cache_dir, f"joueur_{url_hash}.png")

        def fetch():
            try:
                is_windows = (platform == 'win')
                r = requests.get(url, timeout=10, verify=not is_windows)
                if r.status_code == 200:
                    with open(local_path, "wb") as f:
                        f.write(r.content)
                    Clock.schedule_once(lambda dt: self._apply_img(local_path), 0)
            except Exception as e:
                print(f"Erreur de telechargement image joueur : {e}")

        threading.Thread(target=fetch, daemon=True).start()

    def _apply_img(self, path):
        """Met à jour l'image si la carte est toujours attachée au DOM Kivy."""
        if self.parent and self.avatar.source != path:
            self.avatar.source = path

    def _sync_layout(self, *args):
        text_h = self.name_label.texture_size[1]
        row_h = max(dp(65), text_h + dp(20))
    
        if self.height != row_h:
            self.height = row_h
    
        if self.name_label.height != row_h:
            self.name_label.height = row_h
    
        if self.index_label.height != row_h:
            self.index_label.height = row_h

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            if self.callback_clic:
                self.callback_clic(self.joueur_data)
            return True
        return super().on_touch_down(touch)

# ==============================================================================
# VESTIAIRE SCREEN PRINCIPAL
# ==============================================================================

class FloatingButton(Button):

    def on_touch_down(self, touch):
        if self.disabled or self.opacity == 0:
            return super().on_touch_down(touch)

        if self.collide_point(*touch.pos):
            self._touch_started_inside = True
            return True

        return super().on_touch_down(touch)

    def on_touch_up(self, touch):
        if getattr(self, "_touch_started_inside", False):
            self._touch_started_inside = False

            if self.collide_point(*touch.pos):
                self.dispatch("on_release")

            return True

        return super().on_touch_up(touch)


class VestiaireScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.current_cat = None
        self.current_sub_tab = "CALENDRIER"
        self._cache_data = {}
        self.KIVY_BLUE = (30 / 255, 58 / 255, 138 / 255, 1)
        self.YELLOW = (247 / 255, 236 / 255, 63 / 255, 1)
        with self.canvas.before:
            Color(*self.KIVY_BLUE)
            self.rect_bg = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._update_rect, size=self._update_rect)
        # Utilisation d'un FloatLayout pour pouvoir superposer le bouton flottant par-dessus le contenu
        self.root_layout = FloatLayout()
        self.add_widget(self.root_layout)
        self.main_layout = BoxLayout(orientation="vertical", size_hint=(1, 1))
        self.root_layout.add_widget(self.main_layout)
        # Barre supérieure des catégories d'équipes
        self.cat_scroll = ScrollView(
            size_hint_y=None, height=dp(70), do_scroll_x=True, do_scroll_y=False, bar_width=0
        )
        self.cat_bar = BoxLayout(size_hint_x=None, height=dp(70), spacing=dp(8), padding=[dp(10), dp(10)])
        self.cat_bar.bind(minimum_width=self.cat_bar.setter("width"))
        self.cat_scroll.add_widget(self.cat_bar)
        # Barre des sous-onglets façon SportEasy
        self.sub_scroll = ScrollView(
            size_hint_y=None, height=dp(60), do_scroll_x=True, do_scroll_y=False, bar_width=0
        )
        self.sub_bar = BoxLayout(size_hint_x=None, height=dp(60), spacing=dp(2), padding=[dp(10), dp(5)])
        self.sub_bar.bind(minimum_width=self.sub_bar.setter("width"))
        self.sub_scroll.add_widget(self.sub_bar)
        self.scroll_content = ScrollView(bar_width=0)
        self.main_layout.add_widget(self.cat_scroll)
        self.main_layout.add_widget(self.sub_scroll)
        self.main_layout.add_widget(self.scroll_content)
        # Création du Bouton Flottant (FAB) sécurisé avec la classe FloatingButton
        self.fab_button = FloatingButton(
            text="+",
            font_size=sp(42),  # Augmenté de 32 à 42 pour grossir le "+"
            bold=True,
            color=(0, 0, 0, 1),
            size_hint=(None, None),
            size=(dp(75), dp(75)),  # Taille augmentée à 75dp x 75dp
            pos_hint={"right": 0.93, "y": 0.04},
            background_normal="",
            background_color=(0, 0, 0, 0),
        )
        
        # Fond arrondi jaune pour le bouton flottant (le radius doit être la moitié de la taille pour faire un cercle parfait : 75 / 2 = 37.5)
        with self.fab_button.canvas.before:
            Color(0.97, 0.93, 0.25, 1)  # Jaune
            self.fab_bg = RoundedRectangle(pos=self.fab_button.pos, size=self.fab_button.size, radius=[dp(37.5)])
        self.fab_button.bind(
            pos=lambda i, v: setattr(self.fab_bg, "pos", v),
            size=lambda i, v: setattr(self.fab_bg, "size", v),
        )
        # Action au clic : s'ouvre uniquement si l'utilisateur est ADMIN
        self.fab_button.bind(on_release=self.verifier_et_ouvrir_admin)
        # On l'ajoute au root_layout pour qu'il flotte par-dessus le reste
        self.root_layout.add_widget(self.fab_button)
        # Masqué par défaut (sera affiché uniquement sur l'onglet Calendrier si Admin)
        self.fab_button.opacity = 0
        self.fab_button.disabled = True

    def _update_rect(self, instance, value):
        self.rect_bg.pos = instance.pos
        self.rect_bg.size = instance.size
    
    def check_fab_visibility(self):
        app = App.get_running_app()
        role = app.get_role_for_cat(self.current_cat) if hasattr(app, "get_role_for_cat") else "PARENT"
        
        if self.current_sub_tab == "CALENDRIER" and role == "ADMIN":
            self.fab_button.opacity = 1
            self.fab_button.disabled = False
        else:
            self.fab_button.opacity = 0
            self.fab_button.disabled = True

    def verifier_et_ouvrir_admin(self, *args):
        calendrier = self._cache_data.get(self.current_cat, {}).get("calendrier", {})
        content = BoxLayout(orientation="vertical", padding=dp(15), spacing=dp(10))
        with content.canvas.before:
            Color(0.95, 0.95, 0.97, 1)
            content.bg_rect = RoundedRectangle(pos=content.pos, size=content.size, radius=[dp(15)])
        content.bind(pos=lambda o, v: setattr(content.bg_rect, 'pos', v), size=lambda o, v: setattr(content.bg_rect, 'size', v))
        
        btn_add = Button(text="[b]+ Ajouter un événement[/b]", markup=True, size_hint_y=None, height=dp(45), background_normal="", background_color=(0.15, 0.65, 0.35, 1), color=(1, 1, 1, 1))
        btn_close = Button(text="Fermer", size_hint_y=None, height=dp(40), background_normal="", background_color=(0.7, 0.7, 0.73, 1), color=(0.2, 0.2, 0.25, 1), bold=True)
        
        content.add_widget(Label(text="[b]Gestion des événements[/b]", markup=True, size_hint_y=None, height=dp(35), font_size=dp(18), color=(0.1, 0.1, 0.15, 1), halign="center"))
        content.add_widget(btn_add)
        
        scroll = ScrollView(size_hint=(1, 1), bar_width=0)
        grid = GridLayout(cols=1, size_hint_y=None, spacing=dp(8), padding=dp(2))
        grid.bind(minimum_height=grid.setter("height"))

        if not calendrier:
            grid.add_widget(Label(text="Aucun événement enregistré.", size_hint_y=None, height=dp(40), color=(0.4, 0.4, 0.45, 1), halign="center"))
        else:
            for nom_match, match_info in calendrier.items():
                vrai_titre = match_info.get("titre") or match_info.get("adversaire") or match_info.get("nom") or str(nom_match)
                type_ev, date_ev = match_info.get("type", "ÉVÉNEMENT").upper(), match_info.get("date", "")
                
                box = BoxLayout(size_hint_y=None, height=dp(45), spacing=dp(8))
                with box.canvas.before:
                    Color(1, 1, 1, 1)
                    box.bg_rect = RoundedRectangle(pos=box.pos, size=box.size, radius=[dp(8)])
                box.bind(pos=lambda o, v, bg=box.bg_rect: setattr(bg, 'pos', v), size=lambda o, v, bg=box.bg_rect: setattr(bg, 'size', v))

                lbl = Label(text=f"[b]{vrai_titre}[/b] ({type_ev})" + (f" - {date_ev}" if date_ev else ""), markup=True, color=(0.15, 0.15, 0.2, 1), halign="left", padding=(dp(10), 0))
                lbl.bind(size=lambda s, w: setattr(s, 'text_size', w))
                
                btn_edit = Button(text="Modifier", size_hint_x=None, width=dp(85), background_normal="", background_color=(0.2, 0.5, 0.8, 1), color=(1, 1, 1, 1), bold=True)
                btn_del = Button(text="X", size_hint_x=None, width=dp(40), background_normal="", background_color=(0.8, 0.2, 0.2, 1), color=(1, 1, 1, 1), bold=True)
                
                btn_edit.bind(on_release=lambda _, s=nom_match, i=match_info: [self.convoc_admin_popup.dismiss(), self.ouvrir_gestion_convocations(s, i)])
                btn_del.bind(on_release=lambda _, s=nom_match: self.supprimer_convocation(s))

                box.add_widget(lbl); box.add_widget(btn_edit); box.add_widget(btn_del)
                grid.add_widget(box)

        scroll.add_widget(grid)
        content.add_widget(scroll)
        content.add_widget(btn_close)

        self.convoc_admin_popup = Popup(title="", title_size=0, content=content, size_hint=(0.92, 0.88), separator_height=0, background="", background_color=(0, 0, 0, 0.6))
        btn_close.bind(on_release=lambda _: self.convoc_admin_popup.dismiss())
        btn_add.bind(on_release=lambda _: [self.convoc_admin_popup.dismiss(), self.ouvrir_gestion_convocations("Nouvel événement", {})])
        self.convoc_admin_popup.open()

    def update_ui(self):
        app = App.get_running_app()
        if not getattr(app, "authorized_vestiaires", None): return
        if not self.current_cat: self.current_cat = app.authorized_vestiaires[0]
        fs = get_user_font_size()

        self.cat_bar.clear_widgets()
        for cat in app.authorized_vestiaires:
            is_active = self.current_cat == cat
            role = app.get_role_for_cat(cat) if hasattr(app, "get_role_for_cat") else "PARENT"
            disp = f"{cat} [size={int((fs+2)*0.7)}sp][color=888888](ADMIN)[/color][/size]" if role == "ADMIN" else cat

            btn = Button(text=disp, markup=True, size_hint=(None, 1), font_size=f"{fs+2}sp", background_normal="", background_color=(0, 0, 0, 0), bold=True, color=(0, 0, 0, 1) if is_active else (1, 1, 1, 1))
            btn.bind(texture_size=lambda i, v: setattr(i, "width", max(dp(100), v[0] + dp(30))))
            with btn.canvas.before:
                Color(0.97, 0.93, 0.25, 1) if is_active else Color(1, 1, 1, 0.15)
                btn.bg = RoundedRectangle(pos=btn.pos, size=btn.size, radius=[dp(8)])
            btn.bind(pos=lambda i, v: setattr(i.bg, "pos", v), size=lambda i, v: setattr(i.bg, "size", v), on_release=lambda _, c=cat: self.set_category(c))
            self.cat_bar.add_widget(btn)

        self.sub_bar.clear_widgets()
        role_actuel = app.get_role_for_cat(self.current_cat) if hasattr(app, "get_role_for_cat") else "PARENT"

        for sub in ["CALENDRIER", "MESSAGES", "NOTIFICATIONS", "SAISON", "EQUIPE", "DOCS", "PROFIL"]:
            if sub == "EQUIPE" and role_actuel != "ADMIN": continue
            is_active = self.current_sub_tab == sub
            btn = Button(text=sub.capitalize(), size_hint=(None, 1), font_size=f"{fs-2}sp", background_normal="", background_color=(0, 0, 0, 0), bold=is_active, color=(0, 0, 0, 1) if is_active else (1, 1, 1, 1))
            btn.bind(texture_size=lambda i, v: setattr(i, "width", max(dp(90), v[0] + dp(20))))
            with btn.canvas.before:
                Color(0.97, 0.93, 0.25, 1) if is_active else Color(1, 1, 1, 0.1)
                btn.bg = Rectangle(pos=btn.pos, size=btn.size)
            btn.bind(pos=lambda i, v: setattr(i.bg, "pos", v), size=lambda i, v: setattr(i.bg, "size", v), on_release=lambda _, s=sub: self.set_sub_tab(s))
            self.sub_bar.add_widget(btn)

        if self.current_sub_tab == "EQUIPE" and role_actuel != "ADMIN": self.current_sub_tab = "CALENDRIER"

        self.scroll_content.clear_widgets()
        data = self._cache_data.get(self.current_cat)
        is_cal = self.current_sub_tab == "CALENDRIER"

        if data:
            # Si le calendrier n'a pas encore été chargé depuis Firebase
            if is_cal and "calendrier" not in data:
                self.scroll_content.add_widget(Label(text="Chargement des événements...", color=(1, 1, 1, 0.6), font_size=f"{fs + 2}sp"))
                self.fetch_convocations_from_firebase(data, silent=True)
            else:
                self.render_content(data)
                if is_cal:
                    self.fetch_convocations_from_firebase(data, silent=True)
        else:
            self.scroll_content.add_widget(Label(text="Chargement des événements..." if is_cal else "Chargement des données de l'équipe...", color=(1, 1, 1, 0.6 if is_cal else 0.5), font_size=f"{fs + (2 if is_cal else 4)}sp"))
            vest_cfg = app.app_config.get("fcvv", {}).get("appli", {}).get("vestiaire", []) if hasattr(app, "app_config") else []
            cat_info = next((i for i in vest_cfg if i.get("categorie") == self.current_cat), None)
            if cat_info:
                path = os.path.join(getattr(app, "user_data_dir", "."), f"data_{self.current_cat}.yaml")
                threading.Thread(target=lambda info, p: self.verify_and_load(info, p), args=(cat_info, path), daemon=True).start()

        self.check_fab_visibility()

    def fetch_convocations_from_firebase(self, data, silent=False):
        if getattr(self, "_fetching_in_progress", False): return
        self._fetching_in_progress, requested_cat, requested_tab = True, self.current_cat, self.current_sub_tab

        if not silent:
            self.scroll_content.clear_widgets()
            self.scroll_content.opacity, self.scroll_content.do_scroll_y = 1, True
            self.scroll_content.add_widget(Label(text="Chargement des événements...", color=(1, 1, 1, 0.6), font_size=f"{get_user_font_size() + 2}sp"))

        url = f"https://fcvv-api.onrender.com/convocations/{requested_cat}"

        def apply_result(convocations):
            self._fetching_in_progress = False
            if requested_cat == self.current_cat and requested_tab == self.current_sub_tab:
                data["calendrier"] = convocations
                self.render_content(data)

        def do_request():
            try:
                is_windows = (platform == 'win')
                r = requests.get(url, timeout=10, verify=not is_windows)
                convs = r.json() if r.status_code == 200 else {}
            except Exception:
                convs = {}
            Clock.schedule_once(lambda dt: apply_result(convs), 0)

        threading.Thread(target=do_request, daemon=True).start()

    def on_enter(self, *args):
        app = App.get_running_app()
        
        if not hasattr(app, "authorized_vestiaires") or not app.authorized_vestiaires:
            if hasattr(app, "root") and hasattr(app.root, "switch_screen"):
                app.root.switch_screen("login_vestiaire")
            return

        if not self.current_cat:
            self.current_cat = app.authorized_vestiaires[0]
        # 1. Afficher l'UI immédiatement avec ce qu'on a (en cache ou non)
        self.update_ui()
        # 2. Vérifier et mettre à jour TOUTES les AUTRES catégories autorisées en arrière-plan
        self.verifier_toutes_les_categories()

    def verifier_toutes_les_categories(self):
        app = App.get_running_app()
        vest_cfg = app.app_config.get("fcvv", {}).get("appli", {}).get("vestiaire", []) if hasattr(app, "app_config") else []
        for cat in getattr(app, "authorized_vestiaires", []):
            if cat != self.current_cat and (cat_info := next((i for i in vest_cfg if i.get("categorie") == cat), None)):
                path = os.path.join(getattr(app, "user_data_dir", "."), f"data_{cat}.yaml")
                threading.Thread(target=self._verifier_et_charger_silencieux, args=(cat_info, path, cat), daemon=True).start()

    def _verifier_et_charger_silencieux(self, cat_info, path, target_cat):
        url = f"https://docs.google.com/uc?id={cat_info.get('file_id')}&export=download"
        try:
            is_windows = (platform == 'win')
            r = requests.get(url, timeout=10, verify=not is_windows)
            if r.status_code == 200:
                if not os.path.exists(path) or hashlib.md5(open(path, "rb").read()).hexdigest() != hashlib.md5(r.content).hexdigest():
                    with open(path, "wb") as f: f.write(r.content)
                else:
                    print(f"[VESTIAIRE DEBUG] Fichier YAML inchange pour {target_cat}")
        except Exception as e:
            print(f"[VESTIAIRE DEBUG] Erreur telechargement pour {target_cat}: {e}")

        data = cat_info.copy()
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f: data.update(yaml.safe_load(f) or {})
            except Exception as e:
                print(f"[VESTIAIRE DEBUG] Erreur YAML pour {target_cat}: {e}")

        self._cache_data[target_cat] = data
        if target_cat == self.current_cat:
            Clock.schedule_once(lambda dt: self.fetch_convocations_from_firebase(data) if self.current_sub_tab == "CALENDRIER" else self.render_content(data), 0)

    def set_category(self, cat):
        if self.current_cat == cat:
            return
        self.scroll_content.clear_widgets()
        self.current_cat = cat
        self.current_sub_tab = "CALENDRIER"
        anim = Animation(opacity=0, duration=0.1)

        def on_complete(*args):
            self.update_ui()
            self.scroll_content.opacity = 0
            Animation(opacity=1, duration=0.15).start(self.scroll_content)

        anim.bind(on_complete=on_complete)
        anim.start(self.scroll_content)

    def set_sub_tab(self, sub):
        if self.current_sub_tab == sub:
            return
        self.current_sub_tab = sub
        anim = Animation(opacity=0, duration=0.1)

        def on_complete(*args):
            self.update_ui()
            Animation(opacity=1, duration=0.1).start(self.scroll_content)

        anim.bind(on_complete=on_complete)
        anim.start(self.scroll_content)

    def verify_and_load(self, cat_info, path):
        url = f"https://docs.google.com/uc?id={cat_info.get('file_id')}&export=download"
        try:
            is_windows = (platform == 'win')
            r = requests.get(url, timeout=10, verify=not is_windows)
            if r.status_code == 200:
                if not os.path.exists(path) or hashlib.md5(open(path, "rb").read()).hexdigest() != hashlib.md5(r.content).hexdigest():
                    with open(path, "wb") as f: f.write(r.content)
        except Exception as e:
            logging.error(f"Erreur téléchargement: {e}")

        data = cat_info.copy()
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f: data.update(yaml.safe_load(f) or {})
            except Exception as e:
                logging.error(f"Erreur YAML: {e}")

        self._cache_data[self.current_cat] = data
        Clock.schedule_once(lambda dt: self.fetch_convocations_from_firebase(data) if self.current_sub_tab == "CALENDRIER" else self.render_content(data), 0)

    def render_content(self, data):
        self.scroll_content.clear_widgets()
        self.scroll_content.scroll_y = 1
        fs = get_user_font_size()

        def SectionTitle(t):
            return Label(text=f"[b]{t}[/b]", markup=True, color=self.YELLOW, size_hint_y=None, height=dp(45), font_size=f"{fs + 4}sp")

        if self.current_sub_tab == "MESSAGES":
            self.scroll_content.do_scroll_y = False
            self.scroll_content.add_widget(ChatView(categorie=self.current_cat, screen_instance=self, size_hint=(1, 1)))
            if hasattr(self, "check_fab_visibility"): self.check_fab_visibility()
            return

        self.scroll_content.do_scroll_y = True
        layout = BoxLayout(orientation="vertical", padding=dp(20), spacing=dp(20), size_hint_y=None, opacity=0)
        layout.bind(minimum_height=layout.setter("height"))

        app = App.get_running_app()
        role = app.get_role_for_cat(self.current_cat) if hasattr(app, "get_role_for_cat") else "PARENT"

        if self.current_sub_tab == "CALENDRIER":
            active_cat = self.current_cat
            if not (calendrier := data.get("calendrier", {})):
                layout.add_widget(InfoCard(text="Aucun événement à venir pour le moment."))
            else:
                aujourd_hui, evenements_a_venir, evenements_passes = datetime.now().date(), [], {}
                mois_fr = ["", "JANVIER", "FEVRIER", "MARS", "AVRIL", "MAI", "JUIN", "JUILLET", "AOUT", "SEPTEMBRE", "OCTOBRE", "NOVEMBRE", "DECEMBRE"]

                for match_id, match_info in calendrier.items():
                    raw_date, parsed_dt = match_info.get("date", "").strip(), None
                    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):
                        try:
                            parsed_dt = datetime.strptime(raw_date, fmt).date(); break
                        except ValueError: continue

                    if parsed_dt:
                        if parsed_dt >= aujourd_hui:
                            evenements_a_venir.append((parsed_dt, match_id, match_info))
                        else:
                            evenements_passes.setdefault(f"{mois_fr[parsed_dt.month]} {parsed_dt.year}", []).append((parsed_dt, match_id, match_info))
                    else:
                        evenements_a_venir.append((datetime.max.date(), match_id, match_info))

                if evenements_a_venir:
                    layout.add_widget(SectionTitle("À venir..."))
                    for _, m_id, m_info in sorted(evenements_a_venir, key=lambda x: x[0]):
                        layout.add_widget(EventCard(match_id=m_id, match_data=m_info, categorie=active_cat))

                for mois_annee in sorted(evenements_passes.keys(), reverse=True):
                    layout.add_widget(SectionTitle(mois_annee))
                    for _, m_id, m_info in sorted(evenements_passes[mois_annee], key=lambda x: x[0], reverse=True):
                        layout.add_widget(EventCard(match_id=m_id, match_data=m_info, categorie=active_cat))

        elif self.current_sub_tab == "NOTIFICATIONS":
            layout.add_widget(SectionTitle("CENTRE DE NOTIFICATIONS"))
            if not (calendrier := data.get("calendrier", {})):
                layout.add_widget(InfoCard(text="Aucune notification récente."))
            else:
                historique = []
                for match_id, match_info in calendrier.items():
                    type_evt = match_info.get("type", "ÉVÉNEMENT").upper()
                    titre, adversaire, date_evt, lieu_evt = map(lambda k: match_info.get(k, "").strip(), ("titre", "adversaire", "date", "lieu"))
                    commit_msg, timestamp_action = match_info.get("dernier_commit", "").strip(), match_info.get("timestamp_action", "")

                    titre_carte = titre or ("Entraînement" if type_evt == "ENTRAINEMENT" else (f"Match ({match_id})" if type_evt == "MATCH" else f"Événement : {titre}" if titre else "Événement"))
                    est_mod = bool(commit_msg) and "création" not in commit_msg.lower()
                    
                    ligne_statut = f"[b]{'Modifié le' if est_mod else 'Crée le'}[/b]" + (f" {timestamp_action}" if timestamp_action else "")
                    ligne_details = f"Date : {date_evt}" + (f" • Lieu : {lieu_evt}" if lieu_evt else "")
                    ligne_commit = f"\n[color=555555]« {commit_msg} »[/color]" if (est_mod and commit_msg) else ""

                    texte_notif = f"[size={fs + 2}sp][b]{titre_carte}[/b][/size]\n[size={fs - 1}sp]{ligne_statut}\n{ligne_details}{ligne_commit}[/size]"
                    parsed_dt = next((datetime.strptime(date_evt, fmt) for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y") if datetime.strptime(date_evt, fmt)), datetime.min)
                    historique.append((parsed_dt, texte_notif))

                for _, texte in sorted(historique, key=lambda x: x[0], reverse=True):
                    card = BoxLayout(orientation="vertical", padding=dp(12), spacing=dp(5), size_hint_y=None)
                    with card.canvas.before:
                        Color(0.95, 0.95, 0.95, 1)
                        card.bg_rect = RoundedRectangle(pos=card.pos, size=card.size, radius=[dp(8)])
                    card.bind(pos=lambda c, p: setattr(c.bg_rect, 'pos', p), size=lambda c, s: setattr(c.bg_rect, 'size', s))

                    lbl_notif = Label(text=texte, markup=True, color=(0.1, 0.1, 0.1, 1), font_size=f"{fs - 1}sp", halign="center", valign="middle", size_hint_y=None)
                    card.add_widget(lbl_notif)

                    def update_card_height(c, w, label=lbl_notif):
                        if w > 0:
                            label.text_size = (w - dp(24), None)
                            label.texture_update()
                            c.height = label.height = label.texture_size[1] + dp(24)

                    card.bind(width=update_card_height)
                    Clock.schedule_once(lambda dt, c=card: update_card_height(c, c.width), 0.05)
                    layout.add_widget(card)

        elif self.current_sub_tab == "SAISON":
            layout.add_widget(SectionTitle("CALENDRIER & CLASSEMENT"))
            if not (calendrier_saison := data.get("calendrier_saison", {})):
                layout.add_widget(Label(text="Aucune donnée saison trouvée.", italic=True))
            else:
                for nom_eq, infos_eq in calendrier_saison.items():
                    layout.add_widget(Label(text=f"[b]{nom_eq.upper()}[/b]", markup=True, size_hint_y=None, height=dp(40), font_size=f"{fs-2}sp"))
                    for label, url_key in [("Calendrier", "calendrier"), ("Classement", "classement")]:
                        if (url := infos_eq.get("liens_fff", {}).get(url_key)) and url.startswith("http"):
                            btn = Button(text=label, size_hint_y=None, height=dp(50), font_size=f"{fs*0.8}sp")
                            btn.bind(on_release=lambda _, u=url: webbrowser.open(u))
                            layout.add_widget(btn)

        elif self.current_sub_tab == "EQUIPE":
            layout.add_widget(SectionTitle("EFFECTIF COMPLET"))
            joueurs = sorted(data.get("tous_les_joueurs", []), key=lambda j: (j.get("nom", "").strip().upper(), j.get("prenom", "").strip().upper()))
            if not joueurs:
                layout.add_widget(Label(text="Aucun joueur enregistré.", italic=True, size_hint_y=None, height=dp(100)))
            else:
                if hasattr(self, "_populate_event") and self._populate_event: self._populate_event.cancel()

                def stream_joueurs(joueurs_list, batch_size=5):
                    total = len(joueurs_list)
                    def add_batch(index_actuel, *args):
                        if self.current_sub_tab != "EQUIPE":
                            self._populate_event = None; return
                        fin = min(index_actuel + batch_size, total)
                        for idx in range(index_actuel, fin):
                            layout.add_widget(JoueurCardItem(joueur_data=joueurs_list[idx], index=idx + 1, callback_clic=self.ouvrir_details_joueur))
                        self._populate_event = Clock.schedule_once(lambda dt: add_batch(fin), 0) if fin < total else None
                    self._populate_event = Clock.schedule_once(lambda dt: add_batch(0), 0)

                stream_joueurs(joueurs)

        elif self.current_sub_tab == "DOCS":
            layout.add_widget(SectionTitle("DOCUMENTS UTILES"))
            if not (docs := [d for d in data.get("documents", []) if d.get("nom")]):
                layout.add_widget(Label(text="Aucun document disponible pour le moment.", italic=True, size_hint_y=None, height=dp(100), font_size=f"{fs-2}sp", color=(0.7, 0.7, 0.7, 1)))
            else:
                for doc in docs:
                    btn = Button(text=doc.get("nom"), size_hint_y=None, height=dp(60), font_size=f"{fs*0.8}sp")
                    if url := doc.get("url"): btn.bind(on_release=lambda _, u=url: webbrowser.open(u))
                    else: btn.disabled = True; btn.text += " (Lien invalide)"
                    layout.add_widget(btn)

        elif self.current_sub_tab == "PROFIL":
            layout.add_widget(SectionTitle("MON PROFIL"))
            mon_nom = app.config.get("User", "nom_parent", fallback="Inconnu") if hasattr(app, "config") else "Inconnu"
            valeur_brute = app.config.get("Roles", f"{self.current_cat.lower()}_joueur", fallback="") if hasattr(app, "config") and app.config.has_section("Roles") else ""
            elements = [e.strip() for e in valeur_brute.split(",") if e.strip()]
            enfants = [e for e in elements if not e.startswith("COACH_")]
            est_coach = any(e.startswith("COACH_") for e in elements) or ("COACH" in role.upper())
            
            bloc_enfants = "[b]Joueur associé :[/b] Aucun" if not enfants else f"[b]Joueur associé :[/b] {enfants[0]}" if len(enfants) == 1 else f"[b]Joueurs associés :[/b]\n" + "\n".join([f"  • {e}" for e in enfants])
            hauteur_label = dp(140) if len(enfants) <= 1 else dp(140) + (len(enfants) * dp(20))

            layout.add_widget(Label(text=f"[b]Utilisateur :[/b] {mon_nom}\n[b]Rôle principal :[/b] {role}\n[b]Catégorie active :[/b] {self.current_cat}\n{bloc_enfants}\n[b]Statut Coach :[/b] {'Oui (Coach / Staff)' if est_coach else 'Non'}", markup=True, font_size=f"{fs}sp", size_hint_y=None, height=hauteur_label))
            layout.add_widget(Widget(size_hint_y=None, height=dp(25)))
            
            btn_logout = Button(text="Déconnexion de la catégorie", size_hint_y=None, height=dp(50), background_color=(0.8, 0.2, 0.2, 1), background_normal="")
            btn_logout.bind(on_release=lambda _: self.logout_user())
            layout.add_widget(btn_logout)

        self.scroll_content.add_widget(layout)
        layout.opacity = 1
        if hasattr(self, "check_fab_visibility"): self.check_fab_visibility()
        Clock.schedule_once(lambda dt: self.scroll_content.canvas.ask_update(), 0.1)
        
    
    def ouvrir_details_joueur(self, joueur):
        fs = get_user_font_size()
        content = BoxLayout(orientation="vertical", padding=dp(20), spacing=dp(15))
        with content.canvas.before:
            Color(0.95, 0.95, 0.97, 1)
            content.bg_rect = RoundedRectangle(pos=content.pos, size=content.size, radius=[dp(15)])
        content.bind(pos=lambda o, v: setattr(content.bg_rect, 'pos', v), size=lambda o, v: setattr(content.bg_rect, 'size', v))

        nom_complet = f"{joueur.get('nom', '').upper()} {joueur.get('prenom', '')}"
        content.add_widget(Label(text=f"[b]{nom_complet}[/b]", markup=True, size_hint_y=None, height=dp(35), font_size=f"{fs+4}sp", color=(0.1, 0.1, 0.15, 1), halign="center"))

        avatar_source = 'assets/default_user.png'
        if (photo_url := joueur.get('photo_url') or joueur.get('photo', '')) and photo_url.startswith("http"):
            cache_dir = os.path.join(App.get_running_app().user_data_dir, "joueur_cache")
            local_path = os.path.join(cache_dir, f"joueur_{hashlib.md5(photo_url.encode('utf-8')).hexdigest()}.png")
            if os.path.exists(local_path) and os.path.getsize(local_path) > 0:
                avatar_source = local_path

        img_container = BoxLayout(size_hint=(None, None), size=(dp(120), dp(120)), pos_hint={"center_x": 0.5})
        img_container.add_widget(Image(source=avatar_source, fit_mode="contain"))
        content.add_widget(img_container)

        scroll = ScrollView(size_hint=(1, 1), bar_width=0)
        details_layout = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(10), padding=dp(5))
        details_layout.bind(minimum_height=details_layout.setter("height"))

        licence = joueur.get('licence', 'Non renseignée')
        date_nais = joueur.get('date_naissance') or joueur.get('naissance') or 'Non renseignée'
        telephone = joueur.get('telephone') or joueur.get('tel') or 'Non renseigné'
        email = joueur.get('email') or 'Non renseigné'
        adresse = joueur.get('adresse') or 'Non renseignée'
        poste = joueur.get('poste') or joueur.get('position') or 'Non spécifié'
        
        lbl_details = Label(
            text=f"[b]Informations sportives :[/b]\n• Poste : {poste}\n• Numéro de licence : {licence}\n\n"
                 f"[b]Informations personnelles :[/b]\n• Date de naissance : {date_nais}\n• Adresse : {adresse}\n\n"
                 f"[b]Contacts :[/b]\n• Téléphone : {telephone}\n• Email : {email}",
            markup=True, font_size=f"{fs}sp", color=(0.2, 0.2, 0.25, 1), halign="left", valign="top", size_hint_y=None
        )
        lbl_details.bind(width=lambda s, w: setattr(s, 'text_size', (w, None)), texture_size=lambda s, t: setattr(s, 'height', t[1]))
        
        details_layout.add_widget(lbl_details)
        scroll.add_widget(details_layout)
        content.add_widget(scroll)

        btn_close = Button(text="Fermer", size_hint_y=None, height=dp(45), background_normal="", background_color=(0.15, 0.5, 0.8, 1), color=(1, 1, 1, 1), bold=True)
        content.add_widget(btn_close)

        self.joueur_popup = Popup(title="", title_size=0, content=content, size_hint=(0.9, 0.85), separator_height=0, background="", background_color=(0, 0, 0, 0.6))
        btn_close.bind(on_release=lambda _: self.joueur_popup.dismiss())
        self.joueur_popup.open()
    
    
    def logout_user(self):
        app = App.get_running_app()
        if not app or not (cat_id := str(self.current_cat or "").strip()): return

        anciennes_categories, joueurs_a_retirer = list(getattr(app, "authorized_vestiaires", [])), []

        if hasattr(app, "get_joueur_associe_pour_cat") and (res := app.get_joueur_associe_pour_cat(cat_id)):
            joueurs_a_retirer.extend(res if isinstance(res, list) else [x.strip() for x in str(res).split(",") if x.strip()])

        if not joueurs_a_retirer and hasattr(app, "roles") and isinstance(app.roles, dict):
            if isinstance(cat_role := app.roles.get(cat_id, {}) or app.roles.get(cat_id.lower(), {}), dict):
                v = cat_role.get("joueur", "") or cat_role.get("joueurs", "")
                joueurs_a_retirer.extend(v if isinstance(v, list) else [x.strip() for x in str(v).split(",") if x.strip()])

        if not joueurs_a_retirer and hasattr(app, "config") and app.config:
            for k in [f"{cat_id.lower()}_joueur", f"{cat_id}_joueur", f"joueur_{cat_id.lower()}", f"joueur_{cat_id}"]:
                val = app.config.get("Roles", k, fallback="") if app.config.has_option("Roles", k) else app.config.get("User", k, fallback="") if app.config.has_option("User", k) else ""
                if val:
                    joueurs_a_retirer.extend([x.strip() for x in val.split(",") if x.strip()]); break

        if not joueurs_a_retirer and hasattr(self, "get_joueurs_associes_pour_parent") and isinstance(res := self.get_joueurs_associes_pour_parent(), list):
            joueurs_a_retirer.extend([str(x).strip() for x in res if x])

        joueurs_a_retirer = list(set(str(j).strip() for j in joueurs_a_retirer if str(j).strip()))

        if hasattr(app, "authorized_vestiaires") and isinstance(app.authorized_vestiaires, list):
            app.authorized_vestiaires = [v for v in app.authorized_vestiaires if str(v).strip() != cat_id]

        if hasattr(app, "roles") and isinstance(app.roles, dict): app.roles.pop(cat_id, None)

        if hasattr(app, "config") and app.config:
            if app.config.has_section("Roles"):
                cat_lower, pfx = cat_id.lower(), f"{cat_id.lower()}_"
                for opt in list(app.config.options("Roles")):
                    if opt.lower() == cat_lower or opt.lower().startswith(pfx): app.config.remove_option("Roles", opt)

            for k in [f"joueur_{cat_id.lower()}", f"joueur_{cat_id}", f"{cat_id.lower()}_joueur", f"{cat_id}_joueur"]:
                if app.config.has_option("User", k): app.config.remove_option("User", k)

            if app.config.has_section("User"): app.config.set("User", "authorized_list", ",".join(getattr(app, "authorized_vestiaires", [])))
            app.config.write()

        if hasattr(app, "gerer_abonnements_fcm"):
            try: app.gerer_abonnements_fcm(getattr(app, "authorized_vestiaires", []), anciennes_categories)
            except Exception as e: print(f"[DEBUG] Erreur desabonnement FCM : {e}")

        def _sync_firebase_unregister():
            try:
                user_nom = ""
                if hasattr(app, "config") and app.config:
                    user_nom = app.config.get("User", "nom_parent", fallback="") or app.config.get("User", "nom", fallback="")
                if not user_nom and hasattr(app, "user_nom"): user_nom = app.user_nom
                if not user_nom: return print("[FIREBASE] Annulation : Aucun nom d'utilisateur trouve pour la desinscription.")

                headers = self.get_user_header() if hasattr(self, "get_user_header") else {"Content-Type": "application/json"}
                is_windows = (platform == 'win')
                res = requests.post("https://fcvv-api.onrender.com/users/unregister", json={"nom": user_nom, "categorie": cat_id, "joueurs_a_retirer": joueurs_a_retirer}, headers=headers, timeout=10, verify=not is_windows)
                print(f"[FIREBASE] Succes unregister : {res.json()}" if res.status_code == 200 else f"[FIREBASE] Erreur unregister ({res.status_code}) : {res.text}")
            except Exception as e: print(f"[FIREBASE] Erreur lors de l'appel /users/unregister : {e}")

        threading.Thread(target=_sync_firebase_unregister, daemon=True).start()
        self.current_cat = None

        def _changer_ecran(dt):
            try:
                if hasattr(app, "root") and hasattr(app.root, "switch_screen"):
                    app.root.switch_screen("home" if getattr(app, "authorized_vestiaires", []) else "login_vestiaire")
            except Exception as e: print(f"[ERROR] Impossible de changer d'ecran : {e}")

        Clock.schedule_once(_changer_ecran, 0)

    def get_joueurs_associes_pour_parent(self, categorie_cible=None):
        app = App.get_running_app()
        cat = categorie_cible or self.current_cat
        # 1. On récupère en priorité le joueur associé enregistré localement pour cette catégorie
        joueur_stocke = app.get_joueur_associe_pour_cat(cat) if hasattr(app, "get_joueur_associe_pour_cat") else ""
        if joueur_stocke:
            # Si c'est une chaîne avec des virgules (ex: "Enfant 1, Enfant 2"), on la découpe pour voir si c'est ça qui bloque
            if isinstance(joueur_stocke, str) and "," in joueur_stocke:
                liste_decoupee = [j.strip() for j in joueur_stocke.split(",") if j.strip()]
                return liste_decoupee
            return [joueur_stocke]
        # 2. Fallback de sécurité si l'admin n'a pas d'enfant direct lié mais le rôle ADMIN
        role = app.get_role_for_cat(self.current_cat) if hasattr(app, "get_role_for_cat") else "PARENT"
        if role == "ADMIN":
            cat_data = self._cache_data.get(self.current_cat, {})
            tous_les_joueurs = cat_data.get("tous_les_joueurs", [])
            admin_joueurs = [f"{j.get('nom', '').upper()} {j.get('prenom', '')}" for j in tous_les_joueurs]
            return admin_joueurs
        return []
    
    def get_user_header(self):
        app = App.get_running_app()
        nom = app.config.get("User", "nom_parent", fallback="").strip() if hasattr(app, "config") else ""
        return {"nom_parent": nom or "anonymous"}

    def ouvrir_gestion_convocations(self, match_id, match_info):
        # Fait le lien avec l'Event Manager propre
        EventManager.ouvrir_formulaire(self, match_id, match_info)

    def supprimer_convocation(self, nom_match):
        target_cat = self.current_cat
        def do_delete():
            try:
                is_windows = (platform == 'win')
                if requests.delete(f"https://fcvv-api.onrender.com/convocations/delete/{target_cat}/{nom_match}", headers=self.get_user_header(), timeout=10, verify=not is_windows).status_code == 200:
                    cat_data = self._cache_data.get(target_cat, {})
                    cat_data.get("calendrier", {}).pop(nom_match, None)

                    def actualiser(dt):
                        if popup := getattr(self, "convoc_admin_popup", None):
                            try: popup.dismiss()
                            except Exception: pass
                        if self.current_cat == target_cat:
                            self.fetch_convocations_from_firebase(cat_data)
                            self.verifier_et_ouvrir_admin()

                    Clock.schedule_once(actualiser)
            except Exception as e:
                print(f"Erreur suppression : {e}")

        threading.Thread(target=do_delete, daemon=True).start()

    def sauvegarder_tout_match(self, match_id, fields, checkboxes, popup_instance=None):
        if not (nom_equipe := match_id.strip()): return
        date_val = fields["Date"].text.strip()
        try:
            datetime.strptime(date_val, "%d/%m/%Y")
        except ValueError:
            return Popup(title="Erreur", content=Label(text="Format de date invalide !\nUtilisez JJ/MM/AAAA"), size_hint=(0.7, 0.3)).open()

        liste_joueurs = [{"nom": cb.nom_joueur, "prenom": cb.prenom_joueur, "est_manuel": False} for cb in checkboxes if cb.active]
        data = {
            "adversaire": fields["Adversaire"].text.strip(), "date": date_val,
            "heure_rdv": fields["Heure RDV"].text.strip(), "heure_match": fields["Heure Match"].text.strip(),
            "lieu": fields["Lieu"].text.strip(), "entraineurs": fields["Entraineurs"].text.strip(),
            "joueurs_convoques": liste_joueurs, "sondage_actif": True
        }

        def do_save():
            try:
                is_windows = (platform == 'win')
                if requests.put(f"https://fcvv-api.onrender.com/convocations/update/{self.current_cat}/{nom_equipe}", json=data, headers=self.get_user_header(), timeout=10, verify=not is_windows).status_code == 200:
                    Clock.schedule_once(lambda dt: self.fetch_convocations_from_firebase(self._cache_data.get(self.current_cat, {})))
                    if popup_instance: Clock.schedule_once(lambda dt: popup_instance.dismiss())
            except Exception as e:
                print(f"Erreur sauvegarde match : {e}")

        threading.Thread(target=do_save, daemon=True).start()