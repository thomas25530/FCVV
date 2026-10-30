from kivy.app import App
from kivy.clock import Clock
from kivy.graphics import Color, RoundedRectangle
from kivy.metrics import dp
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen
from kivy.uix.scrollview import ScrollView
from kivy.uix.widget import Widget
from kivy.uix.image import Image
from kivy.uix.popup import Popup
from kivy.uix.button import Button
from kivy.utils import platform

API_BASE_URL = "https://fcvv-api.onrender.com"

def get_user_font_size():
    app = App.get_running_app()
    return (
        app.config.getint('User', 'font_size_factor', fallback=18)
        if hasattr(app, 'config')
        else 18
    )

class NotificationCard(ButtonBehavior, BoxLayout):
    def __init__(self, notif, callback=None, debug=False, **kwargs):
        super().__init__(orientation="vertical", padding=dp(12), spacing=dp(8), size_hint_y=None, **kwargs)
        self.notif = notif
        self.callback = callback
        self.debug = debug
        # Couleur + icône selon l'état
        if not notif.get("lue", False):
            bg_color = (1.0, 0.96, 0.90, 1)
            icon_path = "assets/icons/notif_new.png"
        elif not notif.get("traitee", False):
            bg_color = (1.0, 1.0, 0.92, 1)
            icon_path = "assets/icons/notif_read.png"
        else:
            bg_color = (0.95, 0.95, 0.95, 1)
            icon_path = "assets/icons/notif_done.png"
        with self.canvas.before:
            Color(*bg_color)
            self.bg_rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(8)])
        self.bind(pos=lambda inst, pos: setattr(self.bg_rect, "pos", pos),  size=lambda inst, size: setattr(self.bg_rect, "size", size))  
        titre = notif.get("titre", "")
        message = notif.get("message", "")
        date = notif.get("date", "")
        categorie = notif.get("categorie", "")
        # ==========================
        # Entête : icône + titre + bouton supprimer
        # ==========================
        header = BoxLayout(orientation="horizontal",size_hint_y=None,height=dp(32),spacing=dp(8))
        self.icon = Image( source=icon_path,size_hint=(None, None),size=(dp(18), dp(18)),pos_hint={'center_y': 0.5})
        self.title_label = Label( text=f"[b]{titre}[/b]", markup=True,color=(0.1, 0.1, 0.1, 1),halign="left",valign="middle",size_hint=(1, None),height=dp(32))
        header.add_widget(self.icon)
        header.add_widget(self.title_label)
        self.add_widget(header)
        # ==========================
        # Catégorie
        # ==========================
        if categorie:
            self.categorie_label = Label(text=f"[color=555555]{categorie}[/color]",  markup=True,  color=(0.2, 0.2, 0.2, 1), halign="left", valign="middle", size_hint_y=None)
            self.add_widget(self.categorie_label)
        # ==========================
        # Message
        # ==========================
        self.message_label = Label( text=message, color=(0.1, 0.1, 0.1, 1),  halign="left",  valign="top", size_hint_y=None)
        self.add_widget(self.message_label)
        # ==========================
        # Footer : Date + Indication de la page de destination
        # ==========================
        footer_layout = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(20), spacing=dp(4))
        self.date_label = Label(text=date,color=(0.5, 0.5, 0.5, 1), font_size="11sp",halign="left", valign="middle", size_hint_x=0.55,shorten=True, shorten_from="right", max_lines=1 )
        self.date_label.bind( size=lambda instance, value: setattr( instance, "text_size", value ))
        # Détermination du texte de destination avec sous-onglet
        dest_text = self._get_destination_text(notif)
        self.dest_label = Label( text=f"[i]>> {dest_text}[/i]", markup=True,color=(0.3, 0.4, 0.7, 1), font_size="11sp", halign="left", valign="middle",  size_hint_x=0.45, shorten=True,shorten_from="right",  max_lines=1)
        self.dest_label.bind(size=lambda instance, value: setattr( instance, "text_size", value ))
        footer_layout.add_widget(self.date_label)
        footer_layout.add_widget(self.dest_label)
        self.add_widget(footer_layout)
        # ==========================
        # DEBUG
        # ==========================
        if self.debug:
            payload = notif.get("payload") or {}
            debug_text = (
                f"id={notif.get('id')}\n"
                f"source_id={notif.get('source_id')}\n"
                f"android_id={notif.get('android_id')}\n"
                f"ios_identifier={payload.get('ios_identifier')}\n"
                f"type={notif.get('type')}\n"
                f"categorie={notif.get('categorie')}\n"
                f"lue={notif.get('lue')}\n"
                f"traitee={notif.get('traitee')}\n"
                f"payload={payload}"
            )
            self.debug_label = Label(text=debug_text, color=(0.8, 0.1, 0.1, 1), font_size="10sp", halign="left",valign="top",size_hint_y=None)
            self.add_widget(self.debug_label)
        self.bind(width=self._update_height)
        Clock.schedule_once(lambda dt: self._update_height(), 0)

    def _get_destination_text(self, notif):
        """Traduit le type de notification et la catégorie en destination précise avec sous-onglet."""
        notif_type = notif.get("type")
        payload = notif.get("payload") or {}
        cat = payload.get("categorie") or notif.get("categorie")
        nt = (notif_type or "").strip().lower()
        if notif_type in ("vestiaire", "vestiaire_message", "match", "chat", "message", "messages", "nouveau_message", "echange", "evenement", "événement", "event", "creation_evenement", "evenement_creation","validation","convocation",):
            # Déduction exacte du sous-onglet selon ta logique
            if nt == "echange":
                sous_onglet = "Chat"
            elif nt in ("chat", "message", "messages", "nouveau_message"):
                sous_onglet = "Messages"
            elif nt == "validation":
                sous_onglet = "Calendrier"
            else:
                sous_onglet = "Calendrier"
            base_dest = f"Vestiaire ({cat})" if cat else "Vestiaire"
            return f"{base_dest} > {sous_onglet}"
        elif notif_type in ("news", "home", "manual", None):
            return "Accueil"
        else:
            return "Détails"

    def _update_height(self, *args):
        largeur = max(1, self.width - dp(24))
        header_available_width = largeur - dp(18) - dp(8)
        self.title_label.text_size = (max(1, header_available_width), None)
        self.title_label.texture_update()
        self.title_label.height = max(dp(28), self.title_label.texture_size[1])
        if hasattr(self, "categorie_label"):
            self.categorie_label.text_size = (largeur, None)
            self.categorie_label.texture_update()
            self.categorie_label.height = self.categorie_label.texture_size[1]
        self.message_label.text_size = (largeur, None)
        self.message_label.texture_update()
        self.message_label.height = self.message_label.texture_size[1]
        # Ajustement des largeurs du footer (un peu plus de place pour le texte de destination s'il est long)
        footer_w1 = largeur * 0.50
        footer_w2 = largeur * 0.50
        self.date_label.text_size = (footer_w1, None)
        self.date_label.texture_update()
        self.dest_label.text_size = (footer_w2, None)
        self.dest_label.texture_update()
        contenu = max(dp(32), self.title_label.height)
        if hasattr(self, "categorie_label"):
            contenu += self.categorie_label.height + dp(8)
        contenu += self.message_label.height + dp(8)
        contenu += max(self.date_label.height, self.dest_label.height)
        if hasattr(self, "debug_label"):
            self.debug_label.text_size = (largeur, None)
            self.debug_label.texture_update()
            self.debug_label.height = self.debug_label.texture_size[1]
            contenu += self.debug_label.height + dp(8)
        self.height = contenu + dp(24)

    def on_release(self):
        if self.callback:
            self.callback(self.notif)
            
    def supprimer_notification(self, *args):
        app = App.get_running_app()
        app.notification_manager.supprimer_notification(self.notif["id"])
        screen = getattr(self, "notifications_screen", None)
        if screen:
            screen.refresh()
        if hasattr(app.root, "rebuild_menu"):
            app.root.rebuild_menu()

class NotificationsScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.notifications_par_page = 15
        self.nombre_notifications_affichees = 15
        self.KIVY_BLUE = (30 / 255, 58 / 255, 138 / 255, 1)
        self.YELLOW = (247 / 255, 236 / 255, 63 / 255, 1)
        self.main_layout = BoxLayout(orientation="vertical",spacing=dp(8), padding=[dp(15), dp(10), dp(15), dp(10)] )
        self.main_layout.add_widget(self.SectionTitle("CENTRE DE NOTIFICATIONS") )
        self.btn_clear = Button( text="Tout vider", size_hint_y=None,height=dp(42),background_normal="",background_color=(0.85, 0.2, 0.2, 1))
        self.btn_clear.bind(on_release=self.vider_notifications)
        self.main_layout.add_widget(self.btn_clear)
        self.btn_read_all = Button(text="Marquer comme lues",size_hint_y=None, height=dp(42),background_normal="",background_color=(0.2, 0.5, 0.3, 1))
        self.btn_read_all.bind(on_release=self.marquer_tout_comme_lu)
        self.main_layout.add_widget(self.btn_read_all)
        self.scroll = ScrollView(do_scroll_x=False,bar_width=0)
        self.content = BoxLayout( orientation="vertical", spacing=dp(10), padding=[dp(2), dp(5), dp(2), dp(10)],size_hint_y=None)
        self.content.bind( minimum_height=self.content.setter("height") )
        self.scroll.add_widget(self.content)
        self.main_layout.add_widget(self.scroll)
        self.add_widget(self.main_layout)

    def SectionTitle(self, text, **kwargs):
        fs = get_user_font_size()
        params = {"text": f"[b]{text}[/b]","markup": True, "color": self.YELLOW,"size_hint_y": None, "height": dp(45),"font_size": f"{fs + 4}sp","halign": "left","valign": "middle", }
        params.update(kwargs)
        return Label(**params)
    
    def on_pre_enter(self):
        self.nombre_notifications_affichees = 15
        self.refresh()
        
    def charger_plus(self, *args):
        self.nombre_notifications_affichees += self.notifications_par_page
        self.refresh()

    def marquer_tout_comme_lu(self, *args):
        app = App.get_running_app()
        manager = app.notification_manager
        # Marquer toutes les notifications comme lues sans les supprimer.
        manager.marquer_tout_comme_lu()
        # Remettre le badge serveur à zéro et actualiser le badge iOS.
        if platform == "ios":
            if hasattr(app, "remettre_zero_badge_depuis_api"):
                app.remettre_zero_badge_depuis_api()
            else:
                print("[BADGE] Methode remettre_zero_badge_depuis_api absente")
        # Actualiser le menu et les cartes.
        if hasattr(app.root, "rebuild_menu"):
            app.root.rebuild_menu()
        self.refresh()
    
    def vider_notifications(self, *args):
        content = BoxLayout(orientation="vertical",spacing=dp(10),padding=dp(10) )
        message = Label(text="Supprimer toutes les notifications ?",halign="center",valign="middle")
        message.bind(size=lambda instance, size: setattr( instance, "text_size", (size[0] - dp(10), None)))
        content.add_widget(message)
        boutons = BoxLayout(size_hint_y=None, height=dp(45), spacing=dp(10) )
        popup = Popup(title="Confirmation",content=content,size_hint=(0.85, 0.4),auto_dismiss=False )
        btn_annuler = Button(text="Annuler")
        btn_ok = Button(text="Supprimer")
        boutons.add_widget(btn_annuler)
        boutons.add_widget(btn_ok)
        content.add_widget(boutons)
        btn_annuler.bind(on_release=popup.dismiss)
        def afficher_message_erreur(texte):
            content.clear_widgets()
            message = Label(text=texte,halign="center", valign="middle",size_hint_y=1)
            message.bind(size=lambda instance, size: setattr( instance, "text_size", (size[0] - dp(12), size[1])))
            content.add_widget(message)
            boutons.clear_widgets()
            btn_annuler.disabled = False
            btn_ok.disabled = False
            btn_ok.text = "Réessayer"
            boutons.add_widget(btn_annuler)
            boutons.add_widget(btn_ok)
            content.add_widget(boutons)
    
        def confirmer(*_):
            app = App.get_running_app()
            api_url = API_BASE_URL
            nom_parent = (app.config.get("User", "nom_parent", fallback="") or app.config.get("User", "nom", fallback="")) if hasattr(app, "config") else ""
            if not api_url or not nom_parent:
                print("[NOTIFICATIONS] URL ou utilisateur manquant.")
                afficher_message_erreur("Utilisateur introuvable.")
                return
            manager = getattr(app, "notification_manager", None)
            if manager is None:
                print("[NOTIFICATIONS] Gestionnaire local introuvable.")
                afficher_message_erreur("Erreur de stockage local.")
                return
            btn_ok.disabled = True
            btn_annuler.disabled = True
            btn_ok.text = "Suppression..."
            def appeler_api():
                import requests
                try:
                    response = requests.delete(f"{api_url}/notifications/vider",headers={"nom_parent": nom_parent},timeout=20, verify=(platform != "win"))
                    response.raise_for_status()
                    resultat = response.json()
                    if not resultat.get("success"):
                        raise RuntimeError("Le serveur n'a pas confirmé le vidage." )
                    def terminer(_dt):
                        try:
                            with app._notifications_lock:
                                app._notifications_sync_generation += 1
                                vidage_local_reussi = ( manager.vider_notifications())
                            if vidage_local_reussi is not True:
                                raise RuntimeError( "Échec de la sauvegarde locale.")
                            popup.dismiss()
                            if ( app.root and hasattr(app.root, "rebuild_menu")):
                                app.root.rebuild_menu()
                            if (platform == "ios" and hasattr(app,"remettre_zero_badge_depuis_api")):
                                app.remettre_zero_badge_depuis_api()
                            self.nombre_notifications_affichees = 15
                            self.refresh()
                        except Exception as e:
                            print(f"[NOTIFICATIONS] Erreur locale : {e}")
                            afficher_message_erreur("Vidage local impossible.\nRéessaie.")
                    Clock.schedule_once(terminer, 0)
                except Exception as e:
                    print(f"[NOTIFICATIONS] echec du vidage serveur : {e}")
                    def afficher_erreur(_dt):
                        afficher_message_erreur("Connexion impossible.\nRéessaie." )
                    Clock.schedule_once(afficher_erreur, 0)
            import threading
            threading.Thread(target=appeler_api,daemon=True).start()
        btn_ok.bind(on_release=confirmer)
        popup.open()

    def refresh(self):
        self.content.clear_widgets()
        app = App.get_running_app()
        notifications = app.notification_manager.notifications
        if not notifications:
            self.content.add_widget( Label( text="Aucune notification", size_hint_y=None, height=dp(60) ))
            return
        # Afficher uniquement les notifications autorisées par la pagination.
        notifications_visibles = notifications[
            :self.nombre_notifications_affichees
        ]
        for notif in notifications_visibles:
            card = NotificationCard(notif=notif,callback=self.ouvrir_notification,debug=True )
            card.notifications_screen = self
            self.content.add_widget(card)
        # Ajouter le bouton seulement s'il reste des notifications.
        if len(notifications) > len(notifications_visibles):
            restantes = len(notifications) - len(notifications_visibles)
            btn_charger = Button(text=f"Charger plus ({restantes} restantes)", size_hint=(0.85, None), height=dp(55), pos_hint={'center_x': 0.5}, background_color=(0.2, 0.2, 0.2, 1),halign='center', valign='middle')
            btn_charger.bind(on_release=self.charger_plus)
            self.content.add_widget(btn_charger)
        self.content.add_widget(Widget(size_hint_y=None, height=dp(50)))
    
    def rediriger_notification(self, notif):
        """Redirige via les méthodes centrales de l'application."""
        app = App.get_running_app()
        notif_type = notif.get("type")
        payload = notif.get("payload") or {}
        # Compatibilité avec les anciennes notifications
        categorie = (payload.get("categorie") or notif.get("categorie") )
        match_id = (payload.get("match_id") or notif.get("match_id"))
        try:
            if notif_type in ("vestiaire","vestiaire_message", "match","chat", "message","messages", "nouveau_message", "echange", "evenement", "événement","event","creation_evenement", "evenement_creation","validation","convocation",):
                if not categorie:
                    print( "[NOTIFICATION] Categorie absente dans la notification." )
                    return False
                # Réutilise la logique existante du fichier principal.
                app.executer_redirection_vestiaire( categorie,match_id,notif_type )
            elif notif_type in ("news", "home", "manual", None):
                app.executer_redirection_home()
            else:
                print(f"[NOTIFICATION] Type inconnu : {notif_type}")
                return False
            return True
        except Exception as e:
            print(f"[NOTIFICATION] Erreur redirection : {e}")
            return False
    
    def ouvrir_notification(self, notif):
        app = App.get_running_app()
        manager = app.notification_manager
        # Mémoriser l'état avant de modifier la notification.
        etait_non_lue = not notif.get("lue", False)
        # Conserver la redirection existante.
        succes = manager.rediriger_notification(notif)
        if not succes:
            return
        # 1. Annuler la notification de la barre d'état (Android / iOS via le manager)
        print(
            f"[NOTIFICATION OUVERTURE] "
            f"id={notif.get('id')!r}, "
            f"android_id={notif.get('android_id')!r}, "
            f"source_id={notif.get('source_id')!r}, "
            f"cles={list(notif.keys())}"
        )
        manager.annuler_notification_barre(notif)
        # Marquer la notification comme traitée localement.
        manager.marquer_comme_traitee(notif["id"])
        # Décrémenter le badge serveur uniquement si elle était non lue.
        if etait_non_lue and platform == "ios" and notif.get("categorie") != "TournoiVercel" :
            app.decrementer_badge_depuis_api()
        if hasattr(app.root, "rebuild_menu"):
            app.root.rebuild_menu()
        self.refresh()
