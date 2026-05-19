import os
import time
import json
import yaml
import requests
import sys
import configparser
import urllib3

# DÃ©tection de la plateforme sans importer kivy.utils (pour la stabilitÃ© du service)
IS_ANDROID = 'PYTHON_SERVICE_ARGUMENT' in os.environ or 'PYTHON_SERVICE_ARG' in os.environ

try:
    import certifi
    # On vÃ©rifie sur Android, on ignore sur PC (Ã  cause des antivirus/pare-feu)
    VERIFY_SSL = certifi.where() if IS_ANDROID else False
except ImportError:
    VERIFY_SSL = False

if not IS_ANDROID:
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Import sÃ©curisÃ© de plyer
try:
    from plyer import notification
except ImportError:
    notification = None

# --- CONFIGURATION DES CHEMINS ---
def get_data_path():
    """
    Récupère dynamiquement le chemin des données.
    """
    # 1. API Jnius pour Android (RÃ©cupÃ¨re l'argument passÃ© dans service.start)
    try:
        from jnius import autoclass
        PythonService = autoclass('org.kivy.android.PythonService')
        if PythonService.mService:
            arg = PythonService.mService.getStartObject()
            if arg:
                return str(arg)
    except:
        pass

    # 2. Variables d'environnement Kivy (Android fallback)
    arg_env = os.environ.get('PYTHON_SERVICE_ARGUMENT') or os.environ.get('PYTHON_SERVICE_ARG')
    if arg_env:
        return arg_env
    
    # 3. Fallback PC
    app_name = "fcvv"
    if os.name == 'nt':  # Windows
        base_pc = os.environ.get('APPDATA', os.path.expanduser('~'))
        path_official = os.path.join(base_pc, app_name)
        path_kivy_default = os.path.join(base_pc, "my")
        if os.path.exists(path_kivy_default) and not os.path.exists(path_official):
            return path_kivy_default
        return path_official
    else:  # Linux / macOS
        base_pc = os.path.expanduser('~')
        if sys.platform == 'darwin': # macOS
            return os.path.join(base_pc, 'Library', 'Application Support', app_name)
        return os.path.join(base_pc, '.local', 'share', app_name)

# Initialisation du chemin global
ARG_PATH = get_data_path()

# CrÃ©ation du dossier si inexistant
if not os.path.exists(ARG_PATH):
    try:
        os.makedirs(ARG_PATH, exist_ok=True)
    except:
        pass

# Fichiers de configuration
CONFIG_MONITOR = os.path.join(ARG_PATH, "service_monitor.json")
APP_CONFIG_FILE = os.path.join(ARG_PATH, "config_tournoi.yaml")
STATE_FILE = os.path.join(ARG_PATH, "last_service_state.json")
GLOBAL_STATE_FILE = os.path.join(ARG_PATH, "last_global_state.json")
DEBUG_TRIGGER = os.path.join(ARG_PATH, "debug_trigger.txt")

def send_alert(title, message):
    # --- VÃ‰RIFICATION DES PARAMÃˆTRES UTILISATEUR ---
    notifications_enabled = True
    try:
        # APP_CONFIG_FILE est votre config_cache.yaml ou config.ini
        # Si vous utilisez config.ini (Kivy default), adaptez le chemin.
        # Ici, on va lire directement lÃ  oÃ¹ l'app Ã©crit :
        
        config_path = os.path.join(ARG_PATH, "fcvv.ini") # Nom par dÃ©faut de Kivy
        
        if os.path.exists(config_path):
            cfg = configparser.ConfigParser()
            cfg.read(config_path, encoding='utf-8')
            # On rÃ©cupÃ¨re la valeur, par dÃ©faut True (1)
            notifications_enabled = cfg.getboolean('User', 'notifications', fallback=True)
    except Exception as e:
        print(f"[SERVICE] Erreur lecture config notifications: {e}")

    if not notifications_enabled:
        print(f"[SERVICE] Alerte bloquée par l'utilisateur : {title}")
        return
    
    print(f"[SERVICE] Alert: {title} - {message}")
    
    # 1. MÃ‰THODE NATIVE ANDROID
    if IS_ANDROID:
        try:
            from jnius import autoclass
            PythonService = autoclass('org.kivy.android.PythonService')
            service_context = PythonService.mService
            
            if service_context:
                Context = autoclass('android.content.Context')
                NotificationManager = autoclass('android.app.NotificationManager')
                NotificationChannel = autoclass('android.app.NotificationChannel')
                NotificationBuilder = autoclass('android.app.Notification$Builder')
                AndroidString = autoclass('java.lang.String')
                
                # Changement d'ID pour forcer la mise Ã  jour des paramÃ¨tres systÃ¨me
                channel_id = "tournoi_updates"
                notification_manager = service_context.getSystemService(Context.NOTIFICATION_SERVICE)
                
                # CrÃ©ation du Channel avec IMPORTANCE_HIGH (4) pour la banniÃ¨re descendante
                channel = NotificationChannel(channel_id, AndroidString("Alertes Tournoi"), 4)
                notification_manager.createNotificationChannel(channel)
                
                # Construction de la notification
                builder = NotificationBuilder(service_context, channel_id)
                builder.setContentTitle(AndroidString(title))
                builder.setContentText(AndroidString(message))
                builder.setSmallIcon(service_context.getApplicationInfo().icon)
                
                # ParamÃ¨tres pour forcer l'affichage prioritaire (Heads-up notification)
                builder.setPriority(1)  # PRIORITY_HIGH
                builder.setDefaults(-1) # Utilise les sons/vibrations par dÃ©faut du systÃ¨me
                
                # Envoi avec un ID unique basÃ© sur le temps
                notification_manager.notify(int(time.time()), builder.build())
                return
        except Exception as e:
            print(f"[SERVICE ERROR] Native Android failed: {e}")

    # 2. FALLBACK PLYER (PC ou Echec Android)
    if notification:
        try:
            notification.notify(
                title=title,
                message=message,
                app_name="FCVV",
                timeout=10
            )
        except Exception as e:
            print(f"[SERVICE ERROR] Plyer failed: {e}")

def check_tournament_updates(data, tournoi_nom):
    all_states = {}
    state_exists = os.path.exists(STATE_FILE)
    
    if state_exists:
        try:
            with open(STATE_FILE, 'r', encoding='utf-8') as f:
                all_states = json.load(f)
        except: pass

    # 1. Extraction du vainqueur (votre logique de dÃ©tection)
    v = data.get('vainqueur') 
    if not v:
        phases_list = data.get('phases_finales', [])
        if isinstance(phases_list, list):
            finale_tour = next((p for p in phases_list if isinstance(p, dict) and p.get("tour") == "finale"), None)
            if finale_tour and finale_tour.get("matchs"):
                v = finale_tour["matchs"][0].get("vainqueur")

    # 2. Analyse des phases finales
    pf_cfg = data.get("phases_finales_mode") or data.get("phases_finales", {})
    has_phases_finales = False
    if isinstance(pf_cfg, dict):
        has_phases_finales = pf_cfg.get("actif", False)
    elif isinstance(pf_cfg, list):
        has_phases_finales = len(pf_cfg) > 0

    matchs_poules = data.get('matchs', [])
    poules_terminees = len(matchs_poules) > 0 and all(
        m.get("SA") is not None and m.get("SB") is not None 
        for m in matchs_poules
    )

    # 3. Ã‰tats pour la comparaison
    is_new_entry = tournoi_nom not in all_states
    old_state = all_states.get(tournoi_nom, {"vainqueur": None, "phases_on": False})
    alerts = []

    # --- LOGIQUE DE FILTRAGE ---
    # Si c'est la premiÃ¨re fois qu'on voit ce tournoi :
    # ON NE NOTIFIE RIEN, on se contente d'enregistrer l'Ã©tat actuel.
    if is_new_entry:
        status_log = "TERMINEE" if v else "EN COURS"
        print(f"[SERVICE] Premier enregistrement de {tournoi_nom} (Statut: {status_log})")
    
    # Si on connaissait dÃ©jÃ  le tournoi, on compare pour notifier
    else:
        # Alerte Phases Finales (si elles viennent de s'activer)
        if has_phases_finales and poules_terminees and not old_state.get('phases_on'):
            alerts.append((f"🔥 {tournoi_nom}", "Les poules sont terminées, place aux phases finales !"))

        # Alerte Vainqueur (si le nom du vainqueur vient de changer ou d'apparaÃ®tre)
        if v and v != old_state.get('vainqueur'):
            alerts.append((f"🏆 {tournoi_nom}", f"Le tournoi est terminé ! Champion : {v}"))

    # 4. Mise Ã  jour de l'Ã©tat mÃ©moire
    all_states[tournoi_nom] = {
        "vainqueur": v, 
        "phases_on": poules_terminees if has_phases_finales else False 
    }
    
    try:
        with open(STATE_FILE, 'w', encoding='utf-8') as f:
            json.dump(all_states, f)
    except Exception as e:
        print(f"[SERVICE] Erreur sauvegarde état: {e}")
        
    return alerts

def check_global_config_updates():
    # ID de ton fichier config_cache sur Google Drive (celui qui contient la liste des tournois)
    CONFIG_FILE_ID = "14V5epxHOUIqBDHPOQpTtAIaRRyKeFRLw"
    URL_CONFIG_GLOBALE = f"https://drive.google.com/uc?export=download&id={CONFIG_FILE_ID}"
    
    current_config = {}
    
    # 1. TENTATIVE DE TÃ‰LÃ‰CHARGEMENT DE LA CONFIG FRAÃŽCHE
    try:
        # Utilisation de certifi pour SSL sur Android
        verify_param = certifi.where() if certifi else True
        r = requests.get(URL_CONFIG_GLOBALE, timeout=15, verify=VERIFY_SSL)
        r.raise_for_status()
        current_config = yaml.safe_load(r.text) or {}
        
        # On sauvegarde immÃ©diatement en local pour que l'App (UI) profite aussi de la MAJ
        with open(APP_CONFIG_FILE, 'w', encoding='utf-8') as f:
            yaml.dump(current_config, f)
            
    except Exception as e:
        print(f"[SERVICE] Impossible de fetch la config distante: {e}")
        # En cas d'Ã©chec rÃ©seau, on tente de lire le cache local existant
        if os.path.exists(APP_CONFIG_FILE):
            try:
                with open(APP_CONFIG_FILE, 'r', encoding='utf-8') as f:
                    current_config = yaml.safe_load(f) or {}
            except:
                return []
        else:
            return []

    # 2. FILTRAGE DES TOURNOIS VALIDES
    # On cherche d'abord dans la clé 'tournoi', sinon on prend à la racine (fallback)
    if "tournoi" in current_config:
        tournois_bruts = current_config.get("tournoi", {}).get("tournois", [])
    else:
        tournois_bruts = current_config.get("tournois", [])
        
    tournois_valides = []
    for t in tournois_bruts:
        annee_str = str(t.get("annee", "")).strip()
        if annee_str.isdigit():
            tournois_valides.append(t)
    
    # 3. CHARGEMENT DE L'ANCIEN Ã‰TAT (MÃ©moire du service)
    old_global_state = []
    state_exists = os.path.exists(GLOBAL_STATE_FILE)
    if state_exists:
        try:
            with open(GLOBAL_STATE_FILE, 'r', encoding='utf-8') as f:
                old_global_state = json.load(f)
        except: 
            pass

    # 4. COMPARAISON ET GÃ‰NÃ‰RATION DES ALERTES
    alerts = []
    current_keys = [f"{t.get('nom')} {t.get('annee')}" for t in tournois_valides]
    
    # On n'alerte que si le fichier d'Ã©tat existait dÃ©jÃ  (Ã©vite le spam au premier lancement)
    if state_exists:
        for key in current_keys:
            if key not in old_global_state:
                alerts.append(("ðŸ†• Nouveau Tournoi !", f"Le tournoi {key} est maintenant disponible !"))

    # 5. SAUVEGARDE DU NOUVEL Ã‰TAT
    try:
        with open(GLOBAL_STATE_FILE, 'w', encoding='utf-8') as f:
            json.dump(current_keys, f)
    except Exception as e:
        print(f"[SERVICE] Erreur sauvegarde global state: {e}")
    
    return alerts

def run_service():
    # --- CONFIGURATION FOREGROUND (Obligatoire Android 14 / API 34) ---
    if IS_ANDROID:
        try:
            from jnius import autoclass
            PythonService = autoclass('org.kivy.android.PythonService')
            service_context = PythonService.mService
            if service_context:
                NotificationBuilder = autoclass('android.app.Notification$Builder')
                AndroidString = autoclass('java.lang.String')
                channel_id = "service_monitor_permanent"
                
                Context = autoclass('android.content.Context')
                NotificationManager = autoclass('android.app.NotificationManager')
                NotificationChannel = autoclass('android.app.NotificationChannel')
                nm = service_context.getSystemService(Context.NOTIFICATION_SERVICE)
                chan = NotificationChannel(channel_id, AndroidString("Service de mise à jour"), 2)
                nm.createNotificationChannel(chan)
                
                builder = NotificationBuilder(service_context, channel_id)
                builder.setContentTitle(AndroidString("Tournoi de Vercel"))
                builder.setContentText(AndroidString("Suivi des matchs en direct"))
                builder.setSmallIcon(service_context.getApplicationInfo().icon)
                
                service_context.startForeground(1, builder.build())
                print("[SERVICE] Foreground mode activé.")
        except Exception as e:
            print(f"[SERVICE] Erreur Foreground: {e}")

    time.sleep(5)
    print(f"[SERVICE] Lancement surveillance dans : {ARG_PATH}")
    
    while True:
        url = None
        nom = "Tournoi"
        
        try:
            # 0. DEBUG
            if os.path.exists(DEBUG_TRIGGER):
                send_alert("🛠️ Test", "Service actif !")
                try: os.remove(DEBUG_TRIGGER)
                except: pass

            # 1. CONFIG GLOBALE
            for title, msg in check_global_config_updates():
                send_alert(title, msg)

            # 2. LECTURE CONFIG MONITOR
            if os.path.exists(CONFIG_MONITOR):
                try:
                    with open(CONFIG_MONITOR, 'r', encoding='utf-8') as f:
                        config = json.load(f)
                    url = config.get("url")
                    nom = config.get("nom", "Tournoi")
                except:
                    url = None

            # 3. RÃ‰SEAU
            if url:
                try:
                    # ParamÃ¨tres par dÃ©faut
                    verify_param = certifi.where() if certifi else True
                    
                    # --- PATCH SPECIAL WINDOWS / FIREWALL ---
                    if not IS_ANDROID and os.name == 'nt':
                        # Si on est sur Windows, on tente avec vÃ©rification, 
                        # sinon on bypass si le pare-feu bloque
                        try:
                            r = requests.get(url, timeout=15, verify=verify_param)
                        except requests.exceptions.SSLError:
                            # DÃ©sactive les warnings SSL dans la console
                            import urllib3
                            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
                            # Tentative sans vÃ©rification
                            r = requests.get(url, timeout=15, verify=False)
                    else:
                        # Comportement normal (Android ou autre)
                        r = requests.get(url, timeout=15, verify=verify_param)
                    # ----------------------------------------

                    r.raise_for_status()
                    content = r.text.strip()
                    
                    if url.endswith('.json') or content.startswith('{'):
                        data = r.json()
                    else:
                        data = yaml.safe_load(content)
                    
                    if data:
                        for title, msg in check_tournament_updates(data, nom):
                            send_alert(title, msg)
                            
                except Exception as net_e:
                    # Formatage plus court pour les logs si c'est une erreur commune
                    err_msg = str(net_e).split(')')[0] if 'SSL' in str(net_e) else str(net_e)
                    print(f"[SERVICE] Erreur réseau : {err_msg}")

        except Exception as e:
            print(f"[SERVICE LOOP ERROR] : {e}")
        
        time.sleep(60)

if __name__ == '__main__':
    run_service()