import numpy as np
import pandas as pd
from skyfield.api import load
from skyfield import almanac
from skyfield import almanac_east_asia as almanac_ea
from zoneinfo import ZoneInfo
from datetime import datetime
from diagnostics import solartime_by_ip
import sqlite3 as sql
from pathlib import Path
import os


DB_PATH = Path(os.path.abspath(__file__)).parents[0] / "acu.db"
SEASONS = ["春", "夏", "秋", "冬"]
SEASON_ENERGY = {
    "春": "木",
    "夏": "火",
    "秋": "金",
    "冬": "水",
}

tz = solartime_by_ip()[1]
tz = ZoneInfo(tz)


def update_solar_term_data():
    """Check whether solar term data in acu.db is up-to-date."""

    yr = datetime.now().year

    with sql.connect(DB_PATH) as conn:
        c = conn.cursor()

        c.execute("""
        SELECT date_utc FROM seasons WHERE solar_term = "春分";
        """)

        db_yr = c.fetchone()

    if yr != db_yr:
        build_season_data()


def load_solar_term_data():
    """Load solar term data from skyfield.
    This should be automatically updated once every calendar year."""

    ts = load.timescale()
    eph = load('de421.bsp')  # Covers 1900-2050; use de422 for Chinese History Project

    yr = datetime.now().year

    t0 = ts.utc(yr, 1, 1)
    t1 = ts.utc(yr, 12, 31)  # relative date one month from now
    t, tm = almanac.find_discrete(t0, t1, almanac_ea.solar_terms(eph))

    solar_term = []
    date = []
    for tmi, ti in zip(tm, t):
        solar_term.append(almanac_ea.SOLAR_TERMS_ZHT[tmi])
        date.append(ti.utc_datetime())

    solar_term_df = pd.DataFrame(list(zip(solar_term, date)), columns=["solar_term", "date_utc"])

    return solar_term_df


def season_solar_terms():
    jieqi_terms = almanac_ea.SOLAR_TERMS_ZHT[-3:] + almanac_ea.SOLAR_TERMS_ZHT[:-3]
    jieqi_season = [[season] * 6 for season in SEASONS]
    jieqi_season = [item for sublist in jieqi_season for item in sublist]

    terms_array = np.array(jieqi_terms)
    season_array = np.array(jieqi_season)

    return terms_array, season_array


def build_season_data():

    terms_array, season_array = season_solar_terms()
    season_energy = np.vectorize(SEASON_ENERGY.get)(list(season_array))
    season_change = np.where(season_array[:-1] != season_array[1:])[0]  # 大寒、穀雨、大暑、霜降。「立春」等前一個節氣，約換季前十八天。屬土，宜補脾。《素問·太陰陽明論》：“脾者土也，治中央，常以四時長四藏，各十八日寄治，不得獨主於時也。”

    if season_array[1] != season_array[-1]:
        earth_energy = np.append(season_change, 23)

    season_dict = {
        "solar_term": terms_array,
        "season": season_array,
        "long_summer": [True if term in ["大暑", "立秋", "處暑"] else False for term in terms_array],  # 夏末跨季一個月
        "energy_5elem": season_energy,
        "earth_energy": [True if term in terms_array[earth_energy] else False for term in terms_array],
    }  # merge long_summer and inter-season earth_energy to get best timing for treating the spleen.

    season_df = pd.DataFrame(season_dict)
    solar_term_df = load_solar_term_data()
    season_df = pd.merge(season_df, solar_term_df, on='solar_term', how='outer')

    with sql.connect(DB_PATH) as conn:
        season_df.to_sql("seasons", conn, if_exists='replace', index=False)

    return season_df


def current_season():
    """Return current season, the last solar term (節氣) and the present date."""

    with sql.connect(DB_PATH) as conn:
        c = conn.cursor()

        c.execute("""
        SELECT solar_term, season, date_utc FROM seasons;
        """)

        jieqi = c.fetchall()
        dates = [dt for tm, sn, dt in jieqi]

    current_date = datetime.now(tz)

    for i, dt in enumerate(dates):
        if i+1 <= len(dates):
            lower_bound = datetime.fromisoformat(dt)
            upper_bound = datetime.fromisoformat(dates[i+1])

            if lower_bound <= current_date < upper_bound:
                solar_term = jieqi[i][0]
                season = jieqi[i][1]

                return season, solar_term, current_date
        else:
            break


if __name__ == '__main__':

    update_solar_term_data()
    # print(current_season())
    # print(load_solar_term_data())
