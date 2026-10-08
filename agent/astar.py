"""
Algo A* : trouver le chemin le moins cher entre le départ et la cible.

L'idée
    Pour chaque case on calcule f = g + h :
      - g = ce qu'on a déjà payé depuis le départ pour arriver sur la case
      - h = une estimation de ce qu'il reste jusqu'à la cible (juste une
            distance, elle ne regarde pas les obstacles)
    A chaque tour on prend la case qui a le plus petit f.

Comment ça tourne
    1. On met le départ dans la file avec g = 0.
    2. On sort la case qui a le plus petit f.
    3. Si c'est la cible on s'arrête, et on remonte les parents pour avoir le chemin.
    4. Sinon on demande ses voisins à la grid-api. Si en passant par la case
       actuelle un voisin coûte moins cher qu'avant, on change son g et son
       parent, et on le met dans la file.
    5. On recommence au 2 jusqu'à ce que la file soit vide.

Les variables
    g        : pour chaque case, le meilleur coût trouvé depuis le départ
    parent   : pour chaque case, la case d'où on vient (sert à refaire le chemin)
    explored : les cases déjà traitées
    queue    : la file de priorité avec des tuples (f, case), gérée avec heapq
    steps    : pour chaque case, le nombre de pas depuis le départ
    max_depth : la plus grande profondeur qu'on a explorée
    max_queue : la plus grande taille de la file pendant la recherche

    search(start, target, client, metric) renvoie le chemin et un dictionnaire
    stats avec explored, max_depth et max_queue.

Ce que la fonction prend et renvoie
    search(start, target, client, metric) renvoie la liste des cases du chemin,
    du départ jusqu'à la cible. Une case = un tuple (ligne, colonne).
    Les requêtes vers la grid-api sont dans client.py, pas ici.

A savoir sur l'heuristique
    A* donne le meilleur chemin seulement si h n'est jamais plus grand que le
    vrai coût restant. On a pris "euclidean" parce que ça marche en 4 et en 8
    voisins. "manhattan" marche seulement en 4 voisins : en 8, une diagonale
    coûte 1.5 mais manhattan la compte 2, donc elle surestime.
"""
import heapq


def search(start, target, client, metric="euclidean"):
    """Renvoie le chemin [start, ..., target], ou None s'il n'y en a pas."""
    g = {start: 0}          # coût réel depuis le départ
    parent = {}             # parent[case] = la case d'où on est venu
    explored = set()
    queue = [(client.distance(start, target, metric), start)]   # (f, case)
    steps = {start: 0}
    max_depth = 0
    max_queue = 1
    while queue:
        f, node = heapq.heappop(queue)      # la case au plus petit f
        if node in explored:
            continue
        explored.add(node)
        max_depth = max(max_depth, steps[node])
        if node == target:
            stats = {"explored": len(explored), "max_depth": max_depth, "max_queue": max_queue}
            return build_path(parent, start, target), stats

        for neighbor, cost in client.neighbors(node):
            new_g = g[node] + cost
            if neighbor not in g or new_g < g[neighbor]:
                g[neighbor] = new_g
                parent[neighbor] = node
                steps[neighbor] = steps[node] + 1   
                h = client.distance(neighbor, target, metric)   # coût estimé jusqu'à la cible
                heapq.heappush(queue, (new_g + h, neighbor))
                max_queue = max(max_queue, len(queue)) 
    stats = {"explored": len(explored), "max_depth": max_depth, "max_queue": max_queue}
    return None, stats


def build_path(parent, start, target):
    """Remonte les parents depuis la cible jusqu'au départ."""
    path = [target]
    while path[-1] != start:
        path.append(parent[path[-1]])
    path.reverse()
    return path
