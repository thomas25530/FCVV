# core/NotificationManager.py
from kivy.utils import platform
from kivy.clock import Clock
from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.metrics import dp
from kivy.app import App

def declencher_alerte_depuis_natif(
    titre,
    corps,
    match_id=None
):

    try:

        app = App.get_running_app()

        if not app:
            print("[PUSH] Application Kivy non disponible")
            return

        if hasattr(app, "afficher_alerte_push"):

            print(
                "[PUSH] Transmission vers MyApp.afficher_alerte_push()"
            )

            Clock.schedule_once(
                lambda dt: app.afficher_alerte_push(
                    titre,
                    corps
                ),
                0
            )

        elif app.root and hasattr(
            app.root,
            "afficher_popup_flottante"
        ):

            print(
                "[PUSH] Transmission vers RootLayout"
            )

            Clock.schedule_once(
                lambda dt: app.root.afficher_popup_flottante(
                    titre,
                    corps
                ),
                0
            )

        else:

            print(
                "[PUSH] Aucun gestionnaire d'alerte disponible"
            )

    except Exception as e:

        print(
            f"[PUSH ERROR] {e}"
        )

class NotificationManager:
    def init_service(self): raise NotImplementedError
    def subscribe_to_topic(self, topic): raise NotImplementedError
    def unsubscribe_from_topic(self, topic): raise NotImplementedError
    def request_permissions(self): raise NotImplementedError

if platform == "android":

    from jnius import PythonJavaClass, java_method


    class FcmPythonCallback(PythonJavaClass):

        __javacontext__ = "app"

        __javainterfaces__ = [
            "org/fcvv/notifications/FcmCallback"
        ]

        def __init__(self, manager):
            super().__init__()
            self.manager = manager

        @java_method(
            "(Ljava/lang/String;Ljava/lang/String;Ljava/lang/String;)V"
        )
        def onFcmMessage(self, title, body, match_id):

            print(
                f"[FCM PYTHON] Message recu : "
                f"{title} / {body} / {match_id}"
            )

            # IMPORTANT :
            # on ne touche pas directement à l'UI depuis
            # le thread FCM.
            Clock.schedule_once(
                lambda dt: self.manager._handle_foreground_message(
                    title,
                    body,
                    match_id
                ),
                0
            )

class AndroidNotificationManager(NotificationManager):
    def __init__(self):
        from jnius import autoclass
        self.autoclass = autoclass
        self.PythonActivity = autoclass('org.kivy.android.PythonActivity')
        self.FirebaseApp = autoclass('com.google.firebase.FirebaseApp')
        self.FirebaseMessaging = autoclass('com.google.firebase.messaging.FirebaseMessaging')
        self.NotificationChannel = autoclass('android.app.NotificationChannel')
        self.Context = autoclass('android.content.Context')
        self.activity = self.PythonActivity.mActivity
        self.context = self.activity.getApplicationContext()
        self.token_task = None
        # --------------------------------------------------
        # Callback FCM Java -> Python
        # --------------------------------------------------
    
        self.fcm_callback = None
        self.FcmService = None
    
        try:
    
            self.FcmService = self.autoclass(
                "org.fcvv.notifications.FCVVFirebaseMessagingService"
            )
    
            self.fcm_callback = FcmPythonCallback(self)
    
            self.FcmService.setCallback(
                self.fcm_callback
            )
    
            print(
                "[FCM] Callback Python enregistré"
            )
    
        except Exception as e:
    
            print(
                f"[FCM ERROR] Callback FCM : {e}"
            )
    
    def _handle_foreground_message(
        self,
        title,
        body,
        match_id=None
    ):
    
        print(
            f"[FCM FOREGROUND] "
            f"{title} - {body} - {match_id}"
        )
    
        try:
    
            declencher_alerte_depuis_natif(
                title,
                body,
                match_id
            )
    
        except Exception as e:
    
            print(
                f"[FCM FOREGROUND ERROR] {e}"
            )

    def init_service(self):
        try:
            # 1. NOUVEL ID : indispensable pour écraser l'ancien canal restreint
            channel_id = "fcvv_high_priority_v2"
            # 2. IMPORTANCE HAUTE (4 = IMPORTANCE_HIGH -> active le pop-up / heads-up)
            importance = 4 
            channel = self.NotificationChannel(
                channel_id,
                "FCVV Notifications Importantes",
                importance
            )
            # Options supplémentaires pour forcer la visibilité
            channel.enableVibration(True)
            channel.enableLights(True)
            channel.setDescription("Notifications urgentes avec pop-up d'affichage")
            manager = self.activity.getSystemService(
                self.Context.NOTIFICATION_SERVICE
            )
            manager.createNotificationChannel(channel)
            print("[FCM] Canal Haute Priorite (Pop-up) cree avec succes.")

            # Firebase
            apps = self.FirebaseApp.getApps(self.context)
            if apps.isEmpty():
                FirebaseOptionsBuilder = self.autoclass(
                    'com.google.firebase.FirebaseOptions$Builder'
                )
                builder = FirebaseOptionsBuilder()
                builder.setApiKey("AIzaSyDTxB5sz0Y1Olg4qXoreO5AviBVbUhHIhw")
                builder.setApplicationId(
                    "1:512335597045:android:9819dbed0c70a09d3be4bc"
                )
                builder.setProjectId("fcvv-app")
                self.FirebaseApp.initializeApp(
                    self.context,
                    builder.build()
                )
            # Récupération du token FCM
            messaging = self.FirebaseMessaging.getInstance()
            self.token_task = messaging.getToken()
            print("[FCM] Demande de token envoyee")

            # --- AJOUT : Vérification de l'intent d'ouverture si l'app a été ouverte via une notification ---
            self._check_intent_for_notification()

        except Exception as e:
            print(f"[FCM ERROR] init_service : {e}")

    def _check_intent_for_notification(self):
        """Récupère les données si l'utilisateur a ouvert l'app en cliquant sur une notification"""
        try:
            intent = self.activity.getIntent()
            extras = intent.getExtras()
            if extras:
                title = extras.getString("gcm.notification.title") or extras.getString("title")
                body = extras.getString("gcm.notification.body") or extras.getString("body")
                match_id = extras.getString("match_id")
                if title and body:
                    print(f"[FCM Intent] Notification detectee au lancement : {title}")
                    Clock.schedule_once(lambda dt: declencher_alerte_depuis_natif(title, body, match_id), 1.0)
        except Exception as e:
            print(f"[FCM Intent Error] {e}")

    def subscribe_to_topic(self, topic):
        try:
            if self.token_task is not None:
                if self.token_task.isComplete():
                    if self.token_task.isSuccessful():
                        token = self.token_task.getResult()
                        print(f"[FCM] Token OK : {str(token)[:25]}...")
                    else:
                        print("[FCM WARNING] Token indisponible")
                else:
                    print("[FCM] Token en cours de creation...")
            print(f"[FCM] Demande d'abonnement au topic : {topic}")
            task = self.FirebaseMessaging.getInstance().subscribeToTopic(topic)
            print(f"[FCM] Requete envoyee pour : {topic}")
        except Exception as e:
            print(f"[FCM ERROR] subscribe_to_topic : {e}")

    def unsubscribe_from_topic(self, topic):
        try:
            print(f"[FCM] Desabonnement : {topic}")
            self.FirebaseMessaging.getInstance().unsubscribeFromTopic(topic)
        except Exception as e:
            print(f"[FCM ERROR] unsubscribe : {e}")

    def request_permissions(self):
        from android.permissions import (
            request_permissions,
            Permission
        )
        request_permissions([
            Permission.POST_NOTIFICATIONS
        ])

class IOSNotificationManager(NotificationManager):
    def __init__(self):
        from pyobjus import autoclass
        self.FIRApp = None
        self.FIRMessaging = None
        self.UNCenter = None
        self.UIApplication = None
        self.pending_topics = set()
        self.waiting_for_token = False
        self.token_wait_count = 0
        self.max_token_wait = 60

        try:
            print("[FCM DEBUG] Chargement Firebase...")
            self.FIRApp = autoclass("FIRApp")
            
            # Firebase est deja configure dans main.m
            if not self.FIRApp.defaultApp():
                print("[FCM iOS] FIRApp absent, tentative configure")
                self.FIRApp.configure()

            print("[FCM DEBUG] Chargement FIRMessaging...")
            FIRMessagingClass = autoclass("FIRMessaging")
            
            # Recuperation de l'instance FIRMessaging
            try:
                self.FIRMessaging = FIRMessagingClass.messaging()
            except Exception:
                self.FIRMessaging = FIRMessagingClass.sharedInstance()

            self.UNCenter = autoclass("UNUserNotificationCenter").currentNotificationCenter()
            self.UIApplication = autoclass("UIApplication")
            
            print("[FCM iOS] Initialisation Firebase OK")
        except Exception as e:
            print(f"[FCM iOS Init Error] {e}")

    def init_service(self):
        token = self._get_token()
        if token:
            print(f"[FCM iOS] Token deja disponible : {str(token)[:12]}...")
        else:
            print("[FCM iOS] En attente du token FCM (APNS necessaire)...")

    def _get_token(self):
        """Recuperation synchrone et securisee du token FCM"""
        if not self.FIRMessaging:
            return None

        for name in ("FCMToken", "fcmToken"):
            try:
                token = getattr(self.FIRMessaging, name)
                if callable(token):
                    token = token()
                if token:
                    # Conversion en string Python au cas ou Pyobjus renvoie un NSString
                    return str(token)
            except Exception:
                pass
        return None

    def _start_waiting_for_token(self):
        if self.waiting_for_token:
            return
        self.waiting_for_token = True
        self.token_wait_count = 0
        print("[FCM iOS] Surveillance token demarree")
        Clock.schedule_interval(self._check_token, 1.0)

    def _check_token(self, dt):
        self.token_wait_count += 1
        token = self._get_token()
        
        if not token:
            if self.token_wait_count >= self.max_token_wait:
                print("[FCM iOS] Timeout attente token FCM")
                self.waiting_for_token = False
                return False  # Stoppe le Clock
            return True       # Continue d'attendre

        print(f"[FCM iOS] Token obtenu : {str(token)[:12]}...")
        self.waiting_for_token = False
        
        # Inscription aux topics en attente
        for topic in list(self.pending_topics):
            try:
                print(f"[FCM iOS] Abonnement automatique : {topic}")
                self.FIRMessaging.subscribeToTopic_(topic)
            except Exception as e:
                print(f"[FCM iOS] Erreur topic {topic}: {e}")
                
        self.pending_topics.clear()
        return False  # Stoppe le Clock

    def apns_token_received(self):
        print("[FCM iOS] APNS recu, demarrage attente FCM")
        self._start_waiting_for_token()

    def subscribe_to_topic(self, topic):
        token = self._get_token()
        if not token:
            print(f"[FCM iOS] Token absent -> attente topic : {topic}")
            self.pending_topics.add(topic)
            self._start_waiting_for_token()
            return False

        try:
            print(f"[FCM iOS] Abonnement topic : {topic}")
            self.FIRMessaging.subscribeToTopic_(topic)
            return True
        except Exception as e:
            print(f"[FCM iOS] Erreur abonnement : {e}")
            return False

    def unsubscribe_from_topic(self, topic):
        self.pending_topics.discard(topic)
        try:
            self.FIRMessaging.unsubscribeFromTopic_(topic)
        except Exception as e:
            print(f"[FCM iOS] Erreur desabonnement : {e}")

    def request_permissions(self):
        """
        Demande de permission et reenregistrement APNs securise pour Pyobjus.
        """
        if not self.UNCenter:
            print("[FCM iOS] UNUserNotificationCenter absent")
            return
            
        try:
            print("[FCM iOS] Demande permissions et enregistrement APNs...")
            # 1. Demande d'autorisation (7 = Alert + Sound + Badge)
            self.UNCenter.requestAuthorizationWithOptions_completionHandler_(7, None)
            
            # 2. Enregistrement aupres d'APNs sur le thread principal Kivy
            Clock.schedule_once(self._register_remote_notifications, 0.5)
        except Exception as e:
            print(f"[FCM iOS] Erreur request_permissions : {e}")

    def _register_remote_notifications(self, dt=None):
        try:
            app = self.UIApplication.sharedApplication()
            app.registerForRemoteNotifications()
            print("[FCM iOS] registerForRemoteNotifications envoye avec succes")
            self._start_waiting_for_token()
        except Exception as e:
            print(f"[FCM iOS Error] registerForRemoteNotifications : {e}")
            
    def userNotificationCenter_willPresentNotification_withCompletionHandler(self, center, notification, completionHandler):
        """
        Méthode appelée automatiquement par iOS lorsque l'application est au PREMIER PLAN 
        et qu'une notification FCM arrive.
        """
        try:
            content = notification.request().content()
            title = str(content.title())
            body = str(content.body())
            
            # Récupération d'éventuelles données supplémentaires (userInfo)
            user_info = content.userInfo()
            match_id = None
            if user_info and user_info.objectForKey_("match_id"):
                match_id = str(user_info.objectForKey_("match_id"))

            print(f"[FCM iOS Foreground] Notification recue en temps reel : {title} - {body}")
            
            # Déclenchement immédiat de votre popup Kivy personnalisée
            Clock.schedule_once(lambda dt: declencher_alerte_depuis_natif(title, body, match_id), 0)
            
            # Optionnel : Appel du handler pour dire à iOS comment se comporter 
            # (1 = PresentationOptionBadge, 2 = PresentationOptionSound, 4 = PresentationOptionBanner)
            if completionHandler:
                completionHandler(4 | 2) # Affiche la bannière et joue le son
        except Exception as e:
            print(f"[FCM iOS Foreground Error] {e}")

def get_notification_manager():
    if platform == 'android':
        return AndroidNotificationManager()
    elif platform == 'ios':
        return IOSNotificationManager()
    return None

def afficher_popup_notification(titre, corps, match_id=None):
    """
    Affiche une popup d'alerte Kivy au premier plan (thread-safe grâce à Clock).
    """
    def _ouvrir(dt):
        content = BoxLayout(orientation="vertical", padding=dp(20), spacing=dp(15))
        
        # Titre
        content.add_widget(Label(
            text=f"[b]{titre}[/b]", 
            markup=True, 
            font_size=dp(18), 
            color=(0.1, 0.1, 0.2, 1),
            size_hint_y=None, 
            height=dp(30),
            halign="center"
        ))
        
        # Corps du message
        content.add_widget(Label(
            text=corps, 
            font_size=dp(15), 
            color=(0.2, 0.2, 0.25, 1),
            halign="center"
        ))
        
        popup = Popup(
            title="", 
            title_size=0, 
            content=content, 
            size_hint=(0.8, 0.4), 
            separator_height=0
        )
        
        # Boutons d'action
        btn_layout = BoxLayout(size_hint_y=None, height=dp(45), spacing=dp(10))
        
        if match_id:
            def voir_evenement(x):
                popup.dismiss()
                # Vous pouvez déclencher une logique globale ici si besoin
                
            btn_voir = Button(text="Voir", background_normal="", background_color=(0.15, 0.65, 0.35, 1), color=(1,1,1,1), bold=True)
            btn_voir.bind(on_release=voir_evenement)
            btn_layout.add_widget(btn_voir)
            
        btn_fermer = Button(text="Fermer", background_normal="", background_color=(0.8, 0.8, 0.82, 1), color=(0.2,0.2,0.2,1), bold=True)
        btn_fermer.bind(on_release=popup.dismiss)
        btn_layout.add_widget(btn_fermer)
        
        content.add_widget(btn_layout)
        popup.open()

    # Planifie l'ouverture sur le thread principal de l'UI Kivy en toute sécurité
    Clock.schedule_once(_ouvrir, 0)