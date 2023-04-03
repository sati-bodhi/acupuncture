from acupuncture.build_db import *
from tabula import read_pdf
import numpy as np
from copy import deepcopy
import re
from tabulate import tabulate


BASE_SCRIPT = f"""
CREATE TABLE IF NOT EXISTS pentaShu_base (
ID TEXT PRIMARY KEY, -- Acupoint ID
attrib TEXT, -- 井、滎、輸、經、合
attrib_en TEXT GENERATED ALWAYS
                AS (CASE
                        WHEN attrib = "井" THEN "well"
                        WHEN attrib = "滎" THEN "spring"
                        WHEN attrib = "輸" THEN "stream"
                        WHEN attrib = "經" THEN "river"
                        WHEN attrib = "合" THEN "sea"
                    END), 
elem TEXT, -- 木、火、土、金、水——注意陰經陽經的差異
cardinal BOOLEAN DEFAULT "0" NOT NULL CHECK (cardinal IN (0, 1)), -- 本穴，由五行來推斷
FOREIGN KEY (ID) REFERENCES Acupoint(ID));
"""

PENTASHU_SCRIPT = f"""
DROP TABLE IF EXISTS pentaShu;

CREATE TABLE pentaShu AS
SELECT `pentaShu_base`.`ID` AS ID, 
        acuName_zh AS name, 
        attrib, 
        elem,
        `Meridian`.`ID` AS `meridian_id`,
        `meridianName_zh` AS meridian,
        `meridianName_abbrev` AS meridian_abbrev, 
        limb as `meridian_limb`,
        yinyang,
        yinyang_tri, 
        cardinal
    FROM pentaShu_base
    JOIN Acupoint ON `pentaShu_base`.`ID` = `Acupoint`.`ID`
    JOIN Meridian ON `Meridian`.`ID` = `Acupoint`.`meridianID`;
    
    ALTER TABLE pentaShu ADD COLUMN
    phenom_tri;
    
    ALTER TABLE pentaShu ADD COLUMN
    phenom_elem;
    
    ALTER TABLE pentaShu ADD COLUMN
        label GENERATED ALWAYS 
        AS (CASE 
                WHEN cardinal = 1 THEN attrib ||"（" || elem || "）"|| "；"|| meridian_abbrev || "本穴"
                ELSE attrib ||"（" || elem || "）"
            END);
"""

ORGAN_VISCERA =f"""
DROP TABLE IF EXISTS Organ_Viscera;

CREATE TABLE Organ_Viscera AS
SELECT ID, meridianName_abbrev AS zh_name, meridianName_en AS en_name FROM Meridian
WHERE meridianExtra = 0;
"""

BIAOLI = {
    # 臟腑表裡關係
    "GB": "LR",
    "SI": "HT",
    "ST": "SP",
    "LI": "LU",
    "BL": "KI",
    "TE": "PC",
}


LHan = [[0x2E80, 0x2E99],    # Han # So  [26] CJK RADICAL REPEAT, CJK RADICAL RAP
        [0x2E9B, 0x2EF3],    # Han # So  [89] CJK RADICAL CHOKE, CJK RADICAL C-SIMPLIFIED TURTLE
        [0x2F00, 0x2FD5],    # Han # So [214] KANGXI RADICAL ONE, KANGXI RADICAL FLUTE
        0x3005,              # Han # Lm       IDEOGRAPHIC ITERATION MARK
        0x3007,              # Han # Nl       IDEOGRAPHIC NUMBER ZERO
        [0x3021, 0x3029],    # Han # Nl   [9] HANGZHOU NUMERAL ONE, HANGZHOU NUMERAL NINE
        [0x3038, 0x303A],    # Han # Nl   [3] HANGZHOU NUMERAL TEN, HANGZHOU NUMERAL THIRTY
        0x303B,              # Han # Lm       VERTICAL IDEOGRAPHIC ITERATION MARK
        [0x3400, 0x4DB5],    # Han # Lo [6582] CJK UNIFIED IDEOGRAPH-3400, CJK UNIFIED IDEOGRAPH-4DB5
        [0x4E00, 0x9FC3],    # Han # Lo [20932] CJK UNIFIED IDEOGRAPH-4E00, CJK UNIFIED IDEOGRAPH-9FC3
        [0xF900, 0xFA2D],    # Han # Lo [302] CJK COMPATIBILITY IDEOGRAPH-F900, CJK COMPATIBILITY IDEOGRAPH-FA2D
        [0xFA30, 0xFA6A],    # Han # Lo  [59] CJK COMPATIBILITY IDEOGRAPH-FA30, CJK COMPATIBILITY IDEOGRAPH-FA6A
        [0xFA70, 0xFAD9],    # Han # Lo [106] CJK COMPATIBILITY IDEOGRAPH-FA70, CJK COMPATIBILITY IDEOGRAPH-FAD9
        [0x20000, 0x2A6D6],  # Han # Lo [42711] CJK UNIFIED IDEOGRAPH-20000, CJK UNIFIED IDEOGRAPH-2A6D6
        [0x2F800, 0x2FA1D]]  # Han # Lo [542] CJK COMPATIBILITY IDEOGRAPH-2F800, CJK COMPATIBILITY IDEOGRAPH-2FA1D


def build_re():
    L = []
    for i in LHan:
        if isinstance(i, list):
            f, t = i
            try:
                f = chr(f)
                t = chr(t)
                L.append('%s-%s' % (f, t))
            except:
                pass  # A narrow python build, so can't use chars > 65535 without surrogate pairs!

        else:
            try:
                L.append(chr(i))
            except:
                pass

    RE = '[%s]' % ''.join(L)
    print('RE:', RE.encode('utf-8'))
    return re.compile(RE, re.UNICODE)


# 五輸穴

def get_shu_table(connect: sql.Connection):
    session = Session()
    with session.get('http://cht.a-hospital.com/w/五输穴') as resp:
        resp.raise_for_status()
        df = pd.read_html(resp.content)[2]
        df.rename(columns={'Unnamed: 0':'十二正經'}, inplace=True )

        # df.to_sql('pentaShu_raw', connect, if_exists='replace', index=False)

    return df


def create_tables(connect: sql.Connection):
    """Run script to create tables for specific points."""
    c = connect.cursor()
    c.executescript(BASE_SCRIPT)


def build_pentashu_data(connect: sql.Connection):
    df = get_shu_table(connect)

    c = connect.cursor()
    for label, values in list(df.iteritems())[1:]:
        for value in values:
            acu_id = get_id(value, with_alias=True, fuzzy=False)
            if not acu_id:
                acu_id = get_id(transliterate(value))
                c.execute(f"""
                INSERT INTO acuAlias (acuID, aliasName, aliasSrc)
                VALUES("{acu_id}", "{value}", "醫學百科：五输穴")
                """)

            try:
                c.execute(f'''
                INSERT INTO pentaShu_base (ID, attrib)
                VALUES ("{acu_id}", "{label.replace('穴', '')}");
                ''')
            except sql.IntegrityError:
                print(f"{acu_id} already exist in pentaShu_base（五行）table.")

    # 五行

    c.execute(f'''
    SELECT `pentaShu_base`.`ID`, acuName_zh, attrib, `Meridian`.`ID`, yinyang FROM pentaShu_base
    JOIN Acupoint ON `pentaShu_base`.`ID` = `Acupoint`.`ID`
    JOIN Meridian ON `Meridian`.`ID` = `Acupoint`.`meridianID`
    ''')

    base = c.fetchall()
    shu_attribs = ("井","滎","輸","經","合")
    yin_elem = ("木","火","土","金","水")
    yang_elem = ("金","水","木","火","土")
    organ = ("LR", "HT", "SP", "LU", "KI")

    for item in base:
        acu_id, name, attrib, meridian, yinyang = item
        elem_id = shu_attribs.index(attrib)

        if yinyang == 0 :  # 陰經：木火土金水
            elem = yin_elem[elem_id]
            if meridian == "PC":
                organ_elem = "相火"
            else:
                organ_id = organ.index(meridian)  # 可用 yin_elem[organ_id] 來查五臟的五行屬性
                organ_elem = yin_elem[organ_id]

        else:  # 陽經：金水木火土
            elem = yang_elem[elem_id]
            if meridian == "TE":
                organ_elem = "相火"
            else:
                organ_id = organ.index(BIAOLI[meridian])
                organ_elem = yin_elem[organ_id]

        if organ_elem == elem or elem in organ_elem:  # 本穴，腧穴的五行屬性與其所代表的臟腑相同。
            c.executescript(f'''
            UPDATE pentaShu_base
            SET elem = "{elem}",
                cardinal = 1
            WHERE ID = "{acu_id}";
            ''')
        else:
            c.execute(f'''
            UPDATE pentaShu_base
            SET elem = "{elem}"
            WHERE ID = "{acu_id}";
            ''')

    # Build full table with joined data

    c.executescript(PENTASHU_SCRIPT)


def mu_shu_points():
    df_list = read_pdf("Pialoux_AC_guide.pdf", pages="124-125", stream=True)

    df = df_list[0]
    z = zip(df.columns[1:].to_list(), df.iloc[0, 1:].to_list())
    df.columns = [df.columns[0]] + [x+" "+y for x,y in z]
    df.columns = [s.strip() for s in df.columns]
    df = df.drop(0, axis=0)
    df = df.drop("Element", axis=1)
    col = df.columns
    df_list[0] = df

    df = df_list[1]
    df = df.drop(0, axis=0)
    df = df.drop("Element", axis=1)
    df.columns = col
    df_list[1] = df

    # Somatic organ-jingbie Front-Mu and Back-Shu points (seasonal, semi-chronic)

    classic_pts = pd.concat(df_list)
    classic_pts.loc[:,'Blood: Mu points'] = [s.replace(" ", "") for s in classic_pts['Blood: Mu points']]
    classic_pts.loc[:,'Energy: Shu points'] = [s.replace(" ", "") for s in classic_pts['Energy: Shu points']]
    classic_pts = classic_pts.replace("None", np.nan)
    classic_pts.reset_index(drop=True, inplace=True)

    # Somatic organ-function Front-Mu and Back-Shu points (chronic)

    df = read_pdf("Pialoux_AC_guide.pdf", pages="126", stream=True)[0]
    df = df.drop([0,1], axis=0)
    df = df.drop("Element", axis=1)
    df.columns = col

    acu_func_list = list(df.iloc[:, 2])
    acu_func_list = [item.split("-") for item in acu_func_list]
    acu_func_list = [lst+[acu_func_list[i+1][-1]] if len(lst) == 1 and "None" not in lst else lst for i, lst in enumerate(acu_func_list) ]
    acu_func_list = [lst for lst in acu_func_list if "" not in lst]
    acu_list = [lst[0].replace(" ", "") if len(lst) >1 else None for lst in acu_func_list]
    func_list = [lst[1].strip() if len(lst) >1 else None for lst in acu_func_list]

    df = df.dropna()
    df = deepcopy(df)
    df.loc[:, 'Blood: Mu points']  = [s.replace(" ", "") for s in df['Blood: Mu points']]
    df.loc[:, 'Energy: Shu points'] = acu_list
    df['Function'] = func_list
    soma_func = df.fillna(value=np.nan)
    soma_func.reset_index(drop=True, inplace=True)

    # Emotional organ-jingbie Front-Mu and Back-Shu points (seasonal, semi-chronic)

    df_list = read_pdf("Pialoux_AC_guide.pdf", pages="127-128", stream=True, multiple_tables=True)
    df = df_list[0]
    df = df.drop([0], axis=0)
    df = df.drop("Element", axis=1)
    df.columns = col

    mu = df['Blood: Mu points'].to_list()
    df.loc[:, 'Blood: Mu points'] = [s.replace(" ", "") for s in mu]
    shu = df['Energy: Shu points'].to_list()
    df.loc[:, 'Energy: Shu points'] = [s.replace(" ", "") for s in shu]
    emo_jb = df
    emo_jb.reset_index(drop=True, inplace=True)

    # Emotional organ-function Front-Mu and Back-Shu points (chronic)

    df_list = df_list[1:]
    for i, df in enumerate(df_list):
        df = df.drop(0, axis=0)
        df = df.drop("Element", axis=1)
        df.columns = col

        mu = df['Blood: Mu points'].to_list()
        df.loc[:, 'Blood: Mu points'] = [s.replace(" ", "") for s in mu]
        shu = df['Energy: Shu points'].to_list()
        df.loc[:, 'Energy: Shu points'] = [s.replace(" ", "") for s in shu]

        df_list[i] = df

    emo_func = pd.concat(df_list)
    emo_func.reset_index(drop=True, inplace=True)

    return classic_pts, soma_func, emo_jb, emo_func


def build_mu_shu_data(connect: sql.Connection):
    c = connect.cursor()
    soma_jb, soma_func, emo_jb, emo_func = mu_shu_points()
    mu_shu_list = [soma_jb, soma_func, emo_jb, emo_func]

    zangfu_tr = {
        "Liver": "肝",
        "Gallbladder":"膽",
        "Heart":"心",
        "Small Intestine": "小腸",
        "Pericardium": "心包",
        "Triple Burner": "三焦",
        "Spleen": "脾",
        "Stomach": "胃",
        "Lungs": "肺",
        "Large Intestine": "大腸",
        "Kidneys": "腎",
        "Bladder": "膀胱",
    }

    c.executescript('''
    DROP TABLE IF EXISTS Mu_Shu;
    
    CREATE TABLE Mu_Shu(
    ID INTEGER PRIMARY KEY AUTOINCREMENT, 
    acuID TEXT,
    mu_shu TEXT NOT NULL,  -- use "mu" or "shu"
    org_vis TEXT, -- organ and viscera （臟腑）
    som_emo TEXT, -- Somatic（身體） or Emotional（精神）
    jb_func TEXT -- Jingbie（經別） or Function（功能）
    );
    ''')

    i=0
    for cat in ("肉體", "精神"):
        for lvl in ("經別", "功能"):
            df = mu_shu_list[i]
            i += 1
            for j in range(12):
                org_vis = df.iloc[j,0]
                mu = df.iloc[j,1]
                shu = df.iloc[j,2]

                if mu and not(pd.isna(mu)) and mu != "None":
                    c.execute(f'''
                    INSERT INTO Mu_Shu ("acuID","mu_shu","org_vis", "som_emo", "jb_func")
                    VALUES (
                            (SELECT ID FROM Acupoint
                            WHERE cl_ID = "{mu}"), 
                            "募", "{zangfu_tr[org_vis]}", "{cat}", "{lvl}");
                    ''')

                if shu and not(pd.isna(shu)) and shu != "None":
                    c.execute(f'''
                    INSERT INTO Mu_Shu ("acuID","mu_shu","org_vis", "som_emo", "jb_func")
                    VALUES (
                            (SELECT ID FROM Acupoint
                            WHERE cl_ID = "{shu}"), 
                            "俞", "{zangfu_tr[org_vis]}", "{cat}", "{lvl}");
                    ''')


def update_org_vis_table(connect: sql.Connection):
    c = connect.cursor()
    c.executescript(ORGAN_VISCERA)
    c.execute('''
    SELECT ID, zh_name FROM Organ_Viscera;
    ''')
    zh_name = [(id, re.sub("經", "", name)) for id, name in c.fetchall()]

    for id, name in zh_name:
        c.execute(f'''
        UPDATE Organ_Viscera
        SET zh_name = "{name}"
        WHERE ID = "{id}";
        ''')

# TODO: Possibility of incorporating glossary data into database.


def glossary():
    df_list = read_pdf("Pialoux_AC_guide.pdf", pages="197-213", lattice=True, multiple_tables=True)
    df_clean_list = []
    rez = build_re()

    def shift_cells_left(row, col, test="zh"):
        s = df_clean.iloc[row, col]
        try:
            if test == "zh":  # test if string is in Chinese
                match = rez.search(s)
            else:
                match = re.search("[a-zA-Z ]", s)

        except TypeError:
            print(f"Non-string object {s} detected at row {row} column {col} of dataframe:\n {tabulate(df_clean)}.")
            match = True

        if not (match):
            df_clean.iloc[row, col] = df_clean.iloc[row, col - 1] + " " + s
            df_clean.iloc[row, :] = df_clean.iloc[row, :].shift(-1)
            shift_cells_left(row, col, test)
        else:
            return

    for i, df in enumerate(df_list):
        heading_list = [(name, i) for i, name in enumerate(df['Chinese\r(pinyin)']) if df.iloc[i,1:].isnull().all()]
        df = df.drop(index=[idx for name, idx in heading_list])
        # df_clean_list.append((df))

        # zh_list = df['Chinese\r(pinyin)'].to_list()
        # tr = [rez.sub("", s) for s in lst]  # remove all Chinese characters in list
        # zh = ["".join(rez.findall(s)) for s in lst]
        df_clean = df['Chinese\r(pinyin)'].str.split('\r', expand=True)
        df_clean.reset_index(drop=True, inplace=True)

        for row in df_clean.index:
            shift_cells_left(row, 1)

        df_clean.dropna(axis=1, how="all", inplace=True)

        # if len(df_clean.columns) > 2:
        #     for row in df_clean.index:
        #         shift_cells_left(row, 2, test="zh")

        df_clean_list.append(df_clean)

    return df_clean_list


def build_luo_data(connect: sql.Connection):
    df = read_pdf("Pialoux_AC_guide.pdf", pages="140-142", lattice=True, multiple_tables=False)[0]
    df.replace({'\r': ' ', r'-\s': ''}, regex=True, inplace=True)
    df.drop(df[df.Trajectory == "Trajectory"].index, inplace=True)

    luo_id = ["LO" + str(i+1).zfill(2) for i in range(len(df['Longitudinal Luo']))]

    luo = [re.search("[A-Z]{2,} [0-9]+", s) for s in df['Longitudinal Luo']]
    luo = [o.group(0).replace(" ", "") if o else None for o in luo]

    desc = ['肺', '大腸', '胃', '脾', '心', '小腸', '膀胱', '腎', '心包', '三焦', '膽', '肝',
            '任脈', '督脈', '胃之大絡', '脾之大絡']

    c = connect.cursor()
    acu_name = []
    acu_id = []
    for i, pt in enumerate(luo):

        if pt is None:

            acu_id.append(luo_id[i])
            acu_name.append("虛里")
            continue

        if "TW" in pt:

            pt = pt.replace("TW", "TB")

        c.execute(f'''
        SELECT ID, acuName_zh FROM Acupoint
        WHERE cl_ID = "{pt}"
        ''')

        acu_data = c.fetchone()
        acu_name.append(acu_data[1])
        acu_id.append(acu_data[0])

    luo_dict = {
        "ID": luo_id,
        "acuID": acu_id,
        "desc_zh": desc,
        "name_zh": acu_name,
        "longitudinal_luo": list(df['Longitudinal Luo']),
        "trajectory": list(df['Trajectory']),
        "deficiency": list(df['Deficiency']),
        "excess": list(df['Excess']),
    }

    luo_df = pd.DataFrame(luo_dict)

    luo_df.to_sql('Luo', connect, dtype={'ID': 'TEXT PRIMARY KEY'}, if_exists='replace', index=False)


if __name__ == '__main__':
    with sql.connect("acu.db") as conn:  # establish connection to database
        # create_tables(conn)
        # build_pentashu_data(conn)
        # update_org_vis_table(conn)
        # build_mu_shu_data(conn)
        build_luo_data(conn)

        #
        #
        # conn.commit()
    #     pass
    # glossary()