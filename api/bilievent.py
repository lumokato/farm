import urllib.request
import json
import datetime
# from os import truncate
import re
import ast
from html.parser import HTMLParser


keyword_list = [
    'year',
    'month',
    'day',
    'qdhd',  # 庆典活动
    'tdz',  # 团队战
    'tbhd',  # 特别活动
    'jqhd',  # 剧情活动
    'jssr',  # 角色生日
]

event_keyword_list = [
    'qdhd',  # 庆典活动 04:59
    'tbhd',  # 特别活动 23:59
    'jqhd',  # 剧情活动 23:59
    'tdz',  # 团队战 23:59
]


class ContentParse(HTMLParser):
    def __init__(self):
        HTMLParser.__init__(self)
        self.data = []
        self.is_title = False

    def handle_starttag(self, tag, attrs):
        try:
            if 'cl-t' in attrs[0]:
                self.is_title = True
            else:
                self.is_title = False
        except Exception:
            self.is_title = False

    def handle_data(self, data):
        if self.is_title:
            self.data.append(data)


def parse_content(day_content):
    content_html = ''
    data = {}
    for keyword in event_keyword_list:
        content_html = day_content[keyword]
        parser = ContentParse()
        parser.feed(content_html)
        data[keyword] = parser.data
    return data


def extract_calendar_data(js_text):
    # 提取js的data部分转换为python对象
    data_str = re.search(r'\[.*?\]', js_text, re.S).group(0)
    for keyword in keyword_list:
        data_str = data_str.replace(keyword, f'"{keyword}"')
        data_str = data_str.replace('//', '')
    data = ast.literal_eval(data_str)
    # 解析活动内容html
    for i in range(len(data)):
        for day in data[i]['day']:
            content = parse_content(data[i]['day'][day])
            data[i]['day'][day] = content
    return data


def transform_calendar_data(data):
    event_cache = {}
    event_list = []
    for i in range(len(data)):
        for day_str in data[i]['day']:
            # print(data[i]['year'], data[i]['month'], day_str, data[i]['day'][day_str])
            # 遍历本日活动
            year = int(data[i]['year'])
            month = int(data[i]['month'])
            day = int(day_str)
            for keyword in event_keyword_list:
                end_time = '23:59'
                if keyword == 'qdhd':
                    end_time = '04:59'
                for event_name in data[i]['day'][day_str][keyword]:
                    if event_name not in event_cache.keys():
                        # event_cache[event_name] = {'year': year, 'month': month, 'day': int(day)}
                        event_cache[event_name] = {
                            'start_year': year,
                            'start_month': month,
                            'start_day': day,
                            'end_year': year,
                            'end_month': month,
                            'end_day': day,
                            'end_time': end_time,
                        }
            for event_name in list(event_cache.keys()):
                is_active = False
                for keyword in event_keyword_list:
                    if event_name in data[i]['day'][day_str][keyword]:
                        is_active = True
                if is_active:
                    event_cache[event_name]['end_year'] = year
                    event_cache[event_name]['end_month'] = month
                    event_cache[event_name]['end_day'] = day
                else:
                    event_list.append({
                        'title': event_name,
                        'start': f'{event_cache[event_name]["start_year"]}/{event_cache[event_name]["start_month"]}/{event_cache[event_name]["start_day"]} 05:00',
                        'end': f'{event_cache[event_name]["end_year"]}/{event_cache[event_name]["end_month"]}/{event_cache[event_name]["end_day"]} {event_cache[event_name]["end_time"]}',
                    })
                    event_cache.pop(event_name)
    return event_list


def transform_bilibili_calendar(data):
    data = extract_calendar_data(data)
    data = transform_calendar_data(data)
    return data


def get_record(url):
    resp = urllib.request.urlopen(url)
    return resp.read().decode('utf-8')


def load_event_bilibili(nowtime=datetime.datetime.now()):
    data = ''

    data = get_record('https://static.biligame.com/pcr/gw/calendar.js')

    data = transform_bilibili_calendar(data)
    # print(nowtime)
    if data:
        for item in data:
            start_time = datetime.datetime.strptime(
                item['start'], r"%Y/%m/%d %H:%M")
            end_time = datetime.datetime.strptime(
                item['end'], r"%Y/%m/%d %H:%M")
            if nowtime < end_time and nowtime > start_time and '普通关卡' in item['title']:
                print(item['title'])
                if '3倍' in item['title']:
                    return 3
                else:
                    return 2
    return 0


def load_battle_bilibili(nowtime=datetime.datetime.now()):
    data = ''

    data = get_record('https://static.biligame.com/pcr/gw/calendar.js')

    data = transform_bilibili_calendar(data)
    # print(nowtime)
    if data:
        for item in data:
            start_time = datetime.datetime.strptime(
                item['start'], r"%Y/%m/%d %H:%M")
            end_time = datetime.datetime.strptime(
                item['end'], r"%Y/%m/%d %H:%M")
            if nowtime < end_time and nowtime > start_time and '期' in item['title'] and '团队战' in item['title']:
                print(item['title'])
                return True
    return False


def time_battle_bilibili(nowtime=datetime.datetime.now()):
    data = ''

    data = get_record('https://static.biligame.com/pcr/gw/calendar.js')

    data = transform_bilibili_calendar(data)
    # print(nowtime)
    if data:
        for item in data:
            start_time = datetime.datetime.strptime(
                item['start'], r"%Y/%m/%d %H:%M")
            end_time = datetime.datetime.strptime(
                item['end'], r"%Y/%m/%d %H:%M")
            if nowtime < end_time and nowtime - start_time < datetime.timedelta(30) and '期' in item['title'] and '团队战' in item['title']:
                return start_time, end_time
    return False


def load_event_cn(nowtime=datetime.datetime.now()):

    data = json.loads(get_record('https://pcrbot.github.io/calendar-updater-action/cn.json'))

    if data:
        for item in data:
            start_time = datetime.datetime.strptime(item['start_time'], "%Y/%m/%d %H:%M:%S")
            end_time = datetime.datetime.strptime(item['end_time'], "%Y/%m/%d %H:%M:%S")
            if nowtime < end_time and nowtime > start_time and 'N图' in item['name']:
                print(item['name'])
                if '3' in item['name']:
                    return 3
                else:
                    return 2
    return 0


def load_battle_cn(nowtime=datetime.datetime.now()):

    data = json.loads(get_record('https://pcrbot.github.io/calendar-updater-action/cn.json'))

    if data:
        for item in data:
            start_time = datetime.datetime.strptime(item['start_time'], "%Y/%m/%d %H:%M:%S")
            end_time = datetime.datetime.strptime(item['end_time'], "%Y/%m/%d %H:%M:%S")
            if nowtime < end_time and nowtime > start_time and '公会战' in item['name']:
                # print(item['name'])
                return start_time, end_time
    return False


def time_battle_cn(nowtime=datetime.datetime.now()):

    data = json.loads(get_record('https://pcrbot.github.io/calendar-updater-action/cn.json'))

    if data:
        for item in data:
            start_time = datetime.datetime.strptime(item['start_time'], "%Y/%m/%d %H:%M:%S")
            end_time = datetime.datetime.strptime(item['end_time'], "%Y/%m/%d %H:%M:%S")
            if nowtime < end_time and nowtime - start_time < datetime.timedelta(30) and '公会战' in item['name']:
                # print(item)
                return start_time, end_time
    return False


if __name__ == '__main__':
    print(load_event_cn(datetime.datetime.now()))
