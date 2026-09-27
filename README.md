# AI Calculability – RL – Groupe 4

Projet en deux applications conteneurisées :

- **C1 – Environment** : graphe, fonctions spatiales (l'état du monde).
- **C2 – Agent** : déplacements (`move`), algorithmes de recherche.

## Architecture

```
            docker-compose.yaml (réseau commun)
 ┌──────────────────────┐        ┌──────────────────────┐
 │  C1 : environment    │  HTTP  │  C2 : agent          │
 │  - graphe            │◄──────►│  - move              │
 │  - fonctions spatiales│       │  - algos de recherche│
 │  - params (taille...)│        │  - params (algo...)  │
 └──────────────────────┘        └──────────────────────┘
```

- Chaque app a sa propre **image** (Dockerfile basé sur `python:3.13-slim`, code dans `/app`).
- `docker-compose.yaml` lance les deux **containers** sur le même réseau : l'agent joint l'environnement par son nom de service (`http://environment:5000`).
- Les paramètres de chaque app passent par des variables d'environnement dans le compose.

## Brainstorm : modèle des deux apps

### C1 – Environment

- **Grid(N×N)** : chaque case `(x, y)` est un noeud.
- **Poids des cases** : `1` normal, `×1.5` terrain lent, `×0.5` bonus, `+∞` obstacle (infranchissable).
- **Graph** : `V = N²` noeuds.
  - connectivité 4 : `E4 = 2N(N-1)` arêtes
  - connectivité 8 : `E8 = E4 + 2(N-1)²` (on ajoute les diagonales)
- **distance(node1, node2)** :
  - L1 Manhattan : `|x1-x2| + |y1-y2|`
  - L2 Euclidienne : `sqrt((x1-x2)² + (y1-y2)²)`

### C2 – Agent

- **Agent** : `position -> node`, `target -> node`, `speed`
- **move(subtarget -> node)** : avance d'un noeud vers le prochain sous-objectif.
- **brain -> algorithm(position, target, grid)** : renvoie le chemin. Algos interchangeables :
  A\*, Dijkstra, D\*, optimisation par essaim particulaire...

## Pourquoi Docker

- **Consistency** : même environnement de dev sur toutes les machines.
- **Efficiency** : pas de second OS, contrairement à une VM.
- **Portability** : les images peuvent être poussées sur un registre et récupérées de partout.
- **Security** : isolation, ports non exposés par défaut.

## Structure

```
.
├── environment/   # C1 : Dockerfile + code
├── agent/         # C2 : Dockerfile + code
└── docker-compose.yaml
```

## Lancer

```bash
docker compose build     # construit les images rl-g4/environment et rl-g4/agent
docker compose up        # crée et lance les containers
docker compose down      # arrête et supprime les containers
```

## Branches

- `main` : version stable (démos, rendus).
- `dev` : intégration ; chacun travaille sur une branche `feature/...` puis fait une PR vers `dev`.
