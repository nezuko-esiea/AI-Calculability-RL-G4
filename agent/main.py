import os

import astar
from client import GridClient

client = GridClient(os.environ.get("GRID_URL", "http://localhost:8000"))

mission = client.mission()
start = tuple(mission["start"])
target = tuple(mission["target"])
print(f"Mission : {start} -> {target}, seuil {mission['threshold']}")

path = astar.search(start, target, client)
print("Chemin trouvé par A* :", path)

client.follow(path)
print(client.mission()["message"])
