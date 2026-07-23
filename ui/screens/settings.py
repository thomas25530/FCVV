# -*- coding: utf-8 -*-
import socket
import threading
import os
from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.switch import Switch
from kivy.uix.slider import Slider
from kivy.uix.scrollview import ScrollView
from kivy.graphics import Color, Rectangle
from kivy.app import App
from kivy.clock import Clock
from kivy.metrics import dp, sp
from kivy.graphics.context_instructions import PushMatrix, PopMatrix, Scale

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
        self.KIVY_BLUE = (30/255, 58/255, 138/255, 1)
        self.ACCENT_YELLOW = (247/255, 236/255, 63/255, 1)
        self.main_layout = None
        self.font_value_label = None
        self.refresh_value_label = None
        self.news_period_label = None
        self.cache_label = None
        self.conn_label = None
        with self.canvas.before:
            Color(*self.KIVY_BLUE)
            self.rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._update_rect, size=self._update_rect)
        self.scroll = ScrollView(do_scroll_x=False, bar_width=0)
        self.scroll.scroll_timeout = 250
        self.scroll.scroll_distance = dp(8)
        self.add_widget(self.scroll)
        self.refresh_settings_layout()

    def _update_rect(self, instance, value):
        self.rect.pos = instance.pos
        self.rect.size = instance.size

    def _update_switch_scale(self, instance, value):
        if hasattr(instance, 'scale_instr'):
            instance.scale_instr.origin = instance.center

    def _update_label_size_limit(self, instance, value):
        instance.text_size = (value[0], None)

    def _update_setting_row_label(self, instance, value):
        instance.text_size = (value[0], value[1])

    def _cleanup_layout(self):
        if self.main_layout:
            for child in list(self.main_layout.children):
                child.unbind()
                if isinstance(child, BoxLayout):
                    for sub_child in list(child.children):
                        sub_child.unbind()
            self.main_layout.unbind()

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
        
        current_font = 24
        current_refresh = 5
        current_news_period = 15
        current_dark_mode = False
        if hasattr(app, 'config') and app.config.has_section('User'):
            current_font = int(app.config.get('User', 'font_size_factor', fallback=24))
            current_refresh = int(app.config.get('User', 'refresh_interval', fallback=5))
            current_news_period = int(app.config.get('User', 'news_period', fallback=15))
            current_dark_mode = app.config.getboolean('User', 'dark_mode')
            
        self._cleanup_layout()
        self.scroll.clear_widgets()
        padding_val = res_d(25)
        self.main_layout = BoxLayout(orientation='vertical', padding=[padding_val, padding_val, padding_val, res_d(60)], spacing=res_d(25), size_hint_y=None)
        self.main_layout.bind(minimum_height=self.main_layout.setter('height'))
        
        # DISPLAY
        self.add_section_title(tr("display").upper(), f_title, res_d(60))
        dark_switch = Switch(active=current_dark_mode, size_hint=(None, None), size=(res_d(120), res_d(60)))
        dark_switch.bind(active=self.on_dark_mode_toggle)
        self.main_layout.add_widget(self.create_setting_row(tr("dark_mode"), dark_switch, h_row, f_text))
        
        # SLIDER TAILLE POLICE
        font_slider = Slider(
            min=12, max=30, value=current_font, step=1, 
            # Curseur plus gros
            cursor_size=(dp(50), dp(50)), 
            # Padding pour que la zone de toucher autour du curseur soit plus grande
            padding=dp(20) 
        )
        self.font_value_label = Label(text=str(int(current_font)), font_size=f_small, color=self.ACCENT_YELLOW)
        font_slider.bind(value=self.update_font_label_and_config)
        font_cont = BoxLayout(orientation='vertical', spacing=res_d(5))
        font_cont.add_widget(font_slider)
        font_cont.add_widget(self.font_value_label)
        self.main_layout.add_widget(self.create_setting_row(tr("font_size"), font_cont, h_row_tall, f_text))
        
        # ACCÈS VESTIAIRES
        self.add_section_title("ACCÈS VESTIAIRES", f_title, res_d(60))
        btn_conn = Button(
            text="Ajouter un nouvel accès", 
            size_hint_y=None, 
            height=h_btn, 
            font_size=f_text,  # Utilise la taille f_text définie dans votre méthode
            bold=True,         # Ajout du gras pour la lisibilité
            background_color=(0, 0.7, 0, 1)
        )
        btn_conn.bind(on_release=self.go_to_login)
        self.main_layout.add_widget(btn_conn)
        
        authorized = app.authorized_vestiaires if hasattr(app, 'authorized_vestiaires') else []
        if authorized:
            for cat in authorized:
                row = BoxLayout(orientation='horizontal', size_hint_y=None, height=h_btn, spacing=dp(10))
                row.add_widget(Label(text=f"• {cat}", font_size=f_text, halign='left'))
                btn_del = Button(text="Supprimer", size_hint_x=0.4, background_color=(0.8, 0.2, 0.2, 1))
                btn_del.bind(on_release=lambda x, c=cat: self.remove_vestiaire_access(c))
                row.add_widget(btn_del)
                self.main_layout.add_widget(row)
        else:
            self.main_layout.add_widget(Label(text="Aucun accès enregistré.", font_size=f_small, italic=True))
        # --- SECTION 2 : AUTOMATISATION ---
        self.add_section_title(tr("automation").upper(), f_title, res_d(60))
        # Fréquence de rafraîchissement
        refresh_slider = Slider(min=1, max=15, value=current_refresh, step=1, cursor_size=(dp(50), dp(50)), 
            # Padding pour que la zone de toucher autour du curseur soit plus grande
            padding=dp(20) 
        )
        self.refresh_value_label = Label(text=f"{int(current_refresh)} min", font_size=f_small, color=self.ACCENT_YELLOW)
        refresh_slider.bind(value=self.update_refresh_label_and_config)
        refresh_cont = BoxLayout(orientation='vertical', spacing=res_d(5))
        refresh_cont.add_widget(refresh_slider)
        refresh_cont.add_widget(self.refresh_value_label)
        self.main_layout.add_widget(self.create_setting_row(tr("refresh_rate"), refresh_cont, h_row_tall, f_text))
        # AJOUT : Période de validité des actualités (Affichage d'actu)
        news_period_slider = Slider(min=1, max=60, value=current_news_period, step=1, cursor_size=(dp(50), dp(50)), 
            # Padding pour que la zone de toucher autour du curseur soit plus grande
            padding=dp(20) 
        )
        self.news_period_label = Label(text=f"{int(current_news_period)} jours", font_size=f_small, color=self.ACCENT_YELLOW)
        news_period_slider.bind(value=self.update_news_period_label_and_config)
        news_period_cont = BoxLayout(orientation='vertical', spacing=res_d(5))
        news_period_cont.add_widget(news_period_slider)
        news_period_cont.add_widget(self.news_period_label)
        self.main_layout.add_widget(self.create_setting_row(tr("Affichage actus"), news_period_cont, h_row_tall, f_text))
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
        btn_reset = Button(
            text=tr("reset_btn"),
            size_hint_y=None,
            height=h_btn,
            font_size=f_text,
            background_color=(0.7, 0.7, 0.7, 1),
            bold=True
        )
        btn_reset.bind(on_release=self.confirm_reset)
        self.main_layout.add_widget(btn_reset)
        self.scroll.add_widget(self.main_layout)
        
    def go_to_login(self, *args):
        # AU LIEU DE : app.root.sm.current = 'login_vestiaire'
        
        # UTILISEZ :
        app = App.get_running_app()
        if app.root:
            app.root.switch_screen('login_vestiaire')

    def remove_vestiaire_access(self, category):
        app = App.get_running_app()
        if hasattr(app, 'authorized_vestiaires') and category in app.authorized_vestiaires:
            
            # 1. Sauvegarde de l'état AVANT suppression pour la comparaison FCM
            anciennes_categories = list(app.authorized_vestiaires)
            
            # 2. Mise à jour de la mémoire RAM
            app.authorized_vestiaires.remove(category)
            
            # 3. Gestion réseau (Désabonnement FCM)
            # On passe les deux listes pour permettre la comparaison dans _execute_fcm_subscription
            if hasattr(app, 'gerer_abonnements_fcm'):
                # Note: Assurez-vous que gerer_abonnements_fcm accepte maintenant 2 arguments
                app.gerer_abonnements_fcm(app.authorized_vestiaires, anciennes_categories)
            
            # 4. Mise à jour de la persistance (Fichier .ini)
            if hasattr(app, 'config'):
                new_list_str = ','.join(app.authorized_vestiaires)
                app.config.set('User', 'authorized_list', new_list_str)
                app.config.write()
            
            # 5. Rafraîchissement UI
            self.refresh_settings_layout()
            
            # 6. Rafraîchissement de l'écran Home
            if app.root and hasattr(app.root, 'sm') and app.root.sm.has_screen('home'):
                home = app.root.sm.get_screen('home')
                if hasattr(home, 'update_ui'):
                    home.update_ui()
            
    def on_pre_enter(self):
        """
        Appelé automatiquement chaque fois que l'écran est affiché.
        Cela garantit que la liste des accès est rafraîchie à chaque retour.
        """
        self.refresh_settings_layout()

    def update_news_period_label_and_config(self, instance, value):
        """AJOUT : Callback de modification de la plage temporelle des actualités"""
        new_val = int(value)
        if self.news_period_label:
            self.news_period_label.text = f"{new_val} jours"
        app = App.get_running_app()
        if hasattr(app, 'config'):
            app.config.set('User', 'news_period', str(new_val))
            app.config.write()
        # Commande la mise à jour immédiate du HomeScreen s'il est chargé
        if app.root and hasattr(app.root, 'sm'):
            if app.root.sm.has_screen('home'):
                home = app.root.sm.get_screen('home')
                if hasattr(home, 'update_ui_from_config'):
                    home.update_ui_from_config()

    def update_cache_display(self):
        if hasattr(self, 'cache_label') and self.cache_label:
            prefix = self.app_tr('cache_size_label')
            size_str = self.get_cache_size() 
            self.cache_label.text = f"{prefix} : [b]{size_str}[/b]"

    def on_enter(self):
        # 1. Met à jour le cache (si la méthode existe)
        if hasattr(self, 'update_cache_display'):
            self.update_cache_display()
        
        # 2. Vérification sécurisée : on ne touche à conn_label que s'il est initialisé
        if getattr(self, 'conn_label', None) is not None:
            tr = self.app_tr('conn_state')
            self.conn_label.text = f"{tr} : [color=FFFF00]...[/color]"
            Clock.schedule_once(self.update_network_status, 0.2)
        else:
            # Optionnel : forcer la reconstruction si le layout est vide
            # Cela garantit que les composants sont créés
            self.refresh_settings_layout()
            # On ré-essaie après reconstruction
            if self.conn_label:
                tr = self.app_tr('conn_state')
                self.conn_label.text = f"{tr} : [color=FFFF00]...[/color]"
                Clock.schedule_once(self.update_network_status, 0.2)

    def create_setting_row(self, label_text, widget, row_height, font_sz):
        row = BoxLayout(
            orientation='horizontal',
            size_hint_y=None,
            height=row_height,
            spacing=dp(15),
            padding=[0, dp(5)]
        )
        lbl = Label(
            text=label_text,
            halign='left',
            valign='middle',
            font_size=font_sz,
            size_hint_x=0.45
        )
        lbl.bind(size=self._update_setting_row_label)
        row.add_widget(lbl)
        container = BoxLayout(
            size_hint_x=0.55
        )
        container.add_widget(widget)
        row.add_widget(container)
        return row

    def add_section_title(self, title, font_sz, h):
        lbl = Label(text=title, font_size=font_sz, color=self.ACCENT_YELLOW, bold=True, 
                    size_hint_y=None, height=h, halign='left', valign='bottom')
        lbl.bind(size=self._update_label_size_limit)
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
        fl = filename.lower()
        if fl.endswith('.ini'):
            return False
        return (
            (fl.startswith('tournoi_') and fl.endswith(('.json', '.yaml'))) or
            (fl.startswith('data_') and fl.endswith('.yaml')) or
            (fl.startswith('chat_') and fl.endswith('.json')) or
            fl in ['config_cache.yaml', 'config_tournoi.yaml', 'config_fcvv.yaml'] or
            (fl.startswith('sponsor_') and fl.endswith(('.png', '.jpg', '.jpeg'))) or
            (fl.startswith('img_') and fl.endswith(('.png', '.jpg', '.jpeg'))) or
            (fl.startswith('part_') and fl.endswith(('.png', '.jpg', '.jpeg'))) or
            (fl.startswith('memb_') and fl.endswith(('.png', '.jpg', '.jpeg'))) or
            (fl.startswith('prod_') and fl.endswith(('.png', '.jpg', '.jpeg')))
        )

    def update_network_status(self, dt):
        def worker():
            is_online = check_internet()
            Clock.schedule_once(lambda dt: self.finish_network_update(is_online))
        threading.Thread(target=worker, daemon=True).start()

    def finish_network_update(self, is_online):
        if hasattr(self, 'conn_label') and self.conn_label:
            tr_state = self.app_tr('conn_state')
            color = "00FF00" if is_online else "FF0000"
            status = "OK" if is_online else "OFFLINE"
            self.conn_label.text = f"{tr_state} : [color={color}]{status}[/color]"

    def clear_local_cache(self, instance):
        app = App.get_running_app()
        target_dir = app.user_data_dir
        files_deleted = 0
        instance.disabled = True
        if os.path.exists(target_dir):
            for dirpath, _, filenames in os.walk(target_dir):
                for f in filenames:
                    if self.is_cache_file(f):
                        try:
                            os.remove(os.path.join(dirpath, f))
                            files_deleted += 1
                        except Exception as e:
                            print(f"Erreur suppression {f}: {e}")
        if hasattr(app, 'load_remote_config'):
            threading.Thread(target=app.load_remote_config, daemon=True).start()
        if files_deleted > 0:
            instance.text = f"Vidé ({files_deleted} f.)"
            self.update_cache_display()
        else:
            instance.text = "Déja vide"
        Clock.schedule_once(lambda dt: self._reset_btn_ui(instance, self.app_tr("cache")), 2)

    def confirm_reset(self, instance):
        print("Clic détecté sur le bouton Reset")
        instance.disabled = True
        instance.text = "PATIENTEZ..."
        
        app = App.get_running_app()
        if hasattr(app, 'config'):
            # 1. Réinitialisation des paramètres utilisateur (Section 'User')
            app.config.set('User', 'font_size_factor', '24')
            app.config.set('User', 'refresh_interval', '5')
            app.config.set('User', 'news_period', '15')
            app.config.set('User', 'dark_mode', '0')
            app.config.set('User', 'authorized_list', '') 
            app.config.set('User', 'nom_parent', '')
            
            # Réinitialisation acceptation CGU / Politique confidentialité
            app.config.set('User', 'vestiaire_cgu_accept', '0')
            
            # 2. Suppression TOTALE de la section 'Roles'
            # Cela supprime tous les hashs et rôles stockés localement
            if app.config.has_section('Roles'):
                app.config.remove_section('Roles')
            
            # Recréation d'une section 'Roles' vide (pour éviter les erreurs si l'app la cherche)
            app.config.add_section('Roles')
            
            # 3. Mise à jour de la mémoire
            if hasattr(app, 'authorized_vestiaires'):
                app.authorized_vestiaires = []
                
            # 4. Désabonnement FCM
            if hasattr(app, 'gerer_abonnements_fcm'):
                app.gerer_abonnements_fcm([])
            
            # Écriture immédiate sur le disque
            app.config.write()
            print("Configuration réinitialisée (Sections User & Roles nettoyées)")
            
        # 5. Thread secondaire pour les fichiers lourds
        Clock.schedule_once(lambda dt: self._start_reset_safe(instance), 0.1)

    def _start_reset_safe(self, instance):
        t = threading.Thread(target=self._perform_reset_logic, args=(instance,))
        t.daemon = True
        t.start()

    def _perform_reset_logic(self, instance):
        app = App.get_running_app()
        try:
            # 3. Suppression des fichiers lourds en tâche de fond (os.walk sécurisé)
            data_dir = app.user_data_dir
            if os.path.exists(data_dir):
                for dirpath, _, filenames in os.walk(data_dir):
                    for f in filenames:
                        if self.is_cache_file(f):
                            try:
                                os.remove(os.path.join(dirpath, f))
                            except Exception as e:
                                print(f"Erreur suppression {f}: {e}")
                                
            # 4. Retour au thread principal pour notifier la fin du nettoyage
            Clock.schedule_once(lambda dt: self.finalize_reset(instance), 0.1)
        except Exception as e:
            print(f"ERREUR RESET THREAD : {e}")

    def finalize_reset(self, instance):
        app = App.get_running_app()
        # UI immédiate légère
        instance.text = "Réinitialisation..."
        instance.disabled = True
        # Téléchargement fond
        if hasattr(app, 'load_remote_config'):
            threading.Thread(
                target=self._background_reset_reload,
                daemon=True
            ).start()
            
    def _background_reset_reload(self):
        app = App.get_running_app()
        try:
            app.load_remote_config()
        except Exception as e:
            print(f"Erreur reload config: {e}")
        # Retour thread principal
        Clock.schedule_once(self._finish_reset_reload, 0)
        
    def _finish_reset_reload(self, dt):
        app = App.get_running_app()
        # 1. Reconstruction complète de l'interface
        self.refresh_settings_layout()
        
        # 2. Force manuellement le lancement de la vérification réseau
        # Puisque refresh_settings_layout vient de recréer self.conn_label,
        # on peut appeler directement la méthode de mise à jour.
        Clock.schedule_once(self.update_network_status, 0.2)
        
        if hasattr(app, 'refresh_ui_theme'):
            app.refresh_ui_theme()
            
    def _reset_btn_ui(self, btn, original_text):
        if btn:
            btn.text = original_text
            btn.disabled = False

    def update_refresh_label_and_config(self, instance, value):
        new_val = int(value)
        if self.refresh_value_label:
            self.refresh_value_label.text = f"{new_val} min"
        app = App.get_running_app()
        
        if hasattr(app, 'config'):
            app.config.set('User', 'refresh_interval', str(new_val))
            app.config.write()
        try:
            sm = app.root if hasattr(app.root, 'get_screen') else app.root.sm
            if sm.has_screen('soirees'):
                soirees_screen = sm.get_screen('soirees')
                if hasattr(soirees_screen, 'setup_auto_refresh'):
                    soirees_screen.setup_auto_refresh()
        except Exception as e:
            print(f"Erreur notification timer : {e}")

    def update_font_label_and_config(self, instance, value):
        if self.font_value_label:
            self.font_value_label.text = str(int(value))
        app = App.get_running_app()
        if hasattr(app, 'config'):
            app.config.set('User', 'font_size_factor', str(int(value)))
            app.config.write()
            if app.root:
                app.root.menu_built = False 
            if hasattr(app, 'refresh_ui_theme'): 
                app.refresh_ui_theme()
                
        # --- AJOUT : Force le HomeScreen à se recharger ---
        try:
            # On cherche le ScreenManager (s'adapte à votre architecture racine)
            sm = app.root if hasattr(app.root, 'get_screen') else app.root.sm
            if sm and sm.has_screen('home'):
                home = sm.get_screen('home')
                if hasattr(home, 'update_ui_from_config'):
                    # On force la reconstruction des NewsCard avec la nouvelle police
                    home.update_ui_from_config(force=True) 
        except Exception as e:
            print(f"[Font Sync Error] : {e}")

    def on_dark_mode_toggle(self, switch, value):
        app = App.get_running_app()
        if hasattr(app, 'config'):
            app.config.set('User', 'dark_mode', '1' if value else '0')
            app.config.write()
            if app.root:
                app.root.menu_built = False
            if hasattr(app, 'refresh_ui_theme'): 
                app.refresh_ui_theme()