# core/NotificationManager.py
from kivy.utils import platform
from kivy.clock import Clock
import json
import os
import time
from datetime import datetime
import tempfile

class NotificationManager:
    def __init__(self, app):
        self.app = app
        self.file_path = os.path.join(app.user_data_dir,"notifications.json")
        self.notifications = []
        self.charger_notifications()

    def charger_notifications(self):
        """Charge l'historique des notifications."""
        if not os.path.exists(self.file_path):
            self.notifications = []
            return
        try:
            with open( self.file_path,"r", encoding="utf-8") as f:
                self.notifications = json.load(f)
        except Exception as e:
            print( f"[NOTIFICATIONS] Erreur chargement : {e}" )
            self.notifications = []
            
    def trouver_notification_par_android_id(self, android_id):
        """Retrouve une notification Android déjà enregistrée."""
        if not android_id:
            return None
    
        for notif in self.notifications:
            ancien_id = notif.get("android_id")
            if ancien_id is not None and str(ancien_id) == str(android_id):
                return notif
    
        return None
    
    def ajouter_notification(self, titre, message, categorie=None, match_id=None, notif_type=None, payload=None, android_id=None, source_id=None,):
        """Ajoute une notification sans doublon et conserve ses identifiants."""
        # Normaliser les identifiants
        source_id = str(source_id).strip() if source_id else None
        if android_id is not None:
            try:
                android_id = int(android_id)
            except (TypeError, ValueError):
                android_id = None
        # 1. Chercher par source_id
        existante = None
        if source_id:
            for notif in self.notifications:
                if notif.get("source_id") == source_id:
                    existante = notif
                    break
        # 2. Sinon, chercher par android_id
        if existante is None and android_id is not None:
            existante = self.trouver_notification_par_android_id(android_id)
        # 3. Compléter la notification existante
        if existante is not None:
            modifiee = False
            if source_id and not existante.get("source_id"):
                existante["source_id"] = source_id
                modifiee = True
            if android_id is not None and existante.get("android_id") != android_id:
                existante["android_id"] = android_id
                modifiee = True
            if not existante.get("titre") and titre:
                existante["titre"] = titre
                modifiee = True
            if not existante.get("message") and message:
                existante["message"] = message
                modifiee = True
            if not existante.get("categorie") and categorie:
                existante["categorie"] = categorie
                modifiee = True
            if existante.get("match_id") is None and match_id is not None:
                existante["match_id"] = match_id
                modifiee = True
            if not existante.get("type") and notif_type:
                existante["type"] = notif_type
                modifiee = True
            if modifiee:
                self.sauvegarder_notifications()
            return existante
        # 4. Créer une nouvelle notification
        ids_existants = {str(n.get("id")) for n in self.notifications}
        notif_id = str(int(time.time() * 1000))
        while notif_id in ids_existants:
            notif_id = str(int(notif_id) + 1)
        notif = {
            "id": notif_id,
            "android_id": android_id,
            "date": datetime.now().strftime("%d.%m.%Y %H:%M"),
            "titre": titre,
            "message": message,
            "categorie": categorie,
            "match_id": match_id,
            "type": notif_type,
            "payload": payload or {},
            "lue": False,
            "traitee": False,
            "source_id": source_id,
        }
        self.notifications.insert(0, notif)
        self.sauvegarder_notifications()
        return notif
    
    def get_unread_count(self):
        return sum(
            1
            for notif in self.notifications
            if not notif.get("lue", False)
        )
    
    def get_unprocessed_count(self):
        return sum(
            1
            for notif in self.notifications
            if not notif.get("traitee", False)
        )
        
    def marquer_comme_lue(self, notif_id):
        for notif in self.notifications:
            if notif.get("id") == notif_id:
                notif["lue"] = True
                break
        self.sauvegarder_notifications()
        
    def marquer_comme_traitee(self, notif_id):
        for notif in self.notifications:
            if notif.get("id") == notif_id:
                notif["lue"] = True
                notif["traitee"] = True
                break
        self.sauvegarder_notifications()
        
    def rediriger_notification(self, notif):
        """Redirige vers l'écran adapté au type de notification."""
        app = self.app
        root = app.root
        notif_type = notif.get("type")
        payload = notif.get("payload") or {}
        # Compatibilité avec les notifications déjà enregistrées
        categorie = ( payload.get("categorie") or notif.get("categorie"))
        match_id = ( payload.get("match_id") or notif.get("match_id"))
        try:
            if notif_type in ( "vestiaire", "vestiaire_message", "match", "chat", "message", "messages", "nouveau_message","echange","evenement","événement", "event", "creation_evenement","evenement_creation","validation","convocation"):
                if not categorie:
                    print( "[NOTIFICATION] Categorie absente de la notification.")
                    return False
                app.executer_redirection_vestiaire( categorie, match_id, notif_type)
            elif notif_type in ("news", "home", "manual", None):
                app.executer_redirection_home()
            else:
                print(f"[NOTIFICATION] Type inconnu : {notif_type}")
                return False
            return True
        except Exception as e:
            print( f"[NOTIFICATION] Erreur de redirection : {e}" )
            return False
    
    def marquer_tout_comme_lu(self):
        self.annuler_toutes_notifications_barre()
        for notif in self.notifications:
            notif["lue"] = True
        self.sauvegarder_notifications()
    
    def supprimer_notification(self, notif_id):
        """Supprime une notification."""
        avant = len(self.notifications)
        self.notifications = [
            notif
            for notif in self.notifications
            if notif.get("id") != notif_id
        ]
        if len(self.notifications) != avant:
            self.sauvegarder_notifications()
        
    def supprimer_notifications(self, notif_ids):
        """Supprime plusieurs notifications."""
        notif_ids = set(notif_ids)
        self.notifications = [
            notif
            for notif in self.notifications
            if notif.get("id") not in notif_ids
        ]
        self.sauvegarder_notifications()
        
    def sauvegarder_notifications(self):
        """Sauvegarde les notifications de façon atomique."""
        dossier = os.path.dirname(self.file_path)
        fichier_temporaire = None
        try:
            os.makedirs(dossier, exist_ok=True)
            with tempfile.NamedTemporaryFile(mode="w",encoding="utf-8",dir=dossier,delete=False) as fichier:
                fichier_temporaire = fichier.name
                json.dump( self.notifications,fichier, ensure_ascii=False, indent=2 )
                fichier.flush()
                os.fsync(fichier.fileno())
            os.replace(fichier_temporaire, self.file_path)
            return True
        except Exception as e:
            print(f"[NOTIFICATIONS] Erreur sauvegarde : {e}")
            if fichier_temporaire and os.path.exists(fichier_temporaire):
                try:
                    os.remove(fichier_temporaire)
                except OSError:
                    pass
            return False
    
    def vider_notifications(self):
        """Vide les notifications et vérifie la sauvegarde locale."""
        anciennes_notifications = self.notifications.copy()
        self.annuler_toutes_notifications_barre()
        self.notifications.clear()
        if not self.sauvegarder_notifications():
            self.notifications = anciennes_notifications
            print("[NOTIFICATIONS] echec du vidage local.")
            return False
        print("[NOTIFICATIONS] Historique local vide.")
        return True
        
    def supprimer_traitees(self):
        """Supprime les notifications deja traitees."""
        self.notifications = [
            notif
            for notif in self.notifications
            if not notif.get("traitee", False)
        ]
        self.sauvegarder_notifications()
        
    def init_service(self): raise NotImplementedError
    def subscribe_to_topic(self, topic): raise NotImplementedError
    def unsubscribe_from_topic(self, topic): raise NotImplementedError
    def request_permissions(self): raise NotImplementedError
    def get_fcm_token(self): raise NotImplementedError
    def annuler_notification_barre(self, notif):
        """Méthode de base, surchargée par les plateformes."""
        return False
    def annuler_toutes_notifications_barre(self):
        """Annule toutes les notifications natives connues."""
        succes = True
        for notif in list(self.notifications):
            try:
                if not self.annuler_notification_barre(notif):
                    succes = False
            except Exception as e:
                succes = False
                print(f"[NOTIFICATIONS] Erreur annulation : {e}")
        return succes

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

    
    def annuler_notification_barre(self, notif):
        """Annule la notification système Android et vérifie le résultat."""
        try:
            android_id = notif.get("android_id")
            if android_id is None or str(android_id).strip() == "":
                print("[ANDROID] Aucun android_id : annulation impossible.")
                return False
            notification_id = int(android_id)
            notification_manager = self.activity.getSystemService(self.Context.NOTIFICATION_SERVICE )
            # Vérifier si cette notification est actuellement active.
            actives_avant = notification_manager.getActiveNotifications()
            presente_avant = any(n.getId() == notification_id for n in actives_avant)
            print(
                f"[ANDROID] Annulation demandee : id={notification_id}, "
                f"active_avant={presente_avant}"
            )
            notification_manager.cancel(notification_id)
            actives_apres = notification_manager.getActiveNotifications()
            presente_apres = any(n.getId() == notification_id for n in actives_apres)
            print(
                f"[ANDROID] Resultat annulation : id={notification_id}, "
                f"active_apres={presente_apres}"
            )
            return not presente_apres
        except Exception as e:
            print(f"[ANDROID ERROR] annuler_notification_barre : {e}")
            return False
    
    def remettre_zero_badge_android(self):
        """Demande la remise à zéro du badge de l'application Android."""
        try:
            from jnius import autoclass
            PythonActivity = autoclass("org.kivy.android.PythonActivity")
            activity = PythonActivity.mActivity
            NotificationManager = autoclass("android.app.NotificationManager")
            notification_manager = activity.getSystemService("notification")
            # Supprime les notifications affichées dans la barre système.
            notification_manager.cancelAll()
            print("[ANDROID] Notifications systeme annulees.")
        except Exception as e:
            print(f"[ANDROID BADGE ERROR] {e}")
    
    def annuler_toutes_notifications_barre(self):
        """Supprime toutes les notifications système de l'application."""
        try:
            notification_manager = self.activity.getSystemService(self.Context.NOTIFICATION_SERVICE)
            notification_manager.cancelAll()
            print("[ANDROID] Toutes les notifications systeme ont ete annulees.")
            return True
        except Exception as e:
            print(f"[ANDROID ERROR] Annulation globale : {e}")
            return False
    
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
            self.UNCenter = (autoclass("UNUserNotificationCenter").currentNotificationCenter())
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
    
    def annuler_notification_barre(self, notif):
        """Retire la notification du centre de notifications iOS."""
        try:
            if not self.UNCenter:
                return
            payload = notif.get("payload") or {}
            ios_identifier = payload.get("ios_identifier")
            if not ios_identifier:
                print("[FCM iOS] Aucun ios_identifier trouve pour cette notification.")
                return
            from pyobjus import autoclass
            NSArray = autoclass("NSArray")
            NSString = autoclass("NSString")
            ns_id = NSString.stringWithUTF8String_(str(ios_identifier))
            identifiers = NSArray.arrayWithObject_(ns_id)
            self.UNCenter.removeDeliveredNotificationsWithIdentifiers_(identifiers)
            print(
                f"[FCM iOS] Notification supprimee : "
                f"ios_identifier={ios_identifier}"
            )
        except Exception as e:
            print(f"[FCM iOS ERROR] annuler_notification_barre : {e}")
    
    def annuler_toutes_notifications_barre(self):
        """Supprime les notifications livrées et celles en attente sur iOS."""
        try:
            if not self.UNCenter:
                print("[FCM iOS] UNUserNotificationCenter indisponible.")
                return False
            self.UNCenter.removeAllDeliveredNotifications()
            self.UNCenter.removeAllPendingNotificationRequests()
            print("[FCM iOS] Toutes les notifications livrees et en attente ont ete supprimees.")
            return True
        except Exception as e:
            print(f"[FCM iOS ERROR] Annulation globale : {e}")
            return False
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
            print(f"[FCM iOS] Erreur lecture FCMToken : {e!r}")
            return None

    def get_fcm_token(self):
        token = self._get_token()
        if token:
            print(
                f"[FCM iOS] Token disponible : "
                f"{token[:25]}..."
            )
            return token
        print("[FCM iOS] Token FCM indisponible pour le moment.")
        return None
    # ----------------------------------------------------------
    # Topics
    # ----------------------------------------------------------
    def _do_subscribe(self, topic):
        if not self.FIRMessaging:
            print("[FCM iOS] FIRMessaging indisponible.")
            return False
        try:
            print(f"[FCM iOS] Abonnement topic : {topic}")
            if hasattr(self.FIRMessaging,"subscribeToTopic_completionHandler_"):
                self.FIRMessaging.subscribeToTopic_completionHandler_(topic, None )
            else:
                self.FIRMessaging.subscribeToTopic_(topic)
            print(f"[FCM iOS] Demande abonnement envoyee : {topic}" )
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
            print("[FCM iOS] FIRMessaging indisponible.")
            return False
        try:
            self.FIRMessaging.unsubscribeFromTopic_(topic)
            print(f"[FCM iOS] Desabonnement : {topic}")
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
        print( "[FCM iOS] Les permissions APNs sont gerees par SDLUIKitDelegate.")
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
