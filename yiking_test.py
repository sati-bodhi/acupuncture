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


def create_hexagram_df():
    hexagram_list = []
    for i, num in enumerate(range(0x4dc0, 0x4e00)):
        hexagram_list.append(chr(num))

    s = "乾、坤、屯、蒙、需、訟、師、比、小畜、履、泰、否、同人、大有、謙、豫、隨、蠱、臨、觀、噬嗑、賁、剝、復、無妄、大畜、頤、大過、坎、離、鹹、恆、遁、大壯、晉、明夷、家人、睽、蹇、解、損、益、夬、姤、萃、升、困、井、革、鼎、震、艮、漸、歸妹、豐、旅、巽、兑、渙、節、中孚、小過、既濟、未濟"
    names = s.split("、")
    hexagram = list(zip(hexagram_list, names))

    hexagram_df = pd.DataFrame(hexagram, columns = ["hexagram", "name"])

    return hexagram_df

print(create_hexagram_df())

def build_hexagram_df():
    [
        "bin",  # bindary code
        "bin_rev_int",  # reversed binary code integer (for sorting)
    ]
    hexagram_bin = build_hexagram_bin()
    hexagram = [(item[0], item[1], hexagram_bin[i], int(hexagram_bin[i][::-1], 2))  # use [::-1] to reverse string
                for i, item in enumerate(hexagram)]

    hexagram_arr = sorted(hexagram, key=lambda tup: tup[3])


def create_trigram_df_with_neiwaigua():
    s = """
    | §    | ☰ 乾   | ☱ 兌   | ☲ 離   | ☳ 震   | ☴ 巽   | ☵ 坎   | ☶ 艮   | ☷ 坤   |
    |------+--------+--------+--------+--------+--------+--------+--------+--------|
    | ☰ 乾 | ䷀ 乾   | ䷪ 夬   | ䷍ 大有 | ䷡ 大壯 | ䷈ 小畜 | ䷄ 需   | ䷙ 大畜 | ䷊ 泰   |
    | ☱ 兌 | ䷉ 履   | ䷹ 兌   | ䷥ 睽   | ䷵ 歸妹 | ䷼ 中孚 | ䷻ 節   | ䷨ 損   | ䷒ 臨   |
    | ☲ 離 | ䷌ 同人 | ䷰ 革   | ䷝ 離   | ䷶ 豐   | ䷤ 家人 | ䷾ 既濟 | ䷕ 賁   | ䷣ 明夷 |
    | ☳ 震 | ䷘ 妄   | ䷐ 隨   | ䷔ 噬嗑 | ䷲ 震   | ䷩ 益   | ䷂ 屯   | ䷚ 頤   | ䷗ 復   |
    | ☴ 巽 | ䷫ 姤   | ䷛ 大過 | ䷱ 鼎   | ䷟ 恒   | ䷸ 巽   | ䷯ 井   | ䷑ 蠱   | ䷭ 升   |
    | ☵ 坎 | ䷅ 訟   | ䷮ 困   | ䷿ 未濟 | ䷧ 解   | ䷺ 渙   | ䷜ 坎   | ䷃ 蒙   | ䷆ 師   |
    | ☶ 艮 | ䷠ 遯   | ䷞ 咸   | ䷷ 旅   | ䷽ 小過 | ䷴ 漸   | ䷦ 蹇   | ䷳ 艮   | ䷎ 謙   |
    | ☷ 坤 | ䷋ 否   | ䷬ 萃   | ䷢ 晉   | ䷏ 豫   | ䷓ 觀   | ䷇ 比   | ䷖ 剝   | ䷁ 坤   |
    """

    comb_list = s.split("\n")
    comb_list = [s.split("|") for s in comb_list]
    comb_list = [lst for lst in comb_list if len(lst) > 1]
    comb_list.pop(1)
    comb_list = [list(filter(None, lst)) for lst in comb_list]
    comb_list = [[item.strip() for item in lst] for lst in comb_list]

    trigram = [tuple(item.split(" ")) for item in comb_list[0]]
    trigram.pop(0)
    comb_list.pop(0)

    inner_outer_dict = {}  # 內外卦
    for lst in comb_list:
        nei = lst[0][0]
        for item in lst[1:]:
            idx = lst.index(item)-1
            wai = trigram[idx][0]
            inner_outer_dict[item[0]] = (nei, wai)

    trigram_df = pd.DataFrame(trigram)

    return trigram_df, inner_outer_dict

trigram_df, inner_outer_dict = create_trigram_df_with_neiwaigua()
print(trigram_df)

# trigram_code = [
#     (1,1,1),
#     (1,1,0),
#     (1,0,1),
#     (1,0,0),
#     (0,1,1),
#     (0,1,0),
#     (0,0,1),
#     (0,0,0),
# ]

trigram_bin = [
    0b111,  # 乾
    0b110,  # 兌
    0b101,  # 離
    0b100,  # 震
    0b011,  # 巽
    0b010,  # 坎
    0b001,  # 艮
    0b000,  # 坤
]

trigram_bin = [format(n, "03b") for n in trigram_bin]

bigram_PL = [
    ("T", "00"),  # 元氣：Life energy, Transcendent (Transcendante), North
    ("C", "10"),   # 清氣：Respiratory energy, Combustive (Comburante), East
    ("A", "11"),  # 谷氣：Nutritive energy, Alimentary (Alimentaire), South
    ("G", "01"),   # 精氣：Ancestral energy, Genetic (Génétique), West
]

bigram_PL_dict = {bin:code for code, bin in bigram_PL}

trigram_PL = [
    "A''",  # 乾
    "T''",  # 兌
    "C''",  # 離
    "G''",  # 震
    "C'",  # 巽
    "G'",  # 坎
    "A'",  # 艮
    "T'",  # 坤
]

trigram_bearing = [  # 仁表用的是「伏羲八卦方位」，見朱子《周易本義》。
    "S",  # 乾
    "SE", # 兌
    "E",  # 離
    "NE", # 震
    "SW", # 巽
    "W",  # 坎
    "NW", # 艮
    "N",  # 坤
]

trigram_df = pd.DataFrame([trigram, trigram_bin, trigram_PL, trigram_bearing])

HETU_index = [
    (1, "天一"),  # 乾
    (7, "天七"),  # 兌
    (3, "天三"),  # 離
    (8, "地八"),  # 震
    (9, "天九"),  # 巽
    (4, "地四"),  # 坎
    (6, "地六"),  # 艮
    (2, "地二"),  # 坤
    (5, "天五"),  # O
    (10, "地十"),  # O
]

hetu_trigram = list(zip(HETU_index, trigram + 2*[("O", "中")]))
hetu_trigram = [t1+t2 for t1, t2 in hetu_trigram]
# hetu_df = pd.DataFrame(hetu_trigram)

hetu_trigram.sort(key=lambda tup: tup[0])
print(trigram_df)

bearing_values = {
    "N": 0,
    "NE": 45,
    "E": 90,
    "SE": 135,
    "S": 180,
    "SW":225,
    "W": 270,
    "NW": 315,
}

QJBM = [  # 奇經八脈
    ("坎", "申脈", "陽蹻脈"),
    ("坤", "照海", "陰蹻脈"),
    ("震", "外關", "陽維脈"),
    ("巽", "足臨泣", "帶脈"),
    ("乾", "公孫", "衝脈"),
    ("兌", "後谿", "督脈"),
    ("艮", "內關", "陰維脈"),
    ("離", "列缺", "任脈"),
]

bamai_jiaohui = [  # 八脈交會
    ("內關","公孫"),
    ("外關", "足臨泣"),
    ("列缺", "照海"),
    ("後谿", "申脈"),
]


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


def get_org_nodes(file):
    path = Path(__file__)
    path = path.home()/"Creation"/"gutenberg"/file
    path = path.with_suffix(".org")
    root = load(path)

    nodes = root.env.nodes

    return nodes


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


# hexagram_df = build_hexagram_df()
# hexagram_df["inner_outer"] = [(trigram_name(inner), trigram_name(outer)) for inner, outer in
#                               [inner_outer_dict[hexagram] for hexagram in hexagram_df.iloc[:,0].to_list()]]
#
# hexagram_df["PL_trigram"] = [(trigram_name(inner, "Pialoux"), trigram_name(outer, "Pialoux")) for inner, outer in
#                               [inner_outer_dict[hexagram] for hexagram in hexagram_df.iloc[:,0].to_list()]]
# # hexagram_df["PL_trigram"] = hexagram_df["PL_trigram"].astype("|S")
#
# hexagram_by_2 = [re.findall("..", s) for s in hexagram_df.iloc[:,2].to_list()]
#
# hexagram_df["PL_bigram"] = [bigram_PL_dict[l] + bigram_PL_dict[m] + bigram_PL_dict[u] for l, m, u in hexagram_by_2]
# # hexagram_df["PL_bigram"] = hexagram_df["PL_bigram"].astype("|S3")  # store as string of len 3.
#
# hexagram_df["PL_16_series"] = [s[0:2] for s in hexagram_df.loc[:,"PL_bigram"].to_list()]

# PL_16_series = hexagram_df.loc[:, "PL_16_series"]
# PL_16_series_bin = ["".join(lst[:2]) for lst in hexagram_by_2]
# PL_16_series_set = set(zip(PL_16_series, PL_16_series_bin))

# get pialoux bigram code
# print(hexagram_df.query("PL_bigram == 'TAA'").PL_16_series.tolist()[0])

# print([(jiaohui_xue_attrib(a), jiaohui_xue_attrib(b)) for a, b in bamai_jiaohui])

# PL_16_series_df = pd.DataFrame(PL_16_series_set, columns=['16-series','bin'])
# PL_16_series_df["id"] = PL_16_series_df['bin'].apply(lambda x: int(str(x), 2) + 1)
# PL_16_series_df.set_index("id", inplace=True)
# PL_16_series_df.sort_index(inplace=True)
#
# mutations = list(product(["T", "G", "C", "A", "O"], repeat = 2))
# petit_yin = []
# for i, doublet in enumerate(mutations):
#     # print(i, doublet)
#     if "O" in doublet:
#         petit_yin.append(doublet)
#
# print(petit_yin)

# petit_yang = [doublet for doublet in mutations if doublet not in petit_yin]
#
# print(petit_yang)
############################

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

