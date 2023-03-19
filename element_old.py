from matplotlib import pyplot as plt
import networkx as nx
import numpy as np
from pathlib import Path
import os

DB_PATH = Path(os.path.abspath(__file__)).parents[0] / "acu.db"

ELEM = ("木", "火", "土", "金", "水")


def make_cyclic_edge(lst):
    cyclic = []
    for i, elem in enumerate(lst):
        if i+1 < len(lst):
            cyclic.append((elem, lst[i+1]))
        else:
            cyclic.append((elem, lst[0]))

    return cyclic


ELEM_CYCLE_GEN = make_cyclic_edge(ELEM)  # 5 element generation cycle edges
ELEM_CYCLE_INHIBIT = make_cyclic_edge(("木", "土", "水", "火", "金"))


def cycle_diagram(generate, inhibit, top=None, clockwise=True, organ_func=False, plot=False):
    """Generate element cycle diagram with Networkx. """

    G = nx.MultiDiGraph()
    for pair in generate:
        G.add_edge(*pair, color="g", group="generate")

    for pair in inhibit:
        G.add_edge(*pair, color="r", group="inhibit")

    pos = nx.circular_layout(G, center=(0, 0))

    if top:
        c, s = pos[top]
        R_mat = np.array([[-s, c], [c, s]])
        for k, v in pos.items():
            pos[k] = R_mat @ v

    if not clockwise:
        for k, v in pos.items():
            pos[k][0] *= -1

    generate_list = [(u, v, c) for (u, v, c) in G.edges.data('group') if c == "generate"]
    edges_to_adjust = []

    if organ_func:
        plt.figure(2, figsize=(5, 5), dpi=200)

        edges_to_adjust = [("LI", "GB", 0), ("LI", "GB", 1), ("GB", "TE", 0), ("TE", "LI", 0),
                           ("ST", "BL", 0), ("BL", "SI", 0)]

        for edge in edges_to_adjust:
            G.remove_edge(*edge)  # temporarily remove edges that require a different connection style.

    inhibit_list = [(u, v, c) for (u, v, c) in G.edges.data('group') if c == "inhibit"]

    if organ_func:
        nx.draw(
            G, pos=pos,
            with_labels=True,
            font_family='AR PL KaitiM Big5',
            font_size=16,
            node_size=800,
            node_color='#C6DDCB',
            connectionstyle=f"arc3, rad=-0.1",
            edgelist=generate_list,
            edge_color="g",
        )

        nx.draw_networkx_edges(G,
                               pos=pos,
                               node_size=800,
                               edgelist=inhibit_list,
                               connectionstyle=f"arc3, rad=-0",
                               edge_color="r",
                               )

        nx.draw_networkx_edges(G,
                               pos=pos,
                               node_size=800,
                               edgelist=edges_to_adjust,  # build back removed edges.
                               connectionstyle=f"arc3, rad=-0.6",
                               edge_color="r",
                               )

    else:

        plt.figure(1, figsize=(4, 4), dpi=200)

        nx.draw(
            G, pos=pos,
            with_labels=True,
            font_family='AR PL KaitiM Big5',
            font_size=16,
            node_size=800,
            node_color='#C6DDCB',
            connectionstyle=f"arc3, rad=-0.235",
            edgelist=generate_list,
            edge_color="g",
        )

        nx.draw_networkx_edges(G,
                               pos=pos,
                               node_size=800,
                               edgelist=inhibit_list,
                               connectionstyle=f"arc3, rad=0.0",
                               edge_color="r",
                               )

    if plot:
        plt.show()

    return G


ORGAN_FUNC = (
    "SP",
    "LU",
    "PC",
    "LI",
    "TE",
    "GB",
    "LR",
    "KI",
    "HT",
    "SI",
    "BL",
    "ST",
)

ORGAN_FUNC_GEN = make_cyclic_edge(ORGAN_FUNC)

ORGAN_FUNC_INHIBIT_A = (
    "BL",
    "SI",
    "LI",
    "GB",
    "ST",
)

ORGAN_FUNC_INHIBIT_Am = (
    "LI",
    "GB",
    "TE",
)

ORGAN_FUNC_INHIBIT_B = (
    "SP",
    "KI",
    "PC",
    "HT",
    "LU",
    "LR",
)

ORGAN_FUNC_INHIBIT_C = (
    "LR",
    "PC",
    "HT",
    "LU",
)

ORGAN_FUNC_INHIBIT_D = (
    "BL",
    "TE",
)

ORGAN_FUNC_inhibit_list = [
    ORGAN_FUNC_INHIBIT_A,
    ORGAN_FUNC_INHIBIT_Am,
    ORGAN_FUNC_INHIBIT_B,
    ORGAN_FUNC_INHIBIT_C,
    ORGAN_FUNC_INHIBIT_D,
                             ]

ORGAN_FUNC_INHIBIT = []
for cycle in ORGAN_FUNC_inhibit_list:
    ORGAN_FUNC_INHIBIT += make_cyclic_edge(cycle)


if __name__ == '__main__':

    ELEM_CYCLE = cycle_diagram(ELEM_CYCLE_GEN, ELEM_CYCLE_INHIBIT, top="火")
    ORGAN_FUNC_CYCLE = cycle_diagram(ORGAN_FUNC_GEN, ORGAN_FUNC_INHIBIT, top="BL", organ_func=True, plot=True)

    print("!")

