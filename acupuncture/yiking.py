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

# Trigram Hexagram Relations Table
TRI_HEX_REL = """
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

trigram_bin = [
    "111",  # 乾
    "110",  # 兌
    "101",  # 離
    "100",  # 震
    "011",  # 巽
    "010",  # 坎
    "001",  # 艮
    "000",  # 坤
]


bigram_PL = [
    ("T", "00"),  # 元氣：Life energy, Transcendent (Transcendante), North
    ("C", "10"),   # 清氣：Respiratory energy, Combustive (Comburante), East
    ("A", "11"),  # 谷氣：Nutritive energy, Alimentary (Alimentaire), South
    ("G", "01"),   # 精氣：Ancestral energy, Genetic (Génétique), West
]

bigram_PL_dict = {bin:code for code, bin in bigram_PL}
bigram_PL_bin_dict = {code:bin for code, bin in bigram_PL}

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
    ["內關", "公孫"],
    ["外關", "足臨泣"],
    ["列缺", "照海"],
    ["後谿", "申脈"],
]

HETU_index = [
    (2, "地二"),  # 乾
    (7, "天七"),  # 兌
    (3, "天三"),  # 離
    (8, "地八"),  # 震
    (9, "天九"),  # 巽
    (4, "地四"),  # 坎
    (6, "地六"),  # 艮
    (1, "天一"),  # 坤
    (5, "天五"),  # O
    (10, "地十"),  # O
]

def build_hexagram_df():
    hexagram_list = []
    for i, num in enumerate(range(0x4dc0, 0x4e00)):
        hexagram_list.append(chr(num))

    s = "乾、坤、屯、蒙、需、訟、師、比、小畜、履、泰、否、同人、大有、謙、豫、隨、蠱、臨、觀、噬嗑、賁、剝、復、無妄、大畜、頤、大過、坎、離、鹹、恆、遁、大壯、晉、明夷、家人、睽、蹇、解、損、益、夬、姤、萃、升、困、井、革、鼎、震、艮、漸、歸妹、豐、旅、巽、兑、渙、節、中孚、小過、既濟、未濟"
    names = s.split("、")
    hexagram = list(zip(hexagram_list, names))

    hexagram_df = pd.DataFrame(hexagram, columns = ["hexagram", "name"])

    inner_outer_dict = build_relations_dict()
    trigram = build_trigram_df()

    hexagram_df["inner_outer"] = [inner_outer_dict[graph] for graph in hexagram_df.hexagram]
    hexagram_df["bin"] = [trigram.query(f"name == '{n}'")["bin"].tolist()[0] +
               trigram.query(f"name == '{w}'")["bin"].tolist()[0]
               for n, w in hexagram_df.inner_outer]
    # reversed binary code integer (for sorting)
    hexagram_df["bin_rev_int"] = [int(n[::-1], 2) for n in hexagram_df.bin]  # use [::-1] to reverse string

    # Pialoux trigram
    hexagram_df["PL_tri"] = [(trigram.query(f"name == '{n}'")["PL_tri"].tolist()[0],
                              trigram.query(f"name == '{w}'")["PL_tri"].tolist()[0]) for n, w in hexagram_df.inner_outer]
    hexagram_by_2 = [re.findall("..", s) for s in hexagram_df.loc[:,"bin"].to_list()]
    # Pialoux bigram
    hexagram_df["PL_bi"] = [bigram_PL_dict[l] + bigram_PL_dict[m] + bigram_PL_dict[u] for l, m, u in hexagram_by_2]
    # Pialoux 16-series
    hexagram_df["PL_16"] = hexagram_df["PL_bi"].apply(lambda x: x[:2])
    hexagram_df["PL_16_bin"] = hexagram_df["bin"].apply(lambda x: x[:4])

    return hexagram_df


def build_trigram_df():
    trigram_list = []
    for i, num in enumerate(range(0x2630, 0x2638)):
        trigram_list.append(chr(num))

    s = "乾兌離震巽坎艮坤"
    names = list(s)
    trigram = list(zip(trigram_list, names, trigram_bin))

    trigram_df = pd.DataFrame(trigram, columns = ["trigram", "name", "bin"])
    trigram_df["bin_int"] = trigram_df["bin"].apply(lambda x: int(x,2))
    trigram_df["bearing"] = trigram_bearing
    trigram_df["bearing_values"] = [bearing_values[b] for b in trigram_df.bearing]
    trigram_df["PL_tri"] = trigram_PL
    trigram_df["PL_bi_base"] = [bigram_PL_dict[s] for s in trigram_df['bin'].str[:2].to_list()]

    # 16-series, with one extra monogram at the top.
    ref = trigram_df['bin'].str[-1].to_list()
    trigram_df["PL_bi16_candidates"] = [[tup[0] for tup in bigram_PL if tup[1][0] == n] for n in ref]


    qjbm = [None] * 8
    acu = [None] * 8

    for g ,a, v in QJBM:
        qjbm[trigram_df[trigram_df['name'] == g].index[0]] = v
        acu[trigram_df[trigram_df['name'] == g].index[0]] = a

    trigram_df["qjbm"] = qjbm
    trigram_df["qjbm_master_pt"] = acu
    trigram_df["qjbm_intersect_pt"] = trigram_df["qjbm_master_pt"].apply(lambda x: [list(filter(lambda y: y != x, pair))[0]
                                                                                    for pair in bamai_jiaohui if x in pair][0])
    trigram_df["hetu_id"] = [id for id, name in HETU_index][:8]
    trigram_df["hetu_name"] = [name for id, name in HETU_index][:8]

    return trigram_df


def build_relations_dict():

    comb_list = TRI_HEX_REL.split("\n")
    comb_list = [s.split("|") for s in comb_list]
    comb_list = [lst for lst in comb_list if len(lst) > 1]
    comb_list.pop(1)
    comb_list = [list(filter(None, lst)) for lst in comb_list]
    comb_list = [[item.strip() for item in lst] for lst in comb_list]

    trigram = comb_list.pop(0)[2:]
    trigram = [item[-1] for item in trigram]

    inner_outer_dict = {}  # 內外卦
    for lst in comb_list:
        lst.pop(0)
        nei = lst[0][-1]
        for item in lst[1:]:
            idx = lst.index(item)-1
            wai = trigram[idx][0]
            inner_outer_dict[item[0]] = (nei, wai)

    return inner_outer_dict


def build_16_series_df():
    PL_16_series = set(list(zip(hexagram["PL_16"], hexagram["PL_16_bin"])))
    PL_16_series_df = pd.DataFrame(PL_16_series, columns=['series','bin'])
    PL_16_series_df["id"] = PL_16_series_df['bin'].apply(lambda x: int(str(x), 2) + 1)
    PL_16_series_df.set_index("id", inplace=True)
    PL_16_series_df.sort_index(inplace=True)
    petit_yinyang = "陰 陰 陽 陰陽 陰 陽 陰 陽 陰 陽 陽 陰陽 陰 陽 陰 陽".split(" ")
    PL_16_series_df["petit_yinyang"] = petit_yinyang


    return PL_16_series_df


def find_petit_yin():

    mutations = list(product(["T", "G", "C", "A", "O"], repeat = 2))
    petit_yin = []
    for i, doublet in enumerate(mutations):
        # print(i, doublet)
        if "O" in doublet:
            petit_yin.append(doublet)

    return petit_yin

def petit_yin_candidates():

    petit_yin = find_petit_yin()
    candidates = []
    for tup in petit_yin:
        if tup == ("O", "O"):
            candidates.append("TT")
        else:
            n, w = tup

            bool = np.array(PL_16_series['series'].str[0] == n)
            arr = np.array(PL_16_series['series'])
            result = arr[bool]
            if any(result):
                candidates.append(list(result))

            bool = np.array(PL_16_series['series'].str[1] == w)
            result = arr[bool]
            if any(result):
                candidates.append(list(result))

    return(candidates)


def build_petit_yin_df():
    petit_yin_df = pd.DataFrame({"find": ["".join(tup) for tup in  find_petit_yin()]})
    petit_yin_df['bi_candidates'] = petit_yin_candidates()
    petit_yin_df['quadrant'] = [tup[0] for tup in petit_yin_df.find[:4].tolist()] + [None]*4 + ["center"]
    petit_yin_df['bin'] = [(bigram_PL_bin_dict.get(n, "..") + bigram_PL_bin_dict.get(w, "..")) for n, w in petit_yin_df.find.tolist()]

    trigram = build_trigram_df()

    tri_candidates = [None] * len(petit_yin_df.bin.tolist())
    for i, s in enumerate(petit_yin_df['bin'].str[:3].tolist()):
        if s == "...":
            s = "O"
            tri_candidates[i] = "中"
            continue
        candidates = []
        for j, b in enumerate(trigram.bin.tolist()):
            if re.search(s, b):
                candidates.append(trigram.iloc[j,1])

        tri_candidates[i] = candidates

    petit_yin_df['tri_candidates'] = tri_candidates


    # 內卦為 O 的都是陰卦：坤（母）、巽（長女）、離（中女）、兌（少女）
    # 篩除陰卦
    petit_yin_df.loc[petit_yin_df.find.str.match("O."), 'tri_candidates'] = \
        petit_yin_df['tri_candidates'][petit_yin_df.find.str.match("O.")].apply(
        lambda x: [i for i in x if i not in ["乾","震","坎","艮"]])
    # 篩除陽卦
    petit_yin_df.loc[petit_yin_df.find.str.match("[ACTG]O"), 'tri_candidates'] = \
        petit_yin_df['tri_candidates'][petit_yin_df.find.str.match("[ACTG]O")].apply(
        lambda x: [i for i in x if i not in ["坤","巽","離","兌"]])
    # unlist lists with only 1 item
    petit_yin_df['tri_candidates'] = petit_yin_df['tri_candidates'].apply(lambda x: x[0] if len(x) == 1 else x)

    # sync bi_candidates with tri results
    petit_yin_df.loc[petit_yin_df.find != "OO", 'bi_candidates'] = petit_yin_df[petit_yin_df.find != "OO"]['bi_candidates'].apply(lambda x: [i for i in x if i not in ["TT"]])

    return petit_yin_df


hexagram = build_hexagram_df()
trigram = build_trigram_df()
PL_16_series = build_16_series_df()
hexagram["PL_16_yinyang"] = hexagram["PL_16"].map(lambda x: PL_16_series.loc[PL_16_series.series==f"{x}", "petit_yinyang"].values.item())

print(hexagram)


# hetu_trigram = list(zip(HETU_index, trigram.name.to_list() + 2*[("O", "中")]))
# hetu_trigram = [t1+t2 for t1, t2 in hetu_trigram]
# # hetu_df = pd.DataFrame(hetu_trigram)
#
# hetu_trigram.sort(key=lambda tup: tup[0])
# print(hetu_trigram)

# p_yin = build_petit_yin_df()
# p_yin_candidates = p_yin.bi_candidates.tolist()
# p_yin_series = set([i for l in p_yin_candidates for i in l])
# print(PL_16_series)
# print(p_yin)

# get pialoux bigram code
# print(hexagram.query("PL_bi == 'TAA'").name.tolist()[0])

# print(PL_16_series)
# print(hexagram.query("PL_16 == 'TG'")['bin'])
# print(trigram.sort_values("hetu_id"))


# trigram = [tuple(item.split(" ")) for item in comb_list[0]]
# trigram.pop(0)
#
# return trigram, comb_list