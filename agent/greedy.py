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
    depth  : pour chaque case, son nombre de pas depuis le départ dans l'arbre
             d'exploration
    queue  : la file de priorité avec des tuples (h, case), gérée avec heapq

Ce que la fonction prend et renvoie
    search(start, target, client, metric) renvoie la liste des cases du chemin,
    du départ jusqu'à la cible. Une case = un tuple (ligne, colonne).
    Les requêtes vers la grid-api sont dans client.py, pas ici.

Les métriques
    search() accepte un dictionnaire `stats` optionnel et le remplit pendant la
    recherche. Deux métriques sont relevées ici, les autres (pas, coût, temps,
    mission) sont calculées par le script de comparaison :

      cases_explorees      un compteur, incrémenté à chaque case sortie de la file
      profondeur_exploree  depth[voisin] = depth[case] + 1, on garde le maximum

    Le paramètre est optionnel, donc les appels existants comme
    `greedy.search(start, target, client)` continuent de fonctionner tels quels.

A savoir
    Greedy trouve un chemin s'il y en a un, et il explore souvent très peu de
    cases. Mais le chemin n'est pas forcément le moins cher : comme il ne
    regarde pas les coûts, il peut traverser un obstacle qui est sur la ligne
    droite vers la cible.

test plusieurs config (deux_murs et obstacle) :
    Greedy trie par h seul, la distance géométrique jusqu'à la cible. Il ne
    demande jamais le coût d'un déplacement, donc sa trajectoire ne dépend que
    de la position du départ et de la cible, pas du terrain.

    Sur obstacle_u il va tout droit de (3,0) à (3,7) et traverse le fond du U
    en (3,5) qui pèse 9 : six pas à 1 plus un pas à 9 font exactement 15,0 pour
    un seuil de 15, et la mission échoue puisque l'API exige un coût
    strictement inférieur.

    Sur deux_murs il prend la diagonale de (0,0) à (7,7) et franchit les deux
    murs en diagonale, donc au tarif fort : 1,5 x 3 puis 1,5 x 8, pour un total
    de 24,0 qui passe de justesse sous le seuil de 25.

    Dans les deux cas : 8 cases explorées, profondeur 7, 7 pas. Des chiffres
    identiques malgré des obstacles différents. Le travail de Greedy est
    constant, seule sa facture varie — il réussit ou échoue selon que
    l'obstacle se trouve ou non sur sa ligne droite.

"""
import heapq


def search(start, target, client, metric="euclidean", stats=None):
    """Renvoie le chemin [start, ..., target], ou None s'il n'y en a pas."""
    if stats is None:
        stats = {}
    stats["cases_explorees"] = 0
    stats["profondeur_exploree"] = 0

    parent = {}             # parent[case] = la case d'où on est venu
    seen = {start}
    depth = {start: 0}      # nombre de pas depuis le départ dans l'arbre d'exploration
    queue = [(client.distance(start, target, metric), start)]   # (h, case)

    while queue:
        _, node = heapq.heappop(queue)      # la case au plus petit h
        stats["cases_explorees"] += 1

        if node == target:
            return build_path(parent, start, target)

        for neighbor, cost in client.neighbors(node):   # cost n'est pas utilisé par Greedy
            if neighbor not in seen:
                seen.add(neighbor)
                parent[neighbor] = node
                depth[neighbor] = depth[node] + 1
                if depth[neighbor] > stats["profondeur_exploree"]:
                    stats["profondeur_exploree"] = depth[neighbor]
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

# greedy config obstacle_u.json : {'cases_explorees': 8, 'profondeur_exploree': 7} chemin : [(3, 0), (3, 1), (3, 2), (3, 3), (3, 4), (3, 5), (3, 6), (3, 7)]
# greedy config deux_murs.json : {'cases_explorees': 8, 'profondeur_exploree': 7} chemin : [(0, 0), (1, 1), (2, 2), (3, 3), (4, 4), (5, 5), (6, 6), (7, 7)]
