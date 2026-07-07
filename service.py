from jnius import autoclass
import time

# On récupère le contexte du service
PythonService = autoclass('org.kivy.android.PythonService')
service = PythonService.mService
Context = autoclass('android.content.Context')
NotificationManager = autoclass('android.app.NotificationManager')
NotificationChannel = autoclass('android.app.NotificationChannel')
Notification = autoclass('android.app.Notification')

def start_foreground_service():
    channel_id = "fcvv_service_channel"
    channel_name = "FCVV Notifications"
    
    # Création du canal (obligatoire pour Android 8+)
    channel = NotificationChannel(channel_id, channel_name, NotificationManager.IMPORTANCE_DEFAULT)
    manager = service.getSystemService(Context.NOTIFICATION_SERVICE)
    manager.createNotificationChannel(channel)
    
    # Construction de la notification persistante
    # Utilisation de Notification.Builder pour être compatible avec les versions récentes
    builder = Notification.Builder(service, channel_id)
    builder.setContentTitle("FCVV")
    builder.setContentText("Service de notifications actif")
    builder.setSmallIcon(service.getApplicationInfo().icon)
    
    # Passage en mode Foreground
    service.startForeground(1, builder.build())

if __name__ == '__main__':
    # Important : il faut démarrer le service en foreground immédiatement
    start_foreground_service()
    
    # Boucle de vie légère
    while True:
        # Le service reste actif ici. FCM gérera les messages 
        # en tâche de fond automatiquement.
        time.sleep(30)