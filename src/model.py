"""
Modèle d'optimisation PL — Simulateur Capacité-Commande Maghreb Steel.

Objectif : Maximiser la marge sur coût variable sur un horizon de 4 semaines.
Familles : CRC, HDG, PPGI, BACR (+ HRC DEC marginal).
Variables de décision continues (LP relaxation).
"""

import pandas as pd
import numpy as np
from pathlib import Path
import sys

from pulp import (
    LpProblem, LpMaximize, LpVariable, lpSum, LpStatus, value, PULP_CBC_CMD
)

sys.path.insert(0, str(Path(__file__).parent))
from data_loader import load_data, get_cout_transformation, get_prix_hrc, get_capacite_nette

# ─────────────────────────────────────────────────────────────────────────────
# CHEMINS DE PRODUCTION PAR FAMILLE
# ─────────────────────────────────────────────────────────────────────────────
CHEMINS = {
    "CRC":    [("PK","PK"), ("CRMB","CRMB"), ("BAF","BAF"), ("SKP","SKP")],
    "HDG_A":  [("PK","PK"), ("CRMA","CRMA"), ("LGA","LGA")],
    "HDG_B":  [("PK","PK"), ("CRMB","CRMB"), ("LGA","LGA")],
    "HDG_C":  [("PK","PK"), ("CRMB","CRMB"), ("LGB","LGB")],
    "PPGI_A": [("PK","PK"), ("CRMA","CRMA"), ("LGA","LGA")],
    "PPGI_B": [("PK","PK"), ("CRMB","CRMB"), ("LGA","LGA")],
    "BACR_A": [("PK","PK"), ("CRMB","CRMB"), ("BAF","BAF"), ("LGB","LGB")],
    "BACR_B": [("PK","PK"), ("CRMA","CRMA"), ("LGA","LGA")],
    "BACR_C": [("PK","PK"), ("CRMB","CRMB"), ("LGA","LGA")],
    "HRC_DEC":[("PK","PK")],
}

FAMILLE_CHEMINS = {
    "CRC":     ["CRC"],
    "HDG":     ["HDG_A", "HDG_B", "HDG_C"],
    "PPGI":    ["PPGI_A", "PPGI_B"],
    "BACR":    ["BACR_A", "BACR_B", "BACR_C"],
    "HRC DEC": ["HRC_DEC"],
}

LIGNES_PHYSIQUES = ["PK", "CRMA", "CRMB", "BAF", "SKP", "LGA", "LGB"]

# Famille utilisée dans le tableau cadences pour chaque chemin × ligne
CHEMIN_LIGNE_FAMILLE_CAD = {
    ("CRC",    "PK"):   "CRC",
    ("CRC",    "CRMB"): "CRC",
    ("CRC",    "BAF"):  "CRC",
    ("CRC",    "SKP"):  "CRC",
    ("HDG_A",  "PK"):   "HDG",
    ("HDG_A",  "CRMA"): "HDG",
    ("HDG_A",  "LGA"):  "HDG",
    ("HDG_B",  "PK"):   "HDG",
    ("HDG_B",  "CRMB"): "HDG",
    ("HDG_B",  "LGA"):  "HDG",
    ("HDG_C",  "PK"):   "HDG",
    ("HDG_C",  "CRMB"): "HDG",
    ("HDG_C",  "LGB"):  "HDG",
    ("PPGI_A", "PK"):   "PPGI",
    ("PPGI_A", "CRMA"): "PPGI",
    ("PPGI_A", "LGA"):  "PPGI",
    ("PPGI_B", "PK"):   "PPGI",
    ("PPGI_B", "CRMB"): "PPGI",
    ("PPGI_B", "LGA"):  "PPGI",
    ("BACR_A", "PK"):   "BACR",
    ("BACR_A", "CRMB"): "BACR",
    ("BACR_A", "BAF"):  "BACR",
    ("BACR_A", "LGB"):  "BACR",
    ("BACR_B", "PK"):   "BACR",
    ("BACR_B", "CRMA"): "BACR",
    ("BACR_B", "LGA"):  "BACR",
    ("BACR_C", "PK"):   "BACR",
    ("BACR_C", "CRMB"): "BACR",
    ("BACR_C", "LGA"):  "BACR",
    ("HRC_DEC","PK"):   "HRC_DEC",
}


def _get_cadence_for_chemin_ligne(ck, ligne, cadences):
    """Retourne la cadence journalière (T/j) pour un chemin × ligne."""
    fam_cad = CHEMIN_LIGNE_FAMILLE_CAD.get((ck, ligne), None)
    if fam_cad is None or ligne not in cadences.index:
        return 0.0
    if fam_cad not in cadences.columns:
        return 0.0
    v = cadences.loc[ligne, fam_cad]
    try:
        return float(v)
    except (ValueError, TypeError):
        return 0.0


def build_and_solve(
    data_path: str = "data/Donnees_MaghrebSteel.xlsx",
    hrc_multiplier: float = 1.0,
    extra_arrets: dict = None,
    extra_commandes: list = None,
) -> dict:
    """
    Construit et résout le modèle LP Maghreb Steel.

    Args:
        data_path: Fichier Excel de données.
        hrc_multiplier: Multiplicateur sur les prix HRC (scénario E20).
        extra_arrets: Arrêts supplémentaires {ligne: {semaine: jours}} (scénario E21).
        extra_commandes: Commandes supplémentaires à ajouter (scénario E22).

    Returns:
        dict: Résultats complets.
    """
    # ── Chargement ──────────────────────────────────────────────────────────
    data = load_data(data_path)
    commandes   = data["commandes"].copy()
    cadences    = data["cadences"]
    rendements  = data["rendements"]
    couts_df    = data["couts_variables"]
    prix_hrc_df = data["prix_hrc"].copy()
    dispo_hrc   = dict(data["dispo_hrc"])
    arrets      = data["arrets"].copy()
    params      = data["params"]
    stocks_fp   = data["stocks_fp"]
    stocks_pk   = data["stocks_pk"]

    SEMAINES      = [1, 2, 3, 4]
    JOURS_SEM     = int(params.get("Jours ouvrés / semaine", 7))
    PRIX_CHUTE    = float(params.get("Prix de valorisation des chutes", 1800))
    PRIX_ZINC     = float(params.get("Prix zinc", 18000))
    CONSO_ZINC    = float(params.get("Consommation zinc HDG", 0.025))
    CONSO_ZINC_P  = float(params.get("Consommation zinc PPGI", 0.025))
    PRIX_PEINTURE = float(params.get("Prix peinture (PPGI)", 12000))
    CONSO_PEINTURE= float(params.get("Consommation peinture PPGI", 0.01))

    # Appliquer scénario HRC cher
    if hrc_multiplier != 1.0:
        prix_hrc_df = prix_hrc_df * hrc_multiplier

    # Appliquer arrêts supplémentaires
    if extra_arrets:
        for ligne, sems in extra_arrets.items():
            for sem, jours in sems.items():
                col = f"S{sem}"
                if ligne in arrets.index and col in arrets.columns:
                    arrets.loc[ligne, col] += jours

    # Ajouter commandes supplémentaires
    if extra_commandes:
        for ec in extra_commandes:
            new_row = pd.DataFrame([ec])
            commandes = pd.concat([commandes, new_row], ignore_index=True)

    # Filtrer familles valides
    commandes = commandes[
        commandes["Famille"].isin(["CRC", "HDG", "PPGI", "BACR", "HRC DEC"])
    ].copy().reset_index(drop=True)

    # ── Pré-calcul par commande × chemin ────────────────────────────────────
    cmd_data = []
    for idx, row in commandes.iterrows():
        famille   = str(row["Famille"])
        grade     = str(row["Grade"])
        epaisseur = float(row["Epaisseur"])
        largeur   = float(row["Largeur"])
        tonnage   = float(row["Tonnage"])
        prix_v    = float(row["Prix_vente"])
        semaine   = min(int(row["Semaine_livraison"]), 4)
        priorite  = str(row["Priorite"])
        cmd_id    = str(row["ID"])

        chemins_fam = FAMILLE_CHEMINS.get(famille, [])
        p_hrc = get_prix_hrc(grade, largeur, prix_hrc_df)

        # Extras zinc/peinture (MAD/T fini)
        cout_extras = 0.0
        if famille == "HDG":
            cout_extras = PRIX_ZINC * CONSO_ZINC
        elif famille == "PPGI":
            cout_extras = PRIX_ZINC * CONSO_ZINC_P + PRIX_PEINTURE * CONSO_PEINTURE

        chemins_info = {}
        for ck in chemins_fam:
            # Check if this path uses LGA or LGB
            uses_lga = any(ligne == "LGA" for proc, ligne in CHEMINS[ck])
            uses_lgb = any(ligne == "LGB" for proc, ligne in CHEMINS[ck])

            # Apply thickness limits
            if uses_lga and epaisseur > 0.6:
                continue
            if uses_lgb and epaisseur <= 0.6:
                continue

            rend_cum = 1.0
            cout_transfo = 0.0
            for proc, ligne in CHEMINS[ck]:
                rend_proc = rendements.get(proc, 1.0)
                c = get_cout_transformation(epaisseur, proc, couts_df)
                # Coût par tonne de produit fini = c / rendement_cumulé_avant_ce_step
                cout_transfo += c / rend_cum if rend_cum > 0 else c
                rend_cum *= rend_proc
            r_global = rend_cum
            hrc_par_t = 1.0 / r_global if r_global > 0 else 999.0
            # Valorisation chutes : (HRC_entrant - sortie_conforme) × prix_chute
            # Approximation: chutes ≈ (1/r - 1) × tonnage_fini × 0.5 (fraction ferraille)
            val_chute = (hrc_par_t - 1.0) * PRIX_CHUTE * 0.5
            marge_tonne = prix_v - p_hrc * hrc_par_t - cout_transfo + val_chute - cout_extras
            chemins_info[ck] = {
                "r_global":        r_global,
                "hrc_par_t":       hrc_par_t,
                "cout_transfo":    cout_transfo,
                "marge_tonne":     marge_tonne,
                "p_hrc":           p_hrc,
            }

        cmd_data.append({
            "i":        idx,
            "id":       cmd_id,
            "famille":  famille,
            "grade":    grade,
            "epaisseur":epaisseur,
            "largeur":  largeur,
            "tonnage":  tonnage,
            "prix_v":   prix_v,
            "semaine":  semaine,
            "priorite": priorite,
            "chemins":  chemins_info,
        })

    # ── Modèle PL ────────────────────────────────────────────────────────────
    prob = LpProblem("MaghrebSteel_CapComm", LpMaximize)

    # Variables x[i][ck] : tonnage livré de la commande i via chemin ck
    x = {}
    for cd in cmd_data:
        i = cd["i"]
        x[i] = {}
        for ck in cd["chemins"]:
            x[i][ck] = LpVariable(f"x_{i}_{ck}", lowBound=0, upBound=cd["tonnage"])

    # Fonction objectif
    obj = []
    for cd in cmd_data:
        i = cd["i"]
        for ck, ci in cd["chemins"].items():
            obj.append(ci["marge_tonne"] * x[i][ck])
    prob += lpSum(obj), "Marge_totale"

    # C1 : Tonnage livré ≤ tonnage demandé
    for cd in cmd_data:
        i = cd["i"]
        if cd["chemins"]:
            prob += (
                lpSum(x[i][ck] for ck in cd["chemins"]) <= cd["tonnage"],
                f"dem_{cd['id'].replace('-','_')}"
            )

    # C2 : Capacité nette par ligne × semaine
    # Chargement de chaque ligne physique par semaine
    cap_load = {l: {s: [] for s in SEMAINES} for l in LIGNES_PHYSIQUES}

    for cd in cmd_data:
        i   = cd["i"]
        sem = cd["semaine"]
        for ck, ci in cd["chemins"].items():
            rend_cum = 1.0
            for proc, ligne in CHEMINS[ck]:
                # Tonnage traversant cette ligne = x * (1/rend_cum_amont)
                coeff = 1.0 / rend_cum if rend_cum > 0 else 1.0
                if ligne in cap_load:
                    famille_finale = cd["famille"]
                    cadence = float(cadences.loc[ligne, famille_finale]) if ligne in cadences.index and famille_finale in cadences.columns else 0.0
                    cap_load[ligne][sem].append((coeff, x[i][ck], ck, ligne, cadence))
                rend_cum *= rendements.get(proc, 1.0)

    for ligne in LIGNES_PHYSIQUES:
        for sem in SEMAINES:
            # Disponibilité nette en jours:
            col_sem = f"S{sem}"
            arret = float(arrets.loc[ligne, col_sem]) if ligne in arrets.index and col_sem in arrets.columns else 0.0
            dispo_jours = JOURS_SEM - arret

            terms = cap_load[ligne][sem]
            if not terms:
                continue

            if dispo_jours <= 0:
                # La ligne est arrêtée toute la semaine
                lp_terms = [var for _, var, _, _, _ in terms]
                if lp_terms:
                    prob += (lpSum(lp_terms) == 0, f"cap_{ligne}_S{sem}_zero")
                continue

            # lp_terms: temps consommé par chaque var = (tonnage traversant) / cadence
            lp_terms = []
            for coeff, var, ck, _, cadence in terms:
                if cadence > 0:
                    lp_terms.append((coeff / cadence) * var)
                else:
                    # Si la cadence est 0, le produit ne peut pas passer
                    prob += (var == 0, f"no_cadence_{ligne}_S{sem}_{ck}_{var.name}")

            if lp_terms:
                prob += (lpSum(lp_terms) <= dispo_jours, f"cap_time_{ligne}_S{sem}")

    # C3 : Disponibilité HRC par grade
    for grade in list(dispo_hrc.keys()):
        hrc_terms = []
        for cd in cmd_data:
            if cd["grade"] != grade:
                continue
            i = cd["i"]
            for ck, ci in cd["chemins"].items():
                hrc_terms.append(ci["hrc_par_t"] * x[i][ck])
        if hrc_terms:
            stock_pk = stocks_pk.get(grade, {}).get("initial", 0)
            dispo_totale = dispo_hrc.get(grade, 0) + stock_pk
            prob += (lpSum(hrc_terms) <= dispo_totale, f"hrc_{grade}")

    # C4 : Stock minimum produits finis
    for fam, si in stocks_fp.items():
        fam_key = fam.strip()
        if fam_key not in ["CRC", "HDG", "PPGI", "BACR", "HRC DEC"]:
            continue
        stock_init = si.get("initial", 0)
        stock_min  = si.get("min", 0)
        besoin     = max(0.0, stock_min - stock_init)
        if besoin <= 0:
            continue
        prod_terms = []
        for cd in cmd_data:
            if cd["famille"] == fam_key:
                i = cd["i"]
                prod_terms.extend(x[i][ck] for ck in cd["chemins"])
        if prod_terms:
            prob += (lpSum(prod_terms) >= besoin, f"stock_min_{fam_key.replace(' ','_')}")

    # ── Résolution ────────────────────────────────────────────────────────────
    import sys, io
    if hasattr(sys.stdout, 'reconfigure'):
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except Exception:
            pass
    print("[LP] Resolution en cours (CBC)...")
    solver = PULP_CBC_CMD(msg=0, timeLimit=300)
    prob.solve(solver)
    status = LpStatus[prob.status]
    print("[LP] Statut : {}".format(status))

    # ── Extraction des résultats ──────────────────────────────────────────────
    marge_totale = value(prob.objective) or 0.0
    tonnage_demande_total = sum(cd["tonnage"] for cd in cmd_data)
    tonnage_livre_total   = 0.0
    commandes_res = []
    commandes_refusees = []

    for cd in cmd_data:
        i = cd["i"]
        vol_livre = sum(value(x[i][ck]) or 0.0 for ck in cd["chemins"])
        tonnage_livre_total += vol_livre
        taux = vol_livre / cd["tonnage"] if cd["tonnage"] > 0 else 0
        chemin_choisi = next(
            (ck for ck in cd["chemins"] if (value(x[i][ck]) or 0) > 0.1), None
        )
        marge_unit = cd["chemins"].get(chemin_choisi, {}).get("marge_tonne", 0.0) if chemin_choisi else 0.0
        r = {
            "id":               cd["id"],
            "famille":          cd["famille"],
            "grade":            cd["grade"],
            "epaisseur":        cd["epaisseur"],
            "largeur":          cd["largeur"],
            "tonnage_demande":  cd["tonnage"],
            "tonnage_livre":    round(vol_livre, 2),
            "taux_service":     round(taux * 100, 1),
            "semaine":          cd["semaine"],
            "priorite":         cd["priorite"],
            "prix_vente":       cd["prix_v"],
            "chemin_choisi":    chemin_choisi,
            "marge_unitaire":   round(marge_unit, 2),
            "marge_totale_cmd": round(marge_unit * vol_livre, 0),
        }
        commandes_res.append(r)
        if taux < 0.05:
            commandes_refusees.append(r)

    taux_service_global = (tonnage_livre_total / tonnage_demande_total * 100
                           if tonnage_demande_total > 0 else 0)

    # Plan de marche
    plan = {l: {s: {f: 0.0 for f in ["CRC","HDG","PPGI","BACR","HRC DEC"]}
                for s in SEMAINES}
            for l in LIGNES_PHYSIQUES}
    for cd in cmd_data:
        i   = cd["i"]
        sem = cd["semaine"]
        fam = cd["famille"]
        for ck in cd["chemins"]:
            vol = value(x[i][ck]) or 0.0
            if vol < 0.01:
                continue
            rend_cum = 1.0
            for proc, ligne in CHEMINS[ck]:
                tonnage_step = vol / rend_cum if rend_cum > 0 else vol
                if ligne in plan:
                    plan[ligne][sem][fam] = plan[ligne][sem].get(fam, 0.0) + tonnage_step
                rend_cum *= rendements.get(proc, 1.0)

    # Utilisation lignes
    util_lignes = {}
    for ligne in LIGNES_PHYSIQUES:
        util_lignes[ligne] = {}
        for sem in SEMAINES:
            col_sem = f"S{sem}"
            arret = float(arrets.loc[ligne, col_sem]) if ligne in arrets.index and col_sem in arrets.columns else 0.0
            dispo_jours = JOURS_SEM - arret
            
            if dispo_jours <= 0:
                util_lignes[ligne][sem] = 0.0
                continue
                
            charge_jours = 0.0
            for coeff, var, _, _, cadence in cap_load[ligne][sem]:
                if cadence > 0:
                    charge_jours += (coeff * (value(var) or 0.0)) / cadence
                    
            util_lignes[ligne][sem] = round(
                min(charge_jours / dispo_jours * 100, 100), 1
            )

    # Shadow prices
    shadow_prices = {}
    for name, cst in prob.constraints.items():
        sp = cst.pi
        if sp is not None and abs(sp) > 0.001:
            shadow_prices[name] = round(sp, 2)

    # Marge par famille
    marge_par_famille = {}
    tonnage_par_famille = {}
    for r in commandes_res:
        fam = r["famille"]
        marge_par_famille[fam] = marge_par_famille.get(fam, 0) + r["marge_totale_cmd"]
        tonnage_par_famille[fam] = tonnage_par_famille.get(fam, 0) + r["tonnage_livre"]

    return {
        "status":                 status,
        "marge_totale":           marge_totale,
        "taux_service":           taux_service_global,
        "tonnage_livre_total":    tonnage_livre_total,
        "tonnage_demande_total":  tonnage_demande_total,
        "commandes":              commandes_res,
        "commandes_refusees":     commandes_refusees,
        "plan_marche":            plan,
        "utilisation_lignes":     util_lignes,
        "shadow_prices":          shadow_prices,
        "marge_par_famille":      marge_par_famille,
        "tonnage_par_famille":    tonnage_par_famille,
        "data":                   data,
        "cmd_data":               cmd_data,
        "prob":                   prob,
        "cap_load":               cap_load,
    }


def export_results(resultats: dict, output_dir: str = "outputs") -> None:
    """Exporte les résultats en CSV et Excel."""
    out = Path(output_dir)
    out.mkdir(exist_ok=True)

    # Commandes
    df_cmd = pd.DataFrame(resultats["commandes"])
    df_cmd.to_csv(out / "commandes_resultats.csv", index=False, encoding="utf-8-sig")

    # Plan de marche
    rows = []
    for ligne, sems in resultats["plan_marche"].items():
        for sem, fams in sems.items():
            for fam, tonnage in fams.items():
                if tonnage > 0.1:
                    rows.append({"Ligne": ligne, "Semaine": sem,
                                 "Famille": fam, "Tonnage_T": round(tonnage, 2)})
    df_plan = pd.DataFrame(rows)
    df_plan.to_csv(out / "plan_marche.csv", index=False, encoding="utf-8-sig")

    # Utilisation lignes
    rows_util = []
    for ligne, sems in resultats["utilisation_lignes"].items():
        for sem, util in sems.items():
            rows_util.append({"Ligne": ligne, "Semaine": sem, "Utilisation_%": util})
    pd.DataFrame(rows_util).to_csv(out / "utilisation_lignes.csv", index=False, encoding="utf-8-sig")

    # Shadow prices
    df_sp = pd.DataFrame([
        {"Contrainte": k, "Shadow_Price_MAD": v}
        for k, v in sorted(resultats["shadow_prices"].items(),
                            key=lambda kv: abs(kv[1]), reverse=True)
    ])
    df_sp.to_csv(out / "shadow_prices.csv", index=False, encoding="utf-8-sig")

    # Excel consolidé
    with pd.ExcelWriter(out / "resultats_complets.xlsx", engine="openpyxl") as writer:
        df_cmd.to_excel(writer, sheet_name="Commandes", index=False)
        df_plan.to_excel(writer, sheet_name="Plan_Marche", index=False)
        pd.DataFrame(rows_util).to_excel(writer, sheet_name="Utilisation_Lignes", index=False)
        df_sp.to_excel(writer, sheet_name="Shadow_Prices", index=False)

    print("[OK] Resultats exportes dans : {}".format(out.resolve()))


if __name__ == "__main__":
    r = build_and_solve("../data/Donnees_MaghrebSteel.xlsx")
    print(f"\nStatut       : {r['status']}")
    print(f"Marge totale : {r['marge_totale']:,.0f} MAD")
    print(f"Taux service : {r['taux_service']:.1f}%")
    print(f"Cdes refusées: {len(r['commandes_refusees'])}")
    export_results(r, "../outputs")
