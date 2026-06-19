"""
Module d'analyses de sensibilité et scénarios avancés (B8 et B9).
"""
import pandas as pd
from model import build_and_solve

def analyse_enveloppe_dc01(data_path: str = "data/Donnees_MaghrebSteel.xlsx") -> pd.DataFrame:
    """
    Analyse B8 : Courbe d'enveloppe pour la disponibilité HRC DC01.
    Fait varier la disponibilité de DC01 de -50% à +50% (multiplicateur de 0.5 à 1.5).
    """
    # Disponibilité nominale DC01 = 7550 T
    DISPO_NOMINALE = 7550.0
    multipliers = [0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 1.1, 1.2, 1.3, 1.4, 1.5]
    results = []

    print("Calcul de la courbe d'enveloppe DC01 (B8)...")
    for mult in multipliers:
        res = build_and_solve(data_path, dc01_multiplier=mult)
        dispo = DISPO_NOMINALE * mult
        results.append({
            "multiplicateur": mult,
            "variation_pct": round((mult - 1.0) * 100, 0),
            "dispo_tonnes": dispo,
            "marge_totale": res["marge_totale"],
            "taux_service": res["taux_service"],
            "status": res["status"]
        })
    
    return pd.DataFrame(results)


def analyse_robustesse_cadences(data_path: str = "data/Donnees_MaghrebSteel.xlsx") -> pd.DataFrame:
    """
    Analyse B9 : Analyse de robustesse par rapport aux cadences.
    Fait varier toutes les cadences de -5% à +5% (multiplicateur de 0.95 à 1.05).
    """
    multipliers = [0.95, 0.96, 0.97, 0.98, 0.99, 1.0, 1.01, 1.02, 1.03, 1.04, 1.05]
    results = []

    print("Calcul de l'analyse de robustesse des cadences (B9)...")
    for mult in multipliers:
        res = build_and_solve(data_path, cadence_multiplier=mult)
        results.append({
            "multiplicateur": mult,
            "variation_pct": round((mult - 1.0) * 100, 0),
            "marge_totale": res["marge_totale"],
            "taux_service": res["taux_service"],
            "status": res["status"]
        })
        
    return pd.DataFrame(results)
