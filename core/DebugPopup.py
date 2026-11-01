
import builtins

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
        self.capture_installee = False
        self.rafraichissement = None

    def installer(self):
        if self.capture_installee:
            return

        def debug_print(*args, **kwargs):
            # Conserver le comportement original
            self.original_print(*args, **kwargs)
            try:
                message = " ".join(str(arg) for arg in args)
                self.logs.append(message)
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
        self.scroll = ScrollView( do_scroll_x=False )
        self.label = Label(text="",size_hint_y=None,halign="left",valign="top", font_size=dp(12),color=(1, 1, 1, 1))
        self.label.bind(width=lambda instance, value:setattr(instance, "text_size", (value, None)))
        self.label.bind( texture_size=lambda instance, value:setattr(instance, "height", value[1] + dp(20)))
        self.scroll.add_widget(self.label)
        contenu.add_widget(self.scroll)
        boutons = BoxLayout(size_hint_y=None,height=dp(45),spacing=dp(5))
        btn_copier = Button(text="Copier")
        btn_effacer = Button(text="Effacer")
        btn_fermer = Button(text="Fermer")
        btn_copier.bind(on_release=self.copier)
        btn_effacer.bind(on_release=self.effacer)
        btn_fermer.bind(on_release=lambda instance: self.popup.dismiss())
        boutons.add_widget(btn_copier)
        boutons.add_widget(btn_effacer)
        boutons.add_widget(btn_fermer)
        contenu.add_widget(boutons)
        self.popup = Popup(title="FCVV - DEBUG",content=contenu,size_hint=(0.95, 0.85),auto_dismiss=False)
        self.popup.bind(on_open=self.demarrer_rafraichissement)
        self.popup.bind(on_dismiss=self.arreter_rafraichissement)
        self.popup.open()

    def demarrer_rafraichissement(self, instance):
        self.actualiser()
        if self.rafraichissement:
            self.rafraichissement.cancel()
        self.rafraichissement = Clock.schedule_interval(self.actualiser_periodique,0.5)

    def arreter_rafraichissement(self, instance):
        if self.rafraichissement:
            self.rafraichissement.cancel()
            self.rafraichissement = None
        self.label = None
        self.scroll = None

    def actualiser_periodique(self, dt):
        self.actualiser()

    def actualiser(self, dt=0):
        if not self.label:
            return
        texte = "\n".join(self.logs)
        if self.label.text != texte:
            self.label.text = texte
            self.label.texture_update()
            self.label.height = (self.label.texture_size[1] + dp(20))
            Clock.schedule_once(self.descendre, 0.1)

    def descendre(self, dt=0):
        if self.scroll:
            self.scroll.scroll_y = 0

    def effacer(self, instance):
        self.logs.clear()
        self.actualiser()

    def copier(self, instance):
        try:
            from kivy.core.clipboard import Clipboard
            Clipboard.copy("\n".join(self.logs))
            self.original_print("[DEBUG] Logs copies dans le presse-papiers.")
        except Exception as e:
            self.original_print("[DEBUG] Erreur copie :", repr(e))
