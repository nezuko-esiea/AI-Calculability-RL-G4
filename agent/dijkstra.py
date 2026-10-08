"""
Algo Dijkstra : trouver le chemin le moins cher entre le départ et la cible.

En gros
    Pour chaque case on garde g = ce qu'on a déjà payé depuis le départ.
    A chaque tour on prend la case qui a le plus petit g, cad la case la 
    moins chère à atteindre parmi celles qu'on connaît. Dijkstra ne
    regarde PAS où est la cible : il s'étend autour du départ en cercles de
    coût croissant, jusqu'à tomber sur la cible.
    (C'est A* avec h = 0 : on enlève l'estimation, il reste seulement g.)

Comment ça tourne
    1. On met le départ dans la file avec g = 0.
    2. On sort la case qui a le plus petit g.
    3. Si c'est la cible on s'arrête, et on remonte les parents pour avoir le chemin.
       A ce moment g[cible] est forcément le coût minimal : toutes les cases
       moins chères ont déjà été traitées et les coûts ne sont jamais négatifs.
    4. Sinon on demande ses voisins à la grid-api. Si en passant par la case
       actuelle un voisin coûte moins cher qu'avant, on change son g et son
       parent, et on le met dans la file.
    5. On recommence au 2 jusqu'à ce que la file soit vide.

Les variables
    g        : pour chaque case, le meilleur coût trouvé depuis le départ
    parent   : pour chaque case, la case d'où on vient (sert à refaire le chemin)
    explored : les cases déjà traitées (leur g est définitif)
    queue    : la file de priorité avec des tuples (g, case), gérée avec heapq
"""
import heapq


def search(start, target, client):
    """Renvoie le chemin [start, ..., target], ou None s'il n'y en a pas."""
    g = {start: 0}
    parent = {}
    explored = set()
    queue = [(0, start)]

    while queue:
        cost, node = heapq.heappop(queue)   # la case au plus petit g
        if node in explored:
            continue
        explored.add(node)

        if node == target:
            return build_path(parent, start, target)

        for neighbor, step_cost in client.neighbors(node):
            new_g = g[node] + step_cost
            if neighbor not in g or new_g < g[neighbor]:
                g[neighbor] = new_g
                parent[neighbor] = node
                heapq.heappush(queue, (new_g, neighbor))

    return None


def build_path(parent, start, target):
    """Remonte les parents depuis la cible jusqu'au départ."""
    path = [target]
    while path[-1] != start:
        path.append(parent[path[-1]])
    path.reverse()
    return path