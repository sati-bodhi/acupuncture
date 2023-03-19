import sqlite3 as sql
import pandas as pd
import ephem
from ephem import degree
from timezonefinder import TimezoneFinder
from datetime import datetime
from math import pi
import geocoder
from pathlib import Path
import os

DB_PATH = Path(os.path.abspath(__file__)).parents[0] / "acu.db"

yinyang_df = pd.DataFrame(
    {
        "id": [1, 0],
        "zh": list("陽陰"),
        "en": ["yang", "yin"],
        "fr": ["yang", "inn"],
    }
)

qixue_df = pd.DataFrame(
    {
        "id": [0, 1],
        "zh": ["血", "氣"],
        "en": ["blood", "energy"],
        "fr": ["sang", "energie"],
    }
)

rel_lvl_df = pd.DataFrame(  # Relative level: excess or deficiency 虛實.
    {
        "id": ["-", "+"],
        "zh": list("虛實"),
        "en": ["deficient", "excess"],
        "fr": ["vide", "plénitude"],
    }
)

treatment_df = pd.DataFrame(
    {
        "id": ["++", "--"],
        "zh": ["補", "瀉"],
        "en": ["tonify", "disperse"],
        "fr": ["tonifier", "disperser"],
    }
)

MERIDIAN = ("LU", "LI", "ST", "SP", "HT", "SI", "BL", "KI", "PC", "TE", "GB", "LR")
BRANCH = ('子', '丑', '寅', '卯', '辰', '巳', '午', '未', '申', '酉', '戌', '亥')
ELEM = ("木", "火", "土", "金", "水")
PHENOM = ("風", "火", "濕", "燥", "寒")
phenom_dict = {e: p for e, p in zip(ELEM, PHENOM)}

elem_df = pd.DataFrame(
    {
        "id":["W", "F", "E", "M", "H"],
        "elem": ELEM,
        "phenom": PHENOM,
    }
)


def blood_energy_status():
    # 氣血陰陽
    # Diagnostics for energy Quantity and Quality

    pulse_df = pd.DataFrame(  # describes energy QUALITY.
        {
            "id": ["W", "I", "F", "S"],
            "zh": list("弦洪浮沉"),
            "en": ["wiry", "immense", "floating", "sunken"],  # pulse description
            "fr": ["tendu", "vaste", "flottant", "profond"],
            "yinyang_id": [1,0,1,0],
            "rel_lvl_id": list("++--"),
        }
    )

    renying_df = pd.DataFrame(  # describes (relative) energy Quantity
        {
            "renying":["L", "R"],
            "yinyang_id": [1,0],  # 陽氣陰血
        }
    )

    renying_df["qixue"] = renying_df["yinyang_id"].map(lambda x: qixue_df.query(f"id == {x}").zh.item())

    quantity = {
        "1": "ST36",  # 氣；足三里
        "0": "SP6",  # 血；三陰交
    }

    meridian_quantity = {
        "1": "LI4",  # 陽經；合谷
        "0": "PC6",  # 陰經；內關
    }

    quality = {
        "10": "GV14",  # 氣陰；大椎
        "11": "GV20",  # 氣陽；百會
        "00": "CV6",  # 血陰；氣海
        "01": "CV12",  # 血陽；中脘
    }

    stronger_list = []
    pulse_list = []
    sbj_list = []
    quality_list = []
    status_list = []
    diagnose_list = []

    for stronger in renying_df.renying:
        for pulse in pulse_df.id:
            stronger_list.append(stronger)
            pulse_list.append(pulse)
            rel_lvl_id = pulse_df.loc[pulse_df.id == pulse, "rel_lvl_id"].item()
            rel_lvl = rel_lvl_df.query(f"id == '{rel_lvl_id}'").zh.item()
            status_list.append(rel_lvl_id)

            qual_id = pulse_df.loc[pulse_df.id == pulse, "yinyang_id"].item()
            yinyang = yinyang_df.query(f"id == {qual_id}").zh.item()
            quality_list.append(str(qual_id))

            if rel_lvl_id == "+":
                sbj_id = renying_df.loc[renying_df.renying == stronger, "yinyang_id"].item()
                subject = renying_df.loc[renying_df.renying == stronger, "qixue"].item()
                sbj_list.append(str(sbj_id))
                diagnose_list.append(subject + yinyang + rel_lvl)
            else:
                sbj_id = renying_df.loc[renying_df.renying != stronger, "yinyang_id"].item()
                subject = renying_df.loc[renying_df.renying != stronger, "qixue"].item()
                sbj_list.append(str(sbj_id))
                diagnose_list.append(subject + yinyang + rel_lvl)

    # Treatment of energy Quantity

    treat_qty_list = []

    for i, sbj in enumerate(sbj_list):
        qual = quality_list[i]
        stat = status_list[i]

        if stat == "-":  # 虛脈
            if sbj == "0":
                treat_quantity = [(quantity["0"], "++")]  # 陰虛補陰
                treat_qty_list.append(treat_quantity)

            else:
                treat_quantity = [(quantity["1"], "++"), (quantity["0"], "++")]  # 陽虛補陽，再補陰
                treat_qty_list.append(treat_quantity)

        elif stat == "+":  # 實脈

            if sbj == "0":
                treat_quantity = [(quantity["1"], "++")]  # 陰實補陽
                treat_qty_list.append(treat_quantity)
            else:
                treat_quantity = [(quantity["1"], "--")]  # 陽實瀉陽
                treat_qty_list.append(treat_quantity)


    # Treatment of energy Quality

    treat_qual_list = []
    for i, sbj in enumerate(sbj_list):
        qual = quality_list[i]
        stat = status_list[i]

        if stat == "-":  # 虛脈
            if qual == "0":
                treat_quality = [(quality[sbj + "0"], "++")]  # 陰虛補陰
                treat_qual_list.append(treat_quality)
            else:
                treat_quality = [(quality[sbj + "1"], "++"), (quality[sbj + "0"], "++")]  # 陽虛補陽，再補陰
                treat_qual_list.append(treat_quality)

        elif stat == "+":  # 實脈
            if qual == "0":
                treat_quality = [(quality[sbj + "1"], "++")]  # 陰實補陽
                treat_qual_list.append(treat_quality)
            else:
                treat_quality = [(quality[sbj + "1"], "--")]  # 陽實瀉陽
                treat_qual_list.append(treat_quality)


    # Treatment of yinyang meridian relitive Quantity

    meridian_yinyang_prescription = [
                            [(meridian_quantity["1"], "++")],  # 陰有餘補陽
                            [(meridian_quantity["0"], "++")],  # 陰不足補陰
                            [(meridian_quantity["1"], "--")],  # 陽有餘瀉陽
                            [(meridian_quantity["1"], "++"), (meridian_quantity["0"], "++")],  # 陽不足補陽、再補陰
                            ]

    meridian_yinyang_df = pd.DataFrame(
        {
            "rel_qty":["0+", "0-", "1+", "1-"],  # relative quantity
            "prescription": [str(item) for item in meridian_yinyang_prescription],
        }
    )

    diagnose_df = pd.DataFrame(
        {
            "stronger": stronger_list,
            "pulse": pulse_list,
            "subject": sbj_list,
            "quality": quality_list,
            "status": status_list,
            "diagnose": diagnose_list,
            "treat_qty": [str(item) for item in treat_qty_list],  # treat quantity
            "treat_qual": [str(item) for item in treat_qual_list],  # treat quality
        }
    )

    with sql.connect(DB_PATH) as conn:
        diagnose_df.to_sql("diagnose_general", conn, if_exists='replace', index=False)
        treatment_df.to_sql("treatment_action", conn, if_exists='replace', index=False)
        pulse_df.to_sql("pulse", conn, if_exists='replace', index=False)
        meridian_yinyang_df.to_sql("treat_meridian_qty", conn, if_exists='replace', index=False)


def six_phenomena():
    """六氣"""
    phenomena_df = pd.DataFrame(
        {
            "id": ["ty", "YM", "sy", "TY", "jy", "SY"],
            "yinyang_tri": "太陰.陽明.少陰.太陽.厥陰.少陽".split("."),
            "yinyang_tri_tr": ["taiyin", "yangming", "shaoyin", "taiyang", "jueyin", "shaoyang"],
            "phenomena": ["濕", "燥", "熱", "寒", "風", "暑"],
            "phenomena_en": ["dampness", "dryness", "heat", "cold", "depression", "pressure"],
            "phenomena_fr": ["humidité", "sécheresse", "chaleur", "froid",  "chaleur", "vent"],
        }
    )

    tri_opp = [("ty", "YM"), ("sy", "TY"), ("jy", "SY")]
    phenom_opp = [("濕", "燥"), ("熱", "寒"), ("風", "暑")]
    phenom_elem_opp = [("濕", "燥"), ("火", "寒"), ("風", "火")]

    def get_opposing_tri(tri):
        for pair in tri_opp:
            if tri in pair:
                opp = pair[pair.index(tri)-1]

        return opp

    def get_opposing_phenom(phenom, category="tri"):
        if category == "tri":
            for pair in phenom_opp:
                if phenom in pair:
                    opp = pair[pair.index(phenom)-1]
                    return opp

        elif category == "elem":
            if phenom in ["熱", "暑"]:
                opp = get_opposing_phenom(phenom)
                return opp
            else:
                for pair in phenom_elem_opp:
                    if phenom in pair:
                        opp = pair[pair.index(phenom)-1]
                        return opp

    mother_son = meridian_treatment()

    with sql.connect(DB_PATH) as conn:

        c = conn.cursor()

        # Update pentashu with element phenom data

        for elm in ELEM:
            c.execute(f'''
            UPDATE pentashu
            SET phenom_elem = '{phenom_dict[elm]}'
            WHERE elem = '{elm}'; 
            ''')

        # Update pentashu with yinyang triple qualities phenom data
        for tri in phenomena_df.id:
            c.execute(f'''
            UPDATE pentashu
            SET phenom_tri = '{phenomena_df.query(f"id == '{tri}'")["phenomena"].item()}'
            WHERE yinyang_tri = '{tri}';
            ''')

        # Treatment Principles
        # 補母瀉子（預防）
        # 五行（排邪氣）

        c.execute('''
        SELECT ID, yinyang_tri FROM Meridian
        WHERE limb = "F" AND meridianExtra = 0
        ''')

        root_meridian = c.fetchall()

        root_treatment = {}  # 根補穴與根瀉穴
        for meridian, tri in root_meridian:
            root_treatment[tri] = mother_son[meridian]

        phenomena_df['root_tonify'] = [root_treatment[id][0] for id in phenomena_df['id']]
        phenomena_df['root_disperse'] = [root_treatment[id][1] for id in phenomena_df['id']]
        phenomena_df['root_knot'] = ["CV12", "ST8", "CV23", "BL1", "CV18", "BL2"]  # 根結穴，聯接同質手部經脈

        # Environment pathogen dataframe

        env_pathogen_df = pd.DataFrame({
            "ID": ["ty", "YM", "sy", "TY", "jy", "SY"],
            "pathogen": phenomena_df['phenomena'],
            "treatment": [get_opposing_phenom(item) for item in phenomena_df['phenomena']],
            "elem_treatment": [get_opposing_phenom(item, "elem") for item in phenomena_df['phenomena']],
        })

        phenomena_df.to_sql("env_phenomena", conn, if_exists='replace', index=False)
        env_pathogen_df.to_sql("env_pathogen", conn, if_exists='replace', index=False)


def meridian_treatment():
    with sql.connect(DB_PATH) as conn:
        c = conn.cursor()

        mother_son_dict = {}
        yinyang_tri = []

        c.execute('''
        SELECT ID, name, meridian_id, yinyang_tri, elem FROM pentashu
        WHERE cardinal = 1;
        ''')

        rslt = c.fetchall()
        if rslt is not None:
            cardinals = rslt
        else:
            pass

        for point in cardinals:
            elem = point[-1]
            meridian = point[2]

            elem_mother = ELEM[ELEM.index(elem) - 1]
            try:
                elem_son = ELEM[ELEM.index(elem) + 1]
            except IndexError:
                elem_son = ELEM[0]

            c.execute(f'''
            SELECT ID, yinyang_tri FROM pentashu
            WHERE meridian_id = "{meridian}" AND elem = "{elem_mother}";
            ''')

            m, tri = c.fetchone()
            if m is not None:
                mother = m
                yinyang_tri.append(tri)
            else:
                pass

            c.execute(f'''
            SELECT ID FROM pentashu
            WHERE meridian_id = "{meridian}" AND elem = "{elem_son}";
            ''')

            s = c.fetchone()
            if s is not None:
                son = s[0]
            else:
                pass

            mother_son_dict[meridian] = (mother, son)
            c.execute(f'''
            UPDATE Meridian
            SET tonify = "{mother}", disperse = "{son}"
            WHERE ID = "{meridian}";
            ''')

        return mother_son_dict


def horary():
    """The horary cycle."""
    labels = BRANCH[2:] + BRANCH[:2]

    time = list(range(1, 24, 2))
    time = time[1:] + time[:1]
    time_disp = [str(h)+":00" for h in time]

    entry_pt = [1, 4, 8, 1, 1, 1, 1, 1, 1, 1, 1, 1]
    exit_pt = [7, 20, 42, 21, 9, 18, 67, 22, 8, 21, 41, 14]

    entry_pt = [MERIDIAN[i] + str(idx) for i, idx in enumerate(entry_pt)]
    exit_pt = [MERIDIAN[i] + str(idx) for i, idx in enumerate(exit_pt)]

    horary_df = pd.DataFrame(
        {
            "ID": MERIDIAN,
            "time": time,
            "entry": entry_pt,
            "exit": exit_pt,
        }
    )

    hour_conv_df = pd.DataFrame(
        {
            "start": time,
            "end": [t + 1 for t in time],
            "name": labels,
        }
    )

    with sql.connect(DB_PATH) as conn:

        c = conn.cursor()
        horary_df.to_sql("horary", conn, dtype={'ID': 'TEXT PRIMARY KEY'}, if_exists='replace', index=False)
        hour_conv_df.to_sql("hour_conv", conn, dtype={'start': 'TEXT PRIMARY KEY'}, if_exists='replace', index=False)


def solartime_by_ip():
    sun = ephem.Sun()

    loc = ephem.Observer()
    loc.date = ephem.date(datetime.utcnow())

    g = geocoder.ip('me')
    data = g.json
    timezone = data["raw"]["timezone"]
    loc.lat, loc.long = [ephem.degrees(str(latlng)) for latlng in g.latlng]

    sun.compute(loc)
    loc_time = ephem.date(loc.date + (loc.long / pi * 12) * ephem.hour)

    # print(loc_time, timezone)

    return loc_time, timezone


def solartime_by_city(city):

    sun = ephem.Sun()
    loc = ephem.city(city)

    # Calculate departure location solar time
    sun.compute(loc)
    loc_time = ephem.date(loc.date + (loc.long / pi * 12) * ephem.hour)
    tf = TimezoneFinder()
    loc_tz = tf.timezone_at(lng=loc.long/degree, lat=loc.lat/degree)

    return loc_time, loc_tz


def horary_calc(depart, local):
    """
    Input local and departure venue horary meridian id
    to get prescription.
    """

    if depart == local:
        return

    with sql.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute(f'''
            SELECT ID from horary 
            ORDER BY time;
        ''')
        horary_list = [meridian[0] for meridian in c.fetchall()]
        depart_id = horary_list.index(depart)
        local_id = horary_list.index(local)

        if local_id > depart_id:
            traverse_pts = horary_list[depart_id:local_id+1]
        else:
            traverse_pts = horary_list[depart_id:] + horary_list[:local_id + 1]

        luo_in = None
        luo_out = None

        if len(traverse_pts) > 6:
            luo_out = traverse_pts[0]
            luo_in = traverse_pts[6]
            traverse_pts = traverse_pts[6:]

            with sql.connect(DB_PATH) as conn:
                c = conn.cursor()
                c.execute(f'''
                SELECT acuID, desc_zh FROM Luo
                WHERE acuID LIKE "{luo_in}%"
                ''')

                luo_tonify = c.fetchone()
                luo_tonify_presc = (luo_tonify[0], '++')
                luo_tonify_desc = luo_tonify[1]

                c.execute(f'''
                SELECT acuID, desc_zh FROM Luo
                WHERE acuID LIKE "{luo_out}%"
                ''')

                luo_disperse = c.fetchone()
                luo_disperse_presc = (luo_disperse[0], '--')
                luo_disperse_desc = luo_disperse[1]

        to_tonify = traverse_pts[1:]
        to_disperse = traverse_pts[:-1]

        tonify = []
        tonify_vessel = []
        for pt in to_tonify:
            c.execute(f'''
                SELECT entry, meridianName_abbrev FROM horary
                JOIN Meridian on Meridian.ID = horary.ID
                WHERE horary.ID = "{pt}"; 
            ''')
            entry_pt, entry_vessel = c.fetchone()
            tonify.append((entry_pt, '++'))
            tonify_vessel.append(entry_vessel)

        disperse = []
        disperse_vessel = []
        for pt in to_disperse:
            c.execute(f'''
                SELECT exit, meridianName_abbrev FROM horary
                JOIN Meridian on Meridian.ID = horary.ID
                WHERE horary.ID = "{pt}"; 
            ''')
            exit_pt, exit_vessel = c.fetchone()
            disperse.append((exit_pt, '--'))
            disperse_vessel.append(exit_vessel)

    if luo_in:
        return True, \
               [(luo_tonify_presc, luo_disperse_presc),
                (luo_tonify_desc, luo_disperse_desc)], \
               [list(zip(tonify, disperse)),
                list(zip(tonify_vessel, disperse_vessel))]
    else:
        return False, [list(zip(tonify, disperse)),
                       list(zip(tonify_vessel, disperse_vessel))]


if __name__ == '__main__':

    print(horary_calc("BL", "SI"))
    # blood_energy_status()
    # six_phenomena()
    solartime_by_ip()


