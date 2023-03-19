import sqlite3 as sql
import os
import glob
from pathlib import Path
import re
from typing import List, Type, Dict
from build_db import get_column


def parse_image_id(img_id: str) -> List[str]:
    """Parse image ID to return and expanded list of strings indicated by the initial string.
    e.g. "GB41-52" --> ["GB41", "GB52"]
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


def update_meridian_route_img_tag(connect: Type[sql.Connection]):
    """Update non-numeric image tags to 'meridianRoute' category.
    This is for cases where images are scanned from the same textbook
    and saved in a single, undifferentiated folder. """

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


def write_file(data, filename):
    """Write BLOB (binary) data to a file."""

    with open (filename, 'wb') as f:
        f.write(data)


def read_blob(connect: Type[sql.Connection], category="acuLoc", source="王華_針灸學2012"):

    if category == "acuLoc":
        print(f"\n\nReading acupoint image data...\n")
        query = f"""
            SELECT refID, acuName_zh, imgCAT, img FROM `imgLink`
                JOIN `Images` ON `Images`.`ID` = `imgLink`.`imgID` AND `Images`.category = `imgLink`.`imgCAT` AND `Images`.source = `imgLink`.`imgSRC`
                JOIN `Acupoint` ON `Acupoint`.ID = `imgLink`.`refID`
                WHERE `imgSRC` = "{source}";
                """
    else:
        print(f"\n\nReading meridian route image data...\n")
        query = f"""
            SELECT refID, meridianName_zh, imgCAT, img FROM `imgLink`
                JOIN `Images` ON `Images`.`ID` = `imgLink`.`imgID` AND `Images`.category = `imgLink`.`imgCAT` AND `Images`.source = `imgLink`.`imgSRC`
                JOIN `Meridian` ON `Meridian`.`ID` = `imgLink`.`refID`
                WHERE `imgSRC` = "{source}";
                """

    c = connect.cursor()
    c.execute(query)

    for item in c.fetchall():
        ref_id, name, category, image = item

        filename = f"{category}/{ref_id}.png"
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        # write_file(image, filename)

        print(ref_id, name)


def import_images(connect: Type[sql.Connection], folder: str, source: str, category="acuLoc") -> None:
    """Import images from a specific folder into acu.db database Image table.
    The images should be named by acupoint or meridian code for quick referencing.
    Acupoint code can include a range. e.g. "GB10-15.png"
    'Category' is the database table to which the images are referenced to. """
    c = connect.cursor()

    for filename in glob.glob(f'./{folder}/*.png'):
        file = convert_to_binary_data(filename)
        c.execute(f'''
        INSERT INTO Images (ID, category, source, img)
            VALUES ("{Path(filename).stem}", "{category}", "{source}", ?);
        ''', [sql.Binary(file)])


def img_link_data(connect: Type[sql.Connection]) -> List[Dict]:
    """Generate imgLink data."""
    img_id_list = get_column(connect, "ID", "Images")
    img_cat_list = get_column(connect, "category", "Images")
    img_src_list = get_column(connect, "source", "Images")
    ref_id_list = [parse_image_id(item) for item in img_id_list]
    data = []
    for i, ref_id in enumerate(ref_id_list):
        for ref_id_expanded in ref_id:
            data.append(
                {"imgID": img_id_list[i],
                 "imgCAT": img_cat_list[i],
                 "imgSRC": img_src_list[i],
                 "refID": ref_id_expanded,
                 }
            )

    return data


def update_img_link_table(connect: Type[sql.Connection]):
    """Update imgLink table with generated imgLink data."""

    sql_update = ('''
        INSERT INTO imgLink (imgID, imgCAT, imgSRC, refID)
        VALUES(:imgID, :imgCAT, :imgSRC, :refID);
        ''')

    c = connect.cursor()

    return c.executemany(sql_update, img_link_data(connect))


def load_img(connect: Type[sql.Connection]):
    read_blob(connect)
    read_blob(connect, "meridian")


if __name__ == '__main__':
    with sql.connect("acu.db") as conn:
        import_images(conn, "WH", "王華_針灸學2012")  # default category is "acuLoc";
        update_meridian_route_img_tag(conn)  # use this function to update non-numeric ID to "meridianRoute" tag.
        update_img_link_table(conn)
        load_img(conn)

