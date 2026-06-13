# Guide d'Explication du Modèle d'Optimisation (Maghreb Steel)

Ce document récapitule les explications détaillées des variables, coûts, fonction objectif et contraintes du modèle d'optimisation capacité-commande de l'usine de Tit Mellil. Il est rédigé dans un style hybride (Français et Darija) pour faciliter la compréhension et la préparation de la soutenance du projet.

---

## 1. Les Variables de Décision $x_{i,k}$

### Q: Wach $x_{i,k}$ kaykhod 1 wela 0 (Binaire) ?
**Non, machi binaire (0/1).** 
$x_{i,k}$ est une **variable continue (nombre réel/décimal)** qui représente le **tonnage** (en Tonnes) produit pour la commande $i$ via le chemin $k$.

*   **Low Bound = 0** : Minimum de production est 0 (commande refusée).
*   **Up Bound = Tonnage demandé** : Maximum de production est le tonnage demandé par le client (ma9drouch ndépassiw chno tleb).
*   **Les valeurs intermédiaires** : $x_{i,k}$ peut prendre n'importe quelle valeur réelle entre ces deux bornes (ex. $125.5 \text{ T}$).

**Pourquoi ?**
1.  **Livraison Partielle** : Le modèle peut accepter de produire une partie de la commande si la capacité de la machine ou le HRC is insuffisant, au lieu de la rejeter complètement.
2.  **Vitesse de calcul** : Les variables continues sont beaucoup plus rapides à résoudre par le solveur (CBC) que les variables binaires (0/1) du type Mixed Integer Programming (MIP).

---

### Q: Chno hiya dik $k$ (Chemin de production) ?
Le **chemin ($k$)** est la **séquence de machines (process)** par laquelle passe la bobine d'acier pour devenir un produit fini.

**Exemple concret pour la famille `HDG` (Galvanisé) :**
Une commande de cette famille peut être produite via 3 chemins différents selon la disponibilité des machines :
1.  **Chemin `HDG_A`** : PK (Décapage) $\rightarrow$ CRMA (Laminoir A) $\rightarrow$ LGA (Galvanisation A).
2.  **Chemin `HDG_B`** : PK (Décapage) $\rightarrow$ CRMB (Laminoir B) $\rightarrow$ LGA (Galvanisation A).
3.  **Chemin `HDG_C`** : PK (Décapage) $\rightarrow$ CRMB (Laminoir B) $\rightarrow$ LGB (Galvanisation B).

**L'intérêt des chemins dans le modèle :**
*   **Routage Dynamique** : Si le laminoir CRMA est surchargé, le modèle va automatiquement router la commande vers CRMB (chemin `HDG_B`) pour éviter de la refuser.
*   **Contraintes Physiques (Épaisseur)** : LGA gère uniquement les épaisseurs fines ($\le 0.6 \text{ mm}$), tandis que LGB gère les épaisseurs épaisses ($> 0.6 \text{ mm}$). Le code filtre automatiquement les chemins incompatibles avant l'optimisation.

---

## 2. Le Coût de Transformation (Coûts Variables)

### Q: Chnahowa Coût de Transformation ?
C'est le coût variable (exprimé en **MAD/Tonne**) payé par l'usine pour traiter l'acier sur chaque machine. Il dépend de deux facteurs :
1.  **Le Process (la machine)** : Faire tourner un laminoir comme CRMB consomme beaucoup d'électricité et coûte plus cher qu'un simple passage dans la ligne PK (Décapage) ou SKP (Skin-pass).
2.  **L'Épaisseur de l'acier** : Plus la tôle demandée est mince, plus elle nécessite de passes de laminage et plus le coût est élevé. Les tôles épaisses se laminent rapidement et coûtent moins cher.

**Tableau des coûts variables de transformation (MAD/T) :**

| Process \ Épaisseur (mm) | <0.3 | 0.3-0.4 | 0.4-0.5 | 0.5-0.7 | 0.7-1.0 | 1.0-1.5 | >1.5 |
|---|---|---|---|---|---|---|---|
| **PK** (Décapage) | 180 | 175 | 170 | 165 | 160 | 155 | 150 |
| **CRMA** (Laminoir A) | 620 | 580 | 550 | 510 | 470 | 430 | 400 |
| **CRMB** (Laminoir B) | 600 | 560 | 530 | 490 | 450 | 415 | 385 |
| **BAF** (Recuit) | 290 | 280 | 270 | 260 | 250 | 240 | 230 |
| **SKP** (Skin-pass) | 150 | 145 | 140 | 135 | 130 | 125 | 120 |
| **LGA-HDG** | 720 | 680 | 640 | 600 | 560 | 520 | 480 |
| **LGA-PPGI** | 820 | 780 | 740 | 700 | 660 | 620 | 580 |
| **LGA-BACR** | 680 | 640 | 610 | 580 | 550 | 520 | 490 |
| **LGB-HDG** | 790 | 750 | 710 | 670 | 630 | 590 | 560 |
| **LGB-BACR** | 680 | 640 | 610 | 580 | 550 | 520 | 490 |

**Calcul cumulé dans le code :**
Si une commande d'épaisseur $0.45 \text{ mm}$ utilise le chemin PK $\rightarrow$ CRMB $\rightarrow$ LGA-HDG, le coût est la somme des coûts de ces trois étapes ajustés par les rendements matière cumulés de chaque étape.

---

## 3. La Fonction Objectif

### Q: Chnahya la Fonction Objectif dyal l-modèle ?
C'est la fonction cible que le solveur cherche à **maximiser**. Son but est de trouver la combinaison de commandes et de chemins de production qui rapporte le profit net (la marge sur coût variable) le plus élevé possible :

$$\text{Maximiser } Z = \sum_{i} \sum_{k} \left( \text{Marge\_Unitaire}_{i, k} \times x_{i, k} \right)$$

Où la marge unitaire par tonne de produit fini est définie par :
$$\text{Marge\_Unitaire}_{i, k} = \text{Prix de Vente}_i - \text{Coût HRC}_{i, k} - \text{Coût Transformation}_{i, k} + \text{Valorisation Chutes}_{i, k} - \text{Coût Extras}_{i, k}$$

1.  **Prix de Vente ($+$)** : Prix unitaire négocié avec le client.
2.  **Coût HRC ($-$)** : Prix d'achat de la matière première (HRC) ajusté par le rendement global du chemin : $\text{Prix\_HRC} \times \frac{1}{\text{Rendement\_Global}}$.
3.  **Coût de Transformation ($-$)** : La somme des coûts des machines du chemin $k$ (provenant du tableau des coûts).
4.  **Valorisation des Chutes ($+$)** : La ferraille générée par les pertes de rendement est valorisée et vendue à $1800 \text{ MAD/T}$ avec un coefficient de récupération de $50\%$.
5.  **Coût des Extras ($-$)** : Coût du Zinc consommé pour la galvanisation (HDG) et de la Peinture (PPGI).

---

## 4. Les Contraintes du Modèle

### C1 : Limite de Livraison
$$\sum_k x_{i,k} \le \text{Tonnage\_demandé}_i \quad \forall i$$
*   **Explication** : La quantité totale produite pour une commande $i$ ne peut pas dépasser la quantité demandée par le client.
*   **Contrainte active ($\sum_k x_{i,k} = \text{Tonnage\_demandé}$)** : Signifie que la commande est acceptée à 100% (Taux de service = 100%).

### C2 : Capacité nette par Ligne × Semaine
$$\sum_{i, k \ni \text{ligne} \in k} \left( \frac{x_{i,k}}{\rho_{\text{cumul}}} \right) \le \text{Cadence}_{\text{ligne}} \times (7 - \text{Arrêts}_{\text{ligne}, s}) \quad \forall \text{ligne}, \forall s$$
*   **Explication** : Le tonnage réel passant par une machine durant la semaine $s$ ne doit pas dépasser sa capacité physique maximale de traitement.
*   **$\frac{x_{i,k}}{\rho_{\text{cumul}}}$** : Ajuste le tonnage final par le rendement des étapes suivantes pour connaître la charge réelle passant par la machine.
*   **$\text{Cadence} \times (7 - \text{Arrêts})$** : Calcule le temps de fonctionnement effectif de la machine (7 jours moins les jours d'arrêts planifiés pour maintenance) multiplié par son débit quotidien.

### C3 : Disponibilité HRC par Grade
$$\sum_{i \text{ de grade } g, k} \left( \frac{x_{i,k}}{\rho_{\text{chemin } k}} \right) \le \text{Dispo\_HRC}_g + \text{Stock\_PK}_g \quad \forall g$$
*   **Explication** : La consommation totale de bobines HRC d'un grade $g$ ne doit pas dépasser les ressources physiques de l'usine (Stock initial existant dans les décapages + Tonnage d'achat maximum mensuel autorisé auprès du fournisseur).
*   **Exemple (DC01)** : Stock PK (800T) + Disponibilité (6750T) = 7550 T maximum consommables.

### C4 : Stock Minimum de Sécurité
$$\sum_{i \text{ de famille } f, k} x_{i,k} \ge \max(0, \text{Stock\_min}_f - \text{Stock\_initial}_f) \quad \forall f$$
*   **Explication** : Garantit que l'usine conserve un volume minimal de stock physique de produits finis à la fin du mois pour faire face aux urgences du mois suivant.
*   **Analyse Critique (Cas de l'usine)** :
    Comme l'usine commence avec un stock initial de produits finis supérieur au stock de sécurité minimum ($\text{Stock\_initial} > \text{Stock\_min}$ pour toutes les familles) et que ce stock initial n'est pas utilisé pour livrer les commandes courantes, le déficit à combler est nul ($\text{Besoin} = 0$). La contrainte est donc toujours respectée sans forcer de production supplémentaire. Le modèle ne produit que pour satisfaire les commandes clients les plus rentables.
