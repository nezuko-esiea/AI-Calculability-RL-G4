"""
main.py : le script qu'on lance pour faire tourner l'agent avec BFS.

Ce qu'il fait
    1. Il crée le client pour parler à la grid-api (par défaut sur
       http://localhost:8000, on peut changer avec la variable GRID_URL).
    2. Il demande la mission à la grid-api : le départ, la cible et le seuil.
    3. Il lance BFS pour calculer le chemin. A ce moment l'agent ne bouge pas
       encore, l'algo regarde juste les voisins.
    4. Il fait suivre le chemin à l'agent, case par case, avec client.follow().
    5. Il affiche le résultat de la mission (réussie ou échouée, coût total,
       nombre de pas).

Pour le lancer
    Il faut d'abord que la grid-api tourne :
        cd grid_api
        docker build -t grid-api -f Containerfile .
        docker run --rm -p 8000:8000 grid-api
    Puis dans un autre terminal :
        pip install -r requirements.txt
        python main.py

"""
import os

import bfs as bfs
from client import GridClient

client = GridClient(os.environ.get("GRID_URL", "http://localhost:8000"))

mission = client.mission()
start = tuple(mission["start"])
target = tuple(mission["target"])
print(f"Mission : {start} -> {target}, seuil {mission['threshold']}")

path = bfs.search(start, target, client)
print("Chemin trouvé par BFS :", path)

client.follow(path)
print(client.mission()["message"])
