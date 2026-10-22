"""
evaluate.py : évaluer une solution (w, h) de l'A* pondéré.

Le problème d'optimisation
    Variables de décision : w dans [1, 50] et h parmi L1, L2, L_inf
    Hyperparamètres       : la grille (taille, connectivité, obstacles, départ, cible)
    Mesures               : C = coût du chemin
                            T = temps de recherche (en secondes)
                            M = taille maximale du tas (max_queue)
    Fonction objectif     : F = a * C/C* + b * T/T* + c * M/M*   (à minimiser)
    Contraintes           : h admissible, C <= k * C*, T <= T_MAX

    C*, T* et M* sont les valeurs de la référence : l'A* classique (w = 1, h = L2).
    On divise par la référence pour que les trois termes soient à la même
    échelle (autour de 1), sinon le plus grand écraserait les autres.

Comment ça tourne
    1. load_grid() envoie une config à la grid-api (POST /init).
    2. reference() lance l'A* classique et donne C*, T* et M*.
    3. evaluate() lance l'A* pondéré avec un (w, h), mesure C, T et M,
       vérifie les contraintes et calcule F.
    Les méthodes de recherche (grid search, recuit...) appellent seulement
    evaluate(), c'est la seule partie qui parle à la grid-api.

A savoir
    - L'agent ne bouge pas pendant l'évaluation : on calcule le chemin et son
      coût avec neighbors(), sans appeler move(). On peut donc évaluer autant
      de solutions qu'on veut sur la même grille sans la réinitialiser.
    - Le temps T compte surtout les requêtes HTTP, donc il varie un peu d'un
      lancement à l'autre. On garde aussi "explored" pour expliquer les écarts.
    - Une solution non faisable a un score = infini : les méthodes de
      recherche la classent toujours derrière les solutions faisables.
"""
import json
import math
import time

import requests

import weighted_astar


HEURISTICS = {"L1": "manhattan", "L2": "euclidean", "L_inf": "chebyshev"}

# valeurs provisoires 
WEIGHTS = (0.5, 0.25, 0.25)     # (a, b, c) : poids du coût, du temps et de la mémoire, total = 1
K = 1.2                         # on accepte un chemin jusqu'à 20 % plus cher que le meilleur
T_MAX = 3.0                     # temps de recherche maximum, en secondes
W_MAX = 50                      # borne haute de w


def load_grid(client, config_path):
    """Envoie une config à la grid-api et renvoie la mission (départ, cible, seuil...)."""
    with open(config_path, encoding="utf-8") as f:
        config = json.load(f)
    requests.post(f"{client.url}/init", json=config).raise_for_status()
    return client.mission()


def run(client, start, target, w, h):
    """Lance l'A* pondéré une fois et mesure C, T et M."""
    t0 = time.perf_counter()
    path, stats = weighted_astar.search(start, target, client, metric=HEURISTICS[h], weight=w)
    t = time.perf_counter() - t0

    cost = math.inf
    if path is not None:
        cost = 0.0
        for a, b in zip(path, path[1:]):
            cost += dict(client.neighbors(a))[b]   # coût du pas a -> b donné par la grid-api

    return {"w": w, "h": h, "C": cost, "T": t, "M": stats["max_queue"],
            "explored": stats["explored"], "steps": len(path) - 1 if path else None}


def reference(client, start, target):
    """L'A* classique (w = 1, h = L2) : donne C*, T* et M*."""
    return run(client, start, target, w=1, h="L2")


def admissible(h, connectivity):
    """L1 surestime en 8 voisins (une diagonale coûte 1.5 mais L1 la compte 2)."""
    return not (h == "L1" and connectivity == 8)


def evaluate(client, start, target, w, h, ref, connectivity, threshold,
             weights=WEIGHTS, k=K, t_max=T_MAX):
    """Évalue la solution (w, h) : mesures, contraintes et F."""
    r = run(client, start, target, w, h)
    a, b, c = weights

    r["F"] = a * r["C"] / ref["C"] + b * r["T"] / ref["T"] + c * r["M"] / ref["M"]

    violated = []
    if not 1 <= w <= W_MAX:
        violated.append(f"w hors de [1, {W_MAX}]")
    if not admissible(h, connectivity):
        violated.append(f"{h} non admissible en connectivité {connectivity}")
    if r["C"] > k * ref["C"]:
        violated.append(f"coût {r['C']:g} > {k} x {ref['C']:g}")
    if r["C"] >= threshold:
        violated.append(f"coût {r['C']:g} >= seuil {threshold:g} (mission échouée)")
    if r["T"] > t_max:
        violated.append(f"temps {r['T']:.2f} s > {t_max} s")

    r["feasible"] = not violated
    r["violated"] = violated
    r["score"] = r["F"] if r["feasible"] else math.inf
    return r


if __name__ == "__main__":
    # petit test : la référence puis quelques (w, h) sur une config
    import os
    import sys

    from client import GridClient

    config_path = sys.argv[1] if len(sys.argv) > 1 else "configs/obstacle_u.json"
    client = GridClient(os.environ.get("GRID_URL", "http://localhost:8000"))

    mission = load_grid(client, config_path)
    start, target = tuple(mission["start"]), tuple(mission["target"])
    connectivity = client.state()["connectivity"]

    ref = reference(client, start, target)
    print(f"Config {config_path} : {start} -> {target}, connectivité {connectivity}")
    print(f"Référence A* (w = 1, L2) : C* = {ref['C']:g}  T* = {ref['T']:.2f} s  M* = {ref['M']}\n")

    print(f"{'w':>5} {'h':>6} {'C':>6} {'T (s)':>6} {'M':>4} {'explored':>8} {'F':>6}  faisable")
    for h in ["L1", "L2", "L_inf"]:
        for w in [1, 1.5, 2, 5]:
            r = evaluate(client, start, target, w, h, ref, connectivity, mission["threshold"])
            status = "oui" if r["feasible"] else "non : " + ", ".join(r["violated"])
            print(f"{w:>5} {h:>6} {r['C']:>6g} {r['T']:>6.2f} {r['M']:>4} {r['explored']:>8} {r['F']:>6.3f}  {status}")
