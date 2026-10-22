"""
search_tabou.py : recherche tabou sur l'espace (w, h) de l'A* pondéré.

Le principe
    C'est un hill climbing avec deux règles en plus :
      1. on va toujours sur le meilleur voisin, MÊME s'il est moins bon que
         la solution actuelle : on ne s'arrête pas au premier creux ;
      2. les dernières solutions quittées sont interdites (la liste tabou),
         pour ne pas revenir en arrière et tourner en rond.
    On retient la meilleure solution vue pendant toute la marche : c'est elle
    qu'on renvoie, pas la position du dernier tour.

    Le hill climbing s'arrête sur le premier optimum local (ou dès qu'il
    arrive sur un palier). La tabou continue : elle peut sortir d'un creux
    pour en chercher un meilleur, et elle parcourt les paliers jusqu'à leurs
    bords, ce qui dit sur quel intervalle de w on peut choisir sans rien perdre.

Les voisins et le point de départ
    Les mêmes que search_hill_climbing.py (on réutilise sa classe Problem) :
    w +- pas, ou une autre heuristique admissible. Départ par défaut : l'A*
    classique (w = 1, L2).

Le budget
    Un nombre fixé de tours (--turns). Chaque solution n'est évaluée qu'une
    fois : le nombre d'évaluations affiché est le vrai coût de la recherche,
    à comparer avec celui de la grid et du random.

Pour le lancer (la grid-api doit tourner)
    python search_tabou.py configs/default.json
    python search_tabou.py configs/default.json --turns 30 --tabu-size 10 --step 0.5
"""
import os

from search_grid import ecrire_csv
from search_hill_climbing import Problem, arguments, preparer, resume

N_TURNS = 20        # nombre de tours
TABU_SIZE = 10      # nombre de solutions gardées dans la liste tabou
CSV_PATH = "tabou.csv"


def tabu_search(problem, w0, h0, n_turns=N_TURNS, tabu_size=TABU_SIZE, verbose=True):
    """Va toujours sur le meilleur voisin non tabou, même s'il est moins bon."""
    current = problem.score(w0, h0)
    best = current
    tabu = []
    for turn in range(n_turns):
        candidates = [v for v in problem.neighbors(current["w"], current["h"]) if v not in tabu]
        if not candidates:
            if verbose:
                print(f"  tour {turn:2}: tous les voisins sont tabou, on s'arrête")
            break
        results = [problem.score(w, h) for w, h in candidates]
        best_neighbor = min(results, key=lambda r: r["score"])

        tabu.append((round(current["w"], 2), current["h"]))   # la solution quittée devient tabou
        tabu = tabu[-tabu_size:]                               # on garde seulement les dernières

        current = best_neighbor                                # on bouge, même si c'est moins bon
        note = ""
        if current["score"] < best["score"]:
            best = current
            note = "  <- meilleur jusqu'ici"
        if verbose:
            print(f"  tour {turn:2}: -> w = {current['w']:<6g} {current['h']:<6} F = {current['F']:.3f}"
                  f"{'' if current['feasible'] else ' (non faisable)'}{note}")
    return best


def main():
    p = arguments("Recherche tabou sur (w, h) de l'A* pondéré.", CSV_PATH)
    p.add_argument("--turns", type=int, default=N_TURNS, help="nombre de tours")
    p.add_argument("--tabu-size", type=int, default=TABU_SIZE, help="taille de la liste tabou")
    args = p.parse_args()

    url = os.environ.get("GRID_URL", "http://localhost:8000")
    client, start, target, threshold, connectivity, ref = preparer(args.config, url)
    print(f"Recherche tabou : départ (w = {args.w0:g}, {args.h0}), pas {args.step:g}, "
          f"{args.turns} tours, liste tabou de {args.tabu_size}\n")

    problem = Problem(client, start, target, threshold, connectivity, ref,
                      args.step, args.w_min, args.w_max)
    best = tabu_search(problem, args.w0, args.h0, args.turns, args.tabu_size)
    resume("Recherche tabou", best, problem)

    ecrire_csv(problem.history, args.csv)
    print(f"\nRésultats écrits dans {args.csv}")


if __name__ == "__main__":
    main()
