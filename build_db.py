import sqlite3
import sqlite3 as sql
import wikipedia as wp
import pandas as pd
from copy import deepcopy
from typing import List, Set, Dict, Tuple, Type, BinaryIO
from requests import Session, get
import re
from opencc import OpenCC
from pypinyin import pinyin, Style
from itertools import chain
import os
import glob
from pathlib import Path


def initialize_database(connect: Type[sqlite3.Connection]):
    """Build the basic database structure from scratch. """

    print("Building the Acupuncture database...")

    # Build database structure
    c = connect.cursor()  # use Cursor object to perform SQL commands

    # Drop tables if exist
    c.executescript('''
    DROP TABLE IF EXISTS Acupoint;
    DROP TABLE IF EXISTS acuLoc;
    DROP TABLE IF EXISTS acuFind;
    DROP TABLE IF EXISTS acuEx;
    DROP TABLE IF EXISTS acuAlias;
    DROP TABLE IF EXISTS Meridian;
    DROP TABLE IF EXISTS meridianRoute;
    DROP TABLE IF EXISTS Images;
    DROP TABLE IF EXISTS imgLink;
    ''')

    # Create tables
    # NOTE: Derived values (such as Yinyang attributes of meridians) will not be stored in the database.
    c.executescript('''
    CREATE TABLE IF NOT EXISTS Acupoint (
    ID TEXT PRIMARY KEY, -- International Standard Code.
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
    meridianName_zh TEXT, 
    meridianName_zh_sim TEXT,
    meridianName_tr TEXT, -- transliteration; Wikipedia provides values only for extraordinary meridians. 
    meridianName_en TEXT, -- name of organ as meridian name. 
    meridianExtra BOOLEAN DEFAULT "0" NOT NULL CHECK (meridianExtra IN (0, 1)));  -- True for extraordinary meridian
    
    CREATE TABLE IF NOT EXISTS meridianRoute ( -- 循經路線. Routes taken by the extraordinary meridians are related to the AcuEx table. 
    meridianID TEXT PRIMARY KEY,
    route TEXT, -- route of meridian
    route_src TEXT, -- source of route description
    route_classic TEXT, -- route of meridian; quote 《黃帝內經·靈樞》.
    meridian_img TEXT,
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
    img_desc TEXT, -- description of image in context, if any.
    FOREIGN KEY (imgID) REFERENCES Images (ID),
    FOREIGN KEY (refID) REFERENCES acuLoc (acuID),
    FOREIGN KEY (refID) REFERENCES meridianRoute (meridianID));
    ''')


# Furnish data


def get_basic_data(connect: Type[sqlite3.Connection]) -> None:
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

    extraordinary_meridian = deepcopy(extraordinary_meridian)
    as_list = extraordinary_meridian['meridianName_zh'].tolist()
    split_list = [item.split('; ') for item in as_list]
    sim_list = [sim for sim, zh in split_list]
    zh_list = [zh for sim, zh in split_list]

    extraordinary_meridian['meridianName_zh'] = zh_list
    extraordinary_meridian['meridianName_zh_sim'] = sim_list
    extraordinary_meridian['meridianExtra'] = 1

    # Acupoint data

    acupoint = deepcopy(acupoint)  # make sure df is a copy, not a view.
    name_list = list(acupoint['acuName_zh'])
    acu_list = [re.search("([\u4e00-\u9fff]+)([a-z0-9 \\[;\\(\\)\\]]+)?", item).group(1) for item in name_list]
    acupoint['acuName_zh'] = acu_list  # remove aliases from Chinese name.

    as_list = list(acupoint['ID'])
    split_list = [item.split('-') for item in as_list]
    tag_list = [tag.upper() for tag, sn in split_list]
    sn_list = [sn for tag, sn in split_list]  # serial-number of acupoint index

    tag_list = ["LR" if tag == "LIV" else tag for tag in tag_list]
    tag_list = ["GV" if tag == "DU" else tag for tag in tag_list]
    tag_list = ["CV" if tag == "REN" else tag for tag in tag_list]

    new_id_list = [tag + sn for tag, sn in zip(tag_list, sn_list)]
    meridian_id_list = tag_list
    acupoint["ID"] = new_id_list
    acupoint["meridianID"] = meridian_id_list

    cc = OpenCC('t2s')
    acupoint["acuName_zh_sim"] = [cc.convert(item) for item in acu_list]
    meridian["meridianName_zh_sim"] = [cc.convert(item) for item in meridian_list]
    meridian["meridianName_tr"] = ["".join(list(
        chain.from_iterable(
            pinyin(item, style = Style.NORMAL)))).capitalize() for item in meridian_list_abbrev]
    meridian["ID"] = ["LR" if tag == "LV" else tag for tag in meridian["ID"]]

    # aliases

    c = connect.cursor()
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


def get_extraordinary_route_data(connect: Type[sqlite3.Connection]) -> (List[str], Dict[str, str]):
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

    for i, item in enumerate(route_list):
        c.executescript(f'''
        INSERT INTO meridianRoute (meridianID, route, route_src) 
            VALUES 
                ("{meridian_list[i]}", "{item}", "https://zh.wikipedia.org/wiki/腧穴列表#奇經八脈"); 
        ''')


def get_location_data(connect: Type[sqlite3.Connection]) -> None:
    """Scrape data from A+醫學百科 \
    to furnish acupoint location data in Chinese."""

    print("Getting acupoint location data...")

    with get('http://cht.a-hospital.com/w/中华人民共和国国家标准·经穴部位') as resp:
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
        
        DROP TABLE acuLoc_temp;
        ''')


def parse_image_id(img_id: str) -> List[str]:
    """Parse image ID to return and expanded list of strings indicated by the initial string.
    e.g. "GB41-52" --> ["GB41", "52"]
    Returns original string in a single element list if no range is indicated.
    e.g. "CV1" --> ["CV1"] """
    id_elem_list = img_id.split("-")

    if len(id_elem_list) > 1:
        root = re.search("([A-Z]+)([0-9]+)", id_elem_list[0]).group(1)
        range_start = int(re.search("([A-Z]+)([0-9]+)", id_elem_list[0]).group(2))  # get digit from string
        range_end = int(id_elem_list[1]) + 1  # range excludes the end number.

        expanded_list = []
        for i in range(range_start, range_end):
            expanded_list.append(f"{root}{i}")  # ["GB41", "GB42"..., "GB52"]

        return expanded_list

    else:

        return [img_id]


def has_numbers(inputString):
    return any(char.isdigit() for char in inputString)


def get_column(connect: Type[sqlite3.Connection], column, table):

    c = connect.cursor()
    c.execute(f'''
    SELECT {column} FROM {table}; 
    ''')

    # field_name = [field[0] for field in c.description]
    values = [value[0] for value in c.fetchall()]

    print(values)

    return values


def update_meridian_route_img_tag(connect: Type[sqlite3.Connection]):
    """Update non-numeric image tags to 'meridianRoute' category. """

    c = connect.cursor()
    c.executescript(f"""
    UPDATE Images
        SET category = "meridianRoute"
        WHERE NOT ID GLOB "*[0-9]*"AND category == "acuLoc";
    """)


def convert_to_binary_data(filename) -> bytes:
    """Convert digital data to binary format"""
    with open(filename, 'rb') as file:
        blob_data = file.read()
    return blob_data


def import_images(connect: Type[sqlite3.Connection], folder: str, source: str) -> None:
    """Import images from a specific folder into acu.db database Image table.
    The images should be named by acupoint or meridian code for quick referencing.
    Acupoint code can include a range. e.g. "GB10-15.png"
    The folder should be named the same as the database table to which the images are referenced to. """
    os.chdir(f"./{folder}")
    c = connect.cursor()

    for filename in glob.glob('*.png'):
        file = convert_to_binary_data(filename)
        c.execute(f'''
        INSERT INTO Images (ID, category, source, img)
            VALUES ("{Path(filename).stem}", "{folder}", "{source}", ?);
        ''', [sql.Binary(file)])

# read images to disk

# imgLink table


if __name__ == '__main__':
    with sql.connect("acu.db") as conn:  # establish connection to database
        # initialize_database(conn)
        # get_basic_data(conn)
        # get_extraordinary_route_data(conn)
        # get_location_data(conn)
        # import_images(conn, "acuLoc", "王華_針灸學2012")

        # get_column(conn, "ID", "Images")
        update_meridian_route_img_tag(conn)
#
#         conn.commit()
#
    print("Done!")
