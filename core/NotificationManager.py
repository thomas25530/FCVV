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

        self.FIRMessaging = None
        self.UNCenter = None
        self.UIApplication = None

        self.pending_topics = set()

        try:
            print("[FCM iOS] Chargement Firebase...")

            # Firebase est configuré côté Objective-C dans
            # SDLUIKitDelegate.
            self.FIRMessaging = autoclass("FIRMessaging").messaging()

            self.UNCenter = (
                autoclass("UNUserNotificationCenter")
                .currentNotificationCenter()
            )

            self.UIApplication = autoclass("UIApplication")

            print("[FCM iOS] Firebase Messaging initialise.")

        except Exception as e:
            print(f"[FCM iOS INIT ERROR] {e!r}")

    # ----------------------------------------------------------
    # Initialisation
    # ----------------------------------------------------------

    def init_service(self):
        print("[FCM iOS] Service FCM initialise.")

        # Firebase + APNs sont initialisés côté Objective-C.
        #
        # On ne demande pas le token immédiatement :
        # Firebase attend que le token APNs soit associé.
        return True

    # ----------------------------------------------------------
    # Token
    # ----------------------------------------------------------

    def _objc_string_to_python(self, value):

        if value is None:
            return None

        # NSString -> Python
        try:
            result = value.UTF8String()

            if result:
                result = str(result)

                if result and not result.startswith("<"):
                    return result

        except Exception:
            pass

        # Fallback NSString.description
        try:
            result = value.description()

            if result:
                result = str(result)

                if result and not result.startswith("<"):
                    return result

        except Exception:
            pass

        return None

    def _get_token(self):

        if not self.FIRMessaging:
            return None

        try:
            token = self.FIRMessaging.FCMToken

            return self._objc_string_to_python(token)

        except Exception as e:
            print(
                f"[FCM iOS] Erreur lecture FCMToken : {e!r}"
            )
            return None

    def get_fcm_token(self):

        token = self._get_token()

        if token:
            print(
                f"[FCM iOS] Token disponible : "
                f"{token[:25]}..."
            )
            return token

        print(
            "[FCM iOS] Token FCM indisponible pour le moment."
        )

        return None

    # ----------------------------------------------------------
    # Topics
    # ----------------------------------------------------------

    def _do_subscribe(self, topic):

        if not self.FIRMessaging:
            print(
                "[FCM iOS] FIRMessaging indisponible."
            )
            return False

        try:
            print(
                f"[FCM iOS] Abonnement topic : {topic}"
            )

            if hasattr(
                self.FIRMessaging,
                "subscribeToTopic_completionHandler_"
            ):
                self.FIRMessaging.subscribeToTopic_completionHandler_(
                    topic,
                    None
                )
            else:
                self.FIRMessaging.subscribeToTopic_(topic)

            print(
                f"[FCM iOS] Demande abonnement envoyee : {topic}"
            )

            return True

        except Exception as e:
            print(
                f"[FCM iOS] Erreur abonnement "
                f"'{topic}' : {e!r}"
            )
            return False

    def subscribe_to_topic(self, topic):

        if not topic:
            return False

        token = self._get_token()

        if not token:
            print(
                f"[FCM iOS] Token absent -> "
                f"topic mis en attente : {topic}"
            )

            self.pending_topics.add(topic)

            return False

        return self._do_subscribe(topic)

    def unsubscribe_from_topic(self, topic):

        if not topic:
            return False

        self.pending_topics.discard(topic)

        if not self.FIRMessaging:
            print(
                "[FCM iOS] FIRMessaging indisponible."
            )
            return False

        try:
            self.FIRMessaging.unsubscribeFromTopic_(topic)

            print(
                f"[FCM iOS] Desabonnement : {topic}"
            )

            return True

        except Exception as e:
            print(
                f"[FCM iOS] Erreur desabonnement "
                f"'{topic}' : {e!r}"
            )

            return False

    # ----------------------------------------------------------
    # Permissions
    # ----------------------------------------------------------

    def request_permissions(self):

        print(
            "[FCM iOS] Les permissions APNs sont "
            "gerees par SDLUIKitDelegate."
        )

        # La demande de permission et
        # registerForRemoteNotifications()
        # sont effectués côté Objective-C.
        #
        # On ne les redemande pas ici.
        return True

def get_notification_manager():
    if platform == 'android':
        return AndroidNotificationManager()
    elif platform == 'ios':
        return IOSNotificationManager()
    return None