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
            channel = self.NotificationChannel("fcvv_high_priority_v2", "FCVV Notifications Importantes", 4)
            channel.enableVibration(True)
            channel.enableLights(True)
            channel.setDescription("Notifications urgentes avec pop-up d'affichage")
            self.activity.getSystemService(self.Context.NOTIFICATION_SERVICE).createNotificationChannel(channel)
            print("[FCM] Canal Haute Priorite cree avec succes.")

            if self.FirebaseApp.getApps(self.context).isEmpty():
                builder = self.autoclass('com.google.firebase.FirebaseOptions$Builder')()
                builder.setApiKey("AIzaSyDTxB5sz0Y1Olg4qXoreO5AviBVbUhHIhw")
                builder.setApplicationId("1:512335597045:android:9819dbed0c70a09d3be4bc")
                builder.setProjectId("fcvv-app")
                self.FirebaseApp.initializeApp(self.context, builder.build())

            self.token_task = self.FirebaseMessaging.getInstance().getToken()
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
        from android.permissions import Permission, request_permissions
        request_permissions([Permission.POST_NOTIFICATIONS])

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
            print("[FCM DEBUG] Chargement Firebase iOS...")
            self.FIRApp = autoclass("FIRApp")
            # Firebase configuré dans main.m ou AppDelegate
            if not self.FIRApp.defaultApp():
                print("[FCM iOS] FIRApp absent, tentative de configuration...")
                self.FIRApp.configure()
            print("[FCM DEBUG] Chargement FIRMessaging...")
            FIRMessagingClass = autoclass("FIRMessaging")
            try:
                self.FIRMessaging = FIRMessagingClass.messaging()
            except Exception:
                self.FIRMessaging = FIRMessagingClass.sharedInstance()
            self.UNCenter = autoclass("UNUserNotificationCenter").currentNotificationCenter()
            self.UIApplication = autoclass("UIApplication")
            print("[FCM iOS] Initialisation Firebase OK")
        except Exception as e:
            print(f"[FCM iOS Init Error] {e!r}")

    def init_service(self):
        token = self._get_token()
        if token:
            print(f"[FCM iOS] Token deja disponible : {token[:12]}...")
        else:
            print("[FCM iOS] En attente du token FCM (APNs necessaire)...")

    def _get_token(self):
        """Récupération synchrone et sécurisée du token FCM."""
        if not self.FIRMessaging:
            return None
        for name in ("FCMToken", "fcmToken"):
            try:
                token = getattr(self.FIRMessaging, name)
                if callable(token):
                    token = token()
                if token and str(token) != "<null>" and str(token) != "None":
                    return str(token)
            except Exception:
                pass
        return None

    def _start_waiting_for_token(self):
        if self.waiting_for_token:
            return
        self.waiting_for_token = True
        self.token_wait_count = 0
        print("[FCM iOS] Surveillance du token demarree...")
        Clock.schedule_interval(self._check_token, 1.0)

    def _check_token(self, dt):
        self.token_wait_count += 1
        token = self._get_token()
        if not token:
            if self.token_wait_count >= self.max_token_wait:
                print("[FCM iOS] Timeout attente token FCM.")
                self.waiting_for_token = False
                return False  # Arrête le timer
            return True       # Recommence au prochain tick
        print(f"[FCM iOS] Token obtenu : {token[:12]}...")
        self.waiting_for_token = False
        # Inscription aux topics en attente
        for topic in list(self.pending_topics):
            self._do_subscribe(topic) 
        self.pending_topics.clear()
        return False  # Arrête le timer

    def apns_token_received(self):
        print("[FCM iOS] APNs reçu, demarrage de l'attente FCM...")
        self._start_waiting_for_token()

    def _do_subscribe(self, topic):
        """Méthode interne d'abonnement gérant les différentes signatures SDK."""
        try:
            print(f"[FCM iOS] Abonnement topic : {topic}")
            # Signature récente (Firebase iOS SDK 8+)
            if hasattr(self.FIRMessaging, "subscribeToTopic_completionHandler_"):
                self.FIRMessaging.subscribeToTopic_completionHandler_(topic, None)
            else:
                # Ancienne signature
                self.FIRMessaging.subscribeToTopic_(topic)
            return True
        except Exception as e:
            print(f"[FCM iOS] Erreur abonnement topic '{topic}' : {e!r}")
            return False

    def subscribe_to_topic(self, topic):
        token = self._get_token()
        if not token:
            print(f"[FCM iOS] Token absent -> topic mis en attente : {topic}")
            self.pending_topics.add(topic)
            self._start_waiting_for_token()
            return False
        return self._do_subscribe(topic)

    def unsubscribe_from_topic(self, topic):
        self.pending_topics.discard(topic)
        try:
            if hasattr(self.FIRMessaging, "unsubscribeFromTopic_completionHandler_"):
                self.FIRMessaging.unsubscribeFromTopic_completionHandler_(topic, None)
            else:
                self.FIRMessaging.unsubscribeFromTopic_(topic)
        except Exception as e:
            print(f"[FCM iOS] Erreur desabonnement topic '{topic}' : {e!r}")

    def request_permissions(self):
        """Demande de permission et enregistrement APNs sécurisé pour PyObjUS."""
        if not self.UNCenter:
            print("[FCM iOS] UNUserNotificationCenter absent")
            return
        try:
            print("[FCM iOS] Demande de permissions et enregistrement APNs...")
            from pyobjus import blockify
            # Callback sécurisé évitant les crashs Segfault d'un completionHandler à None
            def on_permission_result(granted, error):
                print(f"[FCM iOS] Permission accordee : {granted}")
            # 7 = UNAuthorizationOptionAlert | UNAuthorizationOptionSound | UNAuthorizationOptionBadge
            handler_block = blockify(on_permission_result, signature="v@?B@")
            self.UNCenter.requestAuthorizationWithOptions_completionHandler_(7, handler_block)
            # Enregistrement auprès d'APNs sur le thread UI Kivy
            Clock.schedule_once(self._register_remote_notifications, 0.5)
        except Exception as e:
            print(f"[FCM iOS] Erreur lors de request_permissions : {e!r}")
    def _register_remote_notifications(self, dt=None):
        try:
            app = self.UIApplication.sharedApplication()
            app.registerForRemoteNotifications()
            print("[FCM iOS] registerForRemoteNotifications envoye avec succes.")
            self._start_waiting_for_token()
        except Exception as e:
            print(f"[FCM iOS Error] registerForRemoteNotifications : {e!r}")

def get_notification_manager():
    if platform == 'android':
        return AndroidNotificationManager()
    elif platform == 'ios':
        return IOSNotificationManager()
    return None
