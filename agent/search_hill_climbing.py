"""
search_hill_climbing.py : hill climbing sur l'espace (w, h) de l'A* pondéré.

Le principe
    On part d'une solution (w, h) et on regarde ses voisins. On va sur le
    meilleur voisin s'il est strictement meilleur, et on recommence. Dès
    qu'aucun voisin n'est meilleur, on s'arrête : c'est un optimum local.
    C'est "un genre de greedy" : il ne prend que des décisions qui améliorent
    tout de suite, sans jamais accepter de faire moins bien.

Les voisins d'une solution (w, h)
    - (w - pas, h) et (w + pas, h) : on change un peu w
    - (w, autre h)                 : on garde w et on change d'heuristique
    On enlève les w hors de [w_min, w_max] et les h non admissibles pour la
    connectivité (L1 en connectivité 8).

Le point de départ
    Par défaut l'A* classique (w = 1, L2) : c'est la référence, donc le
    hill climbing part de la solution qu'il doit battre.

Les paliers
    Plusieurs w peuvent donner exactement le même chemin (même C, E, M), donc
    le même F. Sur un palier aucun voisin n'est strictement meilleur : le hill
    climbing s'arrête dès qu'il y arrive. Il trouve donc un point du palier,
    pas ses bords.

Les mesures
    Même fonctionnement que search_grid.py et search_random.py : client en
    cache et préchauffé, chaque évaluation relancée K_REPETITIONS fois en
    gardant le temps médian. F utilise E et pas T, il est donc identique d'un
    lancement à l'autre. Chaque solution n'est évaluée qu'une fois (cache).

Pour le lancer (la grid-api doit tourner)
    python search_hill_climbing.py configs/default.json
    python search_hill_climbing.py configs/default.json --w0 3.95 --h0 L2 --step 0.2
"""
import argparse
import os

import evaluate
from cached_client import CachedGridClient, prechauffer
from client import GridClient
from search_grid import ecrire_csv, metriques_admissibles, run_median

STEP = 0.5          # le pas sur w
MAX_TURNS = 50      # garde-fou : nombre maximum de déplacements
CSV_PATH = "hill_climbing.csv"


class Problem:
    """Une grille à optimiser : évalue les solutions et donne leurs voisins."""

    def __init__(self, client, start, target, threshold, connectivity, ref,
                 step=STEP, w_min=1.0, w_max=evaluate.W_MAX):
        self.client = client
        self.start, self.target = start, target
        self.threshold = threshold
        self.connectivity = connectivity
        self.ref = ref
        self.step, self.w_min, self.w_max = step, w_min, w_max
        self.metriques = metriques_admissibles(connectivity)
        self.cache = {}         # (w, h) -> résultat d'evaluate
        self.history = []       # toutes les évaluations, dans l'ordre

    def score(self, w, h):
        """Évalue (w, h) une seule fois, puis renvoie le résultat gardé en cache."""
        key = (round(w, 2), h)
        if key not in self.cache:
            r = run_median(lambda: evaluate.evaluate(
                self.client, self.start, self.target, key[0], h, self.ref,
                self.connectivity, self.threshold, w_max=self.w_max))
            self.cache[key] = r
            self.history.append(r)
        return self.cache[key]

    def neighbors(self, w, h):
        """Les voisins de (w, h) : w +- pas, ou une autre heuristique admissible."""
        candidates = [(round(w - self.step, 2), h), (round(w + self.step, 2), h)]
        candidates += [(w, other) for other in self.metriques if other != h]
        return [(cw, ch) for cw, ch in candidates if self.w_min <= cw <= self.w_max]


def hill_climbing(problem, w0, h0, max_turns=MAX_TURNS, verbose=True):
    """Va sur le meilleur voisin tant qu'il est strictement meilleur."""
    current = problem.score(w0, h0)
    for turn in range(max_turns):
        results = [problem.score(w, h) for w, h in problem.neighbors(current["w"], current["h"])]
        best_neighbor = min(results, key=lambda r: r["score"])
        if best_neighbor["score"] >= current["score"]:
            if verbose:
                print(f"  tour {turn:2}: aucun voisin strictement meilleur, on s'arrête")
            break
        current = best_neighbor
        if verbose:
            print(f"  tour {turn:2}: -> w = {current['w']:<6g} {current['h']:<6} F = {current['F']:.3f}")
    return current


def paliers(history):
    """Regroupe les évaluations qui donnent le même chemin (même C, M, explored)."""
    groupes = {}
    for r in history:
        groupes.setdefault((r["C"], r["M"], r["explored"], r["h"]), []).append(r["w"])
    return groupes


def resume(nom, best, problem):
    """Affiche la meilleure solution, le budget et les paliers rencontrés."""
    print(f"\n{nom} : w = {best['w']:g}, h = {best['h']}, F = {best['F']:.3f} "
          f"(C = {best['C']:g}, explored = {best['explored']}, M = {best['M']}), "
          f"{len(problem.history)} évaluations")
    print("Paliers rencontrés :")
    for (c, m, e, h), ws in sorted(paliers(problem.history).items(), key=lambda kv: min(kv[1])):
        ws.sort()
        etendue = f"w = {ws[0]:g}" if len(ws) == 1 else f"w de {ws[0]:g} à {ws[-1]:g}"
        print(f"  {h:<6} C = {c:>5g}  M = {m:>3}  explored = {e:>3}   {etendue}  ({len(ws)} points)")


def preparer(config, url):
    """Charge la grille, préchauffe le cache et mesure la référence."""
    client = CachedGridClient(GridClient(url))
    mission = evaluate.load_grid(client, config)
    start, target = tuple(mission["start"]), tuple(mission["target"])
    etat = client.state()
    connectivity, size = etat["connectivity"], etat["size"]

    print(f"Config {config} : {start} -> {target}, connectivité {connectivity}")
    print("Préchauffage du cache...", end=" ", flush=True)
    prechauffer(client, size, target, evaluate.HEURISTICS.values())
    print(f"{client.appels_reseau} requêtes, cache rempli")

    ref = run_median(lambda: evaluate.reference(client, start, target))
    print(f"Référence A* (w = 1, L2) : C* = {ref['C']:g}  E* = {ref['explored']}  M* = {ref['M']}")
    return client, start, target, mission["threshold"], connectivity, ref


def arguments(description, csv_path):
    p = argparse.ArgumentParser(description=description)
    p.add_argument("config", nargs="?", default="configs/default.json")
    p.add_argument("--w0", type=float, default=1.0, help="w de départ (défaut : A* classique)")
    p.add_argument("--h0", default="L2", help="heuristique de départ")
    p.add_argument("--step", type=float, default=STEP, help="pas sur w")
    p.add_argument("--w-min", type=float, default=1.0)
    p.add_argument("--w-max", type=float, default=float(evaluate.W_MAX))
    p.add_argument("--csv", default=csv_path)
    return p


def main():
    args = arguments("Hill climbing sur (w, h) de l'A* pondéré.", CSV_PATH).parse_args()
    url = os.environ.get("GRID_URL", "http://localhost:8000")
    client, start, target, threshold, connectivity, ref = preparer(args.config, url)
    print(f"Hill climbing : départ (w = {args.w0:g}, {args.h0}), pas {args.step:g}\n")

    problem = Problem(client, start, target, threshold, connectivity, ref,
                      args.step, args.w_min, args.w_max)
    best = hill_climbing(problem, args.w0, args.h0)
    resume("Hill climbing", best, problem)

    ecrire_csv(problem.history, args.csv)
    print(f"\nRésultats écrits dans {args.csv}")


if __name__ == "__main__":
    main()
