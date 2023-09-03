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
    # log = logger('farm-')
    try:
        all_account(BaseApi.gacha_select)
    except Exception as e:
        print(e)
        # log.exception(e)


# 检查农场号所在工会
def check_clan_all():
    async def check_farm():
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
        client = BaseApi(total["accounts"][0]["vid"], total["accounts"][0]["uid"], total['access_key'])
        await client.query(client.load_index)
        for clan in equip_account:
            members = await client.client.callapi('clan/others_info', {'clan_id': clan})
            mem_query = []
            for mem in members['clan']['members']:
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

    async def check_main():
        task_list = []
        task = asyncio.create_task(check_farm())
        task_list.append(task)
        await asyncio.gather(*task_list)
    asyncio.run(check_main())


# 检查装备号
def check_equip_all():
    async def check_equip():
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

        client = GonghuiApi(total["accounts"][0]["vid"], total["accounts"][0]["uid"], total['access_key'])
        await client.query(client.load_index)
        for account in total["accounts"]:
            res = await client.client.callapi('profile/get_profile', {'target_viewer_id': int(account["vid"])})
            if sum(res['quest_info']['normal_quest']) > 270:
                equip_a[account["clan_id"]].append(account["vid"])
                if account["clan_id"] and account["vid"] not in equip_account[account["clan_id"]]:
                    print(account["vid"])
            elif sum(res['quest_info']['normal_quest']) > 190:
                equip_b[account["clan_id"]].append(account["vid"])

        # 打印信息
        with open('./log/check.txt', 'a', encoding='utf-8') as f:
            for clan in equip_a.keys():
                f.write('工会'+str(clan)+'可用装备号'+str(len(equip_a[clan]))+'个, 包含'+str(equip_a[clan])+'\n')
            for clan in equip_b.keys():
                f.write('工会'+str(clan)+'备用装备号'+str(len(equip_b[clan]))+'个, 包含'+str(equip_b[clan])+'\n')

    async def check_main():
        task_list = []
        task = asyncio.create_task(check_equip())
        task_list.append(task)
        await asyncio.gather(*task_list)
    asyncio.run(check_main())


# 批量修改equip状态
def change_equip(equip_list):
    for i, account in enumerate(total["accounts"]):
        if account['vid'] in equip_list:
            total["accounts"][i]["equip"] = 1
        else:
            total["accounts"][i]["equip"] = 0
    save_total()


# 移动人员
def move_member(mem_list, clan_id):
    async def move_clan():
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
                client = GonghuiApi(clan['owner'])
                await client.query(client.load_index)
                mem_clan = clan_remove[clan['clan_id']]
                for mem in mem_clan:
                    msg = await client.remove_members(mem)
                    if msg:
                        total["accounts"][move_seq[mem]]["clan_id"] = 0
                        message += msg
        for move_mem in mem_list:
            client_mem = GonghuiApi(move_mem)
            await client_mem.query(client_mem.load_index)
            msg = await client_mem.join_clan(clan_id)
            if msg:
                total["accounts"][move_seq[move_mem]]["clan_id"] = clan_id
                message += msg

        save_total()
        print(message)
        with open('./log/total.txt', 'a', encoding='utf-8') as f:
            f.write(message)

    async def move_main():
        task_list = []
        task = asyncio.create_task(move_clan())
        task_list.append(task)
        await asyncio.gather(*task_list)
    asyncio.run(move_main())


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

def check_equip_stock():
    log = logger('equip')
    try:
        all_account(BaseApi.check_equip_num)
    except Exception as e:
        print(e)
        log.exception(e)



if __name__ == '__main__':
    check_equip_stock()
