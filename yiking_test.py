# Pialoux's Yijing System
# 仁表的《周易》體系

from pathlib import Path
from orgparse import load, loads
from googletrans import Translator
from selenium.webdriver import Firefox
from tika import parser
import networkx as nx
import pandas as pd
import numpy as np
import httpx
import re
from itertools import product

import matplotlib.pyplot as plt

import sys
import warnings


warnings.filterwarnings("ignore")

print('Python Version : '+sys.version)
print('NetworkX version : '+nx.__version__)














def jiaohui_xue_attrib(acupoint, attrib="meridian"):
    if attrib == "meridian":
        return [mai[2] for mai in QJBM if mai[1] == acupoint][0]
    elif attrib == "hexagram":
        return [mai[0] for mai in QJBM if mai[1] == acupoint][0]


def tri2hex(lower, upper):
    """Concatenate binary numbers of trigrams to form hexagrams."""
    trigram_graph = [item[0] for item in trigram]
    lower_bin = trigram_bin[trigram_graph.index(lower)]
    upper_bin = trigram_bin[trigram_graph.index(upper)]

    hex_bin = lower_bin + upper_bin

    return hex_bin




def build_hexagram_bin():
    hexagram_graph = [item[0] for item in hexagram]

    hexa_bin_list = []
    for graph in hexagram_graph:
        inner, outer = inner_outer_dict[graph]

        hexa_bin_list.append(tri2hex(inner, outer))

    return hexa_bin_list






def trigram_name(graph, category="default"):
    if category == "default":
        return [v[1] for i, v in enumerate(trigram) if graph in v][0]
    else:
        return [trigram_PL[i] for i, v in enumerate(trigram) if graph in v][0]


#

#



# PL_16_series = hexagram_df.loc[:, "PL_16_series"]
#
# PL_16_series_set = set(zip(PL_16_series, PL_16_series_bin))



# print([(jiaohui_xue_attrib(a), jiaohui_xue_attrib(b)) for a, b in bamai_jiaohui])


#


# petit_yang = [doublet for doublet in mutations if doublet not in petit_yin]
#
# print(petit_yang)
############################


def get_org_nodes(file):
    path = Path(__file__)
    path = path.home()/"Creation"/"gutenberg"/file
    path = path.with_suffix(".org")
    root = load(path)

    nodes = root.env.nodes

    return nodes

def pdf_to_org(source, write_to_file=False):

    raw = parser.from_file(source)
    data = raw['content']
    title = raw['metadata']['title']
    target = title.replace(" ", "_")

    path = Path(__file__)
    path = path.home() / "Creation" / "gutenberg" / target
    path = path.with_suffix(".org")

    if write_to_file:
        with path.open("r") as f:
            f.write(data)

        return path
    else:
        return path, data


def translate_ebook():

    ebook = '/home/sati/Zotero/storage/8M4L5F7T/Pialoux-2002-Le_diamant_chauve.pdf'
    book = pdf_to_org(ebook)[0]
    book_tr = book.parent / (book.with_suffix("").name + "_en.org")

    chapters = get_org_nodes(book)

    for chapter in chapters:
        heading = chapter.heading
        body = chapter.body
        paragraphs = body.split("\n\n")

        timeout = httpx.Timeout(10)  # 10 seconds timeout
        translator = Translator(timeout=timeout)

        for paragraph in paragraphs:
            if paragraph:
                try:
                    translation = translator.translate(paragraph.replace("\n", " "), src="fr", dest="en")
                    print(f"{translation.text}\n")

                    with book_tr.open("a") as f:
                        f.write(f"{translation.text}\n\n")

                except IndexError:
                    translation = paragraph
                    print(f"{translation}\n")

                    with book_tr.open("a") as f:
                        f.write(f"{translation}\n\n")

