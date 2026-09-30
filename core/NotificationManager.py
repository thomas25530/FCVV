# core/NotificationManager.py
from kivy.utils import platform
from kivy.clock import Clock

class NotificationManager:
    def init_service(self): raise NotImplementedError
    def subscribe_to_topic(self, topic): raise NotImplementedError
    def unsubscribe_from_topic(self, topic): raise NotImplementedError
    def request_permissions(self): raise NotImplementedError
    def get_fcm_token(self): raise NotImplementedError

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

    def subscribe_to_topic(self, topic, retry=0):
        try:
            # Token pas encore prêt
            if self.token_task is None:
                self.token_task = self.FirebaseMessaging.getInstance().getToken()
    
            if not self.token_task.isComplete():
                print(f"[FCM WAIT] Token non disponible pour abonnement {topic}")
                if retry < 5:
                    Clock.schedule_once(lambda dt: self.subscribe_to_topic(topic, retry + 1), 2)
                return
            if not self.token_task.isSuccessful():
                print("[FCM ERROR] Token generation failed")
                self.token_task = self.FirebaseMessaging.getInstance().getToken()
                if retry < 5:
                    Clock.schedule_once(lambda dt: self.subscribe_to_topic(topic, retry + 1), 2)
                return
            
            # Appel direct sans OnCompleteListener (plus d'erreur de class loader)
            print(f"[FCM OK] Demande d'abonnement envoyee : {topic}")
            self.FirebaseMessaging.getInstance().subscribeToTopic(topic)
            
        except Exception as e:
            print(f"[FCM ERROR] subscribe_to_topic : {e}")
            if retry < 5:
                Clock.schedule_once(lambda dt: self.subscribe_to_topic(topic, retry + 1), 2)

    def unsubscribe_from_topic(self, topic):
        try:
            print(f"[FCM] Desabonnement : {topic}")
            self.FirebaseMessaging.getInstance().unsubscribeFromTopic(topic)
        except Exception as e:
            print(f"[FCM ERROR] unsubscribe : {e}")
            
    def get_fcm_token(self):
        try:
            if self.token_task is None:
                self.token_task = self.FirebaseMessaging.getInstance().getToken()
            if self.token_task.isComplete():
                if self.token_task.isSuccessful():
                    token = self.token_task.getResult()
                    if token:
                        token = str(token)
                        print(f"[FCM] Token Android disponible : {token[:25]}...")
                        return token
                print("[FCM] Token Android indisponible")
                return None
            print("[FCM] Token Android encore en cours de recuperation...")
            return None
        except Exception as e:
            print(f"[FCM ERROR] get_fcm_token Android : {e}")
            return None

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
            print("[FCM iOS] Chargement Firebase...")
            self.FIRApp = autoclass("FIRApp")
            if not self.FIRApp.defaultApp():
                print("[FCM iOS] Firebase non configure.")
                self.FIRApp.configure()
            self.FIRMessaging = autoclass("FIRMessaging").messaging()
            self.UNCenter = (
                autoclass("UNUserNotificationCenter")
                .currentNotificationCenter()
            )
            self.UIApplication = autoclass("UIApplication")
            print("[FCM iOS] Firebase initialise.")
        except Exception as e:
            print(f"[FCM iOS INIT ERROR] {e!r}")

    def init_service(self):
        token = self._get_token()
        if token:
            print(f"[FCM iOS] Token deja disponible : {token[:12]}...")
        else:
            print("[FCM iOS] En attente du token FCM (APNs necessaire)...")

    def _get_token(self):
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
                return False
            return True
        print(f"[FCM iOS] Token obtenu : {token[:12]}...")
        self.waiting_for_token = False
        for topic in list(self.pending_topics):
            self._do_subscribe(topic) 
        self.pending_topics.clear()
        return False

    def apns_token_received(self):
        print("[FCM iOS] APNs recu, demarrage de l'attente FCM...")
        self._start_waiting_for_token()

    def _do_subscribe(self, topic):
        try:
            print(f"[FCM iOS] Abonnement topic : {topic}")
            if hasattr(self.FIRMessaging, "subscribeToTopic_completionHandler_"):
                self.FIRMessaging.subscribeToTopic_completionHandler_(topic, None)
            else:
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
        print("[FCM iOS] Demande permission notifications...")
        if not self.UNCenter:
            print("[FCM iOS] UNUserNotificationCenter absent")
            return
        try:
            options = 4 | 2 | 1
            def completion(granted, error):
                print(
                    f"[FCM iOS] Permission result : "
                    f"granted={granted}, error={error}"
                )
                if granted:
                    Clock.schedule_once(
                        self._register_remote_notifications,
                        0.2
                    )
            self.UNCenter.requestAuthorizationWithOptions_completionHandler_(
                options,
                completion
            )
        except Exception as e:
            print(f"[FCM iOS] Permission error : {e!r}")
            
    def _register_remote_notifications(self, dt=None):
        try:
            app = self.UIApplication.sharedApplication()
            app.registerForRemoteNotifications()
            print("[FCM iOS] registerForRemoteNotifications envoye avec succes.")
            self._start_waiting_for_token()
        except Exception as e:
            print(f"[FCM iOS Error] registerForRemoteNotifications : {e!r}")
    
    def get_fcm_token(self):
        token = self._get_token()
        if token:
            print(f"[FCM iOS] Token disponible : {token[:25]}...")
            return token
        print("[FCM iOS] Token FCM indisponible pour le moment.")
        return None

def get_notification_manager():
    if platform == 'android':
        return AndroidNotificationManager()
    elif platform == 'ios':
        return IOSNotificationManager()
    return None