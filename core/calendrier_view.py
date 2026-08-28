# -*- coding: utf-8 -*-
from kivy.utils import platform
import threading
from datetime import datetime
import requests

from kivy.app import App
from kivy.clock import Clock
from kivy.graphics import Color, Line, RoundedRectangle
from kivy.metrics import dp
from kivy.parser import parse_color
from kivy.utils import escape_markup

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.checkbox import CheckBox
from kivy.uix.gridlayout import GridLayout
from kivy.uix.image import Image  # IMPORT OBLIGATOIRE POUR L'ICÔNE
from kivy.uix.label import Label
from kivy.uix.modalview import ModalView
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView

def try_parse(d, f): 
    try: 
        return datetime.strptime(d.strip(), f) 
    except ValueError: 
        return None

class StopPropagationButton(Button):
    """Bouton qui consomme complètement le touch pour empêcher
    la carte EventCard parent de réagir au même clic.
    """

    def on_touch_down(self, touch):
        if self.disabled or self.opacity == 0:
            return super().on_touch_down(touch)

        if self.collide_point(*touch.pos):
            # Signale à la EventCard parente que ce touch appartient
            # à un contrôle enfant et ne doit donc pas ouvrir sa popup.
            parent = self.parent
            while parent is not None:
                if isinstance(parent, EventCard):
                    parent._touch_consumed_by_child = True
                    break
                parent = parent.parent

            touch.grab(self)
            self._touch_started_inside = True

            # On consomme le touch.
            return True

        return super().on_touch_down(touch)

    def on_touch_up(self, touch):
        if touch.grab_current is self:
            touch.ungrab(self)

            if getattr(self, "_touch_started_inside", False):
                self._touch_started_inside = False

                if self.collide_point(*touch.pos):
                    self.dispatch("on_release")

                # Très important : le bouton consomme aussi le touch_up.
                return True

        return super().on_touch_up(touch)

class EventCard(BoxLayout):
    """Carte d'événement avec affichage visuel (ballon) si l'utilisateur est convoqué."""

    def __init__(self, match_id, match_data, categorie=None, on_presence_click=None, **kwargs):
        super().__init__(orientation="vertical", size_hint_y=None, spacing=dp(10), padding=dp(15), **kwargs)
        self.match_id = match_id
        self.match_data = match_data if isinstance(match_data, dict) else {}
        if categorie and isinstance(self.match_data, dict):
            self.match_data.setdefault("categorie", categorie)
        self.categorie, self.on_presence_click_callback = categorie, on_presence_click
        self.active, self._check_events = True, []
        self._touch_consumed_by_child = False

        raw_imgs = self.match_data.get("images", self.match_data.get("flyer", []))
        raw_list = [raw_imgs] if isinstance(raw_imgs, str) else (list(raw_imgs) if isinstance(raw_imgs, list) else [])
        self.image_list = list(dict.fromkeys([src for src in raw_list if src]))

        self.bind(minimum_height=self.setter("height"))

        app = App.get_running_app()
        cfg = app.config if (app and hasattr(app, "config") and app.config.has_section("User")) else None
        try: self.user_font_size = cfg.getint("User", "font_size_factor") if cfg else 18
        except Exception: self.user_font_size = 18
        self.nom_parent = cfg.get("User", "nom_parent", fallback="").strip() if cfg else ""

        with self.canvas.before:
            Color(1, 1, 1, 1)
            self.bg_rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(10)])
        self.bind(pos=self._update_rect, size=self._update_rect)

        # Helper pour instancier rapidement les Labels répétitifs
        def make_lbl(txt, color, size_offset, height=None, halign="center"):
            lbl = Label(
                text=txt,
                markup=True,
                color=color,
                font_size=f"{self.user_font_size + size_offset}sp",
                size_hint_y=None,
                halign=halign,
                valign="middle",
            )
            if height:
                lbl.height = height
            else:
                lbl.bind(
                    width=lambda s, w: setattr(s, "text_size", (w, None)),
                    texture_size=lambda s, t: setattr(s, "height", max(dp(20), t[1])),
                )
            return lbl

        columns_layout = BoxLayout(orientation="horizontal", spacing=dp(15), size_hint_y=None)
        columns_layout.bind(minimum_height=columns_layout.setter("height"))

        date_box = BoxLayout(orientation="vertical", size_hint_x=0.25, spacing=dp(1), size_hint_y=None)
        date_box.bind(minimum_height=date_box.setter("height"))

        evt_type = str(self.match_data.get("type", "EVENEMENT")).upper()
        raw_date = str(self.match_data.get("date", ""))
        heure_key, prefixe = ("heure_rdv", "RDV") if evt_type == "MATCH" else ("heure", "à")
        heure_str = str(self.match_data.get(heure_key, self.match_data.get("heure" if heure_key == "heure_rdv" else "heure_rdv", "N/C")))

        parsed_dt = next((dt for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y") for dt in [try_parse(raw_date, fmt)] if dt), None)
        jours_fr, mois_fr = ["LUN", "MAR", "MER", "JEU", "VEN", "SAM", "DIM"], ["", "JAN", "FEV", "MAR", "AVR", "MAI", "JUIN", "JUIL", "AOUT", "SEP", "OCT", "NOV", "DEC"]
        js = jours_fr[parsed_dt.weekday()] if parsed_dt else "EVENEMENT"
        num = str(parsed_dt.day) if parsed_dt else raw_date
        m = mois_fr[parsed_dt.month] if parsed_dt else ""

        for lbl in [make_lbl(f"[b]{escape_markup(js)}[/b]", (0.7,0.7,0.7,1), -6, dp(18)),
                    make_lbl(f"[b]{escape_markup(num)}[/b]", (0.1,0.3,0.8,1), 4, dp(28)),
                    make_lbl(f"[b]{escape_markup(m)}[/b]", (0.3,0.3,0.3,1), -5, dp(18)),
                    make_lbl(f"{prefixe} {escape_markup(heure_str)}", (0.5,0.5,0.5,1), -6, dp(20))]:
            date_box.add_widget(lbl)

        with columns_layout.canvas.after:
            Color(0.65, 0.65, 0.65, 1)
            self.v_line = Line(points=[], width=1)
        columns_layout.bind(pos=self._update_line, size=self._update_line)

        title_box = BoxLayout(orientation="vertical", size_hint_x=0.75, spacing=dp(2), padding=[dp(12), 0, 0, 0], size_hint_y=None)
        title_box.bind(minimum_height=title_box.setter("height"))

        titre_evt = str(self.match_data.get("titre", "")) or (str(self.match_data.get("adversaire", "")) if evt_type == "MATCH" else "Événement")
        adversaire_evt, lieu_evt = str(self.match_data.get("adversaire", "")), str(self.match_data.get("lieu", ""))

        self.titre_layout = BoxLayout(orientation="horizontal", size_hint_y=None, spacing=dp(5),height=dp(28),)
        self.titre_layout.bind(minimum_height=self.titre_layout.setter("height"))

        self.lbl_title = make_lbl(f"[b]{escape_markup(titre_evt)}[/b]", (0.1, 0.1, 0.3, 1), 0, halign="left")
        self.lbl_title.size_hint_x = 1
        
        self.ball_icon = Image(source="assets/icons/ball.png", size_hint=(None, None), size=(dp(22), dp(22)), pos_hint={"center_y": 0.5}, opacity=0)
        self.badge_box = BoxLayout(orientation="vertical", size_hint_x=None, width=0, spacing=dp(2), size_hint_y=None, pos_hint={"top": 1})
        self.badge_box.bind(minimum_height=self.badge_box.setter("height"))

        for w in [self.lbl_title, self.ball_icon, self.badge_box]: self.titre_layout.add_widget(w)
        title_box.add_widget(self.titre_layout)

        if evt_type == "MATCH" and adversaire_evt:
            title_box.add_widget(make_lbl(f"Adversaire : {escape_markup(adversaire_evt)}", (0.3, 0.3, 0.3, 1), -4, halign="left"))

        sub_text = f"Lieu : {lieu_evt}" if lieu_evt else "Cliquez pour voir les détails et voter"
        title_box.add_widget(make_lbl(escape_markup(sub_text), (0.5, 0.5, 0.5, 1), -5, halign="left"))

        columns_layout.add_widget(date_box)
        columns_layout.add_widget(title_box)
        self.add_widget(columns_layout)

        # --- SECTION COACH : Affichage direct des résultats & votants au niveau de la carte ---
        cat_match = getattr(self, "categorie", None) or self.match_data.get("categorie")
        user_role = app.get_role_for_cat(cat_match) if (app and hasattr(app, "get_role_for_cat")) else "PARENT"

        if user_role in ["ADMIN"]:
            coach_section = self._build_coach_votes_summary()
            if coach_section:
                self.add_widget(coach_section)

        if self.image_list and (media_zone := self._build_media_zone()):
            self.add_widget(media_zone)
        
        self.mettre_a_jour(self.match_data)

    def _build_coach_votes_summary(self):
        """Construit un bloc visible sur la carte montrant le résumé des votants et un bouton d'accès rapide."""
        data = self.match_data or {}
        votes = data.get("votes", {}) or {}
        type_sondage = data.get("type_sondage", "classique")
        sondage_actif = bool(data.get("sondage_actif"))

        if not sondage_actif and not votes:
            return None

        container = BoxLayout(orientation="vertical", size_hint_y=None, height=dp(58), spacing=dp(6), padding=[0, dp(5), 0, 0])
        container.bind(minimum_height=container.setter("height"))

        presents, absents, total_votes = [], [], len(votes)
        if type_sondage == "multiple":
            details_str = f"Total votants : {total_votes}"
        else:
            for n, d in votes.items():
                disp = d.get("disponibilite") if isinstance(d, dict) else d
                if disp == "Présent": presents.append(n)
                elif disp == "Absent": absents.append(n)
            details_str = f"[color=1a8c38][b]Présents : {len(presents)}[/b][/color]  |  [color=d93838][b]Absents : {len(absents)}[/b][/color]  |  Total : {total_votes}"

        lbl_info = Label(
            text=details_str,
            markup=True,
            font_size=f"{self.user_font_size - 4}sp",
            size_hint_y=None,
            height=dp(20),
            halign="left",
            valign="center",
        )
        lbl_info.bind(size=lambda s, z: setattr(s, "text_size", z))
        container.add_widget(lbl_info)

        btn_resultats = StopPropagationButton(
            text="Résultats & Votants",
            size_hint_y=None,
            height=dp(34),
            background_normal="",
            background_color=(0.1, 0.45, 0.85, 1),
            color=(1, 1, 1, 1),
            bold=True,
            font_size=f"{self.user_font_size - 4}sp"
        )
        
        def format_nom_avec_places(nom, dict_vote):
            """Helper pour formater uniquement 'Nom (X places)' pour Valdahon si renseigné."""
            if isinstance(dict_vote, dict):
                # Accepte 'nb_places' ET 'nombre_de_places'
                nb = dict_vote.get("nb_places") if dict_vote.get("nb_places") is not None else dict_vote.get("nombre_de_places")
                if nb is not None:
                    try:
                        nb_int = int(nb)
                        txt_pl = "place" if nb_int <= 1 else "places"
                        return f"{nom} ({nb_int} {txt_pl})"
                    except (ValueError, TypeError):
                        pass
            return nom

        def ouvrir_resultats(instance):
            if type_sondage == "multiple":
                opts = data.get("options_sondage", ["1", "2", "3", "4", "5"])
                t_sond = data.get("titre_sondage_multiple", "Votre Choix")
                sec_m = {f"Option : {o}": [n for n, d in votes.items() if isinstance(d, dict) and str(d.get("choix_multiple")) == str(o)] for o in opts}
                self._afficher_popup_resultats_coach(f"Votes - {t_sond}", sec_m)
            else:
                sec_v = {"Présents": presents, "Absents": absents}
                if data.get("sondage_trajet"):
                    # Calcul des votants Valdahon avec le nombre de places
                    valdahon_list = []
                    total_places_valdahon = 0
                    for n, d in votes.items():
                        if isinstance(d, dict) and d.get("trajet") == "Valdahon":
                            valdahon_list.append(format_nom_avec_places(n, d))
                            # Extraction sécurisée du nombre de places
                            nb = d.get("nb_places") if d.get("nb_places") is not None else d.get("nombre_de_places")
                            if nb is not None:
                                try: total_places_valdahon += int(nb)
                                except (ValueError, TypeError): pass
                    
                    lbl_valdahon = f"Valdahon ({total_places_valdahon} place{'s' if total_places_valdahon > 1 else ''} dispo)" if total_places_valdahon > 0 else "Valdahon (Départ)"
                    sec_v[lbl_valdahon] = valdahon_list
                    sec_v["Stade Adverse"] = [n for n, d in votes.items() if isinstance(d, dict) and d.get("trajet") == "Stade adverse"]
                    sec_v["Besoin Voiture"] = [n for n, d in votes.items() if isinstance(d, dict) and d.get("trajet") == "Besoin voiture"]
                self._afficher_popup_resultats_coach("Résultats des votes", sec_v)

        btn_resultats.bind(on_release=ouvrir_resultats)
        container.add_widget(btn_resultats)

        return container

    def _afficher_popup_resultats_coach(self, titre_votes, sections_dict):
        """Ouvre directement la popup des résultats détaillés des votants pour le Coach."""
        pop_cnt = BoxLayout(orientation="vertical", padding=dp(20), spacing=dp(10))
        with pop_cnt.canvas.before:
            Color(1, 1, 1, 1)
            pop_cnt.bg_rect = RoundedRectangle(pos=pop_cnt.pos, size=pop_cnt.size, radius=[dp(10)])
        pop_cnt.bind(pos=lambda s, v: setattr(s.bg_rect, "pos", v), size=lambda s, v: setattr(s.bg_rect, "size", v))

        lbl_titre = Label(
            text=f"[b]{escape_markup(titre_votes)}[/b]",
            markup=True,
            color=(0.1, 0.3, 0.8, 1),
            font_size=f"{self.user_font_size + 1}sp",
            size_hint_y=None,
            height=dp(35),
            halign="center",
            valign="middle"
        )
        lbl_titre.bind(width=lambda s, w: setattr(s, "text_size", (w, None)))
        pop_cnt.add_widget(lbl_titre)

        sc_v = ScrollView(bar_width=0, size_hint=(1, 1))
        box_r = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(5), padding=dp(5))
        box_r.bind(minimum_height=box_r.setter("height"))

        for sec_title, lst in sections_dict.items():
            lbl_sec = Label(
                text=f"[b]{escape_markup(str(sec_title))} ({len(lst)}) :[/b]",
                markup=True,
                color=(0.1, 0.1, 0.1, 1),
                font_size=f"{self.user_font_size - 1}sp",
                size_hint_y=None,
                height=dp(28),
                halign="left",
                valign="middle"
            )
            lbl_sec.bind(width=lambda s, w: setattr(s, "text_size", (w, None)))
            box_r.add_widget(lbl_sec)

            for item in (lst or ["Aucun"]):
                txt = f"  • {escape_markup(str(item))}" if lst else "  • Aucun"
                lbl_item = Label(
                    text=txt,
                    markup=True,
                    color=(0.6, 0.6, 0.6, 1) if not lst else (0.2, 0.2, 0.2, 1),
                    font_size=f"{self.user_font_size - 2}sp",
                    size_hint_y=None,
                    height=dp(24),
                    halign="left",
                    valign="middle"
                )
                lbl_item.bind(width=lambda s, w: setattr(s, "text_size", (w, None)))
                box_r.add_widget(lbl_item)

            box_r.add_widget(BoxLayout(size_hint_y=None, height=dp(8)))

        sc_v.add_widget(box_r)
        pop_cnt.add_widget(sc_v)

        sub_pop = ModalView(size_hint=(0.85, 0.75), auto_dismiss=True, background_color=(0, 0, 0, 0.6))
        
        btn_fermer = Button(
            text="Fermer",
            size_hint_y=None,
            height=dp(42),
            background_normal="",
            background_color=(0.82, 0.82, 0.85, 1),
            color=(0.15, 0.15, 0.15, 1),
            bold=True,
            font_size=f"{self.user_font_size - 2}sp"
        )
        btn_fermer.bind(on_release=lambda x: sub_pop.dismiss())
        
        pop_cnt.add_widget(btn_fermer)
        sub_pop.add_widget(pop_cnt)
        sub_pop.open()

    def _est_convoque(self):
        if not self.match_data:
            return False
            
        norm = lambda s: " ".join(str(s or "").strip().lower().split())
        raw_convs = (
            self.match_data.get("joueurs_convoques") 
            or self.match_data.get("convocations") 
            or self.match_data.get("convoques") 
            or []
        )
        convs = [norm(self._obtenir_nom_joueur(j)) for j in raw_convs]
        if not convs:
            return False
    
        cat = getattr(self, "categorie", None) or self.match_data.get("categorie")
        associes = [norm(self._obtenir_nom_joueur(j)) for j in (self.get_joueurs_associes_pour_parent(self.nom_parent, cat) or [])]
        
        # Vérification exacte du nom complet plutôt qu'une inclusion partielle (in c)
        for a in associes:
            if not a:
                continue
            for c in convs:
                if a == c:  # Égalité exacte recommandée pour éviter les doublons de prénoms/noms
                    return True
        return False

    def _obtenir_nom_joueur(self, joueur):
        if isinstance(joueur, dict):
            nom = str(joueur.get("nom", "") or "").strip()
            prenom = str(joueur.get("prenom", "") or "").strip()
            if nom and prenom:
                return f"{nom} {prenom}".strip()
            return (nom or prenom).strip()
        return str(joueur or "").strip()

    def get_joueurs_associes_pour_parent(self, nom_parent, categorie_cible=None):
        if not (app := App.get_running_app()): return []
        match_cat = self.match_data.get("categorie") if isinstance(getattr(self, "match_data", None), dict) else None
        cat = str(categorie_cible or getattr(self, "categorie", None) or match_cat or (app.get_categorie_courante() if hasattr(app, "get_categorie_courante") else "") or "").strip().lower()
        if not cat: return []

        if hasattr(app, "get_joueur_associe_pour_cat"):
            try:
                if jl := app.get_joueur_associe_pour_cat(cat):
                    if isinstance(jl, (list, tuple, set)): return [str(j).strip() for j in jl if j and str(j).strip()]
                    if isinstance(jl, dict): return [f"{jl.get('nom', '')} {jl.get('prenom', '')}".strip()] if f"{jl.get('nom', '')} {jl.get('prenom', '')}".strip() else []
                    return [j.strip() for j in str(jl).split(",") if j.strip()]
            except Exception as e: print(f"[ERREUR] get_joueur_associe_pour_cat({repr(cat)}) : {e}")

        if not (p_clean := str(nom_parent or "").strip().lower()): return []

        joueurs = []
        for j in (getattr(app, "_cache_data", {}).get(cat, {}).get("tous_les_joueurs", []) or []):
            if isinstance(j, dict) and str(j.get("parent", j.get("nom_parent", ""))).strip().lower() == p_clean:
                if (full := f"{j.get('nom', '')} {j.get('prenom', '')}".strip()) and full not in joueurs:
                    joueurs.append(full)

        role = app.get_role_for_cat(cat) if hasattr(app, "get_role_for_cat") else "PARENT"
        return joueurs or ([f"Coach / Admin ({nom_parent})"] if role == "ADMIN" else [])

    def ouvrir_popup_choix_enfants_vote(self, match_id, target_cat, joueurs_associes, choix, choix_trajet, second_vote, choix_multiple, nb_places=None):
        content = BoxLayout(orientation="vertical", padding=dp(15), spacing=dp(10))
        with content.canvas.before:
            Color(0.95, 0.95, 0.97, 1)
            self_bg = RoundedRectangle(pos=content.pos, size=content.size, radius=[dp(15)])
        content.bind(pos=lambda o, v: setattr(self_bg, "pos", v), size=lambda o, v: setattr(self_bg, "size", v))

        content.add_widget(Label(text="[b]Pour qui souhaitez-vous voter ?[/b]", markup=True, size_hint_y=None, height=dp(35), color=(0.1, 0.1, 0.15, 1), font_size=dp(18)))

        scroll, grid, checkboxes_dict = ScrollView(size_hint=(1, 1), bar_width=0), GridLayout(cols=1, size_hint_y=None, spacing=dp(8)), {}
        grid.bind(minimum_height=grid.setter("height"))

        for item in joueurs_associes:
            cle = str(item).strip() if not isinstance(item, dict) else f"{item.get('nom', '')} {item.get('prenom', '')}".strip()
            if not cle: continue
            
            row = BoxLayout(size_hint_y=None, height=dp(45), spacing=dp(10))
            chk = CheckBox(size_hint_x=None, width=dp(40), active=False)
            checkboxes_dict[cle] = chk
            
            lbl = Label(text="Coach / Staff" if cle.startswith("COACH_") else cle, markup=cle.startswith("COACH_"), color=(0.2, 0.2, 0.2, 1), halign="left", valign="middle")
            lbl.bind(width=lambda s, w: setattr(s, "text_size", (w, None)))
            row.add_widget(chk); row.add_widget(lbl)
            grid.add_widget(row)

        scroll.add_widget(grid)
        content.add_widget(scroll)

        btn_valider = Button(text="Valider le vote", size_hint_y=None, height=dp(45), background_normal="", background_color=(0.15, 0.65, 0.35, 1), color=(1, 1, 1, 1), bold=True)
        content.add_widget(btn_valider)

        popup = ModalView(size_hint=(0.85, 0.6), auto_dismiss=True, background_color=(0, 0, 0, 0.6))
        popup.add_widget(content)

        def on_valider(instance):
            if selectionnes := [cle for cle, chk in checkboxes_dict.items() if chk.active]:
                for cible in selectionnes:
                    self.envoyer_vote(id_match=match_id, categorie=target_cat, choix=choix, choix_trajet=choix_trajet, second_vote=second_vote, choix_multiple=choix_multiple, joueur_concerne=cible, nb_places=nb_places, _ignorer_verification_enfants=True)
                popup.dismiss()

        btn_valider.bind(on_release=on_valider)
        popup.open()
        
    def envoyer_vote(self, id_match, categorie=None, choix=None, choix_trajet=None, second_vote=None, choix_multiple=None, joueur_concerne=None, nb_places=None, _ignorer_verification_enfants=False):
        if not (app := App.get_running_app()): return print("[ERREUR VOTE] Application Kivy introuvable.")

        target_cat = categorie or getattr(self, "categorie", None) or (app.get_categorie_courante() if hasattr(app, "get_categorie_courante") else None) or "PROBLEME"

        cfg_parent = app.config.get("User", "nom_parent", fallback="").strip() if hasattr(app, "config") and app.config.has_section("User") else ""
        header_parent = (app.get_user_header() or {}).get("nom_parent", "") if hasattr(app, "get_user_header") else ""
        vrai_parent = cfg_parent if cfg_parent and cfg_parent.lower() != "anonymous" else str(getattr(self, "nom_parent", "") or getattr(app, "nom_parent", "") or getattr(self, "votant_courant", "") or header_parent).strip()

        if not vrai_parent or vrai_parent.lower() == "anonymous": return print("[ERREUR VOTE] Aucun parent connecte identifie.")

        self.nom_parent = vrai_parent
        joueurs_associes = self.get_joueurs_associes_pour_parent(vrai_parent, target_cat) or []

        if len(joueurs_associes) > 1 and not _ignorer_verification_enfants and not joueur_concerne:
            return self.ouvrir_popup_choix_enfants_vote(id_match, target_cat, joueurs_associes, choix, choix_trajet, second_vote, choix_multiple, nb_places=nb_places)

        joueur_cible = joueur_concerne or (joueurs_associes[0] if len(joueurs_associes) == 1 else vrai_parent)
        self._executer_envoi_vote(match_id=id_match, categorie=target_cat, choix=choix, choix_trajet=choix_trajet, choix_multiple=choix_multiple, second_vote=second_vote, joueur_concerne=joueur_cible, nb_places=nb_places)

    def on_presence_click(self, match_id, categorie=None, choix=None, choix_trajet=None, choix_multiple=None, second_vote=None, joueur_concerne=None, nb_places=None, _ignorer_verification_enfants=False):
        if not match_id: return print("[ERREUR] Tentative de vote sans ID de match.")
        
        self.envoyer_vote(
            id_match=match_id, 
            categorie=categorie or getattr(self, "categorie", None), 
            choix=choix, 
            choix_trajet=choix_trajet, 
            second_vote=second_vote, 
            choix_multiple=choix_multiple, 
            joueur_concerne=joueur_concerne or getattr(self, "joueur_concerne", None), 
            nb_places=nb_places,
            _ignorer_verification_enfants=_ignorer_verification_enfants
        )

    def _executer_envoi_vote(self, match_id, categorie, choix, choix_trajet, choix_multiple, second_vote, joueur_concerne, nb_places=None):
        app = App.get_running_app()
        target_cat = categorie or getattr(app, "categorie_courante", "U14_U15")
        
        p_cfg = app.config.get("User", "nom_parent", fallback="").strip() if app and hasattr(app, "config") and app.config.has_section("User") else ""
        nom_parent = (self.nom_parent or "").strip()
        nom_parent = p_cfg if (not nom_parent or nom_parent.lower() == "anonymous") else nom_parent
        if not nom_parent: return print("[ERREUR VOTE] Nom du parent introuvable.")

        joueur = (joueur_concerne or "").strip()
        payload = {
            "id_sondage": match_id, 
            "nom_parent": nom_parent, 
            "nom_joueur_concerne": joueur, 
            **{k: v for k, v in [("choix", choix), ("choix_trajet", choix_trajet), ("choix_multiple", choix_multiple), ("second_vote", second_vote), ("nombre_de_places", nb_places)] if v is not None}
        }

        def envoyer_requete():
            try:
                print(f"[VOTE] Categorie = {target_cat} | Parent = {nom_parent!r} | Joueur = {joueur!r} | Places = {nb_places}")
                api_url = getattr(app, "api_url", "https://fcvv-api.onrender.com")
                res = requests.post(f"{api_url}/voter/{target_cat}", json=payload, headers={"nom_parent": nom_parent, "Content-Type": "application/json"}, timeout=5, verify=(platform != 'win'))

                if res.status_code == 200:
                    if joueur:
                        votes = self.match_data.setdefault("votes", {})
                        norm = lambda s: " ".join(str(s).strip().lower().split())
                        cle = next((k for k in votes if norm(k) == norm(joueur)), joueur)
                        vote = votes.setdefault(cle, {})
                        
                        # --- CORRECTION 1 : On enregistre sous les deux clés pour compatibilité locale et API ---
                        for attr, val in [("disponibilite", choix), ("trajet", choix_trajet), ("choix_multiple", choix_multiple), ("nb_places", nb_places), ("nombre_de_places", nb_places)]:
                            if val is not None: vote[attr] = val

                    Clock.schedule_once(
                        lambda dt: (
                            self.mettre_a_jour(self.match_data),
                            setattr(self, "height", self.minimum_height),
                        ),
                        0.05,
                    )
                else: print(f"[ERREUR VOTE] {res.status_code} {res.text}")
            except Exception as e: print(f"[ERREUR RESEAU VOTE] {e}")

        threading.Thread(target=envoyer_requete, daemon=True).start()

    def calculer_etat_vote(self):
        data = self.match_data or {}
        s_actif, s_trajet, type_s = bool(data.get("sondage_actif")), bool(data.get("sondage_trajet")), data.get("type_sondage", "classique")
        
        target_cat = getattr(self, "categorie", None) or data.get("categorie")
        associes = list(dict.fromkeys(str(n).strip() for n in (self.get_joueurs_associes_pour_parent(self.nom_parent, target_cat) or []) if str(n).strip()))
        if not (s_actif or s_trajet) or not associes: return []

        norm = lambda s: " ".join(str(s or "").strip().lower().split())
        votes_norm = {norm(k): v for k, v in (data.get("votes", {}) or {}).items()}
        joueurs, coachs = [n for n in associes if not n.upper().startswith("COACH_")], [n for n in associes if n.upper().startswith("COACH_")]
        
        statuts_colores, complet, total = [], True, len(joueurs) + len(coachs)

        for nom in joueurs + coachs:
            vote = votes_norm.get(norm(nom), {})
            v_dict = vote if isinstance(vote, dict) else {}
            dispo = v_dict.get("disponibilite") if v_dict else vote
            
            st = str(v_dict.get("choix_multiple") if type_s == "multiple" else dispo) if (s_actif and (v_dict.get("choix_multiple") if type_s == "multiple" else dispo)) else None

            if s_trajet and dispo != "Absent" and v_dict.get("trajet"):
                tr = "Valdahon" if "Valdahon" in str(v_dict["trajet"]) else ("Direct" if "Stade" in str(v_dict["trajet"]) else "Voiture")
                
                # --- CORRECTION 2 : Accepter 'nb_places' ET 'nombre_de_places' envoyés par l'API ---
                places = v_dict.get("nb_places") if v_dict.get("nb_places") is not None else v_dict.get("nombre_de_places")
                
                if tr == "Valdahon" and places is not None:
                    tr = f"Valdahon ({places})"
                st = f"{st} - {tr}" if st else tr

            if nom in joueurs:
                p_ok = bool(v_dict.get("choix_multiple") if type_s == "multiple" else dispo) if s_actif else True
                if not (p_ok and (dispo == "Absent" or not s_trajet or bool(v_dict.get("trajet")))):
                    complet = False

            if nom in coachs and not st: continue

            prenom = str(nom).replace("COACH_", "").replace("coach_", "").strip().split(" ")[-1]
            if st and total > 1: st = st.replace("Présent", "Prés").replace("Absent", "Abs")

            txt = (f"{prenom} : {st}" if st else f"{prenom} : VOTE") if total > 1 else (str(st) if st else "VOTE")
            statuts_colores.append((txt, (0.9, 0.5, 0.1, 1) if "Abs" in str(st) else (0.1, 0.7, 0.3, 1)))

        if not complet and self.nom_parent != "anonymous":
            if coachs:
                return [(" ", (1, 1, 1, 0))]
            if joueurs:
                return [("/!\\ VOTE", (0.9, 0.2, 0.2, 1))]
        
        return statuts_colores

    def ouvrir_popup_nb_places(self, match_id, nom_enfant, parent_popup):
        """Popup demandant le nombre de places restantes dans le véhicule pour Valdahon."""
        # 1. Récupération du vote existant pour ce joueur
        vote_existant = None
        votes = self.match_data.get("votes", {})
        if nom_enfant and nom_enfant in votes:
            vote_existant = votes[nom_enfant].get("nombre_de_places")

        content = BoxLayout(orientation="vertical", padding=dp(20), spacing=dp(15))
        with content.canvas.before:
            Color(1, 1, 1, 1)
            bg = RoundedRectangle(pos=content.pos, size=content.size, radius=[dp(12)])
        content.bind(pos=lambda _, v: setattr(bg, "pos", v), size=lambda _, v: setattr(bg, "size", v))

        # --- LABEL AVEC RETOUR À LA LIGNE DYNAMIQUE ---
        lbl_question = Label(
            text="[b]Combien de places vous reste-t-il dans votre voiture ?[/b]",
            markup=True,
            font_size=f"{self.user_font_size}sp",
            color=(0.1, 0.1, 0.3, 1),
            size_hint_y=None,
            halign="center",
            valign="middle"
        )
        # Force le calcul de la largeur du texte selon la largeur du composant
        lbl_question.bind(width=lambda s, w: setattr(s, "text_size", (w, None)))
        # Ajuste dynamiquement la hauteur du Label pour accueillir toutes les lignes de texte
        lbl_question.bind(texture_size=lambda s, t: setattr(s, "height", max(dp(40), t[1] + dp(5))))
        content.add_widget(lbl_question)

        grid = GridLayout(cols=3, spacing=dp(10), size_hint_y=None, height=dp(110))
        
        # Un size_hint de (0.85, None) permet à la popup d'adapter sa hauteur au contenu sans déformer la grille
        places_popup = ModalView(size_hint=(0.85, None), auto_dismiss=False, background_color=(0, 0, 0, 0.65))
        # Ajuste la hauteur de la popup dynamiquement en fonction de son contenu
        content.bind(minimum_height=places_popup.setter("height"))

        def choisir_places(nb):
            places_popup.dismiss()
            if parent_popup:
                parent_popup.dismiss()
            self.on_presence_click(self.match_id, choix_trajet="Valdahon", joueur_concerne=nom_enfant, nb_places=nb)

        # 2. Génération des boutons
        for i in range(6):
            # Si aucun vote existant -> TOUT EN BLEU
            # Si vote existe -> BLEU uniquement pour la case votée, GRIS pour les autres
            if vote_existant is None:
                bg_color = (0.1, 0.5, 0.8, 1)
                txt_color = (1, 1, 1, 1)
            else:
                est_vote_actif = (str(vote_existant) == str(i))
                bg_color = (0.1, 0.5, 0.8, 1) if est_vote_actif else (0.7, 0.7, 0.72, 1)
                txt_color = (1, 1, 1, 1) if est_vote_actif else (0.2, 0.2, 0.2, 1)

            btn = Button(
                text=str(i),
                font_size=f"{self.user_font_size + 2}sp",
                bold=True,
                background_normal="",
                background_color=bg_color,
                color=txt_color
            )
            btn.bind(on_release=lambda x, val=i: choisir_places(val))
            grid.add_widget(btn)

        content.add_widget(grid)

        btn_annuler = Button(
            text="Annuler",
            size_hint_y=None,
            height=dp(40),
            background_normal="",
            background_color=(0.82, 0.82, 0.85, 1),
            color=(0.15, 0.15, 0.15, 1),
            bold=True
        )
        btn_annuler.bind(on_release=lambda x: places_popup.dismiss())
        content.add_widget(btn_annuler)

        places_popup.add_widget(content)
        places_popup.open()

    def ouvrir_popup_detail(self, joueur_concerne=None):
        """Affiche le détail d'un événement et permet au parent de voter."""
        norm = lambda n: " ".join(str(n or "").strip().lower().split())
        target_cat = getattr(self, "categorie", None) or self.match_data.get("categorie")
        associes = self.get_joueurs_associes_pour_parent(self.nom_parent, target_cat) or []

        nom_enfant = self._obtenir_nom_joueur(joueur_concerne) if joueur_concerne else (self._obtenir_nom_joueur(associes[0]) if len(associes) == 1 else "")
        self.joueur_concerne = nom_enfant
        votes = self.match_data.get("votes", {}) or {}

        def get_vote_sel():
            if not nom_enfant: return {}
            data = next((v for k, v in votes.items() if norm(k) == norm(nom_enfant)), {})
            return data if isinstance(data, dict) else {"disponibilite": data}

        content = BoxLayout(orientation="vertical", padding=dp(20), spacing=dp(12))
        with content.canvas.before:
            Color(1, 1, 1, 1)
            content.bg_rect = RoundedRectangle(pos=content.pos, size=content.size, radius=[dp(10)])
        content.bind(pos=lambda s, v: setattr(s.bg_rect, "pos", v), size=lambda s, v: setattr(s.bg_rect, "size", v))

        def make_lbl(txt, color=(0.1, 0.1, 0.1, 1), offset=-1, halign="left", height=None):
            lbl = Label(text=txt, markup=True, font_size=f"{self.user_font_size + offset}sp", color=color, size_hint_y=None, halign=halign, valign="middle")
            if height: lbl.height = height
            lbl.bind(width=lambda s, w: setattr(s, "text_size", (w, None)), **({} if height else {"texture_size": lambda s, t: setattr(s, "height", max(dp(28), t[1] + dp(6)))}))
            return lbl

        def make_btn(txt, color, bg, cb, height=dp(40)):
            btn = Button(text=txt, background_normal="", background_color=bg, color=color, bold=True, font_size=f"{self.user_font_size - 2}sp", size_hint_y=None, height=height)
            btn.bind(on_release=cb)
            return btn

        # Entête
        titre = self.match_data.get("titre", self.match_data.get("adversaire", "Détails de l'événement"))
        content.add_widget(make_lbl(f"[b]{escape_markup(str(titre))}[/b]", (0.1, 0.1, 0.3, 1), 2, "center"))
        if nom_enfant: content.add_widget(make_lbl(f"[b]Vote pour : {escape_markup(nom_enfant)}[/b]", (0.1, 0.45, 0.2, 1), 0, "center"))

        info_scroll, info_box = ScrollView(bar_width=0, size_hint=(1, 1)), BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(12), padding=dp(5))
        info_box.bind(minimum_height=info_box.setter("height"))

        champs_a_afficher = [
            ("Type", "type"),
            ("Titre", "titre"),
            ("Adversaire", "adversaire"),
            ("Date", "date"),
            ("Heure du RDV à Valdahon", "heure_rdv"),
            ("Convocation sur place", "heure_sur_place"),
            ("Heure du coup d'envoi", "heure_coup_envoi"),
            ("Lieu", "lieu"),
            ("Notes", "notes")
        ]

        for lbl_name, key in champs_a_afficher:
            val = self.match_data.get(key)
            # Rétrocompatibilité si un ancien match utilise juste "heure"
            if not val and key == "heure_rdv":
                val = self.match_data.get("heure")
                
            if val:
                if key == "notes":
                    info_box.add_widget(make_lbl(f"[b]Informations complémentaires :[/b]\n{escape_markup(str(val))}"))
                else:
                    info_box.add_widget(make_lbl(f"[b]{lbl_name} :[/b] {escape_markup(str(val))}"))

        def afficher_popup_votes(titre_votes, sections_dict):
            self._afficher_popup_resultats_coach(titre_votes, sections_dict)

        type_sondage, sondage_actif, sondage_trajet = self.match_data.get("type_sondage", "classique"), bool(self.match_data.get("sondage_actif")), bool(self.match_data.get("sondage_trajet"))

        # SECTION MULTIPLE
        if sondage_actif and type_sondage == "multiple":
            opts, t_sond = self.match_data.get("options_sondage", ["1", "2", "3", "4", "5"]), self.match_data.get("titre_sondage_multiple", "Votre Choix")
            info_box.add_widget(make_lbl(f"[b]--- {escape_markup(str(t_sond))} ---[/b]", (0.1, 0.3, 0.8, 1), 0, "center", dp(35)))
            val_m = get_vote_sel().get("choix_multiple") if isinstance(get_vote_sel(), dict) else None

            grid_m = GridLayout(cols=min(len(opts), 3), size_hint_y=None, height=dp(45 * ((len(opts) - 1) // 3 + 1)), spacing=dp(5))
            for opt in opts:
                c = (0.1, 0.7, 0.3, 1) if (not val_m or str(val_m) == str(opt)) else (0.85, 0.85, 0.85, 1)
                grid_m.add_widget(make_btn(str(opt), (1,1,1,1), c, lambda x, o=opt: (self.on_presence_click(self.match_id, choix_multiple=o, joueur_concerne=nom_enfant), popup.dismiss())))
            info_box.add_widget(grid_m)

            sec_m = {f"Option : {o}": [n for n, d in votes.items() if isinstance(d, dict) and str(d.get("choix_multiple")) == str(o)] for o in opts}
            info_box.add_widget(make_btn("Voir les votes", (0.15, 0.15, 0.15, 1), (1.0, 0.85, 0.2, 1), lambda x: afficher_popup_votes(f"Votes - {t_sond}", sec_m)))

        # SECTION DISPONIBILITE
        elif sondage_actif:
            info_box.add_widget(make_lbl("[b]--- Votre Disponibilité ---[/b]", (0.1, 0.3, 0.8, 1), 0, "center", dp(35)))
            val_d = get_vote_sel().get("disponibilite") if isinstance(get_vote_sel(), dict) else None

            box_v = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(45), spacing=dp(10))
            for choice, color in [("Présent", (0.1, 0.7, 0.3, 1)), ("Absent", (0.8, 0.2, 0.2, 1))]:
                bg = color if (not val_d or val_d == choice) else (0.85, 0.85, 0.85, 1)
                box_v.add_widget(make_btn(choice, (1,1,1,1), bg, lambda x, c=choice: (self.on_presence_click(self.match_id, choix=c, joueur_concerne=nom_enfant), popup.dismiss()), dp(45)))
            info_box.add_widget(box_v)

            presents = [n for n, d in votes.items() if (d.get("disponibilite") if isinstance(d, dict) else d) == "Présent"]
            absents = [n for n, d in votes.items() if (d.get("disponibilite") if isinstance(d, dict) else d) == "Absent"]
            info_box.add_widget(make_btn("Voir les votes", (0.15, 0.15, 0.15, 1), (1.0, 0.85, 0.2, 1), lambda x: afficher_popup_votes("Votes - Disponibilité", {"Présents": presents, "Absents": absents})))

        # SECTION TRAJET
        if sondage_trajet and type_sondage != "multiple" and isinstance(get_vote_sel(), dict) and get_vote_sel().get("disponibilite") != "Absent":
            info_box.add_widget(make_lbl("[b]--- Choix du Trajet ---[/b]", (0.1, 0.3, 0.8, 1), 0, "center", dp(35)))
            val_t = get_vote_sel().get("trajet")

            box_t = BoxLayout(orientation="vertical", size_hint_y=None, height=dp(125), spacing=dp(5))
            trajets = [
                ("Valdahon (Départ club)", "Valdahon", (0.1, 0.5, 0.8, 1)), 
                ("Directement au Stade du Match", "Stade adverse", (0.1, 0.7, 0.3, 1)), 
                ("Besoin d'une Voiture (Transport)", "Besoin voiture", (0.8, 0.5, 0.1, 1))
            ]

            def gerer_clic_trajet(val_btn):
                if val_btn == "Valdahon":
                    # Ouvre la popup pour demander le nombre de places disponibles
                    self.ouvrir_popup_nb_places(self.match_id, nom_enfant, popup)
                else:
                    self.on_presence_click(self.match_id, choix_trajet=val_btn, joueur_concerne=nom_enfant)
                    popup.dismiss()

            for txt_btn, val_btn, color in trajets:
                bg = color if (not val_t or val_t == val_btn) else (0.85, 0.85, 0.85, 1)
                box_t.add_widget(make_btn(txt_btn, (1,1,1,1), bg, lambda x, v=val_btn: gerer_clic_trajet(v), dp(35)))
            info_box.add_widget(box_t)

            # Formate 'Nom (X places)' pour la popup de détails (Uniquement Valdahon)
            def format_nom_valdahon(n, d):
                if isinstance(d, dict):
                    # Accepte 'nb_places' ET 'nombre_de_places'
                    nb = d.get("nb_places") if d.get("nb_places") is not None else d.get("nombre_de_places")
                    if nb is not None:
                        try:
                            nb_int = int(nb)
                            txt_pl = "place" if nb_int <= 1 else "places"
                            return f"{n} ({nb_int} {txt_pl})"
                        except ValueError:
                            pass
                return n

            sec_t = {
                "Valdahon (Départ club)": [format_nom_valdahon(n, d) for n, d in votes.items() if isinstance(d, dict) and d.get("trajet") == "Valdahon"],
                "Sur place": [n for n, d in votes.items() if isinstance(d, dict) and d.get("trajet") == "Stade adverse"],
                "Besoin voiture": [n for n, d in votes.items() if isinstance(d, dict) and d.get("trajet") == "Besoin voiture"]
            }
            info_box.add_widget(make_btn("Voir les votes", (0.15, 0.15, 0.15, 1), (1.0, 0.85, 0.2, 1), lambda x: afficher_popup_votes("Votes - Trajets", sec_t)))

        # SECTION CONVOCATIONS (AVEC TOTAL DES CONVOQUÉS)
        if self.match_data.get("activer_convocation", False):
            j_conv = self.match_data.get("joueurs_convoques", []) or []
            total_convoques = len(j_conv)
            
            # Affichage du titre avec le total entre parenthèses
            titre_conv = f"[b]--- Joueurs Convoqués ({total_convoques}) ---[/b]"
            info_box.add_widget(make_lbl(titre_conv, (0.1, 0.3, 0.8, 1), 0, "center", dp(35)))

            if not j_conv:
                info_box.add_widget(make_lbl("  • Aucun joueur convoqué", (0.6, 0.6, 0.6, 1), height=dp(25)))
            else:
                for j in j_conv:
                    if isinstance(j, dict):
                        nom_j = j.get("nom", "").strip()
                        prenom_j = j.get("prenom", "").strip()
                        cat_j = j.get("categorie", "").strip()
                        txt = f"[{cat_j}] {nom_j} {prenom_j}".strip() if cat_j else f"{nom_j} {prenom_j}".strip()
                    else:
                        txt = str(j).strip()
                    info_box.add_widget(make_lbl(f"  • {escape_markup(txt)}", (0.3, 0.3, 0.3, 1), height=dp(25)))
            info_box.add_widget(BoxLayout(size_hint_y=None, height=dp(10)))

        info_scroll.add_widget(info_box)
        content.add_widget(info_scroll)

        # Création unique du Popup
        popup = Popup(title="", title_size=0, content=content, size_hint=(0.85, 0.8), separator_height=0, background="", background_color=(0, 0, 0, 0.6))

        content.add_widget(make_btn("Fermer", (0.15, 0.15, 0.15, 1), (0.82, 0.82, 0.85, 1), popup.dismiss, dp(45)))
        popup.open()

    def ouvrir_popup_selection_votant(self, joueurs_associes):
        joueurs = list(dict.fromkeys(
            f"{j.get('nom', '')} {j.get('prenom', '')}".strip() if isinstance(j, dict) else str(j).strip()
            for j in (joueurs_associes or []) if j
        ))
        if not (joueurs := [j for j in joueurs if j]): return
    
        norm = lambda s: " ".join(str(s or "").strip().lower().split())
        votes = {norm(k): v for k, v in (self.match_data.get("votes", {}) or {}).items()}
    
        def deja_vote(nom):
            v = votes.get(norm(nom))
            return bool(v) if not isinstance(v, dict) else any(v.get(k) not in (None, "") for k in ("disponibilite", "choix_multiple", "trajet"))
    
        content = BoxLayout(orientation="vertical", padding=dp(20), spacing=dp(12))
        with content.canvas.before:
            Color(1, 1, 1, 1)
            bg = RoundedRectangle(pos=content.pos, size=content.size, radius=[dp(15)])
        content.bind(pos=lambda _, v: setattr(bg, "pos", v), size=lambda _, v: setattr(bg, "size", v))
        content.add_widget(Label(text="[b]Pour qui souhaitez-vous voter ?[/b]", markup=True, font_size=dp(19),
                                 color=(0.1, 0.1, 0.2, 1), size_hint_y=None, height=dp(45), halign="center", valign="middle"))
    
        scroll = ScrollView(bar_width=0, size_hint=(1, 1))
        liste = GridLayout(cols=1, spacing=dp(10), padding=dp(5), size_hint_y=None)
        liste.bind(minimum_height=liste.setter("height"))
        scroll.add_widget(liste)
        content.add_widget(scroll)
    
        popup = ModalView(size_hint=(0.85, 0.65), auto_dismiss=False, background_color=(0, 0, 0, 0.65))
        popup.add_widget(content)
    
        def make_btn(txt, bg, h, cb, col=(1, 1, 1, 1)):
            btn = Button(text=txt, size_hint_y=None, height=h, background_normal="", background_color=bg,
                         color=col, bold=True, font_size=dp(16))
            btn.bind(on_release=cb)
            return btn
    
        def select(v):
            self.joueur_concerne = self._joueur_vote_selectionne = v
            popup.dismiss()
            Clock.schedule_once(lambda dt: self.ouvrir_popup_detail(joueur_concerne=v), 0.15)
    
        for i, nom in enumerate(joueurs, 1):
            affiche = f"{i}. Coach / Staff ({nom.replace('_', ' ')})" if nom.upper().startswith("COACH_") else f"{i}. {nom.replace('_', ' ')}"
            liste.add_widget(make_btn(affiche, (0.65, 0.65, 0.68, 1) if deja_vote(nom) else (0.12, 0.55, 0.85, 1),
                                     dp(55), lambda _, v=nom: select(v)))
    
        content.add_widget(make_btn("Annuler", (0.82, 0.82, 0.85, 1), dp(45),
                                    lambda _: popup.dismiss(), col=(0.15, 0.15, 0.15, 1)))
        popup.open()

    

    def mettre_a_jour(self, nouveau_match_data=None):
        if nouveau_match_data:
            self.match_data = nouveau_match_data
    
        est_conv = self._est_convoque()
        if getattr(self, "ball_icon", None):
            self.ball_icon.opacity = int(est_conv)
            self.ball_icon.size_hint_x = None
            self.ball_icon.width = dp(22) if est_conv else 0
    
        self.badge_box.clear_widgets()
        statuts = self.calculer_etat_vote()
    
        for texte, couleur in statuts or []:
            lbl = Label(
                text=f"[b]{escape_markup(texte)}[/b]",
                markup=True,
                color=couleur,
                font_size=f"{self.user_font_size - 9}sp",
                size_hint=(1, None),
                height=dp(20),
                halign="right",
                valign="middle",
            )
            lbl.bind(width=lambda s, w: setattr(s, "text_size", (w, None)))
            self.badge_box.add_widget(lbl)
    
        self.badge_box.size_hint = (None, None)
        self.badge_box.width = dp(120) if statuts else 0
        self.badge_box.height = dp(20) * len(statuts) if statuts else 0
        self.badge_box.opacity = 1 if statuts else 0
        self.lbl_title.size_hint_x = 1

    def _update_rect(self, instance, value):
        self.bg_rect.pos = instance.pos
        self.bg_rect.size = instance.size

    def _update_line(self, instance, value):
        self.v_line.points = [
            instance.x + instance.width * 0.25,
            instance.y,
            instance.x + instance.width * 0.25,
            instance.y + instance.height,
        ]

    def _build_media_zone(self):
        if not self.image_list:
            return None
        box = BoxLayout(size_hint_y=None, height=dp(150))
        img = Image(source=self.image_list[0], allow_stretch=True, keep_ratio=True)
        box.add_widget(img)
        return box

    def on_touch_up(self, touch):
        if getattr(self, "_touch_consumed_by_child", False):
            self._touch_consumed_by_child = False
            return True
    
        if not self.collide_point(*touch.pos):
            return super().on_touch_up(touch)
    
        if (
            not self.nom_parent
            and (app := App.get_running_app())
            and getattr(app, "config", None)
            and app.config.has_section("User")
        ):
            self.nom_parent = app.config.get("User", "nom_parent", fallback="").strip()
    
        target_cat = getattr(self, "categorie", None) or self.match_data.get("categorie")
        joueurs = list(
            dict.fromkeys(
                nom
                for j in (self.get_joueurs_associes_pour_parent(self.nom_parent, target_cat) or [])
                if (nom := self._obtenir_nom_joueur(j))
            )
        )
    
        if len(joueurs) > 1:
            Clock.schedule_once(lambda dt: self.ouvrir_popup_selection_votant(joueurs), 0)
        else:
            kwargs = {"joueur_concerne": joueurs[0]} if joueurs else {}
            Clock.schedule_once(lambda dt: self.ouvrir_popup_detail(**kwargs), 0)
    
        return True