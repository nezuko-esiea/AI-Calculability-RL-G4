# BFS — parcours en largeur

## Ce que fait l'algo

BFS explore la grille couche par couche : depuis le départ, il visite toutes les cases à
1 pas, puis toutes celles à 2 pas, et ainsi de suite. Comme il traite les cases dans
l'ordre où il les découvre, le premier chemin qu'il trouve vers la cible est forcément
celui qui compte le moins de pas.

Trois éléments suffisent :

- une file FIFO (`collections.deque`) : on ajoute au bout, on retire par le devant ;
- un ensemble `seen` : les cases déjà découvertes, pour ne pas les remettre en file ;
- un dictionnaire `parent` : pour chaque case, celle d'où on vient. C'est le fil d'Ariane
  qui permet de reconstruire le chemin à la fin.

## Le code

```python
seen = {start}
parent = {}
queue = collections.deque([start])
```

La file démarre avec le départ, déjà marqué comme vu.

```python
while queue:
    node = queue.popleft()
    if node == target:
        return build_path(parent, start, target)
```

On sort la case qui attend depuis le plus longtemps. Si c'est la cible, terminé.

```python
    for neighbor, _ in client.neighbors(node):
        if neighbor not in seen:
            seen.add(neighbor)
            parent[neighbor] = node
            queue.append(neighbor)
```

Les voisins viennent de `client.neighbors()`, donc de la grid-api : l'algo n'a pas besoin
de savoir si la connectivité est 4 ou 8, ni où sont les murs. Chaque voisin jamais vu est
marqué, on note son parent, et il part au bout de la file.

Le `_` est le coût du déplacement, renvoyé par l'API mais jeté : BFS compte des pas, pas
des coûts.

```python
def build_path(parent, start, target):
    path = [target]
    while path[-1] != start:
        path.append(parent[path[-1]])
    path.reverse()
    return path
```

On remonte de la cible vers le départ en suivant les parents, puis on inverse. Même
fonction que dans `astar.py`.

## En quoi c'est du BFS

Tout tient dans le `deque` utilisé en FIFO. Le `popleft()` sort toujours la case
découverte le plus anciennement, ce qui force l'exploration couche par couche : toutes
les cases à 1 pas avant celles à 2 pas, celles à 2 avant celles à 3. C'est cette
discipline qui garantit le chemin le plus court en nombre de pas.

Remplacer `popleft()` par `pop()` donnerait une pile, donc un DFS. La structure de
données est ce qui définit l'algorithme.

## Organisation des fichiers

Même découpage que pour A* : `client.py` contient toutes les requêtes HTTP et est partagé
par le groupe, `bfs.py` contient seulement l'algo, `main.py` est le script à lancer.

```
cd grid_api
docker run --rm -p 8000:8000 grid-api   # terminal 1
python main.py                          # terminal 2
```

## Pourquoi la mission échoue avec un seuil de 25

Sur la config par défaut, BFS trouve un chemin de 7 pas :

```
(0,0) → (1,1) → (2,2) → (3,3) → (4,4) → (5,5) → (6,6) → (7,7)
```

C'est le **seul** chemin de 7 pas possible. En connectivité 8, un pas fait varier la
ligne et la colonne de 1 au maximum ; il faut +7 sur chacune, donc les 7 pas doivent tous
être diagonaux. Passer par le côté coûterait 14 pas.

Problème : la diagonale est exactement là où sont les gros obstacles. Le coût d'un pas
vaut `edge_weight × obstacle_value` (une multiplication, pas une addition), avec
`edge_weight` à 1,5 en diagonale.

| Pas | Poids de la case | Coût | Total |
|---|---|---|---|
| → (1,1) | 5 | 1,5 × 5 = 7,5 | 7,5 |
| → (2,2) | 5 | 1,5 × 5 = 7,5 | 15,0 |
| → (3,3) | 8 | 1,5 × 8 = 12,0 | **27,0** |

Le seuil de 25 est franchi au 3ᵉ pas et la mission passe en `failed`. Si elle allait au
bout, le chemin complet coûterait 43,5.

Ce n'est pas un bug : BFS ignore volontairement les coûts renvoyés par l'API. Il est donc
optimal en nombre de mouvements et peut être arbitrairement mauvais en coût — c'est
précisément sa limite, et la raison d'être des algorithmes pondérés.

## Note sur client.py

`follow()` a besoin d'un garde-fou que la version d'origine n'avait pas : quand la mission
se termine avant la fin du chemin, la grid-api refuse le déplacement suivant et renvoie
`{"error": ...}` au lieu de `{"move_cost": ...}`, ce qui faisait planter `follow()` avec
un `KeyError: 'move_cost'`.

Le cas ne se présente jamais avec A*, qui arrive au bout. Il se présente systématiquement
avec BFS, qui se fait sortir au 3ᵉ pas sur 7. `follow()` s'arrête maintenant dès que le
statut de la mission n'est plus `running`.
