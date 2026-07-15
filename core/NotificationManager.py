# core/NotificationManager.py
from kivy.utils import platform
from kivy.clock import Clock

class NotificationManager:
    def init_service(self): raise NotImplementedError
    def subscribe_to_topic(self, topic): raise NotImplementedError
    def unsubscribe_from_topic(self, topic): raise NotImplementedError
    def request_permissions(self): raise NotImplementedError

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
    
    def init_service(self):
        try:
            # Canal Android
            channel_id = "fcvv_service_channel"
            channel = self.NotificationChannel(
                channel_id,
                "FCVV Notifications",
                3
            )
    
            manager = self.activity.getSystemService(
                self.Context.NOTIFICATION_SERVICE
            )
            manager.createNotificationChannel(channel)
    
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
    
        except Exception as e:
            print(f"[FCM ERROR] init_service : {e}")
    
    def subscribe_to_topic(self, topic):
        try:
            # Vérification du token uniquement pour le diagnostic
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
    
            # On lance TOUJOURS l'abonnement
            task = self.FirebaseMessaging.getInstance().subscribeToTopic(topic)
    
            print(f"[FCM] Requete envoyee pour : {topic}")
    
        except Exception as e:
            print(f"[FCM ERROR] subscribe_to_topic : {e}")
    
    def unsubscribe_from_topic(self, topic):
        try:
            print(f"[FCM] Desabonnement : {topic}")
    
            self.FirebaseMessaging.getInstance()\
                .unsubscribeFromTopic(topic)
    
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

        # Initialisation sécurisée par défaut
        self.FIRApp = None
        self.FIRMessaging = None
        self.UNCenter = None

        # Topics en attente tant que le token FCM n'est pas disponible
        self.pending_topics = set()

        # Pour éviter de lancer plusieurs timers
        self.waiting_for_token = False

        try:
            print("[FCM DEBUG] Recherche FIRApp...")
            self.FIRApp = autoclass("FIRApp")

            if not self.FIRApp.defaultApp():
                self.FIRApp.configure()

            print("[FCM DEBUG] Recherche FIRMessaging...")
            FIRMessagingClass = autoclass("FIRMessaging")

            if hasattr(FIRMessagingClass, "messaging"):
                self.FIRMessaging = FIRMessagingClass.messaging()
            else:
                self.FIRMessaging = FIRMessagingClass.sharedInstance()

            self.UNCenter = autoclass(
                "UNUserNotificationCenter"
            ).currentNotificationCenter()

            self.UIApplication = autoclass("UIApplication")

            print("[FCM iOS] Initialisation Firebase reussie.")

        except Exception as e:
            print(f"[FCM iOS Init Error] {e}")

    def init_service(self):
        token = self._get_token()

        if token:
            print(f"[FCM iOS] Token deja disponible : {str(token)[:12]}...")
        else:
            print("[FCM iOS] En attente du token FCM...")

    def _get_token(self):

        if not self.FIRMessaging:
            return None

        for name in (
            "FCMToken",
            "fcmToken",
            "token",
        ):
            try:
                attr = getattr(self.FIRMessaging, name)

                token = attr() if callable(attr) else attr

                if token:
                    return token

            except Exception:
                pass

        return None

    def _start_waiting_for_token(self):
        if self.waiting_for_token:
            return

        self.waiting_for_token = True
        print("[FCM iOS] Attente automatique du token...")
        Clock.schedule_interval(self._check_token, 1.0)

    def _check_token(self, dt):

        token = self._get_token()

        if not token:
            return True

        print(f"[FCM iOS] Token obtenu : {str(token)[:12]}...")

        self.waiting_for_token = False

        for topic in list(self.pending_topics):
            try:
                print(f"[FCM iOS] Abonnement automatique : {topic}")
                self.FIRMessaging.subscribeToTopic_(topic)
            except Exception as e:
                print(f"[FCM iOS] Erreur abonnement {topic} : {e}")

        self.pending_topics.clear()

        return False

    def subscribe_to_topic(self, topic):

        token = self._get_token()

        if not token:
            print(f"[FCM iOS] Token absent. Topic mis en attente : {topic}")

            self.pending_topics.add(topic)

            self._start_waiting_for_token()

            return False

        print(f"[FCM iOS] Abonnement au topic : {topic}")

        try:
            self.FIRMessaging.subscribeToTopic_(topic)
            print("[FCM iOS] Abonnement envoye")
            return True

        except Exception as e:
            print(f"[FCM iOS] Erreur : {e}")
            return False

    def unsubscribe_from_topic(self, topic):
        print(f"[FCM iOS] Desabonnement : {topic}")

        self.pending_topics.discard(topic)

        try:
            self.FIRMessaging.unsubscribeFromTopic_(topic)

        except Exception as e:
            print(f"[FCM iOS] Erreur desabonnement : {e}")

    def request_permissions(self):
        options = 7

        print("[FCM iOS] Demande de permissions...")

        self.UNCenter.requestAuthorizationWithOptions_completionHandler_(
            options,
            self.handle_permission_response
        )

    def handle_permission_response(self, granted, error):

        if granted:
            print("[FCM iOS] Permission accordee")

            app = self.UIApplication.sharedApplication()
            app.registerForRemoteNotifications()

            print("[FCM iOS] registerForRemoteNotifications envoye")

            # On démarre également l'attente du token
            self._start_waiting_for_token()

        else:
            err = error.localizedDescription if error else "Inconnue"
            print(f"[FCM iOS] Permission refusee : {err}")