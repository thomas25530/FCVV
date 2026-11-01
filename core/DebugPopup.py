import builtins
import traceback
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.button import Button


class DebugPopup:
    def __init__(self):
        self.popup = None
        self.label = None
        self.scroll = None
        self.logs = []
        self.original_print = builtins.print

    def installer(self):
        """Capture les print() de l'application."""
        def debug_print(*args, **kwargs):
            # Conserver le print original
            self.original_print(*args, **kwargs)
            try:
                message = " ".join(str(arg) for arg in args)
                self.ajouter_log(message)
            except Exception:
                pass
        builtins.print = debug_print

    def ajouter_log(self, message):
        self.logs.append(str(message))
        # Limiter la mémoire utilisée
        if len(self.logs) > 500:
            self.logs = self.logs[-500:]
        if self.label:
            Clock.schedule_once(lambda dt: self.actualiser(), 0)

    def actualiser(self):
        if not self.label:
            return
        self.label.text = "\n".join(self.logs)
        Clock.schedule_once(lambda dt: self.descendre(), 0.1)

    def descendre(self):
        if self.scroll:
            self.scroll.scroll_y = 0

    def afficher(self):
        if self.popup and self.popup.parent:
            self.popup.dismiss()
        contenu = BoxLayout(orientation="vertical",spacing=dp(5),padding=dp(8))
        self.scroll = ScrollView(do_scroll_x=False )
        self.label = Label(
            text="\n".join(self.logs),
            size_hint_y=None,
            halign="left",
            valign="top",
            font_size=dp(12),
            color=(1, 1, 1, 1)
        )
        self.label.bind( width=lambda instance, value:setattr(instance, "text_size", (value, None)))
        self.label.bind(texture_size=lambda instance, value:setattr(instance, "height", value[1] + dp(20)))
        self.scroll.add_widget(self.label)
        contenu.add_widget(self.scroll)
        boutons = BoxLayout(size_hint_y=None,height=dp(45), spacing=dp(5))
        btn_copier = Button(text="Copier")
        btn_effacer = Button(text="Effacer")
        btn_fermer = Button(text="Fermer")
        btn_copier.bind(on_release=self.copier)
        btn_effacer.bind(on_release=self.effacer)
        boutons.add_widget(btn_copier)
        boutons.add_widget(btn_effacer)
        boutons.add_widget(btn_fermer)
        contenu.add_widget(boutons)
        self.popup = Popup( title="FCVV - DEBUG",content=contenu,size_hint=(0.95, 0.85),auto_dismiss=False)
        btn_fermer.bind(on_release=lambda instance: self.popup.dismiss())
        self.popup.open()
        Clock.schedule_once(lambda dt: self.descendre(), 0.2)

    def effacer(self, instance):
        self.logs.clear()
        self.actualiser()

    def copier(self, instance):
        try:
            from kivy.core.clipboard import Clipboard
            Clipboard.copy("\n".join(self.logs))
            self.ajouter_log("[DEBUG] Logs copiés dans le presse-papiers.")
        except Exception as e:
            self.ajouter_log( f"[DEBUG] Erreur copie : {e!r}")
