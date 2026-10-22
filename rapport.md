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
- Seuil d'arbitrage sur `a` : en gardant `b = c`, le palier à `C = 23` (deux fois plus cher, trois fois moins d'exploration) ne devient préférable que si `a < 0.29`. Au-dessus on privilégie le chemin optimal, en dessous on paie pour chercher moins.
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

La grid fine coûte cher parce qu'elle évalue tous les points, y compris les 76 qui donnent exactement le même résultat. Une recherche locale choisit au contraire ses points d'après les résultats précédents. Nous en avons implémenté deux (`search_hill_climbing.py`, `search_tabou.py`) :

- Voisins d'une solution `(w, h)` : `w ± 0.5` avec la même `h`, ou la même `w` avec une autre `h` admissible
- Départ : l'A\* classique (`w = 1`, L2), c'est-à-dire la solution à battre
- Hill climbing — va sur le meilleur voisin tant qu'il est strictement meilleur, s'arrête sinon
- Tabou — va toujours sur le meilleur voisin non tabou, même s'il est moins bon ; les 10 dernières solutions quittées sont interdites ; renvoie la meilleure solution vue sur 20 tours
- Chaque solution n'est évaluée qu'une fois : le nombre d'évaluations est le vrai coût de la recherche

Sur `default.json` :

| Méthode | Meilleur `F` | Évaluations |
|---|---|---|
| Grid ×10 | 1.000 | 12 |
| Random | 0.767 | 50 |
| Grid fine | 0.767 | 162 |
| **Hill climbing** | **0.767** | **5** |
| Recherche tabou | 0.767 | 41 |

- Le hill climbing atteint l'optimum en 5 évaluations : un seul pas (`w = 1 → 1.5`) le pose sur le palier, et il s'arrête puisqu'aucun voisin n'est strictement meilleur.
- La tabou ne fait pas mieux en `F`, mais elle parcourt le palier jusqu'à ses bords : L2 optimal de `w = 1.5` à `8.5`, puis le coût passe à 23 à `w = 9`. C'est la même information que la grid fine (`[1.3, 8.8]`), en 41 évaluations au lieu de 162.
- Sur cette grille, le paysage n'a qu'un creux : la tabou n'a pas d'optimum local à quitter, donc son avantage sur le hill climbing (sortir d'un creux pour en chercher un meilleur) ne peut pas se voir ici. Il faudra le vérifier sur des grilles avec obstacles.
**Le choix du pas**

Même départ (`w = 1`, L2), même budget (20 tours, soit 41 évaluations), seul le pas change :

| Pas | Meilleur `F` | Palier L2 trouvé | Ce que la tabou voit |
|---|---|---|---|
| 0.1 | 0.767 | `[1.3, 3]` | le début exact du palier (1.3, comme la grid fine), mais n'atteint pas sa fin |
| 0.2 | 0.767 | `[1.4, 5]` | n'atteint pas non plus la fin du palier |
| **0.5** | **0.767** | **`[1.5, 8.5]`** | **le palier entier, et sa fin : à `w = 9` le coût passe à 23** |
| 1 | 0.767 | `[2, 8]` | dépasse le palier jusqu'à la zone Greedy (infaisable dès `w = 15`), mais ses bords sont imprécis |

- Tous les pas trouvent l'optimum `F = 0.767` : sur cette grille, le pas ne change pas le meilleur `F`, seulement ce qu'on apprend du paysage.
- Un petit pas donne des bords précis mais avance lentement : sur un palier, tous les voisins se valent, et la tabou le parcourt point par point. À 0.1, 20 tours ne couvrent que `[1, 3]`.
- Un grand pas couvre beaucoup de terrain, mais il saute les transitions : à 1, la tabou ne voit ni le début réel du palier (1.3) ni la transition à `w = 1.1`.
- Nous avons gardé **0.5**, le plus petit pas qui parcourt le palier entier en 20 tours. Il reste bien plus petit que la moitié de l'écart de la grid ×10 autour de l'optimum (les points 1 et 10, soit 4.5). Le prix : il voit le début du palier à 1.5 au lieu de 1.3, une précision que seul un pas de 0.1 donne.

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

---

## 3. Test sur configuration variable

*À compléter — mesures à produire.*

Commandes :

```
python baseline.py configs/obstacle_u.json --csv baseline_u.csv
python search_grid.py configs/obstacle_u.json --w-min 1 --w-max 9 --step 0.1 --csv fin_u.csv
python baseline.py configs/deux_murs.json --csv baseline_murs.csv
python search_grid.py configs/deux_murs.json --w-min 1 --w-max 9 --step 0.1 --csv fin_murs.csv
```

Et les variantes `_con4` pour l'effet de la connectivité.

Questions auxquelles répondre :

- Le palier `[1.3, 8.8]` tient-il sur les autres grilles, ou se déplace-t-il ?
- La métrique gagnante reste-t-elle L2 ?
- En connectivité 4, L1 redevient admissible — change-t-elle le résultat ?
- Y a-t-il un `w` qui fonctionne partout, ou faut-il un `w` par configuration ?

---

## 4. Gérer la recherche quand la configuration change

- **Normaliser par la référence de chaque grille**, ce que fait déjà `F`. Un `F` calculé sur une grille est comparable à un `F` calculé sur une autre, puisque les deux sont rapportés à l'A\* classique de leur propre configuration.
- **Chercher un intervalle robuste plutôt qu'une valeur.** Le palier est large, donc on peut prendre l'intersection des paliers optimaux de plusieurs grilles. Un `w` au centre de cette intersection résiste à un changement de configuration ; un `w` au bord d'un palier bascule au premier changement.- **Optimiser sur un panel de configurations au lieu d'une seule.** Minimiser le `F` moyen rend la solution bonne en général ; minimiser le pire `F` la rend sûre dans le cas défavorable. Les deux sont défendables, le choix dépend de l'usage.
- **Garder `a`, `b`, `c` fixes.** Ils expriment une préférence — ce qui compte pour nous entre coût, effort et mémoire — pas une propriété de la grille. Les réajuster par configuration reviendrait à changer la définition de « meilleur » à chaque mesure, et plus rien ne serait comparable.
- **Lier `h` à la connectivité et non à la grille.** L'admissibilité ne dépend que du modèle de déplacement : L1 est utilisable en connectivité 4, interdite en 8. C'est une règle déterministe, pas une recherche.
- **Si rechercher à chaque changement coûte trop cher**, apprendre une règle plutôt que refaire la recherche : relier le `w` optimal à des caractéristiques mesurables de la grille — densité d'obstacles, poids moyen, rapport entre la distance départ-cible et la taille. La recherche ne tourne alors qu'une fois, hors ligne, sur un échantillon de configurations.
