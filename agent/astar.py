"""A* : explore toujours la case au plus petit f = g + h."""
import heapq


def search(start, target, client, metric="euclidean"):
    """Renvoie le chemin [start, ..., target], ou None s'il n'y en a pas."""
    g = {start: 0}          # coût réel depuis le départ
    parent = {}             # parent[case] = la case d'où on est venu
    explored = set()
    queue = [(client.distance(start, target, metric), start)]   # (f, case)

    while queue:
        f, node = heapq.heappop(queue)      # la case au plus petit f
        if node in explored:
            continue
        explored.add(node)

        if node == target:
            return build_path(parent, start, target)

        for neighbor, cost in client.neighbors(node):
            new_g = g[node] + cost
            if neighbor not in g or new_g < g[neighbor]:
                g[neighbor] = new_g
                parent[neighbor] = node
                h = client.distance(neighbor, target, metric)   # coût estimé jusqu'à la cible
                heapq.heappush(queue, (new_g + h, neighbor))

    return None


def build_path(parent, start, target):
    """Remonte les parents depuis la cible jusqu'au départ."""
    path = [target]
    while path[-1] != start:
        path.append(parent[path[-1]])
    path.reverse()
    return path
