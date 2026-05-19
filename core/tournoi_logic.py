# -*- coding: utf-8 -*-
import os
import json
import yaml
import math
import random
from datetime import datetime, timedelta
import re
import copy
from copy import deepcopy
from pathlib import Path
import threading

from kivy.app import App
from kivy.utils import platform

# Supprime la variable globale BASE_USER_FOLDER = get_base_path()

def get_save_path(annee, nom_tournoi):
    app = App.get_running_app()
    if app and app.user_data_dir:
        base = Path(app.user_data_dir) / "save"
    else:
        # Fallback sécurisé pour iOS et le dev local : le dossier du script
        base = Path(__file__).parent / "save"
    
    path = base / str(annee)
    path.mkdir(parents=True, exist_ok=True)
    return path / f"{safe_filename(nom_tournoi)}.json"

def safe_filename(name):
    name = name.strip()
    name = re.sub(r"[^\w\- ]+", "", name)  # enlève caractères interdits
    name = name.replace(" ", "_")
    return name or "tournoi"

def parse_duree(val):
    """Convertit une durée en timedelta, supporte int (minutes) ou string MM:SS"""
    if isinstance(val, int) or isinstance(val, float):
        return timedelta(minutes=val)
    elif isinstance(val, str):
        parts = [p.strip() for p in val.split(":")]
        if len(parts) == 2:
            minutes, seconds = int(parts[0]), int(parts[1])
            return timedelta(minutes=minutes, seconds=seconds)
        elif len(parts) == 1:
            return timedelta(minutes=int(parts[0]))
    raise ValueError("Duree invalide : %s" % val)

def build_group_colors(groupes):
    COLORS = [
        "#fff0f0",  # rouge
        "#f0fff0",  # vert
        "#f0f4ff",  # bleu
        "#fffbe0",  # jaune
        "#f3e8ff",  # violet
        "#e8f7f7",  # turquoise
        "#fff1e6",  # orange
        "#f5f5f5",  # gris
    ]
    return {
        g: COLORS[i % len(COLORS)]
        for i, g in enumerate(groupes.keys())
    }

class TournoiLogic:
    def __init__(self, data, save_callback=None):
        # 1. État Interne & Threading (Initialiser en premier)
        self.save_callback = save_callback
        self._save_lock = threading.Lock()
        self._save_running = False
        self._save_thread = None
        self._save_args = None
        
        # Initialisation des caches
        self._team_to_pos_cache = {}
        self._groupes_snapshot = None
        self._real_teams_dict_snapshot = None
        self._classement_matches_cache = None
        self._classement_team_to_pos_cache = None
        self._bracket_snapshot = None

        # 2. Chargement de la configuration
        if isinstance(data, dict):
            self.config = data
        elif isinstance(data, str) and os.path.exists(data):
            try:
                with open(data, "r", encoding="utf-8") as f:
                    self.config = yaml.safe_load(f) or {}
            except Exception as e:
                print(f"[ERREUR] Lecture YAML : {e}")
                self.config = {}
        else:
            self.config = {}

        self.tournoi_data = self.config
        self.nom = self.config.get("nom", "Tournoi")
        
        parametres = self.config.get("parametres", {})
        self.date = parametres.get("date", "Non définie")
        self.annee = parametres.get("annee", "default")
        
        # 3. Initialisation des Groupes (CORRECTION NOM : _initiaux)
        groupes_cfg = self.config.get("groupes", {})
        self.groupes_initiaux = {str(g): [str(e) for e in eqs] for g, eqs in groupes_cfg.items()}
        self.groupes_dynamiques = copy.deepcopy(self.groupes_initiaux)
        self.groupes = copy.deepcopy(self.groupes_initiaux)

        # 4. Structures Matchs & Pauses
        pause_cfg = self.config.get("pauses", {})
        self.pauses_actives = pause_cfg.get("actif", False)
        self.pauses = pause_cfg.get("liste", [])
        
        m_cfg = self.config.get("matchs", {})
        self.matchs = m_cfg if isinstance(m_cfg, list) else m_cfg.get("normaux", [])
        
        self.classement = {}
        self.phases = []

        # 5. Phases finales
        phases_cfg = self.config.get("phases_finales", {})
        self.automatique = phases_cfg.get("automatique", True)
        options = phases_cfg.setdefault("options", {})
        options.setdefault("classement_final", False)
        options.setdefault("match_classement", True)

        # 6. Initialisation Logique
        self._init_classement()
        
        if self.groupes:
            # On ne génère les matchs que si la config n'est pas vide (cas du from_json)
            if self.config: 
                self.generer_matchs(preserve_scores=True)
                self.recalculer_classement()
                
                if phases_cfg.get("actif", False):
                    try:
                        self.creer_phases_finales()
                    except Exception as e:
                        print(f"[ERREUR] Création phases finales : {e}")

        # 7. Chargement Sauvegarde (Uniquement si pas d'appel par from_json)
        if self.config:
            self.load_from_save()
        
        self.total_goals = self.get_total_goals()
        try:
            self.qualifies = self.calculer_qualifies()
        except Exception:
            self.qualifies = {}

    def load_from_save(self):
        """ Charge les scores depuis le stockage local """
        save_file = get_save_path(self.annee, self.nom)
        if not save_file.exists():
            return False
        try:
            with open(save_file, "r", encoding="utf-8") as f:
                saved_data = json.load(f)
            
            self.matchs = saved_data.get("matchs", self.matchs)
            self.phases = saved_data.get("phases_finales", self.phases)
            
            self._init_classement()
            self.recalculer_classement(preserve_tab=True)
            self.total_goals = self.get_total_goals()
            return True
        except Exception as e:
            print(f"[ERREUR] Échec chargement sauvegarde : {e}")
            return False
        
    @classmethod
    def from_json(cls, data, save_callback=None):
        if not data:
            return None

        # Crée l'instance vide (le __init__ initialise groupes_initiaux à {})
        instance = cls(data={}, save_callback=save_callback)

        # Injection des métadonnées
        instance.tournoi_data = data
        instance.nom = data.get("nom", "Tournoi")
        
        parametres = data.get("parametres", {})
        instance.date = parametres.get("date", data.get("date", "Non définie"))
        instance.annee = parametres.get("annee", "default")
        instance.smartphone = parametres.get("storage", "") == "gdrive"
        
        # Groupes (MÊME NOM QUE DANS INIT)
        raw_groupes = data.get("groupes", {})
        instance.groupes_initiaux = {str(g): [str(e) for e in eqs] for g, eqs in raw_groupes.items()}
        instance.groupes_dynamiques = copy.deepcopy(instance.groupes_initiaux)
        instance.groupes = copy.deepcopy(instance.groupes_initiaux)
        
        instance.matchs = data.get("matchs", [])
        instance.pauses = data.get("pauses", [])
        instance.pauses_actives = bool(instance.pauses)

        mode = data.get("phases_finales_mode", {})
        instance.automatique = mode.get("automatique", True)
        instance.debut_phase = mode.get("debut", "huitieme")
        instance.phases = data.get("phases_finales", [])

        # Sécurité structure matchs
        for phase in instance.phases:
            for m in phase.get("matchs", []):
                m.setdefault("type", "normal")
                for key in ["SA", "SB", "TAB_A", "TAB_B", "vainqueur"]:
                    m.setdefault(key, None)

        # Reconstruction de la config
        phases_options = data.get("phases_finales_options", {})
        has_pf = any(p.get("tour") == "petite_finale" for p in instance.phases)
        
        instance.config = {
            "nom": instance.nom,
            "parametres": parametres,
            "groupes": instance.groupes,
            "pauses": {"actif": instance.pauses_actives, "liste": instance.pauses},
            "phases_finales": {
                "actif": bool(instance.phases),
                "automatique": instance.automatique,
                "debut": instance.debut_phase,
                "options": {
                    "classement_final": phases_options.get("classement_final", False),
                    "match_classement": phases_options.get("match_classement", True),
                    "petite_finale": phases_options.get("petite_finale", has_pf)
                }
            }
        }

        instance._init_classement()
        if instance.matchs or instance.phases:
            instance.recalculer_classement(preserve_tab=True)
            instance.total_goals = instance.get_total_goals()
            instance.qualifies = instance.calculer_qualifies()

        return instance
    
    def generer_matchs(self, preserve_scores=False):
        """Round-robin intercalé par tour avec préservation des scores existants"""
        # ⚡ Conserver les scores existants si nécessaire
        old_matchs = deepcopy(self.matchs) if preserve_scores else []
        p = self.config.get("parametres", {})
        heure = datetime.strptime(p.get("heure_debut", "09:00"), "%H:%M")
        duree = p.get("duree_match", 5)
        pause = p.get("pause", 0)
        duree_td = parse_duree(duree)
        pause_td = parse_duree(pause)
        rotations = {}
        max_len = max(len(eqs) for eqs in self.groupes.values())
        rounds = max_len if max_len % 2 == 1 else max_len - 1
        for g, eqs in self.groupes.items():
            l = list(eqs)
            if len(l) % 2 == 1:
                l.append("BYE")
            rotations[g] = l
        new_matchs = []
        for r in range(rounds):
            for g, eqs in rotations.items():
                n = len(eqs)
                for i in range(n // 2):
                    a, b = eqs[i], eqs[n - 1 - i]
                    if "BYE" in (a, b):
                        continue
                    # 🔀 RANDOMISATION A / B
                    #if random.random() < 0.5:
                    #    a, b = b, a
                    # 🔹 Chercher ancien match correspondant pour récupérer scores
                    old_m = next(
                        (m for m in old_matchs if m.get("A") == a and m.get("B") == b and m.get("groupe") == g),
                        {}
                    )
                    new_matchs.append({
                        "heure": heure.strftime("%H:%M:%S"),
                        "groupe": g,
                        "tour": r + 1,
                        "A": a,
                        "B": b,
                        "SA": old_m.get("SA"),
                        "SB": old_m.get("SB"),
                        "TAB_A": old_m.get("TAB_A"),
                        "TAB_B": old_m.get("TAB_B")
                    })
                    heure += duree_td + pause_td
                if len(eqs) > 2:
                    rotations[g] = [eqs[0]] + [eqs[-1]] + eqs[1:-1]
        self.matchs = new_matchs

    def update_petite_finale_from_demi(self):
        demi_phase = next((p for p in self.phases if p["tour"] == "demi"), None)
        petite_phase = next((p for p in self.phases if p["tour"] == "petite_finale"), None)
        if not demi_phase or not petite_phase:
            return
        perdants = []
        for m in demi_phase["matchs"]:
            winner = self.compute_winner(m)
            if not winner:
                continue
            a = m.get("A")
            b = m.get("B")
            if not a or not b:
                continue
            loser = b if winner == a else a
            perdants.append(loser)    
        if len(perdants) >= 2:
            pf_match = petite_phase["matchs"][0]
            pf_match["A"] = perdants[0]
            pf_match["B"] = perdants[1]

    def compute_winner(self, match):
        sa = match.get("SA")
        sb = match.get("SB")  
        if sa is None or sb is None:
            return None   
        if sa > sb:
            return match.get("A")
        if sb > sa:
            return match.get("B")   
        # Match nul → regarder TAB
        tab_a = match.get("TAB_A")
        tab_b = match.get("TAB_B")    
        if tab_a is None or tab_b is None:
            return None   
        if tab_a > tab_b:
            return match.get("A")
        if tab_b > tab_a:
            return match.get("B")   
        return None
    
    def recalc_first_round_if_necessary(self):
        """
        Recalcule toujours le 1er tour en mode automatique
        pour garantir cohérence avec le classement poules.
        """
        if not getattr(self, "automatique", True):
            return   
        if not self.phases:
            return    
        # 🔥 On ne régénère QUE si aucun match du 1er tour n'est joué
        premiere_phase = self.phases[0]   
        phase_jouee = any(
            m.get("SA") is not None and m.get("SB") is not None
            for m in premiere_phase["matchs"]
            if m.get("type") != "classement"
        )  
        if not phase_jouee:
            self._reset_phases_scores()
            self.generate_first_round()  
        self.update_phase_after_match()   
    
    def calculer_qualifies(self):   
        classement_groupes = self.classement_par_groupe()
        groupes = list(classement_groupes.keys())
        nb_groupes = len(groupes)  
        if not self.phases or nb_groupes == 0:
            return {}
        premiere_phase = self.phases[0]
        tour = premiere_phase.get("tour", "quart").lower()  
        correspondance = {
            "huitieme": 16,
            "quart": 8,
            "demi": 4,
            "finale": 2
        }
        total_qualifies_attendus = correspondance.get(tour, 0)
        if total_qualifies_attendus == 0:
            return {}
        qualifies_par_groupe = total_qualifies_attendus // nb_groupes
        qualifies = {}
        for groupe, classement in classement_groupes.items():
            # 🔹 Tri par points, puis diff, puis ordre alphabétique
            classement_ordonnee = sorted(
                classement,
                key=lambda x: (-x[1]["pts"], -x[1]["diff"], x[0])
            )
            qualifies[groupe] = [equipe[0] for equipe in classement_ordonnee[:qualifies_par_groupe]]
        reste_a_qualifier = total_qualifies_attendus - (qualifies_par_groupe * nb_groupes)
        if reste_a_qualifier > 0:
            position = qualifies_par_groupe  # ⚠️ À corriger (voir plus bas)
            while reste_a_qualifier > 0:
                candidats = []
                for groupe, classement in classement_groupes.items():
                    classement_ordonnee = sorted(
                        classement,
                        key=lambda x: (-x[1]["pts"], -x[1]["diff"], x[0])
                    )
                    if len(classement_ordonnee) > position:
                        equipe, stats = classement_ordonnee[position]
                        candidats.append((equipe, groupe, stats))
                if not candidats:
                    break
                # ✅ TRI GLOBAL (LE PLUS IMPORTANT)
                candidats = sorted(
                    candidats,
                    key=lambda x: (-x[2]["pts"], -x[2]["diff"], x[0])
                )
                # ✅ On prend les meilleurs seulement
                for equipe, groupe, _ in candidats:
                    if reste_a_qualifier == 0:
                        break
                    qualifies[groupe].append(equipe)
                    reste_a_qualifier -= 1
                position += 1
        return qualifies

    def distribuer_qualifies_bracket(self, qualifies_par_groupe: dict):
        groupes = sorted(qualifies_par_groupe.keys())
        nb_groupes = len(groupes)
        nb_qual_par_groupe = [len(eq) for eq in qualifies_par_groupe.values()]
        total_equipes = sum(nb_qual_par_groupe)
        bracket = [None] * total_equipes
        # --- Cas spécial : un seul groupe ---
        if len(qualifies_par_groupe) == 1:
            equipes = list(qualifies_par_groupe.values())[0]
            n = len(equipes)
            # --- Fonction de seeding tennis ---
            def generate_seed_positions(n):
                if n == 1:
                    return [1]
                prev = generate_seed_positions(n // 2)
                res = []
                for p in prev:
                    res.append(p)
                    res.append(n + 1 - p)
                return res
            # --- Adapter à puissance de 2 (BYE si nécessaire) ---
            next_pow2 = 2 ** math.ceil(math.log2(n))
            equipes_extended = equipes[:]
            while len(equipes_extended) < next_pow2:
                equipes_extended.append(None)  # BYE
            # --- Génération du bracket seedé ---
            positions = generate_seed_positions(len(equipes_extended))
            bracket = [None] * len(equipes_extended)
            for i, seed in enumerate(positions):
                bracket[i] = equipes_extended[seed - 1]
            return bracket
        # --- Cas spécial : demi-directe ---
        if all(n == 1 for n in nb_qual_par_groupe):
            equipes = [qualifies_par_groupe[g][0] for g in groupes]
            gauche = equipes[:len(equipes)//2]
            droite = equipes[len(equipes)//2:]
            droite.reverse()
            bracket = []
            for i in range(len(gauche)):
                bracket.append(gauche[i])
                bracket.append(droite[i])
            return bracket
        # --- Si divisible sans reste, on garde le code actuel ---
        quart_size = total_equipes / 4
        tailles = [len(eqs) for eqs in qualifies_par_groupe.values()]
        if len(set(tailles)) == 1:
            # --- Etape 1 : placement des 1ers ---
            step = total_equipes // nb_groupes
            for i, g in enumerate(groupes):
                bracket[i * step] = qualifies_par_groupe[g][0]
            # --- Etape 2 : placement des derniers contre 1ers ---
            derniers = [qualifies_par_groupe[g][-1] for g in groupes][::-1]
            for i, g in enumerate(groupes):
                candidate = derniers[i]
                pos_1er = bracket.index(qualifies_par_groupe[g][0])
                placed = False
                for offset in range(1, step):
                    idx = (pos_1er + offset) % total_equipes
                    g_candidate = next(grp for grp in groupes if candidate in qualifies_par_groupe[grp])
                    if bracket[idx] is None and g_candidate != g:
                        bracket[idx] = candidate
                        placed = True
                        break
                if not placed:
                    for idx in range(total_equipes):
                        if bracket[idx] is None:
                            bracket[idx] = candidate
                            break
            # --- Etape 3 : placement des 2èmes dans l'autre moitié du bracket ---
            for g in groupes:
                e1 = qualifies_par_groupe[g][0]
                if len(qualifies_par_groupe[g]) > 1:
                    e2 = qualifies_par_groupe[g][1]
                else:
                    continue
                if e2 in bracket:
                    continue
                pos_1er = bracket.index(e1)
                half_offset = total_equipes // 2
                target_pos = (pos_1er + half_offset) % total_equipes
                placed = False
                for i in range(total_equipes // 2):
                    idx = (target_pos + i) % total_equipes
                    if bracket[idx] is None:
                        bracket[idx] = e2
                        placed = True
                        break
            # --- Etape 4 : placement intelligent des restantes ---
            restantes = [e for g in groupes for e in qualifies_par_groupe[g] if e not in bracket]
            quartiers = [list(range(i, i + 4)) for i in range(0, total_equipes, 4)]
            for q in quartiers:
                free_slots = [idx for idx in q if bracket[idx] is None]
                for idx in free_slots:
                    if not restantes:
                        break
                    for i, equipe in enumerate(restantes):
                        g_equipe = next(g for g in groupes if equipe in qualifies_par_groupe[g])
                        groupes_dans_quartier = set(
                            next(g for g in groupes if bracket[p] in qualifies_par_groupe[g])
                            for p in q if bracket[p] is not None
                        )
                        if g_equipe not in groupes_dans_quartier:
                            bracket[idx] = equipe
                            restantes.pop(i)
                            break
                    else:
                        bracket[idx] = restantes.pop(0)
            return bracket
        else:
            # --- Étape 1 : placer les 1ers de chaque groupe ---
            step = (total_equipes) // (nb_groupes+1)  # espacement approx
            for i, g in enumerate(groupes):
                bracket[i * step] = qualifies_par_groupe[g][0]
            # Vérifier quels matchs sont encore vides et ajouter un ou plusieurs 2ème pour avoir au moins une équipe
            for idx in range(0, total_equipes, 2):  # parcours par match
                if bracket[idx] is None:
                    # Vérifier si la deuxième case existe et est vide
                    if idx + 1 < total_equipes:
                        if bracket[idx + 1] is None:
                            # match vide complet
                            for g in groupes:
                                if len(qualifies_par_groupe[g]) > 1 and qualifies_par_groupe[g][1] not in bracket:
                                    bracket[idx] = qualifies_par_groupe[g][1]
                                    break
            # --- Étape 2 : placer les qualifiés les plus faibles contre les 1ers ---
            # Construire les rangs du pire au meilleur (dernier, avant-dernier, etc.)
            max_len = max(len(v) for v in qualifies_par_groupe.values())
            rangs = []
            for pos in range(max_len - 1, -1, -1):  # du dernier au premier
                rang = []
                for g in groupes:
                    if len(qualifies_par_groupe[g]) > pos:
                        rang.append((g, qualifies_par_groupe[g][pos]))
                rangs.append(rang)
            # Liste plate des candidats dans le bon ordre
            candidats = []
            for rang in rangs:
                for g, equipe in rang:
                    candidats.append((g, equipe))
            # On va consommer les candidats au fur et à mesure
            utilises = set()
            for g in groupes:
                e1 = qualifies_par_groupe[g][0]
                pos_1er = bracket.index(e1)
                placed = False
                for i, (g_candidate, candidate) in enumerate(candidats):
                    # 🔥 correction ici
                    if candidate in utilises or candidate in bracket:
                        continue
                    if g_candidate == g:
                        continue  # pas même groupe que le 1er
                    # Chercher une position valide autour du 1er
                    for offset in range(1, total_equipes):
                        idx = (pos_1er + offset) % total_equipes
                        if bracket[idx] is not None:
                            continue
                        # Déterminer adversaire dans le match
                        voisin_idx = idx + 1 if idx % 2 == 0 else idx - 1
                        voisin = bracket[voisin_idx] if 0 <= voisin_idx < total_equipes else None
                        if voisin:
                            g_voisin = next(grp for grp in groupes if voisin in qualifies_par_groupe[grp])
                            if g_voisin == g_candidate:
                                continue  # même groupe dans le match interdit
                        # OK on place
                        bracket[idx] = candidate
                        utilises.add(candidate)
                        placed = True
                        break
                    if placed:
                        break
            # --- Étape 3 : compléter les cases où on avait ajouté un 2ème ---
            restantes = [e for g in groupes for e in qualifies_par_groupe[g] if e not in bracket]
            for idx in range(total_equipes):
                if bracket[idx] is not None:
                    continue
                if not restantes:
                    break
                # placer un dernier qualifié restant si possible, sinon avant-dernier
                for i, equipe in enumerate(restantes):
                    bracket[idx] = equipe
                    restantes.pop(i)
                    break
            # --- Étape 4 : placer les 2èmes encore non choisis dans l'autre moitié du bracket ---
            for g in groupes:
                if len(qualifies_par_groupe[g]) > 1:
                    e2 = qualifies_par_groupe[g][1]
                else:
                    continue
                if e2 in bracket:
                    continue
                pos_1er = bracket.index(qualifies_par_groupe[g][0])
                half_offset = total_equipes // 2
                target_pos = (pos_1er + half_offset) % total_equipes
                placed = False
                for i in range(total_equipes // 2):
                    idx = (target_pos + i) % total_equipes
                    if bracket[idx] is None:
                        bracket[idx] = e2
                        placed = True
                        break
            # --- Étape 5 : placer les dernières équipes restantes de façon intelligente ---
            restantes = [e for g in groupes for e in qualifies_par_groupe[g] if e not in bracket]
            quartiers = [list(range(i, min(i + 4, total_equipes))) for i in range(0, total_equipes, 4)]
            for q in quartiers:
                free_slots = [idx for idx in q if bracket[idx] is None]
                for idx in free_slots:
                    if not restantes:
                        break
                    for i, equipe in enumerate(restantes):
                        g_equipe = next(g for g in groupes if equipe in qualifies_par_groupe[g])
                        groupes_dans_quartier = set(
                            next(g for g in groupes if bracket[p] in qualifies_par_groupe[g])
                            for p in q if bracket[p] is not None
                        )
                        if g_equipe not in groupes_dans_quartier:
                            bracket[idx] = equipe
                            restantes.pop(i)
                            break
                    else:
                        # fallback si impossible d’éviter doublon de groupe
                        if restantes:
                            bracket[idx] = restantes.pop(0)
            return bracket
    
    def generate_first_round(self):
        if not getattr(self, "automatique", True):
            return
        # 🔹 Calcul des équipes qualifiées
        qualifies_par_groupe = self.calculer_qualifies()
        if not qualifies_par_groupe:
            return
        # 🔹 Distribution intelligente dans le bracket
        bracket_slots = self.distribuer_qualifies_bracket(qualifies_par_groupe)
        total_equipes = len(bracket_slots)
        # 🔹 Création ou récupération de la phase
        if not self.phases:
            # Créer une phase si elle n'existe pas
            debut_tour = self.config.get("parametres", {}).get("tour", "quart").lower()
            self.phases = [{"tour": debut_tour, "matchs": []}]
            nb_matchs = total_equipes // 2
            for _ in range(nb_matchs):
                self.phases[0]["matchs"].append({
                    "A": None, "B": None,
                    "SA": None, "SB": None,
                    "vainqueur": None,
                    "TAB_A": None, "TAB_B": None
                })
        premiere_phase = self.phases[0]
        # 🔹 Injection des équipes dans les matchs
        for idx, match in enumerate(premiere_phase["matchs"]):
            i_a, i_b = idx * 2, idx * 2 + 1
            if i_a < total_equipes and i_b < total_equipes:
                match["A"] = bracket_slots[i_a]
                match["B"] = bracket_slots[i_b]
        # 🔹 Propagation des vainqueurs / petite finale
        self.update_phase_after_match()

    def update_phase_after_match(self):
        """
        Remplace l'ancienne méthode propagate().
        Met à jour :
        - vainqueurs
        - propagation tours suivants
        - petite finale
        - classement
        """
        if not hasattr(self, "phases"):
            return
        # 1️⃣ Calcul des vainqueurs
        for phase in self.phases:
            for m in phase["matchs"]:
                m["vainqueur"] = self.compute_winner(m)
        # 2️⃣ Propagation normale (hors petite finale)
        self._propagate_winner()
        # 3️⃣ Petite finale
        self.update_petite_finale_from_demi()
        # 4️⃣ Recalcul classement
        self.recalculer_classement()
    
    def _propagate_winner(self):
        """
        Met à jour les phases finales en propagant les vainqueurs vers les tours suivants.
        Ne fait pas de propagation pour la petite finale.
        Gère les égalités avec tirs aux buts et évite les IndexError.
        """
        for phase_index, phase in enumerate(self.phases[:-1]):  # ignore petite finale
            next_phase = self.phases[phase_index + 1] if phase_index + 1 < len(self.phases) else None
            if not next_phase:
                continue
            for match_index, match in enumerate(phase['matchs']):
                A, B = match.get('A'), match.get('B')
                SA, SB = match.get('SA'), match.get('SB')
                TAB_A, TAB_B = match.get('TAB_A'), match.get('TAB_B')
                # 🔹 Déterminer le vainqueur correctement
                vainqueur = None
                if SA is not None and SB is not None:
                    if SA > SB:
                        vainqueur = A
                    elif SB > SA:
                        vainqueur = B
                    else:
                        # Egalité → regarder tir au but
                        if TAB_A is not None and TAB_B is not None:
                            if TAB_A > TAB_B:
                                vainqueur = A
                            elif TAB_B > TAB_A:
                                vainqueur = B
                            else:
                                vainqueur = None  # match TAB égal improbable
                        else:
                            vainqueur = None  # match nul sans TAB
                match['vainqueur'] = vainqueur
                # 🔹 Propagation vers le tour suivant (si index valide)
                if next_phase:
                    next_match_index = match_index // 2
                    if next_match_index < len(next_phase['matchs']):
                        next_slot = 'A' if match_index % 2 == 0 else 'B'
                        next_phase['matchs'][next_match_index][next_slot] = vainqueur
       
    def recalc_all(self):
        # 1️⃣ Recalcul classement poules
        self.recalculer_classement()
        # 2️⃣ Vérifier si une phase finale contient déjà des matchs COMPLETEMENT joués
        phases_deja_jouees = False
        for phase in getattr(self, "phases", []):
            for m in phase.get("matchs", []):
                if m.get("SA") is not None and m.get("SB") is not None:
                    phases_deja_jouees = True
                    break
            if phases_deja_jouees:
                break
        # 3️⃣ Gestion automatique
        if getattr(self, "automatique", True):
            # Si aucune phase finale réellement jouée → reconstruction
            if not phases_deja_jouees:
                self._reset_phases_scores()
                self.generate_first_round()
            # 🔥 Toujours recalculer les matchs de classement
            self.remplir_matchs_classement()
        # 4️⃣ Propagation des vainqueurs
        self._propagate_winner()
        # 5️⃣ Mise à jour complète
        self.update_phase_after_match()
        # 6️⃣ Total buts
        total = self.get_total_goals()
        #if hasattr(self, "total_goals_var"):
        #    self.total_goals_var.set(f"Total buts : {total}")
        return total

    def _reset_phases_scores(self):
        """
        Supprime tous les scores et vainqueurs
        pour forcer une reconstruction propre
        """
        for phase in self.phases:
            for match in phase["matchs"]:
                match["SA"] = None
                match["SB"] = None
                match["TAB_A"] = None
                match["TAB_B"] = None
                match["vainqueur"] = None

    def get_total_goals(self, debug=False):
        """
        Calcule le total des buts marqués, poules + phases finales (hors TAB).
        debug=True => affichage détaillé pour debug
        """
        total = 0
        # --- Matchs de poule ---
        for m in self.matchs:
            sa, sb = m.get("SA"), m.get("SB")
            if sa is not None and sb is not None:
                total += sa + sb
                if debug:
                    print(f"[Poules] {m.get('A')} {sa} - {sb} {m.get('B')} => total={total}")
        # --- Phases finales ---
        for phase_index, phase in enumerate(getattr(self, "phases", [])):
            for m_index, m in enumerate(phase.get("matchs", [])):
                sa, sb = m.get("SA"), m.get("SB")
                if sa is not None and sb is not None:
                    total += sa + sb
                    if debug:
                        print(f"[Phase {phase_index+1}] {m.get('A')} {sa} - {sb} {m.get('B')} => total={total}")
                else:
                    if debug:
                        print(f"[Phase {phase_index+1}] Match {m_index+1} incomplet: SA={sa} SB={sb}")
        if debug:
            print(f"TOTAL BUTS = {total}\n")
        return total
   
    def recalculer_classement(self, preserve_tab=False):
        """Recalcule le classement pour tous les matchs (poules + phases finales)"""
        self._init_classement()
        # 🔹 Matchs de poule
        for m in self.matchs:
            if m.get("groupe") not in self.groupes:
                continue
            self._traiter_match(m, preserve_tab=preserve_tab)
        # 🔹 Différence de buts
        for e, d in self.classement.items():
            d["diff"] = d["bp"] - d["bc"]
        # 🔹 Mise à jour des groupes dynamiques selon le classement actuel
        self.groupes_dynamiques = {}
        for g, equipes in self.groupes_initiaux.items():
            sorted_eqs = sorted(
                equipes,
                key=lambda e: (
                    -self.classement.get(e, {}).get("pts", 0),  # points
                    -(self.classement.get(e, {}).get("bp", 0) - self.classement.get(e, {}).get("bc", 0)),  # diff
                    -self.classement.get(e, {}).get("bp", 0),
                    e.lower()  # stabilité du tri
                )
            )
            self.groupes_dynamiques[g] = sorted_eqs
    
    # ---------------------------------------
    def _traiter_match(self, match, preserve_tab=False):
        SA = match.get("SA")
        SB = match.get("SB")
        A = match.get("A")
        B = match.get("B")
        # 🔴 Match non joué → on ignore
        if SA is None or SB is None:
            return
        # --- Traitement équipe A ---
        if A in self.classement:
            self.classement[A]["bp"] += SA
            self.classement[A]["bc"] += SB
            self.classement[A]["victoires"] += 1 if SA > SB else 0
            self.classement[A]["nuls"] += 1 if SA == SB else 0
            self.classement[A]["defaites"] += 1 if SA < SB else 0
            self.classement[A]["pts"] += 3 if SA > SB else 1 if SA == SB else 0
        # --- Traitement équipe B ---
        if B in self.classement:
            self.classement[B]["bp"] += SB
            self.classement[B]["bc"] += SA
            self.classement[B]["victoires"] += 1 if SB > SA else 0
            self.classement[B]["nuls"] += 1 if SB == SA else 0
            self.classement[B]["defaites"] += 1 if SB < SA else 0
            self.classement[B]["pts"] += 3 if SB > SA else 1 if SB == SA else 0
        # 🔹 Gestion TAB seulement si match nul
        if SA == SB:
            if not preserve_tab:
                match.setdefault("TAB_A", 0)
                match.setdefault("TAB_B", 0)
       
    def _init_classement(self):
        self.classement = {}
        for g, equipes in self.groupes.items():
            for e in equipes:
                self.classement[e] = {
                    "groupe": g,
                    "pts": 0,
                    "victoires": 0,
                    "nuls": 0,
                    "defaites": 0,
                    "bp": 0,
                    "bc": 0,
                    "diff": 0
                }

    def classement_par_groupe(self):
        """
        Retourne le classement recalculé par groupe.
        ⚡ Ne prend en compte que les matchs de poule (ceux avec 'groupe' défini)
        """
        # 1️⃣ Réinitialisation des stats
        classement_temp = {}
        for g, equipes in self.groupes.items():
            for e in equipes:
                classement_temp[e] = {
                    "pts": 0,
                    "victoires": 0,
                    "nuls": 0,
                    "defaites": 0,
                    "bp": 0,
                    "bc": 0,
                    "diff": 0,
                    "groupe": g
                }
        # 2️⃣ Parcours de tous les matchs    
        for m in self.matchs:
            groupe = m.get("groupe")
            if not groupe:
                continue
            a, b = m.get("A"), m.get("B")
            sa, sb = m.get("SA"), m.get("SB")
            if a not in classement_temp or b not in classement_temp:
                continue
            if sa is None or sb is None:
                continue
            # ⚡ Mise à jour des buts
            classement_temp[a]["bp"] += sa
            classement_temp[a]["bc"] += sb
            classement_temp[b]["bp"] += sb
            classement_temp[b]["bc"] += sa
            # ⚡ Victoire / nul / défaite et pts
            if sa > sb:
                classement_temp[a]["victoires"] += 1
                classement_temp[a]["pts"] += 3
                classement_temp[b]["defaites"] += 1
            elif sb > sa:
                classement_temp[b]["victoires"] += 1
                classement_temp[b]["pts"] += 3
                classement_temp[a]["defaites"] += 1
            else:
                classement_temp[a]["nuls"] += 1
                classement_temp[b]["nuls"] += 1
                classement_temp[a]["pts"] += 1
                classement_temp[b]["pts"] += 1
        # 3️⃣ Calcul de la différence de buts
        for eq, stats in classement_temp.items():
            stats["diff"] = stats["bp"] - stats["bc"]
        # 4️⃣ Construction du classement par groupe
        groupes_dict = {}
        for g, equipes in self.groupes.items():
            eqs = []
            for e in equipes:
                eqs.append((e, classement_temp[e]))
            # Tri par points, différence, bp
            eqs.sort(
                key=lambda x: (
                    -x[1]["pts"],
                    -x[1]["diff"],
                    -x[1]["bp"],
                    x[0].lower()
                )
            )
            groupes_dict[g] = eqs
        return groupes_dict

    def creer_phases_finales(self):
        cfg = self.config.get("phases_finales", {})
        debut = cfg.get("debut", "quart")
        self.automatique = cfg.get("automatique", True)
        tours = ["huitieme", "quart", "demi", "finale"]
        start_idx = tours.index(debut)
        nb_matchs = {"huitieme": 8, "quart": 4, "demi": 2, "finale": 1}
        phases = []
        for t in tours[start_idx:]:
            matchs = []
            for _ in range(nb_matchs[t]):
                matchs.append({
                    "A": "",
                    "B": "",
                    "SA": None,
                    "SB": None,
                    "vainqueur": None
                })
            phases.append({"tour": t, "matchs": matchs})
        # -----------------------
        # PETITE FINALE
        # -----------------------
        options = cfg.get("options", {})
        if options.get("petite_finale", False):
            phases.append({
                "tour": "petite_finale",
                "matchs": [{
                    "A": "",
                    "B": "",
                    "SA": None,
                    "SB": None,
                    "vainqueur": None
                }]
            })
        # -----------------------
        # MATCHS DE CLASSEMENT
        # -----------------------
        if options.get("match_classement", False):
            nb_groupes = len(self.groupes)
            # uniquement si nombre pair
            if nb_groupes % 2 == 0:
                qualifies_per_group = (nb_matchs[debut] * 2) // nb_groupes
                taille_groupe = len(next(iter(self.groupes.values())))
                nb_non_qualifies = taille_groupe - qualifies_per_group
                matchs_classement = []
                for _ in range(nb_non_qualifies * (nb_groupes // 2)):
                    matchs_classement.append({
                        "A": "",
                        "B": "",
                        "SA": None,
                        "SB": None,
                        "vainqueur": None,
                        "type": "classement"
                    })
                # ajout sous le 1er tour
                phases[0]["matchs"].extend(matchs_classement)
        self.phases = phases
                              
    def compute_classement_final(self):  
        automatique = getattr(self, "automatique", True)
        toutes_equipes = set(e for eqs in self.groupes.values() for e in eqs)
        if not self.phases:
            return None
        phases = self.phases
        # --------------------------------------------------
        # Vérification matchs joués
        # --------------------------------------------------
        for phase in self.phases:
            for match in phase.get("matchs", []):
                if match.get("SA") is None or match.get("SB") is None:
                    return None
        # --------------------------------------------------
        # Classement poules
        # --------------------------------------------------
        try:
            classement_groupes = self.classement_par_groupe()
        except:
            classement_groupes = {}
        position_poule = {}
        for g, data in classement_groupes.items():
            for idx, (eq, _) in enumerate(data):
                position_poule[eq] = idx + 1
        # --------------------------------------------------
        # Détermination équipes qualifiées
        # --------------------------------------------------
        premiere_phase = self.phases[0]
        qualifies = set()
        if automatique:
            qualifies.update(
                eq
                for eqs in self.calculer_qualifies().values()
                for eq in eqs
            )
        else:
            # MODE MANUEL
            for match in premiere_phase.get("matchs", []):
                if match.get("type") == "classement":
                    continue
                if match.get("A"):
                    qualifies.add(match["A"])
                if match.get("B"):
                    qualifies.add(match["B"])          
        non_qualifies = toutes_equipes - qualifies
        # --------------------------------------------------
        # Initialisation stats
        # --------------------------------------------------
        stats_dyn = {
            eq: {"J":0,"V":0,"N":0,"D":0,"BP":0,"BC":0,"Diff":0}
            for eq in toutes_equipes
        }
        # --------------------------------------------------
        # Injection stats poules (TOUJOURS)
        # --------------------------------------------------
        for g, data in classement_groupes.items():
            for eq, st in data:
                stats_dyn[eq]["J"] += st["victoires"] + st["nuls"] + st["defaites"]
                stats_dyn[eq]["V"] += st["victoires"]
                stats_dyn[eq]["N"] += st["nuls"]
                stats_dyn[eq]["D"] += st["defaites"]
                stats_dyn[eq]["BP"] += st["bp"]
                stats_dyn[eq]["BC"] += st["bc"]
                stats_dyn[eq]["Diff"] = stats_dyn[eq]["BP"] - stats_dyn[eq]["BC"]
        # --------------------------------------------------
        # Parcours phases finales
        # --------------------------------------------------
        encore_en_lice = sorted(
            qualifies,
            key=lambda e: position_poule.get(e, 999)
        )
        demi_perdants = []
        finale_match = None
        petite_finale_match = None
        matchs_classement_non_qualifies = []
        for phase in self.phases:
            tour = phase.get("tour", "").lower()
            perdants_tour = []
            for match in phase.get("matchs", []):
                eq1 = match.get("A")
                eq2 = match.get("B")
                if not eq1 or not eq2:
                    continue
                sa = match.get("SA")
                sb = match.get("SB")
                # stats buts
                stats_dyn[eq1]["J"] += 1
                stats_dyn[eq2]["J"] += 1
                stats_dyn[eq1]["BP"] += sa
                stats_dyn[eq1]["BC"] += sb
                stats_dyn[eq2]["BP"] += sb
                stats_dyn[eq2]["BC"] += sa
                stats_dyn[eq1]["Diff"] = stats_dyn[eq1]["BP"] - stats_dyn[eq1]["BC"]
                stats_dyn[eq2]["Diff"] = stats_dyn[eq2]["BP"] - stats_dyn[eq2]["BC"]
                winner = self.compute_winner(match)
                if winner is None:
                    continue
                loser = eq2 if winner == eq1 else eq1
                stats_dyn[winner]["V"] += 1
                stats_dyn[loser]["D"] += 1
                # --------------------------------------------------
                # Matchs classement non qualifiés
                # --------------------------------------------------
                if eq1 in non_qualifies and eq2 in non_qualifies:
                    if automatique:
                        matchs_classement_non_qualifies.append((winner, loser))
                    continue
                # --------------------------------------------------
                # Phases normales
                # --------------------------------------------------
                if tour == "demi":
                    demi_perdants.append(loser)
                elif tour in ["petite_finale","petite finale"]:
                    petite_finale_match = match
                elif tour == "finale":  
                    finale_match = match
                else:
                    perdants_tour.append(loser)
            # Attribution rangs perdants tour
            if perdants_tour:
                rang = len(encore_en_lice) - len(perdants_tour) + 1
                for eq in perdants_tour:
                    stats_dyn[eq]["rang"] = rang
                    if eq in encore_en_lice:
                        encore_en_lice.remove(eq)
        # --------------------------------------------------
        # Finale
        # --------------------------------------------------
        if finale_match:
            winner = self.compute_winner(finale_match)
            if winner:
                loser = finale_match["B"] if winner == finale_match["A"] else finale_match["A"]
                stats_dyn[winner]["rang"] = 1
                stats_dyn[loser]["rang"] = 2
        # --------------------------------------------------
        # Petite finale
        # --------------------------------------------------
        if petite_finale_match:
            winner = self.compute_winner(petite_finale_match)
            if winner:
                loser = petite_finale_match["B"] if winner == petite_finale_match["A"] else petite_finale_match["A"]
                # 🔒 écrase les rangs
                stats_dyn[winner]["rang"] = 3
                stats_dyn[loser]["rang"] = 4
                # 🔒 nettoyer demi_perdants
                demi_perdants = [eq for eq in demi_perdants if eq not in (winner, loser)]
        elif demi_perdants:
            # 🔒 sécurité : max 2 équipes
            for eq in demi_perdants[:2]:
                stats_dyn[eq]["rang"] = 3
        # --------------------------------------------------
        # Matchs classement non qualifiés
        # --------------------------------------------------
        phases_finales_options = self.config.get("phases_finales_options", None)
        if isinstance(phases_finales_options, dict) and "match_classement" in phases_finales_options:
            match_classement = phases_finales_options.get("match_classement", True)
            source = "config.phases_finales_options"
        else:
            match_classement = self.config.get("phases_finales", {}) \
                .get("options", {}) \
                .get("match_classement", True)
            source = "config.phases_finales.options"
        if match_classement:
            if automatique and matchs_classement_non_qualifies:
                matchs_par_position = {}
                for winner, loser in matchs_classement_non_qualifies:
                    pos = position_poule.get(winner, 1000)
                    if pos not in matchs_par_position:
                        matchs_par_position[pos] = {"gagnants": [], "perdants": []}
                    matchs_par_position[pos]["gagnants"].append(winner)
                    matchs_par_position[pos]["perdants"].append(loser)
                rang_depart = len(qualifies) + 1
                for pos in sorted(matchs_par_position.keys()):
                    gagnants = matchs_par_position[pos]["gagnants"]
                    perdants = matchs_par_position[pos]["perdants"]
                    for eq in gagnants:
                        stats_dyn[eq]["rang"] = rang_depart
                    rang_suivant = rang_depart + len(gagnants)
                    for eq in perdants:
                        stats_dyn[eq]["rang"] = rang_suivant
                    rang_depart = rang_suivant + len(perdants)
            elif not automatique:
                # 1. Récupérer tous les matchs de classement dans l'ordre
                matchs_classement = []
                for phase in self.phases:
                    for match in phase.get("matchs", []):
                        if match.get("type") == "classement":
                            matchs_classement.append(match)
                # 2. Grouper par 2 (MC1+MC2, MC3+MC4, etc.)
                groupes = [matchs_classement[i:i+2] for i in range(0, len(matchs_classement), 2)]
                rang_depart = rang_depart = len(qualifies) + len(non_qualifies) - 1
                for idx, groupe in enumerate(groupes):
                    gagnants = []
                    perdants = []
                    for match in groupe:
                        eq1 = match.get("A")
                        eq2 = match.get("B")
                        if not eq1 or not eq2:
                            continue
                        winner = self.compute_winner(match)
                        if not winner:
                            continue
                        loser = eq2 if winner == eq1 else eq1
                        gagnants.append(winner)
                        perdants.append(loser)
                    # 3. Attribution des rangs (même logique que AUTO)
                    # perdants → pires rangs
                    for eq in perdants:
                        stats_dyn[eq]["rang"] = rang_depart
                    # gagnants → juste au-dessus
                    for eq in gagnants:
                        stats_dyn[eq]["rang"] = rang_depart - len(perdants)
                    # 4. On remonte dans le classement
                    rang_depart -= (len(gagnants) + len(perdants))   
        # --------------------------------------------------
        # Non qualifiés sans match classement
        # --------------------------------------------------
        for eq in non_qualifies:
            if stats_dyn[eq].get("rang") is None:
                stats_dyn[eq]["rang"] = len(qualifies) + 1
        # --------------------------------------------------
        # Construction classement final
        # --------------------------------------------------
        classement = {}
        for eq, st in stats_dyn.items():
            rang = st.get("rang")
            if rang is None:
                continue
            classement.setdefault(rang, []).append(eq)
        classement_final = []
        for rang in sorted(classement.keys()):
            classement_final.append({
                "rang": rang,
                "equipes": sorted(classement[rang]),
                "stats": {eq: stats_dyn[eq] for eq in classement[rang]}
            })
        return classement_final

    def remplir_matchs_classement(self):
        """
        Remplit les matchs de classement pour les équipes non qualifiées.
        ⚠️ Ne touche PAS aux scores si le match a déjà été joué.
        """
        if not self.phases or not self.phases[0]["matchs"]:
            return
        premiere_phase = self.phases[0]
        matchs_classement = [
            m for m in premiere_phase["matchs"]
            if m.get("type") == "classement"
        ]
        # ⚠️ IMPORTANT : on ne reset PAS les scores !
        # On ne modifie que les équipes si match vide
        non_qualifies_groupes = self.get_non_qualifies(premiere_phase)
        groupes = list(non_qualifies_groupes.keys())
        if not groupes:
            return
        nb_positions = max(len(l) for l in non_qualifies_groupes.values())
        match_index = 0
        for pos in range(nb_positions):
            rang_equipes = []
            for g in groupes:
                if pos < len(non_qualifies_groupes[g]):
                    rang_equipes.append((g, non_qualifies_groupes[g][-(pos+1)]))
            used = set()
            paires_rang = []
            for i, (g1, e1) in enumerate(rang_equipes):
                if e1 in used:
                    continue
                for j, (g2, e2) in enumerate(rang_equipes):
                    if j <= i or e2 in used:
                        continue
                    if g2 != g1:
                        paires_rang.append((e1, e2))
                        used.update([e1, e2])
                        break
            for paire in paires_rang:
                if match_index >= len(matchs_classement):
                    break
                match = matchs_classement[match_index]
                # 🔥 NE PAS ECRASER UN MATCH DEJA JOUE
                if match.get("SA") is None and match.get("SB") is None:
                    match["A"] = paire[0]
                    match["B"] = paire[1]
                match_index += 1

    def get_non_qualifies(self, phase):
        """
        Retourne les équipes non qualifiées par groupe
        en se basant sur le classement ACTUEL.
        """
        qualifies = self.calculer_qualifies()  # ⚡ recalcul dynamique
        classement_groupes = self.classement_par_groupe()
        non_qualifies = {}
        for groupe, classement in classement_groupes.items():
            equipes_classees = [e for e, _ in classement]
            qualif = qualifies.get(groupe, [])
            non_qualifies[groupe] = [e for e in equipes_classees if e not in qualif]
        return non_qualifies
    
    def get_classement_matches(self):
        """
        Retourne la liste des matchs de classement (type 'classement') 
        dans la première phase (premier tour).
        """
        if not self.phases or not self.phases[0]["matchs"]:
            return []
        return [m for m in self.phases[0]["matchs"] if m.get("type") == "classement"]
