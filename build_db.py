import sqlite3 as sql
import wikipedia as wp
import pandas as pd
from copy import deepcopy
from typing import List, Dict, Type
from requests import Session
import re
from opencc import OpenCC
from pypinyin import pinyin, Style
from itertools import chain
from lookup import get_id
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from orgparse import load, loads
import os
from pathlib import Path
from opencc import OpenCC as CC

SCRIPT = '''
    CREATE TABLE IF NOT EXISTS Acupoint (
    ID TEXT PRIMARY KEY, -- International Standard Code.
    cl_ID TEXT UNIQUE,
    prcID TEXT UNIQUE, -- PRC Standard Code.
    acuName_zh TEXT, 
    acuName_zh_sim TEXT,
    acuName_en TEXT, 
    acuName_tr TEXT, -- transliterated Chinese text
    meridianID TEXT, -- must create column before adding it as a foreign key. 
    FOREIGN KEY (meridianID) REFERENCES Meridian (ID));
    
    CREATE TABLE IF NOT EXISTS acuLoc ( -- Location of Acupoints.
    acuID TEXT PRIMARY KEY, 
    acuLoc_desc TEXT, 
    -- acuLoc_desc_en TEXT,
    acuLoc_pos TEXT, -- General position of acupoint: head, upper/lower limb etc.
    FOREIGN KEY (acuID) REFERENCES Acupoint (ID)); -- primary key is also a foreign key.
    
    CREATE TABLE IF NOT EXISTS acuFind ( -- How to find an Acupoint.
    acuID TEXT PRIMARY KEY, 
    acuFind_desc TEXT,
    ref TEXT);
    
    CREATE TABLE IF NOT EXISTS acuEx ( -- Acupoints shared by the extraordinary meridians.
    ID TEXT PRIMARY KEY, -- in the form of TV1, BV2... etc.
    bypass TEXT, -- use primary key of Acupoint table as foreign key.
    meridianID TEXT, 
    FOREIGN KEY (meridianID) REFERENCES Meridian (ID),
    FOREIGN KEY (bypass) REFERENCES Acupoint (ID));
    
    CREATE TABLE IF NOT EXISTS acuAlias (
    acuID TEXT, 
    aliasName TEXT,
    aliasSrc TEXT, -- source of aliasName.
    PRIMARY KEY (acuID, aliasName));
    
    CREATE TABLE IF NOT EXISTS Meridian (
    ID TEXT PRIMARY KEY, 
    cl_ID TEXT GENERATED ALWAYS -- Classical Acupuncture codes
        AS (CASE
                WHEN ID = "TV" THEN "CV"
                WHEN ID = "YinLV" THEN "yWM"
                WHEN ID = "YangLV" THEN "YWM"
                WHEN ID = "YinHV" THEN "yQM"
                WHEN ID = "YangLV" THEN "YQM"
                WHEN ID = "CV" THEN "RM"
                WHEN ID = "GV" THEN "DM"  -- Pialoux does not differentiate in code between 帶脈 and 督脈; we use the international standard for the latter. 
                WHEN ID = "BL" THEN "UB"
                WHEN ID = "KI" THEN "KD"
                WHEN ID = "TE" THEN "TB"
                WHEN ID = "LR" THEN "LV"
                ELSE ID
            END),
    meridianName_zh TEXT, 
    meridianName_zh_sim TEXT,
    meridianName_abbrev TEXT,
    meridianName_tr TEXT, -- transliteration; Wikipedia provides values only for extraordinary meridians. 
    meridianName_en TEXT, -- name of organ as meridian name. 
    meridianExtra BOOLEAN DEFAULT "0" NOT NULL CHECK (meridianExtra IN (0, 1)),  -- True for extraordinary meridian
    related TEXT, -- 表裡關係
    yinyang BOOLEAN GENERATED ALWAYS
        AS (CASE 
                WHEN meridianName_zh LIKE "%陰%" OR meridianName_zh LIKE "任%" THEN 0
                WHEN meridianName_zh LIKE "%帶%" OR meridianName_zh LIKE "%衝%" THEN NULL
            ELSE 1
            END),
    yinyang_tri BOOLEAN GENERATED ALWAYS
    AS (CASE 
            WHEN meridianName_zh LIKE "%太陰%" THEN "ty"
            WHEN meridianName_zh LIKE "%少陰%" THEN "sy"
            WHEN meridianName_zh LIKE "%厥陰%" THEN "jy"
            WHEN meridianName_zh LIKE "%太陽%" THEN "TY"
            WHEN meridianName_zh LIKE "%少陽%" THEN "SY"
            WHEN meridianName_zh LIKE "%陽明%" THEN "YM"
        END),
    limb TEXT GENERATED ALWAYS
        AS (CASE 
                WHEN meridianName_zh LIKE "%手%" THEN "H"
            ELSE "F"
            END),
    tonify TEXT,
    disperse TEXT); 
    
    CREATE TABLE IF NOT EXISTS meridianRoute ( -- 循經路線. Routes taken by the extraordinary meridians are related to the AcuEx table. 
    meridianID TEXT PRIMARY KEY,
    route TEXT, -- route of meridian
    route_src TEXT, -- source of route description
    FOREIGN KEY (meridianID) REFERENCES Meridian (ID));
    
    CREATE TABLE IF NOT EXISTS Images ( -- Images for archival and display purposes
    ID TEXT, 
    category TEXT, -- Use names of existing tables to define the data category. eg. acuLoc to indicate location of a point. 
    source TEXT, 
    img BLOB,
    PRIMARY KEY (ID, category, source));
    
    CREATE TABLE IF NOT EXISTS imgLink ( -- Link image to datapoint. 
    ID INTEGER PRIMARY KEY AUTOINCREMENT, 
    imgID TEXT, -- references Images.ID
    refID TEXT, -- references acuID, meridianID etc.; to be derived from imgID
    imgCAT TEXT, -- references Images.category
    imgSRC TEXT, -- references Images.source
    img_desc TEXT, -- description of image in context, if any.
    FOREIGN KEY (imgID) REFERENCES Images (ID),
    FOREIGN KEY (imgCAT) REFERENCES Images (category),
    FOREIGN KEY (imgSRC) REFERENCES Images (source),
    FOREIGN KEY (refID) REFERENCES acuLoc (acuID),
    FOREIGN KEY (refID) REFERENCES meridianRoute (meridianID));
    '''


def created_tables() -> List[str]:
    """List of tables that have been created by the SQLite script above."""
    r = re.compile("CREATE TABLE IF NOT EXISTS (\\w+)")
    tables = r.findall(SCRIPT)

    return tables


def initialize_database(connect: sql.Connection):
    """Build the basic database structure from scratch. """

    print("Building the Acupuncture database...")

    # Build database structure
    c = connect.cursor()  # use Cursor object to perform SQL commands

    for table in created_tables():
        # Drop tables if exist
        c.executescript(f'''
        DROP TABLE IF EXISTS {table};
        ''')

    # Create tables
    # NOTE: Derived values (such as Yinyang attributes of meridians) will not be stored in the database.
    c.executescript(SCRIPT)


# Furnish data


def get_basic_data(connect: sql.Connection) -> None:
    """Scrape data from English wikipedia \
    to populate the Acupoint and Meridian tables."""

    print("Furnishing database with data from Wikipedia... ")

    html = wp.page("List_of_acupuncture_points").html()
    df = pd.read_html(html)  # parses all tables into dataframes

    # Set meridian, extraordinary meridian and acupoint data

    meridian = df[0][['Code', 'Chinese Name', 'English']]
    meridian.columns = ['ID', 'meridianName_zh', 'meridianName_en']

    extraordinary_meridian = df[1][['Code', 'Name', 'Transliteration', 'English']]
    extraordinary_meridian.columns = ['ID', 'meridianName_zh', 'meridianName_tr', 'meridianName_en']

    acupoint = pd.concat(df[2:16])[['Point', 'Name', 'Transliteration', 'English']]  # standard :16, all (include 奇穴):18
    acupoint.columns = ['ID', 'acuName_zh', 'acuName_tr', 'acuName_en']  # ID = International Standard Code.

    # DATA CLEANING

    # Meridian data
    meridian = deepcopy(meridian)  # make sure df is a copy, not a view to avoid SettingwithCopyWarning.
    meridian_list = list(meridian["meridianName_zh"])
    meridian_list_abbrev = [re.search(".+[陰陽明](.+經)", item).group(1) for item in meridian_list]
    # re.search(".+[陰陽明](.+經)", item) abbreviates Traditional Chinese meridian names
    # gotten from the website to a shorter form that better matches its English name. 
    # Eg. "手太陰肺經" (literally, Hand-Taiyin-Lung meridian) --> "肺經" (Lung meridian).

    extraordinary_meridian = deepcopy(extraordinary_meridian)
    as_list = extraordinary_meridian['meridianName_zh'].tolist()
    split_list = [item.split('; ') for item in as_list]
    sim_list = [sim for sim, zh in split_list]
    cc = CC('t2s')  # Convert to simplified Chinese
    sim_list = [cc.convert(s) for s in sim_list]
    zh_list = [zh for sim, zh in split_list]
    zh_list = [name.replace("蹺", "蹻") for name in zh_list]

    extraordinary_meridian['meridianName_zh'] = zh_list
    extraordinary_meridian['meridianName_zh_sim'] = sim_list
    extraordinary_meridian['meridianExtra'] = 1

    # Acupoint data

    acupoint = deepcopy(acupoint)  # make sure df is a copy, not a view.
    name_list = list(acupoint['acuName_zh'])
    acu_list = [re.search("([\u4e00-\u9fff]+)([a-z\\d \\[;()\\]]+)?", item).group(1) for item in name_list]
    acupoint['acuName_zh'] = acu_list  # remove aliases from Chinese name.

    as_list = list(acupoint['ID'])
    split_list = [item.split('-') for item in as_list]
    tag_list = [tag.upper() for tag, sn in split_list]
    sn_list = [sn for tag, sn in split_list]  # serial-number of acupoint index

    tag_list = ["LR" if tag == "LIV" else tag for tag in tag_list]
    tag_list = ["GV" if tag == "DU" else tag for tag in tag_list]
    tag_list = ["CV" if tag == "REN" else tag for tag in tag_list]
    tag_list = ["KI" if tag == "K" else tag for tag in tag_list]

    new_id_list = [tag + sn for tag, sn in zip(tag_list, sn_list)]
    meridian_id_list = tag_list
    acupoint["ID"] = new_id_list
    acupoint["meridianID"] = meridian_id_list
    acupoint["acuName_tr"] = [transliterate(item) for item in acupoint["acuName_zh"]]

    cc = OpenCC('t2s')
    acupoint["acuName_zh_sim"] = [cc.convert(item) for item in acu_list]
    meridian["meridianName_zh_sim"] = [cc.convert(item) for item in meridian_list]
    meridian["meridianName_abbrev"] = meridian_list_abbrev
    meridian["meridianName_tr"] = [transliterate(item) for item in meridian_list_abbrev]
    meridian["ID"] = ["LR" if tag == "LV" else tag for tag in meridian["ID"]]

    # aliases

    c = connect.cursor()

    c.executescript(f'''
    INSERT INTO acuAlias (acuID, aliasName, aliasSrc)
        VALUES  ("YinHV", "陰蹻脈", "wiki"),
                ("YangHV", "陽蹻脈", "wiki");
    ''')

    for i, item in enumerate(name_list):
        alias = re.search(".+([a-z0-9 \\[;\\(\\)\\]]+)([\u4e00-\u9fff]+)", item)
        if alias:
            c.executescript(f'''
            INSERT INTO acuAlias (acuID, aliasName, aliasSrc)
                VALUES ("{new_id_list[i]}", "{alias.group(2)}", "wiki");
            ''')

    # NOTE: This wiki page uses a different code (against the PRC standard) for certain acupoints.
    # e.g. TE instead of SJ for 三焦經; GV instead of DU for 督脈 etc.
    # We'll be using the International Standard for this App.
    # The PRC Standard will be referenced under the Acupoint.prcID column.

    # PRC Standard CODE DISCREPANCIES
    # TE -> SJ （三焦）
    # LV -> LR （肝）
    # CV -> RN
    # GV -> DU

    # NOTE: China has switched to International code by 2012.
    # We keep track of that standard to access「A+醫學百科」data.

    prc_tag_list = ["SJ" if tag == "TE" else tag for tag in tag_list]  # 三焦
    prc_tag_list = ["RN" if tag == "CV" else tag for tag in prc_tag_list]  # 任
    prc_tag_list = ["DU" if tag == "GV" else tag for tag in prc_tag_list]  # 督
    prc_id_list = [tag + sn for tag, sn in zip(prc_tag_list, sn_list)]
    acupoint["prcID"] = prc_id_list

    # Write to database

    acupoint.to_sql('Acupoint', connect, if_exists='append', index=False)  # save to sql database
    meridian.to_sql('Meridian', connect, if_exists='append', index=False)
    extraordinary_meridian.to_sql('Meridian', connect, if_exists='append', index=False)

    # Remove duplicated Simplified Chinese from alias table.
    c.executescript('''
    DELETE FROM `acuAlias`
        WHERE EXISTS
            (SELECT `acuName_zh_sim` FROM `Acupoint`
            WHERE `acuName_zh_sim` = `aliasName`);
    ''')


def get_extraordinary_route_data(connect: sql.Connection) -> (List[str], Dict[str, str]):
    """Scrape data from Chinese wikipedia \
    to furnish extraordinary meridian route data to database."""

    wp.set_lang("zh")
    html = wp.page("腧穴列表").html()
    df = pd.read_html(html)

    print("Getting Extraordinary Meridian data...")

    acu_ex = df[1]  # dataframe of acupoints on the extraordinary meridians.
    acu_ex = deepcopy(acu_ex)
    acu_ex = acu_ex.iloc[2:, :]  # slice off 任脈 and 督脈
    acu_ex_list = acu_ex["穴位名稱及序號"].tolist()

    split_list = [item.split(': ') for item in acu_ex_list]
    route_list = [route for route, points in split_list]
    points_list = [points for route, points in split_list]
    meridian_list = list(acu_ex["國際代碼"])

    acu_ex_dict = {}
    for i, lst in enumerate(points_list):
        points = lst.split(" ")
        split_list = [item.split(".") for item in points]
        bypass = [acuID for acuID, acuName in split_list]
        meridian = meridian_list[i]

        for j, bypass_point in enumerate(bypass):
            acu_ex_dict[f"{meridian}{j + 1}"] = bypass_point

    c = connect.cursor()

    for key in acu_ex_dict.keys():
        c.executescript(f'''
        INSERT INTO acuEx (ID, bypass, meridianID)
        VALUES ("{key}", "{acu_ex_dict[key]}", "{''.join(i for i in key if not i.isdigit())}");
        ''')

    c.execute(f'''
    UPDATE acuEx
    SET bypass = "LR13" WHERE meridianID = "BV" AND bypass = "GB25"
    ''')
    # for i, item in enumerate(route_list):
    #     c.executescript(f'''
    #     INSERT INTO meridianRoute (meridianID, route, route_src)
    #         VALUES
    #             ("{meridian_list[i]}", "{item}", "https://zh.wikipedia.org/wiki/腧穴列表#奇經八脈");
    #     ''')


def get_location_data(connect: sql.Connection) -> None:
    """Scrape data from A+醫學百科 \
    to furnish acupoint location data in Chinese."""

    print("Getting acupoint location data...")

    session = Session()
    with session.get('http://cht.a-hospital.com/w/中华人民共和国国家标准·经穴部位') as resp:
        resp.raise_for_status()
        df = pd.read_html(resp.text)

        acu_loc = pd.concat(df[4:18])
        acu_loc = deepcopy(acu_loc)
        acu_loc.columns = ["prcID", "acuName_zh", "acuName_tr", "acuLoc_desc"]

        acu_loc.to_sql('acuLoc_temp', connect, if_exists='replace', index=False)

        c = connect.cursor()
        c.executescript('''
        INSERT INTO `acuLoc`(`acuID`, `acuLoc_desc`)
        SELECT "ID", "acuLoc_desc" FROM `Acupoint`
        JOIN `acuLoc_temp` ON `Acupoint`.`prcID` = `acuLoc_temp`.`prcID`;
        
        UPDATE acuLoc
        SET acuLoc_desc = "在足背與小腿交界處的橫紋中央凹陷中，當拇長伸肌鍵與趾長伸肌鍵之間。"
        WHERE acuID = "ST41";
        
        DROP TABLE acuLoc_temp;
        ''')

    with session.get('http://cht.a-hospital.com/w/穴位') as resp:
        resp.raise_for_status()
        soup = BeautifulSoup(resp.content, 'html.parser')

        table = soup.select('table:-soup-contains("位置區分") table')[0]
        rows = table.find_all("tr")

    data_list = []
    pos_conv = {
        "頭部": "H",
        "腹部\n胸部": "TF",
        "背部": "TB",
        "上肢": "UL",
        "下肢": "LL",
        "足部": "F",
    }
    for row in rows:
        if row.th and row.td:
            heading = row.th.text

            if row.tr:
                sub_rows = row.find_all("tr")

                for sub_row in sub_rows:
                    if sub_row.th:
                        rows.remove(sub_row)

                        if sub_row.ul:
                            data = sub_row.ul.text
                            data_list.append((heading, data))

            if row.ul and not row.tr:
                data = row.ul.text
                data_list.append((heading, data))

    for pos, acu_list in data_list:
        acu_list = acu_list.replace("\n", "")
        acu_list = acu_list.split("穴")
        for point in acu_list:
            c.execute(f'''
            UPDATE acuLoc
            SET acuLoc_pos = "{pos_conv[pos]}"
            WHERE `acuID` = (SELECT ID FROM `Acupoint` WHERE acuName_zh = "{point}");
            ''')


def get_ctext(file, chapter):
    path = Path(__file__)
    path = path.home()/"Creation"/"ctext"/file
    path = path.with_suffix(".org")
    root = load(path)

    try:
        chapter_node = root.get_nodes_with_heading(chapter)

        return chapter_node[0]

    except IndexError:
        print(f"No chapter with heading {chapter} can be found in {file}.org")


def transliterate(string: str) -> str:
    tr = "".join(list(
        chain.from_iterable(
            pinyin(string, style=Style.NORMAL)))).capitalize()

    if "俞" in string:
        tr = tr.replace("yu", "shu")

    return tr


def get_meridian_route():
    jingmai = get_ctext("黃帝內經", "經脈第十")
    meridians = jingmai.children[0].children
    meridian_route = {}
    for meridian in meridians[:-1]:
        meridian_route[meridian.heading] = meridian.body.split("\n")[1]

    return meridian_route


def get_ex_route(connect: sql.Connection):
    """Get classical text for routes taken by the extraordinary meridians."""
    ex_names = get_column(connect, "meridianName_zh", "Meridian", "meridianExtra = 1")

    meridian_route = {}
    for name in ex_names:
        meridian = get_ctext("奇經八脈考", name)
        meridian_route[meridian.heading] = list(filter(None, meridian.body.split("\n")))[0]

    return meridian_route


def update_meridian_route_table(connect: sql.Connection):
    data = get_meridian_route()
    ex_data = get_ex_route(connect)

    c = connect.cursor()

    for key, value in data.items():
        c.execute(f"""
            INSERT INTO meridianRoute (meridianID, route, route_src)
            VALUES ((SELECT ID FROM `Meridian` WHERE `meridianName_abbrev` = "{key}"),
                    "{value}",
                    "《黃帝內經·靈樞·經脈》")
            """)

    for key, value in ex_data.items():
        c.execute(f"""
            INSERT INTO meridianRoute (meridianID, route, route_src)
            VALUES ((SELECT ID FROM `Meridian` WHERE `meridianName_zh` = "{key}"),
                    "{value}",
                    "《奇經八脈考·{key}》")
            """)

def get_aliases():
    """Furnish alias names of acupoint from 醫砭 website."""
    base_url = 'http://yibian.hopto.org/acu'
    alias_list = []
    heading_list = []
    url_list = []
    id_list = []

    session = Session()
    for i in range(1, 15):

        with session.get (base_url,
                          params={
                              'mn': 'jing',
                              'sn': i,
                          }
                          ) as resp:

            resp.raise_for_status()
            resp.encoding = resp.apparent_encoding
            soup = BeautifulSoup(resp.content, 'html.parser')
            alias_tags = soup.select(".content_small_label:-soup-contains('別名')")

            for tag in alias_tags:
                anchor = tag.find_previous_siblings('a')[0]
                heading = anchor.text
                href = anchor['href']
                aliases = tag.find_next_sibling().text.split(",")

                print(f"Getting aliases for {heading}...")

                heading_list.append(heading)
                alias_list.append(aliases)
                url_list.append(urljoin(base_url, href))

            # print("Building id list...")
    # for url in url_list:
    #     with session.get(url,
    #                      headers={"User-Agent":
    #                                   "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:99.0) Gecko/20100101 Firefox/99.0}",
    #                               }
    #                      ) as resp:
    #         resp.raise_for_status()
    #         resp.encoding = resp.apparent_encoding
    #         soup = BeautifulSoup(resp.content, 'html.parser')
    #         print(url)
    #         tag = soup.select_one('td.content_board table td b').nextSibling
    #         id_str = "".join(filter(str.isalnum, tag))
    #         alias_id = re.sub("[^A-Z0-9]+", "", id_str)
    #         id_list.append(alias_id)
    #         print(alias_id)

    return id_list, heading_list, alias_list


def alias_id_is_null(connect: sql.Connection):
    """Returns the names of acupoints where the ID is null.
    Meaning: Name given on website does not match existing data on our database."""
    c = connect.cursor()
    c.execute('''
        SELECT `aliasName` FROM `acuAlias`
        WHERE `acuID` ISNULL;
    ''')
    return [item[0] for item in c.fetchall()]


def get_column(connect: sql.Connection, column, table, condition=None) -> List[str]:

    c = connect.cursor()
    if condition:
        c.execute(f'''
        SELECT {column} FROM {table}
        WHERE {condition}; 
        ''')
    else:
        c.execute(f'''
        SELECT {column} FROM {table}; 
        ''')

    values = [value[0] for value in c.fetchall()]

    return values


def update_acu_alias_table(connect: sql.Connection):
    id_list, heading_list, alias_list = get_aliases()

    hdg_idx_dict = {}  # index that points to the corresponding heading for each alias list item
    for i, name in enumerate(heading_list):
        for item in alias_list[i]:
            hdg_idx_dict[item] = name

    c = connect.cursor()
    for i, name in enumerate(heading_list):
        for item in alias_list[i]:
            c.execute(f'''
                INSERT INTO acuAlias (acuID, aliasName, aliasSrc)
                VALUES ((SELECT ID FROM Acupoint WHERE acuName_zh = "{name}"),
                "{item}",
                "醫砭")
            ''')

    # Remove controversial entries
    c.execute(f"""
    DELETE FROM acuAlias
        WHERE   (aliasName = "太陽")
        OR      (aliasName = "髮際")
        OR      (aliasName = "陽蹻")
        OR      (aliasName = "陰蹻");
    """)

    # Update null values
    null_list = alias_id_is_null(connect)
    db_acuname = get_column(connect, "acuName_zh", "Acupoint")

    for i, item in enumerate(null_list):
        # null list item match db
        heading = hdg_idx_dict[item]
        null_id = get_id(item)
        if item in db_acuname:
            null_list.remove(item)
            c.executescript(f"""
            DELETE FROM acuAlias
            WHERE aliasName = "{item}";
            
            INSERT INTO acuAlias (acuID, aliasName, aliasSrc)
            VALUES ("{null_id}", "{heading}", "醫砭");
            """)

    null_list = alias_id_is_null(connect)
    for item in null_list:
        heading = hdg_idx_dict[item]
        # heading tr match db
        hdg_id = get_id(transliterate(heading))  # use transliterated heading to search
        if hdg_id:
            c.execute(f'''
            UPDATE acuAlias
            SET acuID = "{hdg_id}"
            WHERE aliasName = "{item}";
            ''')
            try:
                c.execute(f'''
                INSERT INTO acuAlias (acuID, aliasName, aliasSrc)
                VALUES ("{hdg_id}", "{heading}", "醫砭");
                ''')
            except sql.IntegrityError:
                print(f"Acupoint {heading} is already registered as an alias.")

    # Manual

    c.executescript(f'''
    UPDATE acuAlias
    SET acuID = "TE18", aliasSrc = "醫砭"
    WHERE aliasName = "資脈";
    
    INSERT INTO acuAlias (acuID, aliasName, aliasSrc)
    VALUES  ("TE18", "瘛脈", "醫砭"),
            ("KI16", "肓腧", "奇經八脈考"),
            ("KI12", "太赫", "奇經八脈考"),
            ("CV11", "建裏", "奇經八脈考");
    ''')


def update_meridian_biaoli(connect: sql.Connection):
    BIAOLI = {
        # 臟腑表裡關係
        "GB": "LR",
        "SI": "HT",
        "ST": "SP",
        "LI": "LU",
        "BL": "KI",
        "TE": "PC",
    }

    c = connect.cursor()

    c.execute('''
    SELECT ID, yinyang FROM Meridian
    WHERE meridianExtra = 0 AND yinyang = 1;
    ''')

    meridian_lst = c.fetchall()

    for meridian in meridian_lst:
        meridian = meridian[0]

        c.executescript(f'''
        UPDATE Meridian
        SET related = "{BIAOLI[meridian]}"
        WHERE ID = "{meridian}";

        UPDATE Meridian
        SET related = "{meridian}"
        WHERE ID = "{BIAOLI[meridian]}";
        ''')


def update_cl_id(connect: sql.Connection):
    """Update classical acupuncture code for acupoint table."""
    c = connect.cursor()

    c.execute('''
    SELECT `Acupoint`.`ID`, `Meridian`.`cl_ID` FROM `Acupoint`
        JOIN `Meridian` ON `Acupoint`.`meridianID` = `Meridian`.`ID`; 
    ''')

    update_values = c.fetchall()

    for acu_id, cl_tag in update_values:
        sno = re.sub("[a-zA-Z]+", "", acu_id)
        cl_id = cl_tag + sno

        c.execute(f'''
        UPDATE Acupoint
        SET cl_ID = "{cl_id}"
        WHERE ID = "{acu_id}";
        ''')



if __name__ == '__main__':
    with sql.connect("acu.db") as conn:  # establish connection to database
        initialize_database(conn)
        get_basic_data(conn)
        get_extraordinary_route_data(conn)
        get_location_data(conn)
        update_acu_alias_table(conn)
        update_meridian_route_table(conn)
        update_meridian_biaoli(conn)
        update_cl_id(conn)

        conn.commit()

        print("Done!")


