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

            # Firebase est déjà configuré dans main.m
            if not self.FIRApp.defaultApp():
                print("[FCM iOS] FIRApp absent, tentative configure")
                self.FIRApp.configure()

            print("[FCM DEBUG] Chargement FIRMessaging...")

            FIRMessagingClass = autoclass("FIRMessaging")

            if hasattr(FIRMessagingClass, "messaging"):
                self.FIRMessaging = FIRMessagingClass.messaging()
            else:
                self.FIRMessaging = FIRMessagingClass.sharedInstance()


            self.UNCenter = autoclass(
                "UNUserNotificationCenter"
            ).currentNotificationCenter()

            self.UIApplication = autoclass(
                "UIApplication"
            )

            print("[FCM iOS] Initialisation Firebase OK")


        except Exception as e:
            print(f"[FCM iOS Init Error] {e}")


    def init_service(self):

        token = self._get_token()

        if token:
            print(
                f"[FCM iOS] Token deja disponible : {str(token)[:12]}..."
            )
        else:
            print(
                "[FCM iOS] En attente du token FCM (APNS necessaire)..."
            )


    def _get_token(self):

        if not self.FIRMessaging:
            return None


        # Accès direct propriété
        for name in (
            "FCMToken",
            "fcmToken",
        ):
            try:
                token = getattr(self.FIRMessaging, name)

                if callable(token):
                    token = token()

                if token:
                    return token

            except Exception:
                pass


        # Fallback méthode Firebase
        try:
            if hasattr(
                self.FIRMessaging,
                "tokenWithCompletion_"
            ):

                result = []

                def callback(token, error):
                    if token:
                        result.append(token)

                self.FIRMessaging.tokenWithCompletion_(callback)

                if result:
                    return result[0]

        except Exception:
            pass


        return None


    def _start_waiting_for_token(self):

        if self.waiting_for_token:
            return

        self.waiting_for_token = True
        self.token_wait_count = 0

        print("[FCM iOS] Surveillance token demarree")

        Clock.schedule_interval(
            self._check_token,
            1.0
        )


    def _check_token(self, dt):

        self.token_wait_count += 1

        token = self._get_token()


        if not token:

            if self.token_wait_count >= self.max_token_wait:

                print(
                    "[FCM iOS] Timeout attente token FCM"
                )

                self.waiting_for_token = False
                return False

            return True


        print(
            f"[FCM iOS] Token obtenu : {str(token)[:12]}..."
        )


        self.waiting_for_token = False


        for topic in list(self.pending_topics):

            try:
                print(
                    f"[FCM iOS] Abonnement automatique : {topic}"
                )

                self.FIRMessaging.subscribeToTopic_(topic)


            except Exception as e:

                print(
                    f"[FCM iOS] Erreur topic {topic}: {e}"
                )


        self.pending_topics.clear()

        return False


    def apns_token_received(self):
        print("[FCM iOS] APNS recu, demarrage attente FCM")
        self._start_waiting_for_token()
    
    
    def subscribe_to_topic(self, topic):

        token = self._get_token()


        if not token:

            print(
                f"[FCM iOS] Token absent -> attente topic : {topic}"
            )

            self.pending_topics.add(topic)

            self._start_waiting_for_token()

            return False


        try:

            print(
                f"[FCM iOS] Abonnement topic : {topic}"
            )

            self.FIRMessaging.subscribeToTopic_(topic)

            return True


        except Exception as e:

            print(
                f"[FCM iOS] Erreur abonnement : {e}"
            )

            return False



    def unsubscribe_from_topic(self, topic):

        self.pending_topics.discard(topic)

        try:

            self.FIRMessaging.unsubscribeFromTopic_(topic)

        except Exception as e:

            print(
                f"[FCM iOS] Erreur desabonnement : {e}"
            )



    def request_permissions(self):

        if not self.UNCenter:
            print(
                "[FCM iOS] UNUserNotificationCenter absent"
            )
            return


        print(
            "[FCM iOS] Demande permissions..."
        )


        self.UNCenter.requestAuthorizationWithOptions_completionHandler_(
            7,
            self.handle_permission_response
        )



    def handle_permission_response(self, granted, error):

        if granted:

            print(
                "[FCM iOS] Permission accordee"
            )

            app = self.UIApplication.sharedApplication()

            app.registerForRemoteNotifications()


            print(
                "[FCM iOS] registerForRemoteNotifications envoye"
            )


            print(
                "[FCM iOS] Attente du token APNS avant FCM"
            )


        else:

            err = (
                error.localizedDescription
                if error
                else "Inconnue"
            )

            print(
                f"[FCM iOS] Permission refusee : {err}"
            )
            

def get_notification_manager():
    if platform == 'android':
        return AndroidNotificationManager()
    elif platform == 'ios':
        return IOSNotificationManager()
    return None