"""
Script principal — Simulateur Capacité-Commande Maghreb Steel.

Usage:
    python main.py
    python main.py --data data/Donnees_MaghrebSteel.xlsx
    python main.py --scenario panne_lgb

Scénarios disponibles :
    base          : Cas de base
    hrc_cher      : Prix HRC +10% (E20)
    panne_lgb     : LGB en panne 2j supplémentaires semaine 2 (E21)
    commande_urgente : Nouvelle commande HDG 300T semaine 1 (E22)
"""

import sys
import io
import argparse
from pathlib import Path

# Force UTF-8 encoding for Windows terminals
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
if hasattr(sys.stderr, 'reconfigure'):
    try:
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.model import build_and_solve, export_results
from src.data_loader import load_data


def print_banner():
    print("""
+--------------------------------------------------------------+
|       SIMULATEUR CAPACITE-COMMANDE -- MAGHREB STEEL          |
|       Projet RO -- EMINES UM6P -- Promotion 2026             |
+--------------------------------------------------------------+
""")


def print_results_summary(resultats: dict, scenario: str = "base"):
    print(f"\n{'═'*62}")
    print(f"  SCÉNARIO : {scenario.upper()}")
    print(f"{'═'*62}")
    print(f"  Statut          : {resultats['status']}")
    print(f"  Marge totale    : {resultats['marge_totale']:>15,.0f} MAD")
    print(f"  Taux de service : {resultats['taux_service']:>14.1f} %")
    print(f"  Tonnage demandé : {resultats['tonnage_demande_total']:>12,.0f} T")
    print(f"  Tonnage livré   : {resultats['tonnage_livre_total']:>12,.0f} T")
    print(f"  Commandes refusées : {len(resultats['commandes_refusees'])}")

    print(f"\n  {'─'*58}")
    print(f"  UTILISATION DES LIGNES (par semaine, %) :")
    print(f"  {'Ligne':<8} {'S1':>6} {'S2':>6} {'S3':>6} {'S4':>6}")
    print(f"  {'─'*36}")
    for ligne, sems in resultats["utilisation_lignes"].items():
        vals = [sems.get(s, 0) for s in [1, 2, 3, 4]]
        flag = "🔴" if any(v >= 95 for v in vals) else ("🟡" if any(v >= 80 for v in vals) else "🟢")
        print(f"  {ligne:<8} {vals[0]:>5.1f}% {vals[1]:>5.1f}% {vals[2]:>5.1f}% {vals[3]:>5.1f}% {flag}")

    print(f"\n  {'─'*58}")
    print(f"  TOP 5 SHADOW PRICES (contraintes les plus critiques) :")
    sp_sorted = sorted(resultats["shadow_prices"].items(),
                       key=lambda kv: abs(kv[1]), reverse=True)[:5]
    for name, sp in sp_sorted:
        print(f"  {name:<35} : {sp:>10.2f} MAD")

    if resultats["commandes_refusees"]:
        print(f"\n  {'─'*58}")
        print(f"  COMMANDES REFUSÉES ({len(resultats['commandes_refusees'])}) :")
        for cmd in resultats["commandes_refusees"][:10]:
            print(f"  {cmd['id']} | {cmd['famille']:<8} | {cmd['grade']:<5} | "
                  f"{cmd['tonnage_demande']:>6.0f}T | Prio: {cmd['priorite']}")
        if len(resultats["commandes_refusees"]) > 10:
            print(f"  ... et {len(resultats['commandes_refusees'])-10} autres")

    print(f"{'═'*62}\n")


def scenario_hrc_cher(data_path: str) -> dict:
    """
    Scénario E20 : Prix HRC +10%.
    Recharge les données avec les prix majorés et relance l'optimisation.
    """
    import copy
    from src.data_loader import load_data
    data_orig = load_data(data_path)
    # On modifie le DataFrame prix_hrc directement dans le fichier en mémoire
    # En pratique : on passe un paramètre de majoration au modèle
    print("📈 Scénario HRC +10% : modification des prix...")
    # Pour simplifier, on relance avec un override
    # Le modèle sera patché pour multiplier les coûts HRC
    return build_and_solve(data_path, hrc_multiplier=1.10)


def scenario_panne_lgb(data_path: str) -> dict:
    """
    Scénario E21 : LGB panne 2 jours supplémentaires en semaine 2.
    """
    print("🔧 Scénario panne LGB : +2j d'arrêt en S2...")
    return build_and_solve(data_path, extra_arrets={"LGB": {2: 2}})


def scenario_commande_urgente(data_path: str) -> dict:
    """
    Scénario E22 : Nouvelle commande HDG 300T DC01 0.5mm 1140mm S1 11500 MAD/T.
    """
    print("🚀 Scénario commande urgente HDG 300T...")
    new_cmd = {
        "ID": "CMD-NEW", "Client": "Nouveau_Client", "Famille": "HDG",
        "Grade": "DC01", "Epaisseur": 0.5, "Largeur": 1140,
        "Tonnage": 300, "Prix_vente": 11500, "Semaine_livraison": 1,
        "Priorite": "Haute"
    }
    return build_and_solve(data_path, extra_commandes=[new_cmd])


def main():
    print_banner()

    parser = argparse.ArgumentParser(
        description="Simulateur Capacité-Commande Maghreb Steel"
    )
    parser.add_argument(
        "--data", default="data/Donnees_MaghrebSteel.xlsx",
        help="Chemin vers le fichier de données Excel"
    )
    parser.add_argument(
        "--scenario", default="base",
        choices=["base", "hrc_cher", "panne_lgb", "commande_urgente"],
        help="Scénario à simuler"
    )
    parser.add_argument(
        "--output", default="outputs",
        help="Répertoire de sortie des résultats"
    )
    args = parser.parse_args()

    data_path = args.data
    if not Path(data_path).exists():
        # Essayer depuis la racine du projet
        alt = Path(__file__).parent / data_path
        if alt.exists():
            data_path = str(alt)
        else:
            print(f"❌ Fichier non trouvé : {data_path}")
            sys.exit(1)

    print(f"📂 Données : {data_path}")
    print(f"🎯 Scénario : {args.scenario}\n")

    # Lancer le bon scénario
    if args.scenario == "base":
        resultats = build_and_solve(data_path)
    elif args.scenario == "hrc_cher":
        resultats = scenario_hrc_cher(data_path)
    elif args.scenario == "panne_lgb":
        resultats = scenario_panne_lgb(data_path)
    elif args.scenario == "commande_urgente":
        resultats = scenario_commande_urgente(data_path)
    else:
        resultats = build_and_solve(data_path)

    print_results_summary(resultats, args.scenario)
    export_results(resultats, args.output)

    print("✅ Terminé ! Résultats disponibles dans :", Path(args.output).resolve())
    return resultats


if __name__ == "__main__":
    main()
