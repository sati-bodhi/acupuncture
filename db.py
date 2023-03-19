from pathlib import Path
import os
import sqlite3 as sql

DB_PATH = Path(os.path.abspath(__file__)).parents[0] / "acu.db"


class Database:
    def __init__(self):
        self.DB_PATH = None
        self.result = None

    def exec_script(self, script, fetch_result=True, fetch_one=False):
        with sql.connect(DB_PATH) as conn:
            c = conn.cursor()

            c.execute(script)

            if fetch_result:
                if fetch_one:
                    self.result = c.fetchone()
                    return self.result
                else:
                    self.result = c.fetchall()
                    return self.result
            else:
                return


    @staticmethod
    def df_to_sql(df):
        with sql.connect(DB_PATH) as conn:
            df.to_sql("seasons", conn, if_exists='replace', index=False)

