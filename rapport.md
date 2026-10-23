Groupe 4 :
Boudjema Dyhia


# A* pondéré : recherche des meilleurs paramètres

Grille de base : `default.json`, 8×8, connectivité 8, départ (0,0), cible (7,7), seuil de mission 25.

---

## 1. Modélisation du problème

Le problème :
- Variables de décision : `w` (le poids de l'heuristique) et `h` (L1, L2 ou L∞)
- Hyperparamètres, fixés et pas optimisés : la grille (taille, connectivité, obstacles, départ, cible, seuil)
- Mesures : `C` le coût du chemin, `E` le nombre de cases explorées, `M` la taille max du tas, `T` le temps
- Fonction objectif, à minimiser : `F = a·C/C* + b·E/E* + c·M/M*`, avec `a = 0.5` et `b = c = 0.25`
- Référence (`C*`, `E*`, `M*`) : l'A* classique (`w = 1`, L2), recalculé sur chaque grille

Pourquoi ces choix :
- On divise par la référence pour que les 3 termes soient à la même échelle (autour de 1). Sinon le plus grand écrase les autres
- Exemple sur `deux_murs`, avec `a = 0.8` (le coût compte beaucoup) : sans normaliser, Greedy (coût 24) battrait l'A* (coût 20.5), juste parce que l'effort se compte en dizaines de cases (8 contre 46). En normalisant, l'A* gagne, comme les poids le demandent
- On utilise `E` et pas `T` : avec le cache, une recherche dure quelques microsecondes et `T` variait jusqu'à x4 pour le même calcul. `E` mesure le même travail mais ne bouge pas d'un lancement à l'autre. `T` est quand même mesuré et noté dans les CSV
- `a = 0.5` : on veut d'abord un chemin pas cher. L'effort et la mémoire comptent pour l'autre moitié
- L'A* classique comme référence : avec une `h` admissible il garantit le coût optimal, donc `C*` est le vrai minimum. Et c'est notre algo avec `w = 1`, c'est-à-dire sans réglage
- L2 dans la référence : elle est admissible en connectivité 4 et 8, donc on garde la même référence sur toutes les grilles

Les contraintes :

| Contrainte | Pourquoi |
|---|---|
| `1 ≤ w ≤ 100` | en dessous de 1 on se rapproche de Dijkstra. Au-dessus de 100 plus rien ne change (testé jusqu'à 100 000 : même chemin) |
| `h` admissible | L1 interdite en connectivité 8 : elle compte une diagonale 2 alors qu'elle coûte 1.5 |
| `C ≤ 2.5 × C*` | on accepte un chemin plus cher s'il fait gagner beaucoup en effort. Sur `default`, les coûts possibles sont 11, 23 et 43.5 : 2.5 garde 11 et 23 |
| `C < seuil` (25) | imposé par la mission |
| `T ≤ 3 s` | garde-fou, jamais atteint |

- Une solution qui viole une contrainte reçoit un score infini, elle ne peut jamais être choisie

---

## 2. Résolution sur la configuration par défaut

La stratégie, du grossier au fin :
- Grid x10 de 1 à 100 000 (12 essais) : situer les ordres de grandeur. Au-delà de 100 plus rien ne change
- Random entre 1 et 100 (50 essais) : trouver la zone utile, sous `w = 10`
- Grid fine au pas de 0.1 entre 1 et 9 (162 essais) : trouver les bords précis
- Puis deux métaheuristiques locales pour faire pareil en moins d'essais : hill climbing et recherche tabou (départ `w = 1` L2, pas de 0.5)

Le résultat :

| | C | E | M | F |
|---|---|---|---|---|
| Dijkstra (`w = 0`) | 11 | 62 | 22 | 1.249 |
| A* classique (`w = 1`, L2) | 11 | 26 | 36 | 1.000 |
| Greedy (`w` très grand) | 43.5 | 8 | 27 | 2.242, mission ratée |
| **Notre meilleur : L2, `w` de 1.3 à 8.8** | **11** | **9** | **26** | **0.767** |

- Même coût optimal que l'A*, 65 % de cases explorées en moins, 28 % de mémoire en moins
- Ce n'est pas un `w` précis mais un intervalle : les 76 valeurs entre 1.3 et 8.8 donnent exactement le même chemin
- L∞ fait presque pareil (`F = 0.774`) : même chemin, mais une case de plus dans le tas

Pourquoi ces résultats :
- `F` varie en escalier : `w` est continu mais ne donne que quelques chemins différents (12 sur 162 essais)
- À `w = 1`, beaucoup de cases ont le même `f` et l'A* les explore toutes. Un peu plus de poids sur `h` (`w = 1.1`) suffit à les départager vers la cible : on passe de 26 à 9 cases
- Trop de poids (`w ≥ 9`) et le chemin change : il coûte 23, puis 43.5 quand on devient Greedy
- Dijkstra explore le plus mais garde le plus petit tas : explorer moins ne veut pas dire utiliser moins de mémoire

Les méthodes de recherche comparées :

| Méthode | Essais | Meilleur `F` | Remarque |
|---|---|---|---|
| Grid x10 | 12 | 1.000 | saute de 1 à 10 et rate toute la zone utile |
| Random | 50 | 0.767 | 45 tirages sur 50 tombent là où la mission échoue |
| Grid fine | 162 | 0.767 | donne les bords exacts du palier |
| Hill climbing | 5 | 0.767 | le moins cher, mais ne sait pas où le palier s'arrête |
| Tabou | 41 | 0.767 | trouve aussi les bords (1.5 à 8.5) |

- Le hill climbing ne fait que 5 essais : un pas de 0.5 le met sur le palier, puis aucun voisin n'est strictement meilleur, donc il s'arrête
- Sur cette grille il n'y a pas d'optimum local, donc la tabou ne gagne rien en `F` ici

Ce que donne la modification de la fonction de coût :
- Avec `T` dans `F`, le classement dépendait du bruit du chrono : L∞ passait devant L2 alors qu'elle n'est meilleure sur rien. D'où le passage à `E`
- Le poids `a` change peu le résultat ici. Le chemin à 23 bat l'A* classique si `a < 0.29`, mais il ne bat jamais notre meilleur réglage : il explore autant de cases (9) pour un coût deux fois plus grand
- `k` : en dessous de 2.09 seul le coût 11 reste autorisé, mais le meilleur réglage ne change pas, il avait déjà le coût optimal

Ce que donne la modification des paramètres de recherche :
- La grid x10 seule mène à une mauvaise conclusion : on avait d'abord cru que pondérer ne servait à rien
- Le random uniforme gaspille son budget. Un tirage logarithmique aurait mieux réparti les essais
- Le pas de la tabou (même départ, 20 tours) :

| Pas | Palier L2 trouvé |
|---|---|
| 0.1 | 1.3 à 3 |
| 0.2 | 1.4 à 5 |
| 0.5 | 1.5 à 8.5, et la fin du palier (coût 23 à `w = 9`) |
| 1 | 2 à 8, bords moins précis |

- Tous les pas trouvent `F = 0.767`. Petit pas : bords précis mais avance lentement. Grand pas : va loin mais rate des transitions
- On est parti du pas de 0.2 de l'exemple du cours, trop lent. On garde 0.5, le plus petit qui parcourt tout le palier en 20 tours
- Le nombre de tours (20) et la taille de la liste tabou (10) n'ont pas été optimisés

Avantages et inconvénients :
- Grid : simple et reproductible. Mais le nombre d'essais explose avec le nombre de paramètres, et le pas décide de ce qu'on voit
- Random : ne suppose rien sur la forme de `F`. Mais dépend de la loi de tirage et de la graine
- Hill climbing : très peu d'essais. Mais s'arrête au premier optimum local
- Tabou : peut sortir d'un optimum local. Mais plus d'essais, et plus de réglages (pas, tours, liste)
- Du grossier au fin : peu d'essais au total. Mais si la première passe rate une zone, les suivantes ne la verront jamais
- Sur un `F` en escalier, aucune méthode ne donne « le » meilleur `w`, seulement un intervalle

---

## 3. Test sur d'autres configurations

Les grilles testées (8×8, de (0,0) à (7,7), seuil 25) :
- `deux_murs` : deux colonnes d'obstacles (poids 3 et 8) sur toute la hauteur
- `obstacle_u` : un obstacle en U (poids 9)
- `deux_murs_con4` et `obstacle_u_con4` : les mêmes en connectivité 4
- Mêmes commandes et mêmes `a`, `b`, `c`, `k` que sur `default`

La solution de `default` (L2, `w = 5`) appliquée telle quelle aux autres grilles :

| Grille | `F` avec L2, `w = 5` | Meilleur `F` possible | Écart |
|---|---|---|---|
| default | 0.767 | 0.767 | optimale |
| deux_murs | 0.922 | 0.835 | +0.087 |
| deux_murs_con4 | 1.074 | 0.939 | +0.135, pire que l'A* classique |
| obstacle_u | 0.715 | 0.715 | optimale |
| obstacle_u_con4 | 0.799 | 0.705 | +0.094 |

- Elle reste optimale sur `obstacle_u`, correcte sur `deux_murs` et `obstacle_u_con4`, et fait moins bien que l'A* classique sur `deux_murs_con4`
- Elle reste faisable partout (pas de mission ratée)

En cherchant à nouveau sur chaque grille :

| Grille | Meilleure baseline (`F`) | Meilleur réglage | `w` conseillé | `F` | Gain sur la meilleure baseline |
|---|---|---|---|---|---|
| default | A* (1.000) | L2, `w` de 1.3 à 8.8 | 5 | 0.767 | 23 % |
| deux_murs | Greedy (0.879) | L∞, `w` de 5.8 à 7.2 | 6.5 | 0.835 | 5 % |
| deux_murs_con4 | Dijkstra (0.975) | L∞, `w` de 1.8 à 1.9 | 1.8 | 0.939 | 4 % |
| obstacle_u | Dijkstra (0.965) | L2, `w` de 4.1 à 11 au moins | 7.5 | 0.715 | 26 % |
| obstacle_u_con4 | Greedy L1 (0.705) | L1, `w` de 1.1 à 100 | 10 | 0.705 | 0 % |

- `w` conseillé : une valeur testée vers le milieu du palier, pour garder de la marge

Ce qu'on remarque :
- Le meilleur réglage change avec la grille : pas la même `h`, pas le même intervalle de `w`
- `h` : L2 sur les grilles ouvertes, L∞ derrière les murs, L1 sur le U en connectivité 4
- On garde le coût optimal sur 4 grilles sur 5. Sur `deux_murs` on accepte 21 au lieu de 20.5 pour explorer 10 cases au lieu de 46
- L'A* classique n'est la meilleure baseline que sur `default`
- Sur `obstacle_u_con4`, Greedy avec L1 est déjà optimal : la recherche n'apporte rien

Pourquoi :
- Les obstacles changent la forme de l'escalier. Avec deux murs sur toute la hauteur, on doit de toute façon passer par des cases chères, donc aller tout droit vers la cible coûte peu : Greedy devient bon
- Avec les murs en connectivité 4, l'A* explore 64 cases comme Dijkstra, quelle que soit `h` : l'heuristique ne guide plus rien
- La connectivité change quelle `h` est admissible et précise. En connectivité 4, L1 compte exactement les pas, donc sur le U elle guide parfaitement

Les méthodes de recherche (meilleur `F` / nombre d'essais) :

| Grille | Grid x10 | Random | Grid fine | Hill climbing | Tabou |
|---|---|---|---|---|---|
| default | 1.000 / 12 | 0.767 / 50 | 0.767 / 162 | 0.767 / 5 | 0.767 / 41 |
| deux_murs | 0.879 / 12 | 0.869 / 50 | 0.835 / 162 | 0.946 / 6 | 0.835 / 35 |
| deux_murs_con4 | 1.000 / 18 | 1.012 / 50 | 0.939 / 243 | 1.000 / 4 | 0.966 / 46 |
| obstacle_u | 0.715 / 12 | 0.715 / 50 | 0.715 / 162 | 0.737 / 9 | 0.715 / 41 |
| obstacle_u_con4 | 0.705 / 18 | 0.705 / 50 | 0.705 / 243 | 0.705 / 7 | 0.705 / 58 |

- Le hill climbing reste bloqué sur 3 grilles : `deux_murs`, `obstacle_u` (sur un petit palier de 2.2 à 3, juste avant le vrai qui commence à 4.1) et `deux_murs_con4`
- La tabou sort de ces blocages et retrouve le résultat de la grid fine sur 4 grilles sur 5, avec environ 4 fois moins d'essais
- La tabou rate `deux_murs_con4` : le palier ne fait que 0.1 de large et le pas de 0.5 passe par-dessus

Variation des contraintes et des poids (`sensibilite.py`) :
- On change un seul paramètre à la fois, les autres restent à `k = 2.5`, seuil 25, `a = 0.5`
- Pas besoin de relancer de recherche : `C`, `E` et `M` ne dépendent pas des contraintes, on recalcule juste la faisabilité et `F` à partir des CSV
- `k` : avec `a = 0.5` ça ne change presque rien. Il compte seulement si `a` est petit. Exemple sur `deux_murs` avec `a = 0.2` : `k = 1` donne un coût de 20.5, `k = 1.1` donne 21, `k ≥ 1.2` donne 24
- Seuil : c'est tout ou rien. En dessous de `C*` la mission est impossible (avec un seuil de 20, plus aucune solution sur les deux grilles à murs). Au-dessus, il ne change pas le meilleur réglage
- `a` : le meilleur réglage ne bouge pas entre 0.1 et 0.8 sur 4 grilles sur 5. Seule `deux_murs` change de chemin (24, puis 21, puis 20.5 quand `a` augmente)
- À `a = 1` seul le coût compte, et l'A* classique suffit

Pourquoi `a` change si peu (avec `b = c`) :
- `a` ne change pas les chemins, donc pas `C`, `E` et `M`. Il change seulement la note `F`, et donc peut-être le classement
- Sur `default`, le palier est égal ou meilleur que tous les autres réglages faisables sur les trois mesures : `C = 11, E = 9, M = 26`, contre `11, 26, 36` pour l'A* et `23, 9, 27` pour le chemin à 23. Un réglage qui n'est derrière personne sur aucune mesure gagne quels que soient les poids
- Sur `deux_murs`, aucun réglage n'est meilleur partout : explorer moins oblige à payer un peu plus. C'est là que `a` décide :

| `a` | `default` : `F` du palier / de l'A* | `deux_murs` : gagnant |
|---|---|---|
| 0.2 | 0.627 / 1.000, palier | L∞ `w ≥ 9.5`, coût 24 (`F = 0.704`) |
| 0.5 | 0.767 / 1.000, palier | L∞ `w` 5.8 à 7.2, coût 21 (`F = 0.835`) |
| 0.8 | 0.907 / 1.000, palier | L∞ `w` 5.3 à 5.7, coût 20.5 (`F = 0.948`) |

- Donc `a` ne compte que quand il y a un vrai compromis entre le coût et le reste

Le partage entre `b` (effort) et `c` (mémoire), avec `a = 0.5` :
- Sur les grilles sans murs, il ne change rien : le palier optimal explore le moins et a aussi le plus petit tas. Seule exception : si la mémoire ne compte pas du tout (`c = 0`), d'autres réglages qui explorent autant arrivent à égalité avec lui
- Sur les deux grilles à murs, il change le résultat : explorer moins oblige à garder plus de cases en attente. Sur `deux_murs_con4`, L1 avec `w ≥ 4.6` explore 15 cases mais garde un tas de 19, alors que l'A* explore 64 cases avec un tas de 10
- Si seule la mémoire compte, l'A* classique redevient le meilleur sur ces deux grilles

---

## 4. Gérer la recherche quand la configuration change

- Garder la même définition de `F` (référence = l'A* classique de chaque grille) pour pouvoir comparer les grilles entre elles
- Garder `a`, `b`, `c` fixes : c'est notre préférence entre coût, effort et mémoire, pas une propriété de la grille
- Choisir `h` selon la connectivité : L1 seulement en connectivité 4. Pas besoin de la chercher
- Prendre `w` au milieu du palier et pas au bord : il reste bon si la grille change un peu
- Si on veut un seul réglage pour toutes les grilles, il faut un compromis :
  - L2 avec `w ≈ 5.3` : le meilleur `F` moyen (0.845), mais un peu pire que l'A* sur `deux_murs_con4` (1.020)
  - L∞ avec `w ≈ 1.6` : jamais pire que l'A* (pire `F` = 0.951), mais optimal nulle part
- Si on peut chercher sur chaque nouvelle grille : grid x10 pour trouver la zone, puis tabou depuis le meilleur point, avec un pas plus petit que les paliers
- Pour ne pas chercher à chaque fois : relier le bon `w` à des caractéristiques de la grille (densité d'obstacles, poids, connectivité), à apprendre une fois sur plusieurs grilles

---

## Pour relancer

Depuis `agent/`, avec la grid-api lancée. Les CSV sont dans `agent/resultats/` (un sous-dossier par grille, sauf `default`).

```
python baseline.py             configs/default.json --csv resultats/baseline.csv
python search_grid.py          configs/default.json --w-min 1 --w-max 100000 --factor 10 --csv resultats/etape1_grossier.csv
python search_random.py        configs/default.json --w-min 1 --w-max 100 --draws 50 --csv resultats/etape2_random.csv
python search_grid.py          configs/default.json --w-min 1 --w-max 9 --step 0.1 --csv resultats/etape3_fin.csv
python search_hill_climbing.py configs/default.json --w-max 100 --csv resultats/hc_default.csv
python search_tabou.py         configs/default.json --w-max 100 --csv resultats/tabou_default.csv
python search_tabou.py         configs/default.json --w-max 100 --step 0.1 --csv resultats/tabou_pas_0.1.csv
python sensibilite.py
```

Pour les autres grilles : mêmes commandes avec `configs/<grille>.json` et `--csv resultats/<grille>/<méthode>.csv`.
