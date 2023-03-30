from acupuncture.db import Database
import numpy as np
import pandas as pd


def acu_ex_table_as_df():

    db = Database()

    acu_ex = db.exec_script("""
    SELECT * FROM acuEx;
    """)

    ex_df = pd.DataFrame(acu_ex, columns=['ID', 'bypass', 'meridianID'])

    return ex_df


def zero_pad_id(df, meridian_id):

    id_array = df.loc[df["meridianID"] == meridian_id, "ID"]
    arr = np.array(id_array)
    arr = np.array(id_array.str.replace(meridian_id, ""))
    arr = arr.astype(np.int64) + 1
    arr = np.char.mod('%02d', arr)
    df.loc[df["meridianID"] == meridian_id, "ID"] = np.char.add(np.array([meridian_id] * len(arr)), arr)

    return df


def bypass_as_list(meridian_id):
    bp_arr = ex_df.loc[ex_df["meridianID"] == meridian_id, "bypass"]
    bp_arr = list(bp_arr)

    return bp_arr


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

bypass_lst = [tv, bv, yinlv, yanglv, yinhv, yanghv]
ex_id = ["TV", "BV", "YinLV", "YangLV", "YinHV", "YangHV"]


def generate_accom_data(ex_lst, ex_meridian):
    meridian_id = np.array([ex_meridian] * len(ex_lst))
    acu_ex_id = list(range(1, len(ex_lst) + 1))
    acu_ex_id = [str(n).zfill(2) for n in acu_ex_id]
    acu_ex_id = np.array(acu_ex_id)
    acu_ex_id = np.char.add(meridian_id, acu_ex_id)

    return acu_ex_id, meridian_id


def build_ex_df_dict():
    all_idx = []
    all_bypass = []
    all_mer = []

    for i, m in enumerate(bypass_lst):
        idx, mer = generate_accom_data(m, ex_id[i])
        all_idx += list(idx)
        all_mer += list(mer)

    ex_df_dict = {
        "ID": all_idx,
        "bypass": [item for sublist in bypass_lst for item in sublist],
        "meridianID": all_mer,
    }

    return ex_df_dict


def build_ex_df():

    df = pd.DataFrame(build_ex_df_dict())

    db = Database()
    db.df_to_sql(df, "acuEx")


# TODO: Update acupoint query with bypass info.

# df_new = zero_pad_id(ex_df, "TV")
# df_new = zero_pad_id(df_new, "YinLV")

build_ex_df()
