# Recherche de paramètres pour l'A* pondéré

Configuration de référence : `default.json`, grille 8×8, connectivité 8, départ (0,0), cible (7,7), seuil de mission 25.

---

## 1. Modélisation sous forme de contraintes

**Le problème**

- Variables de décision : `w` (poids de l'heuristique) et `h` (métrique)
- Hyperparamètres : la grille — taille, connectivité, obstacles, départ, cible, seuil
- Mesures : `C` coût du chemin, `E` nœuds développés, `M` pic du tas, `T` temps
- Fonction objectif : `F = a·C/C* + b·E/E* + c·M/M*`, à minimiser, avec `a = 0.5`, `b = c = 0.25`
- Référence : A\* classique (`w = 1`, `h = L2`) → `C* = 11`, `E* = 26`, `M* = 36`

**Les contraintes et leurs raisons**

- `w ∈ [1, 100]` — borne basse à 1 parce qu'en dessous A\* domine Dijkstra dès que `h` est admissible : on perd en efficacité sans rien gagner. Borne haute mesurée, pas choisie : de `w = 100` à `w = 100000`, les huit points testés donnent exactement `C = 43.5`, `E = 8`, `M = 27`. L'algorithme est devenu Greedy et plus rien ne change.
- `h` admissible — L1 compte une diagonale 2 alors qu'elle coûte 1.5, donc elle surestime en connectivité 8 et la garantie d'optimalité tombe. Elle est exclue dès le tirage plutôt que testée puis rejetée.
- `C ≤ k·C*` avec `k = 2.5` — les coûts possibles sur cette grille sont 11, 23 et 43.5, soit des ratios de 1, 2.09 et 3.95. En dessous de 2.09 un seul palier survit et il n'y a plus d'arbitrage à faire ; au-dessus de 3.95 la contrainte ne rejette plus rien. 2.5 laisse deux paliers en concurrence.
- `C < seuil de mission` (25) — contrainte du problème, pas un choix. L'API exige un coût strictement inférieur.
- `T ≤ 3 s` — garde-fou contre une recherche qui ne terminerait pas.

**Deux choix de normalisation à justifier**

- Diviser par la référence rend les trois termes sans unité et du même ordre de grandeur. Sans ça, le terme le plus grand en valeur absolue écraserait les autres quelle que soit l'intention derrière `a`, `b`, `c`.
- `E` remplace `T` dans `F`. Mesuré, `T` varie d'un facteur 4 sur un calcul identique, même en prenant la médiane sur 11 répétitions — à l'échelle de quelques dizaines de microsecondes le chronomètre ne mesure plus que du bruit. `E` capte le même phénomène sous forme d'entier reproductible. `T` reste mesuré et reporté, mais ne pilote plus la décision.

---

## 2. Résolution sur configuration fixe

**La stratégie : coarse-to-fine en trois passes**

- Grid logarithmique ×10 sur `[1, 100000]` — 12 évaluations, pour situer les ordres de grandeur
- Random uniforme sur `[1, 100]` — 50 évaluations, pour repérer les régions intéressantes
- Grid fin de pas 0.1 sur `[1, 9]` — 162 évaluations, pour localiser les frontières

**Le résultat**

- Optimum : `w ∈ [1.3, 8.8]` avec `h = L2`, `F = 0.767`
- Ce n'est pas un point mais un **palier** : les 76 valeurs de l'intervalle donnent le même `C = 11`, `E = 9`, `M = 26`, au chiffre près

| | C | E | M | F |
|---|---|---|---|---|
| Greedy (`w → ∞`) | 43.5 | 8 | 27 | 2.242 — infaisable |
| Dijkstra (`w = 0`) | 11 | 62 | 22 | 1.249 |
| A\* (`w = 1`, L2) | 11 | 26 | 36 | 1.000 |
| **Optimum** (`w ∈ [1.3, 8.8]`, L2) | **11** | **9** | **26** | **0.767** |

- Gain : 23 % sur `F`, 65 % d'exploration en moins, 28 % de mémoire en moins, coût optimal conservé

**Pourquoi ces résultats**

- Le paysage est un **escalier**, pas une courbe : 12 comportements distincts seulement sur 162 évaluations. `w` est continu mais ne produit qu'une poignée de résultats.
- La transition est brutale : `w = 1.0` explore 26 cases, `w = 1.1` en explore 9. Dix pour cent de poids en plus suffisent.
- L'explication : à `w = 1` avec une `h` admissible, beaucoup de cases partagent le même `f` et A\* les développe toutes. Amplifier `h` brise ces égalités en faveur des cases proches du but, sans encore fausser assez le classement pour dégrader le chemin.
- Dijkstra explore le plus (62) mais consomme le moins de mémoire (22), A\* l'inverse (26 et 36). Sa frontière avance en cercle serré là où celle d'A\* s'étire vers la cible. Moins de nœuds développés ne veut donc pas dire moins de mémoire.
- L_inf n'est pas monotone : son exploration descend de 34 à 9 entre `w = 1` et `w = 1.6`, puis **remonte** à 10 puis 11 avant la falaise de coût. Plus de poids sur `h` ne réduit pas toujours l'effort.

**Ce que donne la modification de la fonction de coût**

- Avec `T` au lieu de `E`, le classement s'inversait : L_inf passait devant L2 alors qu'elle est dominée sur `C`, `E` et `M`. Pire, la configuration de référence affichait `F = 1.72` au lieu de 1.0 par construction. Un terme bruité pesant un quart de l'objectif décidait du résultat, et décidait mal.
- Seuil d'arbitrage sur `a` : en gardant `b = c`, le palier à `C = 23` (deux fois plus cher, trois fois moins d'exploration que l'A\* classique) ne devient préférable à l'A\* classique que si `a < 0.29`. Il ne bat jamais le palier optimal, qui explore autant de cases (9) pour un coût de 11 (voir section 3). Au-dessus on privilégie le chemin optimal, en dessous on paie pour chercher moins.
- Avec `k < 2.09` un seul palier reste faisable : `F` n'arbitre plus rien, l'expérience se réduit à « quel est le plus grand `w` qui conserve l'optimum ».

**Ce que donne la modification des paramètres de recherche**

- Grid logarithmique seul : 12 évaluations suffisent à éliminer `[100, 100000]`, mais il saute directement de `w = 1` à `w = 10` et rate entièrement la zone utile. Conclusion erronée si on s'arrête là — nous avions d'abord conclu que la pondération ne payait jamais.
- Random uniforme sur `[1, 100]` : 45 tirages sur 50 sont tombés dans la zone morte. 90 % du budget perdu, et les 5 points utiles relèvent de la chance. Un tirage logarithmique aurait réparti les tirages entre les décennies.
- Grid fin : donne les frontières au dixième près, mais 162 évaluations pour une seule dimension — le coût explose dès qu'on ajoute un paramètre.

**Avantages et inconvénients de cette recherche**

- Grid — exhaustif sur l'intervalle, reproductible sans graine, lisible. Mais le coût croît exponentiellement avec le nombre de paramètres, et le pas décide de ce qu'on voit : un pas trop grand saute les transitions.
- Random — couvre mieux quand certaines dimensions ne comptent pas, et ne suppose aucune régularité. Mais dépend de la graine, et gaspille le budget si la loi de tirage ne correspond pas à la forme de l'espace.
- Coarse-to-fine — peu d'évaluations au total pour un espace non borné. Mais chaque passe hérite des erreurs de la précédente : si le balayage grossier saute une région, les passes fines ne la retrouveront jamais.
- Sur un paysage en escalier, aucune des trois ne donne « le » meilleur `w` : elles donnent un intervalle. Classer les points à l'intérieur d'un palier revient à trier du bruit.

**Les métaheuristiques locales : hill climbing et recherche tabou**

Pourquoi :
- La grid fine évalue tous les points, y compris les 76 qui donnent le même résultat
- Une recherche locale choisit ses points d'après les résultats précédents

Le fonctionnement (`search_hill_climbing.py`, `search_tabou.py`) :
- Voisins de `(w, h)` : `w ± 0.5` avec la même `h`, ou la même `w` avec une autre `h` admissible
- Départ : l'A\* classique (`w = 1`, L2), la solution à battre
- Hill climbing : va sur le meilleur voisin tant qu'il est strictement meilleur, s'arrête sinon
- Tabou : va toujours sur le meilleur voisin non tabou, même s'il est moins bon
- Tabou : les 10 dernières solutions quittées sont interdites, 20 tours, renvoie la meilleure solution vue
- Chaque solution n'est évaluée qu'une fois (cache) : le nombre d'évaluations est le vrai coût

**Comparaison des méthodes sur `default.json`**

Référence : A\* classique (`w = 1`, L2), `F = 1.000`, `C = 11`, `E = 26`, `M = 36`.

| Méthode | Type | Évaluations | Meilleur `F` | Réglage | C | E | M | Palier L2 trouvé | Optimum ? |
|---|---|---|---|---|---|---|---|---|---|
| Grid ×10 | exhaustive, grossière | 12 | 1.000 | `w = 1`, L2 | 11 | 26 | 36 | aucun | non : saute de 1 à 10 |
| Random | aléatoire | 50 | 0.767 | `w = 3.95`, L2 | 11 | 9 | 26 | 2 points | oui, 45 tirages sur 50 perdus |
| Grid fine | exhaustive, fine | 162 | 0.767 | `w = 1.3`, L2 | 11 | 9 | 26 | `[1.3, 8.8]` | oui, bords exacts |
| **Hill climbing** | locale | **5** | **0.767** | `w = 1.5`, L2 | 11 | 9 | 26 | début seulement | **oui, le moins cher** |
| **Tabou** | locale | 41 | **0.767** | `w = 1.5`, L2 | 11 | 9 | 26 | **`[1.5, 8.5]`** | **oui, avec les bords** |

- Hill climbing : même `F` que la grid fine, avec 32 fois moins d'évaluations (5 contre 162)
- Tabou : même `F`, presque les mêmes bords de palier, avec 4 fois moins d'évaluations (41 contre 162)
- Grid fine : la plus précise, la plus chère
- Pas d'optimum local sur cette grille : l'avantage propre de la tabou (sortir d'un creux) ne peut pas se voir ici, à vérifier sur des grilles avec obstacles

**Pourquoi le hill climbing ne fait que 5 évaluations**

| N° | Solution | `F` | Pourquoi |
|---|---|---|---|
| 1 | `w = 1`, L2 | 1.000 | départ |
| 2 | `w = 1.5`, L2 | 0.767 | tour 1, voisin `w + 0.5` |
| 3 | `w = 1`, L∞ | 1.091 | tour 1, autre heuristique |
| 4 | `w = 2`, L2 | 0.767 | tour 2, voisin `w + 0.5` |
| 5 | `w = 1.5`, L∞ | 0.833 | tour 2, autre heuristique |

- Tour 1 : `(0.5, L2)` rejeté (`w < 1`), `(1, L1)` rejeté (non admissible) : 2 voisins seulement. `(1.5, L2)` est meilleur, on s'y déplace
- Tour 2 : `(1, L2)` déjà évalué, servi par le cache. Le meilleur voisin `(2, L2)` est à égalité (0.767), pas strictement meilleur : arrêt
- Limite : il s'arrête au premier point du palier, sans savoir où il finit. C'est ce que la tabou ajoute

**Le choix du pas**

Même départ (`w = 1`, L2), même budget (20 tours, 41 évaluations), seul le pas change :

| Pas | Meilleur `F` | Palier L2 trouvé | Fin du palier atteinte ? |
|---|---|---|---|
| 0.1 | 0.767 | `[1.3, 3]` | non, mais début exact (comme la grid fine) |
| 0.2 | 0.767 | `[1.4, 5]` | non |
| **0.5** | **0.767** | **`[1.5, 8.5]`** | **oui : le coût passe à 23 à `w = 9`** |
| 1 | 0.767 | `[2, 8]` | oui, va jusqu'à la zone Greedy, bords imprécis |

- Tous les pas trouvent l'optimum : le pas change ce qu'on apprend du paysage, pas le meilleur `F`
- Petit pas : bords précis, mais avance lentement sur le palier (tous les voisins se valent)
- Grand pas : couvre plus de terrain, mais saute les transitions
- Point de départ : le pas de 0.2 de l'exemple du cours, trop lent sur le palier
- Choix final : 0.5, le plus petit pas qui parcourt le palier entier en 20 tours
- Prix : début du palier vu à 1.5 au lieu de 1.3
- Non optimisés : le nombre de tours (20) et la taille de la liste tabou (10), choisis comme budget raisonnable

**Pour reproduire les résultats**

Depuis le dossier `agent/`, avec la grid-api lancée. Chaque commande écrit son CSV dans `agent/resultats/` :

```
python baseline.py             configs/default.json --csv resultats/baseline.csv
python search_grid.py          configs/default.json --w-min 1 --w-max 100000 --factor 10 --csv resultats/etape1_grossier.csv
python search_random.py        configs/default.json --w-min 1 --w-max 100 --draws 50 --csv resultats/etape2_random.csv
python search_grid.py          configs/default.json --w-min 1 --w-max 9 --step 0.1 --csv resultats/etape3_fin.csv
python search_hill_climbing.py configs/default.json --w-max 100 --csv resultats/hc_default.csv
python search_tabou.py         configs/default.json --w-max 100 --csv resultats/tabou_default.csv
```

Et la comparaison des pas :

```
python search_tabou.py configs/default.json --w-max 100 --step 0.1 --csv resultats/tabou_pas_0.1.csv
python search_tabou.py configs/default.json --w-max 100 --step 0.2 --csv resultats/tabou_pas_0.2.csv
python search_tabou.py configs/default.json --w-max 100 --step 0.5 --csv resultats/tabou_pas_0.5.csv
python search_tabou.py configs/default.json --w-max 100 --step 1   --csv resultats/tabou_pas_1.csv
```

Pour les autres configurations (section 3), les mêmes commandes avec `configs/<config>.json` et `--csv resultats/<config>/<méthode>.csv`. La variation des contraintes se lance sans la grid-api, à partir des CSV :

```
python sensibilite.py
```

---

## 3. Test sur configuration variable

**Le protocole**

- Quatre grilles de plus, toutes 8×8, de (0,0) à (7,7), seuil 25 :
  - `deux_murs` : deux colonnes d'obstacles (poids 3 et 8) qui coupent toute la grille
  - `obstacle_u` : un obstacle en U (poids 9)
  - `deux_murs_con4`, `obstacle_u_con4` : les mêmes en connectivité 4
- Les mêmes commandes que sur `default.json`, mêmes `a`, `b`, `c` et `k`
- Résultats : `agent/resultats/<config>/` (`baseline.csv`, `grossier.csv`, `random.csv`, `fin.csv`, `hill_climbing.csv`, `tabou.csv`)

**Les baselines**

| Config | Conn. | `C*` | A\* (`E`, `M`) | Dijkstra `F` | Meilleur Greedy `F` |
|---|---|---|---|---|---|
| default | 8 | 11 | 26, 36 | 1.249 | 2.242, infaisable |
| deux_murs | 8 | 20.5 | 46, 27 | 1.024 | **0.879** (C = 24) |
| deux_murs_con4 | 4 | 23 | 64, 10 | **0.975** | 1.034 (L1), L2 et L∞ infaisables |
| obstacle_u | 8 | 12.5 | 44, 46 | **0.965** | 1.572, infaisable |
| obstacle_u_con4 | 4 | 14 | 54, 24 | **0.910** | **0.705** (L1, C = 14) |

- L'A\* classique n'est pas toujours la meilleure baseline : sur 4 grilles sur 5, Dijkstra ou Greedy font mieux
- Deux murs : on doit les traverser de toute façon, donc foncer vers la cible coûte peu (24 contre 20.5). Greedy est faisable et bat A\*
- Deux murs en connectivité 4 : A\* explore 64 cases comme Dijkstra, quelle que soit l'heuristique. L'estimation ne guide plus rien
- Le seuil est strict : sur `deux_murs_con4`, Greedy L2 et L∞ trouvent un coût d'exactement 25, donc la mission échoue

**Le meilleur réglage par configuration**

| Config | Meilleur `F` | `h` | Palier de `w` | C | E | M |
|---|---|---|---|---|---|---|
| default | 0.767 | L2 | `[1.3, 8.8]` | 11 | 9 | 26 |
| deux_murs | 0.835 | L∞ | `[5.8, 7.2]` | **21** | 10 | 29 |
| deux_murs_con4 | 0.939 | L∞ | `[1.8, 1.9]` | 23 | 42 | 11 |
| obstacle_u | 0.715 | L2 | `[4.1, 11]` au moins | 12.5 | 12 | 27 |
| obstacle_u_con4 | 0.705 | L1 | `[1.1, 100]` | 14 | 15 | 13 |

- Gain sur l'A\* classique : de 6 % (`deux_murs_con4`) à 30 % (`obstacle_u_con4`)
- 4 grilles sur 5 gardent le coût optimal. Seule `deux_murs` accepte un chemin 2.4 % plus cher (21 contre 20.5) pour explorer 10 cases au lieu de 46

**Les méthodes comparées** (meilleur `F` / évaluations)

| Config | Grid ×10 | Random | Grid fine | Hill climbing | Tabou |
|---|---|---|---|---|---|
| default | 1.000 / 12 | 0.767 / 50 | 0.767 / 162 | **0.767 / 5** | 0.767 / 41 |
| deux_murs | 0.879 / 12 | 0.869 / 50 | 0.835 / 162 | 0.946 / 6 | **0.835 / 35** |
| deux_murs_con4 | 1.000 / 18 | 1.012 / 50 | **0.939 / 243** | 1.000 / 4 | 0.966 / 46 |
| obstacle_u | **0.715 / 12** | 0.715 / 50 | 0.715 / 162 | 0.737 / 9 | 0.715 / 41 |
| obstacle_u_con4 | 0.705 / 18 | 0.705 / 50 | 0.705 / 243 | **0.705 / 7** | 0.705 / 58 |

- Hill climbing : le moins cher (4 à 9 évaluations), trouve l'optimum sur 2 grilles sur 5
- Hill climbing coincé sur 3 grilles :
  - `deux_murs` : optimum local en L∞ à `w = 1.5` (`F = 0.946`)
  - `obstacle_u` : palier intermédiaire `[2.5, 3]` (`F = 0.737`), juste avant le vrai palier qui commence à 4.1
  - `deux_murs_con4` : ne quitte pas son point de départ
- Tabou : trouve l'optimum de la grid fine sur 4 grilles sur 5, avec environ 4 fois moins d'évaluations
- Tabou : sur `deux_murs` et `obstacle_u`, elle sort des optimums locaux où le hill climbing s'arrête. On ne pouvait pas le voir sur `default.json`, qui n'en a pas
- Échec de la tabou sur `deux_murs_con4` : l'optimum est un palier de 0.1 de large, et le pas de 0.5 saute par-dessus (1.5 puis 2.0). Seule la grid fine le trouve
- Grid ×10 : suffit quand le palier s'étend loin (`obstacle_u`, `obstacle_u_con4`), car `w = 10` est dedans
- Random uniforme : gaspille toujours la majorité de ses tirages dans `[10, 100]`

**Ce qui change d'une grille à l'autre**

- Le palier optimal se déplace et n'a pas la même largeur partout : 0.1 sur `deux_murs_con4`, presque tout l'intervalle sur `obstacle_u_con4`
- L2 n'est pas toujours la meilleure heuristique. Elle gagne sur les grilles sans murs, L∞ gagne derrière les murs, et L1 sur le U en connectivité 4
- En connectivité 4, L1 redevient admissible. Sur le U, elle compte exactement les pas : Greedy avec L1 trouve le chemin optimal en explorant 15 cases au lieu de 54. Sur les deux murs, elle n'aide pas plus que les autres
- Aucun `w` n'est optimal sur toutes les grilles. On peut seulement chercher un compromis, calculé sur la grid fine des 5 grilles (L1 exclue, car non admissible en connectivité 8) :

| Critère | Réglage | `F` moyen | Pire `F` | Commentaire |
|---|---|---|---|---|
| Meilleure moyenne | L2, `w ≈ 5.3` | **0.845** | 1.020 | optimal sur `default` et `obstacle_u`, un peu moins bon que l'A\* classique sur `deux_murs_con4` |
| Meilleur pire cas | L∞, `w ≈ 1.6` | 0.890 | **0.951** | bat l'A\* classique sur les 5 grilles, sans être optimal nulle part |

**La variation des contraintes et des poids** (`sensibilite.py`)

- Méthode : un seul paramètre varie à la fois, les autres restent à `k = 2.5`, seuil = 25, `a = 0.5`
- Pas de nouvelle recherche : les CSV contiennent déjà `C`, `E` et `M`, qui ne dépendent pas des contraintes. On recalcule seulement la faisabilité et `F`
- Résultats complets : `agent/resultats/sensibilite.csv`

*Variation de `k`* :
- Avec `a = 0.5`, `k` ne change presque rien : le meilleur réglage garde déjà un coût optimal ou presque
- Seule exception : `deux_murs` avec `k = 1`, où le chemin à 21 est interdit. Le meilleur devient L∞ `w ∈ [5.3, 5.7]`, au coût optimal 20.5 (`F = 0.871` au lieu de 0.835)
- Avec `a = 0.2`, `k` devient actif sur `deux_murs` :

| `k` | Meilleur réglage sur `deux_murs` (`a = 0.2`) | C |
|---|---|---|
| 1.0 | L∞, `w ∈ [5.3, 5.7]` | 20.5 |
| 1.1 | L∞, `w ∈ [5.8, 7.2]` | 21 |
| ≥ 1.2 | L∞, `w ≥ 9.5` (comportement Greedy) | 24 |

- `k` n'a donc d'effet que si `a` est faible : tant que le coût pèse lourd dans `F`, le meilleur réglage reste proche du coût optimal et `k` ne rejette rien

*Variation du seuil de la mission* :

| Seuil | Grilles avec au moins une solution faisable |
|---|---|
| 12 | `default` seulement |
| 15, 20 | `default`, `obstacle_u`, `obstacle_u_con4` |
| 22 | toutes sauf `deux_murs_con4` |
| ≥ 25 | toutes |

- Le seuil agit comme un filtre tout ou rien : en dessous du coût optimal `C*`, la mission devient impossible
- Au-dessus, il ne change jamais le meilleur réglage, qui garde un coût proche de l'optimum

*Variation du poids du coût `a`* (`b = c = (1 − a) / 2`) :

| `a` | `default` | `deux_murs` | `obstacle_u` |
|---|---|---|---|
| 0.1, 0.2 | L2 `[1.3, 8.8]`, C 11 | L∞ `w ≥ 9.5`, **C 24** | L2 `[4.1, 11]`, C 12.5 |
| 0.3 à 0.6 | L2 `[1.3, 8.8]`, C 11 | L∞ `[5.8, 7.2]`, C 21 | L2 `[4.1, 11]`, C 12.5 |
| 0.8 | L2 `[1.3, 8.8]`, C 11 | L∞ `[5.3, 5.7]`, **C 20.5** | L2 `[4.1, 11]`, C 12.5 |
| 1.0 | l'A\* classique | l'A\* classique | l'A\* classique |

- Sur 4 grilles sur 5, le meilleur réglage ne change pas entre `a = 0.1` et `a = 0.8`
- Seule `deux_murs` bascule : plus le coût pèse, plus le chemin choisi est cher (24, puis 21, puis 20.5)
- À `a = 1`, seul le coût compte : tous les réglages au coût optimal sont à égalité, et l'A\* classique suffit
- Sur `default`, le chemin à 23 ne gagne pour aucune valeur de `a` : il explore autant de cases que le palier optimal (9) avec un tas plus grand. Il bat l'A\* classique quand `a < 0.29`, mais jamais l'optimum

---

## 4. Gérer la recherche quand la configuration change

- **Normaliser par la référence de chaque grille**, ce que fait déjà `F`. Un `F` calculé sur une grille est comparable à un `F` calculé sur une autre, puisque les deux sont rapportés à l'A\* classique de leur propre configuration.
- **Chercher un intervalle robuste plutôt qu'une valeur.** Le palier est large, donc on peut prendre l'intersection des paliers optimaux de plusieurs grilles. Un `w` au centre de cette intersection résiste à un changement de configuration ; un `w` au bord d'un palier bascule au premier changement. Sur nos cinq grilles, cette intersection est vide : le palier de `deux_murs_con4` (`[1.8, 1.9]`) ne recoupe pas celui d'`obstacle_u` (à partir de 4.1). Il faut alors accepter un compromis.
- **Optimiser sur un panel de configurations au lieu d'une seule.** Minimiser le `F` moyen rend la solution bonne en général ; minimiser le pire `F` la rend sûre dans le cas défavorable. Les deux sont défendables, le choix dépend de l'usage. Nos mesures donnent deux réponses différentes : L2 à `w ≈ 5.3` pour la moyenne, L∞ à `w ≈ 1.6` pour le pire cas (section 3).
- **Garder `a`, `b`, `c` fixes.** Ils expriment une préférence — ce qui compte pour nous entre coût, effort et mémoire — pas une propriété de la grille. Les réajuster par configuration reviendrait à changer la définition de « meilleur » à chaque mesure, et plus rien ne serait comparable.
- **Lier `h` à la connectivité et non à la grille.** L'admissibilité ne dépend que du modèle de déplacement : L1 est utilisable en connectivité 4, interdite en 8. C'est une règle déterministe, pas une recherche.
- **Si rechercher à chaque changement coûte trop cher**, apprendre une règle plutôt que refaire la recherche : relier le `w` optimal à des caractéristiques mesurables de la grille — densité d'obstacles, poids moyen, rapport entre la distance départ-cible et la taille. La recherche ne tourne alors qu'une fois, hors ligne, sur un échantillon de configurations.

---

## 5. Ce que nous retenons

- Le paysage de `F` est un escalier : le meilleur réglage est un intervalle de `w`, pas une valeur. Sa largeur dit à quel point le choix est robuste
- Pondérer `h` paie : de 6 à 30 % de mieux que l'A\* classique sur les 5 grilles, avec le coût optimal conservé sur 4 grilles sur 5
- La meilleure heuristique dépend de la grille : L2 sur les grilles ouvertes, L∞ derrière des murs, L1 en connectivité 4 sur le U
- Pas de réglage optimal partout : L2 `w ≈ 5.3` pour la moyenne, L∞ `w ≈ 1.6` pour le pire cas
- Aucune méthode de recherche ne gagne partout :
  - hill climbing : le moins cher, mais coincé sur le premier optimum local (3 grilles sur 5)
  - tabou : sort de ces optimums, environ 4 fois moins cher que la grid fine, mais rate un optimum plus étroit que son pas
  - grid fine : la plus sûre, la plus chère
- Les contraintes et les poids agissent ensemble : `k` ne rejette quelque chose que si `a` est faible, et le seuil n'est qu'un filtre tout ou rien
- Stratégie recommandée : une grid ×10 pour situer les ordres de grandeur, puis une recherche tabou depuis le meilleur point, avec un pas plus petit que les paliers recherchés
