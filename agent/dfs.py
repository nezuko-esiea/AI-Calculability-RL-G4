"""
Algo DFS (parcours en profondeur) : trouver un chemin entre le départ et la cible.

L'idée
    On explore la grille en allant le plus loin possible dans une direction avant
    de revenir en arrière. Depuis le départ on prend un voisin, puis un voisin de
    ce voisin, etc., jusqu'à être bloqué ou à trouver la cible. Quand on est
    bloqué, on remonte (backtrack) et on essaie la branche suivante.

Comment ça tourne
    1. On met le départ sur la pile et on le marque comme vu.
    2. On sort la case du dessus de la pile (la dernière découverte).
    3. Si c'est la cible on s'arrête, et on remonte les parents pour avoir le chemin.
    4. Sinon on demande ses voisins à la grid-api. Chaque voisin jamais vu est
       marqué, on note son parent, et on le met sur la pile.
    5. On recommence au 2 jusqu'à ce que la pile soit vide.

Les variables
    seen     : les cases déjà découvertes, pour ne pas les remettre sur la pile
    parent   : pour chaque case, la case d'où on vient (sert à refaire le chemin)
    stack    : la pile LIFO, une simple liste Python

Ce que la fonction prend et renvoie
    search(start, target, client) renvoie la liste des cases du chemin, du départ
    jusqu'à la cible. Une case = un tuple (ligne, colonne).
    Les requêtes vers la grid-api sont dans client.py.

A savoir
    Comme BFS, DFS ne regarde pas les coûts : client.neighbors() renvoie des couples
    (case, coût) et on jette le coût avec le `_`. Du coup le chemin trouvé n'est
    en général PAS le plus court en nombre de pas, ni le moins coûteux. DFS trouve
    un chemin, pas forcément le meilleur.

    La pile est ce qui fait que c'est du DFS : pop() sort toujours la case
    découverte le plus récemment, donc on plonge dans une branche avant de revenir.
    Avec popleft() à la place on aurait une file, donc un BFS.

    Le marquage `seen` est fait à la découverte, pas à la sortie de la pile. C'est
    ce qui garantit que chaque case n'est empilée qu'une fois, et donc que
    l'algorithme termine même sur une grille avec des cycles.
"""


def search(start, target, client):
    """Renvoie un chemin [start, ..., target], ou None s'il n'y en a pas."""
    seen = {start}                              # cases déjà découvertes
    parent = {}                                 # parent[case] = la case d'où on est venu
    stack = [start]                             # pile LIFO des cases à traiter

    while stack:
        node = stack.pop()                      # la case découverte le plus récemment

        if node == target:
            return build_path(parent, start, target)

        for neighbor, _ in client.neighbors(node):      # le coût ne sert pas à DFS
            if neighbor not in seen:
                seen.add(neighbor)
                parent[neighbor] = node
                stack.append(neighbor)

    return None


def build_path(parent, start, target):
    """Remonte les parents depuis la cible jusqu'au départ."""
    path = [target]
    while path[-1] != start:
        path.append(parent[path[-1]])
    path.reverse()
    return path