"""
Algo BFS (parcours en largeur) : trouver le chemin qui compte le moins de pas
entre le départ et la cible.

L'idée
    On explore la grille couche par couche. Depuis le départ on regarde toutes
    les cases à 1 pas, puis toutes celles à 2 pas, puis celles à 3 pas, etc.
    Comme on traite les cases dans l'ordre où on les découvre, la première fois
    qu'on tombe sur la cible c'est forcément par un chemin au nombre de pas
    minimal.

Comment ça tourne
    1. On met le départ dans la file et on le marque comme vu.
    2. On sort la case qui attend depuis le plus longtemps (le devant de la file).
    3. Si c'est la cible on s'arrête, et on remonte les parents pour avoir le chemin.
    4. Sinon on demande ses voisins à la grid-api. Chaque voisin jamais vu est
       marqué, on note son parent, et on le met au bout de la file.
    5. On recommence au 2 jusqu'à ce que la file soit vide.

Les variables
    seen     : les cases déjà découvertes, pour ne pas les remettre dans la file
    parent   : pour chaque case, la case d'où on vient (sert à refaire le chemin)
    queue    : la file d'attente FIFO, gérée avec collections.deque

Ce que la fonction prend et renvoie
    search(start, target, client) renvoie la liste des cases du chemin, du départ
    jusqu'à la cible. Une case = un tuple (ligne, colonne).
    Les requêtes vers la grid-api sont dans client.py, pas ici.

A savoir
    BFS ne regarde pas les coûts. client.neighbors() renvoie des couples
    (case, coût) mais on jette le coût : c'est le `_` dans la boucle. Du coup
    BFS est optimal en nombre de mouvements, mais il peut être très mauvais en
    coût total. Sur la config par défaut il prend la diagonale (7 pas, le
    minimum) et se fait sortir par le seuil parce que les gros obstacles sont
    justement sur la diagonale. Voir bfs.md pour le détail du calcul.

    La file est ce qui fait que c'est du BFS : popleft() sort toujours la case
    découverte le plus anciennement, donc on avance couche par couche. Avec
    pop() à la place on aurait une pile, donc un DFS.
"""
import collections


def search(start, target, client):
    """Renvoie le chemin [start, ..., target], ou None s'il n'y en a pas."""
    seen = {start}                              # cases déjà découvertes
    parent = {}                                 # parent[case] = la case d'où on est venu
    queue = collections.deque([start])          # file FIFO des cases à traiter

    while queue:
        node = queue.popleft()                  # la case découverte le plus anciennement

        if node == target:
            return build_path(parent, start, target)

        for neighbor, _ in client.neighbors(node):      # le coût ne sert pas à BFS
            if neighbor not in seen:
                seen.add(neighbor)
                parent[neighbor] = node
                queue.append(neighbor)

    return None


def build_path(parent, start, target):
    """Remonte les parents depuis la cible jusqu'au départ."""
    path = [target]
    while path[-1] != start:
        path.append(parent[path[-1]])
    path.reverse()
    return path
