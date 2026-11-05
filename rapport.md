Groupe 4 :
Boudjema Dyhia,
Vallet Jules,
Da Gama Clément,
Ding Célivé,
Pedra Léa


# A* pondéré : recherche des meilleurs paramètres

Grille de base : `default.json`, 8×8, connectivité 8, départ (0,0), cible (7,7), seuil de mission 25.



## 1. Modélisation

Ce qu'on cherche :
- Les variables `w` (le poids de l'heuristique) et `h` (L1, L2 ou L∞)
- La grille (taille, connectivité, obstacles, départ, cible, seuil) est fixée, on ne l'optimise pas
- On mesure le coût du chemin `C`, le nombre de cases explorées `E` et la taille max du tas `M`
- On minimise `F = 0.5·C/C* + 0.25·E/E* + 0.25·M/M*`
- `C*`, `E*`, `M*` : les résultats de l'A* classique (`w = 1`, L2) sur la même grille

Nos choix :
- On divise par l'A* pour que les 3 mesures soient à la même échelle. Sinon c'est celle qui a les plus gros chiffres qui décide. Exemple sur `deux_murs` avec `a = 0.8` : sans diviser, Greedy (coût 24) battrait l'A* (coût 20.5), juste parce que `E` se compte en dizaines de cases
- On prend `E` et pas le temps : le temps changeait beaucoup d'un lancement à l'autre pour le même calcul, `E` ne bouge pas
- `a = 0.5` : le coût du chemin compte autant que l'effort et la mémoire réunis
- L'A* comme référence : il donne le coût optimal, et c'est notre algo sans réglage (`w = 1`)

Les contraintes (une solution qui en viole une a un score infini) :
- `1 ≤ w ≤ 100` : en dessous de 1 on va vers Dijkstra, au-dessus de 100 plus rien ne change
- `h` admissible : pas de L1 en connectivité 8, elle compte une diagonale 2 alors qu'elle coûte 1.5
- `C ≤ 2.5 × C*` : on accepte un chemin plus cher si on explore beaucoup moins
- `C < 25` : le seuil de la mission
- `T ≤ 3 s` : garde-fou, jamais atteint



## 2. Configuration par défaut

Notre stratégie, du grossier au fin :
- Grid x10 de 1 à 100 000 : au-delà de 100, plus rien ne change
- Random entre 1 et 100 : la zone utile est en dessous de 10
- Grid fine au pas de 0.1 entre 1 et 9 : on trouve les bords exacts
- Hill climbing et tabou (départ `w = 1`, pas de 0.5) : même chose avec moins d'essais


Ce qu'on trouve :
- Dijkstra (`w = 0`) : coût 11, 62 cases explorées, tas de 22, `F = 1.249`
- A* classique (`w = 1`) : coût 11, 26 cases, tas de 36, `F = 1`
- Greedy (`w` très grand) : coût 43.5, mission ratée
- Notre meilleur réglage, L2 avec `w` entre 1.3 et 8.8 : coût 11, 9 cases, tas de 26, `F = 0.767`
- On garde le coût optimal, mais on explore 9 cases au lieu de 26 et le tas passe de 36 à 26
- Ce n'est pas un `w` précis mais un intervalle : tous les `w` entre 1.3 et 8.8 donnent le même chemin


Pourquoi on obtient ça :
- À `w = 1`, beaucoup de cases ont le même `f` et l'A* les explore toutes. Avec un peu plus de poids sur `h` (`w = 1.1`), il va directement vers la cible
- Avec trop de poids (`w ≥ 9`), le chemin devient plus cher (23), puis on tombe sur Greedy (43.5, mission ratée)
- `F` varie en escalier : il n'y a que quelques chemins possibles, d'où les intervalles


Comment s'en sortent les méthodes :
- Grid x10 (12 essais) : `F = 1`, elle saute de 1 à 10 et rate la bonne zone
- Random (50 essais) : `F = 0.767`, mais 45 tirages sur 50 tombent là où la mission échoue
- Grid fine (162 essais) : `F = 0.767`, avec les bords exacts du palier
- Hill climbing (5 essais) : `F = 0.767`, mais il s'arrête dès qu'il arrive sur le palier, sans savoir où il finit
- Tabou (41 essais) : `F = 0.767`, et elle trouve aussi les bords du palier, avec 4 fois moins d'essais que la grid fine


Si on change la fonction de coût :
- Avec le temps dans `F`, le classement dépendait du hasard du chrono, d'où le passage à `E`
- Changer `a` ne change rien sur cette grille (expliqué en section 3)


Si on change les paramètres de recherche :
- Le pas de la tabou : 0.1 et 0.2 sont précis mais trop lents, 1 va loin mais rate des détails. On garde 0.5, le plus petit qui parcourt tout le palier en 20 tours
- On est parti du pas de 0.2 de l'exemple du cours. Le nombre de tours et la taille de la liste tabou n'ont pas été optimisés

Avantages et inconvénients :
- Grid : simple, mais coûte cher, et le pas décide de ce qu'on voit
- Random : ne suppose rien, mais gaspille si on tire au mauvais endroit
- Hill climbing : très rapide, mais s'arrête au premier optimum local
- Tabou : peut sortir d'un optimum local, mais plus d'essais et plus de réglages



## 3. Autres configurations

Grilles testées (8×8, de (0,0) à (7,7), seuil 25) : `deux_murs` (deux colonnes d'obstacles sur toute la hauteur), `obstacle_u` (un U), et les deux en connectivité 4 (`_con4`).

Notre solution de `default` (L2, `w = 5`) appliquée aux autres grilles, comparée au meilleur réglage de chaque grille :
- `deux_murs` : `F = 0.922`, alors que le meilleur (L∞, `w` de 5.8 à 7.2) fait 0.835
- `deux_murs_con4` : `F = 1.074`, alors que le meilleur (L∞, `w` de 1.8 à 1.9) fait 0.939
- `obstacle_u` : `F = 0.715`, c'est déjà le meilleur (L2, `w` de 4.1 à 11)
- `obstacle_u_con4` : `F = 0.799`, alors que le meilleur (L1, `w` de 1.1 à 100) fait 0.705



Ce qu'on a vu :
- Notre solution marche partout, mais n'est optimale que sur `default` et `obstacle_u`. Sur les deux murs en connectivité 4, elle est même moins bonne que l'A*
- Chaque grille a son propre réglage : L2 sur les grilles ouvertes, L∞ derrière les murs, L1 sur le U en connectivité 4 (elle y compte exactement les pas)
- L'A* n'est la meilleure référence que sur `default`. Sur les autres grilles, Greedy ou Dijkstra font mieux : avec deux murs, on doit traverser de toute façon, donc aller tout droit coûte peu
- Le hill climbing reste bloqué sur 3 grilles. La tabou s'en sort sur 2 d'entre elles, mais rate `deux_murs_con4` : le palier (0.1 de large) est plus petit que son pas (0.5)


Quand on change les poids et les contraintes (`sensibilite.py`) :
- `k` ne compte que si `a` est petit. Le seuil : en dessous du coût optimal la mission est impossible, sinon il ne change rien
- `a` ne change presque rien : le meilleur réglage est le même entre 0.1 et 0.8 sur 4 grilles sur 5
- Pourquoi : sur `default`, notre palier est meilleur ou égal aux autres sur les 3 mesures (`C = 11, E = 9, M = 26`, contre `11, 26, 36` pour l'A*). Un réglage qui n'est battu sur aucune mesure gagne quels que soient les poids
- Sur `deux_murs`, c'est différent : pour explorer moins, il faut payer un peu plus. Là, c'est `a` qui décide : avec `a = 0.2` on prend un chemin à 24 (L∞, `w ≥ 9.5`), avec `a = 0.5` un chemin à 21 (`w` de 5.8 à 7.2), avec `a = 0.8` un chemin à 20.5 (`w` de 5.3 à 5.7)
- `b` et `c` : ça ne change rien sur les grilles ouvertes. Sur les grilles à murs, explorer moins demande un plus gros tas, donc le partage entre `b` et `c` change le réglage choisi



## 4. Si la configuration change

- Garder la même `F` et les mêmes `a`, `b`, `c` pour pouvoir comparer les grilles. Revoir `b` et `c` seulement si la priorité change (par exemple peu de mémoire), surtout sur les grilles à murs
- Choisir `h` selon la connectivité : L1 seulement en connectivité 4
- Prendre `w` au milieu du palier, pas au bord, pour qu'il reste bon si la grille change un peu
- Pour un seul réglage partout : L2 avec `w ≈ 5.3` (meilleur en moyenne) ou L∞ avec `w ≈ 1.6` (jamais pire que l'A*)
- Sinon, relancer une recherche : grid x10 pour trouver la zone, puis tabou depuis le meilleur point



## Pour relancer

Depuis `agent/`, avec la grid-api lancée. Les résultats sont dans `agent/resultats/`.

```
python baseline.py             configs/default.json --csv resultats/baseline.csv
python search_grid.py          configs/default.json --w-min 1 --w-max 100000 --factor 10 --csv resultats/etape1_grossier.csv
python search_random.py        configs/default.json --w-min 1 --w-max 100 --draws 50 --csv resultats/etape2_random.csv
python search_grid.py          configs/default.json --w-min 1 --w-max 9 --step 0.1 --csv resultats/etape3_fin.csv
python search_hill_climbing.py configs/default.json --w-max 100 --csv resultats/hc_default.csv
python search_tabou.py         configs/default.json --w-max 100 --csv resultats/tabou_default.csv
python sensibilite.py
```

Pour les autres grilles : mêmes commandes avec `configs/<grille>.json`.
