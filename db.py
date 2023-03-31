from pathlib import Path
import os
import sqlite3 as sql
import pandas as pd

DB_PATH = Path(os.path.abspath(__file__)).parents[0] / "acu.db"


class Database:
    def __init__(self):
        self.df = None
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
    def df_to_sql(df, table):
        with sql.connect(DB_PATH) as conn:
            df.to_sql(table, conn, if_exists='replace', index=False)

    def table_as_df(self, table):

        db = Database()

        columns = db.exec_script(f"""
        SELECT name FROM PRAGMA_TABLE_INFO("{table}");
        """)

        columns = [n[0] for n in columns]

        data = db.exec_script(f"""
        SELECT * FROM {table};
        """)

        self.df = pd.DataFrame(data, columns=columns)

        return self.df


if __name__ == '__main__':
    pass

    # db = Database()
    # print(db.table_as_df("horary"))
