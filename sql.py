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


def create_sql_level():
    conn = sqlite3.connect('stat.db')
    cursor = conn.cursor()
    cursor.execute("DROP TABLE IF EXISTS `level`")
    # 使用预处理语句创建表
    sql = """CREATE TABLE `level` (
            "viewer_id"	INTEGER NOT NULL UNIQUE,
            PRIMARY KEY("viewer_id")
            )"""
    cursor.execute(sql)
    print("CREATE TABLE level OK")
    cursor.close()
    conn.close()


def add_log_sql(data_dict, date, table_name):
    conn = sqlite3.connect('stat.db')
    cursor = conn.cursor()
    try:
        cursor.execute("ALTER TABLE '%s' ADD COLUMN '%s' INTEGER" % (table_name, date))
    except Exception:
        pass
    for account in data_dict.keys():
        if table_name != 'jewel' or data_dict[account] > 2000:
            cursor.execute("SELECT * FROM '%s' WHERE viewer_id = '%s'" % (table_name, account))
            if list(cursor):
                cursor.execute("UPDATE '%s' SET '%s' = '%s' WHERE viewer_id = '%s'" % (table_name, date, data_dict[account], account))
            else:
                cursor.execute("INSERT INTO '%s' ('viewer_id', '%s') VALUES ('%s', '%s')" % (table_name, date, account, data_dict[account]))
    conn.commit()
    cursor.close()
    conn.close()


def add_jewel_log(date, new=True):
    with open('log/' + date + '.txt', 'r', encoding='utf8') as f:
        lines = f.readlines()
    jewel_dict = {}
    id_list = []
    for line in lines:
        if new:
            search_id = re.search(r'账号(\d*)已进入小屋', line)
            if search_id:
                id = int(search_id.group(1))
                id_list.append(id)
        else:
            search_id = re.search(r'已登录账号(\d*)', line)
            if search_id:
                id = int(search_id.group(1))
                id_list.append(id)
            search_jewel_old = re.search(r'消耗钻(\d*)', line)
            if search_jewel_old:
                jewel = int(search_jewel_old.group(1))
                if id_list[-1] not in jewel_dict.keys():
                    jewel_dict[id_list[-1]] = jewel
                else:
                    jewel_dict[id_list[-1]] = max(jewel, jewel_dict[id_list[-1]])
        search_jewel = re.search(r'免费钻量(\d*)', line)
        if search_jewel:
            jewel = int(search_jewel.group(1))
            if id_list[-1] not in jewel_dict.keys():
                jewel_dict[id_list[-1]] = jewel
            else:
                jewel_dict[id_list[-1]] = max(jewel, jewel_dict[id_list[-1]])
    add_log_sql(jewel_dict, date, 'jewel')


def add_level_log(date):
    with open('log/' + date + '.txt', 'r', encoding='utf8') as f:
        lines = f.readlines()
    level_dict = {}
    id_list = []
    for line in lines:
        search_id = re.search(r'账号(\d*)已进入小屋', line)
        if search_id:
            id = int(search_id.group(1))
            id_list.append(id)
        else:
            search_id = re.search(r'已登录账号(\d*)', line)
            if search_id:
                id = int(search_id.group(1))
                id_list.append(id)
        search_level = re.search(r'账号等级为(\d*)', line)
        if search_level:
            level = int(search_level.group(1))
            if id_list[-1] not in level_dict.keys():
                level_dict[id_list[-1]] = level
            else:
                level_dict[id_list[-1]] = max(level, level_dict[id_list[-1]])
    add_log_sql(level_dict, date, 'level')


def add_list():
    for date in ['2023-01-29']:
        add_jewel_log(date)
        add_level_log(date)


if __name__ == '__main__':
    # create_sql_level()
    add_list()
