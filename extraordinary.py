from acupuncture.db import Database
import numpy as np
import pandas as pd

# 十二正經交會穴

tv = [
    'ST30',
    'KI11',
    'KI12',
    'KI13',
    'KI14',
    'KI15',
    'KI16',
    'KI17',
    'KI18',
    'KI19',
    'KI20',
    'KI21',
]

bv = ['GB26', 'GB27', 'GB28', 'LR13']

yinlv = ['KI9', 'SP13', 'SP15', 'SP16', 'LR14', 'CV22', 'CV23']

yanglv = [
    'BL63',
    'GB35',
    'GB24',
    'SI10',
    'LI14',
    'GB21',
    'TE15',
    'GB13',
    'GB14',
    'GB15',
    'GB16',
    'GB17',
    'GB18',
    'GB19',
    'GB20',
    'GV16',
    'GV15',
]

yinhv = ['KI2', 'KI6', 'KI8', 'BL1']

yanghv = [
    'BL62',
    'BL61',
    'BL59',
    'GB29',
    'SI10',
    'LI15',
    'LI16',
    'ST4',
    'ST3',
    'ST1',
    'BL1',
    'GB20',
    'GV16',
]


class Extraordinary:

    PAIRS = [
        ("TV", "YinLV"),
        ("YinHV", "CV"),
        ("GV", "YangHV"),
        ("YangLV", "BV"),
    ]

    OPPOSITES = [
        ("CV", "GV"),
        ("YinHV", "YangHV"),
        ("YinLV", "YangLV"),
        ("TV", "BV"),
    ]

    MASTER_PTS = {
        "TV": "SP4",
        "YinLV": "PC6",
        "YinHV": "KI6",
        "CV": "LU7",
        "GV": "SI3",
        "YangHV": "BL62",
        "YangLV": "TE5",
        "BV": "GB41",
    }

    def __init__(self):

        self.opp_paired_ex_meridian = None
        self.opp_paired_meridian = None
        self.paired_ex_meridian = None
        self.paired_meridian = None
        self.meridian = None
        self.opp_meridian = None
        self.ex_meridian = None
        self.opp_ex_meridian = None

        self.bypass = {
            "TV": tv,
            "BV": bv,
            "YinLV": yinlv,
            "YangLV": yanglv,
            "YinHV": yinhv,
            "YangHV": yanghv,
            "CV": self.acupoints_in_meridian("CV"),
            "GV": self.acupoints_in_meridian("GV"),
              }

        self.meridian_to_ex = {"".join(x for x in k if not x.isdigit()): v for k, v in zip(self.MASTER_PTS.values(), self.MASTER_PTS.keys())}

        self.acting_meridians = [self.meridian_of(point)
                                 for point in list(self.MASTER_PTS.values())]

        self.pt_opposites = [(self.MASTER_PTS[yin], self.MASTER_PTS[yang]) for yin, yang in self.OPPOSITES]
        self.meridian_opposites = [(self.meridian_of(yin), self.meridian_of(yang)) for yin, yang in self.pt_opposites]
        self.pt_pairs = [(self.MASTER_PTS[a], self.MASTER_PTS[b]) for a, b in self.PAIRS]
        self.meridian_pairs = [(self.meridian_of(a), self.meridian_of(b)) for a, b in self.pt_pairs]

    @staticmethod
    def meridian_of(acupoint):
        meridian = "".join(x for x in acupoint if not x.isdigit())
        return meridian

    @staticmethod
    def generate_accompany_data(ex_lst, ex_meridian):
        meridian_id = np.array([ex_meridian] * len(ex_lst))
        acu_ex_id = list(range(1, len(ex_lst) + 1))
        acu_ex_id = [str(n).zfill(2) for n in acu_ex_id]
        acu_ex_id = np.array(acu_ex_id)
        acu_ex_id = np.char.add(meridian_id, acu_ex_id)

        return acu_ex_id, meridian_id

    def ex_df_dict(self):
        all_idx = []
        all_mer = []

        ex_id = list(self.bypass.keys())
        points = list(self.bypass.values())

        for i, m in enumerate(points):
            idx, mer = self.generate_accompany_data(m, ex_id[i])
            all_idx += list(idx)
            all_mer += list(mer)

        df_dict = {
            "ID": all_idx,
            "bypass": [item for sublist in points for item in sublist],
            "meridianID": all_mer,
        }

        return df_dict

    def rebuild_ex_db(self):

        df_dict = self.ex_df_dict()

        df = pd.DataFrame(df_dict)

        db = Database()
        db.df_to_sql(df, "acuEx")

    @staticmethod
    def elem_index_in_list_of_tuples(elem, lst):
        """Return index element in nested tuple."""
        i = None
        j = None
        for i, tup in enumerate(lst):
            if elem in tup:
                j = tup.index(elem)

                return i, j

    def get_paired_elem(self, elem, lst):
        """Returns the paired element from a list of binary tuples."""
        i, j = self.elem_index_in_list_of_tuples(elem, lst)
        if j == 0:
            paired = lst[i][1]

            return paired

        elif j == 1:
            paired = lst[i][0]

            return paired

    def relative_energies(self, meridian, state):

        i = None
        j = None
        opp_meridian = None

        if meridian in self.acting_meridians:  # is ordinary vessel with a master point
            opp_meridian = self.get_paired_elem(meridian, self.meridian_opposites)

        elif meridian in list(self.MASTER_PTS.keys()):  # is extraordinary vessel
            opp_meridian = self.get_paired_elem(meridian, self.OPPOSITES)

        if opp_meridian:
            if state == "-":
                return opp_meridian, "+"

            elif state == "+":
                return opp_meridian, "-"

    def meridian_to_ex_meridian_energy(self, meridian, state="-"):

        i, j = self.elem_index_in_list_of_tuples(meridian, self.meridian_opposites)
        ex_meridian = self.OPPOSITES[i][j]
        if state == "-":
            return ex_meridian, "+"
        elif state == "+":
            return ex_meridian, "-"

    def diagnose_deficiency(self, meridian):
        """Assume deficiency because extraordinary meridian pathologies
        are always due to excess."""
        self.meridian = (meridian, "-")
        self.ex_meridian = self.meridian_to_ex_meridian_energy(meridian, "-")

        self.opp_meridian = self.relative_energies(meridian, "-")
        self.opp_ex_meridian = self.relative_energies(*self.ex_meridian)

        self.paired_meridian = self.get_paired_elem(meridian, self.meridian_pairs)
        self.paired_ex_meridian = self.meridian_to_ex[self.paired_meridian]

        self.opp_paired_meridian = self.get_paired_elem(self.opp_meridian[0], self.meridian_pairs)
        self.opp_paired_ex_meridian = self.meridian_to_ex[self.opp_paired_meridian]

        return [(self.meridian, self.ex_meridian),
                (self.opp_meridian, self.opp_ex_meridian)]

    @staticmethod
    def acupoints_in_meridian(meridian):
        db = Database()
        acupoints = db.exec_script(f"""
        SELECT ID FROM Acupoint
        WHERE meridianID = "{meridian}";
        """)

        return [i[0] for i in acupoints]

    def treatment(self):
        ex_meridian = self.ex_meridian[0]
        opp_ex_meridian = self.opp_ex_meridian[0]
        bypass = self.bypass[ex_meridian]

        if ex_meridian in ["CV", "GV"]:
            jiaohuixue = [(pt, "++") for pt in bypass]
        else:
            jiaohuixue = [(pt, "--") for pt in bypass]

        target = (self.MASTER_PTS[ex_meridian], "++")
        complement_vessel = self.get_paired_elem(ex_meridian, self.PAIRS)
        complement = (self.MASTER_PTS[complement_vessel], "++")
        opposite = (self.MASTER_PTS[opp_ex_meridian], "--")
        opposite_complement_vessel = self.get_paired_elem(opp_ex_meridian, self.PAIRS)
        opposite_complement = (self.MASTER_PTS[opposite_complement_vessel], "--")

        return jiaohuixue, [target, complement, opposite, opposite_complement]


if __name__ == '__main__':

    ex = Extraordinary()
    ex.diagnose_deficiency("PC")
    print(ex.treatment())

    # print(ex.acupoints_in_meridian("CV"))

    # df_new = zero_pad_id(ex_df, "TV")
    # df_new = zero_pad_id(df_new, "YinLV")

    # build_ex_df()

    # print(id_to_meridian_name(None))