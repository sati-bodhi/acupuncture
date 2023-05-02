import sqlite3 as sql
from pathlib import Path
import os
import hanlp
from hanlp.components.tokenizers.transformer import TransformerTaggingTokenizer
from acupuncture.db import Database


DB_PATH = Path(os.path.abspath(__file__)).parents[0] / "acu.db"

tok: TransformerTaggingTokenizer = hanlp.load(hanlp.pretrained.tok.COARSE_ELECTRA_SMALL_ZH)


class Calc:
    """Transcend lists and tuples to zero in on the data."""

    def __init__(self):
        pass

    @staticmethod
    def elem_index_in_list_of_tuples(elem, lst):  # TODO: Move to lookup.
        """Return index element in nested tuple.
        Useful for parsing parallel lists."""

        for i, tup in enumerate(lst):
            if elem in tup:
                j = tup.index(elem)

                return i, j

    @staticmethod
    def paired_with(elem, tup):
        """Returns the paired element in a binary tuple."""
        return tup[tup.index(elem) - 1]

    def get_paired_elem_from_list(self, elem, lst):  # TODO: Move to lookup.
        """Returns the paired element from a list of binary tuples."""
        return [self.paired_with(elem, tup) for tup in lst if elem in tup][0]


def parse_action(action, lang):
    """Takes in an action symbol and returns the name of that symbol in the stated language."""
    with sql.connect(DB_PATH) as conn:
        c = conn.cursor()

        c.execute(f'''
        SELECT {lang} FROM treatment_action
        WHERE id = "{action}"
        ''')

        action = c.fetchone()[0]

        return action


def parse_state_symbol(state):
    if state == "+":
        zh = "實"
    elif state == "-":
        zh = "虛"
    return zh


def parse_acupoint(acupoint, lang="zh"):
    """Takes in the acupoint ID and returns name of the acupoint in the stated language."""

    with sql.connect(DB_PATH) as conn:
        c = conn.cursor()

        c.execute(f'''
        SELECT acuName_{lang} FROM Acupoint
        WHERE id = "{acupoint}"
        ''')

        action = c.fetchone()[0]

        return action


def parse_state(list_of_states, meridian=True, abbrev=False):
    """A state is given by a tuple, in the form of: (entitiy, state),
    whereby entity is the id and state is given by a '+' string for excess,
    and a '-' for deficiency."""
    parsed = []

    if len(list_of_states) > 1:
        for item in list_of_states:
            point_id, state = item

            if meridian:
                point = id_to_meridian_name(point_id, abbrev=abbrev)
            else:
                point = parse_acupoint(point_id)

            state = parse_state_symbol(state)
            parsed.append((point_id, point, state))

        return iter(parsed)

    else:
        point_id, state = list_of_states[0]

        if meridian:
            point = id_to_meridian_name(point_id, abbrev=abbrev)
        else:
            point = parse_acupoint(point_id)

        state = parse_state_symbol(state)

        return point, state




def parse_prescription(prescription, lang="zh"):
    """
    A valid prescription would be a single tuple in the form of (acupoint_id, action)
    where 'action' is given by the symbols '++' or '--'.
    This function would take in a list of such prescriptions
    and return the human-friendly value in the specified language.
    :param prescription:
    :param lang:
    :return:
    """
    parsed = []
    if len(prescription) > 1:
        for item in prescription:
            if item is None:
                pass
            else:
                point_id, action = item
                point = parse_acupoint(point_id)
                action = parse_action(action, lang)
                parsed.append((point_id, point, action))

    else:
        point_id, action = prescription[0]
        point = parse_acupoint(point_id)
        action = parse_action(action, lang)
        parsed.append((point_id, point, action))

    return iter(parsed)


def render_prescription(prescription):
    """Render parsed prescription as hyperlinked html text."""
    # rendered = []
    # for item in prescription:
    #     if item is not None:
    #         point_id, point, action = item
    #         rendered.append(f"""{action}<a href='/query?q={point_id}&category=acupoint'>{point}</a>""")
    #     else:
    #         rendered.append(None)

    rendered = [f"""{action}<a href='/query?q={point_id}&category=acupoint'>{point}</a>"""
                for point_id, point, action in prescription]

    return rendered


def get_acupoint(query, with_alias=True, fuzzy=True):
    """Return ID and traditional Chinese name of acupoint, given a random search string."""
    with sql.connect(DB_PATH) as conn:
        c = conn.cursor()
        no_alias = f"""
            SELECT ID, acuName_zh, acuName_tr, acuName_en, meridianID FROM `Acupoint`
            WHERE `ID` = "{query}" COLLATE NOCASE OR `acuName_zh` LIKE "%{query}%" OR `acuName_zh_sim` LIKE "%{query}%" OR 
            `acuName_tr` LIKE "%{query}%" COLLATE NOCASE OR `acuName_en` LIKE "%{query}%" COLLATE NOCASE;
            """
        no_alias_precise = f"""
            SELECT ID, acuName_zh, acuName_tr, acuName_en, meridianID FROM `Acupoint`
            WHERE `ID` = "{query}" COLLATE NOCASE OR `acuName_zh` LIKE "{query}" OR `acuName_zh_sim` LIKE "%{query}%" OR 
            `acuName_tr` LIKE "{query}" COLLATE NOCASE OR `acuName_en` LIKE "{query}" COLLATE NOCASE;
            """

        alias = f"""
            SELECT ID, acuName_zh, acuName_tr, acuName_en, meridianID FROM `Acupoint`
            WHERE `ID` = "{query}" COLLATE NOCASE OR `acuName_zh` LIKE "%{query}%" OR `acuName_zh_sim` LIKE "%{query}%" OR 
            `acuName_tr` LIKE "%{query}%" COLLATE NOCASE OR `acuName_en` LIKE "%{query}%" COLLATE NOCASE
            UNION
            SELECT ID, acuName_zh, acuName_tr, acuName_en, meridianID FROM `acuAlias`
            JOIN `Acupoint` ON `acuID` = `ID`
            WHERE `acuAlias`.`aliasName` LIKE "%{query}%"
            """

        alias_precise = f"""
            SELECT ID, acuName_zh, acuName_tr, acuName_en, meridianID FROM `Acupoint`
            WHERE `ID` = "{query}" COLLATE NOCASE OR `acuName_zh` LIKE "{query}" OR `acuName_zh_sim` LIKE "{query}" OR 
            `acuName_tr` LIKE "{query}" COLLATE NOCASE OR `acuName_en` LIKE "{query}" COLLATE NOCASE
            UNION
            SELECT ID, acuName_zh, acuName_tr, acuName_en, meridianID FROM `acuAlias`
            JOIN `Acupoint` ON `acuID` = `ID`
            WHERE `acuAlias`.`aliasName` LIKE "{query}"
            """

        if not with_alias:
            if fuzzy:
                c.execute(no_alias)
            else:
                c.execute(no_alias_precise)
        else:
            if fuzzy:
                c.execute(alias)
            else:
                c.execute(alias_precise)

        return c.fetchall()


def get_meridian(query):
    with sql.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute(f"""
        SELECT ID, meridianName_zh, meridianName_tr, meridianName_en, meridianName_abbrev, meridianExtra FROM `Meridian`
        WHERE `ID` = "{query}" COLLATE NOCASE OR `meridianName_zh` LIKE '%{query}%' OR 
        `meridianName_zh_sim` LIKE '%{query}%' OR `meridianName_tr` LIKE '% {query} %' COLLATE NOCASE OR
        `meridianName_en` LIKE '% {query} %' COLLATE NOCASE""")

        return c.fetchall()


def get_id(query, with_alias=True, fuzzy=True):
    rslt = get_acupoint(query, with_alias, fuzzy)
    if len(rslt) > 1:
        print(f"""Keyword "{query}" is not sufficient to pinpoint a single ID. 
        Please refine your search term.
        Result:\n""")

        print(*rslt, sep='\n')

    elif len(rslt) == 0:
        print(f"""No acupoint with the name "{query}" has been found. 
        Please try again.""")

    else:
        print(f"Your keyword '{query}' corresponds to the acupoint {rslt[0][1]} of ID {rslt[0][0]}.")

        return rslt[0][0]


def id_to_meridian_name(idx, abbrev=False):

    db = Database()

    if abbrev:

        name = db.exec_script(f"""
        SELECT meridianName_abbrev from Meridian
        WHERE ID = "{idx}";
        """, fetch_one=True)[0]

    else:

        name = db.exec_script(f"""
        SELECT meridianName_zh from Meridian
        WHERE ID = "{idx}";
        """, fetch_one=True)[0]

    return name


def get_route(query):
    with sql.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute(f"""
        SELECT route, route_src FROM `meridianRoute`
        WHERE `meridianID` = "{query}"
        """)

        return c.fetchone()


def get_location(query):
    with sql.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute(f"""
        SELECT acuLoc_desc FROM `acuLoc`
        WHERE `acuID` = "{query}"
        """)

        return c.fetchone()[0]


def acupoints_in_meridian(meridian_id):
    with sql.connect(DB_PATH) as conn:
        c = conn.cursor()

        c.execute(f"""
        SELECT ID FROM `Meridian`
        WHERE `meridianExtra` = "1"
        """)

        extra = [item[0] for item in c.fetchall()]

        if meridian_id in extra and meridian_id not in ["CV", "GV"]:
            c.execute(f"""
            SELECT bypass, acuName_zh, acuName_en FROM `acuEx`
            LEFT JOIN `Acupoint` ON `Acupoint`.`ID` = bypass
            WHERE `acuEx`.`meridianID` = "{meridian_id}";
            """)
        else:
            c.execute(f"""
            SELECT ID, acuName_zh, acuName_en FROM `Acupoint`
            WHERE `meridianID` = "{meridian_id}"
            """)

    return c.fetchall()


def href_target(query):
    with sql.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute(f"""
        SELECT acuID, aliasName FROM `acuAlias`
        WHERE `aliasName` LIKE "%{query}%"
        UNION
        SELECT ID, acuName_zh FROM `Acupoint`
        WHERE `acuName_zh` LIKE "%{query}%"
        """)

        return c.fetchall()


def pentashu_table():
    with sql.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute('''
        SELECT `pentaShu_base`.`ID`, acuName_zh, attrib, `Meridian`.`ID`, yinyang_tri, cardinal FROM pentaShu_base
        JOIN Acupoint ON `pentaShu_base`.`ID` = `Acupoint`.`ID`
        JOIN Meridian ON `Meridian`.`ID` = `Acupoint`.`meridianID`
        ''')

        return c.fetchall()


def update_tokenizer_wordlist():
    with sql.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute('''
            SELECT 
            acuName_zh AS name FROM Acupoint
            UNION ALL
            SELECT 
            acuName_zh_sim AS name FROM Acupoint
            UNION ALL
            SELECT
            aliasName AS name FROM `acuAlias`
            UNION ALL
            SELECT
            meridianName_abbrev AS name FROM `Meridian`
            WHERE meridianExtra = 0
        ''')

        word_list = c.fetchall()

        word_list = {item[0]: [item[0]] for item in word_list}
        word_list['臍中央'] = ['臍', '中央']
        word_list['陰維'] = ['陰維']
        word_list['會陰維'] = ['會', '陰維']

        tok.dict_force = word_list

        return tok


def cardinal_table():
    with sql.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute('''
        SELECT `Acupoint`.`ID`, `acuName_zh`, attrib, elem FROM pentaShu_base
        JOIN `Acupoint` ON `Acupoint`.`ID` = pentaShu_base.ID
        WHERE cardinal = 1;
        ''')

        return c.fetchall()


def is_cardinal(acupoint):
    with sql.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute(f'''
        SELECT cardinal FROM pentaShu_base
        WHERE ID = "{acupoint}";
        ''')

        cardinal = c.fetchone()

        if cardinal and cardinal[0] == 1:
                return True


def is_pentashu(acupoint):
    with sql.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute(f'''
        SELECT attrib, elem FROM pentaShu_base
        WHERE ID = "{acupoint}";
        ''')

        pentashu = c.fetchone()

        if pentashu:
            return pentashu


def get_pentashu_label(acupoint):
    with sql.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute(f"""
        SELECT label FROM pentaShu
        WHERE ID = "{acupoint}";
        """)

        pentashu = c.fetchone()

        if pentashu:
            return pentashu[0]


def get_mu_shu_label(acupoint):
    with sql.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute(f"""
        SELECT som_emo, jb_func, org_vis, mu_shu FROM Mu_Shu
        WHERE acuID = "{acupoint}";
        """)

        mu_shu = c.fetchall()
        if mu_shu:
            return mu_shu


def get_extra_id(acupoint):
    with sql.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute(f"""
        SELECT meridianID, meridianName_zh FROM acuEx
        JOIN Meridian on Meridian.ID = meridianID
        WHERE bypass = "{acupoint}";
        """)

        extra = c.fetchall()

        if extra:
            return extra


def get_meridian_treatment_pt(acupoint, action):
    with sql.connect(DB_PATH) as conn:
        c = conn.cursor()

        if action == "++":

            c.execute(f"""
            SELECT meridianName_abbrev FROM Meridian
            WHERE tonify = "{acupoint}";
            """)

            meridian = c.fetchone()

        elif action == "--":

            c.execute(f"""
            SELECT meridianName_abbrev FROM Meridian
            WHERE disperse = "{acupoint}";
            """)

            meridian = c.fetchone()

        if meridian:
            return meridian[0]


def get_entry_exit_pt(acupoint):
    with sql.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute(f"""
        SELECT meridianName_abbrev FROM horary
        JOIN Meridian ON Meridian.ID = horary.ID
        WHERE entry = "{acupoint}";
        """)

        entry_pt = c.fetchone()

        c.execute(f"""
        SELECT meridianName_abbrev FROM horary
        JOIN Meridian ON Meridian.ID = horary.ID
        WHERE exit = "{acupoint}";
        """)

        exit_pt = c.fetchone()

        if entry_pt:
            return entry_pt[0] + "入穴"
        elif exit_pt:
            return exit_pt[0] + "出穴"


def qixue_yinyang(renying, pulse):
    with sql.connect(DB_PATH) as conn:
        c = conn.cursor()

        c.execute(f'''
        SELECT diagnose, treat_qty, treat_qual FROM diagnose_general
        WHERE stronger = "{renying}" AND pulse = "{pulse}"
        ''')

        diagnose = c.fetchall()[0]
        diagnose = [eval(item) if "[" in item else item for item in diagnose]

        return diagnose


def meridian_yinyang(status):
    with sql.connect(DB_PATH) as conn:
        c = conn.cursor()

        c.execute(f'''
        SELECT prescription FROM treat_meridian_qty
        WHERE rel_qty = "{status}"
        ''')

        diagnose = c.fetchall()[0]
        diagnose = [eval(item) if "[" in item else item for item in diagnose]

        return diagnose[0]





def get_horary(hour):
    with sql.connect(DB_PATH) as conn:
        c = conn.cursor()

        c.execute(f'''
        SELECT start, name from hour_conv
        WHERE start = {hour} OR end = {hour};
        ''')

        idx, name = c.fetchone()

        c.execute(f'''
                SELECT horary.ID, meridianName_abbrev from horary
                JOIN Meridian ON Meridian.ID = horary.ID
                WHERE time = {idx};
        ''')

        meridian_id, meridian = c.fetchone()

        return name, meridian_id, meridian


if __name__ == '__main__':
    pass

    # print(acupoints_in_meridian("CV"))
    # print(get_id("崑崙"))
    # print(href_target("幽門"))
    # print(get_acupoint("瞳子", fuzzy=False))
    # print(get_acupoint("瞳子"))
    # print(is_pentashu("LR1"))
    # print(update_tokenizer_wordlist())
    # diagnose, treat_qty, treat_qual = qixue_yinyang("L", "I")
    # print(get_pathogen("sy"))
    # print(phenom_preventive("寒", method="elem"))
    # print(get_extra_label("ST30"))
