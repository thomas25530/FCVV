# -*- coding: utf-8 -*-
import socket
import threading
import os
import glob
import hashlib
import hmac
from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.spinner import Spinner
from kivy.uix.button import Button
from kivy.uix.switch import Switch
from kivy.uix.slider import Slider
from kivy.uix.scrollview import ScrollView
from kivy.graphics import Color, Rectangle
from kivy.app import App
from kivy.clock import Clock
from kivy.metrics import dp, sp
from kivy.graphics.context_instructions import PushMatrix, PopMatrix, Scale
from kivy.uix.textinput import TextInput

def hash_password(password: str) -> str:
    """ Encode le mot de passe en SHA-256 """
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

def check_internet(host="8.8.8.8", port=80, timeout=3):
    try:
        socket.setdefaulttimeout(timeout)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
        return True
    except Exception:
        try:
            host_fallback = "google.com"
            socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host_fallback, port))
            return True
        except Exception:
            return False

class SettingsScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        app = App.get_running_app()
        self.is_apk = getattr(app, 'generate_APK', True) 
        
        self.KIVY_BLUE = (30/255, 58/255, 138/255, 1)
        self.ACCENT_YELLOW = (247/255, 236/255, 63/255, 1)
        
        with self.canvas.before:
            Color(*self.KIVY_BLUE)
            self.rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._update_rect, size=self._update_rect)

        self.scroll = ScrollView(do_scroll_x=False)
        self.add_widget(self.scroll)
        self.refresh_settings_layout()

    def _update_rect(self, instance, value):
        self.rect.pos = instance.pos
        self.rect.size = instance.size

    def refresh_settings_layout(self):
        app = App.get_running_app()
        tr = app._ if hasattr(app, '_') else lambda x: x

        def res_d(val): return dp(val)
        def res_s(val): return sp(val)

        h_row = res_d(95)           
        h_row_tall = res_d(120)    
        h_btn = res_d(75)          
        f_title = res_s(24)        
        f_text = res_s(20)         
        f_small = res_s(16)        

        # Récupération config
        current_font = 20
        current_refresh = 5
        current_dark_mode = False
        current_lang = "Français"
        
        if hasattr(app, 'config') and app.config.has_section('User'):
            current_font = int(app.config.get('User', 'font_size_factor', fallback=20))
            current_refresh = int(app.config.get('User', 'refresh_interval', fallback=5))
            current_dark_mode = app.config.getboolean('User', 'dark_mode')
            current_lang = app.config.get('User', 'langue', fallback="Français")

        self.scroll.clear_widgets()
        
        padding_val = res_d(25)
        self.main_layout = BoxLayout(
            orientation='vertical', 
            padding=[padding_val, padding_val, padding_val, res_d(60)], 
            spacing=res_d(25), 
            size_hint_y=None
        )
        self.main_layout.bind(minimum_height=self.main_layout.setter('height'))
        
        self.add_section_title(tr("display").upper(), f_title, res_d(60))
        
        #=======================================================================
        # # --- SECTION 1 : LANGUE ET AFFICHAGE ---
        # self.add_section_title(tr("display").upper(), f_title, res_d(60))
        # 
        # # AJOUT DU SPINNER (Celui qui manquait !)
        # self.lang_spinner = Spinner(
        #     text=current_lang,
        #     values=('Français', 'English', 'Español'),
        #     size_hint=(None, None),
        #     size=(res_d(180), res_d(60)),
        #     font_size=f_small
        # )
        # self.lang_spinner.bind(text=self.on_language_change)
        # self.main_layout.add_widget(self.create_setting_row(tr("language"), self.lang_spinner, h_row, f_text))
        #=======================================================================

        # SWITCH DARK MODE
        dark_switch = Switch(active=current_dark_mode, size_hint=(None, None), size=(res_d(120), res_d(60)))
        with dark_switch.canvas.before:
            PushMatrix()
            dark_switch.scale_instr = Scale(1.5, 1.5, 1) 
        with dark_switch.canvas.after:
            PopMatrix()
        dark_switch.bind(pos=lambda inst, v: setattr(inst.scale_instr, 'origin', inst.center))
        dark_switch.bind(active=self.on_dark_mode_toggle)
        self.main_layout.add_widget(self.create_setting_row(tr("dark_mode"), dark_switch, h_row, f_text))

        # SLIDER TAILLE POLICE
        font_slider = Slider(min=12, max=30, value=current_font, step=1, cursor_size=(res_d(35), res_d(35)))
        self.font_value_label = Label(text=str(int(current_font)), font_size=f_small, color=self.ACCENT_YELLOW)
        font_slider.bind(value=self.update_font_label_and_config)
        font_cont = BoxLayout(orientation='vertical', spacing=res_d(5))
        font_cont.add_widget(font_slider)
        font_cont.add_widget(self.font_value_label)
        self.main_layout.add_widget(self.create_setting_row(tr("font_size"), font_cont, h_row_tall, f_text))

        # --- SECTION 2 : AUTOMATISATION ---
        self.add_section_title(tr("automation").upper(), f_title, res_d(60))
        refresh_slider = Slider(min=1, max=15, value=current_refresh, step=1, cursor_size=(res_d(35), res_d(35)))
        self.refresh_value_label = Label(text=f"{int(current_refresh)} min", font_size=f_small, color=self.ACCENT_YELLOW)
        refresh_slider.bind(value=self.update_refresh_label_and_config)
        refresh_cont = BoxLayout(orientation='vertical', spacing=res_d(5))
        refresh_cont.add_widget(refresh_slider)
        refresh_cont.add_widget(self.refresh_value_label)
        self.main_layout.add_widget(self.create_setting_row(tr("refresh_rate"), refresh_cont, h_row_tall, f_text))

        # --- SECTION 3 : STOCKAGE ET RESET ---
        self.add_section_title(tr("sync").upper(), f_title, res_d(60))
        btn_cache = Button(text=tr("cache"), background_color=(0.8, 0.3, 0.3, 1), 
                           size_hint_y=None, height=h_btn, font_size=f_text, bold=True)
        btn_cache.bind(on_release=self.clear_local_cache)
        self.main_layout.add_widget(btn_cache)

        self.cache_label = Label(text=f"{tr('cache_size_label')} : [b]{self.get_cache_size()}[/b]",
                                markup=True, font_size=f_small, color=(0.8, 0.8, 0.8, 1),
                                size_hint_y=None, height=res_d(40))
        self.main_layout.add_widget(self.cache_label)
        
        self.conn_label = Label(text=f"{tr('conn_state')} : [color=FFFF00]...[/color]", 
                                markup=True, size_hint_y=None, height=res_d(40), font_size=f_small)
        self.main_layout.add_widget(self.conn_label)
        
        btn_reset = Button(text=tr("reset_btn"), size_hint_y=None, height=h_btn, font_size=f_text,
                           background_color=(0.7, 0.7, 0.7, 1), bold=True)
        btn_reset.bind(on_release=self.confirm_reset)
        self.main_layout.add_widget(btn_reset)

        # SECTION ADMIN (Cachée par défaut)
        self.admin_layout = BoxLayout(orientation='vertical', spacing=res_d(15), size_hint_y=None, height=0, opacity=0, disabled=True)
        self.admin_title = Label(text="ADMIN", font_size=f_title, color=self.ACCENT_YELLOW, bold=True, 
                                 size_hint_y=None, height=res_d(60), halign='left', valign='bottom')
        self.admin_title.bind(size=lambda l, s: setattr(l, 'text_size', (s[0], None)))
        self.admin_row = BoxLayout(orientation='horizontal', size_hint_y=None, height=h_btn, spacing=res_d(10))
        self.debug_input = TextInput(hint_text="Password", password=True, multiline=False, size_hint_x=0.7,
                                    font_size=f_text, padding=[res_d(10), (h_btn - f_text)/4])
        btn_ok = Button(text="OK", size_hint_x=0.3, background_color=(0.2, 0.6, 0.2, 1), bold=True)
        btn_ok.bind(on_release=lambda x: self.on_debug_password_entered(self.debug_input))
        self.admin_row.add_widget(self.debug_input)
        self.admin_row.add_widget(btn_ok)
        self.admin_layout.add_widget(self.admin_title)
        self.admin_layout.add_widget(self.admin_row)
        self.main_layout.add_widget(self.admin_layout)

        self.scroll.add_widget(self.main_layout)

    def on_notifications_toggle(self, switch, value):
        app = App.get_running_app()
        if hasattr(app, 'config'):
            # On stocke '1' pour True, '0' pour False
            app.config.set('User', 'notifications', '1' if value else '0')
            app.config.write()
            print(f"Notifications : {'Activées' if value else 'Désactivées'}")

    def update_cache_display(self):
        if hasattr(self, 'cache_label'):
            prefix = self.app_tr('cache_size_label')
            # On appelle get_cache_size() qui va reparcourir le dossier /save et les autres
            size_str = self.get_cache_size() 
            self.cache_label.text = f"{prefix} : [b]{size_str}[/b]"

    
        
    def check_debug_conditions(self, *args):
        """ Vérifie si les conditions secrètes sont remplies """
        app = App.get_running_app()
        
        # Récupération des valeurs actuelles
        try:
            is_english = self.lang_spinner.text == 'English'
            # On cherche les sliders dans le layout (ou on stocke les refs au début)
            # Ici, on va vérifier via la config pour plus de fiabilité
            is_dark = app.config.getboolean('User', 'dark_mode')
            font_val = int(app.config.get('User', 'font_size_factor'))
            refresh_val = int(app.config.get('User', 'refresh_interval'))
            
            # Conditions : English + Dark + Font Max (30) + Refresh Max (15)
            if is_english and is_dark and font_val == 30 and refresh_val == 15:
                self.show_debug_field(True)
            else:
                self.show_debug_field(False)
        except Exception as e:
            print(f"Debug check error: {e}")

    def show_debug_field(self, show=True):
        if show:
            self.admin_layout.opacity = 1
            self.admin_layout.disabled = False
            self.admin_layout.height = dp(140) # Hauteur titre + row + spacing
        else:
            self.admin_layout.opacity = 0
            self.admin_layout.disabled = True
            self.admin_layout.height = 0
            self.debug_input.text = ""

    def on_debug_password_entered(self, instance):
        app = App.get_running_app()
        password = instance.text.strip()
        
        if not password:
            return

        stored_hash = getattr(app, "_app_password_hash", "")
        input_hash = hashlib.sha256(password.encode("utf-8")).hexdigest()

        if hmac.compare_digest(input_hash, stored_hash):
            # --- AJOUT CRUCIAL : ACTIVER LE MODE DEBUG DANS L'APP ---
            app.debug_mode = True  
            print(">>> DEBUG MODE ACTIVÉ <<<")
            
            instance.background_color = (0, 1, 0, 1) 
            
            # Optionnel : Reset des paramètres config (ton code actuel)
            if hasattr(app, 'config'):
                app.config.set('User', 'langue', 'Français')
                app.config.set('User', 'dark_mode', '0')
                app.config.set('User', 'font_size_factor', '20')
                app.config.set('User', 'refresh_interval', '5')
                app.config.write()

            self.refresh_settings_layout()
            
            # On informe l'utilisateur que c'est validé (changement de hint_text par ex)
            instance.text = ""
            instance.hint_text = "MODE ADMIN ACTIF"
            
            # Relancer le test réseau
            if hasattr(self, 'conn_label'):
                self.conn_label.text = f"{self.app_tr('conn_state')} : [color=FFFF00]...[/color]"
                self.update_network_status(None)

            if hasattr(app, 'refresh_ui_theme'):
                app.refresh_ui_theme()
        else:
            # Code en cas d'échec (déjà correct dans ton script)
            app.debug_mode = False # Sécurité
            instance.text = ""
            instance.hint_text = "Refusé"
            instance.background_color = (1, 0, 0, 0.5)
            Clock.schedule_once(lambda dt: setattr(instance, 'background_color', (1, 1, 1, 1)), 1)

    def finish_reset_ui(self, instance):
        """ Appelé à la fin du nettoyage des fichiers par le thread de reset """
        app = App.get_running_app()
        
        # 1. Appliquer le thème (couleurs, polices) au cas où le Dark Mode a changé
        if hasattr(app, 'refresh_ui_theme'):
            app.refresh_ui_theme()
        
        # 2. Reconstruire tout le layout visuel pour refléter les réglages d'origine
        self.refresh_settings_layout()
        
        # 3. LANCER LE TEST RÉSEAU À LA FIN DE LA RÉINITIALISATION
        if hasattr(self, 'conn_label'):
            tr = self.app_tr('conn_state')
            # On affiche l'état de chargement
            self.conn_label.text = f"{tr} : [color=FFFF00]...[/color]"
            # On déclenche le test (le thread mettra à jour le label à la fin)
            self.update_network_status(None)
        
        # 4. Message visuel de succès sur le bouton
        instance.text = "Système d'origine rétabli !"
        instance.background_color = (0.2, 0.7, 0.2, 1) # Vert succès
        
        # 5. On réactive le bouton et remet son texte initial après 3 secondes
        Clock.schedule_once(lambda dt: self._reset_btn_ui(instance, self.app_tr("reset_btn")), 3)

    def on_enter(self):
        # 1. Mise à jour de la taille du cache
        self.update_cache_display()
        
        # 2. Relancer SYSTÉMATIQUEMENT le test de connexion
        if hasattr(self, 'conn_label'):
            tr = self.app_tr('conn_state')
            # On remet l'indicateur visuel d'attente
            self.conn_label.text = f"{tr} : [color=FFFF00]...[/color]"
            # On lance le test avec un léger délai pour la fluidité de l'UI
            Clock.schedule_once(self.update_network_status, 0.2)

    # --- HELPERS ---
    def create_setting_row(self, label_text, widget, row_height, font_sz):
        row = BoxLayout(orientation='horizontal', size_hint_y=None, height=row_height)
        lbl = Label(text=label_text, halign='left', valign='middle', font_size=font_sz)
        lbl.bind(size=lambda l, s: setattr(l, 'text_size', (s[0], s[1])))
        row.add_widget(lbl)
        
        # On donne un peu plus de largeur au container pour le switch agrandi
        container = BoxLayout(size_hint_x=None, width=dp(220), padding=[0, dp(10)])
        container.add_widget(widget)
        row.add_widget(container)
        return row

    def add_section_title(self, title, font_sz, h):
        lbl = Label(text=title, font_size=font_sz, color=self.ACCENT_YELLOW, bold=True, 
                    size_hint_y=None, height=h, halign='left', valign='bottom')
        lbl.bind(size=lambda l, s: setattr(l, 'text_size', (s[0], None)))
        self.main_layout.add_widget(lbl)

    def app_tr(self, key):
        app = App.get_running_app()
        return app._(key) if hasattr(app, '_') else key

    def get_cache_size(self):
        app = App.get_running_app()
        target_dir = os.path.abspath(app.user_data_dir)
        total_size = 0
        
        if os.path.exists(target_dir):
            for dirpath, _, filenames in os.walk(target_dir):
                for f in filenames:
                    # ON UTILISE LA MÊME LOGIQUE QUE POUR LE NETTOYAGE
                    if self.is_cache_file(f): 
                        full_path = os.path.join(dirpath, f)
                        try:
                            total_size += os.path.getsize(full_path)
                        except OSError:
                            continue
        
        if total_size <= 0: return "0 octet"
        elif total_size < 1024: return f"{total_size} octets"
        elif total_size < 1024**2: return f"{total_size / 1024:.2f} KB"
        else: return f"{total_size / (1024**2):.2f} MB"

    def is_cache_file(self, filename):
        """ Logique étendue pour identifier les fichiers temporaires et caches """
        fl = filename.lower()
        
        # 1. On NE touche PAS au .ini (Configuration vitale de l'app)
        if fl.endswith('.ini'):
            return False
            
        return (
            # Fichiers de données tournois
            (fl.startswith('tournoi_') and fl.endswith(('.json', '.yaml'))) or
            # Fichiers de configuration téléchargés
            fl in ['config_cache.yaml', 'config_tournoi.yaml', 'config_fcvv.yaml'] or
            # Images de sponsors ou images dynamiques (png, jpg, jpeg)
            (fl.startswith('sponsor_') and fl.endswith(('.png', '.jpg', '.jpeg'))) or
            (fl.startswith('img_') and fl.endswith(('.png', '.jpg', '.jpeg')))
        )

    def update_network_status(self, dt):
        def worker():
            is_online = check_internet()
            Clock.schedule_once(lambda dt: self.finish_network_update(is_online))
        threading.Thread(target=worker, daemon=True).start()

    def finish_network_update(self, is_online):
        # Sécurité : on vérifie si l'écran est toujours actif ou si le label existe
        if hasattr(self, 'conn_label') and self.conn_label:
            tr_state = self.app_tr('conn_state')
            color = "00FF00" if is_online else "FF0000"
            status = "OK" if is_online else "OFFLINE"
            self.conn_label.text = f"{tr_state} : [color={color}]{status}[/color]"

    def clear_local_cache(self, instance):
        app = App.get_running_app()
        target_dir = app.user_data_dir
        files_deleted = 0
        
        # Désactivation temporaire du bouton pour éviter le spam pendant le nettoyage
        instance.disabled = True

        if os.path.exists(target_dir):
            for dirpath, _, filenames in os.walk(target_dir):
                for f in filenames:
                    # On utilise la règle de filtrage commune
                    if self.is_cache_file(f):
                        try:
                            os.remove(os.path.join(dirpath, f))
                            files_deleted += 1
                        except Exception as e:
                            print(f"Erreur suppression {f}: {e}")

        # Reconstruction du cache en arrière-plan
        if hasattr(app, 'load_remote_config'):
            threading.Thread(target=app.load_remote_config, daemon=True).start()

        # Mise à jour de l'UI
        if files_deleted > 0:
            instance.text = f"Vidé ({files_deleted} f.)"
            # On force la mise à jour du label de taille (qui affichera 0 octet car même filtre)
            self.update_cache_display()
        else:
            instance.text = "Déjà vide"
            
        # On rétablit le bouton après 2 secondes
        Clock.schedule_once(lambda dt: self._reset_btn_ui(instance, self.app_tr("cache")), 2)

    def confirm_reset(self, instance):
        # LOGS DE DIAGNOSTIC CRITIQUES
        print("\n" + "="*30)
        print("CLIC BOUTON REINITIALISER DETECTE")
        print("="*30 + "\n")
        
        app = App.get_running_app()
        
        # Désactivation immédiate pour éviter les clics multiples
        instance.disabled = True
        instance.text = "PATIENTEZ..."
        
        # On force un rafraîchissement graphique Kivy avant de lancer le thread
        Clock.schedule_once(lambda dt: self._start_reset_safe(instance), 0.1)

    def _start_reset_safe(self, instance):
        print("Lancement du Thread de nettoyage...")
        t = threading.Thread(target=self._perform_reset_logic, args=(instance,))
        t.daemon = True
        t.start()

    def _perform_reset_logic(self, instance):
        app = App.get_running_app()
        print("Thread : Début de la purge des fichiers et reset config...")
        
        try:
            # 1. Reset Config (Valeurs d'usine)
            if hasattr(app, 'config'):
                app.config.set('User', 'font_size_factor', '24')
                app.config.set('User', 'refresh_interval', '5')
                app.config.set('User', 'dark_mode', '0')
                app.config.set('User', 'langue', 'Français')
                app.config.write()
                print("Thread : Config réinitialisée.")

            # 2. Reset Fichiers (Utilisation du filtre commun)
            data_dir = app.user_data_dir
            count = 0
            if os.path.exists(data_dir):
                # On utilise os.listdir ou os.walk selon ton besoin de profondeur
                for f in os.listdir(data_dir):
                    if self.is_cache_file(f):  # COHÉRENCE TOTALE ICI
                        try:
                            os.remove(os.path.join(data_dir, f))
                            count += 1
                        except Exception as e:
                            print(f"Thread : Erreur suppression {f}: {e}")
                print(f"Thread : {count} fichiers de cache supprimés.")

            # 3. Reload (Rechargement des données fraîches)
            if hasattr(app, 'load_remote_config'):
                print("Thread : Appel de load_remote_config...")
                app.load_remote_config()

            print("Thread : Fin des opérations, retour à l'UI.")
            
            # 4. Mise à jour de l'UI (via le thread principal)
            def update_ui_after_reset(dt):
                self.update_cache_display() # Affichera 0 car on a utilisé le même filtre
                self.finish_reset_ui(instance)
            
            Clock.schedule_once(update_ui_after_reset, 0.1)
            
        except Exception as e:
            print(f"ERREUR DANS LE THREAD RESET : {e}")
            Clock.schedule_once(lambda dt: self._reset_btn_ui(instance, "Erreur Fatale"), 0.1)

    

    def _reset_btn_ui(self, btn, original_text):
        btn.text = original_text
        btn.disabled = False

    def update_refresh_label_and_config(self, instance, value):
        new_val = int(value)
        self.refresh_value_label.text = f"{new_val} min"
        app = App.get_running_app()
        
        if hasattr(app, 'config'):
            app.config.set('User', 'refresh_interval', str(new_val))
            app.config.write()

        # --- LE MAILLON MANQUANT ---
        # On cherche l'écran 'soirees' pour rafraîchir son timer immédiatement
        try:
            # On accède au ScreenManager (souvent app.root ou app.root.sm)
            sm = app.root if hasattr(app.root, 'get_screen') else app.root.sm
            if sm.has_screen('soirees'):
                soirees_screen = sm.get_screen('soirees')
                # On appelle la fonction de reset du timer (qu'on va créer dans SoireesScreen)
                if hasattr(soirees_screen, 'setup_auto_refresh'):
                    soirees_screen.setup_auto_refresh()
        except Exception as e:
            print(f"Erreur de notification du timer : {e}")
        
        self.check_debug_conditions()

    def on_language_change(self, spinner, text):
        app = App.get_running_app()
        if hasattr(app, 'config'):
            app.config.set('User', 'langue', text)
            app.config.write()
            if hasattr(app, 'refresh_ui_theme'): app.refresh_ui_theme()
            self.refresh_settings_layout()

    def update_font_label_and_config(self, instance, value):
        self.font_value_label.text = str(int(value))
        app = App.get_running_app()
        if hasattr(app, 'config'):
            app.config.set('User', 'font_size_factor', str(int(value)))
            app.config.write()
            
            # --- AJOUT POUR RECONSTRUIRE LE MENU ---
            if app.root:
                # On dit au RootLayout que le menu n'est plus à jour
                app.root.menu_built = False 
            
            if hasattr(app, 'refresh_ui_theme'): 
                app.refresh_ui_theme()
                
        self.check_debug_conditions()

    def on_dark_mode_toggle(self, switch, value):
        app = App.get_running_app()
        if hasattr(app, 'config'):
            app.config.set('User', 'dark_mode', '1' if value else '0')
            app.config.write()
            
            # --- AJOUT POUR RECONSTRUIRE LE MENU ---
            if app.root:
                app.root.menu_built = False
                
            if hasattr(app, 'refresh_ui_theme'): 
                app.refresh_ui_theme()
        self.check_debug_conditions()