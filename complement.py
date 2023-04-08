import pandas as pd
import numpy as np
from acupuncture.db import Database
from acupuncture.lookup import Calc
from acupuncture.meridian import Meridian
from googletrans import Translator


class GroupLuo:
    POINTS = (("PC5", "TE8"), ("SP6", "GB39"))
    LEFT_RIGHT = ("l", "r")
    YINYANG = (0, 1)
    TOP_BOTTOM = ("t", "b")

    def __init__(self, left_right, top_bottom=None, nature=None, hemiplegia=False):

        self.prescribe = None
        self.pos_lr = left_right  # "l" or "r"
        self.opp_pos_lr = Calc.paired_with(self.pos_lr, self.LEFT_RIGHT)

        self.points_yin = [yin for yin, yang in self.POINTS]
        self.points_yang = [yang for yin, yang in self.POINTS]

        if hemiplegia:
            self.nature = 0 if nature == "atonic" else 1 if nature == "spastic" else None

        else:

            self.nature = nature  # 0 or 1, representing yin or yang.
            self.opp_nature = Calc.paired_with(self.nature, self.YINYANG)

            self.pos_tb = top_bottom  # 0 or 1, representing top or bottom.
            self.pos_tb_idx = self.TOP_BOTTOM.index(top_bottom)
            self.opp_pos_tb = self.TOP_BOTTOM[self.pos_tb_idx - 1]
            self.opp_pos_tb_idx = self.TOP_BOTTOM.index(self.opp_pos_tb)

            self.target_point = self.POINTS[self.pos_tb_idx][self.nature]
            self.pt_opp_yinyang = self.POINTS[self.pos_tb_idx][self.opp_nature]  # 補同側
            self.pt_opp_pos_tb = self.POINTS[self.opp_pos_tb_idx][self.nature]  # 補雙側（課本補同側）

    def pain(self):

        target = None

        if self.nature == 1:
            target = [(self.target_point, "--"), self.pos_lr]

        elif self.nature == 0:
            target = [(self.target_point, "++"), self.pos_lr]

        opp = [(self.target_point, "++"), self.opp_pos_lr]
        adj = [(self.pt_opp_yinyang, "++"), self.pos_lr]
        tb = [(self.pt_opp_pos_tb, "++"), self.pos_lr]

        self.prescribe = [tb, adj, opp, target]

        return self.prescribe

    def hemiplegia(self):

        if self.nature == 0:

            # 陰性補陽瀉陰
            self.prescribe = [(pt, "++") for pt in self.points_yang] + \
                             [(pt, "--") for pt in self.points_yin]

        elif self.nature == 1:

            # 陽性補陰瀉陽
            self.prescribe = [(pt, "++") for pt in self.points_yin] + \
                             [(pt, "--") for pt in self.points_yang]

        pos = [self.opp_pos_lr] * 2 + [self.pos_lr] * 2

        self.prescribe = list(zip(self.prescribe, pos))

        return self.prescribe


class Luo(Meridian, Calc):

    df_dict = {
        'ID': ['LO01',
               'LO02',
               'LO03',
               'LO04',
               'LO05',
               'LO06',
               'LO07',
               'LO08',
               'LO09',
               'LO10',
               'LO11',
               'LO12',
               'LO13',
               'LO14',
               'LO15',
               'LO16'],

        'acuID': ['LU7',
                  'LI6',
                  'ST40',
                  'SP4',
                  'HT5',
                  'SI7',
                  'BL58',
                  'KI4',
                  'PC6',
                  'TE5',
                  'GB37',
                  'LR5',
                  'CV15',
                  'GV1',
                  'LO15',
                  'SP21'],

        'desc_zh': ['肺絡',
                    '大腸絡',
                    '胃絡',
                    '脾絡',
                    '心絡',
                    '小腸絡',
                    '膀胱絡',
                    '腎絡',
                    '心包絡',
                    '三焦絡',
                    '膽絡',
                    '肝絡',
                    '任脈絡',
                    '督脈絡',
                    '胃之大絡',
                    '脾之大絡'],

        'name_zh': ['列缺',
                    '偏歴',
                    '豐隆',
                    '公孫',
                    '通里',
                    '支正',
                    '飛陽',
                    '大鐘',
                    '內關',
                    '外關',
                    '光明',
                    '蠡溝',
                    '鳩尾',
                    '長強',
                    '虛里',
                    '大包'],

        'meridian': ['LU',
                     'LI',
                     'ST',
                     'SP',
                     'HT',
                     'SI',
                     'BL',
                     'KI',
                     'PC',
                     'TE',
                     'GB',
                     'LR',
                     'CV',
                     'GV',
                     'LO',
                     'LO'],

        'longitudinal_luo': ['Lungs LU 7 Paired organ (LI)',
                             'Large Intestine LI 6 (ShuStream: LI 3) Paired organ (LU)',
                             'Stomach ST 40 (ShuStream: ST 43) Paired organ (SP)',
                             'Spleen SP 4 Paired organ (ST)',
                             'Heart HT 5 Paired organ (SI)',
                             'Small Intestine SI 7 (ShuStream: SI 3) Paired organ(HT)',
                             'Bladder UB 58 (ShuStream: UB 65) Paired organ(KD)',
                             'Kidneys KD 4 Paired organ (UB)',
                             'Pericardium PC 6 Paired organ (TW)',
                             'Triple Warmer TW 5 (ShuStream: TW 3) Paired organ (PC)',
                             'Gallbladder GB 37 (Shu-Stream: GB 41) Paired organ (LV)',
                             'Liver LV 5 Paired organ (GB)',
                             'Ren Mai RM 15 Paired organ (DM)',
                             'Du Mai DM 1 Paired organ (RM)',
                             'Great Luo of Stomach (Xu Li)',
                             'Great Luo of Spleen (Da Bao) SP 21'],

        'trajectory': ['From LU7 to palm of hand, thenar eminence and fingers',
                       'From LI6 to arm, teeth and ear',
                       'From ST40 to external aspect of leg, to neck, head and DM 20, and to throat',
                       'From SP 4 to abdomen,intestines and stomach',
                       'From HT5 to heart,base of tongue and eye',
                       'From SI7 to elbow and shoulder (zone of LI15)',
                       'From UB58 to head',
                       'From KD4, curving around the heel,to UB60, knee,abdomen, heart and lumbar spine',
                       'From PC6 to cardiovascular system and mediastinum',
                       'From TW5 to external aspect of arm and chest',
                       'From GB37 to upper aspect of foot',
                       'From LV5 to testes and genital organs',
                       'From RM15 to pelvis minor',
                       'From DM1 to sides of spinal column, neck, crown of head, shoulders, scapulae, terminating at'
                       ' the inner and outer Bladder pathways and dorsal tendons',
                       'From below left breast to diaphragm and lung',
                       'From SP21 to chest and sides'],

        'deficiency_zh': ['口緊，呼吸困難，打哈欠（呵欠），出汗，尿頻',
                          '牙齒冷，隔膜非自主性收縮，壓迫、憋悶感',
                          '腿部肌肉萎縮',
                          '腹部刺痛',
                          '無法說話、不能言',
                          '生疣，痂疥（如疥瘡）',
                          '流鼻血，鼻流清涕',
                          '腰痛',
                          '頭項緊繃疼痛，心煩、焦慮，心前區疼痛',
                          '上肢肌肉鬆軟：雙手抓舉無力，肘鬆弛',
                          '雙腿軟弱無力，肌肉委縮，坐後無法站立',
                          '（男性）陰囊或陰莖奇癢無比，（女性）外陰瘙癢',
                          '瘙癢，下腹部皮膚瘙癢',
                          '頭部沉重，有震顫、眩暈感',
                          None,
                          '所有關節都無力'],

        'deficiency': ['Tight mouth, dyspnea, yawning, sweating, frequent urination',
                       'Cold in teeth, contraction of diaphragm, oppression',
                       'Muscular atrophy of legs',
                       'Stabbing abdominal pain',
                       'Inability to speak',
                       'Warts, scabs (as in scabies)',
                       'Epistaxis, rhinorrhea with clear liquid',
                       'Lumbar pain',
                       'Tight, painful head and neck, anxiety, precordialgia',
                       'Limpness of muscles of upper limb:the hands cannot grasp anything, limp elbow',
                       'Legs wasted, flaccid and weak: cannot stand up from sitting position',
                       'Severe itching of scrotum or penis, vulvar pruritus',
                       'Itching, abdominal pruritus',
                       'Heaviness of head with tremor, dizziness',
                       None,
                       'Loss of strength in all joints'],

        'excess_zh': ['手掌灼熱，手指疼痛，有燒灼感',
                      '齲齒，耳聾',
                      '喉嚨痹，失音，驚厥抽搐，吞嚥困難，癲癇，瘋狂癡呆，有痰液',
                      '腸腹脹，腹瀉，嘔吐，上吐下瀉，痢疾',
                      '膈膜非自主性收縮，疝氣',
                      '超機動性肘關節，肘廢不能用',
                      '鼻塞，頭痛，頭項強痛，背痛',
                      '足根痛，尿液少，憂慮、煩惱，無聊，焦慮',
                      '肩膀和上肢疼痛',
                      '肘部拘攣，不會伸展',
                      '手足冰冷，失去知覺，雷諾氏綜合症',
                      '睾丸或卵巢腫脹，陰囊疝，陰莖勃起疼痛、異常勃起',
                      '腹部皮膚疼痛，對輕微接觸也異常敏感',
                      '背部強直、攣縮',
                      '哮喘，呼吸困難（喘息），呼吸暫停（窒息），胸部壓迫、胸悶、假性心絞痛',
                      '周身疼痛：僵硬酸痛（流行性感冒）'],

        'excess': ['Heat in palm of hand, pain in fingers, burning sensation',
                   'Dental caries, deafness',
                   'Paralysis of throat, aphonia, convulsions, difficulty in swallowing, epilepsy, dementia, phlegm',
                   'Intestinal bloating, diarrhea, dysentery, vomiting',
                   'Involuntary contraction of diaphragm, hernia',
                   'Hyperlaxity or hypermobility of elbow, which does not function',
                   'Congested nose, headache, pain in neck and head, dorsal pain',
                   'Talalgia, scanty urine, worry, boredom, anxiety',
                   'Pain in shoulder and upper limb',
                   'Contracture of elbow, which will not extend',
                   "Cold in extremities, loss of consciousness, Raynaud's syndrome",
                   'Swelling of testes or ovaries, scrotal hernia, painful erection, priapism',
                   'Pain on skin of abdomen, which is sensitive to the slightest contact',
                   'Tight, stiff back',
                   'Asthma, dyspnea, apnea,oppression in chest: false angina pectoris',
                   'Pain throughout body: stiffness (influenza)']}

    def __init__(self, meridian=None, state=None):

        super().__init__()

        self.prescribe = None
        self.logic = None
        self.symptom = None

        self.target_luo = None  # A tuple of the luo meridian with the relevant symptom.
        self.target_luo_meridian = None
        self.target_luo_point = None
        self.target_luo_state = None

        self.paired_luo_meridian = None
        self.paired_luo_point = None

        if all([meridian, state]):

            self.meridian = meridian
            self.paired_meridian = self.get_paired_elem_from_list(meridian, self.SUP_PROFOUND) \
                if meridian != "LO" else None

            self.state = state
            self.paired_state = "+" if self.state == "-" else "-" if self.state == "+" else None

            self.meridian_yinyang = 0 if self.meridian in self.yin else 1 if self.meridian in self.yang else None
            self.paired_yinyang = 0 if self.meridian_yinyang == 1 else 1 if self.meridian_yinyang == 0 else None

            self.relative_state_label = None

    def balance(self):
        # 橫絡，聯繫相表裡的陰經與陽經

        data = [
            (self.meridian, self.meridian_yinyang, self.state),
            (self.paired_meridian, self.paired_yinyang, self.paired_state)
        ]

        if self.meridian_yinyang == 1:
            data = data[-1:] + data[:-1]  # swap list items, yin before yang.

        self.relative_state_label = [(m, s) for m, y, s in data]

        rel_state = [s for m, y, s in data]
        meridian_pair = [m for m, y, s in data]

        if rel_state == ["+", "-"]:  # 陰經有餘，陽經不足。

            self.prescribe = [
                (self.stream_point_of_meridian(meridian_pair[1]), "++"),
                (self.luo_point_of_meridian(meridian_pair[0]), "--"),
            ]

            self.logic = [
                "補陽經輸穴",
                "瀉陰經絡穴",
            ]

            return self.prescribe

        elif rel_state == ["-", "+"]:  # 陽經有餘，陰經不足。

            self.prescribe = [
                (self.luo_point_of_meridian(meridian_pair[0]), "++"),
                (self.luo_point_of_meridian(meridian_pair[1]), "--"),
            ]

            self.logic = [
                "補陰經絡穴",
                "瀉陽經絡穴",
            ]

            return self.prescribe

    def locate_symptom(self, symptom):

        db = Database()

        excess = db.exec_script(f"""
        SELECT ID, acuID, meridian, excess, excess_zh FROM Luo
        WHERE excess LIKE '%{symptom}%' OR excess_zh LIKE '%{symptom}%'
        """)

        deficient = db.exec_script(f"""
        SELECT ID, acuID, meridian, deficiency, deficiency_zh FROM Luo
        WHERE deficiency LIKE '%{symptom}%' OR deficiency_zh LIKE '%{symptom}%'
        """)

        if any([excess, deficient]):
            if all([excess, deficient]):
                return excess, deficient
            elif excess:
                if len(excess) == 1:
                    self.target_luo = [excess, "+"]
                    return self.target_luo
                else:
                    return "+", excess
            elif deficient:
                if len(deficient) == 1:
                    self.target_luo = [deficient, "-"]
                    return self.target_luo
                else:
                    return "-", deficient

    def treat_symptom(self):
        if self.target_luo:
            luo, state = self.target_luo

            if len(luo) == 1:

                luo = luo[0]
                self.target_luo_point = luo[1]
                self.target_luo_meridian = luo[2]
                self.target_luo_state = state

                self.paired_luo_meridian = self.get_paired_elem_from_list(self.target_luo_meridian, self.SUP_PROFOUND)
                self.paired_luo_point = self.luo_point_of_meridian(self.paired_luo_meridian)

                if state == "-":  # 緃絡不足
                    self.prescribe = [(self.target_luo_point, "++")]
                    self.logic = ["補虛脈絡穴"]

                elif state == "+":  # 緃絡有餘
                    if luo[0] not in ["LO15", "LO16"]:
                        self.prescribe = [
                            (self.paired_luo_point, "++"),
                            (self.stream_point_of_meridian(self.paired_luo_meridian), "++"),
                            (self.target_luo_point, "--"),
                        ]
                        self.logic = [
                            "補相表裡經脈的絡穴",
                            "或輸穴",
                            "瀉有餘絡脈的絡穴",
                        ]
                    else:
                        self.prescribe = [(self.target_luo_point, "--")]
                        self.logic = ["大絡直接瀉絡穴"]

        return self.prescribe

    @staticmethod
    def meridian_label():
        db = Database()
        lbl = db.exec_script("""
        SELECT ID, meridianName_abbrev FROM Meridian;
        """)
        if lbl:
            return lbl

    @staticmethod
    def luo_point_of_meridian(meridian):
        db = Database()
        luo = db.exec_script(f"""
        SELECT acuID FROM Luo
        WHERE meridian = '{meridian}';
        """, fetch_one=True)
        if luo:
            return luo[0]

    @staticmethod
    def stream_point_of_meridian(meridian):
        db = Database()
        stream = db.exec_script(f"""
        SELECT ID FROM Pentashu
        WHERE meridian_id = '{meridian}' and attrib = "輸";
        """, fetch_one=True)
        if stream:
            return stream[0]

    @staticmethod
    def is_luo_point(acupoint):
        db = Database()
        label = db.exec_script(f"""
        SELECT desc_zh FROM Luo
        WHERE acuID = '{acupoint}';
        """, fetch_one=True)
        if label:
            return label[0]

    def select_symptom(self, luo_id, state):
        db = Database()

        if state == "+":

            symptom = db.exec_script(f"""
            SELECT ID, acuID, meridian, excess, excess_zh FROM Luo
            WHERE ID = '{luo_id}';
            """, fetch_one=True)

            if symptom:
                self.target_luo = ([symptom], "+")
                return self.target_luo

        elif state == "-":

            symptom = db.exec_script(f"""
            SELECT ID, acuID, meridian, excess, excess_zh FROM Luo
            WHERE ID = '{luo_id}';
            """, fetch_one=True)

            if symptom:
                self.target_luo = [[symptom], "-"]
                return self.target_luo

    @staticmethod
    def translate_symptoms():

        db = Database()

        rslt = db.exec_script("""
        SELECT excess, deficiency from Luo;
        """)

        excess = [e for e, d in rslt]
        deficiency = [d for e, d, in rslt]

        translator = Translator()

        excess_zh = []
        for s in excess:
            if s is not None:
                excess_zh.append(translator.translate(s, src="en", dest="zh-TW").text)
            else:
                excess_zh.append(None)

        deficiency_zh = []
        for s in deficiency:
            if s is not None:
                deficiency_zh.append(translator.translate(s, src="en", dest="zh-TW").text)
            else:
                deficiency_zh.append(None)

        return excess_zh, deficiency_zh

    def build_db(self):

        db = Database()
        df = pd.DataFrame(self.df_dict)
        db.df_to_sql(df, "Luo")


if __name__ == '__main__':
    pass

    # l = Luo()

    # l.build_db()

    # print(l.balance())

    # excess, deficiency = l.translate_symptoms()
    # print(deficiency)

    # l.locate_symptom("掌灼熱")
    # print(l.treat_symptom())

    # gl = GroupLuo("r", nature="atonic", hemiplegia=True)
    # print(gl.hemiplegia())

