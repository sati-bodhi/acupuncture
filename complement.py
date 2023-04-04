import pandas as pd
import numpy as np
from acupuncture.db import Database
from acupuncture.lookup import Calc as calc


class GroupLuo:

    POINTS = (("PC5", "TE8"), ("SP6", "GB39"))
    LEFT_RIGHT = ("l", "r")
    YINYANG = (0, 1)
    TOP_BOTTOM = ("t", "b")

    def __init__(self, left_right, top_bottom=None, nature=None, hemiplegia=False):

        self.prescribe = None
        self.pos_lr = left_right  # "l" or "r"
        self.opp_pos_lr = calc.paired_with(self.pos_lr, self.LEFT_RIGHT)

        self.points_yin = [yin for yin, yang in self.POINTS]
        self.points_yang = [yang for yin, yang in self.POINTS]

        if hemiplegia:
            self.nature = 0 if nature == "atonic" else 1 if nature == "spastic" else None

        else:

            self.nature = nature  # 0 or 1, representing yin or yang.
            self.opp_nature = calc.paired_with(self.nature, self.YINYANG)

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


if __name__ == '__main__':
    pass
    # gl = GroupLuo("r", nature="atonic", hemiplegia=True)
    # print(gl.hemiplegia())
