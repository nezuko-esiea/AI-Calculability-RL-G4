"""
Algo Greedy (best-first) : aller vers la case qui a l'air la plus proche de la cible.

L'idée
    Pour chaque case on regarde seulement h :
      - h = une estimation de ce qu'il reste jusqu'à la cible (juste une
            distance, elle ne regarde pas les obstacles)
    A chaque tour on prend la case qui a le plus petit h.
    La différence avec A* : il n'y a pas de g. Greedy ne compte pas ce qu'il a
    déjà payé, donc le coût des obstacles ne change pas son choix.

Comment ça tourne
    1. On met le départ dans la file.
    2. On sort la case qui a le plus petit h.
    3. Si c'est la cible on s'arrête, et on remonte les parents pour avoir le chemin.
    4. Sinon on demande ses voisins à la grid-api. Chaque voisin qu'on n'a jamais
       vu est noté comme vu, on retient son parent, et on le met dans la file.
    5. On recommence au 2 jusqu'à ce que la file soit vide.

Les variables
    parent : pour chaque case, la case d'où on vient (sert à refaire le chemin)
    seen   : les cases déjà vues (on ne les remet pas dans la file)
    queue  : la file de priorité avec des tuples (h, case), gérée avec heapq

Ce que la fonction prend et renvoie
    search(start, target, client, metric) renvoie la liste des cases du chemin,
    du départ jusqu'à la cible. Une case = un tuple (ligne, colonne).
    Les requêtes vers la grid-api sont dans client.py, pas ici.

A savoir
    Greedy trouve un chemin s'il y en a un, et il explore souvent très peu de
    cases. Mais le chemin n'est pas forcément le moins cher : comme il ne
    regarde pas les coûts, il peut traverser un obstacle qui est sur la ligne
    droite vers la cible.
"""
import heapq


def search(start, target, client, metric="euclidean"):
    """Renvoie le chemin [start, ..., target], ou None s'il n'y en a pas."""
    parent = {}             # parent[case] = la case d'où on est venu
    seen = {start}
    queue = [(client.distance(start, target, metric), start)]   # (h, case)

    while queue:
        h, node = heapq.heappop(queue)      # la case au plus petit h

        if node == target:
            return build_path(parent, start, target)

        for neighbor, cost in client.neighbors(node):   # cost n'est pas utilisé par Greedy
            if neighbor not in seen:
                seen.add(neighbor)
                parent[neighbor] = node
                h = client.distance(neighbor, target, metric)   # coût estimé jusqu'à la cible
                heapq.heappush(queue, (h, neighbor))

    return None


def build_path(parent, start, target):
    """Remonte les parents depuis la cible jusqu'au départ."""
    path = [target]
    while path[-1] != start:
        path.append(parent[path[-1]])
    path.reverse()
    return path
