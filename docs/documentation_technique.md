# Documentation Technique & Guide de Programmation
## Projet d'Optimisation Capacité-Commande — Maghreb Steel (Tit Mellil)
**Promotion EMINES UM6P 2026**

---

## 1. Architecture Globale et Flux de Données

Le système est conçu de manière modulaire en Python. Les fichiers du projet communiquent entre eux selon le schéma suivant :

```mermaid
graph TD
    A["Donnees_MaghrebSteel.xlsx (Excel)"] -->|Lecture pandas| B["data_loader.py (Parsing & Clean)"]
    B -->|Dictionnaire 'data'| C["model.py (Formulation PuLP)"]
    C -->|build_and_solve()| D["scenarios.py (Simulations de sensibilité)"]
    C -->|build_and_solve()| E["main.py (CLI & Exécution Scénarios)"]
    C -->|build_and_solve()| F["app.py (Streamlit Dashboard UI)"]
    D -->|DataFrames de résultats B8/B9| F
    E -->|Sauvegarde CSV/Excel| G["Dossier outputs/"]
```

### 1.1 Structure du dictionnaire de données `data`
La fonction [load_data](file:///c:/Users/HP/Desktop/optimisation/src/data_loader.py#L14) centralise le chargement et retourne un dictionnaire contenant les structures suivantes :

*   `data["commandes"]` (pd.DataFrame) :
    *   Colonnes : `ID`, `Client`, `Famille`, `Grade`, `Epaisseur`, `Largeur`, `Tonnage`, `Prix_vente`, `Semaine_livraison`, `Priorite`.
    *   *Nettoyage* : Exclusion de la famille "Quarto" (hors flux froid) et suppression des lignes vides.
*   `data["cadences"]` (pd.DataFrame) :
    *   Index : `Ligne` (PK, CRMA, CRMB, BAF, SKP, LGA, LGB).
    *   Colonnes : `HRC_DEC`, `CRC`, `HDG`, `PPGI`, `BACR` (Cadences de production en Tonnes/jour).
    *   *Nettoyage* : Remplacement des caractères de tirets (`\u2014`, `\u2013`) par `0.0`.
*   `data["rendements"]` (dict) :
    *   Clés : Process (`PK`, `CRMA`, `CRMB`, `BAF`, `SKP`, `LGA`, `LGB`).
    *   Valeurs : Rendement physique $\rho_p \in [0, 1]$ (ex: `{"PK": 0.98, "CRMA": 0.97, ...}`).
*   `data["couts_variables"]` (pd.DataFrame) :
    *   Index : `Process`.
    *   Colonnes : Tranches d'épaisseur (`lt03`, `t03_04`, `t04_05`, `t05_07`, `t07_10`, `t10_15`, `gt15`).
*   `data["prix_hrc"]` (pd.DataFrame) :
    *   Index : `Grade` (`DC01`, `DD13`, `DX51`, `DX52`, `S320`).
    *   Colonnes : Largeurs standard (`1020`, `1090`, `1100`, `1140`, `1250`, `1280`, `1320`).
*   `data["dispo_hrc"]` (dict) :
    *   Disponibilité maximale mensuelle d'achat pour chaque grade (ex: `{"DC01": 6750, ...}`).
*   `data["stocks_pk"]`, `data["stocks_ip"]`, `data["stocks_fp"]` (dict) :
    *   Stocks initiaux, minimums et maximums de sécurité par grade ou famille.
*   `data["arrets"]` (pd.DataFrame) :
    *   Index : `Ligne`.
    *   Colonnes : `S1`, `S2`, `S3`, `S4` (Jours d'arrêt planifiés par semaine).
*   `data["params"]` (dict) :
    *   Paramètres d'exploitation généraux (`Prix zinc`, `Consommation zinc`, `Prix de valorisation des chutes`, etc.).

---

## 2. Formulation Mathématique Complète

Le modèle résout un problème d'optimisation linéaire continue (LP Relaxation).

### 2.1 Indices et Ensembles
*   $i \in I$ : Ensemble des commandes clients valides.
*   $f \in F$ : Familles de produits finis (`CRC`, `HDG`, `PPGI`, `BACR`, `HRC DEC`).
*   $g \in G$ : Grades d'acier (`DC01`, `DD13`, `DX51`, `DX52`, `S320`).
*   $m \in M$ : Lignes de production physiques (`PK`, `CRMA`, `CRMB`, `BAF`, `SKP`, `LGA`, `LGB`).
*   $s \in \{1, 2, 3, 4\}$ : Semaines de l'horizon de planification.
*   $k \in K_i$ : Ensemble des chemins de production techniquement valides pour la commande $i$. Un chemin $k$ est une liste ordonnée d'étapes $(p, m)$ où $p$ est le process et $m$ la ligne physique.

### 2.2 Variables de Décision
*   $x_{i,k} \ge 0$ : Tonnage de la commande $i$ fabriqué et livré via le chemin de production $k$ (en Tonnes).

### 2.3 Paramètres
*   $T_i$ : Tonnage demandé pour la commande $i$.
*   $P_i$ : Prix de vente unitaire de la commande $i$ (MAD/T).
*   $S_i$ : Semaine de livraison demandée pour la commande $i$.
*   $C^{\text{HRC}}_{g(i), w(i)}$ : Prix d'achat de la bobine HRC pour le grade $g(i)$ et la largeur la plus proche de $w(i)$ (MAD/T).
*   $\rho_p$ : Rendement matière du processus $p$.
*   $c_{p, e(i)}$ : Coût variable de transformation (MAD/T) pour le processus $p$ à l'épaisseur $e(i)$.
*   $A_{m, s}$ : Jours d'arrêts planifiés de la ligne $m$ en semaine $s$.
*   $\text{Cad}_{m, f}$ : Cadence nominale de la ligne $m$ pour la famille $f$ (Tonnes/jour).
*   $\text{DispoHRC}_g$ : Quantité maximale de HRC de grade $g$ disponible à l'achat (Tonnes).
*   $\text{StockInitPK}_g$ : Stock initial disponible de bobines de grade $g$ au décapage (Tonnes).
*   $\text{StockMinFP}_f$, $\text{StockInitFP}_f$ : Stock minimum cible et initial de produits finis pour la famille $f$ (Tonnes).

---

### 2.4 Calculs Préparatoires (Physique & Économie du Flux)

Pour chaque commande $i$ et chemin de production $k \in K_i$ :

#### A. Rendement global du chemin
Le rendement global $\rho^{\text{global}}_{k}$ est le produit des rendements de chaque étape du chemin :
$$\rho^{\text{global}}_{k} = \prod_{(p, m) \in k} \rho_p$$

#### B. Facteur de conversion de matière (HRC par Tonne finie)
Pour obtenir $1 \text{ Tonne}$ de produit fini, il faut engager en entrée d'usine une quantité de matière première égale à :
$$h_{i,k} = \frac{1}{\rho^{\text{global}}_{k}}$$

#### C. Coût cumulé de transformation
Chaque coût unitaire d'étape $c_{p, e(i)}$ s'applique sur le flux entrant dans cette étape. Exprimé par tonne de produit fini, le coût cumulé s'écrit :
$$\text{CoûtTransfo}_{i,k} = \sum_{j=1}^{N_k} \frac{c_{p_j, e(i)}}{\prod_{l=j}^{N_k} \rho_{p_l}}$$
où $N_k$ est le nombre d'étapes dans le chemin $k$.

#### D. Valorisation des chutes de ferraille
La perte de matière est récupérée sous forme de chutes ferreuses valorisées à $50\%$ du prix de la ferraille ($P^{\text{chute}} = 1800 \text{ MAD/T}$) :
$$\text{ValChute}_{i,k} = (h_{i,k} - 1.0) \times P^{\text{chute}} \times 0.5$$

#### E. Coût des suppléments de matière (Extras)
Certains traitements requièrent des matières additionnelles (Zinc, Peinture) appliquées sur le produit fini :
$$\text{CoutExtras}_{i} = \begin{cases} 
P^{\text{Zinc}} \times \text{ConsoZinc} & \text{si } f(i) = \text{"HDG"}\\
P^{\text{Zinc}} \times \text{ConsoZincPPGI} + P^{\text{Peinture}} \times \text{ConsoPeinture} & \text{si } f(i) = \text{"PPGI"}\\
0 & \text{sinon}
\end{cases}$$

#### F. Marge unitaire de la variable
La marge sur coût variable par tonne de produit fini livrée pour la commande $i$ via le chemin $k$ est :
$$M_{i,k} = P_i - \left( C^{\text{HRC}}_{g(i), w(i)} \times h_{i,k} \right) - \text{CoûtTransfo}_{i,k} + \text{ValChute}_{i,k} - \text{CoutExtras}_{i}$$

---

### 2.5 Formulation du Programme Linéaire

#### Fonction Objectif : Maximisation de la marge brute globale
$$\max Z = \sum_{i \in I} \sum_{k \in K_i} M_{i,k} \times x_{i,k}$$

#### Contrainte C1 : Satisfaction de la demande (Volume maximum)
Pour chaque commande $i$, la production totale sur tous les chemins ne doit pas dépasser le tonnage commandé :
$$\sum_{k \in K_i} x_{i,k} \le T_i \quad \forall i \in I$$

#### Contrainte C2 : Capacité physique des lignes par semaine
Le flux traversant chaque ligne physique $m$ en semaine $s$ consomme du temps de production. Pour chaque commande $i$ planifiée pour la semaine $s$ ($S_i = s$), et pour chaque étape $(p, m)$ appartenant à son chemin $k$, le flux physique traversant la machine $m$ est :
$$\text{Flux}_{i,k,m} = x_{i,k} \times \phi_{k,m}$$
où $\phi_{k,m}$ est le facteur de rendement cumulé inversé depuis l'entrée de l'étape $m$ jusqu'à la sortie finale du chemin $k$.
Le temps d'occupation (en jours) sur la machine $m$ est $\frac{\text{Flux}_{i,k,m}}{\text{Cad}_{m, f(i)}}$.

La somme des temps d'occupation pour toutes les commandes traitées en semaine $s$ sur la ligne $m$ ne doit pas dépasser le nombre net de jours ouvrés disponibles :
$$\sum_{i \in I_s} \sum_{k \in K_i} \left( \frac{\phi_{k,m}}{\text{Cad}_{m, f(i)}} \right) x_{i,k} \le 7 - A_{m, s} \quad \forall m \in M, \forall s \in \{1, 2, 3, 4\}$$

*Note mathématique* : Si les jours de disponibilité nets de la ligne sont nuls ($7 - A_{m,s} \le 0$), toutes les variables $x_{i,k}$ dont le chemin $k$ traverse la machine $m$ en semaine $s$ sont immédiatement forcées à zéro :
$$\sum_{i \in I_s} \sum_{k \in K_i \ni m} x_{i,k} = 0$$

#### Contrainte C3 : Approvisionnement en matière première HRC par grade
La consommation totale en bobines HRC d'un grade $g$ ne doit pas dépasser le stock initial disponible aux décapages (PK) cumulé avec l'achat mensuel autorisé :
$$\sum_{i \in I \text{ de grade } g} \sum_{k \in K_i} h_{i,k} \times x_{i,k} \le \text{DispoHRC}_g + \text{StockInitPK}_g \quad \forall g \in G$$

#### Contrainte C4 : Stock minimum de sécurité en produits finis
Pour chaque famille de produits finis $f$, la production cumulée sur l'horizon doit couvrir le déficit éventuel entre le stock initial et le stock de sécurité imposé :
$$\sum_{i \in I \text{ de famille } f} \sum_{k \in K_i} x_{i,k} \ge \max\left(0, \text{StockMinFP}_f - \text{StockInitFP}_f\right) \quad \forall f \in F$$

---

## 3. Exemple Numérique Détaillé de Calcul de Marge

Soit la commande fictive suivante :
*   **ID** : `CMD-EXEMPLE`
*   **Famille** : `HDG` (Galvanisé)
*   **Grade** : `DX51`
*   **Épaisseur** : `0.45 mm` (Tranche $0.4 - 0.5$ mm)
*   **Largeur** : `1140 mm`
*   **Tonnage** : `100 T`
*   **Prix de vente** : `13 000 MAD/T`
*   **Semaine** : `1`

Le chemin testé est **`HDG_B`** : `PK` $\rightarrow$ `CRMB` $\rightarrow$ `LGA`.

### 3.1 Rendements et coefficients de passage
*   $\rho_{\text{PK}} = 0.98$
*   $\rho_{\text{CRMB}} = 0.97$
*   $\rho_{\text{LGA}} = 0.96$
*   **Rendement Global** :
    $$\rho^{\text{global}} = 0.98 \times 0.97 \times 0.96 = 0.912384$$
*   **Consommation HRC unitaire ($h$)** :
    $$h = \frac{1}{0.912384} \approx 1.09603 \text{ Tonnes de HRC par Tonne de HDG fini}$$
*   Pour produire $100 \text{ T}$ de produit fini, l'usine doit consommer **$109.60 \text{ T}$** de bobine HRC.

### 3.2 Coût d'achat de la matière première
Le prix d'achat HRC pour le grade `DX51` à la largeur `1140` est de `9 200 MAD/T`.
$$\text{Coût Matière Première} = 9200 \times 1.09603 \approx 10\,083.48 \text{ MAD par Tonne finie}$$

### 3.3 Coûts de transformation cumulés
Les coûts variables unitaires pour la tranche $0.45 \text{ mm}$ sont :
*   $c_{\text{PK}} = 170 \text{ MAD/T}$
*   $c_{\text{CRMB}} = 530 \text{ MAD/T}$
*   $c_{\text{LGA}} = 640 \text{ MAD/T}$

Ajustement par les rendements successifs :
1.  **LGA (Étape 3)** : Le coût s'applique directement sur le produit final :
    $$\text{Part LGA} = 640.00 \text{ MAD}$$
2.  **CRMB (Étape 2)** : Le coût s'applique à l'entrée de LGA :
    $$\text{Part CRMB} = \frac{530}{\rho_{\text{LGA}}} = \frac{530}{0.96} \approx 552.08 \text{ MAD}$$
3.  **PK (Étape 1)** : Le coût s'applique à l'entrée de CRMB :
    $$\text{Part PK} = \frac{170}{\rho_{\text{LGA}} \times \rho_{\text{CRMB}}} = \frac{170}{0.96 \times 0.97} \approx 182.56 \text{ MAD}$$
*   **Coût de Transformation Cumulé** :
    $$\text{CoûtTransfo} = 640.00 + 552.08 + 182.56 = 1\,374.64 \text{ MAD par Tonne finie}$$

### 3.4 Valorisation des chutes de ferraille
$$\text{Ferraille générée} = 1.09603 - 1.0 = 0.09603 \text{ T}$$
$$\text{Crédit chute} = 0.09603 \times 1800 \times 0.5 \approx 86.43 \text{ MAD par Tonne finie}$$

### 3.5 Suppléments (Extras)
Consommation de Zinc pour galvanisation :
$$\text{Coût Extra Zinc} = 18000 \text{ MAD/T} \times 0.025 \text{ T/T} = 450.00 \text{ MAD par Tonne finie}$$

### 3.6 Calcul de la marge nette unitaire ($M_{i,k}$)
$$M_{i,k} = 13\,000.00 - 10\,083.48 - 1\,374.64 + 86.43 - 450.00 = 1\,178.31 \text{ MAD par Tonne}$$

*   Pour les **100 T** de la commande, la marge totale dégagée s'élève à **$117\,831 \text{ MAD}$**.
*   *Note importante* : Si le prix de vente avait été inférieur (par exemple `11 500 MAD/T`), la marge unitaire serait devenue négative ($-321.69 \text{ MAD/T}$), et le modèle aurait automatiquement refusé de fabriquer cette commande.

---

## 4. Analyse des Fichiers de Code Source

### 4.1 Module `data_loader.py`
Ce module lit le fichier Excel et prépare les variables économiques.

#### `load_data(filepath)`
*   **Entrée** : `filepath` (chemin vers le classeur Excel).
*   **Sortie** : Dictionnaire `data` structuré.
*   **Points clés** :
    *   Nettoyage des colonnes et alignement des en-têtes Excel.
    *   Conversion dynamique des types de données pour éviter les erreurs de type `TypeError` lors des calculs numériques du modèle.
    *   Remplacement des caractères spéciaux de tirets (`—`) dans les cadences.

#### `get_cout_transformation(epaisseur, process, couts_df)`
*   Recherche par indexation pandas les coûts correspondants à la tranche de l'épaisseur de la tôle.

#### `get_prix_hrc(grade, largeur, prix_hrc_df)`
*   Calcule la largeur la plus proche via une recherche par clé de proximité :
    ```python
    nearest = min(largeurs_disponibles, key=lambda x: abs(x - largeur_int))
    ```

#### `get_capacite_nette(ligne, semaine, famille, cadences, arrets)`
*   Calcule la capacité disponible en tonnes pour une machine et une famille de produits :
    $$\text{Capacité} = \text{Cadence} \times (7 - \text{Arrêts})$$

---

### 4.2 Module `model.py`
Ce module contient l'essentiel du code PuLP d'optimisation.

#### `build_and_solve(...)`
Cette fonction orchestre la construction et l'exécution du problème linéaire :
1.  **Réception des scénarios** : Elle accepte des paramètres optionnels permettant de simuler des variations de prix (`hrc_multiplier`), des arrêts de maintenance imprévus (`extra_arrets`), des commandes de dernière minute (`extra_commandes`), des restrictions sur le grade DC01 (`dc01_multiplier`), ou des variations globales des cadences physiques (`cadence_multiplier`).
2.  **Filtrage technique préalable** : Les commandes dont l'épaisseur ne correspond pas aux limites physiques de la ligne finale LGA ou LGB sont exclues d'emblée des chemins candidats.
3.  **Génération des variables PuLP** :
    ```python
    x[i][ck] = LpVariable(f"x_{i}_{ck}", lowBound=0, upBound=cd["tonnage"])
    ```
4.  **Déclaration des contraintes logistiques** :
    *   *Limite Demande (C1)* : La somme de la production par chemin $\le$ Demande.
    *   *Temps Machine (C2)* : La somme des temps consommés sur chaque ligne physique par semaine $\le$ Jours ouvrés restants.
    *   *Approvisionnement HRC (C3)* : Consommation de HRC par grade $\le$ Achat max + Stock PK initial.
    *   *Stock de Sécurité (C4)* : Production totale $\ge$ Besoin de stock.
5.  **Exécution** : Le problème est résolu via le solveur `PULP_CBC_CMD` configuré avec une limite de temps de 5 minutes.
6.  **Extraction post-résolution** :
    *   *Shadow Prices* : Récupérés via `constraint.pi` sur les contraintes saturées.
    *   *Plan de marche* : Calcule l'écoulement physique exact sur chaque machine par semaine.
    *   *Utilisation des lignes* : Ratio entre temps requis et temps disponible net.

#### `export_results(resultats, output_dir)`
*   Exporte les données en fichiers CSV individuels (`commandes_resultats.csv`, `plan_marche.csv`, `utilisation_lignes.csv`, `shadow_prices.csv`).
*   Regroupe tous les tableaux dans un fichier unique Excel consolidé (`resultats_complets.xlsx`) à l'aide de `openpyxl`.

---

### 4.3 Module `scenarios.py`
Ce fichier pilote les boucles d'analyse de sensibilité.

#### `analyse_enveloppe_dc01(data_path)`
*   Fait varier le coefficient d'approvisionnement en HRC grade DC01 de `0.5` à `1.5` par pas de `0.1`.
*   Appelle à chaque itération la fonction `build_and_solve` et stocke l'évolution de la marge totale et du taux de service global.
*   Retourne un DataFrame résumant le comportement du modèle face aux pénuries ou excédents de matière première.

#### `analyse_robustesse_cadences(data_path)`
*   Fait varier le coefficient de cadence de toutes les lignes physiques de `0.95` à `1.05` par pas de `0.01` (représentant une baisse ou une hausse globale de productivité de $\pm 5\%$).
*   Permet d'évaluer la robustesse du plan face aux aléas de productivité des machines.

---

### 4.4 Module `main.py`
Ce script console permet d'exécuter et de tester le modèle sans interface web.

*   **Scénarios Prédéfinis** :
    *   `base` : Paramètres d'origine du fichier Excel.
    *   `hrc_cher` : Simule une augmentation globale de $10\%$ des prix du HRC (`hrc_multiplier=1.10`).
    *   `panne_lgb` : Ajoute 2 jours d'arrêt supplémentaires en semaine 2 sur la ligne LGB (`extra_arrets={"LGB": {2: 2}}`).
    *   `commande_urgente` : Ajoute une commande spéciale HDG de 300 Tonnes en semaine 1 au prix de 11 500 MAD/T.
*   **Formatage** : Il affiche un résumé formaté directement dans le terminal (taux d'utilisation des lignes avec des indicateurs visuels de couleur 🟢/🟡/🔴, top 5 des contraintes critiques, etc.).

---

### 4.5 Module `app.py` (Dashboard UI Streamlit)
Interface utilisateur riche, dynamique et interactive.

#### A. Caching des calculs
Pour optimiser les performances et éviter de relancer l'optimisation à chaque modification d'affichage mineure (changement d'onglet ou de filtre), l'application s'appuie sur le système de cache de Streamlit :
```python
@st.cache_data
def run_model_cached(data_path, hrc_multiplier, extra_arrets, extra_commandes, dc01_multiplier, cadence_multiplier):
    # Appel de build_and_solve et retour des dictionnaires
    return build_and_solve(...)
```

#### B. Visualisation graphique
*   **Heatmap d'Utilisation** : Un graphique interactif `plotly.graph_objects.Heatmap` montre visuellement les goulots d'étranglement (lignes saturées à $\ge 95\%$ en rouge).
*   **Marge par Famille** : Graphiques à barres horizontales `plotly.express.bar` pour illustrer la contribution financière relative de chaque produit.

#### C. Gestion de la compatibilité Pandas
La mise en forme de la couleur du taux de service utilise la méthode `.map()` du `Styler` pandas (ex: `df.style.map(...)`) pour éviter les plantages d'incompatibilité avec pandas version $\ge 2.1.0$ (où `.applymap()` a été supprimée) :
```python
def color_taux(val):
    if val >= 95:
        return "color: #34d399" # Vert
    elif val >= 5:
        return "color: #fbbf24" # Orange
    else:
        return "color: #f87171" # Rouge

styled = df_show.style.map(color_taux, subset=["taux_service"])
st.dataframe(styled, use_container_width=True, hide_index=True)
```

---

## 5. Explication Théorique des Prix d'Ombre (Shadow Prices)

En programmation linéaire, le **prix d'ombre** (ou variable duale) d'une contrainte correspond au taux de variation de la valeur optimale de la fonction objectif par rapport à une modification infinitésimale de la ressource (le membre de droite de la contrainte) :
$$\lambda_c = \frac{\partial Z^*}{\partial b_c}$$

### 5.1 Signification physique dans le modèle
1.  **Contrainte de Capacité Ligne saturée** (Contrainte de type C2) :
    Si le prix d'ombre de la contrainte `cap_time_LGA_S1` est égal à `125 000 MAD/jour`, cela signifie que si LGA pouvait tourner **1 jour de plus** en semaine 1 (par exemple en annulant un arrêt de maintenance), la marge bénéficiaire globale de l'usine augmenterait de **$125\,000 \text{ MAD}$** en planifiant des commandes en attente.
2.  **Contrainte d'Approvisionnement Matière saturée** (Contrainte de type C3) :
    Si la contrainte d'approvisionnement en grade DC01 (`hrc_DC01`) a un prix d'ombre de `450 MAD/Tonne`, cela indique que chaque tonne supplémentaire de grade DC01 achetée ou débloquée permettrait de générer **$450 \text{ MAD}$** de profit net en livrant des commandes de grade DC01 qui ont dû être refusées.

### 5.2 Extraction dans PuLP
Pour obtenir ces valeurs après la résolution, le modèle parcourt les contraintes et extrait l'attribut `.pi` :
```python
shadow_prices = {}
for name, cst in prob.constraints.items():
    sp = cst.pi
    if sp is not None and abs(sp) > 0.001:
        shadow_prices[name] = round(sp, 2)
```
Ces informations sont cruciales pour les décideurs de Maghreb Steel car elles permettent d'orienter les décisions d'investissement (quelles machines renforcer, sur quels grades négocier des contrats d'approvisionnement plus importants).
