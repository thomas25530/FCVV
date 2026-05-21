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
        
        # Références des composants persistants pour éviter les recréations et fuites multiples
        self.main_layout = None
        self.admin_layout = None
        self.debug_input = None
        self.font_value_label = None
        self.refresh_value_label = None
        self.cache_label = None
        self.conn_label = None
        
        with self.canvas.before:
            Color(*self.KIVY_BLUE)
            self.rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._update_rect, size=self._update_rect)

        self.scroll = ScrollView(do_scroll_x=False, bar_width=0)
        self.add_widget(self.scroll)
        self.refresh_settings_layout()

    def _update_rect(self, instance, value):
        self.rect.pos = instance.pos
        self.rect.size = instance.size

    def _update_switch_scale(self, instance, value):
        """ Callback nommé éliminant la fuite mémoire de la lambda du Switch origin """
        if hasattr(instance, 'scale_instr'):
            instance.scale_instr.origin = instance.center

    def _update_label_size_limit(self, instance, value):
        """ Callback nommé pour le text_size des titres de section """
        instance.text_size = (value[0], None)

    def _update_setting_row_label(self, instance, value):
        """ Callback nommé pour le text_size des lignes standards """
        instance.text_size = (value[0], value[1])

    def _cleanup_layout(self):
        """ Désassocie explicitement tous les callbacks pour permettre au GC de purger la RAM """
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

        # FIX FUITE : Nettoyage avant suppression
        self._cleanup_layout()
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

        # SWITCH DARK MODE
        dark_switch = Switch(active=current_dark_mode, size_hint=(None, None), size=(res_d(120), res_d(60)))
        with dark_switch.canvas.before:
            PushMatrix()
            dark_switch.scale_instr = Scale(1.5, 1.5, 1) 
        with dark_switch.canvas.after:
            PopMatrix()
            
        # FIX FUITE : Remplacement du lambda par un callback nommé
        dark_switch.bind(pos=self._update_switch_scale)
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
        self.admin_title.bind(size=self._update_label_size_limit)
        
        self.admin_row = BoxLayout(orientation='horizontal', size_hint_y=None, height=h_btn, spacing=res_d(10))
        self.debug_input = TextInput(hint_text="Password", password=True, multiline=False, size_hint_x=0.7,
                                    font_size=f_text, padding=[res_d(10), (h_btn - f_text)/4])
        
        btn_ok = Button(text="OK", size_hint_x=0.3, background_color=(0.2, 0.6, 0.2, 1), bold=True)
        btn_ok.bind(on_release=self._trigger_debug_password_check)
        
        self.admin_row.add_widget(self.debug_input)
        self.admin_row.add_widget(btn_ok)
        self.admin_layout.add_widget(self.admin_title)
        self.admin_layout.add_widget(self.admin_row)
        self.main_layout.add_widget(self.admin_layout)

        self.scroll.add_widget(self.main_layout)

    def _trigger_debug_password_check(self, instance):
        """ Intermédiaire nommé pour éliminer la lambda de validation admin """
        self.on_debug_password_entered(self.debug_input)

    def on_notifications_toggle(self, switch, value):
        app = App.get_running_app()
        if hasattr(app, 'config'):
            app.config.set('User', 'notifications', '1' if value else '0')
            app.config.write()

    def update_cache_display(self):
        if hasattr(self, 'cache_label') and self.cache_label:
            prefix = self.app_tr('cache_size_label')
            size_str = self.get_cache_size() 
            self.cache_label.text = f"{prefix} : [b]{size_str}[/b]"
        
    def check_debug_conditions(self, *args):
        app = App.get_running_app()
        try:
            # Sécurité anti-crash si le spinner n'est pas instancié dans ce flux
            lang_text = getattr(self, 'lang_spinner', None)
            is_english = lang_text.text == 'English' if lang_text else False
            
            is_dark = app.config.getboolean('User', 'dark_mode')
            font_val = int(app.config.get('User', 'font_size_factor'))
            refresh_val = int(app.config.get('User', 'refresh_interval'))
            
            if is_english and is_dark and font_val == 30 and refresh_val == 15:
                self.show_debug_field(True)
            else:
                self.show_debug_field(False)
        except Exception as e:
            print(f"Debug check error: {e}")

    def show_debug_field(self, show=True):
        if not self.admin_layout:
            return
        if show:
            self.admin_layout.opacity = 1
            self.admin_layout.disabled = False
            self.admin_layout.height = dp(140)
        else:
            self.admin_layout.opacity = 0
            self.admin_layout.disabled = True
            self.admin_layout.height = 0
            if self.debug_input:
                self.debug_input.text = ""

    def on_debug_password_entered(self, instance):
        app = App.get_running_app()
        password = instance.text.strip()
        
        if not password:
            return

        stored_hash = getattr(app, "_app_password_hash", "")
        input_hash = hashlib.sha256(password.encode("utf-8")).hexdigest()

        if hmac.compare_digest(input_hash, stored_hash):
            app.debug_mode = True  
            instance.background_color = (0, 1, 0, 1) 
            
            if hasattr(app, 'config'):
                app.config.set('User', 'langue', 'Français')
                app.config.set('User', 'dark_mode', '0')
                app.config.set('User', 'font_size_factor', '20')
                app.config.set('User', 'refresh_interval', '5')
                app.config.write()

            self.refresh_settings_layout()
            instance.text = ""
            instance.hint_text = "MODE ADMIN ACTIF"
            
            if hasattr(self, 'conn_label'):
                self.conn_label.text = f"{self.app_tr('conn_state')} : [color=FFFF00]...[/color]"
                self.update_network_status(None)

            if hasattr(app, 'refresh_ui_theme'):
                app.refresh_ui_theme()
        else:
            app.debug_mode = False 
            instance.text = ""
            instance.hint_text = "Refusé"
            instance.background_color = (1, 0, 0, 0.5)
            Clock.schedule_once(self._reset_input_fail_bg, 1)

    def _reset_input_fail_bg(self, dt):
        if self.debug_input:
            self.debug_input.background_color = (1, 1, 1, 1)

    def finish_reset_ui(self, instance):
        app = App.get_running_app()
        if hasattr(app, 'refresh_ui_theme'):
            app.refresh_ui_theme()
        
        self.refresh_settings_layout()
        
        if hasattr(self, 'conn_label'):
            tr = self.app_tr('conn_state')
            self.conn_label.text = f"{tr} : [color=FFFF00]...[/color]"
            self.update_network_status(None)
        
        instance.text = "Système d'origine rétabli !"
        instance.background_color = (0.2, 0.7, 0.2, 1)
        
        # FIX FUITE : Élimination du lambda sur le callback d'attente
        Clock.schedule_once(lambda dt: self._reset_btn_ui(instance, self.app_tr("reset_btn")), 3)

    def on_enter(self):
        self.update_cache_display()
        if hasattr(self, 'conn_label'):
            tr = self.app_tr('conn_state')
            self.conn_label.text = f"{tr} : [color=FFFF00]...[/color]"
            Clock.schedule_once(self.update_network_status, 0.2)

    def create_setting_row(self, label_text, widget, row_height, font_sz):
        row = BoxLayout(orientation='horizontal', size_hint_y=None, height=row_height)
        lbl = Label(text=label_text, halign='left', valign='middle', font_size=font_sz)
        lbl.bind(size=self._update_setting_row_label)
        row.add_widget(lbl)
        
        container = BoxLayout(size_hint_x=None, width=dp(220), padding=[0, dp(10)])
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
            fl in ['config_cache.yaml', 'config_tournoi.yaml', 'config_fcvv.yaml'] or
            (fl.startswith('sponsor_') and fl.endswith(('.png', '.jpg', '.jpeg'))) or
            (fl.startswith('img_') and fl.endswith(('.png', '.jpg', '.jpeg')))
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
            instance.text = "Déjà vide"
            
        Clock.schedule_once(lambda dt: self._reset_btn_ui(instance, self.app_tr("cache")), 2)

    def confirm_reset(self, instance):
        instance.disabled = True
        instance.text = "PATIENTEZ..."
        Clock.schedule_once(lambda dt: self._start_reset_safe(instance), 0.1)

    def _start_reset_safe(self, instance):
        t = threading.Thread(target=self._perform_reset_logic, args=(instance,))
        t.daemon = True
        t.start()

    def _perform_reset_logic(self, instance):
        app = App.get_running_app()
        try:
            if hasattr(app, 'config'):
                app.config.set('User', 'font_size_factor', '24')
                app.config.set('User', 'refresh_interval', '5')
                app.config.set('User', 'dark_mode', '0')
                app.config.set('User', 'langue', 'Français')
                app.config.write()

            data_dir = app.user_data_dir
            if os.path.exists(data_dir):
                for f in os.listdir(data_dir):
                    if self.is_cache_file(f):
                        try:
                            os.remove(os.path.join(data_dir, f))
                        except Exception as e:
                            print(f"Thread : Erreur {f}: {e}")

            if hasattr(app, 'load_remote_config'):
                app.load_remote_config()

            Clock.schedule_once(lambda dt: self._post_reset_sync(instance), 0.1)
            
        except Exception as e:
            print(f"ERREUR RESET THREAD : {e}")
            Clock.schedule_once(lambda dt: self._reset_btn_ui(instance, "Erreur Fatale"), 0.1)

    def _post_reset_sync(self, instance):
        """ Évite l'imbrication de lambda asynchrone après l'exécution du Thread """
        self.update_cache_display()
        self.finish_reset_ui(instance)

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
        
        self.check_debug_conditions()

    def on_language_change(self, spinner, text):
        app = App.get_running_app()
        if hasattr(app, 'config'):
            app.config.set('User', 'langue', text)
            app.config.write()
            if hasattr(app, 'refresh_ui_theme'): app.refresh_ui_theme()
            self.refresh_settings_layout()

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
                
        self.check_debug_conditions()

    def on_dark_mode_toggle(self, switch, value):
        app = App.get_running_app()
        if hasattr(app, 'config'):
            app.config.set('User', 'dark_mode', '1' if value else '0')
            app.config.write()
            
            if app.root:
                app.root.menu_built = False
            if hasattr(app, 'refresh_ui_theme'): 
                app.refresh_ui_theme()
        self.check_debug_conditions()