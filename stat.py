import sqlite3
import time
import re


# 创建 TABLE
def create_sql_jewel():
    conn = sqlite3.connect('stat.db')
    cursor = conn.cursor()
    cursor.execute("DROP TABLE IF EXISTS `jewel`")
    # 使用预处理语句创建表
    sql = """CREATE TABLE `jewel` (
            "viewer_id"	INTEGER NOT NULL UNIQUE,
            PRIMARY KEY("viewer_id")
            )"""
    cursor.execute(sql)
    print("CREATE TABLE jewel OK")
    cursor.close()
    conn.close()


def add_jewel_log():
    with open('log/2021-10-22.log', 'r', encoding='utf8') as f:
        lines = f.readlines()
    jewel_dict = {}
    for line in lines:
        
    print(data)
    

if __name__ == '__main__':
    add_jewel_log()
