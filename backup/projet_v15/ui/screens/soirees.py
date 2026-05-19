# -*- coding: utf-8 -*-

# --- STANDARDS ---
import os
import json
import math
import yaml
import requests
import threading
from datetime import datetime, timedelta
import certifi
import traceback
from kivy.utils import platform
import hashlib
import traceback


# On n'importe PythonService que si on est sur Android
PythonService = None

if platform == "android":
    try:
        from android import PythonService
    except Exception as e:
        print("PythonService indisponible:", e)

# --- KIVY CORE ---
from kivy.app import App
from kivy.clock import Clock
from kivy.animation import Animation
from kivy.graphics import Color, Rectangle
# Ajoute ces lignes avec tes autres imports en haut du fichier
from kivy.uix.button import Button
from kivy.uix.spinner import Spinner, SpinnerOption
from datetime import datetime # Requis pour ton rafraîchissement
import os
import json
import yaml
import requests
import certifi
from kivy.utils import platform

# --- KIVY UI (Layouts & Widgets) ---
from kivy.uix.widget import Widget
from kivy.uix.label import Label
from kivy.uix.spinner import Spinner
from kivy.uix.scrollview import ScrollView
from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.tabbedpanel import TabbedPanel, TabbedPanelItem
from kivy.metrics import dp
from kivy.uix.spinner import SpinnerOption
from kivy.graphics import Color, Rectangle, RoundedRectangle

# --- IMPORTS MÉTIER ---
from core.tournoi_logic import TournoiLogic, build_group_colors

# Fonction de traduction locale
def _(key):
    app = App.get_running_app()
    if hasattr(app, '_'):
        return app._(key)
    return key

from kivy.uix.label import Label
from kivy.uix.boxlayout import BoxLayout
from kivy.graphics import Color, Rectangle

def hex_to_rgb(hex_str):
    """Convertit #RRGGBB en liste [R, G, B, 1] utilisable par Kivy"""
    hex_str = hex_str.lstrip('#')
    if len(hex_str) != 6:
        return [1, 1, 1, 1]  # Retourne blanc par défaut si erreur
    return [int(hex_str[i:i+2], 16)/255.0 for i in (0, 2, 4)] + [1]

class HeaderLabel(Label):
    """Label d'en-tête auto-ajustable"""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.markup = True
        self.halign = 'center'
        self.valign = 'middle'
        self.font_size = '11sp'
        # Liaison de la zone de texte à la taille du widget
        self.bind(size=self.setter('text_size'))

class StyledRow(BoxLayout):
    """Ligne avec fond coloré configurable"""
    def __init__(self, bg_color=(1, 1, 1, 1), **kwargs):
        super().__init__(**kwargs)
        with self.canvas.before:
            self.canvas_color = Color(*bg_color)
            self.rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._update_rect, size=self._update_rect)

    def _update_rect(self, instance, value):
        self.rect.pos = instance.pos
        self.rect.size = instance.size

class StyledLabel(Label):
    """Label avec fond coloré et centrage parfait"""
    def __init__(self, bg_color=(1, 1, 1, 1), **kwargs):
        # Configuration des défauts avant le super()
        kwargs.setdefault('markup', True)
        kwargs.setdefault('halign', 'center')
        kwargs.setdefault('valign', 'middle')
        super().__init__(**kwargs)
        
        # Centrage du texte
        self.bind(size=self.setter('text_size'))
        
        # Dessin du fond
        self.background_color = bg_color
        with self.canvas.before:
            self.canvas_color = Color(*self.background_color)
            self.rect = Rectangle(pos=self.pos, size=self.size)
        
        self.bind(pos=self._update_rect, size=self._update_rect)

    def _update_rect(self, instance, value):
        self.rect.pos = instance.pos
        self.rect.size = instance.size

class CustomSpinnerOption(SpinnerOption):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.background_normal = ''
        self.background_color = (70/255, 100/255, 180/255, 1)
        self.height = dp(65) 
        
        # --- AUGMENTATION DE LA POLICE DES OPTIONS ---
        self.font_size = '18sp'  # Taille des choix dans la liste
        
        with self.canvas.after:
            Color(1, 1, 1, 0.2)
            self.line = Rectangle(size=(self.width, dp(1)), pos=self.pos)
            
        self.bind(pos=self._update_line, size=self._update_line)

    def _update_line(self, instance, value):
        self.line.pos = instance.pos
        self.line.size = (instance.width, dp(1))

class SoireesScreen(Screen):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        self._is_initializing = True
        
        # --- INITIALISATION DES VARIABLES DE CONTRÔLE (NE PAS SUPPRIMER) ---
        self.auto_refresh_event = None
        self.current_tournoi = None 
        self.active_header = None
        self.current_tab = "matchs"  # Onglet par défaut (matchs ou classement)
        
        # --- CACHE DE RENDU (Dirty Flags) : Requis par build_matchs_view ---
        self._last_matchs_hash = None
        self._last_classement_hash = None
        self._current_structure_sig = None
        self.score_widgets = {} 
        
        # --- COULEURS THÈME ---
        self.KIVY_BLUE = (30/255, 58/255, 138/255, 1)
        self.YELLOW = (247/255, 236/255, 63/255, 1)
        
        # Fond bleu de l'écran
        with self.canvas.before:
            Color(*self.KIVY_BLUE)
            self.rect_bg = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._update_rect, size=self._update_rect)

        root = BoxLayout(orientation="vertical")

        # =========================
        # 1. TOP BAR (SPINNERS)
        # =========================
        top = BoxLayout(size_hint_y=None, height=dp(120), padding=[dp(5), dp(15), dp(5), dp(15)], spacing=dp(8))
        
        spinner_kwargs = {
            'size_hint_y': None, 
            'height': dp(80), 
            'background_normal': '', 
            'background_color': (1, 1, 1, 0.15), 
            'color': (1, 1, 1, 1),
            'option_cls': CustomSpinnerOption,
            'sync_height': False,
            # --- AUGMENTATION DE LA POLICE DU BOUTON ---
            'font_size': '20sp',  # Taille plus grande pour l'année/tournoi sélectionnés
            'bold': True          # Optionnel : mettre en gras pour plus de lisibilité
        }
        
        self.year_spinner = Spinner(text=_("spinner_year"), values=[], **spinner_kwargs)
        self.year_spinner.bind(text=self.update_tournaments_list)
        
        self.tournament_spinner = Spinner(text=_("spinner_tournament"), values=[], **spinner_kwargs)
        self.tournament_spinner.bind(text=self.load_selected_tournament)
        
        top.add_widget(self.year_spinner)
        top.add_widget(self.tournament_spinner)
        root.add_widget(top)

        # =========================================================
        # 2. SÉLECTEUR D'ONGLETS (STYLE RESTAURATION)
        # =========================================================
        self.tab_bar = BoxLayout(size_hint_y=None, height=dp(85), spacing=dp(10), padding=dp(10))
        root.add_widget(self.tab_bar)

        # =========================================================
        # 3. ZONE D'INFOS (TITRE & MAJ)
        # =========================================================
        self.header_info = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(55), padding=[dp(10), 0])
        self.label_titre_centre = Label(text="", markup=True, bold=True, font_size='18sp', halign='center', valign='middle')
        self.label_titre_centre.bind(size=lambda inst, val: setattr(inst, 'text_size', val))
        
        self.label_maj_droite = Label(text="", markup=True, size_hint_x=None, width=dp(80), font_size='10sp', color=self.YELLOW, halign='right', valign='middle')
        self.label_maj_droite.bind(size=lambda inst, val: setattr(inst, 'text_size', val))
        
        self.header_info.add_widget(self.label_titre_centre)
        self.header_info.add_widget(self.label_maj_droite)
        root.add_widget(self.header_info)

        # =========================================================
        # 4. ZONE DE CONTENU (SCROLLVIEW)
        # =========================================================
        self.scroll = ScrollView(do_scroll_x=False)
        # On crée un layout qui servira aux deux fonctions de rendu
        self.content_container = BoxLayout(orientation='vertical', size_hint_y=None, padding=[0, dp(5), 0, dp(5)], spacing=dp(2))
        self.content_container.bind(minimum_height=self.content_container.setter('height'))
        
        # On assigne ce layout aux deux noms que tes fonctions utilisent
        self.matchs_layout = self.content_container
        self.classement_layout = self.content_container
        
        self.scroll.add_widget(self.content_container)
        root.add_widget(self.scroll)

        self.add_widget(root)
        Clock.schedule_once(lambda dt: self.refresh_years(), 0.5)

    def _update_rect(self, instance, value):
        self.rect_bg.pos = instance.pos
        self.rect_bg.size = instance.size

    def update_tab_bar(self):
        app = App.get_running_app()
        f_factor = 20
        if hasattr(app, 'config'):
            try: f_factor = app.config.getint('User', 'font_size_factor')
            except: pass

        self.tab_bar.clear_widgets()
        # On force la hauteur pour les gros doigts
        self.tab_bar.height = dp(85) 
        
        tabs = [("matchs", _("tab_matches")), ("classement", _("tab_ranking"))]
        
        for tid, tlabel in tabs:
            is_active = (self.current_tab == tid)
            btn_width = max(dp(160), dp(len(tlabel) * (f_factor * 0.7)))
            
            btn = Button(
                text=tlabel.upper(),
                size_hint=(None, 1),
                width=btn_width,
                background_normal='',
                background_color=(0, 0, 0, 0), # Important : transparent !
                color=(0, 0, 0, 1) if is_active else (1, 1, 1, 1),
                bold=is_active,
                font_size=f"{f_factor - 1}sp"
            )
            
            with btn.canvas.before:
                Color(*(0.97, 0.93, 0.25, 1) if is_active else (1, 1, 1, 0.15))
                # On utilise RoundedRectangle mais on importe bien en haut !
                btn.bg_rect = RoundedRectangle(pos=btn.pos, size=btn.size, radius=[dp(8)])
            
            btn.bind(pos=lambda inst, val: setattr(inst.bg_rect, 'pos', inst.pos),
                     size=lambda inst, val: setattr(inst.bg_rect, 'size', inst.size))

            btn.bind(on_release=lambda x, t=tid: self.switch_tab(t))
            self.tab_bar.add_widget(btn)

    def switch_tab(self, tab_name):
        """Change d'onglet et force la reconstruction du contenu"""
        if self.current_tab == tab_name:
            return
            
        self.current_tab = tab_name
        self.update_tab_bar() 
        
        # Reset des hashs pour forcer build_matchs_view à redessiner
        self._last_matchs_hash = None
        self._last_classement_hash = None
        
        if self.current_tournoi:
            self._do_rebuild(self.current_tournoi)

    def _do_rebuild(self, t_logic):
        # 1. On vide le contenu scrollable (les matchs eux-mêmes)
        self.content_container.clear_widgets()
        
        # 2. GESTION DU HEADER FIXE
        if hasattr(self, 'matchs_header'):
            if self.current_tab == "matchs":
                # On l'affiche
                self.matchs_header.opacity = 1
                self.matchs_header.height = dp(40)
                self.matchs_header.disabled = False
            else:
                # On le fait disparaître COMPLÈTEMENT
                self.matchs_header.opacity = 0
                self.matchs_header.height = 0
                self.matchs_header.disabled = True

        # 3. On lance la construction de la vue choisie
        if self.current_tab == "matchs":
            self.build_matchs_view(t_logic)
        else:
            self.build_classement_view()
            
    #===========================================================================
    # def _do_rebuild(self, t_logic):
    #     """ Reconstruction totale des deux onglets """
    #     self._last_matchs_hash = None
    #     self._last_classement_hash = None
    #     self.score_widgets = {}
    #     
    #     # Nettoyage
    #     self.matchs_layout.clear_widgets()
    #     self.classement_layout.clear_widgets()
    #     
    #     # Reconstruction (appelle tes fonctions de création de lignes)
    #     self.build_matchs_view(t_logic)
    #     self.build_classement_view()
    #===========================================================================


    def on_enter(self):
        # 1. On dessine la barre d'onglets
        self.update_tab_bar()
        
        # --- AJOUT ICI : On force l'affichage de l'heure dès l'arrivée ---
        from datetime import datetime
        app = App.get_running_app()
        if hasattr(app.root, 'maj_label'):
            app.root.maj_label.opacity = 1
            app.root.maj_label.width = dp(80)
            heure_actuelle = datetime.now().strftime("%Hh%M")
            app.root.maj_label.text = f"[size=11sp]MAJ[/size]\n[b][size=14sp]{heure_actuelle}[/size][/b]"
        # ----------------------------------------------------------------

        # 2. Vérification de la config en arrière-plan
        def background_check():
            if hasattr(app, 'load_remote_config'):
                app.load_remote_config()
                Clock.schedule_once(lambda dt: self.refresh_years(), 0)

        threading.Thread(target=background_check, daemon=True).start()

        # 3. Chargement différé du contenu
        Clock.schedule_once(self._deferred_loading, 0.15)
        
        #Clock.schedule_once(lambda dt: self.start_background_service(), 1)
    
    def start_background_service(self):
        # Désactivé : on ne lance plus le service Java
        print("[SERVICE] Démarrage ignoré (Service supprimé)")
        return
    
    def get_app_storage_path(self):
        """Retourne le chemin où le service peut lire/écrire"""
        app = App.get_running_app()
        return app.user_data_dir

    def _deferred_loading(self, dt):
        self._is_initializing = False
        current_t = self.tournament_spinner.text
        excluded = [_("spinner_tournament"), "Aucun tournoi", "", None]
        
        # Si on a déjà un tournoi chargé qui correspond au spinner
        if self.current_tournoi and getattr(self.current_tournoi, 'nom', '') == current_t:
            if not self.matchs_layout.children:
                self._do_rebuild(self.current_tournoi)
        else:
            if current_t not in excluded:
                self.load_selected_tournament(self.tournament_spinner, current_t, force=False)
                
        self.setup_auto_refresh()
            
    def on_leave(self):
        """ On arrête tout quand on quitte l'écran pour économiser la batterie """
        if hasattr(self, 'auto_refresh_event') and self.auto_refresh_event:
            self.auto_refresh_event.cancel()
            self.auto_refresh_event = None
            print("[AUTO-UPDATE] Arrêté")
            
    def setup_auto_refresh(self, *args):
        """ (Re)démarre le timer avec la valeur actuelle des réglages """
        app = App.get_running_app()
        # 1. On annule l'ancien timer s'il existe pour éviter les doublons
        if hasattr(self, 'auto_refresh_event') and self.auto_refresh_event:
            self.auto_refresh_event.cancel()
            self.auto_refresh_event = None
        # 2. On récupère la valeur (en minutes) depuis la config
        # On convertit en secondes (min * 60)
        try:
            minutes = int(app.config.get('User', 'refresh_interval', fallback=5))
        except:
            minutes = 5
        refresh_seconds = minutes * 60
        # 3. On programme le nouvel intervalle
        self.auto_refresh_event = Clock.schedule_interval(self.auto_update, refresh_seconds)
        print(f"[TIMER] Prochain rafraîchissement dans {minutes} min")
        
    def update_refresh_timestamp(self, dt=None):
        """ Calcule l'heure de la mise à jour réelle """
        if not self.current_tournoi:
            return
        
        app = App.get_running_app()
        heure_seule = datetime.now().strftime("%Hh%M")
        
        # On vérifie que RootLayout possède bien le label
        if hasattr(app.root, 'maj_label'):
            # On s'assure qu'il est bien visible (sécurité)
            app.root.maj_label.opacity = 1
            app.root.maj_label.width = dp(80)
            
            # Mise à jour du texte
            app.root.maj_label.text = (
                f"[size=11sp]MAJ[/size]\n"
                f"[b][size=14sp]{heure_seule}[/size][/b]"
            )
    
    # --- CALLBACK DE MISE À JOUR DU FOND ---
    def _update_rect_callback(self, instance, value):
        instance.rect.pos = instance.pos
        instance.rect.size = instance.size
    
    def manual_reload(self, instance=None):
        # --- AJOUT : Reset du cache de rendu ---
        app = App.get_running_app()
        if instance and hasattr(instance, 'rot'):
            instance.disabled = True
            anim = Animation(angle=360, duration=0.8, t='in_out_quad')
            anim.repeat = True 
            anim.start(instance.rot)
            self._current_anim = anim

        def perform_load():
            try:
                # --- ÉTAPE A : Recharger la liste globale des tournois ---
                # On appelle la fonction de MyApp qui gère le Hash MD5
                if hasattr(app, 'load_remote_config'):
                    app.load_remote_config() 
                # On attend un tout petit peu que le fichier soit écrit sur le disque
                # et on met à jour la liste des années dans l'UI
                Clock.schedule_once(lambda dt: self.refresh_years(), 0)
                # --- ÉTAPE B : Recharger les scores du tournoi actuel ---
                def force_reload_scores(dt):
                    current_t_name = self.tournament_spinner.text
                    excluded = [_("spinner_tournament"), "Aucun tournoi", "No tournament", ""]
                    if current_t_name not in excluded:
                        # On force le téléchargement du tournoi sélectionné
                        self.load_selected_tournament(self.tournament_spinner, current_t_name, force=True)
                    else:
                        # Si aucun tournoi n'était sélectionné (ex: l'app vient d'être mise à jour)
                        # On déclenche update_tournaments_list pour remplir le spinner
                        self.update_tournaments_list(self.year_spinner, self.year_spinner.text)
                    self.update_refresh_timestamp()
                Clock.schedule_once(force_reload_scores, 0.2)
                success = True
            except Exception as e:
                print(f"Erreur reload complet: {e}")
                success = False
            Clock.schedule_once(lambda dt: restore_button(success), 0.5)

        def restore_button(success):
            if instance:
                if hasattr(self, '_current_anim'):
                    self._current_anim.stop(instance.rot)
                    Animation(angle=0, duration=0.2).start(instance.rot)
                instance.disabled = False
        threading.Thread(target=perform_load, daemon=True).start()
        
    def auto_update(self, dt=None):
        """ Rafraîchissement automatique complet (Config + Scores) """
    
        app = App.get_running_app()
        current_tournament = self.tournament_spinner.text
        excluded_texts = [_("spinner_tournament"), "Aucun tournoi", "No tournament", ""]
        # --- 1. RÉCUPÉRER LE BOUTON ET LANCER L'ANIMATION ---
        target_btn = getattr(app.root, 'btn_reload', None)
        if target_btn and hasattr(target_btn, 'rot'):
            target_btn.disabled = True
            anim = Animation(angle=360, duration=0.8, t='in_out_quad')
            anim.repeat = True 
            anim.start(target_btn.rot)
            self._auto_refresh_anim = anim

        def perform_background_update():
            # --- 2. METTRE À JOUR LA CONFIG (Nouveaux tournois sur le Drive) ---
            # Cette fonction utilise maintenant le Hash MD5, donc c'est très léger
            if hasattr(app, 'load_remote_config'):
                app.load_remote_config()
            # --- 3. RECHARGER LES SCORES DU TOURNOI ACTUEL ---
            if current_tournament not in excluded_texts:
                # On force le téléchargement du fichier de scores
                # Note: load_selected_tournament gère déjà son propre thread interne
                Clock.schedule_once(lambda dt: self.load_selected_tournament(
                    self.tournament_spinner, current_tournament, force=True
                ), 0)
            # --- 4. RAFRAÎCHIR L'UI (Au cas où un nouveau tournoi est apparu) ---
            Clock.schedule_once(lambda dt: self.refresh_years(), 0.1)
            Clock.schedule_once(self.update_refresh_timestamp, 0.2)
            # --- 5. ARRÊTER L'ANIMATION ---
            # On laisse l'animation tourner au moins 1.5s pour le feedback visuel
            Clock.schedule_once(lambda dt: self._stop_auto_rotate(target_btn), 1.5)
            print(f"[AUTO-UPDATE] Config et Scores actualisés à {datetime.now().strftime('%H:%M')}")

        # On lance tout le processus dans un thread séparé pour ne pas freezer l'app
        threading.Thread(target=perform_background_update, daemon=True).start()

    def _stop_auto_rotate(self, btn):
        """ Arrête l'animation et réinitialise le bouton """
        if hasattr(self, '_auto_refresh_anim') and btn:
            self._auto_refresh_anim.stop(btn.rot)
            # Remet l'angle à 0 avec une petite transition fluide
            Animation(angle=0, duration=0.2).start(btn.rot)
            btn.disabled = False
            # Nettoyage de la référence
            self._auto_refresh_anim = None

    # --- CORRECTION DE LA LOGIQUE DE FILTRAGE DES TOURNOIS ---
    def update_tournaments_list(self, spinner, year):
        """ Filtre les tournois selon l'année choisie """
        if year in ["Année", _("spinner_year"), "", None] or self._is_initializing: 
            return
        
        app = App.get_running_app()
        previous_selection = self.tournament_spinner.text
        
        # Extraction sécurisée de la liste des tournois
        tournois_list = app.app_config.get("tournoi", {}).get("tournois", [])
        selected_year_str = str(year).strip()
        
        noms_disponibles = sorted(list(set([
            t.get('nom') for t in tournois_list 
            if str(t.get("annee")).strip() == selected_year_str
        ])))

        if noms_disponibles:
            self.tournament_spinner.values = noms_disponibles
            # On garde l'ancienne sélection si elle existe toujours, sinon on prend le premier
            new_text = previous_selection if previous_selection in noms_disponibles else noms_disponibles[0]
            self.tournament_spinner.text = new_text
        else:
            self.tournament_spinner.values = []
            self.tournament_spinner.text = "Aucun tournoi"

    def refresh_years(self, *args):
        """ Met à jour les années disponibles en fonction du mode Debug """
        app = App.get_running_app()
        if not hasattr(app, 'app_config') or not app.app_config:
            self.year_spinner.text = _("spinner_loading")
            return
        try:
            current_selection = str(self.year_spinner.text)
            is_debug = getattr(app, 'debug_mode', False)
            tournois = app.app_config.get("tournoi", {}).get("tournois", [])
            years_to_show = set()
            for t in tournois:
                year_val = t.get("annee")
                if year_val is None: continue
                
                year_str = str(year_val).strip()
                if not year_str: continue
                
                if is_debug:
                    years_to_show.add(year_str) # On voit tout (2024 + 2024_TEST)
                else:
                    if year_str.isdigit(): # Uniquement 2024, 2025...
                        years_to_show.add(year_str)

            all_y = sorted(list(years_to_show), reverse=True)
            if all_y:
                self.year_spinner.values = all_y
                # Si l'année sélectionnée n'existe plus dans la liste filtrée, on reset
                
                self._is_initializing = False
                
                
                if current_selection not in all_y:
                    self.year_spinner.text = all_y[0]
                else:
                    # On force le déclenchement de update_tournaments_list
                    self.update_tournaments_list(self.year_spinner, self.year_spinner.text)
            
            else:
                self.year_spinner.values = []
                self.year_spinner.text = "Aucune donnée" 
        except Exception as e:
            print(f"[ERREUR-UI] refresh_years : {e}")

    def load_selected_tournament(self, spinner, nom_pur, force=False):
        """ Déclenche le chargement avec un léger délai pour laisser l'UI s'actualiser """
        if getattr(self, '_is_initializing', False) and not force:
            return
        if nom_pur in [_("spinner_tournament"), "Choisir Tournoi", "Aucun tournoi", "", None]: 
            return

        # On ne change PAS le texte ici pour éviter de voir "Chargement" si le fichier est en cache.
        # Le simple fait de sortir de la fonction permet à Kivy de passer le bouton en bleu.
        Clock.schedule_once(lambda dt: self._execute_load_logic(nom_pur, force), 0.05)

    def _execute_load_logic(self, nom_pur, force):
        """ Logique de décision : Cache local (rapide) ou Réseau (lent) """
        app = App.get_running_app()
        year = self.year_spinner.text
        tournois_cache = app.app_config.get("tournoi", {}).get("tournois", [])

        # --- 1. IDENTIFICATION DE L'ENTRÉE ---
        entry = next((t for t in tournois_cache if t.get("nom") == nom_pur 
                      and str(t.get("annee")) == year and t.get("type") == "save"), None)
        
        if not entry:
            entry = next((t for t in tournois_cache if t.get("nom") == nom_pur 
                          and str(t.get("annee")) == year), None)
        
        if not entry: 
            return

        # ========================================================
        # NOUVEAU : SYNCHRONISATION DU SERVICE D'ARRIÈRE-PLAN
        # ========================================================
        #url_pour_service = entry.get("url")
        #if url_pour_service and hasattr(app, 'update_service_monitoring'):
        #    # On envoie l'URL au service via la méthode de MyApp
        #    nom_complet = f"{nom_pur} {year}"
        #    app.update_service_monitoring(url_pour_service, nom_complet)
        # ========================================================

        # --- 2. VÉRIFICATION DU CACHE ---
        file_id = entry["url"].split("id=")[-1]
        ext = "json" if entry.get("type") == "save" else "yaml"
        local_path = os.path.join(app.user_data_dir, f"tournoi_{file_id}.{ext}")

        # Si le fichier existe et qu'on ne force pas le reload, chargement INSTANTANÉ
        if os.path.exists(local_path) and not force:
            try:
                print(f"[FAST-LOAD] Lecture : {local_path}")
                with open(local_path, "r", encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    if ext == "json":
                        t_logic = TournoiLogic.from_json(json.loads(content))
                    else:
                        t_logic = TournoiLogic(yaml.safe_load(content))
                
                self.finalize_ui_update(t_logic, nom_pur)
                return
            except Exception as e:
                print(f"[FAST-LOAD] Erreur lecture cache, passage au réseau: {e}")

        # --- 3. SI RÉSEAU OU FORCE ---
        self.label_titre_centre.text = f"[color=ffff00]{_('loading')}...[/color]"

        def threaded_load():
            t_logic = None
            # On utilise l'entry déjà trouvée plus haut
            is_json = (entry.get("type") == "save")
            t_logic = self._download_and_parse(entry["url"], is_json=is_json, force_download=force)
            
            Clock.schedule_once(lambda dt: self.finalize_ui_update(t_logic, nom_pur), 0)

        threading.Thread(target=threaded_load, daemon=True).start()

    def finalize_ui_update(self, t_logic, nom_pur):
        """ Décide si on rafraîchit juste les scores ou si on reconstruit tout """
        if not t_logic:
            self.label_titre_centre.text = "[color=ff0000]Erreur réseau[/color]"
            return
    
        # Signature pour détecter si la structure (nombre de matchs) a changé
        structure_signature = f"{nom_pur}_{len(t_logic.matchs)}"
        old_signature = getattr(self, '_current_structure_sig', None)
    
        # On vérifie si l'UI est déjà peuplée et si la structure est identique
        can_update_scores_only = (
            old_signature == structure_signature and
            hasattr(self, 'score_widgets') and self.score_widgets and
            self.content_container.children 
        )
    
        self._current_structure_sig = structure_signature
        self.current_tournoi = t_logic
        
        # Mise à jour de l'en-tête (Date)
        date_tournoi = getattr(t_logic, 'date', "Date inconnue")
        self.label_titre_centre.text = f"[b]{date_tournoi}[/b]"
        self.update_refresh_timestamp()
    
        if can_update_scores_only:
            try:
                # --- CORRECTION ICI ---
                # On ne met à jour que ce qui est actuellement visible
                if self.current_tab == "matchs":
                    # Mise à jour fluide des scores uniquement (sans vider le layout)
                    self.update_scores_only(t_logic)
                else:
                    # On est sur l'onglet classement : on vide et on reconstruit 
                    # car le classement change souvent de structure (ordre des lignes)
                    self.content_container.clear_widgets()
                    self.build_classement_view()
                    
            except Exception as e:
                print(f"[FLUID-UPDATE] Erreur, repli sur reconstruction complète: {e}")
                self._do_rebuild(t_logic)
        else:
            # Structure différente ou premier chargement : reconstruction totale
            self._do_rebuild(t_logic)



    def _reconstruct_ui(self, t_logic):
        """ Centralise la reconstruction pour éviter la répétition """
        print("[UI] Reconstruction complète du tableau")
        self._last_matchs_hash = None 
        self.score_widgets = {}       
        self.matchs_layout.clear_widgets() # Optionnel mais propre
        self.build_matchs_view(t_logic)
    
    def _download_and_parse(self, url, is_json=False, force_download=False):
        """ Optimisé : Téléchargement intelligent par comparaison de Hash MD5 """
        app = App.get_running_app()
        file_id = url.split("id=")[-1]
        ext = "json" if is_json else "yaml"
        filename = f"tournoi_{file_id}.{ext}"
        local_path = os.path.join(app.user_data_dir, filename)
        remote_bytes = None
        local_bytes = b""
        # --- ÉTAPE 1 : RÉCUPÉRER LE HASH LOCAL ---
        if os.path.exists(local_path):
            try:
                with open(local_path, "rb") as f:
                    local_bytes = f.read()
            except Exception as e:
                print(f"[CACHE] Erreur lecture binaire : {e}")
        local_hash = hashlib.md5(local_bytes).hexdigest()
        # --- ÉTAPE 2 : RÉCUPÉRATION DISTANTE ---
        # Si on n'a pas de cache ou si on force le rafraîchissement
        if force_download or not os.path.exists(local_path):
            print(f"[NETWORK] Vérification/Téléchargement : {filename}")
            direct_url = f"https://drive.google.com/uc?export=download&id={file_id}"
            try:
                verify_mode = certifi.where() if platform == 'android' else False
                r = requests.get(direct_url, timeout=10, verify=verify_mode)
                r.raise_for_status()
                remote_bytes = r.content # Octets bruts
                remote_hash = hashlib.md5(remote_bytes).hexdigest()
                if remote_hash == local_hash:
                    print(f"[NETWORK] Hash identique ({remote_hash[:8]}). Pas d'écriture disque.")
                    # On utilise les octets locaux déjà chargés pour le parsing
                    final_bytes = local_bytes 
                else:
                    print(f"[NETWORK] Nouveau contenu ! Mise à jour du fichier local.")
                    with open(local_path, "wb") as f:
                        f.write(remote_bytes)
                    final_bytes = remote_bytes
            except Exception as e:
                print(f"[NETWORK] Échec : {e}")
                final_bytes = local_bytes # Repli sur le cache local en cas d'erreur
        else:
            # Cas normal : chargement simple du cache existant
            print(f"[CACHE] Chargement direct du cache local.")
            final_bytes = local_bytes
        # --- ÉTAPE 3 : PARSING (Transformation octets -> objets Python) ---
        if final_bytes:
            try:
                # On décode les octets en texte UTF-8 pour le parser
                content_text = final_bytes.decode('utf-8', errors='ignore')
                if is_json:
                    return TournoiLogic.from_json(json.loads(content_text))
                return TournoiLogic(yaml.safe_load(content_text))
            except Exception as e:
                print(f"[PARSING] Erreur sur {filename} : {e}")
        return None
    
    def _update_bg(self, instance, value):
        self.rect_bg.pos = instance.pos
        self.rect_bg.size = instance.size
        
    def _update_rect_header(self, instance, value):
        """Met à jour le rectangle de fond de l'en-tête bleu"""
        if hasattr(self, 'rect_header'):
            self.rect_header.pos = instance.pos
            self.rect_header.size = instance.size

    def _update_label_text_size(self, instance, value):
        """Ajuste la zone de rendu du texte à la taille du Label pour le centrage"""
        instance.text_size = value
        
    ###########################################################################################################
    ###########################################################################################################
    ###########################################################################################################
    
    def update_scores_only(self, tournoi):
        try:
            if not hasattr(self, 'score_widgets') or not self.score_widgets:
                return
    
            t_data = tournoi.tournoi_data if isinstance(tournoi.tournoi_data, dict) else {}
            
            # 1. État des poules
            tournoi.poules_terminees = all(m.get("SA") is not None and m.get("SB") is not None for m in tournoi.matchs)
            poules_terminees = tournoi.poules_terminees
    
            # 2. Reconstruction de la liste de données (Ordre identique au build_matchs_view)
            # On commence par les poules
            all_matchs_data = list(getattr(tournoi, 'matchs', []))
            
            # On prépare les phases finales
            phases_list = getattr(tournoi, "phases_finales", []) or t_data.get("phases_finales", [])
            phases_map = {p.get("tour"): p for p in phases_list if isinstance(p, dict)}
            
            config_dict = getattr(tournoi, 'config', {})
            phases_cfg = config_dict.get("phases_finales", {})
            debut_yaml = phases_cfg.get("debut", "huitieme").lower() if isinstance(phases_cfg, dict) else "huitieme"
    
            tour_order = ["huitieme", "quart", "demi", "finale"]
            
            # On détermine à quel moment insérer les matchs de classement
            for tour_name in tour_order:
                # Matchs du tour principal
                main_phase = phases_map.get(tour_name) or phases_map.get(tour_name + "s")
                if main_phase:
                    all_matchs_data.extend(main_phase.get("matchs", []))
                
                # INSERTION CRITIQUE : Matchs de classement après le premier tour
                if tour_name == debut_yaml:
                    # On cherche spécifiquement les phases de type classement
                    for p in phases_list:
                        if not isinstance(p, dict): continue
                        m_list = p.get("matchs", [])
                        if any(m.get("type") == "classement" for m in m_list if isinstance(m, dict)):
                            # Pour éviter les doublons si déjà ajouté par main_phase
                            for m_cl in m_list:
                                if m_cl not in all_matchs_data:
                                    all_matchs_data.extend([m_cl])
    
                # Petite Finale après les demis
                if tour_name == "demi":
                    pf_phase = phases_map.get("petite_finale") or phases_map.get("petite-finale")
                    if pf_phase:
                        m_pf = pf_phase.get("matchs", [])
                        if m_pf and m_pf[0] not in all_matchs_data:
                            all_matchs_data.extend(m_pf)
    
            # 3. Mise à jour des widgets
            sorted_indices = sorted(self.score_widgets.keys())
            match_ptr = 0
            
            for row_idx in sorted_indices:
                if match_ptr < len(all_matchs_data):
                    widget_score = self.score_widgets[row_idx]
                    m_data = all_matchs_data[match_ptr]
                    row_layout = widget_score.parent
                    
                    if not row_layout or len(row_layout.children) < 6:
                        continue
    
                    # --- MISE À JOUR DU SCORE ---
                    sa, sb = m_data.get("SA"), m_data.get("SB")
                    score_str = f"[b]{sa} - {sb}[/b]" if (sa is not None and sb is not None) else "[b]-[/b]"
                    
                    # Tirs au but
                    ta, tb = m_data.get("TAB_A"), m_data.get("TAB_B")
                    if ta is not None and tb is not None:
                        score_str += f"\n[size=10sp]({ta}-{tb})[/size]"
                    
                    if widget_score.text != score_str:
                        widget_score.text = score_str
    
                    # --- MISE À JOUR DES NOMS ---
                    # On vérifie si c'est un widget de PF ou de Classement
                    is_dynamic_match = getattr(widget_score, '_is_pf', False) or (m_data.get("type") == "classement")
                    
                    if is_dynamic_match and poules_terminees:
                        nom_A = m_data.get("A")
                        nom_B = m_data.get("B")
                        
                        if nom_A and nom_B:
                            # children[2] = Equipe 1 (Gauche), children[0] = Equipe 2 (Droite)
                            txt_A, txt_B = f"[b]{nom_A}[/b]", f"[b]{nom_B}[/b]"
                            
                            if row_layout.children[2].text != txt_A:
                                row_layout.children[2].text = txt_A
                            if row_layout.children[0].text != txt_B:
                                row_layout.children[0].text = txt_B
                    
                    match_ptr += 1
    
        except Exception as e:
            print(f"[UPDATE-ERROR] : {e}")
            self._last_matchs_hash = "" 
            self.build_matchs_view(tournoi)
        
    def build_matchs_view(self, tournoi, group_color=None):
        app = App.get_running_app()
        is_debug = getattr(app, 'debug_mode', False) # On récupère l'état debug
        
        # ==========================================
        # DEBUG 1 : IDENTIFICATION DU TOURNOI
        # ==========================================
        nom_tournoi = getattr(tournoi, 'nom', 'Inconnu')
        print(f"\n{'='*40}")
        print(f"[DEBUG UI] ANALYSE DU TOURNOI : {nom_tournoi}")
        print(f"[DEBUG UI] Nombre de matchs de poule : {len(getattr(tournoi, 'matchs', []))}")
        print(f"[DEBUG UI] Phases finales actives dans config : {tournoi.config.get('phases_finales', {}).get('actif', False)}")
        
        # Vérification des attributs clés pour les matchs de classement
        has_pf = hasattr(tournoi, 'phases_finales')
        has_phases = hasattr(tournoi, 'phases')
        has_export = hasattr(tournoi, 'classement_matches_for_export')
        print(f"[DEBUG UI] Attributs présents : PF={has_pf}, Phases={has_phases}, Export_Classement={has_export}")
        # ==========================================

        # On ajoute l'état debug dans la chaîne avant de hasher
        current_data_str = str(tournoi.matchs) + str(getattr(tournoi, 'matchs_pf', [])) + str(is_debug)
        current_hash = hashlib.md5(current_data_str.encode()).hexdigest()

        if current_hash == self._last_matchs_hash:
            return # Toujours identique, on sort
        
        self._last_matchs_hash = current_hash
        # ... la suite du code pour vider et reconstruire les widgets
        print("[UI] Matchs modifiés : reconstruction du tableau...")
        
        KIVY_BLUE = (30/255, 58/255, 138/255, 1) 
        container = self.matchs_layout
        
        # --- SÉCURITÉ : ANNULER LE RENDU PRÉCÉDENT ---
        if hasattr(self, '_match_render_ev'):
            Clock.unschedule(self._match_render_ev)
            
        container.clear_widgets()
        app = App.get_running_app()
        self.update_refresh_timestamp()
        
        # ==========================================
        # 1. SÉCURISATION DES DONNÉES (ANTI-CRASH)
        # ==========================================
        # On s'assure que t_data est TOUJOURS un dictionnaire
        t_data = tournoi.tournoi_data if isinstance(tournoi.tournoi_data, dict) else {}
        
        # On sécurise la config
        config_dict = getattr(tournoi, 'config', {})
        if not isinstance(config_dict, dict): config_dict = {}
        
        param = config_dict.get("parametres", {})
        if not isinstance(param, dict): param = {}

        date_text = param.get("date", "")
        if hasattr(self, 'label_titre_centre'):
            self.label_titre_centre.text = f"[b]{date_text}[/b]" if date_text else ""

        column_configs = [
            (_("col_no"), 0.07), (_("col_hour"), 0.13), (_("col_grp"), 0.08),
            (_("col_team1"), 0.31), (_("col_score"), 0.10), (_("col_team2"), 0.31)
        ]

        scroll_parent = container.parent.parent 
        scroll_parent.spacing = 0
        
        
        
        
        # --- BLOC HEADER MATCHS ---
        if hasattr(self, 'matchs_header') and self.matchs_header:
            if self.matchs_header.parent:
                self.matchs_header.parent.remove_widget(self.matchs_header)

        # Création du header
        self.matchs_header = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(40), spacing=2)
        with self.matchs_header.canvas.before:
            Color(*KIVY_BLUE)
            self.rect_header = Rectangle(pos=self.matchs_header.pos, size=self.matchs_header.size)
        
        self.matchs_header.bind(pos=self._update_rect_header, size=self._update_rect_header)

        for text, ratio in column_configs:
            lbl = Label(text=f"[b]{text}[/b]", markup=True, size_hint_x=ratio, color=(1, 1, 1, 1), halign='center', valign='middle', font_size='11sp')
            self.matchs_header.add_widget(lbl)

        # INSERTION PRÉCISE : On l'ajoute au conteneur de l'écran, 
        # mais JUSTE au dessus du ScrollView (souvent l'index 0 ou 1 selon l'ordre)
        # Si ton layout est [Barre Onglet, ScrollView], on l'insère à l'index 1.
        scroll_parent.add_widget(self.matchs_header, index=1) 
        
        # On s'assure qu'il est visible
        self.matchs_header.opacity = 1
        self.matchs_header.height = dp(40)
        
        
        
        
        
        container.spacing = dp(1)

        with container.canvas.before:
            Color(*KIVY_BLUE)
            self.rect_bg = Rectangle(pos=container.pos, size=container.size)
        container.bind(pos=self._update_bg, size=self._update_bg)
        container.spacing = 2

        # --- PRÉPARATION DU SYSTÈME SMOOTH ---
        rows_to_create = []

        def add_row(vals, bg_hex="#FFFFFF", is_bold=False, force_white=False):
            rows_to_create.append({
                "vals": vals, "bg_hex": bg_hex, 
                "is_bold": is_bold, "force_white": force_white
            })

        # ------------------- Logique -------------------
        def parse_duree(d):
            if isinstance(d, int): return timedelta(minutes=d)
            elif isinstance(d, str) and ":" in d:
                mm, ss = map(int, d.split(":"))
                return timedelta(minutes=mm, seconds=ss)
            else: return timedelta(minutes=5)

        pause_td = parse_duree(param.get("pause", 0))
        duree_match_td = parse_duree(param.get("duree_match", 5))
        heure_courante = datetime.strptime(param.get("heure_debut", "09:00"), "%H:%M")

        if not group_color:
            group_color = build_group_colors(tournoi.groupes)

        tournoi.recalc_all()
        if not hasattr(tournoi, 'matchs_pf'):
            tournoi.matchs_pf = []

        match_counter = 1
        pauses = config_dict.get("pauses", {}).get("liste", []) if isinstance(config_dict.get("pauses"), dict) else []
        pause_index = 0

        for m in tournoi.matchs:
            while pause_index < len(pauses):
                p = pauses[pause_index]
                try:
                    p_debut = datetime.strptime(p.get("from", "00:00"), "%H:%M")
                    p_fin = datetime.strptime(p.get("to", "00:00"), "%H:%M")
                except: pause_index += 1; continue
                if p_debut <= heure_courante < p_fin:
                    p_start = heure_courante.strftime("%H:%M")
                    p_end = p_fin.strftime("%H:%M")
                    nom_pause = p.get("nom") or p.get("name") or _("label_pause")
                    add_row(["", p_start, "", nom_pause, f"{p_end}", nom_pause], bg_hex="#FFFF00", is_bold=True)
                    heure_courante = p_fin
                    pause_index += 1
                else: break

            if heure_courante.second > 29: heure_courante += timedelta(minutes=1)
            heure_courante = heure_courante.replace(second=0, microsecond=0)
            m["heure"] = heure_courante.strftime("%H:%M")
            
            g_color = group_color.get(m['groupe'], "#1E3A8A")
            sa = "" if m.get("SA") is None else m["SA"]
            sb = "" if m.get("SB") is None else m["SB"]
            score_str = "-" if (sa == "" and sb == "") else f"{sa} - {sb}"
            
            add_row([match_counter, m["heure"], m["groupe"], m.get("A", ""), score_str, m.get("B", "")], bg_hex=g_color)
            
            match_counter += 1
            heure_courante += duree_match_td + pause_td

        tournoi.poules_terminees = all(m.get("SA") is not None and m.get("SB") is not None for m in tournoi.matchs)
        # On crée une version locale "courte" pour les conditions de cette fonction
        poules_terminees = tournoi.poules_terminees
        
        phases_cfg = config_dict.get("phases_finales_mode") or config_dict.get("phases_finales", {})
        if isinstance(phases_cfg, dict) and phases_cfg.get("actif", False):
            
            # ==========================================
            # DEBUG 2 : ZOOM SUR LA CONFIG CLASSEMENT
            # ==========================================
            opt = config_dict.get("phases_finales_options", {}).get("options", {})
            match_cl_config = phases_cfg.get("match_classement") or opt.get("match_classement")
            print(f"[DEBUG UI] Option match_classement détectée : {match_cl_config}")
            # ==========================================
            
            
            
            add_row(_("title_final_phase"), bg_hex="#000000", is_bold=True, force_white=True)
            
            debut_yaml = phases_cfg.get("debut", "huitieme").lower()
            tour_map = {"huitieme": "HUITIEMES", "quart": "QUARTS", "demi": "DEMIS", "finale": "FINALE"}
            first_round = tour_map.get(debut_yaml, "HUITIEMES")
            tour_order = ["HUITIEMES", "QUARTS", "DEMIS", "FINALE"]
            start_index = tour_order.index(first_round)
            tours_to_play = tour_order[start_index:]
            
            real_teams_dict = getattr(tournoi, "_real_teams_dict_for_export", tournoi.calculer_qualifies())
            bracket = tournoi.distribuer_qualifies_bracket(real_teams_dict).copy()
            
            total_qual = {"HUITIEMES": 16, "QUARTS": 8, "DEMIS": 4, "FINALE": 2}[first_round]
            nb_groupes = len(tournoi.groupes)
            nb_qual_par_groupe = total_qual // nb_groupes
            reste = total_qual % nb_groupes
            team_to_pos = {}
            extra_candidates = []
            for g, eqs in real_teams_dict.items():
                for i, equipe in enumerate(eqs):
                    if i < nb_qual_par_groupe:
                        suffix = "er" if i == 0 else "e"
                        team_to_pos[equipe] = f"{i+1}{suffix} G{g}"
                    elif i == nb_qual_par_groupe:
                        extra_candidates.append((equipe, g))
            for i, (equipe, g) in enumerate(extra_candidates[:reste]):
                rank = nb_qual_par_groupe + 1
                team_to_pos[equipe] = f"Meilleur {rank}e"

            automatique = phases_cfg.get("automatique", True)

            def add_pf_match(h_courante, A, B, tag, duree_td, match_data=None):
                nonlocal match_counter
                start_str = h_courante.strftime("%H:%M")
                bg_hex = cp.get(tag, "#EEEEEE")
                score_display = "-"
                if match_data:
                    sa = match_data.get("SA")
                    sb = match_data.get("SB")
                    if sa is not None and sb is not None:
                        score_display = f"[b]{sa} - {sb}[/b]"
                        ta, tb = match_data.get("TAB_A"), match_data.get("TAB_B")
                        if ta is not None and tb is not None:
                            score_display += f"\n[size=10sp]({ta}-{tb})[/size]"
                
                add_row([match_counter, start_str, "PF", A, score_display, B], bg_hex=bg_hex)
                match_counter += 1
                return h_courante + timedelta(minutes=int(math.ceil(duree_td.total_seconds() / 60)))

            cp = {
                "HUITIEMES": "#1565c0", "QUARTS": "#ef6c00", "DEMIS": "#2e7d32", "FINALE": "#b71c1c",
                "HUITIEMES_MATCH": "#90caf9", "QUARTS_MATCH": "#ffcc80", "DEMIS_MATCH": "#a5d6a7", "FINALE_MATCH": "#ef9a9a",
                "CLASSEMENT_TITLE": "#37474f", "CLASSEMENT_MATCH": "#cfd8dc",
                "PETITE_FINALE": "#6a1b9a", "PETITE_FINALE_MATCH": "#ce93d8"
            }

            for tour_idx, tour in enumerate(tours_to_play):
                add_row(_(f"tour_{tour.lower()}"), bg_hex=cp.get(tour, "#333333"), is_bold=True, force_white=True)
                nb_matchs = len(bracket) // 2
                nouveaux = []
                for i in range(nb_matchs):
                    A_team, B_team = bracket[2*i], bracket[2*i+1]
                    m_data = None
                    mapping_tours = {"HUITIEMES": "huitieme", "QUARTS": "quart", "DEMIS": "demi", "FINALE": "finale"}
                    nom_tour_json = mapping_tours.get(tour, tour.lower())
                    phases_list = getattr(tournoi, "phases_finales", [])
                    if not phases_list:
                        phases_list = t_data.get("phases_finales", [])

                    if isinstance(phases_list, list):
                        target_phase = next((p for p in phases_list if isinstance(p, dict) and (p.get("tour") == nom_tour_json or p.get("tour") == nom_tour_json + "s")), None)
                        if target_phase:
                            matchs_du_tour = target_phase.get("matchs", [])
                            if i < len(matchs_du_tour): m_data = matchs_du_tour[i]

                    if tour == first_round and automatique:
                        A_fallback, B_fallback = team_to_pos.get(A_team, A_team), team_to_pos.get(B_team, B_team)
                    elif tour == first_round and not automatique:
                        pfx = {"huitieme": "H", "quart": "Q", "demi": "D", "finale": "F"}.get(debut_yaml, "H")
                        A_fallback, B_fallback = f"{pfx}{i+1}", f"{pfx}{i+1}"
                    else:
                        A_fallback, B_fallback = A_team, B_team

                    A = m_data["A"] if (poules_terminees and m_data and m_data.get("A") is not None) else A_fallback
                    B = m_data["B"] if (poules_terminees and m_data and m_data.get("B") is not None) else B_fallback

                    heure_courante = add_pf_match(heure_courante, A, B, f"{tour}_MATCH", duree_match_td, match_data=m_data)
                    nouveaux.append(f"{_('label_winner')} {tour[0]}{i+1}")
                    if i != nb_matchs - 1: heure_courante += pause_td
                        
                # --- DÉBUT DU BLOC CORRIGÉ ---
                phases_cfg_opt = config_dict.get("phases_finales_options") or config_dict.get("phases_finales", {})
                opt_dict = phases_cfg_opt.get("options", {}) if isinstance(phases_cfg_opt, dict) else {}
                match_classement = False
                
                
                
                
                
                # --- 1. RÉCUPÉRATION DE L'OPTION (HYBRIDE YAML/JSON) ---
                pf_root = config_dict.get("phases_finales", {})
                pf_mode = config_dict.get("phases_finales_mode", {})
                opt_dict = pf_root.get("options", {}) if isinstance(pf_root, dict) else {}
                
                match_classement = (
                    pf_root.get("match_classement") is True or 
                    opt_dict.get("match_classement") is True or 
                    pf_mode.get("match_classement") is True
                )
                
                if tour_idx == 0 and match_classement:
                    classement_matches = []
                
                    # PRIORITÉ 1 : On cherche des matchs existants dans l'objet tournoi (Données JSON)
                    # On regarde dans 'tournoi.phases' qui est la source de vérité après chargement
                    if hasattr(tournoi, 'phases') and isinstance(tournoi.phases, list):
                        for ph in tournoi.phases:
                            if isinstance(ph, dict):
                                m_list = ph.get('matchs', [])
                                # On extrait uniquement les matchs marqués comme 'classement'
                                found = [m for m in m_list if isinstance(m, dict) and m.get("type") == "classement"]
                                if found:
                                    classement_matches.extend(found)
                                    print(f"[UI] {len(found)} matchs de classement chargés depuis le JSON.")
                
                    # PRIORITÉ 2 : Si le JSON ne contenait pas de matchs (cas du YAML neuf)
                    # On construit les slots dynamiquement pour l'affichage
                    if not classement_matches:
                        print("[UI] Aucun match trouvé dans les données : Génération dynamique (YAML mode).")
                        # Logique de calcul du nombre de matchs (8 équipes -> 2 matchs, 16 équipes -> 4 matchs)
                        nb_matchs_a_creer = 2 if tour == "QUARTS" else (4 if tour == "HUITIEMES" else 0)
                        pfx = "Q" if tour == "QUARTS" else "H"
                
                        for i in range(nb_matchs_a_creer):
                            classement_matches.append({
                                "A": f"Perdant {pfx}{2*i+1}", 
                                "B": f"Perdant {pfx}{2*i+2}", 
                                "type": "classement",
                                "SA": None, "SB": None
                            })
                
                    # --- 2. RENDU DES LIGNES ---
                    if classement_matches:
                        add_row(_("ranking_matches"), bg_hex=cp.get("CLASSEMENT_TITLE", "#333333"), is_bold=True, force_white=True)
                        heure_courante += pause_td
                        
                        for cm_idx, cmatch in enumerate(classement_matches):
                            # On récupère ce qui est écrit dans le match (peut être "FCSM" ou "6e GA")
                            raw_A = cmatch.get("A", "")
                            raw_B = cmatch.get("B", "")
                    
                            # --- LOGIQUE DE SÉCURITÉ ---
                            if not poules_terminees:
                                # SI LES POULES NE SONT PAS FINIES :
                                # On ne veut pas voir "FCSM". On veut voir la position théorique.
                                # On reconstruit le label en fonction de l'index du match.
                                nb_equipes_par_groupe = len(tournoi.groupes.get('A', []))
                                # Le rang se calcule en partant du bas : 6e, 5e, etc.
                                rang = nb_equipes_par_groupe - cm_idx
                                
                                A_disp = f"{rang}e GA"
                                B_disp = f"{rang}e GB"
                            else:
                                # SI LES POULES SONT FINIES :
                                # On affiche le vrai nom de l'équipe.
                                # Si raw_A est déjà le nom du club, on le garde.
                                # Si raw_A est encore le label "6e GA", on cherche le club dans team_to_pos.
                                if "e G" in str(raw_A): # C'est un label théorique
                                    A_disp = next((team for team, pos in team_to_pos.items() if pos == raw_A), raw_A)
                                    B_disp = next((team for team, pos in team_to_pos.items() if pos == raw_B), raw_B)
                                else:
                                    A_disp, B_disp = raw_A, raw_B
                    
                            # Affichage final dans le tableau
                            heure_courante = add_pf_match(
                                heure_courante, A_disp, B_disp, 
                                "CLASSEMENT_MATCH", duree_match_td, 
                                match_data=cmatch
                            )
                            if cm_idx < len(classement_matches) - 1:
                                heure_courante += pause_td
                
                petite_finale_found = phases_cfg_opt.get("petite_finale") or opt_dict.get("petite_finale", False)
                if tour != "FINALE" and not (tour == "DEMIS" and petite_finale_found): heure_courante += pause_td
                bracket = nouveaux
                if tour == "DEMIS" and petite_finale_found:
                    heure_courante += pause_td
                    m_pf_data = None
                    p_list = getattr(tournoi, "phases_finales", [])
                    if not p_list: p_list = t_data.get("phases_finales", [])
                    if isinstance(p_list, list):
                        target = next((p for p in p_list if isinstance(p, dict) and p.get("tour") in ["petite_finale", "petite-finale", "classement"]), None)
                        if target and target.get("matchs"): m_pf_data = target["matchs"][0]
                    p_a = m_pf_data["A"] if (m_pf_data and m_pf_data.get("A")) else f"{_('loser')} D1"
                    p_b = m_pf_data["B"] if (m_pf_data and m_pf_data.get("B")) else f"{_('loser')} D2"
                    add_row(_("third_place_playoff"), bg_hex=cp.get("PETITE_FINALE", "#6a1b9a"), is_bold=True, force_white=True)
                    heure_courante = add_pf_match(heure_courante, p_a, p_b, "PETITE_FINALE_MATCH", duree_match_td, match_data=m_pf_data)
                    heure_courante += pause_td

        self._row_idx = 0
        def render_batch(dt):
            for _ in range(6):
                if self._row_idx >= len(rows_to_create): return False
                r = rows_to_create[self._row_idx]
                base_h = 55 if any('\n' in str(v) for v in r['vals']) else 45
                row = BoxLayout(size_hint_y=None, height=dp(base_h), spacing=dp(2), size_hint_x=1)
                bg_rgb = hex_to_rgb(r['bg_hex'])
                f_size = '12sp' if r['is_bold'] else '11sp'
                if isinstance(r['vals'], str) or (len(r['vals']) == 1):
                    txt = f"[b]{r['vals'] if isinstance(r['vals'], str) else r['vals'][0]}[/b]"
                    row.add_widget(StyledLabel(text=txt, bg_color=bg_rgb, size_hint_x=1, color=((1,1,1,1) if r['force_white'] else (0,0,0,1)), halign='center', valign='middle', font_size='14sp', markup=True))
                else:
                    for i, val in enumerate(r['vals']):
                        if i >= len(column_configs): break
                        lbl = StyledLabel(
                            text=f"[b]{val}[/b]", 
                            bg_color=bg_rgb, 
                            size_hint_x=column_configs[i][1], 
                            color=((1,1,1,1) if r['force_white'] else (0,0,0,1)), 
                            halign='center', valign='middle', 
                            font_size=f_size, markup=True
                        )
                        
                        # --- LA CLÉ : Mémoriser le widget de score ---
                        # Si c'est la colonne des scores (index 4) et qu'on n'est pas sur une ligne de titre/pause
                        if i == 4 and not r['is_bold']:
                            # On utilise l'index de la ligne pour l'identifier
                            self.score_widgets[self._row_idx] = lbl
                            # ASTUCE : On ajoute une propriété personnalisée au widget 
                            # pour savoir s'il s'agit d'un match de poule ou de PF
                            if r['vals'][2] == "PF": # Identifié par le tag 'PF' dans tes colonnes
                                lbl._is_pf = True
                            else:
                                lbl._is_pf = False
                            
                        row.add_widget(lbl)
                container.add_widget(row)
                self._row_idx += 1
            return True

        self._match_render_ev = Clock.schedule_interval(render_batch, 0.02)
        return True

    def build_classement_view(self):
        if not self.current_tournoi:
            return
        
        app = App.get_running_app()
        is_debug = getattr(app, 'debug_mode', False)

        # --- FIX : On ajoute les matchs dans le hash ---
        # Si un score change, le hash changera et la reconstruction se lancera
        current_data_str = str(self.current_tournoi.groupes) + str(self.current_tournoi.matchs) + str(is_debug)
        current_hash = hashlib.md5(current_data_str.encode()).hexdigest()

        # On vérifie aussi si le container est vide (sécurité après un clear_widgets)
        if current_hash == self._last_classement_hash and len(self.classement_layout.children) > 0:
            return

        self._last_classement_hash = current_hash
        
        container = self.classement_layout
        container.clear_widgets()
        
        print("[UI] Classement modifié : reconstruction...")

        container = self.classement_layout
        container.clear_widgets()
        
        # --- CORRECTION 1 : On supprime l'espace automatique entre les lignes ---
        container.spacing = dp(2) # Espace minimal entre les lignes
        container.padding = [0, 0, 0, dp(20)] # Un peu de marge en bas du scroll
        
        if not self.current_tournoi:
            return

        group_colors = build_group_colors(self.current_tournoi.groupes)
        KIVY_BLUE = (30/255, 58/255, 138/255, 1)

        self.current_tournoi.recalculer_classement(preserve_tab=True)
        classement_groupes = self.current_tournoi.classement_par_groupe()

        cols_config = [
            (_("pos"), 0.07), (_("team"), 0.33), (_("pts"), 0.1), 
            (_("played"), 0.08), (_("won"), 0.07), (_("drawn"), 0.07), 
            (_("lost"), 0.07), (_("gf"), 0.07), (_("ga"), 0.07), (_("diff"), 0.07)
        ]

        for g in sorted(classement_groupes.keys()):
            data = classement_groupes[g]

            # Titre du Groupe
            group_label = _("group")
            # --- CORRECTION 2 : On réduit la hauteur du titre (de 50 à 40) ---
            container.add_widget(Label(
                text=f"[b]{group_label} {g}[/b]", 
                markup=True,
                size_hint_y=None, height=dp(40),
                font_size='16sp',
                color=(1, 1, 1, 1)
            ))

            # En-tête du Tableau
            header_layout = BoxLayout(size_hint_y=None, height=dp(30), spacing=1)
            for txt, ratio in cols_config:
                header_layout.add_widget(StyledLabel(
                    text=f"[b]{txt}[/b]", 
                    markup=True, 
                    bg_color=KIVY_BLUE,
                    color=(1, 1, 1, 1),
                    size_hint_x=ratio, 
                    font_size='10sp'
                ))
            container.add_widget(header_layout)

            # Lignes des Équipes
            bg_hex = group_colors.get(g, "#FFFFFF")
            bg_rgb = hex_to_rgb(bg_hex)

            for i, (equipe, d) in enumerate(data, 1):
                # --- CORRECTION 3 : Hauteur de ligne resserrée (de 40 à 35) ---
                row = BoxLayout(size_hint_y=None, height=dp(35), spacing=1)
                
                v, n, dft = d.get("victoires", 0), d.get("nuls", 0), d.get("defaites", 0)
                bp, bc = d.get("bp", 0), d.get("bc", 0)
                
                row_values = [
                    str(i), str(equipe), str(d.get("pts", 0)),
                    str(v + n + dft), str(v), str(n), str(dft),
                    str(bp), str(bc), str(d.get("diff", bp - bc))
                ]

                for idx, val in enumerate(row_values):
                    row.add_widget(StyledLabel(
                        text=f"[b]{val}[/b]",
                        markup=True,
                        bg_color=bg_rgb,
                        color=(0, 0, 0, 1),
                        size_hint_x=cols_config[idx][1],
                        font_size='11sp'
                    ))
                container.add_widget(row)

            # --- CORRECTION 4 : Espace entre deux tableaux de groupes réduit ---
            container.add_widget(BoxLayout(size_hint_y=None, height=dp(15)))
    
    def _update_rect_generic(self, instance, value):
        # Cherche le premier rectangle dans les instructions du canvas
        for instr in instance.canvas.before.children:
            if isinstance(instr, Rectangle):
                instr.pos = instance.pos
                instr.size = instance.size
                break