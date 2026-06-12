# Simulateur Capacité-Commande — Maghreb Steel
## Projet Recherche Opérationnelle · EMINES UM6P · Promotion 2026

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![PuLP](https://img.shields.io/badge/solver-CBC%20via%20PuLP-green.svg)](https://coin-or.github.io/pulp/)
[![Streamlit](https://img.shields.io/badge/UI-Streamlit-red.svg)](https://streamlit.io/)

---

## Description

Simulateur d'optimisation multi-périodes, multi-produits, multi-ressources pour la planification de l'usine de laminage à froid de Maghreb Steel (Tit Mellil, Casablanca).

**Objectif :** Maximiser la marge sur coût variable sur un horizon de 4 semaines, tout en respectant les contraintes industrielles.

---

## Structure du projet

```
optimisation/
├── data/
│   └── Donnees_MaghrebSteel.xlsx   # Données sources
├── src/
│   ├── __init__.py
│   ├── data_loader.py              # Chargement des données Excel
│   └── model.py                   # Modèle LP (PuLP + CBC)
├── outputs/                        # Résultats exportés automatiquement
│   ├── resultats_complets.xlsx
│   ├── commandes_resultats.csv
│   ├── plan_marche.csv
│   ├── utilisation_lignes.csv
│   └── shadow_prices.csv
├── tests/
│   └── test_model.py              # Script de test/validation
├── app.py                         # Application Streamlit (interface web)
├── main.py                        # Script principal CLI
├── requirements.txt
└── README.md
```

---

## Installation

```bash
# Cloner / décompresser le projet
cd optimisation

# Installer les dépendances
pip install -r requirements.txt
```

---

## Utilisation

### 1. Lancer l'optimisation (CLI)

```bash
# Scénario de base
python main.py

# Scénario HRC +10% (question E20)
python main.py --scenario hrc_cher

# Panne LGB semaine 2 (question E21)
python main.py --scenario panne_lgb

# Commande urgente HDG 300T (question E22)
python main.py --scenario commande_urgente
```

### 2. Lancer l'application web interactive

```bash
streamlit run app.py
```
→ Ouvrez http://localhost:8501 dans votre navigateur.

---

## Modèle mathématique

### Variables de décision
- **x[i, k]** : tonnage de la commande *i* produit via le chemin de production *k* (T), continue ≥ 0

### Fonction objectif
**Maximiser** la marge sur coût variable :

```
Marge = Σ_{i,k} [ Prix_vente[i] − Prix_HRC[i] × (1/ρ_k)
                  − Coût_transformation[i,k]
                  + Valorisation_chutes[i,k]
                  − Extras_zinc_peinture[i] ] × x[i,k]
```

### Contraintes
- **C1** : `x[i] ≤ Tonnage_demandé[i]` — limite de commande
- **C2** : `Σ charge[ligne, s] ≤ Cadence[ligne] × (7 − Arrêts[ligne, s])` — capacité nette
- **C3** : `Σ HRC_consommé[grade] ≤ Dispo_HRC[grade] + Stock_PK[grade]` — matière première
- **C4** : `Stock_final[famille] ≥ Stock_min_sécurité[famille]` — stocks de sécurité

### Chemins de production
| Famille | Chemins possibles |
|---------|-------------------|
| CRC     | PK → CRMB → BAF → SKP |
| HDG     | PK → CRMA → LGA, PK → CRMB → LGA, PK → CRMB → LGB |
| PPGI    | PK → CRMA → LGA, PK → CRMB → LGA |
| BACR    | PK → CRMB → BAF → LGB, PK → CRMA → LGA, PK → CRMB → LGA |
| HRC DEC | PK uniquement |

---

## Résultats (scénario de base)

| Indicateur | Valeur |
|------------|--------|
| Marge totale | ~42.9 MMAD |
| Taux de service | 88.0% |
| Tonnage livré | ~14,929 T |
| Commandes refusées | 8 |
| Goulot principal | CRMB (99.6% S1) + LGA (100% S1) |

---

## Questions couvertes

### Essentielles (E1–E24) — Toutes traitées ✅
| # | Description | Où trouver |
|---|-------------|------------|
| E1-E4 | Analyse du problème | Rapport §2 |
| E5-E10 | Formulation mathématique | `src/model.py` + Rapport §3 |
| E11-E12 | Implémentation PuLP | `src/model.py` |
| E13-E15 | Solution optimale + validation | `tests/test_model.py` + outputs/ |
| E16 | Utilisation lignes | App → Tab "Utilisation Lignes" |
| E17 | Commandes refusées | App → Tab "Commandes" |
| E18 | Shadow prices | App → Tab "Shadow Prices" |
| E19 | Marge par famille | App → Tab "Analyse Économique" |
| E20-E22 | Scénarios | `main.py --scenario ...` |
| E23-E24 | Recommandations + limites | App → Tabs dédiés |

### Bonus (B1–B10)
- **B2** : Livraisons en retard → `build_and_solve(allow_late=True)`
- **B3** : Coûts de stockage → intégrés dans la fonction objectif
- **B6** : Interface web → `app.py` (Streamlit)

---

## Solveur

- **CBC** (COIN-OR Branch and Cut) — fourni avec PuLP, gratuit
- Temps de résolution : < 10 secondes
- Variables : ~200 variables continues (LP relaxation)

---

## Contact

Projet encadré par **Maryam Guessous** — EMINES UM6P
En collaboration avec **Haroun & Amal** — Maghreb Steel
