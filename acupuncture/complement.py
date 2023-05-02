import pandas as pd
import numpy as np
from acupuncture.db import Database
from acupuncture.lookup import Calc
from acupuncture.meridian import Meridian
from acupuncture.element import Pentashu, Season
from googletrans import Translator
from tabula import read_pdf


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


class Jingjin(Pentashu, Season):
    CONFLUENCE_PT = [
        ("GB22", ["LU", "HT", "PC"]),
        ("CV3", ["KI", "LR", "SP"]),
        ("GB13", ["LI", "SI", "TE"]),
        ("SI18", ["BL", "GB", "ST"]),
    ]

    df_dict = {
        'Jing Jin:\rTendino-muscular\rchannels Vessels':
            ['Lungs\rHui-Meeting Point:\rGB 22\r- Jing-Well: LU 11\r- Shu-Stream: LU 9\r- Jing-River: LU 8',
             'Large Intestine\rHui-Meeting Point:\rGB 13\r- Jing-Well: LI 1\r- Shu-Stream: LI 3\r- Jing-River: LI 5',
             'Stomach\rHui-Meeting Point:\rSI 18\r- Jing-Well: ST 45\r- Shu-Stream: ST 43\r- Jing-River: ST 41',
             'Spleen\rHui-Meeting Point:\rRM 3\r- Jing-Well: SP 1\r- Shu-Stream: SP 3\r- Jing-River: SP 5',
             'Heart\rHui-Meeting Point:\rGB 22\r- Jing-Well: HT 9\r- Shu-Stream: HT 7\r- Jing-River: HT 4',
             'Small Intestine\rHui-Meeting Point:\rGB 13\r- Jing-Well: SI 1\r- Shu-Stream: SI 3\r- Jing-River: SI 5',
             'Urinary Bladder\rHui-Meeting Point:\rSI 18\r- Jing-Well: UB 67\r- Shu-Stream: UB 65\r- Jing-River: UB 60',
             'Kidneys\rHui-Meeting Point:\rRM 3\r- Jing-Well: KD 1\r- Shu-Stream: KD 3\r- Jing-River: KD 7',
             'Pericardium\rHui-Meeting Point:\rGB 22\r- Jing-Well: PC 9\r- Shu-Stream: PC 7\r- Jing-River: PC 5',
             'Triple Warmer\rHui-Meeting Point:\rGB 13\r- Jing-Well: TW 1\r- Shu-Stream: TW 3\r- Jing-River: TW 6',
             'Gallbladder\rHui-Meeting Point:\rSI 18\r- Jing-Well: GB 44\r- Shu-Stream: GB 41\r- Jing-River: GB 38',
             'Liver\rHui-Meeting Point:\rRM 3\r- Jing-Well: LV 1\r- Shu-Stream: LV 3\r- Jing-River: LV 4'],

        'Trajectory':
            [
                'Thumb>thenaremi-\rnence>radialtunnel\r>forearm>elbow>\ranterior aspect of arm\r> underneath armpit >\rsubclavicularfossa>\rLI 15 > ST 12 > chest >\rdiaphragm>floating\rribs',
                'Extremity of forefinger\r> back of wrist > exter-\rnal border of forearm >\rexternal side of elbow\r>externalaspectof\rarm > LI 15\r-firstbranch>upper\rpart of scapula > inser-\rtion of T2 to T7\r-mainbranch>neck\r> side of nose > nasal\reminence GB 13 > skull\r>descendsagainto\rthe opposite corner of\rthe jaw',
                '- first branch: 2nd, 3rd\rand4thtoes>instep\r(ankle)>externalas-\rpect of leg, fibula > ex-\rternal aspect of knee >\rhip (joint) > side > spi-\rnal cord > T 11 - T 12\r-secondbranch:2nd,\r3rd and 4th toes > instep\r(ankle) > frontal aspect\rof leg >  front of knee\r(sending a small vessel\rto join the first branch )\r> ST  32 > loins (head of\rfemur) > genital organs\r> abdomen > subclavicular fossa >\rneck>aroundmouth\r> nose > a tiny vessel\rbelow the eye and ano-\rther at the front of the\rear',
                'Posterointernalangle\rofnailofgreattoe>\rinternal malleolus > ti-\rbia > internal aspect of\rthigh > hip > head of\rfemur > genital organs\r> abdomen > umbilicus\r> ribs > chest > frontal\raspect of spinal cord >\rT 11',
                'Externalextremityof\rlittlefinger>pisiform\rbone > internal elbow\r> internal arm > armpit\r>breast>sternum>\rdiaphragm > umbilicus',
                'Internalextremityof\rlittlefinger>backof\rwrist > internal aspect\rofforearm>epitro-\rchlea > back of arm >\runder armpit > behind\rand above fold of arm-\rpit > scapula > neck >\rtip of the mastoid > ear\r> lower mandibular an-\rgle > external angle of\reye > forehead',
                'First Part:\rExtremityoflittletoe\r> external malleolus >\rexternal aspect of knee\r> external aspect of leg\r> heel > external aspect\rof foot > external popli-\rteal cavity > descends\rdown middle of calf >\rinternal popliteal cavity\r>posterioraspectof\rthigh > buttock > spinal\rcord >\rSecond Part:\rFirstbranch:napeof\rneck > base of tongue\r>occiput>crownof\rhead > forehead > nose\r> eye > insertion at side\rof the nose\rSecondbranch:T8>\runder armpit and LI 15\r> in front of  armpit >\rsubclavicularfossa>\rtip of mastoid\rThird branch: T 1\r> subclavicular fossa >\rside of nose',
                'Beneath little toe > sole\rof foot > under internal\rmalleolus > heel > in-\rternal aspect of knee >\rthigh > genitals > spi-\rnal cord > nape of neck\r> occiput',
                'Middlefinger>inter-\rnal aspect of elbow >\rinternal aspect of arm\r> under armpit > infe-\rroanteriorexternalrib\rcage > inner aspect of\rchest  > diaphragm',
                'Fourth finger > forearm\r> elbow > arm > shoul-\rder > neck\rFirstbranch:angleof\rjaw > base of tongue\rSecondbranch:angle\rof jaw > in front of ear\r> external angle of the\reye > forehead > nasal\reminence: GB 13',
                'Fourth toe > above ex-\rternalmalleolus>ex-\rternal leg and knee >\rFirstbranch:external\rcondyle > ST 32\rSecond (principal)\rbranch:\rexternal aspect of thigh\r> hip > sacrum > extre-\rmity of floating ribs >\rchest > breast > in front\rthe armpit > subclavi-\rcular fossa > posterior\rear>temple>nasal\reminence>crownof\rhead>branchesto-\rwardslowerjaw,side\rofnoseandexternal\rangle of eye',
                'Big toe > antero-inter-\rnal region of malleolus\r> internal aspect of leg\r> internal tuberosity of\rtibia>internalaspect\rof thigh >\rgenital organs'],

        'Symptoms':
            [
                'Bi of the last month of\rwinter:\rJanuary 6 to February 4,\rend of winter\r- Ligaments contracted\r- respiratory blockage\r- vomiting of blood\r- costal ligaments\raffected',
                'Bi of the first month of\rsummer:\rMay 5 to June 5,\rstart of summer\r- Ligaments contracted\rand spasmic\r- blocked shoulder\r- not possible to rotate\rneck',
                'Bi of the last month of\rspring:\rApril 4 to May 5 ,\rEnd of spring\rLigaments contracted\r- cramps in second,\rthird, fourth toes - fron-\rtal aspect of leg - region\rof ST 32 (Fu Tu – crou-\rching rabbit) - edema\rof pubis - spasms in the\rgenital and abdomen\rregion, subclavicular\rfossa and jaw – pulling\rof muscles in the ocu-\rlar region: When due to cold, the\reyecannotclose,dis-\rplacement of the angle\rof the mouth; when due\rto heat, paralysis of the\rmuscles of the jaw, the\reyes cannot open',
                'Bi of the first month of\rautumn:\rAugust 6 to September 6,\rstart of autumn\rLigamentscontrac-\rted - pain in great toe,\rinternalmalleolus-\rcramps in calf, internal\raspect of thigh - genital\rcontractures - pain in\rumbilical region, ribs,\rspinal cord',
                'Bi of the second month\rof winter:\rDecember 7 to January 6,\rWinter solstice\rLigaments contracted -\rpain from umbilicus to\rheart:aggravatedby\rlyingfacedownona\rhard surface',
                'Bi of the second month\rof summer:\rJune 5 to July 5,\rSummer solstice\rLigaments contracted\r- earache, internal as-\rpect of elbow and arm,\rarmpit, scapula, neck -\rNoise causes pain from\rear to chin - eye closed\rconstantly - edema of\rneck - stiff neck',
                'Bi of the second month\rof spring:\rMarch 4 to April 4,\rSpring equinox\r\rFirst Part:\rLigamentscontrac-\rted - cramps - pain or\redema of little toe and\rheel-poplitealcavity\rcontracted - opisthoto-\rnos\rSecond Part:\rMuscles and ligaments\rof the nape of neck\rstiff - shoulder cannot\rbe raised - tractive, fili-\rform pain from armpit\rto subclavicular fossa',
                'Bi of the second month\rof autumn:\rSeptember 6 to Octo-\rber 6,\rAutumn equinox\rLigaments contracted -\rcramps in sole of foot\r-spasms,convulsions\r–impossible to lean\reither forwards or bac-\rkwards',
                'Bi of the first month of\rwinter:\rNovember 6 - Decem-\rber 7,\rstart of winter\rLigaments contracted -\rblockage of respiration\r- spasms of cardia',
                'Bi of the last month of\rsummer:\rJuly 5 to August 6,\rend of summer\rLigaments contracted,\rspasmic - the tongue\rbends back on itself',
                'Bi of the first month of\rspring:\rFebruary 4 to March 4,\rstart of spring\rFirst branch:\rLigamentscontracted\r- cramps in fourth toe\rand calf - the knee joint\rcannot be either flexed\ror extended\rSecond (principal)\rbranch:\rPain in pubis, sacrum,\rhypochondria,floating\rribs, subclavicular fos-\rsa, throat - attack from\rone side: the opposite\reye cannot open –injury\rof the nasal eminence:\rthe opposite foot can-\rnot move',
                'Bi of the last month of\rautumn:\rOctober 6 to Novem-\rber 6\rEnd of autumn\rLigamentscontracted\r- pain in first toe, front\rantero-internal malleo-\rlus,internalaspectof\rknee - cramp in internal\rthigh-permanentor\rabsent erection'],

        'meridian': [
            "LU",
            "LI",
            "ST",
            "SP",
            "HT",
            "SI",
            "BL",
            "KI",
            "PC",
            "TE",
            "GB",
            "LR",
        ],

        'confluence_pt': [
            'GB22',
            'GB13',
            'SI18',
            'CV3',
            'GB22',
            'GB13',
            'SI18',
            'CV3',
            'GB22',
            'GB13',
            'SI18',
            'CV3',
        ],

        'period': [
            "冬末",
            "夏初",
            "春末",
            "秋初",
            "冬至",
            "夏至",
            "春分",
            "秋分",
            "冬初",
            "夏末",
            "春初",
            "秋末",
        ],

        'month': [1, 5, 4, 8, 12, 6, 3, 9, 11, 7, 2, 10],

        'symptoms_zh': ['韌帶收縮，呼吸阻塞，吐血，脅肋拘急',
                        '韌帶收縮痙攣 ， 肩不舉 ， 無法轉動頸部',
                        '韌帶收縮 ， 第二，第三，第四腳趾的痙攣（抽筋） ， 腿部股前筋肉拘緊（伏兔位置） ， 恥骨部位水腫 ， 生殖器和腹部區域的痙攣，向上牽掣到鎖骨下窩和頰部（下巴）\n'
                        '如有寒邪則掣引眼瞼不能閉合，嘴角歪斜；有熱則頰部（頜骨）肌肉癱瘓，眼睛無法睜開，面癱',
                        '韌帶收縮 ， 大趾、內踝疼痛，（小腿）腓腸肌、大腿的內側筋肉痙攣 ， 陰部緊縮疼痛 ， 臍、兩脅（肋骨），脊柱疼痛',
                        '韌帶收縮，臍部到心區疼痛：俯卧在硬板上疼痛加劇',
                        '韌帶收縮，耳痛，肘和手臂內側、腋窩、肩胛、頸部疼痛，噪聲引發耳朵到下巴（頷部）的疼痛，眼睛始終閉合，頸部水腫、僵硬，斜頸',
                        '第一部分：韌帶收縮，抽筋（痙攣），常見小趾或足跟（腳後跟）疼痛或水腫， 膕窩部攣急，角弓反張，坐骨神經痛；\n'
                        '第二部分：頸部肌肉及韌帶僵值，肩不能抬起，從腋部到鎖骨下窩（冠狀窩）牽掣如絲狀疼痛',
                        '韌帶收縮，腳底板抽筋，痙攣、抽搐，不能前俯後仰，（腰痛、腳心痛）',
                        '韌帶收縮，呼吸阻塞，賁門痙攣',
                        '韌帶收縮，痙攣，舌頭卷縮，肌腱炎',
                        '第一分支開始：韌帶收縮，第四腳趾和腓腸肌痙戀（抽筋）， 膝關節不能屈伸；\n'
                        '第二個（主要）分支：恥骨、骶骨、季肋部、浮肋、鎖骨下窩、咽部（喉嚨）疼痛 ， 患側筋肉拘急時，對側眼睛不能張開，\n'
                        '患側額角（鼻降起？）受傷，引發對側腳不能移動',
                        '韌帶收縮，足大趾、內踝尖前部、膝蓋內側疼痛 ，大腿內側痙攣，陽痿或異常勃起，帶狀疱疹（帶脈、絡穴）']

    }

    def __init__(self, season_section=None):
        super().__init__()
        self.symptom_zh = None
        self.confluence_pt = None
        self.meridian = None
        self.month = None
        self.well = None
        self.stream = None
        self.river = None

        self.season_section = season_section

    @staticmethod
    def get_jj_table():

        data = read_pdf("Pialoux_AC_guide.pdf", pages="146-150", stream=True, lattice=True)
        df_list = [data[i] for i in range(len(data))]
        df = pd.concat(df_list, ignore_index=True)

        return df.to_dict("list")

    def translate_symptoms(self):

        translator = Translator()

        translated = []

        for symptom in self.df_dict['Symptoms']:
            symptom = symptom.replace("-\r", "")
            symptom = symptom.replace("\r", " ")
            translated.append(translator.translate(symptom, src="en", dest="zh-TW").text)

        return translated

    @classmethod
    def build_db(cls):
        db = Database()
        df = pd.DataFrame(cls.df_dict)

        db.df_to_sql(df, "Jingjin")

    @classmethod
    def meridian_to_confluence(cls, meridian):
        return [pt for pt, meridian_list in cls.CONFLUENCE_PT if meridian in meridian_list]

    @classmethod
    def well_stream_river(cls, meridian):
        """Get a meridian's jing 井, shu 輸 and jing 經 acupoints."""

        well = cls.specific_point_of_meridian(meridian, "井")
        stream = cls.specific_point_of_meridian(meridian, "輸")
        river = cls.specific_point_of_meridian(meridian, "經")

        return well, stream, river

    def diagnose(self, period):
        db = Database()
        rslt = db.exec_script(f"""
        SELECT meridian, confluence_pt, month, symptoms_zh FROM Jingjin
        WHERE period = "{period}";
        """, fetch_one=True)
        if rslt:
            self.season_section = period
            self.meridian, self.confluence_pt, self.month, self.symptom_zh = rslt
            self.well, self.stream, self.river = self.well_stream_river(self.meridian)

            return [
                (self.confluence_pt, "++"),
                (self.well, "++"),
                (self.stream, "++"),
                (self.river, "++"),
            ]

    def current_season_section(self):
        return self.current_season()[-1]

    # @classmethod
    # def season_section_labels(cls):
    #     return cls.season_section_labels


class Jingbie:
    df_dict = {
        'Jing Bie\rDivergent Channels': [

            'Lungs\rExtremity point on the\ropposite side: LU 11\rPaired organ: Large\rIntestine',

            'Large Intestine\rExtremity point on the\ropposite side:\rLI 1 & LU 11\rPaired organ: Lungs',

            'Stomach\rExtremity point on the\ropposite side: ST 45\rPaired organ: Spleen',

            'Spleen\rPoint to tonify:\rRM 2 (opposite side)\rPaired organ: Stomach',

            'Heart\rExtremity point on the\ropposite side: HT 9\rPaired organ: Small\rIntestine',

            'Small Intestine\rExtremity point on the\ropposite side: SI 1\rPaired organ: Heart',

            'Urinary Bladder\rExtremity point on the\ropposite side: UB 67\rPaired organ: Kidneys',

            'Kidney\rExtremity point on the\ropposite side: KD 1\rPaired organ: Urinary\rBladder',

            'Pericardium\rExtremity point on the\ropposite side: PC 9\rPaired organ:\rTriple Warmer',

            'Triple Warmer\rExtremity point on the\ropposite side:\rTW 1 & PC 9\rPaired organ: Pericardium',

            'Gallbladder\rExtremity point on the\ropposite side:\rGB 44 & UB 67\rPaired organ: Liver',

            'Liver\rExtremity point on the\ropposite side: LV 1\rPaired organ: Gallbladder'],

        'Trajectory': [

            'Entry point: LU 5\r> in front of the armpit >\rPenetration point: LU 1\r> lungs > large intestine > '
            'Point of emergence: subclavicular\rfossa > neck\rHui-Meeting point: LI 18',

            'Entry point: LI 11\r> branching to thorax,\rbreast >\rPenetration point LI 15\r> back of neck > '
            'spinal\rcord > large intestine >\rlungs > Point of emergence: subclavicular\rfossa > '
            'neck\rHui-Meeting point: LI 18',

            'Entry point: ST 36\r> hip >\rPenetration point: ST30\r> abdomen > stomach\r> spleen > heart > '
            'esophagus > mouth > Point\rof emergence: bridge of\rnose > orbit > forehead\r> internal angle of '
            'eye\rHui-Meeting point: UB 1',

            'Entry point: SP 9\r> hip >\rPenetration point: SP 12\r> abdomen > spleen\r> stomach > heart >\rparallel '
            'to the Jing Bie\rof stomach  >\rHui-Meeting point: UB 1',

            'Entry point: HT 3\r> armpit >\rPenetration point: HT 1\r> chest > heart > throat\r> Point of '
            'emergence:\rface > internal angle\rof eye\rHui-Meeting point: UB 1',

            'Entry point: SI  8\r> shoulder > behind\rarmpit >\rPenetration point: SI 10\r> small intestine >\rheart '
            '> throat >\rPoint of emergence:\rinternal face > angle\rof eye\rHui-Meeting point: UB 1',

            'Entry point UB 40\rPenetration point:\rUB 40\r> anus > bladder >\rkidney > vertebral column > heart > '
            'Point of\remergence: posterior\rbase of neck > nape of\rneck\rHui-Meeting point: UB 10',

            'Entry point: KD 10\rPenetration point: KD 10\r> bladder > kidney > L2\r> DM 4 > heart '
            '>\rPoint of emergence:\rnape of neck\rHui-Meeting point: UB 10',

            'Entry point: PC 3\r> armpit\rPenetration point: PC 1\r> thorax > organs and\rviscera of the three '
            'burners > throat > ear >\rPoint of emergence: tip\rof the mastoid\rHui-Meeting point: TW 16',

            'Entry point: TW 10\r> crown of head >\rPenetration point: DM 20\rBack of ear > subclavicular fossa > '
            'organs\rand viscera of Triple\rHeater> branching to\rthorax > throat > ear >\rPoint of emergence: tip\rof '
            'mastoid\rHui-Meeting point: TW 16',

            'Entry point: GB 34\r>posterior part of hip >\rPenetration point: GB 30\rpubis > abdomen > tip\rof 11th '
            'rib > gall bladder>liver>heart>\resophagus > throat '
            '>\rPoint of emergence:\rchin>mouth>forehead>externalangle\rof eye\rHui-Meeting point: GB 1',

            'Entry point: LV 8\r> instep  (ankle)>\rPenetration point: LV 5\r>pubis> parallel to\rJing Bie of '
            'gallbladder\r> Point of emergence:\rchin>mouth>forehead>external angle\rof eye\rHui-Meeting point: GB '
            '1'],

        'Lateralized symptoms\r(onset or aggravation)': [

            'Between 3 a.m. and 5\ra.m.:\rAsthma - acceleration\rof respiratory rhythm –\rheat in chest',

            'From 5 a.m. to 7 a.m.:\rPain in angle of transverse colon,shoulder,\rsubclavicular fossa,\rthroat - heat '
            'in chest, hand contorted, headache',

            'From 7 a.m. to 9 a.m.:\rMigraine, epistaxis',

            'From 9 a.m. to 11 a.m.\rLumbar pain radiating\rdownwards to the sides and lower abdomen – impossibility '
            'of\rlying on the back',

            'From 11 a.m. to 1 p.m.\rPrecordalgia-oppression',

            'From 1 p.m.. to 3 p.m.\rIntense ringing in ears\r- deafness',

            'From 3 p.m. to 5 p.m.\rPain in the neck and\rhead',

            'From 5 p.m. to 7 p.m.\rBloating - thoracic oppression - pain in heart',

            'From 7 p.m. to 9 p.m.\rSore throat > dry mouth\r> anxiety > precordalgia',

            'From 9 p.m. to 11 p.m.\rPain in the throat > migraines > dry mouth >\ranxiety > precordalgia',

            'From 11 p.m. to 1 a.m.\rOppression in chest cough - sweating',

            'From 1 a.m. to 3 a.m.\rPain in genital organs']}

    def __init__(self):
        pass

    @staticmethod
    def get_jb_table():
        data = read_pdf("Pialoux_AC_guide.pdf", pages="152-154", stream=True, lattice=True)
        df_list = [data[i] for i in range(len(data))]
        df = pd.concat(df_list, ignore_index=True)

        return df.to_dict("list")


if __name__ == '__main__':
    pass

    # jb = Jingbie()
    # print(jb.get_jb_table())

    # print(jj.translate_symptoms())
    # print(Jingjin.meridian_to_confluence())

    # print(jj.diagnose("春分"))
    # print(jj.symptom_zh)

    l = Luo()

    # l.build_db()

    # print(l.balance())

    # excess, deficiency = l.translate_symptoms()
    # print(deficiency)

    l.locate_symptom("鼻塞")
    print(l.treat_symptom())

    # gl = GroupLuo("r", nature="atonic", hemiplegia=True)
    # print(gl.hemiplegia())
