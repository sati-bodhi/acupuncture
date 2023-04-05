import pandas as pd
import numpy as np
from acupuncture.db import Database
from acupuncture.lookup import Calc
from acupuncture.element import Pentashu


class Meridian(Calc):
    
    SUP_PROFOUND = [
        # 臟腑表裡關係
        ("GB", "LR"),
        ("SI", "HT"),
        ("ST", "SP"),
        ("LI", "LU"),
        ("BL", "KI"),
        ("TE", "PC"),
    ]

    MERIDIAN = ("LU", "LI", "ST", "SP", "HT", "SI", "BL", "KI", "PC", "TE", "GB", "LR")
    BRANCH = ('子', '丑', '寅', '卯', '辰', '巳', '午', '未', '申', '酉', '戌', '亥')
    ELEM = ("木", "火", "土", "金", "水")

    def __init__(self):

        super().__init__()
        self.yin = [yin for yang, yin in self.SUP_PROFOUND]
        self.yang = [yang for yang, yin in self.SUP_PROFOUND]

    @staticmethod
    def meridian_of(acupoint):
        meridian = "".join(x for x in acupoint if not x.isdigit())
        return meridian

    @staticmethod
    def acupoints_in_meridian(meridian): 
        db = Database()
        acupoints = db.exec_script(f"""
        SELECT ID FROM Acupoint
        WHERE meridianID = "{meridian}";
        """)

        return [i[0] for i in acupoints]

    @staticmethod
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
    
    
class Phenomena(Meridian, Pentashu):
    PHENOM = ("風", "火", "濕", "燥", "寒")
    MERIDIAN_TYPE_PAIRS = [("ty", "YM"), ("sy", "TY"), ("jy", "SY")]
    PATHOGEN_PAIRS = [("濕", "燥"), ("熱", "寒"), ("風", "暑")]

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

    def __init__(self, pathogen=None):
        super().__init__()

        if pathogen:
            self.pathogen = pathogen
            self.meridian_type = self.pathogen_to_meridian_type(self.pathogen)
            self.opp_pathogen = self.get_paired_elem_from_list(self.pathogen, self.PATHOGEN_PAIRS)
            self.opp_meridian = self.get_paired_elem_from_list(self.meridian_type, self.MERIDIAN_TYPE_PAIRS)

            self.meridian_type_name_zh = self.meridian_type_id_to_name(self.meridian_type)
            self.opp_meridian_name_zh = self.meridian_type_id_to_name(self.opp_meridian)

        self.preventive_method = "mother_son"
        self.preventive_prescription = None
        self.treatment_prescription = None
        self.knot_prescription = None

        self.logic_prevent = []
        self.logic_treat = []

        self.fortify = None
        self.tonify = None
        self.disperse = None

    def phenom_prevent(self):
        """預防六淫，在六經根穴位上應用補母瀉子法。主要作用於經脈的能量上，屬表。"""

        db = Database()

        # 補以邪氣為屬性的穴位
        # （經脈屬性幫人預防相關外邪。如太陽經主寒，補經氣可使人禦寒。）
        # 用根補穴。
        to_tonify = db.exec_script(f'''
        SELECT root_tonify FROM env_phenomena
        JOIN env_pathogen ON phenomena = pathogen
        WHERE phenomena = "{self.pathogen}";
        ''', fetch_one=True)[0]

        self.tonify = (to_tonify, "++")
        self.logic_prevent.append(f"根補穴<br>"
                                  f"{self.get_attributes(to_tonify)}<br>"
                                  f"【{self.meridian_type_name_zh}－{self.pathogen}】")

        if self.preventive_method == "mother_son":

            # 補母瀉子法，用根瀉穴。
            # 瀉除對應經脈的經氣可增強人體對抗邪氣的反面能量。
            to_disperse = db.exec_script(f'''
            SELECT root_disperse FROM env_phenomena
            JOIN env_pathogen ON phenomena = pathogen
            WHERE phenomena = (SELECT treatment FROM env_pathogen WHERE pathogen = "{self.pathogen}");
            ''', fetch_one=True)[0]

            self.disperse = (to_disperse, "--")
            self.logic_prevent.append(f"根瀉穴<br>"
                                      f"{self.get_attributes(to_disperse)}<br>"
                                      f"【{self.opp_meridian_name_zh}－{self.opp_pathogen}】")

            return self.tonify, self.disperse

        elif self.preventive_method == "elem":

            # 五行補瀉法，用對應經脈五輸穴（五行）六氣屬性相反的穴位來抵禦邪氣。
            # 此根據 Sylvie 上課的說法，與課本有出入。
            to_disperse = db.exec_script(f'''
            SELECT `pentashu`.`ID` FROM pentashu
            JOIN env_pathogen ON phenom_tri = pathogen
            WHERE phenom_elem = (SELECT elem_treatment FROM env_pathogen WHERE pathogen = "{self.pathogen}") AND
            phenom_tri = (SELECT treatment FROM env_pathogen WHERE pathogen = "{self.pathogen}") AND 
            meridian_limb = "F";
            ''', fetch_one=True)[0]

            self.disperse = (to_disperse, "--")
            self.logic_prevent.append(f"{self.get_attributes(to_disperse)}<br>"
                                      f"【{self.opp_meridian_name_zh}－{self.opp_pathogen}】")

            return self.tonify, self.disperse

    def phenom_treat(self):
        """排除外邪，在五輸穴上應用根穴位的五行屬性。主要作用於經脈與臟腑能量的對應關係上，屬裡。"""

        db = Database()

        # 補對應經脈屬性與病邪相反的五輸穴
        to_tonify = db.exec_script(f'''
        SELECT `pentashu`.`ID` FROM pentashu
        JOIN env_pathogen ON phenom_tri = pathogen
        WHERE phenom_elem = (SELECT elem_treatment FROM env_pathogen WHERE pathogen = "{self.pathogen}") AND
        phenom_tri = (SELECT treatment FROM env_pathogen WHERE pathogen = "{self.pathogen}") AND 
        meridian_limb = "F";
        ''', fetch_one=True)[0]

        self.tonify = (to_tonify, "++")
        self.logic_treat.append(f"{self.get_attributes(to_tonify)}<br>"
                                f"【{self.opp_meridian_name_zh}－{self.opp_pathogen}】")

        # 瀉邪氣；由經脈屬性與病邪相同的五輸穴來處理
        to_disperse = db.exec_script(f'''
        SELECT `pentashu`.`ID` FROM pentashu
        JOIN env_pathogen ON phenom_tri = pathogen
        WHERE phenom_elem = (SELECT elem_treatment FROM env_pathogen WHERE treatment = "{self.pathogen}") AND
        phenom_tri = "{self.pathogen}" AND 
        meridian_limb = "F";        
        ''', fetch_one=True)[0]

        self.disperse = (to_disperse, "--")
        self.logic_treat.append(f"瀉邪氣<br>"
                                f"{self.get_attributes(to_disperse)}<br>"
                                f"【{self.meridian_type_name_zh}－{self.pathogen}】")

        # 補回被外邪入侵的經脈的能量；由相關經脈的根補穴來進行

        to_fortify = db.exec_script(f'''
        SELECT root_tonify FROM env_phenomena
        JOIN env_pathogen ON phenomena = pathogen
        WHERE phenomena = "{self.pathogen}"; 
        ''', fetch_one=True)[0]

        self.fortify = (to_fortify, "++")
        self.logic_treat.append(f"根補穴<br>"
                                f"{self.get_attributes(to_fortify)}<br>"
                                f"【{self.meridian_type_name_zh}－{self.pathogen}】")

        return self.tonify, self.disperse, self.fortify
        
    @staticmethod
    def root_knot(tri):
        
        db = Database()

        zh, tr, knot = db.exec_script(f'''
        SELECT yinyang_tri, yinyang_tri_tr, root_knot FROM env_phenomena
        WHERE id = "{tri}";
        ''', fetch_one=True)

        return zh, tr, (knot, "--")

    def meridian_type_id_to_name(self, type_id):
        name = self.phenomena_df.loc[self.phenomena_df["id"] == type_id, "yinyang_tri"].item()
        return name

    @staticmethod
    def meridian_type_to_pathogen(tri):
        """Get pathogen related to a meridian type."""
        
        db = Database()

        pathogen = db.exec_script(f'''
        SELECT pathogen FROM env_pathogen
        WHERE ID = "{tri}"
        ''', fetch_one=True)[0]

        return pathogen

    @staticmethod
    def pathogen_to_meridian_type(pathogen):
        """Get pathogen related to a meridian type."""

        db = Database()

        type_id = db.exec_script(f'''
        SELECT ID FROM env_pathogen
        WHERE pathogen = "{pathogen}"
        ''', fetch_one=True)[0]

        return type_id
    #
    # def prescribe_preventive(self, pathogen_list):
    #     """Batch processing preventive prescriptions."""
    #
    #     self.preventive_prescription = []
    #     for pathogen in pathogen_list:
    #         self.preventive_prescription.append(
    #             self.phenom_prevent(pathogen))
    #
    #     return self.preventive_prescription
    #
    # def prescribe_treatment(self, pathogen_list):
    #     """Batch processing treatment prescriptions."""
    #
    #     self.treatment_prescription = []
    #     for pathogen in pathogen_list:
    #         self.treatment_prescription.append(self.phenom_treat(pathogen))
    #
    #         return self.treatment_prescription
    #
    # def prescribe_knot(self, knot_list):
    #     """Batch processing knot-point prescriptions."""
    #
    #     self.knot_prescription = []
    #     for meridian in knot_list:
    #         self.knot_prescription.append(self.get_root_knot(meridian))
    #
    #     return self.knot_prescription

    def diagnose(self):
        pass


if __name__ == '__main__':
    pass
    treat = Phenomena()
    treat.pathogen_list = ["sy", "YM"]
    # print(prevent.phenom_prevent("暑"))
    print(treat.prescribe_treatment())
