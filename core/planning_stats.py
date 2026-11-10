# -*- coding: utf-8 -*-
from collections import defaultdict

class PlanningStats:
    @staticmethod
    def build(days):
        stats = {
            "jours": 0,
            "tournois": 0,
            "benevoles": 0,
            "referents": 0,
            "postes": 0,
            "creneaux": 0,

            "tournois_stats": {},
            "postes_stats": {},
            "creneaux_stats": {},

            "referents_liste": [],
            "telephones_manquants": [],
            "notes_manquantes": [],
            "postes_sans_referent": [],

            "benevoles_uniques": 0,
        }
        benevoles_uniques = set()
        postes_uniques = set()
        creneaux_uniques = set()
        postes_stats = defaultdict(int)
        tournois_stats = defaultdict(int)
        creneaux_stats = defaultdict(int)
        referents_uniques = {}
        telephones_manquants = []
        notes_manquantes = []
        referents_par_poste = defaultdict(int)
        stats["jours"] = len(days)
        for _, tournaments in days.items():
            stats["tournois"] += len(tournaments)
            for tournament in tournaments:
                tournoi_nom = tournament.get( "nom", "Tournoi")
                for affectation in tournament.get( "postes",[]):
                    poste = (affectation.get("poste", "").strip())
                    creneau = (affectation.get("creneau", "").strip())
                    nom = (affectation.get("nom", "") .strip())
                    prenom = (affectation.get("prenom", "").strip())
                    telephone = (affectation.get("telephone", "").strip())
                    notes = (affectation.get("notes", "").strip())
                    referent = bool(affectation.get("referent", False))
                    nom_complet = (f"{prenom} {nom}").strip()
                    if not nom_complet:
                        continue
                    stats["benevoles"] += 1
                    benevoles_uniques.add((nom.lower(),prenom.lower()) )
                    if poste:
                        postes_uniques.add(poste)
                        postes_stats[poste] += 1
                    if creneau:
                        creneaux_uniques.add(creneau)
                        creneaux_stats[creneau] += 1
                    tournois_stats[tournoi_nom] += 1
                    if referent:
                        cle = (nom.lower().strip(),prenom.lower().strip())
                        if cle not in referents_uniques:
                            referents_uniques[cle] = {
                                "nom": nom,
                                "prenom": prenom,
                                "telephone": telephone,
                                "tournois": set(),
                                "postes": set()
                            }
                        if tournoi_nom:
                            referents_uniques[cle]["tournois"].add(tournoi_nom)
                        if poste:
                            referents_uniques[cle]["postes"].add(poste)
                            referents_par_poste[poste] += 1
                    if not telephone:
                        telephones_manquants.append({
                            "nom": nom,
                            "prenom": prenom,
                            "poste": poste,
                            "tournoi": tournoi_nom,
                        })
                    if not notes:
                        notes_manquantes.append({
                            "nom": nom,
                            "prenom": prenom,
                            "poste": poste,
                            "tournoi": tournoi_nom,
                        })
        stats["benevoles_uniques"] = len(benevoles_uniques)
        stats["postes"] = len(postes_uniques)
        stats["creneaux"] = len(creneaux_uniques)
        stats["tournois_stats"] = dict(sorted(tournois_stats.items(), key=lambda item: item[1], reverse=True))
        stats["postes_stats"] = dict(sorted( postes_stats.items(),key=lambda item: item[1],reverse=True))
        stats["creneaux_stats"] = dict(sorted( creneaux_stats.items(),key=lambda item: item[1],reverse=True))
        stats["referents_liste"] = sorted(
            [
                {
                    "nom": ref["nom"],
                    "prenom": ref["prenom"],
                    "telephone": ref["telephone"],
                    "postes": sorted(ref["postes"]),
                    "tournois": sorted(ref["tournois"]),
                }
                for ref in referents_uniques.values()
            ],
            key=lambda x: (
                x["nom"].lower(),
                x["prenom"].lower()
            )
        )
        stats["referents"] = len(stats["referents_liste"])
        stats["telephones_manquants"] = sorted(telephones_manquants, key=lambda x: (x["tournoi"], x["poste"], x["nom"],x["prenom"]))
        stats["notes_manquantes"] = sorted(notes_manquantes,key=lambda x: ( x["tournoi"], x["poste"],x["nom"],x["prenom"]))
        stats["postes_sans_referent"] = sorted([poste
                for poste in postes_uniques
                if referents_par_poste.get(poste, 0) == 0])
        return stats
