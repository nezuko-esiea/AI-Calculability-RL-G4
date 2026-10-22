"""
cached_client.py : un client qui retient les réponses de la grid-api.

Pourquoi
    Une évaluation de l'A* pondéré fait de l'ordre de 90 requêtes HTTP, et une
    campagne en fait des milliers. Or pendant une campagne la grille ne change
    jamais : neighbors() et distance() sont des lectures pures, sans effet de
    bord, qui renvoient toujours la même chose pour les mêmes arguments.
    On peut donc les mémoriser.

Comment
    CachedGridClient enveloppe un GridClient et garde deux dictionnaires. Les
    algos ne voient aucune différence : ils appellent les mêmes méthodes, avec
    les mêmes arguments, et reçoivent les mêmes valeurs.

    Les méthodes qui modifient l'état (move, follow) ne sont pas mémorisées :
    elles sont transmises telles quelles.

Le préchauffage
    prechauffer() remplit le cache d'un coup, avant les mesures. C'est
    important pour le temps T : sans ça, la première évaluation paierait tout
    le réseau et les suivantes rien du tout, donc leurs T ne seraient pas
    comparables — alors que T entre dans la fonction objectif.

    Une fois le cache chaud, T mesure le travail de l'algorithme (les pop, les
    push, les opérations sur le tas) et plus la latence du réseau. C'est ce
    qu'on veut pour comparer des algorithmes entre eux, mais c'est à dire
    explicitement dans le rapport : ce n'est plus le même T qu'avant.

A savoir
    Si tu changes de config dans le même processus (un nouveau POST /init),
    il faut appeler vider() : la grille a changé, le cache est périmé.
"""


class CachedGridClient:
    """Enveloppe un GridClient et mémorise neighbors() et distance()."""

    def __init__(self, client):
        self.client = client
        self.url = client.url           # evaluate.load_grid() en a besoin
        self.agent = client.agent
        self._neighbors = {}
        self._distance = {}
        self.appels_reseau = 0          # requêtes réellement parties
        self.appels_cache = 0           # réponses servies par le cache

    # ---- lectures mémorisées ----

    def neighbors(self, node):
        node = tuple(node)
        if node not in self._neighbors:
            self._neighbors[node] = self.client.neighbors(node)
            self.appels_reseau += 1
        else:
            self.appels_cache += 1
        return self._neighbors[node]

    def distance(self, a, b, metric="euclidean"):
        cle = (tuple(a), tuple(b), metric)
        if cle not in self._distance:
            self._distance[cle] = self.client.distance(a, b, metric)
            self.appels_reseau += 1
        else:
            self.appels_cache += 1
        return self._distance[cle]

    # ---- transmis tels quels ----

    def state(self):
        return self.client.state()

    def mission(self):
        return self.client.mission()

    def move(self, direction):
        return self.client.move(direction)

    def follow(self, path):
        return self.client.follow(path)

    # ---- gestion du cache ----

    def vider(self):
        """À appeler après tout changement de grille."""
        self._neighbors.clear()
        self._distance.clear()

    def taille(self):
        return len(self._neighbors), len(self._distance)


def prechauffer(cache, size, target, metriques):
    """Remplit le cache pour toute la grille, avant les mesures.

    Pour chaque case : ses voisins, et sa distance à la cible dans chaque
    métrique utilisée. Après ça, aucune évaluation ne touchera plus le réseau,
    donc toutes les mesures de T sont comparables entre elles.
    """
    for r in range(size):
        for c in range(size):
            case = (r, c)
            cache.neighbors(case)
            for m in metriques:
                cache.distance(case, target, m)
