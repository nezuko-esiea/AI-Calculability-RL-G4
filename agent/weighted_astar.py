"""
Algo A* pondéré : comme A*, mais on donne plus de poids à l'estimation h.

L'idée
    Pour chaque case on calcule f = g + W * h :
      - g = ce qu'on a déjà payé depuis le départ pour arriver sur la case
      - h = une estimation de ce qu'il reste jusqu'à la cible (juste une
            distance, elle ne regarde pas les obstacles)
      - W = le poids qu'on donne à h (le paramètre weight)
    A chaque tour on prend la case qui a le plus petit f.
    Plus W est grand, plus l'algo fonce vers la cible : il explore moins de
    cases, mais le chemin peut coûter plus cher que le meilleur.

Ce que ça donne selon W
    W = 0       f = g             c'est Dijkstra
    W = 1       f = g + h         c'est A* normal
    W > 1       h compte plus     plus rapide, chemin pas forcément le moins cher
    W très grand                  ça ressemble à Greedy

Comment ça tourne
    1. On met le départ dans la file avec g = 0.
    2. On sort la case qui a le plus petit f.
    3. Si c'est la cible on s'arrête, et on remonte les parents pour avoir le chemin.
    4. Sinon on demande ses voisins à la grid-api. Si en passant par la case
       actuelle un voisin coûte moins cher qu'avant, on change son g et son
       parent, et on le met dans la file avec f = g + W * h.
    5. On recommence au 2 jusqu'à ce que la file soit vide.
    C'est exactement A*, la seule différence est le W * h à l'étape 4.

Les variables
    g        : pour chaque case, le meilleur coût trouvé depuis le départ
    parent   : pour chaque case, la case d'où on vient (sert à refaire le chemin)
    explored : les cases déjà traitées
    queue    : la file de priorité avec des tuples (f, case), gérée avec heapq
    steps    : pour chaque case, le nombre de pas depuis le départ

Les métriques (renvoyées dans le dictionnaire stats)
    explored  : le nombre de cases sorties de la file
    max_depth : la plus grande profondeur explorée, en pas depuis le départ
    max_queue : la plus grande taille de la file pendant la recherche

Ce que la fonction prend et renvoie
    search(start, target, client, metric, weight) renvoie le chemin (la liste
    des cases du départ jusqu'à la cible) et le dictionnaire stats.
    Une case = un tuple (ligne, colonne). Par défaut weight = 1.5.
    Les requêtes vers la grid-api sont dans client.py, pas ici.

A savoir
    Si h ne surestime jamais le vrai coût restant ("euclidean" chez nous), le
    chemin trouvé coûte au plus W fois le coût du meilleur chemin.
    Par exemple avec W = 1.5, si le meilleur chemin coûte 11, celui qu'on
    trouve coûte au plus 16.5.
"""
import heapq



def search(start, target, client, metric="euclidean", weight=1.5):
    """Renvoie (chemin, stats). Le chemin vaut None s'il n'y en a pas."""
    g = {start: 0}          # coût réel depuis le départ
    parent = {}             # parent[case] = la case d'où on est venu
    explored = set()
    queue = [(weight * client.distance(start, target, metric), start)]   # (f, case)
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
                heapq.heappush(queue, (new_g + weight * h, neighbor))   # f = g + W * h
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
