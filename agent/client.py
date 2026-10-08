"""
GridClient : c'est ce qui fait le lien entre nos algos et la grid-api.

Pourquoi on a ce fichier
    La grille tourne à part (dans le conteneur de la grid-api) et on peut lui
    parler seulement avec des requêtes HTTP. On a mis toutes ces requêtes ici
    pour que les fichiers des algos (astar.py, bfs.py...) contiennent seulement
    l'algo. Tout le groupe utilise le même client.

Les méthodes
    state()              GET  /state                      tout l'état de la grille
    mission()            GET  /mission                    départ, cible, seuil, statut, coût total
    neighbors(node)      GET  /nodes/{r}/{c}/neighbors    les voisins d'une case et le coût pour y aller
    distance(a, b, m)    GET  /distance                   distance "manhattan" ou "euclidean"
    move(direction)      POST /agents/{nom}/move/{dir}    avance l'agent d'une case
    follow(path)         fait tous les move() pour suivre un chemin

A savoir
    - Une case = un tuple (ligne, colonne), comme dans la grid-api.
    - neighbors() et distance() ne font pas bouger l'agent, donc l'algo peut
      regarder toute la grille sans rien payer. C'est seulement move() qui
      ajoute au coût de la mission.
    - follow() regarde la différence entre deux cases du chemin et la transforme
      en direction (N, S, E, W, NE, NW, SE, SW) avec le dictionnaire DIRECTIONS.

Exemple
    client = GridClient("http://localhost:8000", agent="robot")
    path = astar.search(start, target, client)
    client.follow(path)
"""
import requests

# différence (ligne, colonne) entre deux cases voisines -> direction à envoyer à l'API
DIRECTIONS = {
    (-1, 0): "N", (1, 0): "S", (0, 1): "E", (0, -1): "W",
    (-1, 1): "NE", (-1, -1): "NW", (1, 1): "SE", (1, -1): "SW",
}


class GridClient:
    def __init__(self, url="http://localhost:8000", agent="robot"):
        self.url = url
        self.agent = agent

    def state(self):
        """Tout l'état : taille, connectivité, agents, obstacles, mission."""
        return requests.get(f"{self.url}/state").json()

    def mission(self):
        """Départ, cible, seuil, statut et coût total de la mission."""
        return requests.get(f"{self.url}/mission").json()

    def neighbors(self, node):
        """Voisins d'une case, sous la forme [((ligne, colonne), coût), ...]."""
        r, c = node
        data = requests.get(f"{self.url}/nodes/{r}/{c}/neighbors").json()
        return [(tuple(n["node"]), n["cost"]) for n in data]

    def distance(self, a, b, metric="euclidean"):
        """Distance géométrique entre deux cases : 'manhattan' ou 'euclidean'."""
        params = {"r1": a[0], "c1": a[1], "r2": b[0], "c2": b[1], "metric": metric}
        return requests.get(f"{self.url}/distance", params=params).json()["distance"]

    def move(self, direction):
        """Avance l'agent d'une case : N, S, E, W, NE, NW, SE, SW."""
        return requests.post(f"{self.url}/agents/{self.agent}/move/{direction}").json()

    def follow(self, path):
        """Fait suivre un chemin à l'agent, case par case.

        On s'arrête dès que la mission est finie : la grid-api refuse les
        déplacements suivants. Ça arrive quand le seuil est dépassé avant
        d'arriver à la cible, par exemple avec BFS qui ignore les coûts.
        """
        for a, b in zip(path, path[1:]):
            direction = DIRECTIONS[(b[0] - a[0], b[1] - a[1])]
            result = self.move(direction)
            if "error" in result:
                print(result["error"])
                return
            print(f"move {direction:<2} -> {b}  coût {result['move_cost']}  total {result['total_weight']}")
            if result["mission"]["status"] != "running":
                return
