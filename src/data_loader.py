"""
Module de chargement des données Maghreb Steel depuis le fichier Excel.
Lit et structure toutes les données nécessaires au modèle d'optimisation.
"""

import pandas as pd
import numpy as np
from pathlib import Path

# Silence deprecation warning for future downcasting behavior in replace
pd.set_option('future.no_silent_downcasting', True)


def load_data(filepath: str = "data/Donnees_MaghrebSteel.xlsx") -> dict:
    """
    Charge toutes les données depuis le fichier Excel Maghreb Steel.

    Args:
        filepath: Chemin vers le fichier Excel des données.

    Returns:
        dict: Dictionnaire contenant toutes les données structurées.
    """
    fp = Path(filepath)
    if not fp.exists():
        # Try relative to script location
        fp = Path(__file__).parent.parent / filepath
    if not fp.exists():
        raise FileNotFoundError(f"Fichier introuvable : {filepath}")

    data = {}

    # ── 1. Commandes ──────────────────────────────────────────────────────────
    df_cmd = pd.read_excel(fp, sheet_name="Commandes", header=2)
    df_cmd.columns = [
        "ID", "Client", "Famille", "Grade", "Epaisseur",
        "Largeur", "Tonnage", "Prix_vente", "Semaine_livraison", "Priorite"
    ]
    df_cmd = df_cmd.dropna(subset=["ID"])
    # Exclure Quarto (hors périmètre flux froid)
    df_cmd = df_cmd[df_cmd["Famille"] != "Quarto"].reset_index(drop=True)
    data["commandes"] = df_cmd

    # ── 2. Cadences (T/jour) par ligne × famille ──────────────────────────────
    df_cad = pd.read_excel(fp, sheet_name="Cadences", header=2)
    df_cad = df_cad.iloc[:8, :6].copy()  # 8 lignes, 6 colonnes utiles
    df_cad.columns = ["Ligne", "HRC_DEC", "CRC", "HDG", "PPGI", "BACR"]
    df_cad = df_cad.dropna(subset=["Ligne"])
    df_cad = df_cad.set_index("Ligne")
    # Remplacer "—" et variantes par 0 using encoding-safe unicode escapes
    df_cad = df_cad.replace({"\u2014": 0, "\u2013": 0, "\u2212": 0})
    df_cad = df_cad.infer_objects(copy=False)
    df_cad = df_cad.apply(pd.to_numeric, errors="coerce").fillna(0)
    data["cadences"] = df_cad

    # ── 3. Rendements par process ──────────────────────────────────────────────
    df_rend = pd.read_excel(fp, sheet_name="Rendements", header=2)
    df_rend = df_rend.iloc[:7, :2].copy()
    df_rend.columns = ["Process", "Rendement"]
    df_rend = df_rend.dropna(subset=["Process"])
    df_rend = df_rend.set_index("Process")["Rendement"].to_dict()
    data["rendements"] = df_rend

    # ── 4. Coûts variables (MAD/T) par process × épaisseur ────────────────────
    df_cout = pd.read_excel(fp, sheet_name="Couts_Variables", header=2)
    df_cout = df_cout.iloc[:10, :8].copy()
    df_cout.columns = ["Process", "lt03", "t03_04", "t04_05", "t05_07", "t07_10", "t10_15", "gt15"]
    df_cout = df_cout.dropna(subset=["Process"])
    df_cout = df_cout.set_index("Process")
    data["couts_variables"] = df_cout

    # ── 5. Prix HRC (MAD/T) par grade × largeur ───────────────────────────────
    df_hrc = pd.read_excel(fp, sheet_name="Prix_HRC", header=2)
    df_hrc = df_hrc.iloc[:5, :8].copy()
    df_hrc.columns = ["Grade", 1020, 1090, 1100, 1140, 1250, 1280, 1320]
    df_hrc = df_hrc.dropna(subset=["Grade"])
    df_hrc = df_hrc.set_index("Grade")

    # Disponibilité HRC par grade
    df_hrc_dispo = pd.read_excel(fp, sheet_name="Prix_HRC", header=None)
    # Find dispo section
    dispo = {}
    grades = ["DC01", "DD13", "DX51", "DX52", "S320"]
    for _, row in df_hrc_dispo.iterrows():
        if str(row.iloc[0]) in grades:
            try:
                dispo[str(row.iloc[0])] = float(row.iloc[1])
            except (ValueError, TypeError):
                pass

    data["prix_hrc"] = df_hrc
    data["dispo_hrc"] = dispo

    # ── 6. Stocks initiaux ────────────────────────────────────────────────────
    df_stock = pd.read_excel(fp, sheet_name="Stocks_Initiaux", header=None)
    stocks_pk = {}
    stocks_fp = {}
    stocks_ip = {}

    current_section = None
    for _, row in df_stock.iterrows():
        cell = str(row.iloc[0]) if pd.notna(row.iloc[0]) else ""
        if "Stocks PK" in cell:
            current_section = "pk"
        elif "Stocks interprocess" in cell or "interprocess" in cell.lower():
            current_section = "ip"
        elif "Stocks produits finis" in cell or "produits finis" in cell.lower():
            current_section = "fp"
        elif current_section and pd.notna(row.iloc[0]) and row.iloc[0] not in ["Grade", "Point de stockage", "Famille", "Stock initial (T)"]:
            try:
                key = str(row.iloc[0]).strip()
                val = float(row.iloc[1]) if pd.notna(row.iloc[1]) else 0.0
                min_v = float(row.iloc[2]) if pd.notna(row.iloc[2]) else 0.0
                max_v = float(row.iloc[3]) if pd.notna(row.iloc[3]) else 99999.0
                if key and key not in ["nan", "None"] and not key.startswith("Stock"):
                    entry = {"initial": val, "min": min_v, "max": max_v}
                    if current_section == "pk":
                        stocks_pk[key] = entry
                    elif current_section == "ip":
                        stocks_ip[key] = entry
                    elif current_section == "fp":
                        stocks_fp[key] = entry
            except (ValueError, TypeError):
                pass

    data["stocks_pk"] = stocks_pk
    data["stocks_ip"] = stocks_ip
    data["stocks_fp"] = stocks_fp

    # ── 7. Arrêts planifiés (jours/semaine) ───────────────────────────────────
    df_arrets = pd.read_excel(fp, sheet_name="Arrets_Planifies", header=2)
    df_arrets = df_arrets.iloc[:8, :5].copy()
    df_arrets.columns = ["Ligne", "S1", "S2", "S3", "S4"]
    df_arrets = df_arrets.dropna(subset=["Ligne"])
    df_arrets = df_arrets.set_index("Ligne")
    df_arrets = df_arrets.apply(pd.to_numeric, errors="coerce").fillna(0)
    data["arrets"] = df_arrets

    # ── 8. Paramètres globaux ─────────────────────────────────────────────────
    df_param = pd.read_excel(fp, sheet_name="Parametres", header=2)
    df_param = df_param.iloc[:15, :2].copy()
    df_param.columns = ["Parametre", "Valeur"]
    df_param = df_param.dropna(subset=["Parametre"])
    params = dict(zip(df_param["Parametre"], df_param["Valeur"]))
    data["params"] = params

    return data


def get_cout_transformation(epaisseur: float, process: str, couts_df: pd.DataFrame) -> float:
    """
    Retourne le coût de transformation (MAD/T) selon l'épaisseur et le process.

    Args:
        epaisseur: Épaisseur en mm.
        process: Nom du process (PK, CRMA, CRMB, etc.).
        couts_df: DataFrame des coûts variables.

    Returns:
        float: Coût de transformation en MAD/T.
    """
    if process not in couts_df.index:
        return 0.0
    row = couts_df.loc[process]
    if epaisseur < 0.3:
        return float(row["lt03"])
    elif epaisseur <= 0.4:
        return float(row["t03_04"])
    elif epaisseur <= 0.5:
        return float(row["t04_05"])
    elif epaisseur <= 0.7:
        return float(row["t05_07"])
    elif epaisseur <= 1.0:
        return float(row["t07_10"])
    elif epaisseur <= 1.5:
        return float(row["t10_15"])
    else:
        return float(row["gt15"])


def get_prix_hrc(grade: str, largeur: float, prix_hrc_df: pd.DataFrame) -> float:
    """
    Retourne le prix HRC (MAD/T) selon le grade et la largeur.

    Args:
        grade: Grade de l'acier (DC01, DD13, DX51, DX52, S320).
        largeur: Largeur en mm.
        prix_hrc_df: DataFrame des prix HRC.

    Returns:
        float: Prix HRC en MAD/T.
    """
    if grade not in prix_hrc_df.index:
        # Default to nearest available grade
        grade = prix_hrc_df.index[0]

    largeurs_disponibles = [int(c) for c in prix_hrc_df.columns if str(c).isdigit()]
    largeur_int = int(largeur)

    # Trouver la largeur la plus proche
    nearest = min(largeurs_disponibles, key=lambda x: abs(x - largeur_int))
    return float(prix_hrc_df.loc[grade, nearest])


def get_capacite_nette(ligne: str, semaine: int, famille: str,
                       cadences: pd.DataFrame, arrets: pd.DataFrame,
                       jours_semaine: int = 7) -> float:
    """
    Calcule la capacité nette hebdomadaire d'une ligne pour une famille.

    Formule: Cadence[ligne, famille] × (jours_semaine - Arrêts[ligne, semaine])

    Args:
        ligne: Nom de la ligne de production.
        semaine: Numéro de semaine (1-4).
        famille: Famille de produits.
        cadences: DataFrame des cadences journalières.
        arrets: DataFrame des arrêts planifiés.
        jours_semaine: Nombre de jours ouvrés par semaine (défaut=7).

    Returns:
        float: Capacité nette en tonnes.
    """
    col_sem = f"S{semaine}"
    if ligne not in cadences.index or famille not in cadences.columns:
        return 0.0
    cadence = float(cadences.loc[ligne, famille])
    arret = float(arrets.loc[ligne, col_sem]) if ligne in arrets.index else 0.0
    return cadence * (jours_semaine - arret)


if __name__ == "__main__":
    data = load_data("data/Donnees_MaghrebSteel.xlsx")
    print("✅ Données chargées avec succès!")
    print(f"   → {len(data['commandes'])} commandes")
    print(f"   → {len(data['cadences'])} lignes de production")
    print(f"   → Grades HRC: {list(data['dispo_hrc'].keys())}")
    print(f"   → Paramètres: {list(data['params'].keys())[:5]} ...")
