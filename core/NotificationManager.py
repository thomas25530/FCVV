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
            # 1. NOUVEL ID : indispensable pour écraser l'ancien canal restreint
            channel_id = "fcvv_high_priority_v1"
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
        except Exception as e:
            print(f"[FCM ERROR] init_service : {e}")

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


from kivy.clock import Clock

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

def get_notification_manager():
    if platform == 'android':
        return AndroidNotificationManager()
    elif platform == 'ios':
        return IOSNotificationManager()
    return None