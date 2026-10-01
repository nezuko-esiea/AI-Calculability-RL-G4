"""Parle à grid_api (le code du prof) en HTTP. Commun à tous les algos."""
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
        """Fait suivre un chemin à l'agent, case par case."""
        for a, b in zip(path, path[1:]):
            direction = DIRECTIONS[(b[0] - a[0], b[1] - a[1])]
            result = self.move(direction)
            print(f"move {direction:<2} -> {b}  coût {result['move_cost']}  total {result['total_weight']}")
