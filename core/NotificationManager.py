# core/NotificationManager.py
from kivy.utils import platform

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
    
            print("[FCM] Demande de token envoyée")
    
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
                    print("[FCM] Token en cours de création...")
    
            print(f"[FCM] Demande d'abonnement au topic : {topic}")
    
            # On lance TOUJOURS l'abonnement
            task = self.FirebaseMessaging.getInstance().subscribeToTopic(topic)
    
            print(f"[FCM] Requête envoyée pour : {topic}")
    
        except Exception as e:
            print(f"[FCM ERROR] subscribe_to_topic : {e}")
    
    def unsubscribe_from_topic(self, topic):
        try:
            print(f"[FCM] Désabonnement : {topic}")
    
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
        # Classes nécessaires pour iOS/Firebase
        self.UNCenter = autoclass('UNUserNotificationCenter').currentNotificationCenter()
        # FIRMessaging est un singleton, on récupère l'instance
        self.FIRMessaging = autoclass('FIRMessaging').messaging()

    def init_service(self):
        # Sur iOS, l'initialisation de Firebase est gérée 
        # via le fichier AppDelegate dans Xcode (FIRApp configure)
        # On vérifie ici si le token est déjà disponible pour confirmer la connexion
        token = self.FIRMessaging.fcmToken
        if token:
            print("[FCM iOS] Service prêt et Token FCM disponible")
        else:
            print("[FCM iOS] Service initialisé, attente du token FCM...")

    def _get_token(self):
        """Retourne le token FCM s'il est disponible, sinon None."""
        return self.FIRMessaging.fcmToken

    def subscribe_to_topic(self, topic):
        # Vérification de la disponibilité du token avant abonnement
        token = self._get_token()
        
        if not token:
            print(f"[FCM iOS WARNING] Token non trouvé. L'abonnement à '{topic}' risque d'échouer.")
        else:
            print(f"[FCM iOS] Token détecté : {str(token)[:25]}...")

        # Utilisation de la méthode Objective-C correspondante
        print(f"[FCM iOS] Demande d'abonnement au topic : {topic}")
        self.FIRMessaging.subscribeToTopic_completion_(topic, None)

    def unsubscribe_from_topic(self, topic):
        print(f"[FCM iOS] Désabonnement du topic : {topic}")
        self.FIRMessaging.unsubscribeFromTopic_completion_(topic, None)

    def request_permissions(self):
        # Demande les autorisations de base (Alertes, Sons, Badges)
        # UNAuthorizationOptionAlert = 1 << 0, Badge = 1 << 1, Sound = 1 << 2
        options = (1 << 0) | (1 << 1) | (1 << 2) 
        self.UNCenter.requestAuthorizationWithOptions_completionHandler_(
            options, 
            self.handle_permission_response
        )

    def handle_permission_response(self, granted, error):
        if granted:
            print("[FCM iOS] Permission accordée")
        else:
            # Si error n'est pas None, on affiche le message d'erreur
            err_msg = error.localizedDescription if error is not None else "Inconnue"
            print(f"[FCM iOS] Permission refusée : {err_msg}")

def get_notification_manager():
    if platform == 'android':
        return AndroidNotificationManager()
    elif platform == 'ios':
        return IOSNotificationManager()
    return None