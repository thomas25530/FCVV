
import builtins
import threading
import inspect
import os

from kivy.clock import Clock
from kivy.metrics import dp
from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.button import Button
from datetime import datetime


class DebugPopup:
    def __init__(self):
        self.popup = None
        self.scroll = None
        self.log_container = None
        self.logs = []
        self.lock = threading.RLock()
        self.original_print = builtins.print
        self.capture_installee = False
        self.rafraichissement = None
        self.logs_affiches = 0

    def installer(self):
        if self.capture_installee:
            return
        def debug_print(*args, **kwargs):
            try:
                self.original_print(" ".join(repr(arg) for arg in args))
            except Exception:
                pass
            try:
                frame = inspect.currentframe().f_back
                fichier = os.path.basename(frame.f_code.co_filename)
                ligne = frame.f_lineno
                fonction = frame.f_code.co_name
                message = " ".join(str(arg) for arg in args)
                heure = datetime.now().strftime("%H:%M:%S")
                log = (
                    f"[{heure}] "
                    f"[{fichier}:{ligne}] "
                    f"[{fonction}()] "
                    f"{message}"
                )
                with self.lock:
                    self.logs.append(log)
                    if len(self.logs) > 500:
                        self.logs = self.logs[-500:]
            except Exception:
                pass
        builtins.print = debug_print
        self.capture_installee = True

    def afficher(self):
        if self.popup and self.popup.parent:
            self.popup.dismiss()
        contenu = BoxLayout(orientation="vertical",spacing=dp(5),padding=dp(8))
        self.scroll = ScrollView( do_scroll_x=False, do_scroll_y=True)
        # Conteneur vertical des lignes de debug
        self.log_container = BoxLayout(orientation="vertical",size_hint_y=None, spacing=dp(2))
        self.log_container.bind(minimum_height=self.log_container.setter("height") )
        self.scroll.add_widget(self.log_container)
        contenu.add_widget(self.scroll)
        boutons = BoxLayout(size_hint_y=None, height=dp(45), spacing=dp(5))
        btn_copier = Button(text="Copier")
        btn_effacer = Button(text="Effacer")
        btn_fermer = Button(text="Fermer")
        btn_copier.bind(on_release=self.copier)
        btn_effacer.bind(on_release=self.effacer)
        boutons.add_widget(btn_copier)
        boutons.add_widget(btn_effacer)
        boutons.add_widget(btn_fermer)
        contenu.add_widget(boutons)
        self.popup = Popup(title="FCVV - DEBUG", content=contenu, size_hint=(0.95, 0.85), auto_dismiss=False)
        btn_fermer.bind(on_release=lambda instance: self.popup.dismiss())
        self.popup.bind( on_open=self.demarrer_rafraichissement )
        self.popup.bind(on_dismiss=self.arreter_rafraichissement)
        self.popup.open()

    def demarrer_rafraichissement(self, instance):
        self.logs_affiches = 0
        self.log_container.clear_widgets()
        self.actualiser()
        # Positionner automatiquement en bas à l'ouverture
        Clock.schedule_once(self.descendre, 0.2)
        if self.rafraichissement:
            self.rafraichissement.cancel()
        self.rafraichissement = Clock.schedule_interval(self.actualiser_periodique, 0.5)

    def arreter_rafraichissement(self, instance):
        if self.rafraichissement:
            self.rafraichissement.cancel()
            self.rafraichissement = None
        self.scroll = None
        self.log_container = None

    def actualiser_periodique(self, dt):
        self.actualiser()

    def actualiser(self):
        if not self.log_container:
            return
        # Vérifier si l'utilisateur est déjà en bas
        est_en_bas = self.scroll and self.scroll.scroll_y <= 0.02
        # Récupérer une copie sécurisée des logs
        with self.lock:
            nouveaux_logs = list(self.logs)
        # Si des anciens logs ont été supprimés
        if self.logs_affiches > len(nouveaux_logs):
            self.log_container.clear_widgets()
            self.logs_affiches = 0
        # Ajouter uniquement les nouvelles lignes
        for message in nouveaux_logs[self.logs_affiches:]:
            ligne = Label(text=message,size_hint_y=None,halign="left",valign="middle",font_size=dp(12), color=(1, 1, 1, 1),padding=(dp(3), dp(3)))
            ligne.bind(width=lambda instance, value: setattr(instance, "text_size", (value, None)))
            ligne.bind(texture_size=lambda instance, value: setattr(instance, "height", value[1] + dp(8)))
            self.log_container.add_widget(ligne)
            self.logs_affiches += 1
        # Descendre uniquement si l'utilisateur était déjà en bas
        if est_en_bas and self.scroll:
            Clock.schedule_once(self.descendre, 0.1)

    def descendre(self, dt=0):
        if self.scroll:
            self.scroll.scroll_y = 0

    def effacer(self, instance):
        with self.lock:
            self.logs.clear()
        if self.log_container:
            self.log_container.clear_widgets()
        self.logs_affiches = 0

    def copier(self, instance):
        try:
            from kivy.core.clipboard import Clipboard
            with self.lock:
                texte = "\n".join(self.logs)
            Clipboard.copy(texte)
            self.original_print("[DEBUG] Logs copies dans le presse-papiers.")
        except Exception as e:
            self.original_print("[DEBUG] Erreur copie :", repr(e))
