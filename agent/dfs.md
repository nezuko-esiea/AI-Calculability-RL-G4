# DFS — parcours en profondeur

## Ce que fait l'algo

DFS explore la grille en allant le plus loin possible dans une direction avant de revenir
en arrière (backtrack). Depuis le départ, il prend un voisin, puis un voisin de ce voisin,
et ainsi de suite, jusqu'à être bloqué ou à trouver la cible. Quand il est bloqué, il
remonte et essaie la branche suivante.


Contrairement au BFS, il n'explore pas la grille couche par couche : une branche est
poussée à fond avant que les autres ne soient regardées. Le premier chemin trouvé vers la
cible n'est donc pas forcément celui qui compte le moins de pas, ni celui qui coûte le
moins.

Trois éléments suffisent :
- une pile LIFO (une simple liste Python) : on ajoute au sommet, on retire par le sommet ;
- un ensemble `seen` : les cases déjà découvertes, pour ne pas les remettre sur la pile ;
- un dictionnaire `parent` : pour chaque case, celle d'où on vient. C'est le fil d'Ariane
qui permet de reconstruire le chemin à la fin.

## Le code

```python
seen = {start}
parent = {}
stack = \[start]

```

La pile démarre avec le départ, déjà marqué comme vu.

```python
while stack:
    node = stack.pop()
    if node == target:
    return build\_path(parent, start, target)
```

On retire la case découverte le plus récemment. Si c'est la cible, terminé.

```python
for neighbor, \_ in client.neighbors(node):
    if neighbor not in seen:
        seen.add(neighbor)
        parent\[neighbor] = node
        stack.append(neighbor)
```

Les voisins viennent de `client.neighbors()`, donc de la grid-api : l'algo n'a pas besoin
de savoir si la connectivité est 4 ou 8, ni où sont les murs. Chaque voisin jamais vu est
marqué, on note son parent, et il est placé au sommet de la pile.

Le `\_` est le coût du déplacement, renvoyé par l'API mais jeté : DFS ne regarde pas les coûts.

```python
def build\_path(parent, start, target):
    path = \[target]

    while path\[-1] != start:
        path.append(parent\[path\[-1]])
        path.reverse()
        return path
```

## En quoi c'est du DFS

Tout tient dans la pile utilisée en LIFO. Le `pop()` sort toujours la case découverte le
plus récemment, ce qui force l'exploration en profondeur : on descend une branche jusqu'au
bout avant de revenir en arrière pour explorer les autres. C'est cette discipline qui
définit l'algorithme.

Remplacer `pop()` par `popleft()` sur une `collections.deque` donnerait une file, donc un
BFS. La structure de données est ce qui définit l'algorithme.

## Terminaison

Le marquage `seen` est fait à la découverte, pas à la sortie de la pile. Chaque case n'est
donc empilée qu'une seule fois, ce qui garantit que l'algorithme termine même sur une
grille avec des cycles.

## Organisation des fichiers

Même découpage que pour BFS et A\\\* : `client.py` contient toutes les requêtes HTTP et est
partagé par le groupe, `dfs.py` contient seulement l'algo, `main.py` est le script à lancer.

```
cd grid\_api
docker run --rm -p 8000:8000 grid-api # terminal 1
python main.py # terminal 2
```

## Ce qu'on peut attendre sur la config par défaut

DFS ne garantit ni le nombre minimal de pas ni le coût minimal. Sur la config par défaut,
le chemin trouvé dépend de l'ordre dans lequel `client.neighbors()` renvoie les voisins :
il peut partir dans une direction et serpenter longtemps avant d'atteindre la cible. Le
nombre de pas peut donc être nettement supérieur aux 7 pas de la diagonale, et le coût
total peut dépasser le seuil de 25 comme il peut aussi passer dessous. Le résultat exact
dépend de l'ordre des voisins, à vérifier en lançant l'algo.

C'est la différence essentielle avec BFS : BFS est optimal en nombre de mouvements, DFS
ne l'est pas, et aucun des deux ne tient compte du coût. La comparaison des deux sur la
même config est donc utile pour illustrer cette limite.