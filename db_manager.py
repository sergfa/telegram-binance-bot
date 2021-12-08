import sqlite3
import atexit

sql_create_jobs_table = """ CREATE TABLE IF NOT EXISTS jobs (
                                        id integer PRIMARY KEY AUTOINCREMENT,
                                        chat_id text NOT NULL,
                                        ticker text NOT NULL
                                    ); """
class DbManager:
    db_file = None
    
    def __init__(self, db_file):
      self.db_file = db_file
      self.create_table(sql_create_jobs_table)
    
    
    def create_table(self, create_table_sql):
        con = sqlite3.connect(self.db_file)  
        cursor = con.cursor()
        cursor.execute(create_table_sql)
        con.commit()
        con.close()

    def insertJob(self, chat_id, ticker) -> None:
        con =sqlite3.connect(self.db_file)  
        cursor = con.cursor()
        cursor.execute("INSERT INTO jobs VALUES (?,?,?)", (None,chat_id, ticker))
        con.commit()
        con.close()  

    def deleteJob(self, chat_id, ticker) -> None:
        con = sqlite3.connect(self.db_file)  
        cursor = con.cursor()
        cursor.execute("DELETE FROM jobs WHERE chat_id=? AND ticker=?", (chat_id, ticker))
        con.commit()
        con.close()

    def getJobs(self):
        con = sqlite3.connect(self.db_file)
        cursor = con.cursor()
        cursor.execute("SELECT * from jobs")
        rows = cursor.fetchall()
        con.close()
        return rows


if __name__ == '__main__':
    db = DbManager('test.db')
    db.insertJob("chat1", "BTCUSDT")
    db.insertJob("chat2", "DOGE")
    db.insertJob("chat3", "ETH")
    rows = db.getJobs()
    for row in rows:
        print(row)
    db.deleteJob("chat1", "BTCUSDT")    
    print("job deleted")
    rows = db.getJobs()
    for row in rows:
        print(row)