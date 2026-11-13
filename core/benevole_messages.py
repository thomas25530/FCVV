# -*- coding: utf-8 -*-

import os
import json
import hashlib
import threading
import requests

from datetime import datetime

from kivy.app import App
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.utils import platform

from kivy.graphics import Color
from kivy.graphics import RoundedRectangle

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.widget import Widget

# ============================================================
# BULLE MESSAGE (AVEC BOUTON "X" INTÉGRÉ)
# ============================================================
class BenevoleMessageBubble(BoxLayout):
    def __init__(self, msg_data, is_me=False, delete_callback=None, **kwargs):
        super().__init__(
            orientation="vertical",
            size_hint_y=None,
            padding=[
                dp(10) if is_me else dp(50),
                0,
                dp(50) if is_me else dp(10),
                0,
            ],
            **kwargs,
        )
        self.msg_data = msg_data
        self.delete_callback = delete_callback
        self.bind(minimum_height=self.setter("height"))
        bg = (
            (0.10, 0.55, 1.0, 1.0)
            if is_me
            else (0.22, 0.22, 0.22, 1)
        )
        self.wrapper = BoxLayout(orientation="horizontal", size_hint=(1, None), spacing=dp(5))
        self.wrapper.bind(height=self.setter("height"))
        self.bubble = BoxLayout(orientation="vertical", spacing=dp(4), padding=[dp(12), dp(8)], size_hint=(None, None))
        with self.bubble.canvas.before:
            Color(*bg)
            self.rect = RoundedRectangle(
                pos=self.bubble.pos,
                size=self.bubble.size,
                radius=[dp(16)]
            )
        self.bubble.bind(pos=lambda *_: setattr(self.rect, "pos", self.bubble.pos))
        self.bubble.bind(size=lambda *_: setattr(self.rect, "size", self.bubble.size))
        # --- EN-TÊTE DE LA BULLE (Prénom + Bouton X optionnel si c'est notre message) ---
        header_layout = BoxLayout(orientation="horizontal", size_hint=(None, None), spacing=dp(10))
        prenom = msg_data.get("prenom", "")
        self.author = Label(
            text=f"[b]{prenom}[/b]",
            markup=True,
            size_hint=(None, None),
            color=(1, 0.85, 0.4, 1),
        )
        header_layout.add_widget(self.author)
        if is_me:
            self.delete_btn = Button(
                text="X",
                size_hint=(None, None),
                size=(dp(24), dp(24)),
                background_normal="",
                background_color=(0.8, 0.2, 0.2, 1),
                color=(1, 1, 1, 1),
                font_size=dp(12)
            )
            self.delete_btn.bind(on_release=self.trigger_delete)
            header_layout.add_widget(self.delete_btn)
        self.bubble.add_widget(header_layout)
        # ------------------------------------------------------------------------------
        self.content = Label(
            text=msg_data.get("contenu", ""),
            size_hint=(None, None),
            halign="left",
            valign="top",
            text_size=(dp(250), None),
            color=(1, 1, 1, 1),
        )
        self.bubble.add_widget(self.content)
        heure = ""
        try:
            dt = datetime.fromisoformat(msg_data["timestamp"].replace("Z", "+00:00"))
            heure = dt.astimezone().strftime("%H:%M")
        except Exception:
            pass
        self.timestamp = Label(text=f"[color=CCCCCC]{heure}[/color]", markup=True, size_hint=(None, None))
        self.bubble.add_widget(self.timestamp)
        # La bulle est maintenant ajoutée directement dans le wrapper sans bouton à côté
        self.wrapper.add_widget(self.bubble)
        Clock.schedule_once(self.finalize)
        self.add_widget(self.wrapper)

    def finalize(self, *_):
        self.author.texture_update()
        self.content.texture_update()
        self.timestamp.texture_update()
        # Ajustement des tailles des éléments de l'en-tête
        author_w = self.author.texture_size[0]
        self.author.size = (author_w, max(self.author.texture_size[1], dp(24)))
        header_w = author_w
        header_h = self.author.height
        if hasattr(self, "delete_btn"):
            self.delete_btn.size = (dp(24), dp(24))
            header_w += dp(10) + self.delete_btn.width
            header_h = max(header_h, self.delete_btn.height)
        header_layout = self.author.parent
        header_layout.size = (header_w, header_h)
        self.content.size = self.content.texture_size
        self.timestamp.size = self.timestamp.texture_size
        width = max(header_w, self.content.width, self.timestamp.width)
        height = (
            header_h
            + self.content.height
            + self.timestamp.height
            + dp(32)
        )
        self.bubble.size = (width + dp(40), height)
        self.wrapper.height = height

    def trigger_delete(self, *_):
        if self.delete_callback:
            self.delete_callback(self.msg_data)

# ============================================================
# VUE PRINCIPALE
# ============================================================
class BenevoleMessagesView(BoxLayout):
    API_URL = (
        "https://fcvv-api.onrender.com/"
        "benevoles/messages"
    )
    def __init__(self, **kwargs):
        super().__init__(orientation="vertical", spacing=0, size_hint=(1, 1), **kwargs)
        self.cached_messages = []
        self.last_hash = None
        app = App.get_running_app()
        self.prenom = app.config.get(
            "Benevoles",
            "prenom_chat",
            fallback=""
        ).strip()
        if not self.prenom:
            self.build_prenom_view()
        else:
            self.build_chat_view()

    # ===========================================================
    # ETAPE 1 : SAISIE DU PRENOM
    # ============================================================
    def build_prenom_view(self):
        self.clear_widgets()
        
        # Conteneur principal pour tout aligner en haut
        main_layout = BoxLayout(orientation="vertical", size_hint=(1, 1))
        
        card = BoxLayout(orientation="vertical", spacing=dp(12), size_hint_y=None, height=dp(200), padding=dp(15))
        
        # Label ajusté pour tenir sur 2 lignes et centré
        lbl = Label(
            text="Entrez votre prénom pour discuter avec les bénévoles",
            size_hint_y=None,
            height=dp(70),
            halign="center",
            valign="middle"
        )
        lbl.bind(size=lambda *_: setattr(lbl, 'text_size', lbl.size))
        card.add_widget(lbl)

        self.prenom_input = TextInput(hint_text="Prénom", multiline=False, size_hint_y=None, height=dp(45))
        self.prenom_input.bind(on_text_validate=lambda *_: self.save_prenom())
        card.add_widget(self.prenom_input)

        btn = Button(text="Continuer", size_hint_y=None, height=dp(45))
        btn.bind(on_release=self.save_prenom)
        card.add_widget(btn)

        main_layout.add_widget(card)
        # Espace vide en dessous pour repousser la carte tout en haut
        main_layout.add_widget(Widget()) 
        
        self.add_widget(main_layout)

    def save_prenom(self, *_):
        prenom = self.prenom_input.text.strip().title()
        if not prenom or len(prenom) < 2 or len(prenom) > 30:
            print("[DEBUG] Prenom invalide (longueur)")
            return
        app = App.get_running_app()
        if not app.config.has_section("Benevoles"):
            app.config.add_section("Benevoles")
        app.config.set("Benevoles", "prenom_chat", prenom)
        app.config.write()
        self.prenom = prenom
        # ======================================================
        # ABONNEMENT FCM : Topic d'exclusion
        # ======================================================
        try:
            if hasattr(app, "notifier") and app.notifier and platform in ("android", "ios"):
                prenom_clean = prenom.strip().replace(" ", "_").lower()
                topic_exclusion = f"Benevole_exclure_{prenom_clean}"
                print(f"[FCM BENEVOLES] Abonnement au topic d'exclusion : {topic_exclusion}")
                app.notifier.subscribe_to_topic(topic_exclusion)
        except Exception as e:
            print(f"[FCM BENEVOLES] Erreur abonnements : {e}")
        # ======================================================
        print(f"[DEBUG] Prenom enregistre avec succes, chargement du chat")
        self.build_chat_view()

    # ============================================================
    # CHAT
    # ============================================================
    def build_chat_view(self):
        self.clear_widgets()
        self.size_hint = (1, 1)
        # 1. HEADER FIXE (en haut de la vue des messages)
        header = Label(
            text=(
                f"[b]Bonjour {self.prenom}[/b]\n"
                "[color=AAAAAA]Discutez avec les autres bénévoles.[/color]"
            ),
            markup=True,
            size_hint=(1, None),
            height=dp(55),
            halign="center",
            valign="middle"
        )
        header.bind(size=lambda *_: setattr(header, 'text_size', header.size))
        # 2. SCROLLVIEW DES MESSAGES
        self.scroll = ScrollView(do_scroll_x=False, size_hint=(1, 1))
        self.msg_container = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(8), padding=[dp(10), dp(10)])
        self.msg_container.bind(minimum_height=self.msg_container.setter("height"))
        self.scroll.add_widget(self.msg_container)
        # 3. CONTENEUR DU BAS : Barre de saisie + Espace de sécurité Android en dessous
        bottom_container = BoxLayout(orientation="vertical", size_hint=(1, None), height=dp(55) + dp(50), spacing=dp(0), padding=[dp(5), dp(5), dp(5), dp(0)])
        self.input_box = BoxLayout(orientation="horizontal", size_hint=(1, None), height=dp(55), spacing=dp(5))
        self.input_field = TextInput(hint_text="Votre message...", multiline=False, size_hint_x=0.75)
        self.input_field.bind(on_text_validate=lambda *_: self.send_message())
        send_btn = Button(text="Envoyer", size_hint_x=0.25)
        send_btn.bind(on_release=self.send_message)
        self.input_box.add_widget(self.input_field)
        self.input_box.add_widget(send_btn)
        bottom_container.add_widget(self.input_box)
        bottom_container.add_widget(Widget(size_hint_y=None, height=dp(50)))
        
        self.add_widget(header)
        self.add_widget(self.scroll)
        self.add_widget(bottom_container)
        self.load_cache()
        self.fetch_messages()
        if hasattr(self, "refresh_event") and self.refresh_event:
            self.refresh_event.cancel()
        self.refresh_event = Clock.schedule_interval(self.fetch_messages, 5)

    # ============================================================
    # AFFICHAGE
    # ============================================================
    def render_messages(self):
        self.msg_container.clear_widgets()
        if not self.cached_messages:
            self.msg_container.add_widget(
                Label(
                    text=(
                        "Aucun message.\n"
                        "Soyez le premier à écrire."
                    ),
                    size_hint_y=None,
                    height=dp(120),
                    halign="center",
                    color=(0.7, 0.7, 0.7, 1)
                )
            )
            return
        for msg in self.cached_messages:
            is_me = (
                msg.get("prenom", "").strip().lower()
                == self.prenom.lower()
            )
            bubble = BenevoleMessageBubble(msg, is_me=is_me, delete_callback=self.delete_message if is_me else None)
            self.msg_container.add_widget(bubble)
        Clock.schedule_once(self.fix_initial_scroll, 0.1)

    def fix_initial_scroll(self, *_):
        try:
            self.msg_container.do_layout()
            self.do_layout()
            self.scroll.scroll_y = 1  
        except Exception as e:
            print(f"[DEBUG] Erreur fix_initial_scroll : {e}")

    def force_layout_and_scroll(self, *_):
        try:
            self.msg_container.do_layout()
            self.do_layout()
        except Exception as e:
            print(f"[DEBUG] Erreur force_layout : {e}")

    def scroll_to_bottom(self, *_):
        try:
            self.msg_container.do_layout()
            self.scroll.scroll_y = 0  
            self.do_layout()
        except Exception as e:
            print(f"[DEBUG] Erreur scroll_to_bottom : {e}")

    # ============================================================
    # RECEPTION
    # ============================================================
    def fetch_messages(self, *_):
        threading.Thread(target=self._fetch_messages_thread, daemon=True).start()

    def _fetch_messages_thread(self):
        try:
            response = requests.get(self.API_URL, timeout=15, verify=(platform != "win"))
            if response.status_code != 200:
                print(f"[DEBUG] Erreur HTTP : {response.text}")
                return
            data = response.json()
            if not isinstance(data, list):
                print(f"[DEBUG] Format de donnees inattendu (pas une liste) : {type(data)}")
                return
            current_hash = hashlib.md5(str(data).encode()).hexdigest()
            if current_hash == self.last_hash and not getattr(self, "force_refresh", False):
                return
            self.last_hash = current_hash
            self.force_refresh = False
            self.cached_messages = data
            self.save_cache()
            Clock.schedule_once(lambda dt: self.render_messages())
        except Exception as e:
            print(f"[MESSAGES_BENEVOLES] Erreur recuperation : {e}")

    # ============================================================
    # ENVOI
    # ============================================================
    def send_message(self, *_):
        texte = self.input_field.text.strip()
        if not texte:
            return
        threading.Thread(
            target=self._send_message_thread,
            args=(self.prenom, texte), daemon=True
        ).start()
        self.input_field.text = ""

    def _send_message_thread(self, prenom, contenu):
        try:
            response = requests.post(
                self.API_URL,
                json={
                    "prenom": prenom,
                    "contenu": contenu,
                },
                timeout=15,
                verify=(platform != "win")
            )
            if response.status_code == 200:
                self.force_refresh = True
                Clock.schedule_once(lambda dt: self.fetch_messages())
            else:
                print(f"[MESSAGES_BENEVOLES] Erreur API : {response.status_code} {response.text}")
        except Exception as e:
            print(f"[MESSAGES_BENEVOLES] Erreur envoi : {e}")

    # ============================================================
    # SUPPRESSION
    # ============================================================
    def delete_message(self, msg_data):
        threading.Thread(target=self._delete_message_thread, args=(msg_data,), daemon=True).start()

    def _delete_message_thread(self, msg_data):
        try:
            msg_id = msg_data.get("id")
            if not msg_id:
                return
            delete_url = f"{self.API_URL}/{msg_id}"
            headers = {"prenom": self.prenom}
            response = requests.delete(delete_url, headers=headers, timeout=10, verify=(platform != "win"))
            if response.status_code in (200, 204):
                self.force_refresh = True
                Clock.schedule_once(lambda dt: self.fetch_messages())
        except Exception as e:
            print(f"[MESSAGES_BENEVOLES] Erreur suppression : {e}")

    # ============================================================
    # CACHE
    # ============================================================
    def get_cache_path(self):
        app = App.get_running_app()
        base = app.user_data_dir if hasattr(app, "user_data_dir") else "."
        return os.path.join(base, "benevole_messages.json")

    def save_cache(self):
        try:
            with open(self.get_cache_path(), "w", encoding="utf-8") as f:
                json.dump(self.cached_messages[-200:], f, ensure_ascii=False)
        except Exception as e:
            print(f"[MESSAGES_BENEVOLES] Erreur cache : {e}")

    def load_cache(self):
        path = self.get_cache_path()
        if not os.path.exists(path):
            print("[DEBUG] Aucun fichier cache trouve.")
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                self.cached_messages = json.load(f)
                self.last_hash = hashlib.md5(str(self.cached_messages).encode()).hexdigest()
            self.render_messages()
        except Exception as e:
            print(f"[MESSAGES_BENEVOLES] Erreur lecture cache : {e}")

    # ============================================================
    # DESTRUCTION
    # ============================================================
    def on_parent(self, *_):
        if not self.parent and hasattr(self, "refresh_event") and self.refresh_event:
            self.refresh_event.cancel()
