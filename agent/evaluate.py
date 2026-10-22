"""
evaluate.py : évaluer une solution (w, h) de l'A* pondéré.

Le problème d'optimisation
    Variables de décision : w dans [1, W_MAX] et h parmi L1, L2, L_inf
    Hyperparamètres       : la grille (taille, connectivité, obstacles, départ, cible)
    Mesures               : C = coût du chemin
                            E = effort de recherche, en nœuds développés
                            M = taille maximale du tas (max_queue)
                            T = temps de recherche, mesuré mais hors de F
    Fonction objectif     : F = a * C/C* + b * E/E* + c * M/M*   (à minimiser)
    Contraintes           : w dans l'espace déclaré, h admissible,
                            C <= k * C*, C < seuil de la mission, T <= T_MAX

    C*, E* et M* sont les valeurs de la référence : l'A* classique (w = 1, h = L2).
    On divise par la référence pour que les trois termes soient à la même
    échelle (autour de 1), sinon le plus grand écraserait les autres.

Pourquoi E et pas T dans F
    Avec le cache, une recherche dure quelques dizaines de microsecondes. À
    cette échelle le chronomètre est dominé par le bruit : deux exécutions du
    même calcul peuvent différer d'un facteur 4, même en prenant la médiane
    sur onze répétitions. Un terme bruité pesant 0.25 dans F finissait par
    décider du classement, et le décidait mal — une solution strictement
    dominée sur C, E et M pouvait passer devant juste parce qu'elle avait été
    chronométrée plus vite.

    Le nombre de nœuds développés mesure le même phénomène (la quantité de
    travail), mais c'est un entier parfaitement reproductible, indépendant de
    la machine et de la charge. C'est aussi ce que recommande le support de
    cours : « l'efficacité se mesure en nœuds développés, pas avec le pire
    cas ».

    T reste mesuré, affiché et écrit dans les CSV : il sert à vérifier qu'il
    suit bien E, et à documenter les temps réels dans le rapport.

Comment ça tourne
    1. load_grid() envoie une config à la grid-api (POST /init).
    2. reference() lance l'A* classique et donne C*, E*, M* et T*.
    3. evaluate() lance l'A* pondéré avec un (w, h), mesure C, E, M et T,
       vérifie les contraintes et calcule F.
    Les méthodes de recherche (grid search, recuit...) appellent seulement
    evaluate(), c'est la seule partie qui parle à la grid-api.

A savoir
    - L'agent ne bouge pas pendant l'évaluation : on calcule le chemin et son
      coût avec neighbors(), sans appeler move(). On peut donc évaluer autant
      de solutions qu'on veut sur la même grille sans la réinitialiser.
    - Une solution non faisable a un score = infini : les méthodes de
      recherche la classent toujours derrière les solutions faisables.
    - W_MAX n'est que la valeur par défaut de la borne. Les scripts de
      recherche passent leur propre w_max, pour que la contrainte corresponde
      à l'espace qu'ils balaient réellement.
"""
import json
import math
import time

import requests

import weighted_astar

# noms du cours -> noms attendus par la grid-api
HEURISTICS = {"L1": "manhattan", "L2": "euclidean", "L_inf": "chebyshev"}

# valeurs provisoires : à décider en groupe
WEIGHTS = (0.5, 0.25, 0.25)     # (a, b, c) : poids du coût, de l'effort et de la mémoire, total = 1
K = 2.5                         # on accepte un chemin jusqu'à 2.5 fois le coût optimal
T_MAX = 3.0                     # temps de recherche maximum, en secondes
W_MAX = 50                      # borne haute de w par défaut


def load_grid(client, config_path):
    """Envoie une config à la grid-api et renvoie la mission (départ, cible, seuil...)."""
    with open(config_path, encoding="utf-8") as f:
        config = json.load(f)
    requests.post(f"{client.url}/init", json=config).raise_for_status()
    return client.mission()


def run(client, start, target, w, h):
    """Lance l'A* pondéré une fois et mesure C, T, M et l'effort."""
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
    """L'A* classique (w = 1, h = L2) : donne C*, E*, M* et T*."""
    return run(client, start, target, w=1, h="L2")


def admissible(h, connectivity):
    """L1 surestime en 8 voisins (une diagonale coûte 1.5 mais L1 la compte 2)."""
    return not (h == "L1" and connectivity == 8)


def evaluate(client, start, target, w, h, ref, connectivity, threshold,
             weights=WEIGHTS, k=K, t_max=T_MAX, w_max=W_MAX):
    """Évalue la solution (w, h) : mesures, contraintes et F."""
    r = run(client, start, target, w, h)
    a, b, c = weights

    # F combine le coût, l'effort (nœuds développés) et la mémoire, chacun
    # rapporté à la référence pour être sans unité et du même ordre de grandeur.
    r["F"] = (a * r["C"] / ref["C"]
              + b * r["explored"] / ref["explored"]
              + c * r["M"] / ref["M"])

    violated = []
    if not 1 <= w <= w_max:
        violated.append(f"w hors de [1, {w_max:g}]")
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

    config_path = sys.argv[1] if len(sys.argv) > 1 else "configs/default.json"
    client = GridClient(os.environ.get("GRID_URL", "http://localhost:8000"))

    mission = load_grid(client, config_path)
    start, target = tuple(mission["start"]), tuple(mission["target"])
    connectivity = client.state()["connectivity"]

    ref = reference(client, start, target)
    print(f"Config {config_path} : {start} -> {target}, connectivité {connectivity}")
    print(f"Référence A* (w = 1, L2) : C* = {ref['C']:g}  E* = {ref['explored']}  M* = {ref['M']}\n")

    print(f"{'w':>5} {'h':>6} {'C':>6} {'explored':>8} {'M':>4} {'T (µs)':>8} {'F':>6}  faisable")
    for h in ["L1", "L2", "L_inf"]:
        for w in [1, 1.5, 2, 5]:
            r = evaluate(client, start, target, w, h, ref, connectivity, mission["threshold"])
            status = "oui" if r["feasible"] else "non : " + ", ".join(r["violated"])
            print(f"{w:>5} {h:>6} {r['C']:>6g} {r['explored']:>8} {r['M']:>4} "
                  f"{r['T'] * 1e6:>8.1f} {r['F']:>6.3f}  {status}")
