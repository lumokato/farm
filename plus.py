"""
一些一次性任务实现
"""
from api.baseapi import BaseApi, all_account
from api.friendapi import FriendApi
from api.gonghuiapi import GonghuiApi
from log import logger
from json import load, dump
from os.path import exists
from api.satrokiapi import WebClient
import asyncio
import time


if exists('account.json'):
    with open('account.json', encoding='utf-8') as fp:
        total = load(fp)

if exists('friend.json'):
    with open('friend.json', encoding='utf-8') as fp:
        friend = load(fp)

if exists('bind.json'):
    with open('bind.json', encoding='utf-8') as fp:
        bind = load(fp)


def save_friend():
    global friend
    with open('friend.json', 'w', encoding='utf-8') as fp:
        dump(friend, fp, indent=4, ensure_ascii=False)


def save_bind():
    global bind
    with open('bind.json', 'w', encoding='utf-8') as fp:
        dump(bind, fp, indent=4, ensure_ascii=False)


def save_total():
    global total
    with open('account.json', 'w', encoding='utf-8') as fp:
        dump(total, fp, indent=4, ensure_ascii=False)


# 免费十连批量选择附奖
def prize_gacha():
    log = logger('farm-')
    try:
        all_account(BaseApi.gacha_select)
    except Exception as e:
        log.exception(e)



# 检查农场号所在工会
def check_clan_all():
    equip_account = {}
    farm_account = {}
    for clan in total["clan"]:
        equip_account[clan["clan_id"]] = []
        farm_account[clan["clan_id"]] = []
    for account in total["accounts"]:
        if account["equip"]:
            equip_account[account["clan_id"]].append(account["vid"])
        elif account["clan_id"]:
            farm_account[account["clan_id"]].append(account["vid"])
    # 检查clanid错误
    App = GonghuiApi(total["accounts"][0]["vid"], total["accounts"][0]["uid"], total['access_key'])
    for clan in equip_account:
        members = App.client.callapi('clan/others_info', {'clan_id': clan})['clan']['members']
        mem_query = []
        for mem in members:
            mem_query.append(mem['viewer_id'])
        for member in equip_account[clan]:
            if member not in mem_query:
                print(member, clan)
        for member in farm_account[clan]:
            if member not in mem_query:
                print(member, clan)
    # 打印信息
    with open('./log/check.txt', 'a', encoding='utf-8') as f:
        for clan in equip_account.keys():
            f.write('工会'+str(clan)+'装备号'+str(len(equip_account[clan]))+'个, 包含'+str(equip_account[clan])+'\n')
        for clan in farm_account.keys():
            f.write('工会'+str(clan)+'农场号'+str(len(farm_account[clan]))+'个, 包含'+str(farm_account[clan])+'\n')


# 检查装备号
def check_equip():
    equip_a = {0: []}
    equip_b = {0: []}
    for clan in total["clan"]:
        equip_a[clan["clan_id"]] = []
        equip_b[clan["clan_id"]] = []
    equip_account = {}
    for clan in total["clan"]:
        equip_account[clan["clan_id"]] = []
    for account in total["accounts"]:
        if account["equip"]:
            equip_account[account["clan_id"]].append(account["vid"])
    App = GonghuiApi(total["accounts"][0]["vid"], total["accounts"][0]["uid"], total['access_key'])
    for account in total["accounts"]:
        res = App.client.callapi('profile/get_profile', {'target_viewer_id': int(account["vid"])})
        if sum(res['quest_info']['normal_quest']) > 270:
            equip_a[account["clan_id"]].append(account["vid"])
            if account["clan_id"] and account["vid"] not in equip_account[account["clan_id"]]:
                print(account["vid"])
        elif sum(res['quest_info']['normal_quest']) > 190:
            equip_b[account["clan_id"]].append(account["vid"])
    # for clan in equip_account:
    #     members = App.client.callapi('clan/others_info', {'clan_id': clan})['clan']['members']
    #     mem_query = []
    #     for mem in members:
    #         mem_query.append(mem['viewer_id'])
    #     for member in equip_account[clan]:
    #         if member not in mem_query:
    #             print(member, clan)
    #     for member in farm_account[clan]:
    #         if member not in mem_query:
    #             print(member, clan)
    # 打印信息
    with open('./log/check.txt', 'a', encoding='utf-8') as f:
        for clan in equip_a.keys():
            f.write('工会'+str(clan)+'可用装备号'+str(len(equip_a[clan]))+'个, 包含'+str(equip_a[clan])+'\n')
        for clan in equip_b.keys():
            f.write('工会'+str(clan)+'备用装备号'+str(len(equip_b[clan]))+'个, 包含'+str(equip_b[clan])+'\n')


# 批量修改equip状态
def change_equip(equip_list):
    for i, account in enumerate(total["accounts"]):
        if account['vid'] in equip_list:
            total["accounts"][i]["equip"] = 1
        else:
            total["accounts"][i]["equip"] = 0
    save_total()


# 移动人员
def move_member(mem_list, move_clan):
    message = ''
    move_seq = {}
    clan_remove = {}
    for i, account in enumerate(total["accounts"]):
        if account['vid'] in mem_list:
            move_seq[account['vid']] = i
            if account['clan_id'] not in clan_remove.keys():
                clan_remove[account['clan_id']] = [account['vid']]
            else:
                clan_remove[account['clan_id']].append(account['vid'])

    for clan in total['clan']:
        if clan['clan_id'] in clan_remove.keys() and clan['clan_id']:
            App = GonghuiApi(clan['owner'])
            mem_clan = clan_remove[clan['clan_id']]
            for mem in mem_clan:
                msg = App.remove_members(mem)
                if msg:
                    total["accounts"][move_seq[mem]]["clan_id"] = 0
                    message += msg
    for move_mem in mem_list:
        App = GonghuiApi(move_mem)
        msg = App.join_clan(move_clan)
        if msg:
            total["accounts"][move_seq[move_mem]]["clan_id"] = move_clan
            message += msg
    save_total()
    print(message)
    with open('./log/total.txt', 'a', encoding='utf-8') as f:
        f.write(message)


# 检查所有账号场次
def check_group():
    App = GonghuiApi(total["accounts"][0]['vid'])
    arena_dict = {}
    grand_dict = {}
    for account in total["accounts"]:
        res = App.client.callapi('profile/get_profile', {'target_viewer_id': int(account['vid'])})
        arena = res['user_info']['arena_group']
        grand = res['user_info']['grand_arena_group']
        if arena not in arena_dict.keys():
            arena_dict[arena] = [account['vid']]
        else:
            arena_dict[arena].append(account['vid'])
        if grand not in grand_dict.keys():
            grand_dict[grand] = [account['vid']]
        else:
            grand_dict[grand].append(account['vid'])
    with open('group.json', 'w', encoding='utf-8') as fp:
        dump(arena, fp, indent=4, ensure_ascii=False)
    with open('group.json', 'a', encoding='utf-8') as fp:
        dump(grand, fp, indent=4, ensure_ascii=False)
    grand_account = {}
    for grand in grand_dict.keys():
        if grand > 0:
            for account in total["accounts"]:
                if account['vid'] == grand_dict[grand][0]:
                    grand_account[grand] = {
                        "viewer_id": account['vid'],
                        "uid": account['uid']
                        }
    with open('grand_account.json', 'w', encoding='utf-8') as fp:
        dump(grand_account, fp, indent=4, ensure_ascii=False)


def change_unit_name():
    with open('unit_id.json', encoding='utf-8') as fp:
        unit = load(fp)
    web = WebClient()
    for unit_id in unit.keys():
        unit_name = web.get_unit_name(int(unit_id))
        if unit_name != unit[unit_id]:
            unit[unit_id] = unit_name

    with open('unit_id_new.json', 'w', encoding='utf-8') as fp:
        dump(unit, fp, indent=4, ensure_ascii=False)


if __name__ == '__main__':
    change_unit_name()
