from datetime import datetime
import hashlib
import os
import threading
import requests

from kivy.app import App
from kivy.metrics import dp
from kivy.clock import Clock
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.modalview import ModalView
from kivy.uix.scrollview import ScrollView
from kivy.uix.carousel import Carousel
from kivy.uix.image import Image
from kivy.uix.checkbox import CheckBox
from kivy.uix.widget import Widget
from kivy.graphics import Color, RoundedRectangle, Line
from kivy.utils import escape_markup

class EventCard(BoxLayout):
    """Carte d'événement sans émojis pour garantir la compatibilité des polices."""
    def __init__(self, match_id, match_data, on_presence_click=None, **kwargs):
        super().__init__(orientation="vertical", size_hint_y=None, spacing=dp(10), padding=dp(15), **kwargs)
        self.match_id = match_id
        self.match_data = match_data if isinstance(match_data, dict) else {}
        self.on_presence_click_callback = on_presence_click
        self.active = True
        self._check_events = []
        
        images = self.match_data.get("images", self.match_data.get("flyer", []))
        if isinstance(images, str):
            raw_list = [images]
        elif isinstance(images, list):
            raw_list = list(images)
        else:
            raw_list = []
        self.image_list = list(dict.fromkeys([src for src in raw_list if src]))

        self.bind(minimum_height=self.setter('height'))
        
        app = App.get_running_app()
        self.user_font_size = 18  
        if app and hasattr(app, 'config') and app.config.has_section('User'):
            try: 
                self.user_font_size = int(app.config.getint('User', 'font_size_factor'))
            except: 
                self.user_font_size = 18

        self.nom_parent = ""
        if app and hasattr(app, 'config') and app.config.has_section('User'):
            self.nom_parent = app.config.get('User', 'nom_parent', fallback="").strip()

        with self.canvas.before:
            Color(1, 1, 1, 1) 
            self.bg_rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(10)])
        self.bind(pos=self._update_rect, size=self._update_rect)

        columns_layout = BoxLayout(orientation='horizontal', spacing=dp(15), size_hint_y=None)
        columns_layout.bind(minimum_height=columns_layout.setter('height'))
        
        date_box = BoxLayout(orientation='vertical', size_hint_x=0.25, spacing=dp(1), size_hint_y=None)
        date_box.bind(minimum_height=date_box.setter('height'))
        
        raw_date = str(self.match_data.get("date", ""))
        evt_type = str(self.match_data.get("type", "EVENEMENT")).upper()
        if evt_type == "MATCH":
            heure_str = str(self.match_data.get("heure_rdv", self.match_data.get("heure", "N/C")))
            prefixe_heure = "RDV"
        else:
            heure_str = str(self.match_data.get("heure", self.match_data.get("heure_rdv", "N/C")))
            prefixe_heure = "à"
        
        jour_semaine, numero, mois = "EVENEMENT", "", ""
        parsed_dt = None
        for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):
            try:
                parsed_dt = datetime.strptime(raw_date.strip(), fmt)
                break
            except ValueError:
                continue

        jours_fr = ["LUN", "MAR", "MER", "JEU", "VEN", "SAM", "DIM"]
        mois_fr = ["", "JAN", "FEV", "MAR", "AVR", "MAI", "JUIN", "JUIL", "AOUT", "SEP", "OCT", "NOV", "DEC"]

        if parsed_dt:
            jour_semaine = jours_fr[parsed_dt.weekday()]
            numero = str(parsed_dt.day)
            mois = mois_fr[parsed_dt.month]
        else:
            numero = raw_date

        lbl_js = Label(text=f"[b]{escape_markup(jour_semaine)}[/b]", markup=True, color=(0.7, 0.7, 0.7, 1), font_size=f"{self.user_font_size - 6}sp", size_hint_y=None, height=dp(18), halign='center')
        lbl_js.bind(width=lambda s, w: setattr(s, 'text_size', (w, None)))
        
        lbl_num = Label(text=f"[b]{escape_markup(numero)}[/b]", markup=True, color=(0.1, 0.3, 0.8, 1), font_size=f"{self.user_font_size + 4}sp", size_hint_y=None, height=dp(28), halign='center')
        lbl_num.bind(width=lambda s, w: setattr(s, 'text_size', (w, None)))

        lbl_mois = Label(text=f"[b]{escape_markup(mois)}[/b]", markup=True, color=(0.3, 0.3, 0.3, 1), font_size=f"{self.user_font_size - 5}sp", size_hint_y=None, height=dp(18), halign='center')
        lbl_mois.bind(width=lambda s, w: setattr(s, 'text_size', (w, None)))

        lbl_heure = Label(text=f"{prefixe_heure} {escape_markup(heure_str)}", markup=True, color=(0.5, 0.5, 0.5, 1), font_size=f"{self.user_font_size - 6}sp", size_hint_y=None, height=dp(20), halign='center')
        lbl_heure.bind(width=lambda s, w: setattr(s, 'text_size', (w, None)))
        
        date_box.add_widget(lbl_js)
        date_box.add_widget(lbl_num)
        date_box.add_widget(lbl_mois)
        date_box.add_widget(lbl_heure)

        with columns_layout.canvas.after:
            Color(0.65, 0.65, 0.65, 1)
            self.v_line = Line(points=[], width=1)
        columns_layout.bind(pos=self._update_line, size=self._update_line)

        title_box = BoxLayout(orientation='vertical', size_hint_x=0.75, spacing=dp(2), padding=[dp(12), 0, 0, 0], size_hint_y=None)
        title_box.bind(minimum_height=title_box.setter('height'))
        
        titre_evt = str(self.match_data.get("titre", ""))
        adversaire_evt = str(self.match_data.get("adversaire", ""))
        lieu_evt = str(self.match_data.get("lieu", ""))
        
        if not titre_evt:
            titre_evt = adversaire_evt if evt_type == "MATCH" else "Événement"

        titre_layout = BoxLayout(orientation='horizontal', size_hint_y=None, spacing=dp(10))
        titre_layout.bind(minimum_height=titre_layout.setter('height'))
        self.titre_layout = titre_layout
        
        self.lbl_title = Label(
            text=f"[b]{escape_markup(titre_evt)}[/b]",
            markup=True, color=(0.1, 0.1, 0.3, 1),
            font_size=f"{self.user_font_size}sp",
            size_hint_x=1,  # Le titre prend tout l'espace possible
            size_hint_y=None, halign="left"
        )
        self.lbl_title.bind(
            width=lambda s,w: setattr(s,"text_size",(w,None)),
            texture_size=lambda s,t: setattr(s,"height",t[1])
        )
        titre_layout.add_widget(self.lbl_title)
        
        # Le badge_box à droite (sans espaceur, avec une taille fixe initiale à 0)
        self.badge_box = BoxLayout(orientation='vertical', size_hint_x=None, width=0, spacing=dp(2), size_hint_y=None, pos_hint={'center_y': 0.5})
        self.badge_box.bind(minimum_height=self.badge_box.setter('height'))
        titre_layout.add_widget(self.badge_box)
        
        self.mettre_a_jour(self.match_data)

        title_box.add_widget(titre_layout)

        if evt_type == "MATCH" and adversaire_evt:
            lbl_adv = Label(text=f"Adversaire : {escape_markup(adversaire_evt)}", markup=True, color=(0.3, 0.3, 0.3, 1), font_size=f"{self.user_font_size - 4}sp", size_hint_y=None, halign='left')
            lbl_adv.bind(width=lambda s, w: setattr(s, 'text_size', (w, None)), texture_size=lambda s, t: setattr(s, 'height', t[1]))
            title_box.add_widget(lbl_adv)

        sub_text = f"Lieu : {lieu_evt}" if lieu_evt else "Cliquez pour voir les détails et voter"
        lbl_sub = Label(text=escape_markup(sub_text), markup=True, color=(0.5, 0.5, 0.5, 1), font_size=f"{self.user_font_size - 5}sp", size_hint_y=None, halign='left')
        lbl_sub.bind(width=lambda s, w: setattr(s, 'text_size', (w, None)), texture_size=lambda s, t: setattr(s, 'height', t[1]))
        title_box.add_widget(lbl_sub)

        columns_layout.add_widget(date_box)
        columns_layout.add_widget(title_box)
        self.add_widget(columns_layout)

        if self.image_list:
            media_zone = self._build_media_zone()
            if media_zone:
                self.add_widget(media_zone)


    def calculer_etat_vote(self):
        data = self.match_data or {}
        type_sondage, sondage_actif, sondage_trajet = data.get("type_sondage", "classique"), bool(data.get("sondage_actif", False)), bool(data.get("sondage_trajet", False))
        associes = list(dict.fromkeys(str(n).strip() for n in (self.get_joueurs_associes_pour_parent(self.nom_parent) or []) if str(n).strip()))
        if not (sondage_actif or sondage_trajet) or not associes: return []

        votes_norm = {" ".join(str(k or "").strip().lower().split()): v for k, v in (data.get("votes", {}) or {}).items()}
        joueurs, coachs = [n for n in associes if not n.upper().startswith("COACH_")], [n for n in associes if n.upper().startswith("COACH_")]
        
        statuts_colores = []
        tous_les_joueurs_ont_vote = True
        total_associes = len(joueurs) + len(coachs)

        def get_statut_info(nom):
            vote = votes_norm.get(" ".join(str(nom).strip().lower().split()), {})
            dispo = vote.get("disponibilite") if isinstance(vote, dict) else None
            statut = str(vote.get("choix_multiple") if type_sondage == "multiple" else dispo) if (sondage_actif and (vote.get("choix_multiple") if type_sondage == "multiple" else dispo)) else None
            if sondage_trajet and dispo != "Absent" and vote.get("trajet"):
                t = "Valdahon" if "Valdahon" in str(vote["trajet"]) else ("Direct" if "Stade" in str(vote["trajet"]) else "Voiture")
                statut = f"{statut} - {t}" if statut else t
            return statut, vote

        for nom in (joueurs + coachs):
            statut, vote = get_statut_info(nom)
            is_coach = nom in coachs

            if nom in joueurs:
                p_ok = bool(vote.get("choix_multiple") if type_sondage == "multiple" else vote.get("disponibilite")) if sondage_actif else True
                t_ok = (vote.get("disponibilite") == "Absent" or not sondage_trajet or bool(vote.get("trajet")))
                if not (p_ok and t_ok): tous_les_joueurs_ont_vote = False
            
            # Le vote du coach est optionnel : s'il n'a pas voté, on l'ignore totalement
            if is_coach and not statut:
                continue

            # Retrait du préfixe "COACH_" pour un affichage propre si le coach a voté
            prenom = str(nom).replace("COACH_", "").replace("coach_", "").strip().split(" ")[-1]
            
            # Application des abréviations si plusieurs personnes sont associées
            if statut and total_associes > 1:
                statut = statut.replace("Présent", "Prés").replace("Absent", "Abs")

            # Affichage conditionnel selon le nombre de personnes associées
            if total_associes > 1:
                txt = f"{prenom} : {statut}" if statut else f"{prenom} : VOTE"
            else:
                txt = str(statut) if statut else "VOTE"

            couleur = (0.9, 0.5, 0.1, 1) if "Abs" in str(statut) else (0.1, 0.7, 0.3, 1)
            statuts_colores.append((txt, couleur))

        if joueurs and not tous_les_joueurs_ont_vote and self.nom_parent != "anonymous":
            return [("/!\\ VOTE", (0.9, 0.2, 0.2, 1))]
        
        return statuts_colores
    
    def mettre_a_jour(self, nouveau_match_data=None):
        if nouveau_match_data: self.match_data = nouveau_match_data
        
        self.badge_box.clear_widgets()
        statuts = self.calculer_etat_vote()
        
        for texte, couleur in statuts:
            lbl = Label(
                text=f"[b]{escape_markup(texte)}[/b]", 
                markup=True, 
                color=couleur,
                font_size=f"{self.user_font_size - 9}sp", 
                size_hint_x=1.0,  # Occupe toute la largeur allouée au badge_box
                size_hint_y=None,
                halign="right",
                valign="middle"
            )
            # Lier text_size à la largeur dynamique du badge_box pour que le texte reste toujours dans la colonne
            lbl.bind(
                texture_size=lambda s, t: setattr(s, "height", t[1]),
                width=lambda s, w: setattr(s, "text_size", (w, None))
            )
            self.badge_box.add_widget(lbl)
            
        if statuts:
            # Répartition propre : 65% pour le titre, 35% pour les votes (reste bien dans la carte)
            self.lbl_title.size_hint_x = 0.65
            self.badge_box.size_hint_x = 0.35
        else:
            self.lbl_title.size_hint_x = 1.0
            self.badge_box.size_hint_x = 0.0
            
        self.titre_layout.do_layout()
        self.do_layout()
        self.height = self.minimum_height

    def _update_rect(self, instance, value):
        self.bg_rect.pos = instance.pos
        self.bg_rect.size = instance.size

    def _update_line(self, instance, value):
        self.v_line.points = [instance.x + instance.width * 0.25, instance.y, instance.x + instance.width * 0.25, instance.y + instance.height]

    def _build_media_zone(self):
        if not self.image_list:
            return None
        box = BoxLayout(size_hint_y=None, height=dp(150))
        img = Image(source=self.image_list[0], allow_stretch=True, keep_ratio=True)
        box.add_widget(img)
        return box

    def get_joueurs_associes_pour_parent(self, nom_parent):
        """Retourne une liste propre des joueurs/rôles associés au parent."""
        app = App.get_running_app()
        if not app:
            return []

        # 1. Catégorie courante
        categorie = getattr(app, "categorie_courante", None)
        if not categorie and hasattr(app, "get_categorie_courante"):
            try:
                categorie = app.get_categorie_courante()
            except Exception:
                categorie = None
        categorie = str(categorie or "u14_u15").strip()

        # 2. PRIORITÉ : association provenant de la configuration
        if hasattr(app, "get_joueur_associe_pour_cat"):
            try:
                if joueur_local := app.get_joueur_associe_pour_cat(categorie):
                    
                    if isinstance(joueur_local, (list, tuple, set)):
                        return [str(j).strip() for j in joueur_local if j is not None and str(j).strip()]
                    
                    if isinstance(joueur_local, dict):
                        nom = str(joueur_local.get("nom", "")).strip()
                        prenom = str(joueur_local.get("prenom", "")).strip()
                        return [f"{nom} {prenom}".strip()] if (nom or prenom) else []
                    
                    joueur_local = str(joueur_local).strip()
                    if "," in joueur_local:
                        resultats = [m.strip() for m in joueur_local.split(",") if m.strip()]
                        return resultats
                    
                    return [joueur_local]
            except Exception as e:
                print(f"[ERREUR] get_joueur_associe_pour_cat : {e}")

        # 3. FALLBACK : cache
        nom_parent_clean = str(nom_parent or "").strip().lower()
        if not nom_parent_clean:
            return []

        cache_data = getattr(app, "_cache_data", {}) or {}
        cat_data = cache_data.get(categorie, {}) or {}
        tous_les_joueurs = cat_data.get("tous_les_joueurs", []) or []

        joueurs_concernes = []
        for j in tous_les_joueurs:
            if isinstance(j, dict):
                parent_joueur = str(j.get("parent", j.get("nom_parent", ""))).strip().lower()
                if parent_joueur == nom_parent_clean:
                    nom = str(j.get("nom", "")).strip()
                    prenom = str(j.get("prenom", "")).strip()
                    if (joueur := f"{nom} {prenom}".strip()) and joueur not in joueurs_concernes:
                        joueurs_concernes.append(joueur)

        # 4. ADMIN / COACH
        role = "PARENT"
        if hasattr(app, "get_role_for_cat"):
            try:
                role = app.get_role_for_cat(categorie) or "PARENT"
            except Exception:
                pass

        if role == "ADMIN" and not joueurs_concernes:
            joueurs_concernes.append(f"Coach / Admin ({nom_parent})")

        return joueurs_concernes

    def ouvrir_popup_choix_enfants_vote(self, match_id, joueurs_associes, choix, choix_trajet, second_vote, choix_multiple):
        """Permet au parent de choisir le ou les enfants / rôles concernés."""
        content = BoxLayout(orientation="vertical", padding=dp(15), spacing=dp(10))
        
        with content.canvas.before:
            Color(0.95, 0.95, 0.97, 1)
            self_bg = RoundedRectangle(pos=content.pos, size=content.size, radius=[dp(15)])
        content.bind(pos=lambda o, v: setattr(self_bg, 'pos', v), size=lambda o, v: setattr(self_bg, 'size', v))

        content.add_widget(Label(text="[b]Pour qui souhaitez-vous voter ?[/b]", markup=True, size_hint_y=None, height=dp(35), color=(0.1, 0.1, 0.15, 1), font_size=dp(18)))

        scroll = ScrollView(size_hint=(1, 1), bar_width=0)
        grid = GridLayout(cols=1, size_hint_y=None, spacing=dp(8))
        grid.bind(minimum_height=grid.setter("height"))
        checkboxes_dict = {}

        for item in joueurs_associes:
            cle_interne = str(item).strip() if not isinstance(item, dict) else f"{item.get('nom', '')} {item.get('prenom', '')}".strip()
            if not cle_interne: continue
            
            nom_affiche = "Coach / Staff" if cle_interne.startswith("COACH_") else cle_interne

            row = BoxLayout(size_hint_y=None, height=dp(45), spacing=dp(10))
            chk = CheckBox(size_hint_x=None, width=dp(40), active=False)
            checkboxes_dict[cle_interne] = chk
            
            lbl = Label(text=nom_affiche, markup=cle_interne.startswith("COACH_"), color=(0.2, 0.2, 0.2, 1), halign="left", valign="middle")
            lbl.bind(width=lambda s, w: setattr(s, 'text_size', (w, None)))

            row.add_widget(chk)
            row.add_widget(lbl)
            grid.add_widget(row)

        scroll.add_widget(grid)
        content.add_widget(scroll)

        btn_valider = Button(text="Valider le vote", size_hint_y=None, height=dp(45), background_normal="", background_color=(0.15, 0.65, 0.35, 1), color=(1, 1, 1, 1), bold=True)
        content.add_widget(btn_valider)

        popup = ModalView(size_hint=(0.85, 0.6), auto_dismiss=True, background_color=(0, 0, 0, 0.6))
        popup.add_widget(content)

        def on_valider(instance):
            selectionnes = [cle for cle, chk in checkboxes_dict.items() if chk.active]
            if not selectionnes:
                print("[VOTE] Aucun element selectionne.")
                return
            for cible in selectionnes:
                self.envoyer_vote(match_id, choix=choix, choix_trajet=choix_trajet, second_vote=second_vote, choix_multiple=choix_multiple, joueur_concerne=cible, _ignorer_verification_enfants=True)
            popup.dismiss()

        btn_valider.bind(on_release=on_valider)
        popup.open()
        
    def envoyer_vote(
        self, id_match, choix=None, choix_trajet=None, second_vote=None,
        choix_multiple=None, joueur_concerne=None, _ignorer_verification_enfants=False
    ):
        """Prépare et envoie un vote."""
        app = App.get_running_app()
        if not app:
            print("[ERREUR VOTE] Application Kivy introuvable.")
            return

        # --- CORRECTION ICI ---
        # On force la récupération si self.nom_parent est vide
        if not self.nom_parent and hasattr(app, 'config') and app.config.has_section('User'):
            self.nom_parent = app.config.get('User', 'nom_parent', fallback="").strip()

        nom_parent = str(
            getattr(self, "nom_parent", "") or
            getattr(app, "nom_parent", "") or
            getattr(self, "votant_courant", "") or
            (app.get_user_header() or {}).get("nom_parent", "") if hasattr(app, "get_user_header") else ""
        ).strip()
        # -----------------------

        if (not nom_parent or nom_parent.lower() == "anonymous") and joueur_concerne and str(joueur_concerne).upper().startswith("COACH_"):
            nom_parent = joueur_concerne

        if not nom_parent or nom_parent.lower() == "anonymous":
            # Dernier recours : si on a un joueur concerné, on tente de le lier au nom parent
            nom_parent = joueur_concerne or "anonymous"
            
        if not nom_parent or nom_parent.lower() == "anonymous":
            print("[ERREUR VOTE] Nom parent non defini.")
            return

        self.nom_parent = nom_parent
        joueurs_associes = self.get_joueurs_associes_pour_parent(nom_parent) or []
        
        # Si aucun joueur associé n'est trouvé mais qu'un joueur_concerne (ex: COACH_Nicolas) est passé, on l'ajoute
        if not joueurs_associes and joueur_concerne:
            joueurs_associes = [joueur_concerne]

        if len(joueurs_associes) > 1 and not _ignorer_verification_enfants and not joueur_concerne:
            self.ouvrir_popup_choix_enfants_vote(
                id_match, joueurs_associes, choix, choix_trajet, second_vote, choix_multiple
            )
            return

        if len(joueurs_associes) == 1 and not joueur_concerne:
            joueur_concerne = joueurs_associes[0]

        if not joueur_concerne:
            print(f"[ERREUR VOTE] Aucun enfant/role cible defini pour le parent : {nom_parent}")
            return

        self._executer_envoi_vote(
            match_id=id_match, choix=choix, choix_trajet=choix_trajet,
            choix_multiple=choix_multiple, second_vote=second_vote, joueur_concerne=joueur_concerne
        )

    def on_presence_click(self, match_id, choix=None, choix_trajet=None, choix_multiple=None, second_vote=None, joueur_concerne=None, _ignorer_verification_enfants=False):
        """
        Point d'entrée principal dans VestiaireScreen.
        Redirige les clics de EventCard vers la logique de vote réelle.
        """
        if not match_id:
            print("[ERREUR] Tentative de vote sans ID de match.")
            return

        # Si le votant courant est défini dans l'écran, on s'assure de le transmettre
        if not joueur_concerne and hasattr(self, 'joueur_concerne') and self.joueur_concerne:
            joueur_concerne = self.joueur_concerne

        self.envoyer_vote(
            id_match=match_id, 
            choix=choix, 
            choix_trajet=choix_trajet, 
            second_vote=second_vote, 
            choix_multiple=choix_multiple, 
            joueur_concerne=joueur_concerne, 
            _ignorer_verification_enfants=_ignorer_verification_enfants
        )

    def _executer_envoi_vote(self, match_id, choix, choix_trajet, choix_multiple, second_vote, joueur_concerne):
        """Envoie effectivement la requête HTTP à l'API."""
        app = App.get_running_app()
        api_url = getattr(app, 'api_url', "https://fcvv-api.onrender.com")
        
        categorie = getattr(app, 'categorie_courante', None)
        if not categorie and hasattr(app, 'get_categorie_courante'):
            categorie = app.get_categorie_courante()
        if not categorie:
            categorie = "U14_U15"

        # Sécurité supplémentaire pour le nom_parent lors de l'envoi
        nom_parent_final = self.nom_parent
        if (not nom_parent_final or nom_parent_final.lower() == "anonymous") and joueur_concerne:
            nom_parent_final = joueur_concerne

        payload = {
            "id_sondage": match_id,
            "nom_parent": nom_parent_final,
            "nom_joueur_concerne": joueur_concerne
        }
        if choix is not None: payload["choix"] = choix
        if choix_trajet is not None: payload["choix_trajet"] = choix_trajet
        if choix_multiple is not None: payload["choix_multiple"] = choix_multiple
        if second_vote is not None: payload["second_vote"] = second_vote

        headers = {"nom_parent": nom_parent_final, "Content-Type": "application/json"}
        url = f"{api_url}/voter/{categorie}"

        def envoyer_requete():
            try:
                response = requests.post(url, json=payload, headers=headers, timeout=5)
                if response.status_code == 200:
                    
                    if joueur_concerne:
                        votes = self.match_data.setdefault("votes", {})
                        cle_vote = next(
                            (k for k in votes if " ".join(str(k).strip().lower().split()) ==
                             " ".join(str(joueur_concerne).strip().lower().split())),
                            joueur_concerne
                        )
                        vote = votes.setdefault(cle_vote, {})
                    
                        if choix is not None:
                            vote["disponibilite"] = choix
                        if choix_trajet is not None:
                            vote["trajet"] = choix_trajet
                        if choix_multiple is not None:
                            vote["choix_multiple"] = choix_multiple

                    def reload_card(dt):
                        try:
                            Clock.schedule_once(
                                lambda dt: self.mettre_a_jour(self.match_data), 0
                            )
                        except Exception as e:
                            print(f"[ERREUR UI VOTE] Impossible de mettre a jour la carte : {e}")
                    
                    Clock.schedule_once(reload_card, 0)
                else:
                    print(f"[ERREUR VOTE] {response.status_code} {response.text}")
            except Exception as e:
                print(f"[ERREUR RESEAU VOTE] {e}")

        threading.Thread(target=envoyer_requete, daemon=True).start()

    def on_touch_up(self, touch):
        """Ouvre le bon écran de vote selon le nombre de joueurs/rôles associés."""
        if not self.collide_point(*touch.pos):
            return super().on_touch_up(touch)

        app = App.get_running_app()
        
        # SÉCURITÉ : S'assurer que self.nom_parent est défini dès le clic
        if not self.nom_parent and app and hasattr(app, 'config') and app.config.has_section('User'):
            self.nom_parent = app.config.get('User', 'nom_parent', fallback="").strip()

        # Récupération et nettoyage des joueurs associés
        joueurs_propres = []
        for j in self.get_joueurs_associes_pour_parent(self.nom_parent) or []:
            nom = (f"{j.get('nom', '')} {j.get('prenom', '')}" if isinstance(j, dict) else str(j)).strip()
            if nom and nom not in joueurs_propres:
                joueurs_propres.append(nom)

        # Sélection du comportement selon le nombre de joueurs
        if len(joueurs_propres) > 1:
            Clock.schedule_once(lambda dt: self.ouvrir_popup_selection_votant(joueurs_propres), 0)
        elif len(joueurs_propres) == 1:
            Clock.schedule_once(lambda dt: self.ouvrir_popup_detail(joueur_concerne=joueurs_propres[0]), 0)
        else:
            Clock.schedule_once(lambda dt: self.ouvrir_popup_detail(), 0)

        return True

    def ouvrir_popup_detail(self, joueur_concerne=None):
        """Affiche le détail d'un événement et permet au parent de voter."""
        def normaliser_nom(n):
            return " ".join(str(n or "").strip().lower().split())

        joueurs_associes = self.get_joueurs_associes_pour_parent(self.nom_parent) or []

        if joueur_concerne:
            nom_enfant_courant = str(joueur_concerne).strip()
        elif joueurs_associes:
            nom_enfant_courant = str(joueurs_associes[0]).strip()
        else:
            nom_enfant_courant = ""

        self.joueur_concerne = nom_enfant_courant

        votes = self.match_data.get("votes", {}) or {}

        def obtenir_vote_selectionne():
            if not nom_enfant_courant:
                return {}
            target = normaliser_nom(nom_enfant_courant)
            for cle, data in votes.items():
                if normaliser_nom(cle) == target:
                    return data if isinstance(data, dict) else {"disponibilite": data}
            return {}

        content = BoxLayout(orientation='vertical', padding=dp(20), spacing=dp(10))
        with content.canvas.before:
            Color(1, 1, 1, 1)
            content.bg_rect = RoundedRectangle(pos=content.pos, size=content.size, radius=[dp(10)])
        content.bind(pos=lambda s, val: setattr(s.bg_rect, 'pos', val), size=lambda s, val: setattr(s.bg_rect, 'size', val))

        titre = self.match_data.get("titre", self.match_data.get("adversaire", "Détails de l'événement"))
        content.add_widget(Label(text=f"[b]{escape_markup(str(titre))}[/b]", markup=True, font_size=f"{self.user_font_size + 2}sp", color=(0.1, 0.1, 0.3, 1), size_hint_y=None, height=dp(40), halign='center'))

        if nom_enfant_courant:
            lbl_votant = Label(text=f"[b]Vote pour : {escape_markup(nom_enfant_courant)}[/b]", markup=True, font_size=f"{self.user_font_size}sp", color=(0.1, 0.45, 0.2, 1), size_hint_y=None, height=dp(35), halign='center')
            lbl_votant.bind(width=lambda s, w: setattr(s, 'text_size', (w, None)))
            content.add_widget(lbl_votant)

        info_scroll = ScrollView(bar_width=0, size_hint=(1, 1))
        info_box = BoxLayout(orientation='vertical', size_hint_y=None, spacing=dp(8), padding=dp(5))
        info_box.bind(minimum_height=info_box.setter('height'))

        def add_info_row(label, val):
            if val:
                lbl = Label(text=f"[b]{label} :[/b] {escape_markup(str(val))}", markup=True, font_size=f"{self.user_font_size - 1}sp", color=(0.1, 0.1, 0.1, 1), size_hint_y=None, height=dp(30), halign='left', valign='middle')
                lbl.bind(width=lambda s, w: setattr(s, 'text_size', (w, None)))
                info_box.add_widget(lbl)

        for label, value in [
            ("Type", self.match_data.get("type")), ("Titre", self.match_data.get("titre")),
            ("Adversaire", self.match_data.get("adversaire")), ("Date", self.match_data.get("date")),
            ("Heure", self.match_data.get("heure", self.match_data.get("heure_rdv"))), ("Lieu", self.match_data.get("lieu")),
        ]:
            add_info_row(label, value)

        def afficher_popup_votes(titre_votes, sections_dict):
            pop_content = BoxLayout(orientation='vertical', padding=dp(20), spacing=dp(10))
            with pop_content.canvas.before:
                Color(1, 1, 1, 1)
                pop_content.bg_rect = RoundedRectangle(pos=pop_content.pos, size=pop_content.size, radius=[dp(10)])
            pop_content.bind(pos=lambda s, val: setattr(s.bg_rect, 'pos', val), size=lambda s, val: setattr(s.bg_rect, 'size', val))

            pop_content.add_widget(Label(text=f"[b]{escape_markup(titre_votes)}[/b]", markup=True, font_size=f"{self.user_font_size + 1}sp", color=(0.1, 0.3, 0.8, 1), size_hint_y=None, height=dp(40), halign='center'))
            sc_votes = ScrollView(bar_width=0, size_hint=(1, 1))
            box_recap = BoxLayout(orientation='vertical', size_hint_y=None, spacing=dp(5), padding=dp(5))
            box_recap.bind(minimum_height=box_recap.setter('height'))

            for titre_section, liste in sections_dict.items():
                box_recap.add_widget(Label(text=f"[b]{escape_markup(str(titre_section))} ({len(liste)}) :[/b]", markup=True, font_size=f"{self.user_font_size}sp", color=(0.1, 0.1, 0.1, 1), size_hint_y=None, height=dp(30), halign='left'))
                if liste:
                    for nom in liste:
                        lbl_nom = Label(text=f"  • {escape_markup(str(nom))}", markup=True, font_size=f"{self.user_font_size - 1}sp", color=(0.3, 0.3, 0.3, 1), size_hint_y=None, height=dp(25), halign='left')
                        lbl_nom.bind(width=lambda s, w: setattr(s, 'text_size', (w, None)))
                        box_recap.add_widget(lbl_nom)
                else:
                    box_recap.add_widget(Label(text="  • Aucun", markup=True, font_size=f"{self.user_font_size - 1}sp", color=(0.6, 0.6, 0.6, 1), size_hint_y=None, height=dp(25), halign='left'))
                box_recap.add_widget(BoxLayout(size_hint_y=None, height=dp(10)))

            sc_votes.add_widget(box_recap)
            pop_content.add_widget(sc_votes)
            sub_popup = ModalView(size_hint=(0.8, 0.7), auto_dismiss=True, background_color=(0, 0, 0, 0.6))
            sub_popup.add_widget(pop_content)

            btn_fermer = Button(text="Fermer", size_hint_y=None, height=dp(45), background_normal="", background_color=(0.82, 0.82, 0.85, 1), color=(0.15, 0.15, 0.15, 1), bold=True, font_size=f"{self.user_font_size}sp")
            btn_fermer.bind(on_release=sub_popup.dismiss)
            pop_content.add_widget(btn_fermer)
            sub_popup.open()

        type_sondage = self.match_data.get("type_sondage", "classique")
        sondage_actif = bool(self.match_data.get("sondage_actif", False))
        sondage_trajet = bool(self.match_data.get("sondage_trajet", False))

        # SECTION MULTIPLE
        if sondage_actif and type_sondage == "multiple":
            options = self.match_data.get("options_sondage", ["1", "2", "3", "4", "5"])
            titre_sondage = self.match_data.get("titre_sondage_multiple", "Votre Choix")
            info_box.add_widget(Label(text=f"[b]--- {escape_markup(str(titre_sondage))} ---[/b]", markup=True, font_size=f"{self.user_font_size}sp", color=(0.1, 0.3, 0.8, 1), size_hint_y=None, height=dp(35), halign='center'))

            vote_user_actuel = obtenir_vote_selectionne()
            val_multiple_actuel = vote_user_actuel.get("choix_multiple") if isinstance(vote_user_actuel, dict) else None
            nb_cols = min(len(options), 3)

            btn_multiple_box = GridLayout(cols=nb_cols, size_hint_y=None, height=dp(45 * ((len(options) - 1) // 3 + 1)), spacing=dp(5))

            for opt in options:
                is_selected = (str(val_multiple_actuel) == str(opt))
                couleur = (0.1, 0.7, 0.3, 1) if (not val_multiple_actuel or is_selected) else (0.85, 0.85, 0.85, 1)

                btn_opt = Button(text=str(opt), background_normal="", background_color=couleur, font_size=f"{self.user_font_size - 2}sp", bold=True, size_hint_y=None, height=dp(40))
                btn_opt.bind(on_release=lambda inst, v=opt: (print(f"[VOTE] CLICK MULTIPLE | votant={nom_enfant_courant} | choix={v}"), self.on_presence_click(self.match_id, choix_multiple=v, joueur_concerne=nom_enfant_courant), popup.dismiss()))
                btn_multiple_box.add_widget(btn_opt)

            info_box.add_widget(btn_multiple_box)
            sections_multiple = {f"Option : {opt}": [n for n, d in votes.items() if isinstance(d, dict) and str(d.get("choix_multiple")) == str(opt)] for opt in options}

            btn_voir_multiple = Button(text="Voir les votes", size_hint_y=None, height=dp(40), background_normal="", background_color=(1.0, 0.85, 0.2, 1), color=(0.15, 0.15, 0.15, 1), bold=True)
            btn_voir_multiple.bind(on_release=lambda x: afficher_popup_votes(f"Votes - {titre_sondage}", sections_multiple))
            info_box.add_widget(btn_voir_multiple)

        # SECTION DISPONIBILITE
        elif sondage_actif:
            info_box.add_widget(Label(text="[b]--- Votre Disponibilité ---[/b]", markup=True, font_size=f"{self.user_font_size}sp", color=(0.1, 0.3, 0.8, 1), size_hint_y=None, height=dp(35), halign='center'))

            vote_user_actuel = obtenir_vote_selectionne()
            val_dispo_actuelle = vote_user_actuel.get("disponibilite") if isinstance(vote_user_actuel, dict) else None

            btn_vote_box = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(45), spacing=dp(10))
            col_present = (0.1, 0.7, 0.3, 1) if (not val_dispo_actuelle or val_dispo_actuelle == "Présent") else (0.85, 0.85, 0.85, 1)
            col_absent = (0.8, 0.2, 0.2, 1) if (not val_dispo_actuelle or val_dispo_actuelle == "Absent") else (0.85, 0.85, 0.85, 1)

            btn_present = Button(text="Présent", background_normal="", background_color=col_present, font_size=f"{self.user_font_size - 2}sp", bold=True)
            btn_absent = Button(text="Absent", background_normal="", background_color=col_absent, font_size=f"{self.user_font_size - 2}sp", bold=True)

            btn_present.bind(on_release=lambda x: (print(f"[VOTE] CLICK PRESENT | votant={nom_enfant_courant}"), self.on_presence_click(self.match_id, choix="Présent", joueur_concerne=nom_enfant_courant), popup.dismiss()))
            btn_absent.bind(on_release=lambda x: (print(f"[VOTE] CLICK ABSENT | votant={nom_enfant_courant}"), self.on_presence_click(self.match_id, choix="Absent", joueur_concerne=nom_enfant_courant), popup.dismiss()))

            btn_vote_box.add_widget(btn_present)
            btn_vote_box.add_widget(btn_absent)
            info_box.add_widget(btn_vote_box)

            presents = [n for n, d in votes.items() if (d.get("disponibilite") if isinstance(d, dict) else d) == "Présent"]
            absents = [n for n, d in votes.items() if (d.get("disponibilite") if isinstance(d, dict) else d) == "Absent"]

            btn_voir_votes = Button(text="Voir les votes", size_hint_y=None, height=dp(40), background_normal="", background_color=(1.0, 0.85, 0.2, 1), color=(0.15, 0.15, 0.15, 1), bold=True)
            btn_voir_votes.bind(on_release=lambda x: afficher_popup_votes("Votes - Disponibilité", {"Présents": presents, "Absents": absents}))
            info_box.add_widget(btn_voir_votes)

        # SECTION TRAJET
        if sondage_trajet and type_sondage != "multiple":
            vote_user_actuel = obtenir_vote_selectionne()
            if isinstance(vote_user_actuel, dict) and vote_user_actuel.get("disponibilite") != "Absent":
                info_box.add_widget(Label(text="[b]--- Choix du Trajet ---[/b]", markup=True, font_size=f"{self.user_font_size}sp", color=(0.1, 0.3, 0.8, 1), size_hint_y=None, height=dp(35), halign='center'))

                btn_trajet_box = BoxLayout(orientation='vertical', size_hint_y=None, height=dp(125), spacing=dp(5))
                val_trajet = vote_user_actuel.get("trajet")

                c1 = (0.1, 0.5, 0.8, 1) if (not val_trajet or val_trajet == "Valdahon") else (0.85, 0.85, 0.85, 1)
                c2 = (0.1, 0.7, 0.3, 1) if (not val_trajet or val_trajet == "Stade adverse") else (0.85, 0.85, 0.85, 1)
                c3 = (0.8, 0.5, 0.1, 1) if (not val_trajet or val_trajet == "Besoin voiture") else (0.85, 0.85, 0.85, 1)

                b1 = Button(text="Valdahon (Départ club)", background_normal="", background_color=c1, bold=True, size_hint_y=None, height=dp(35))
                b2 = Button(text="Directement au Stade du Match", background_normal="", background_color=c2, bold=True, size_hint_y=None, height=dp(35))
                b3 = Button(text="Besoin d'une Voiture (Transport)", background_normal="", background_color=c3, bold=True, size_hint_y=None, height=dp(35))

                b1.bind(on_release=lambda x: (self.on_presence_click(self.match_id, choix_trajet="Valdahon", joueur_concerne=nom_enfant_courant), popup.dismiss()))
                b2.bind(on_release=lambda x: (self.on_presence_click(self.match_id, choix_trajet="Stade adverse", joueur_concerne=nom_enfant_courant), popup.dismiss()))
                b3.bind(on_release=lambda x: (self.on_presence_click(self.match_id, choix_trajet="Besoin voiture", joueur_concerne=nom_enfant_courant), popup.dismiss()))

                btn_trajet_box.add_widget(b1)
                btn_trajet_box.add_widget(b2)
                btn_trajet_box.add_widget(b3)
                info_box.add_widget(btn_trajet_box)

                valdahon = [n for n, d in votes.items() if isinstance(d, dict) and d.get("trajet") == "Valdahon"]
                stade_adv = [n for n, d in votes.items() if isinstance(d, dict) and d.get("trajet") == "Stade adverse"]
                besoin_voiture = [n for n, d in votes.items() if isinstance(d, dict) and d.get("trajet") == "Besoin voiture"]

                btn_voir_trajet = Button(text="Voir les votes", size_hint_y=None, height=dp(40), background_normal="", background_color=(1.0, 0.85, 0.2, 1), color=(0.15, 0.15, 0.15, 1), bold=True)
                btn_voir_trajet.bind(on_release=lambda x: afficher_popup_votes("Votes - Trajets", {"Valdahon (Départ club)": valdahon, "Sur place": stade_adv, "Besoin voiture": besoin_voiture}))
                info_box.add_widget(btn_voir_trajet)

        # JOUEURS CONVOQUES
        if self.match_data.get("activer_convocation", False) and self.match_data.get("joueurs_convoques", []):
            joueurs = self.match_data.get("joueurs_convoques", [])
            info_box.add_widget(Label(text=f"[b]--- Joueurs Convoqués ({len(joueurs)}) ---[/b]", markup=True, font_size=f"{self.user_font_size}sp", color=(0.1, 0.3, 0.8, 1), size_hint_y=None, height=dp(35), halign='center'))

            for j in joueurs:
                if isinstance(j, dict):
                    nom_j = f"[{j.get('categorie', '').upper()}] {j.get('nom', '').upper()} {j.get('prenom', '')}".strip() if j.get('est_manuel') else f"{j.get('nom', '').upper()} {j.get('prenom', '')}".strip()
                else:
                    nom_j = str(j)

                lbl_j = Label(text=f"- {escape_markup(nom_j)}", markup=True, font_size=f"{self.user_font_size - 2}sp", color=(0.1, 0.1, 0.1, 1), size_hint_y=None, height=dp(25), halign='left')
                lbl_j.bind(width=lambda s, w: setattr(s, 'text_size', (w, None)))
                info_box.add_widget(lbl_j)

        info_scroll.add_widget(info_box)
        content.add_widget(info_scroll)

        popup = Popup(title="", title_size=0, content=content, size_hint=(0.85, 0.8), separator_height=0, background="")
        popup.background_color = (0, 0, 0, 0.6)

        btn_fermer = Button(text="Fermer", size_hint_y=None, height=dp(45), background_normal="", background_color=(0.82, 0.82, 0.85, 1), color=(0.15, 0.15, 0.15, 1), bold=True, font_size=f"{self.user_font_size}sp")
        btn_fermer.bind(on_release=popup.dismiss)
        content.add_widget(btn_fermer)

        popup.open()
    
    def ouvrir_popup_selection_votant(self, joueurs_associes):
        """Affiche une popup permettant de choisir le joueur/rôle pour lequel voter."""
    
        # 1. Normalisation des joueurs
        joueurs = []
        for j in joueurs_associes or []:
            nom = (f"{j.get('nom', '')} {j.get('prenom', '')}" if isinstance(j, dict) else str(j)).strip()
            if nom and nom not in joueurs:
                joueurs.append(nom)
    
        if not joueurs:
            print("[VOTE] Aucun votant disponible.")
            return
    
        # 2. Contenu de la popup
        content = BoxLayout(orientation="vertical", padding=dp(20), spacing=dp(12))
        
        with content.canvas.before:
            Color(1, 1, 1, 1)
            bg = RoundedRectangle(pos=content.pos, size=content.size, radius=[dp(15)])
        content.bind(pos=lambda _, v: setattr(bg, "pos", v), size=lambda _, v: setattr(bg, "size", v))
    
        # 3. Titre
        content.add_widget(Label(
            text="[b]Pour qui souhaitez-vous voter ?[/b]", markup=True,
            font_size=dp(19), color=(0.1, 0.1, 0.2, 1), size_hint_y=None, height=dp(45),
            halign="center", valign="middle", text_size=(content.width, None)
        ))
        content.children[-1].bind(width=lambda s, w: setattr(s, "text_size", (w, None)))
    
        # 4. Explication alignée à gauche
        label_explication = Label(
            text="Sélectionnez la personne concernée par ce vote.",
            font_size=dp(14), color=(0.3, 0.3, 0.3, 1), size_hint_y=None, height=dp(40),
            halign="left", valign="middle", text_size=(content.width - dp(40), None)
        )
        label_explication.bind(width=lambda s, w: setattr(s, "text_size", (w, None)))
        content.add_widget(label_explication)
    
        # 5. Liste scrollable
        scroll = ScrollView(bar_width=0, size_hint=(1, 1))
        liste = GridLayout(cols=1, spacing=dp(10), padding=dp(5), size_hint_y=None)
        liste.bind(minimum_height=liste.setter("height"))
        scroll.add_widget(liste)
        content.add_widget(scroll)
    
        # 6. Popup
        popup = ModalView(size_hint=(0.85, 0.65), auto_dismiss=False, background_color=(0, 0, 0, 0.65))
        popup.add_widget(content)
    
        # 7. Fonction de sélection
        def selectionner_votant(_, votant):
            self.joueur_concerne = self._joueur_vote_selectionne = votant
            popup.dismiss()
            Clock.schedule_once(lambda dt: self.ouvrir_popup_detail(joueur_concerne=votant), 0.15)
    
        # 8. Boutons joueurs avec numérotation
        for index, nom in enumerate(joueurs, start=1):
            nom_nettoye = nom.replace('_', ' ')
            nom_affiche = f"{index}. {nom_nettoye}" if not nom.upper().startswith("COACH_") else f"{index}. Coach / Staff ({nom_nettoye})"
            
            btn = Button(
                text=nom_affiche, size_hint_y=None, height=dp(55),
                background_normal="", background_color=(0.12, 0.55, 0.85, 1),
                color=(1, 1, 1, 1), bold=True, font_size=dp(16)
            )
            btn.bind(on_release=lambda inst, v=nom: selectionner_votant(inst, v))
            liste.add_widget(btn)
    
        # 9. Bouton Annuler
        btn_annuler = Button(
            text="Annuler", size_hint_y=None, height=dp(45),
            background_normal="", background_color=(0.82, 0.82, 0.85, 1),
            color=(0.15, 0.15, 0.15, 1), bold=True
        )
        btn_annuler.bind(on_release=lambda _: popup.dismiss())
        content.add_widget(btn_annuler)
    
        # 10. Ouverture
        popup.open()
    
    def ouvrir_popup_detail_pour_joueur(self, joueur_selectionne):
        """Ouvre la popup de détail en forçant le joueur sélectionné."""
        if joueur_selectionne := str(joueur_selectionne or "").strip():
            self.joueur_concerne = self._joueur_vote_selectionne = joueur_selectionne
            self.ouvrir_popup_detail(joueur_concerne=joueur_selectionne)
        else:
            print("[VOTE] Aucun joueur selectionne.")