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
import time  # En haut de ton fichier pour le debug précis


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
        # --- VARIABLES DE CONTRÔLE ---
        self.auto_refresh_event = None
        self.current_tournoi = None 
        self.active_header = None
        self.current_tab = "matchs"
        # --- AJOUT : Dictionnaire de sauvegarde du scroll ---
        self.scroll_positions = {"matchs": 1.0, "classement": 1.0}
        # --- CACHE ---
        self._last_matchs_hash = None
        self._last_classement_hash = None
        self._current_structure_sig = None
        self.score_widgets = {} 
        self.KIVY_BLUE = (30/255, 58/255, 138/255, 1)
        self.YELLOW = (247/255, 236/255, 63/255, 1)
        # Fond bleu
        with self.canvas.before:
            Color(*self.KIVY_BLUE)
            self.rect_bg = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._update_rect, size=self._update_rect)

        root = BoxLayout(orientation="vertical")
        # 1. TOP BAR
        top = BoxLayout(size_hint_y=None, height=dp(120), padding=[dp(5), dp(15), dp(5), dp(15)], spacing=dp(8))
        spinner_kwargs = {
            'size_hint_y': None, 'height': dp(80), 'background_normal': '', 
            'background_color': (1, 1, 1, 0.15), 'color': (1, 1, 1, 1),
            'option_cls': CustomSpinnerOption, 'sync_height': False,
            'font_size': '20sp', 'bold': True
        }
        self.year_spinner = Spinner(text=_("spinner_year"), values=[], **spinner_kwargs)
        self.year_spinner.bind(text=self.update_tournaments_list)
        self.tournament_spinner = Spinner(text=_("spinner_tournament"), values=[], **spinner_kwargs)
        self.tournament_spinner.bind(text=self.load_selected_tournament)
        top.add_widget(self.year_spinner)
        top.add_widget(self.tournament_spinner)
        root.add_widget(top)
        # 2. TAB BAR
        self.tab_bar = BoxLayout(size_hint_y=None, height=dp(85), spacing=dp(10), padding=dp(10))
        root.add_widget(self.tab_bar)
        # 3. HEADER INFO
        self.header_info = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(55), padding=[dp(10), 0])
        self.label_titre_centre = Label(text="", markup=True, bold=True, font_size='18sp', halign='center', valign='middle')
        self.label_titre_centre.bind(size=lambda inst, val: setattr(inst, 'text_size', val))
        self.label_maj_droite = Label(text="", markup=True, size_hint_x=None, width=dp(80), font_size='10sp', color=self.YELLOW, halign='right', valign='middle')
        self.label_maj_droite.bind(size=lambda inst, val: setattr(inst, 'text_size', val))
        self.header_info.add_widget(self.label_titre_centre)
        self.header_info.add_widget(self.label_maj_droite)
        root.add_widget(self.header_info)
        self.root_content = root
        # 4. ZONE DE CONTENU
        self.scroll_matchs = ScrollView(do_scroll_x=False, bar_width=0, size_hint_y=1)
        self.scroll_classement = ScrollView(do_scroll_x=False, bar_width=0, size_hint_y=1)
        self.scroll_mon_equipe = ScrollView(do_scroll_x=False, bar_width=0, size_hint_y=1)
        self.mon_equipe_layout = BoxLayout(orientation='vertical', size_hint_y=None)
        self.mon_equipe_layout.bind(minimum_height=self.mon_equipe_layout.setter('height'))
        self.scroll_mon_equipe.add_widget(self.mon_equipe_layout)
        self.matchs_layout = BoxLayout(orientation='vertical', size_hint_y=None)
        self.matchs_layout.bind(minimum_height=self.matchs_layout.setter('height'))
        self.classement_layout = BoxLayout(orientation='vertical', size_hint_y=None)
        self.classement_layout.bind(minimum_height=self.classement_layout.setter('height'))
        self.scroll_matchs.add_widget(self.matchs_layout)
        self.scroll_classement.add_widget(self.classement_layout)
        # Le root est votre BoxLayout principal, on ajoute le scroll par défaut
        root.add_widget(self.scroll_matchs) 
        self.add_widget(self.root_content)
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
        tabs = [
            ("matchs", _("tab_matches")), 
            ("classement", _("tab_ranking")), 
            ("mon_equipe", "MON ÉQUIPE") # Nouvel onglet
        ]
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

    def get_all_teams_from_tournament(self):
        """Extraction robuste des équipes depuis l'objet TournoiLogic."""
        if not self.current_tournoi:
            return []
        equipes = set()
        # 1. Tenter de récupérer les groupes via l'attribut .groupes de l'objet
        # C'est la méthode la plus fiable si tournoi est une instance de TournoiLogic
        groupes_data = getattr(self.current_tournoi, 'groupes', {})
        # Si groupes_data est un dictionnaire {A: [...], B: [...] }
        if isinstance(groupes_data, dict):
            for liste_noms in groupes_data.values():
                if isinstance(liste_noms, list):
                    for nom in liste_noms:
                        equipes.add(str(nom))
        
        # 2. Sécurité : Si les groupes sont vides, on scanne les matchs
        if not equipes and hasattr(self.current_tournoi, 'matchs'):
            for m in self.current_tournoi.matchs:
                if m.get("A"): equipes.add(str(m.get("A")))
                if m.get("B"): equipes.add(str(m.get("B")))

        return sorted(list(equipes))
    
    def build_mon_equipe_view(self):
        """Construit l'interface pour filtrer les matchs par équipe."""
        self.mon_equipe_layout.clear_widgets()
        if not self.current_tournoi:
            self.mon_equipe_layout.add_widget(Label(text="Aucun tournoi sélectionné", color=(1,1,1,0.5)))
            return
        liste_equipes = self.get_all_teams_from_tournament()
        if not liste_equipes:
            self.mon_equipe_layout.add_widget(Label(text="Aucune équipe trouvée", color=(1,1,1,0.5)))
            return
        # 1. Spinner
        spinner = Spinner(
            text="CHOISIS TON ÉQUIPE",
            values=liste_equipes,
            size_hint_y=None, height=dp(60),
            background_normal='', background_color=(0.97, 0.93, 0.25, 1),
            color=(0, 0, 0, 1), font_size='18sp', bold=True
        )
        spinner.bind(text=self.filter_matches_by_team)
        self.mon_equipe_layout.add_widget(spinner)
        # 2. AJOUT DU HEADER (Style identique à la vue Matchs)
        header = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(30), padding=[dp(5), 0])
        headers = [(_("col_no"), 0.08), (_("col_hour"), 0.12), (_("col_grp"), 0.08), 
                   (_("col_team1"), 0.32), (_("col_score"), 0.08), (_("col_team2"), 0.32)]
        for text, width in headers:
            header.add_widget(Label(text=text, size_hint_x=width, font_size='10sp', color=(1,1,1,0.7)))
        self.mon_equipe_layout.add_widget(header)
        # 3. Conteneur pour les résultats
        self.matches_filtered_container = BoxLayout(orientation='vertical', size_hint_y=None)
        self.matches_filtered_container.bind(minimum_height=self.matches_filtered_container.setter('height'))
        self.mon_equipe_layout.add_widget(self.matches_filtered_container)

    def filter_matches_by_team(self, spinner, team_name):
        # Nettoyage : si l'utilisateur a cliqué sur le texte d'invite
        if team_name == "CHOISIS TON ÉQUIPE":
            return
        # Nettoyage du " v" ajouté manuellement si nécessaire
        clean_team_name = team_name.replace("  v", "")
        self.matches_filtered_container.clear_widgets()
        # Sauvegarde seulement si c'est une vraie équipe
        app = App.get_running_app()
        app.config.set('User', 'favorite_team', clean_team_name)
        app.config.write()
        # Filtrage
        matchs_filtres = [
            m for m in self.current_tournoi.matchs 
            if m.get("A") == clean_team_name or m.get("B") == clean_team_name
        ]
        if not matchs_filtres:
            self.matches_filtered_container.add_widget(Label(text="Aucun match trouvé", height=dp(100), color=(1,1,1,0.5)))
            return
        for match in matchs_filtres:
            self.matches_filtered_container.add_widget(self.create_match_widget(match)) 
        # Mise à jour du texte du spinner pour garder le "v"
        if spinner:
            spinner.text = f"{clean_team_name}"
    
    def normalize_time(self, time_val):
        """Uniformise l'affichage de l'heure en HH:MM."""
        if not time_val:
            return ""
        # Si c'est un objet (ex: datetime du YAML), on formate
        if hasattr(time_val, 'strftime'):
            return time_val.strftime("%H:%M")
        # Si c'est une chaîne (ex: "10:18:00" ou "10:18"), on coupe à 5 caractères
        if isinstance(time_val, str):
            return time_val[:5]
        return str(time_val)
    
    def get_match_number(self, tournoi, match):
        return tournoi.matchs.index(match) + 1
    
    def get_match_real_time(self, target_match):
        """Recalcule l'heure réelle du match en tenant compte des pauses."""
        if not self.current_tournoi:
            return ""
        tournoi = self.current_tournoi
        config_dict = getattr(tournoi, 'config', {}) or {}
        param = config_dict.get("parametres", {}) or {}
        def parse_duree(d):
            if isinstance(d, int):
                return timedelta(minutes=d)
            if isinstance(d, str) and ":" in d:
                mm, ss = map(int, d.split(":"))
                return timedelta(minutes=mm, seconds=ss)
            return timedelta(minutes=5)
        pause_td = parse_duree(param.get("pause", 0))
        duree_match_td = parse_duree(param.get("duree_match", 5))
        heure_courante = datetime.strptime(
            param.get("heure_debut", "09:00"),
            "%H:%M"
        )
        pauses = config_dict.get("pauses", {}).get("liste", [])
        pause_index = 0
        for match in tournoi.matchs:
            # Injection pauses
            while pause_index < len(pauses):
                p = pauses[pause_index]
                try:
                    p_debut = datetime.strptime(
                        p.get("from", "00:00"),
                        "%H:%M"
                    )
                    p_fin = datetime.strptime(
                        p.get("to", "00:00"),
                        "%H:%M"
                    )
                except:
                    pause_index += 1
                    continue
                if p_debut <= heure_courante < p_fin:
                    heure_courante = p_fin
                    pause_index += 1
                else:
                    break
            # Match trouvé
            if match is target_match:
                return heure_courante.strftime("%H:%M")
            heure_courante += duree_match_td + pause_td
        return ""
    
    def create_match_widget(self, match):
        row = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(50), spacing=dp(2))
        # On définit une police plus grande
        font_size = '14sp' 
        # Utilisation de ratios plus agressifs pour gagner de la place
        # 1. Numéro (plus étroit)
        row.add_widget(Label(text=str(self.get_match_number(self.current_tournoi, match)), size_hint_x=0.08, font_size=font_size))
        # 2. Heure
        row.add_widget(Label(text=self.get_match_real_time(match), size_hint_x=0.12, font_size=font_size))
        # 3. Groupe (une seule lettre suffit)
        row.add_widget(Label(text=str(match.get("groupe", "PF")), size_hint_x=0.08, font_size=font_size))
        # 4. Équipe A (32% de l'espace)
        row.add_widget(Label(text=match.get("A", ""), size_hint_x=0.32, font_size=font_size, halign='left', valign='middle'))
        # 5. Score (centré, 8% suffit largement pour "X - Y")
        sa = match.get("SA")
        sb = match.get("SB")
        score_text = f"{sa}-{sb}" if (sa is not None and sb is not None) else "-"
        row.add_widget(Label(text=score_text, size_hint_x=0.08, bold=True, font_size=font_size))
        # 6. Équipe B (32% de l'espace)
        row.add_widget(Label(text=match.get("B", ""), size_hint_x=0.32, font_size=font_size, halign='right', valign='middle'))
        return row
    
    def switch_tab(self, tab_name):
        # 1. Sauvegarder la position du scroll actuel avant de changer
        if self.current_tab == "matchs":
            self.scroll_positions["matchs"] = self.scroll_matchs.scroll_y
        elif self.current_tab == "classement":
            self.scroll_positions["classement"] = self.scroll_classement.scroll_y
        elif self.current_tab == "mon_equipe":
            self.scroll_positions["mon_equipe"] = self.scroll_mon_equipe.scroll_y
        self.current_tab = tab_name
        self.update_tab_bar()
        # 2. Retirer tous les scrolls possibles du root_content
        for scroll in [self.scroll_matchs, self.scroll_classement, self.scroll_mon_equipe]:
            if scroll in self.root_content.children:
                self.root_content.remove_widget(scroll)
        # 3. Ajouter le scroll correspondant à l'onglet et restaurer sa position
        if tab_name == "matchs":
            if len(self.matchs_layout.children) == 0 and self.current_tournoi:
                self.build_matchs_view(self.current_tournoi)
            self.root_content.add_widget(self.scroll_matchs)
            Clock.schedule_once(lambda dt: setattr(self.scroll_matchs, 'scroll_y', self.scroll_positions.get("matchs", 1.0)), 0.1)
        elif tab_name == "classement":
            if len(self.classement_layout.children) == 0:
                self.build_classement_view()
            self.root_content.add_widget(self.scroll_classement)
            Clock.schedule_once(lambda dt: setattr(self.scroll_classement, 'scroll_y', self.scroll_positions.get("classement", 1.0)), 0.1)
        elif tab_name == "mon_equipe":
            # Si le layout est vide, on construit la vue
            if len(self.mon_equipe_layout.children) == 0:
                self.build_mon_equipe_view()
            self.root_content.add_widget(self.scroll_mon_equipe)
            Clock.schedule_once(lambda dt: setattr(self.scroll_mon_equipe, 'scroll_y', self.scroll_positions.get("mon_equipe", 1.0)), 0.1)
            
    def _safe_rebuild(self, t_logic):
        """Reconstruction sécurisée de l'UI"""
        try:
            print(f"[UI] Reconstruction pour {self.current_tab}")
            # 1. Nettoyage des layouts
            self.matchs_layout.clear_widgets()
            self.classement_layout.clear_widgets()
            # 2. Reconstruction selon l'onglet actif
            # Pas besoin de clear/add sur un "wrapper", car ils sont 
            # déjà ajoutés à leurs ScrollView respectifs dans le __init__
            if self.current_tab == "matchs":
                self._last_matchs_hash = None
                self.build_matchs_view(t_logic)
                layout_to_refresh = self.matchs_layout
            elif self.current_tab == "classement":
                self.build_classement_view()
                layout_to_refresh = self.classement_layout
            elif self.current_tab == "mon_equipe":
                self.build_mon_equipe_view()
                layout_to_refresh = self.mon_equipe_layout
            # 3. Forcer la mise à jour de la hauteur du layout concerné
            self._refresh_container_height(layout_to_refresh)
        except Exception as e:
            print(f"[UI CRITICAL ERROR] {e}")
        
    def _do_rebuild(self, t_logic):
        """Reconstruit uniquement le contenu de l'onglet actuellement visible."""
        print(f"[DEBUG] _do_rebuild appele pour {self.current_tab}")
        # Ici aussi, on évite toute manipulation de widget parent/wrapper.
        # On se contente de remplir le layout qui est déjà dans son ScrollView.
        if self.current_tab == "matchs":
            print("[DEBUG] Reconstruction MATCHS")
            self.matchs_layout.clear_widgets()
            self.build_matchs_view(t_logic)
        else:
            print("[DEBUG] Reconstruction CLASSEMENT")
            self.classement_layout.clear_widgets()
            self.build_classement_view()

    def _reconstruct_ui(self, t_logic):
        """ Centralise la reconstruction pour éviter la répétition """
        print("[UI] Reconstruction complete du tableau")
        self._last_matchs_hash = None 
        self.score_widgets = {}       
        self.matchs_layout.clear_widgets() # Optionnel mais propre
        self.build_matchs_view(t_logic)
        
    def _force_layout_refresh(self, container):
        """Force le recalcul des hauteurs dans la scrollview."""
        container.height = container.minimum_height
        # On détermine quel est le ScrollView parent
        scroll_parent = self.scroll_matchs if container == self.matchs_layout else self.scroll_classement
        # Inutile de fixer la hauteur du ScrollView lui-même, Kivy le gère via size_hint_y=1
        print(f"[DEBUG] Hauteur layout apres refresh: {container.height}")
    
    def _refresh_container_height(self, container):
        """Force la mise à jour de la taille après reconstruction."""
        # 1. On force la mise à jour de la hauteur du conteneur en fonction de son contenu
        container.height = container.minimum_height
        # 2. Pas besoin de toucher à la hauteur du ScrollView (il remplit l'espace du root_content)
        # Assurez-vous simplement que le layout est visible
        container.opacity = 1
        print(f"[DEBUG] _refresh_container_height termine. Conteneur={container.height}")
        
    def _structure_signature(self, tournoi, is_debug):
        data = []
        for m in tournoi.matchs:
            data.append((m.get("A"), m.get("B"), m.get("groupe"), m.get("heure")))
        pf = getattr(tournoi, "matchs_pf", [])
        for m in pf:
            data.append((m.get("A"), m.get("B")))
        data.append(is_debug)
        return hashlib.md5(str(data).encode()).hexdigest()

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
        print("[SERVICE] Demarrage ignore (Service supprime)")
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
            print("[AUTO-UPDATE] Arrete")
            
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
        print(f"[TIMER] Prochain rafraichissement dans {minutes} min")
        
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

    def manual_reload(self, *args):
        app = App.get_running_app()
        instance = args[0] if args else None
    
        if instance and hasattr(instance, 'rot'):
            if instance.disabled:
                return
            instance.disabled = True
            
            Animation.cancel_all(instance.rot)
            instance.rot.angle = 0 
            
            # --- DROITE : On cible -36000° pour tourner dans le sens horaire ---
            self._current_anim = Animation(angle=-36000, duration=100.0, t='linear')
            self._current_anim.start(instance.rot)
    
        def perform_load():
            success = True
            try:
                if hasattr(app, 'load_remote_config'):
                    app.load_remote_config()
                
                def force_reload_tournament(dt):
                    current_t_name = self.tournament_spinner.text
                    excluded = [_("spinner_tournament"), "Aucun tournoi", "No tournament", ""]
                    if current_t_name not in excluded:
                        self.load_selected_tournament(self.tournament_spinner, current_t_name, force=True)
                    else:
                        self.update_tournaments_list(self.year_spinner, self.year_spinner.text)
                    self.update_refresh_timestamp()
                    
                Clock.schedule_once(force_reload_tournament, 0.1)
            except Exception as e:
                success = False
    
            Clock.schedule_once(lambda dt: restore_button(success), 1.0)
    
        def restore_button(success):
            if instance and hasattr(self, '_current_anim'):
                Animation.cancel_all(instance.rot)
                
                # --- DROITE : Calcul de la position négative dans le cadran ---
                # Exemple : -750° devient -30° (il reste 330° à parcourir vers la droite pour atteindre -360°)
                position_actuelle = instance.rot.angle % -360
                instance.rot.angle = position_actuelle
                
                # On calcule le temps restant proportionnel pour finir la course jusqu'à -360°
                temps_restant = max(0.1, (-360 - position_actuelle) / -360 * 0.4)
                
                # On termine la course proprement vers -360°
                anim_fin = Animation(angle=-360, duration=temps_restant, t='out_quad')
                
                def final_reset(*args):
                    instance.rot.angle = 0  # Retour à plat propre
                    instance.disabled = False
                    
                anim_fin.bind(on_complete=final_reset)
                anim_fin.start(instance.rot)
    
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
            print(f"[AUTO-UPDATE] Config et Scores actualises a {datetime.now().strftime('%H:%M')}")

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

    def _scores_signature(self, t_logic):
        """ Calcule une empreinte unique représentant uniquement l'état des scores """
        if not t_logic:
            return ""
        scores_data = []
        for m in getattr(t_logic, 'matchs', []):
            scores_data.append((m.get("SA"), m.get("SB"), m.get("TAB_A"), m.get("TAB_B")))
        
        t_data = t_logic.tournoi_data if isinstance(t_logic.tournoi_data, dict) else {}
        phases_list = getattr(t_logic, "phases_finales", []) or t_data.get("phases_finales", [])
        for phase in phases_list:
            if isinstance(phase, dict):
                for m in phase.get("matchs", []):
                    scores_data.append((m.get("SA"), m.get("SB"), m.get("TAB_A"), m.get("TAB_B"), m.get("A"), m.get("B")))
                    
        return hashlib.md5(str(scores_data).encode()).hexdigest()

    def load_selected_tournament(self, spinner, nom_pur, force=False):
        """ Déclenche le chargement avec un léger délai pour laisser l'UI s'actualiser """
        if getattr(self, '_is_initializing', False) and not force:
            return
        if nom_pur in [_("spinner_tournament"), "Choisir Tournoi", "Aucun tournoi", "", None]: 
            return
        
        # 🔥 ANCHOR : Si c'est un reload manuel (force=True), on NE RESET PAS le scroll de l'UI
        if not force:
            self.scroll_positions = {"matchs": 1.0, "classement": 1.0, "mon_equipe": 1.0}
            self.scroll_matchs.scroll_y = 1.0
            self.scroll_classement.scroll_y = 1.0
            self.scroll_mon_equipe.scroll_y = 1.0
            self.mon_equipe_layout.clear_widgets()

        Clock.schedule_once(lambda dt: self._execute_load_logic(nom_pur, force), 0.05)
        
    def _execute_load_logic(self, nom_pur, force):
        """ Logique de décision : Cache local (rapide) ou Réseau (lent) """
        app = App.get_running_app()
        year = self.year_spinner.text
        tournois_cache = app.app_config.get("tournoi", {}).get("tournois", [])
        if not tournois_cache:
            tournois_cache = app.app_config.get("tournois", [])

        entry = next((t for t in tournois_cache if t.get("nom") == nom_pur 
                      and str(t.get("annee")) == year and t.get("type") == "save"), None)
        if not entry:
            entry = next((t for t in tournois_cache if t.get("nom") == nom_pur 
                          and str(t.get("annee")) == year), None)
        if not entry: 
            print(f"[LOAD ERROR] Impossible de trouver le tournoi {nom_pur} ({year}).")
            return

        url_raw = entry.get("url", "")
        file_id = None
        if "id=" in url_raw:
            file_id = url_raw.split("id=")[-1].split("&")[0]
        elif "/d/" in url_raw:
            file_id = url_raw.split("/d/")[-1].split("/")[0]
            
        if not file_id:
            print(f"[LOAD ERROR] URL invalide : {url_raw}")
            return
        ext = "json" if entry.get("type") == "save" else "yaml"
        local_path = os.path.join(app.user_data_dir, f"tournoi_{file_id}.{ext}")

        # --- LOGIQUE DE FINALISATION SMART SANS CLIGNOTEMENT ---
        def finalize(t_logic):
            if not t_logic: 
                return
                
            is_debug = getattr(app, 'debug_mode', False)
            current_struct_sig = self._structure_hash(t_logic, is_debug)
            current_scores_sig = self._scores_signature(t_logic)
            
            # Récupération de la date pour restaurer le titre quoi qu'il arrive
            date_tournoi = getattr(t_logic, 'date', "Date inconnue")
            
            # Décision intelligente : Même tournoi et même structure ?
            if getattr(self, 'current_tournoi', None) and getattr(self, '_current_structure_sig', None) == current_struct_sig:
                # On remet TOUJOURS le vrai titre pour effacer le "(chargement...)"
                self.label_titre_centre.text = f"[b]{date_tournoi}[/b]"
                
                if getattr(self, '_last_scores_hash', None) != current_scores_sig:
                    print("[SMART RELOAD] Structure identique. Injection flash des scores uniquement.")
                    self._last_scores_hash = current_scores_sig
                    self.update_scores_only(t_logic)
                else:
                    print("[SMART RELOAD] Aucun changement detecte.")
                return

            # Si la structure a changé (ou premier chargement), reconstruction complète
            print("[SMART RELOAD] Changement structurel ou initialisation. Reconstruction de l'UI.")
            self.current_tournoi = t_logic
            self._current_structure_sig = current_struct_sig
            self._last_scores_hash = current_scores_sig
            
            # Restauration du titre ici aussi pour le rebuild complet
            self.label_titre_centre.text = f"[b]{date_tournoi}[/b]"
            
            # Synchronisation absolue des hashs pour éliminer l'effet scroll au démarrage
            self._last_matchs_hash = current_struct_sig
            self._last_classement_hash = None  # Force la vue classement à se régénérer
            self.score_widgets = {}
            
            self.matchs_layout.clear_widgets()
            self.classement_layout.clear_widgets()
            self.mon_equipe_layout.clear_widgets() 
            
            self._safe_rebuild(t_logic)
            if self.current_tab == "mon_equipe":
                self.build_mon_equipe_view()

        # --- RECHERCHE ET REPLI CACHE OU RÉSEAU ---
        if os.path.exists(local_path) and not force:
            try:
                print(f"[FAST-LOAD] Lecture du cache : {local_path}")
                with open(local_path, "r", encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    data = json.loads(content) if ext == "json" else yaml.safe_load(content)
                    t_logic = TournoiLogic.from_json(data) if ext == "json" else TournoiLogic(data)
                
                Clock.schedule_once(lambda dt: finalize(t_logic), 0)
                return
            except Exception as e:
                print(f"[FAST-LOAD ERROR] : {e}")

        # Label de chargement discret si c'est un rafraîchissement manuel en tâche de fond
        if force and getattr(self, 'current_tournoi', None):
            self.label_titre_centre.text = f"[b]{getattr(self.current_tournoi, 'date', '')}[/b] [size=14sp][color=ffff00]({_('loading')}...)[/color][/size]"
        else:
            self.label_titre_centre.text = f"[color=ffff00]{_('loading')}...[/color]"

        def threaded_load():
            t_logic = None
            try:
                if hasattr(app, 'preload_latest_tournament'):
                    app.preload_latest_tournament(target_url=url_raw)
                
                if os.path.exists(local_path):
                    with open(local_path, "r", encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                        data = json.loads(content) if ext == "json" else yaml.safe_load(content)
                        t_logic = TournoiLogic.from_json(data) if ext == "json" else TournoiLogic(data)
            except Exception as e:
                print(f"[THREAD-LOAD ERROR] : {e}")
            Clock.schedule_once(lambda dt: finalize(t_logic), 0)
            
        threading.Thread(target=threaded_load, daemon=True).start()

    def finalize_ui_update(self, t_logic, nom_pur):
        """Met à jour le tournoi courant sans clignotement ni effet de scroll."""
        if not t_logic:
            print("[UI ERROR] t_logic est None, annulation du rafraichissement.")
            self.label_titre_centre.text = "[color=ff0000]Erreur réseau[/color]"
            return
            
        app = App.get_running_app()
        is_debug = getattr(app, 'debug_mode', False)
        
        # 1. Calcul des signatures de comparaison
        current_struct_sig = self._structure_hash(t_logic, is_debug)
        current_scores_sig = self._scores_signature(t_logic)
        
        # 2. Si le tournoi est déjà le même et la structure est identique
        if getattr(self, 'current_tournoi', None) and getattr(self, '_current_structure_sig', None) == current_struct_sig:
            if getattr(self, '_last_scores_hash', None) != current_scores_sig:
                self._last_scores_hash = current_scores_sig
                # On met à jour UNIQUEMENT les textes des labels (ZÉRO mouvement d'UI)
                Clock.schedule_once(lambda dt: self.update_scores_only(t_logic), 0)
            return

        # 3. Vrai changement de structure (ou premier chargement) : On reconstruit
        self._last_matchs_hash = current_hash = current_struct_sig
        self._current_structure_sig = current_struct_sig
        self._last_scores_hash = current_scores_sig
        self._last_classement_hash = None
        self.score_widgets = {}
        self.current_tournoi = t_logic
        
        date_tournoi = getattr(t_logic, 'date', "Date inconnue")
        self.label_titre_centre.text = f"[b]{date_tournoi}[/b]"
        Clock.schedule_once(lambda dt: self._safe_rebuild(t_logic), 0)
    
    def _download_and_parse(self, url, is_json=False, force_download=False):
        """ Optimisé : Téléchargement intelligent par comparaison de Hash MD5 (Compatible iOS) """
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
        if force_download or not os.path.exists(local_path):
            print(f"[NETWORK] Verification/Telechargement : {filename}")
            direct_url = f"https://drive.google.com/uc?export=download&id={file_id}"
            try:
                # CORRECTION iOS : certifi est requis pour assurer la chaîne SSL sur iOS/Android de manière homogène
                verify_mode = certifi.where()
                r = requests.get(direct_url, timeout=10, verify=verify_mode)
                r.raise_for_status()
                remote_bytes = r.content 
                remote_hash = hashlib.md5(remote_bytes).hexdigest()
                
                if remote_hash == local_hash:
                    print(f"[NETWORK] Hash identique ({remote_hash[:8]}). Pas d'ecriture disque.")
                    final_bytes = local_bytes 
                else:
                    print(f"[NETWORK] Nouveau contenu ! Mise a jour du fichier local.")
                    with open(local_path, "wb") as f:
                        f.write(remote_bytes)
                    final_bytes = remote_bytes
            except Exception as e:
                print(f"[NETWORK] Echec : {e}")
                final_bytes = local_bytes # Repli sur le cache local
        else:
            print(f"[CACHE] Chargement direct du cache local.")
            final_bytes = local_bytes
        # --- ÉTAPE 3 : PARSING ---
        if final_bytes:
            try:
                content_text = final_bytes.decode('utf-8', errors='ignore')
                if is_json:
                    return TournoiLogic.from_json(json.loads(content_text))
                return TournoiLogic(yaml.safe_load(content_text))
            except Exception as e:
                print(f"[PARSING] Erreur sur {filename} : {e}")
        return None

    # CORRECTIONS ANTI-FUITE : Utilisation de l'instance passée par Kivy plutôt que self
    def _update_bg(self, instance, value):
        if hasattr(instance, 'rect_bg'):
            instance.rect_bg.pos = instance.pos
            instance.rect_bg.size = instance.size
        
    def _update_rect_header(self, instance, value):
        if hasattr(instance, 'rect_header'):
            instance.rect_header.pos = instance.pos
            instance.rect_header.size = instance.size

    def _update_label_text_size(self, instance, value):
        instance.text_size = value
        
    def _structure_hash(self, tournoi, is_debug=False):
        """ Calcule une empreinte basée UNIQUEMENT sur la structure (sans l'ID mémoire) """
        # On extrait une version simplifiée des matchs sans les scores pour figer la structure
        structure_matchs = []
        for m in getattr(tournoi, 'matchs', []):
            structure_matchs.append((m.get("A"), m.get("B"), m.get("groupe"), m.get("type")))
            
        data = {
            "matchs": structure_matchs,
            "phases": getattr(tournoi, "phases_finales", []),
            "groupes": getattr(tournoi, "groupes", {}),
            "debug": is_debug
        }
        return hashlib.md5(str(data).encode()).hexdigest()
    
    def update_scores_only(self, tournoi):
        """ Met à jour les widgets de scores et synchronise le modèle pour le classement """
        try:
            if not hasattr(self, 'score_widgets') or not self.score_widgets:
                return
                
            # Mise à jour de la référence principale de l'application
            self.current_tournoi = tournoi
            
            # On force le modèle de données à recalculer les points et qualifiés
            if hasattr(tournoi, 'recalc_all'):
                tournoi.recalc_all()
                
            t_data = tournoi.tournoi_data if isinstance(tournoi.tournoi_data, dict) else {}
            tournoi.poules_terminees = all(m.get("SA") is not None and m.get("SB") is not None for m in tournoi.matchs)
            poules_terminees = tournoi.poules_terminees
            
            # Extraction propre de la liste ordonnée des matchs
            all_matchs_data = list(getattr(tournoi, 'matchs', []))
            phases_list = getattr(tournoi, "phases_finales", []) or t_data.get("phases_finales", [])
            phases_map = {p.get("tour"): p for p in phases_list if isinstance(p, dict)}
            config_dict = getattr(tournoi, 'config', {})
            phases_cfg = config_dict.get("phases_finales", {})
            debut_yaml = phases_cfg.get("debut", "huitieme").lower() if isinstance(phases_cfg, dict) else "huitieme"
            
            tour_order = ["huitieme", "quart", "demi", "finale"]
            for tour_name in tour_order:
                main_phase = phases_map.get(tour_name) or phases_map.get(tour_name + "s")
                if main_phase:
                    all_matchs_data.extend(main_phase.get("matchs", []))
                if tour_name == debut_yaml:
                    for p in phases_list:
                        if not isinstance(p, dict): continue
                        m_list = p.get("matchs", [])
                        if any(m.get("type") == "classement" for m in m_list if isinstance(m, dict)):
                            for m_cl in m_list:
                                if m_cl not in all_matchs_data:
                                    all_matchs_data.extend([m_cl])
                if tour_name == "demi":
                    pf_phase = phases_map.get("petite_finale") or phases_map.get("petite-finale")
                    if pf_phase:
                        m_pf = pf_phase.get("matchs", [])
                        if m_pf and m_pf[0] not in all_matchs_data:
                            all_matchs_data.extend(m_pf)
                            
            # 1. Injection visuelle des nouveaux scores dans les labels existants
            for row_key, widget_score in self.score_widgets.items():
                match_ptr = getattr(widget_score, '_match_ptr_index', None)
                if match_ptr is not None and match_ptr < len(all_matchs_data):
                    m_data = all_matchs_data[match_ptr]
                    
                    sa, sb = m_data.get("SA"), m_data.get("SB")
                    score_str = f"[b]{sa} - {sb}[/b]" if (sa is not None and sb is not None) else "[b]-[/b]"
                    ta, tb = m_data.get("TAB_A"), m_data.get("TAB_B")
                    if ta is not None and tb is not None:
                        score_str += f"\n[size=10sp]({ta}-{tb})[/size]"
                        
                    if widget_score.text != score_str:
                        widget_score.text = score_str
                        
                    # --- CORRECTION ICI : Gestion indépendante de l'Équipe A et Équipe B ---
                    is_dynamic_match = getattr(widget_score, '_is_pf', False) or (m_data.get("type") == "classement")
                    
                    if is_dynamic_match and poules_terminees:
                        nom_A = m_data.get("A")
                        nom_B = m_data.get("B")
                        
                        # Traitement de l'équipe de gauche (A)
                        if nom_A:
                            lbl_team1 = getattr(widget_score, '_lbl_team1', None)
                            if lbl_team1 and lbl_team1.text != f"[b]{nom_A}[/b]":
                                lbl_team1.text = f"[b]{nom_A}[/b]"
                                
                        # Traitement de l'équipe de droite (B) indépendant
                        if nom_B:
                            lbl_team2 = getattr(widget_score, '_lbl_team2', None)
                            if lbl_team2 and lbl_team2.text != f"[b]{nom_B}[/b]":
                                lbl_team2.text = f"[b]{nom_B}[/b]"

            # 2. Rafraîchissement de l'onglet "Mon Équipe" si l'utilisateur est dessus
            if getattr(self, 'current_tab', None) == "mon_equipe" and hasattr(self, 'matches_filtered_container'):
                app = App.get_running_app()
                fav_team = app.config.get('User', 'favorite_team', fallback="")
                if fav_team and fav_team != "CHOISIS TON ÉQUIPE":
                    self.filter_matches_by_team(None, fav_team)

            # 3. Reconstruction du classement avec le nouveau tournoi recalculé
            if hasattr(self, 'build_classement_view'):
                print("[SMART RELOAD] Reconstruction de la vue Classement basee sur le nouveau modele.")
                self._last_classement_hash = None  
                self.build_classement_view(self.current_tournoi)
    
        except Exception as e:
            print(f"[UPDATE-ERROR] echec de la mise a jour flash, repli global : {e}")
            self._last_matchs_hash = "" 
            self.build_matchs_view(tournoi)
        
    def build_matchs_view(self, tournoi, group_color=None):
        app = App.get_running_app()
        is_debug = getattr(app, 'debug_mode', False)
        current_hash = self._structure_hash(tournoi, is_debug)
        if (self.current_tournoi is tournoi and
            current_hash == self._last_matchs_hash and
            len(self.matchs_layout.children) > 0):
            return
        self._last_matchs_hash = current_hash
        container = self.matchs_layout
        # --- NETTOYAGE ANTI-FUITE MÉMOIRE CRITIQUE ---
        if hasattr(self, '_match_render_ev') and self._match_render_ev:
            Clock.unschedule(self._match_render_ev)
        container.unbind(pos=self._update_bg, size=self._update_bg)
        container.clear_widgets()
        self.score_widgets = {} # Reset complet du dictionnaire de widgets
        self.update_refresh_timestamp()
        t_data = tournoi.tournoi_data if isinstance(tournoi.tournoi_data, dict) else {}
        config_dict = getattr(tournoi, 'config', {}) if isinstance(getattr(tournoi, 'config', {}), dict) else {}
        param = config_dict.get("parametres", {}) if isinstance(config_dict.get("parametres", {}), dict) else {}
        date_text = param.get("date", "")
        if hasattr(self, 'label_titre_centre'):
            self.label_titre_centre.text = f"[b]{date_text}[/b]" if date_text else ""
        column_configs = [
            (_("col_no"), 0.07), (_("col_hour"), 0.13), (_("col_grp"), 0.08),
            (_("col_team1"), 0.31), (_("col_score"), 0.10), (_("col_team2"), 0.31)
        ]
        # --- RE-CRÉATION SÉCURISÉE DU HEADER (INTÉGRÉ DANS CONTAINER) ---
        KIVY_BLUE = (30/255, 58/255, 138/255, 1) 
        self.matchs_header = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(40), spacing=2)
        with self.matchs_header.canvas.before:
            Color(*KIVY_BLUE)
            self.matchs_header.rect_header = Rectangle(pos=self.matchs_header.pos, size=self.matchs_header.size)
        self.matchs_header.bind(pos=self._update_rect_header, size=self._update_rect_header)
        for text, ratio in column_configs:
            lbl = Label(text=f"[b]{text}[/b]", markup=True, size_hint_x=ratio, color=(1, 1, 1, 1), halign='center', valign='middle', font_size='11sp')
            self.matchs_header.add_widget(lbl)
        # Ajout direct au conteneur au lieu du scroll_parent
        container.add_widget(self.matchs_header) 
        container.spacing = dp(2)
        with container.canvas.before:
            Color(*KIVY_BLUE)
            container.rect_bg = Rectangle(pos=container.pos, size=container.size)
        container.bind(pos=self._update_bg, size=self._update_bg)
        rows_to_create = []
        def add_row(vals, bg_hex="#FFFFFF", is_bold=False, force_white=False, match_idx=None, is_pf=False):
            rows_to_create.append({
                "vals": vals, "bg_hex": bg_hex, 
                "is_bold": is_bold, "force_white": force_white,
                "match_idx": match_idx, "is_pf": is_pf
            })

        def parse_duree(d):
            if isinstance(d, int): return timedelta(minutes=d)
            elif isinstance(d, str) and ":" in d:
                mm, ss = map(int, d.split(":"))
                return timedelta(minutes=mm, seconds=ss)
            return timedelta(minutes=5)
        pause_td = parse_duree(param.get("pause", 0))
        duree_match_td = parse_duree(param.get("duree_match", 5))
        heure_courante = datetime.strptime(param.get("heure_debut", "09:00"), "%H:%M")
        if not group_color:
            group_color = build_group_colors(tournoi.groupes)
        tournoi.recalc_all()
        total_match_idx = 0  # Index universel pour mapper avec update_scores_only
        match_counter = 1
        pauses = config_dict.get("pauses", {}).get("liste", []) if isinstance(config_dict.get("pauses"), dict) else []
        pause_index = 0
        # Remplissage des Matchs de Poule
        for m in tournoi.matchs:
            while pause_index < len(pauses):
                p = pauses[pause_index]
                try:
                    p_debut = datetime.strptime(p.get("from", "00:00"), "%H:%M")
                    p_fin = datetime.strptime(p.get("to", "00:00"), "%H:%M")
                except: pause_index += 1; continue
                if p_debut <= heure_courante < p_fin:
                    add_row(["", heure_courante.strftime("%H:%M"), "", p.get("nom") or _("label_pause"), f"{p_fin.strftime('%H:%M')}", ""], bg_hex="#FFFF00", is_bold=True)
                    heure_courante = p_fin
                    pause_index += 1
                else: break

            m["heure"] = heure_courante.strftime("%H:%M")
            g_color = group_color.get(m['groupe'], "#1E3A8A")
            sa = "" if m.get("SA") is None else m["SA"]
            sb = "" if m.get("SB") is None else m["SB"]
            score_str = "-" if (sa == "" and sb == "") else f"{sa} - {sb}"
            add_row([match_counter, m["heure"], m["groupe"], m.get("A", ""), score_str, m.get("B", "")], bg_hex=g_color, match_idx=total_match_idx)
            match_counter += 1
            total_match_idx += 1
            heure_courante += duree_match_td + pause_td
        tournoi.poules_terminees = all(m.get("SA") is not None and m.get("SB") is not None for m in tournoi.matchs)
        poules_terminees = tournoi.poules_terminees
        phases_cfg = config_dict.get("phases_finales", {})
        if isinstance(phases_cfg, dict) and phases_cfg.get("actif", False):
            add_row(_("title_final_phase"), bg_hex="#000000", is_bold=True, force_white=True)
            debut_yaml = phases_cfg.get("debut", "huitieme").lower()
            tour_map = {"huitieme": "HUITIEMES", "quart": "QUARTS", "demi": "DEMIS", "finale": "FINALE"}
            first_round = tour_map.get(debut_yaml, "HUITIEMES")
            tour_order = ["HUITIEMES", "QUARTS", "DEMIS", "FINALE"]
            start_index = tour_order.index(first_round)
            tours_to_play = tour_order[start_index:]
            real_teams_dict = getattr(tournoi, "_real_teams_dict_for_export", tournoi.calculer_qualifies())
            bracket = tournoi.distribuer_qualifies_bracket(real_teams_dict).copy()
            team_to_pos = {}
            for g, eqs in real_teams_dict.items():
                for i, equipe in enumerate(eqs):
                    team_to_pos[equipe] = f"{i+1}{'er' if i==0 else 'e'} G{g}"
            automatique = phases_cfg.get("automatique", True)
            def add_pf_match(h_courante, A, B, tag, duree_td, match_data=None, m_global_idx=None, is_pf_match=False):
                nonlocal match_counter
                start_str = h_courante.strftime("%H:%M")
                bg_hex = cp.get(tag, "#EEEEEE")
                score_display = "-"
                if match_data:
                    sa, sb = match_data.get("SA"), match_data.get("SB")
                    if sa is not None and sb is not None:
                        score_display = f"[b]{sa} - {sb}[/b]"
                        ta, tb = match_data.get("TAB_A"), match_data.get("TAB_B")
                        if ta is not None and tb is not None:
                            score_display += f"\n[size=10sp]({ta}-{tb})[/size]"
                add_row([match_counter, start_str, "PF", A, score_display, B], bg_hex=bg_hex, match_idx=m_global_idx, is_pf=is_pf_match)
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
                    phases_list = getattr(tournoi, "phases_finales", []) or t_data.get("phases_finales", [])
                    if isinstance(phases_list, list):
                        target_phase = next((p for p in phases_list if isinstance(p, dict) and (p.get("tour") == nom_tour_json or p.get("tour") == nom_tour_json + "s")), None)
                        if target_phase:
                            matchs_du_tour = target_phase.get("matchs", [])
                            if i < len(matchs_du_tour): m_data = matchs_du_tour[i]
                    if tour == first_round and automatique:
                        A_fallback = team_to_pos.get(A_team, A_team)
                        B_fallback = team_to_pos.get(B_team, B_team)
                        
                        # --- MODIFICATION ICI : INTERCEPTION ET NETTOYAGE UNIQUEMENT POUR PHASES FINALES ---
                        def nettoyer_libelle_attente(libelle, equipe_id):
                            if poules_terminees:
                                return libelle
                            try:
                                for grp, eqs in real_teams_dict.items():
                                    if equipe_id in eqs:
                                        pos_dans_groupe = eqs.index(equipe_id)
                                        if pos_dans_groupe == 1 and len(real_teams_dict) > nb_matchs:
                                            return "Meilleur 2e"
                                        elif pos_dans_groupe == 2:
                                            return "Meilleur 3e"
                            except:
                                pass
                            return libelle

                        A_fallback = nettoyer_libelle_attente(A_fallback, A_team)
                        B_fallback = nettoyer_libelle_attente(B_fallback, B_team)

                    elif tour == first_round and not automatique:
                        pfx = {"huitieme": "H", "quart": "Q", "demi": "D", "finale": "F"}.get(debut_yaml, "H")
                        A_fallback, B_fallback = f"{pfx}{i+1}", f"{pfx}{i+1}"
                    else:
                        A_fallback, B_fallback = A_team, B_team
                    A = m_data["A"] if (poules_terminees and m_data and m_data.get("A") is not None) else A_fallback
                    B = m_data["B"] if (poules_terminees and m_data and m_data.get("B") is not None) else B_fallback
                    heure_courante = add_pf_match(heure_courante, A, B, f"{tour}_MATCH", duree_match_td, match_data=m_data, m_global_idx=total_match_idx, is_pf_match=True)
                    total_match_idx += 1
                    nouveaux.append(f"{_('label_winner')} {tour[0]}{i+1}")
                    if i != nb_matchs - 1: heure_courante += pause_td
                # --- MATCHS DE CLASSEMENT ---
                opt_dict = phases_cfg.get("options", {}) if isinstance(phases_cfg, dict) else {}
                match_classement = (phases_cfg.get("match_classement") is True or opt_dict.get("match_classement") is True)
                if tour_idx == 0 and match_classement:
                    classement_matches = []
                    if hasattr(tournoi, 'phases') and isinstance(tournoi.phases, list):
                        for ph in tournoi.phases:
                            if isinstance(ph, dict):
                                m_list = ph.get('matchs', [])
                                found = [m for m in m_list if isinstance(m, dict) and m.get("type") == "classement"]
                                if found: classement_matches.extend(found)
                    if not classement_matches:
                        nb_matchs_a_creer = 2 if tour == "QUARTS" else (4 if tour == "HUITIEMES" else 0)
                        pfx = "Q" if tour == "QUARTS" else "H"
                        for i in range(nb_matchs_a_creer):
                            classement_matches.append({"A": f"Perdant {pfx}{2*i+1}", "B": f"Perdant {pfx}{2*i+2}", "type": "classement", "SA": None, "SB": None})
                    if classement_matches:
                        add_row(_("ranking_matches"), bg_hex=cp.get("CLASSEMENT_TITLE", "#333333"), is_bold=True, force_white=True)
                        heure_courante += pause_td
                        for cm_idx, cmatch in enumerate(classement_matches):
                            raw_A, raw_B = cmatch.get("A", ""), cmatch.get("B", "")
                            if not poules_terminees:
                                # --- MODIFICATION ICI : CONSERVATION DES LABELS PAR GROUPE (EX: 2e GA) ---
                                nb_eq_g = len(tournoi.groupes.get('A', []))
                                rang = nb_eq_g - cm_idx
                                A_disp = raw_A if "Perdant" in str(raw_A) else f"{rang}e GA"
                                B_disp = raw_B if "Perdant" in str(raw_B) else f"{rang}e GB"
                            else:
                                A_disp = next((t for t, p in team_to_pos.items() if p == raw_A), raw_A) if "e G" in str(raw_A) else raw_A
                                B_disp = next((t for t, p in team_to_pos.items() if p == raw_B), raw_B) if "e G" in str(raw_B) else raw_B
                            heure_courante = add_pf_match(heure_courante, A_disp, B_disp, "CLASSEMENT_MATCH", duree_match_td, match_data=cmatch, m_global_idx=total_match_idx, is_pf_match=True)
                            total_match_idx += 1
                            if cm_idx < len(classement_matches) - 1: heure_courante += pause_td
                petite_finale_found = phases_cfg.get("petite_finale") or opt_dict.get("petite_finale", False)
                if tour != "FINALE" and not (tour == "DEMIS" and petite_finale_found): heure_courante += pause_td
                bracket = nouveaux
                if tour == "DEMIS" and petite_finale_found:
                    heure_courante += pause_td
                    m_pf_data = None
                    p_list = getattr(tournoi, "phases_finales", []) or t_data.get("phases_finales", [])
                    if isinstance(p_list, list):
                        target = next((p for p in p_list if isinstance(p, dict) and p.get("tour") in ["petite_finale", "petite-finale", "classement"]), None)
                        if target and target.get("matchs"): m_pf_data = target["matchs"][0]
                    p_a = m_pf_data["A"] if (m_pf_data and m_pf_data.get("A")) else f"{_('loser')} D1"
                    p_b = m_pf_data["B"] if (m_pf_data and m_pf_data.get("B")) else f"{_('loser')} D2"
                    add_row(_("third_place_playoff"), bg_hex=cp.get("PETITE_FINALE", "#6a1b9a"), is_bold=True, force_white=True)
                    heure_courante = add_pf_match(heure_courante, p_a, p_b, "PETITE_FINALE_MATCH", duree_match_td, match_data=m_pf_data, m_global_idx=total_match_idx, is_pf_match=True)
                    total_match_idx += 1
                    heure_courante += pause_td
        # --- BATCH RENDERING SECTION (CORRIGÉE POUR LIAISON DES SCORES) ---
        self._row_idx = 0
        def render_batch(dt):
            for _ in range(6):
                if self._row_idx >= len(rows_to_create):
                    return False
                r = rows_to_create[self._row_idx]
                base_h = 55 if any('\n' in str(v) for v in r['vals']) else 45
                row = BoxLayout(
                    size_hint_y=None,
                    height=dp(base_h),
                    spacing=dp(2),
                    size_hint_x=1
                )
                bg_rgb = hex_to_rgb(r['bg_hex'])
                f_size = '12sp' if r['is_bold'] else '11sp'
                if isinstance(r['vals'], str) or (len(r['vals']) == 1):
                    txt = f"[b]{r['vals'] if isinstance(r['vals'], str) else r['vals'][0]}[/b]"
                    row.add_widget(
                        StyledLabel(
                            text=txt,
                            bg_color=bg_rgb,
                            size_hint_x=1,
                            color=((1, 1, 1, 1) if r['force_white'] else (0, 0, 0, 1)),
                            halign='center',
                            valign='middle',
                            font_size='14sp',
                            markup=True
                        )
                    )
                else:
                    labels = []
                    score_label = None
                    for i, val in enumerate(r['vals']):
                        if i >= len(column_configs):
                            break
                        lbl = StyledLabel(
                            text=f"[b]{val}[/b]",
                            bg_color=bg_rgb,
                            size_hint_x=column_configs[i][1],
                            color=((1, 1, 1, 1) if r['force_white'] else (0, 0, 0, 1)),
                            halign='center',
                            valign='middle',
                            font_size=f_size,
                            markup=True
                        )
                        labels.append(lbl)
                        if i == 4:
                            score_label = lbl
                        row.add_widget(lbl)
                    # Une fois TOUS les labels créés
                    if score_label is not None and r['match_idx'] is not None:
                        lbl_t1 = labels[3] if len(labels) > 3 else None
                        lbl_t2 = labels[5] if len(labels) > 5 else None
                        score_label._match_ptr_index = r['match_idx']
                        score_label._is_pf = r['is_pf']
                        score_label._lbl_team1 = lbl_t1
                        score_label._lbl_team2 = lbl_t2
                        self.score_widgets[r['match_idx']] = score_label
                container.add_widget(row)
                self._row_idx += 1
            return True
        self._match_render_ev = Clock.schedule_interval(render_batch, 0.02)

    def _classement_hash(self, tournoi, is_debug=False):
        """ Génère un hash unique dédié exclusivement aux données du classement """
        # On ne se base que sur le dictionnaire des groupes pour le classement
        data = {
            "groupes": getattr(tournoi, "groupes", {}),
            "debug": is_debug
        }
        return hashlib.md5(str(data).encode()).hexdigest()

    def build_classement_view(self, tournoi=None):
        # 🔥 Si on nous passe un tournoi mis à jour, on l'utilise
        if tournoi:
            self.current_tournoi = tournoi
            
        if not self.current_tournoi:
            return
            
        app = App.get_running_app()
        is_debug = getattr(app, 'debug_mode', False)
        
        # 🔥 Utilisation du hash dédié au classement pour ne pas casser le scroll des Matchs
        current_hash = self._classement_hash(self.current_tournoi, is_debug)
        if current_hash == getattr(self, '_last_classement_hash', None) and len(self.classement_layout.children) > 0:
            return
        self._last_classement_hash = current_hash
        
        container = self.classement_layout
        container.clear_widgets()
        container.size_hint_y = None  
        container.spacing = dp(2)
        container.padding = [0, 0, 0, dp(20)]
        print("[UI] Reconstruction du classement...")
        
        group_colors = build_group_colors(self.current_tournoi.groupes)
        KIVY_BLUE = (30/255, 58/255, 138/255, 1)
        
        # 🔥 Forcer le recalcul des points du modèle avant l'affichage
        if hasattr(self.current_tournoi, 'recalc_all'):
            self.current_tournoi.recalc_all()
        self.current_tournoi.recalculer_classement(preserve_tab=True)
        classement_groupes = self.current_tournoi.classement_par_groupe()
        
        cols_config = [
            (_("pos"), 0.07), (_("team"), 0.33), (_("pts"), 0.1), 
            (_("played"), 0.08), (_("won"), 0.07), (_("drawn"), 0.07), 
            (_("lost"), 0.07), (_("gf"), 0.07), (_("ga"), 0.07), (_("diff"), 0.07)
        ]
        for g in sorted(classement_groupes.keys()):
            data = classement_groupes[g]
            container.add_widget(Label(
                text=f"[b]{_('group')} {g}[/b]", 
                markup=True, size_hint_y=None, height=dp(40),
                font_size='16sp', color=(1, 1, 1, 1)
            ))
            header_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(30), spacing=1)
            for txt, ratio in cols_config:
                header_layout.add_widget(StyledLabel(
                    text=f"[b]{txt}[/b]", markup=True, bg_color=KIVY_BLUE,
                    color=(1, 1, 1, 1), size_hint_x=ratio, size_hint_y=1, font_size='10sp'
                ))
            container.add_widget(header_layout)
            bg_rgb = hex_to_rgb(group_colors.get(g, "#FFFFFF"))
            for i, (equipe, d) in enumerate(data, 1):
                row = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(35), spacing=1)
                row_values = [str(i), str(equipe), str(d.get("pts", 0)), 
                              str(d.get("victoires", 0) + d.get("nuls", 0) + d.get("defaites", 0)), 
                              str(d.get("victoires", 0)), str(d.get("nuls", 0)), str(d.get("defaites", 0)), 
                              str(d.get("bp", 0)), str(d.get("bc", 0)), str(d.get("diff", 0))]

                for idx, val in enumerate(row_values):
                    row.add_widget(StyledLabel(
                        text=f"[b]{val}[/b]", markup=True, bg_color=bg_rgb,
                        color=(0, 0, 0, 1), size_hint_x=cols_config[idx][1], size_hint_y=1, font_size='11sp'
                    ))
                container.add_widget(row)
            container.add_widget(BoxLayout(size_hint_y=None, height=dp(15)))
        
        Clock.schedule_once(lambda dt: self._force_layout_refresh(container), 0.1)
    
    def _update_rect_generic(self, instance, value):
        # Cherche le premier rectangle dans les instructions du canvas
        for instr in instance.canvas.before.children:
            if isinstance(instr, Rectangle):
                instr.pos = instance.pos
                instr.size = instance.size
                break