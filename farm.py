from apscheduler.schedulers.background import BlockingScheduler
import time
import random
from api.gonghuiapi import GonghuiApi
from api.shuatuapi import ShuatuApi
from api.zhuangbeiapi import ZhuangbeiApi
import api.bilievent as bilievent
from log import logger
from json import load, dump
from os.path import exists
import datetime
from wechat import send_wechat
import calendar
import asyncio


if exists('account.json'):
    with open('account.json', encoding='utf-8') as fp:
        total = load(fp)

if exists('bind.json'):
    with open('bind.json', encoding='utf-8') as fp:
        bind = load(fp)

with open('equip_id.json', encoding='utf-8') as fp:
    equip_id = load(fp)

account_finish = {}


def save_total():
    global total
    with open('account.json', 'w', encoding='utf-8') as fp:
        dump(total, fp, indent=4, ensure_ascii=False)


def save_bind():
    global bind
    with open('bind.json', 'w', encoding='utf-8') as fp:
        dump(bind, fp, indent=4, ensure_ascii=False)


async def equip_donate(clan, sem):
    async with sem:
        if clan['equip'] == 1:
            donate_account = {}
            for i, account in enumerate(total["accounts"]):
                if account['clan_id'] == clan['clan_id'] and account['equip'] == 1:
                    donate_account[i] = account['today_donate']
            # 随机选取一个账号检测是否需要捐赠
            check_account = total["accounts"][random.choice(list(donate_account.keys()))]
            client = ZhuangbeiApi(check_account['vid'], check_account['uid'], total['access_key'])
            donate_list = await client.donate_check(bind)
            for donate in donate_list:
                for account in sorted(donate_account.items(), key=lambda x: x[1]):
                    client = ZhuangbeiApi(total["accounts"][account[0]]['vid'], total["accounts"][account[0]]['uid'], total['access_key'])
                    msg = await client.donate_message(donate[1])
                    if not msg:
                        break
                    donate_continue, donation_num = msg
                    total["accounts"][account[0]]['today_donate'] = donation_num
                    donate_account[account[0]] = donation_num
                    if not donate_continue:
                        break
                donate_name = bind['users'][str(donate[0])]
                item_id_str = str(donate[2])
                if len(item_id_str) == 6:
                    item_id_str_full = item_id_str[:1] + '0' + item_id_str[2:]
                if item_id_str_full in equip_id:
                    equip_name = equip_id[item_id_str_full]
                else:
                    equip_name = item_id_str_full
                print('已向 ' + donate_name + ' 捐赠装备 ' + equip_name)


# 每小时捐赠装备
def do_equip_cron():
    log = logger('equip')
    try:
        async def equip_main():
            task_list = []
            sem = asyncio.Semaphore(4)
            for clan in total['clan']:
                task = asyncio.create_task(equip_donate(clan, sem))
                task_list.append(task)
            await asyncio.gather(*task_list)

        asyncio.run(equip_main())
        save_total()
    except Exception as e:
        log.exception(e)


# 账号日常
async def daily_matters(index, vid, sem):
    async with sem:
        log = logger('farm')
        try:
            n_event = total['N_event']
            client = ShuatuApi(vid)
            await client.query(client.room)
            # 地下城捐赠
            if not bilievent.load_battle_cn():
                for i, clan in enumerate(bind['clan']):
                    if clan['clan_id'] == client.clan_id and clan['donate_user']:
                        dun = await client.query(client.dungeon, clan['donate_user'])
                        if dun > 0:
                            bind['clan'][i]['donate_times'] += 1
            await client.query(client.mission)  # 收取任务
            await client.shuatu_daily(n_event, total['max_level'])  # 刷图
            await client.query(client.present)   # 收取礼物
            if datetime.datetime.now().weekday() == 0:
                await client.arena_reward()  # 收取双场币
                # App.shop_item()  # 商店购买
            await client.query(client.gacha)     # 扭蛋
            # await client.query(client.alchemy)   # 购买扫荡券
            await client.query(client.training_skip)     # 探索本
            await client.query(client.mission)  # 收取任务
            # 如果收取任务时升级，再次执行刷图函数
            await client.load_index(requery=True)
            if client.user_stamina > 80:
                await client.shuatu_daily(n_event, total['max_level'])
            # 女神祭
            await client.season_ticket()
            await client.season_ticket_reward()

            global account_finish
            account_finish[index] = 1
            return True
        except Exception as e:
            # print(e)
            log.exception(e)
            await asyncio.sleep(5)
            return False


def change_n_event():
    now_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    n_event = bilievent.load_event_bilibili(datetime.datetime.strptime(now_time, "%Y-%m-%d %H:%M:%S"))
    total['N_event'] = n_event
    save_total()


def do_farm_cron():
    start_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    change_n_event()
    global account_finish
    account_finish = {}

    async def farm_daily(farm_list):
        task_list = []
        sem = asyncio.Semaphore(8)
        for index in farm_list:
            task = asyncio.create_task(daily_matters(index, total["accounts"][index]["vid"], sem))
            task_list.append(task)
        await asyncio.gather(*task_list)

    # first routine
    farm_index = list(range(len(total["accounts"])))
    asyncio.run(farm_daily(farm_index))
    first_count = sum(account_finish.values())

    # second routine
    second_list = []
    print(second_list)
    for i in farm_index:
        if i not in account_finish.keys():
            second_list.append(i)
    asyncio.run(farm_daily(second_list))
    second_count = sum(account_finish.values())
    end_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    save_bind()

    fail_account = []
    for j in farm_index:
        if j not in account_finish.keys():
            fail_account.append(total["accounts"][j]["vid"])

    with open('./log/total.txt', 'a', encoding='utf-8') as f:
        f.write('本次共成功处理'+str(second_count)+'个账号, 后续补充处理'+str(second_count - first_count)+'个账号, 开始时间为'+start_time+', 结束时间为'+end_time+'\n')
        if fail_account:
            f.write('未成功处理账号为'+str(fail_account))


# 每日0点次数清零
def clear_daily():
    message = '\n**********每日简报**********\n'
    with open('account.json', encoding='utf-8') as fp:
        msg_total = load(fp)
    for i, clan in enumerate(msg_total['clan']):
        if clan['equip'] == 1:
            clan_donate_num = []
            for account in msg_total['accounts']:
                if account['clan_id'] == clan['clan_id'] and account['equip'] == 1:
                    clan_donate_num.append(account['today_donate'])
            message += '公会' + str(i+1) + '捐赠装备' + str(clan_donate_num)[1:-1].replace(' ', '') + '个\n'

    with open('bind.json', encoding='utf-8') as fp:
        msg_bind = load(fp)
    for i, clan in enumerate(msg_bind['clan']):
        if clan['donate_user']:
            message += '公会' + str(i+1) + '捐赠玛娜' + str(clan['donate_times']) + '次\n'
    message += '***************************\n'
    send_wechat(message)
    with open('./log/total.txt', 'a', encoding='utf-8') as f:
        f.write(message)
    for account in total['accounts']:
        account['today_donate'] = 0
    save_total()
    for clan in bind['clan']:
        clan['donate_times'] = 0
    save_bind()


async def remove_user(clan, seq, sem):
    async with sem:
        message = "移除人员:\n"
        client = GonghuiApi(clan['owner'])
        await client.query(client.load_index)
        mem_clan = await client.check_members()
        mem_farm = []
        for account in total['accounts']:
            if account['clan_id'] == client.clan_id:
                mem_farm.append(account['vid'])
        if seq == 'after':
            for account in list(bind['users'].keys()):
                mem_farm.append(int(account))
        for mem in mem_clan:
            if mem not in mem_farm:
                print(mem)
                msg = await client.remove_members(mem)
                message += msg
        send_wechat(message)


# 移除人员
def refresh_clan(seq='before'):
    # send_wechat('开始移除流程')
    try:
        async def refresh_main():
            task_list = []
            sem = asyncio.Semaphore(4)
            for clan in total['clan']:
                task = asyncio.create_task(remove_user(clan, seq, sem))
                task_list.append(task)
            await asyncio.gather(*task_list)
        asyncio.run(refresh_main())
    except Exception:
        pass


# 会战前移除过程
def battle_remove(scheduler_func):
    today = datetime.datetime.today()
    monthdays = calendar.monthrange(today.year, today.month)
    clan_time_list = bilievent.time_battle_cn(datetime.datetime.now())
    if not clan_time_list:
        clan_time = datetime.datetime(today.year, today.month, monthdays[1]-5, 5, 0)
    else:
        clan_time = clan_time_list[0]
    send_wechat('将于'+str(clan_time-datetime.timedelta(hours=11))+'移除农场人员')
    scheduler_func.add_job(refresh_clan, 'date', run_date=clan_time - datetime.timedelta(hours=11), args=['before'])


async def main_matters():
    log = logger('main')
    try:
        with open('account.json', encoding='utf-8') as fp:
            main_user = load(fp)["main"]
        client = ShuatuApi(main_user["vid"], main_user["uid"])
        time_now = datetime.datetime.now()
        if time_now.hour == 11:
            await asyncio.sleep(20+time_now.day*60)
            await client.query(client.gacha)
            print(await client.clan_equip_donation())
            print(await client.random_like())
            print(await client.buy_dungeon_shop())
            print(await client.buy_jjc_shop())
            print(await client.buy_pjjc_shop())
            await client.sweep_explore_exp()
            await client.sweep_explore_mana()
            print(await client.dungeon_sweep("max"))
            # 每月前半
            if time_now.day < 13:
                await client.query(client.room)
                await client.event_hard_sweep('new')
                await client.star6_sweep(13030001)
        elif time_now.hour == 19:
            await asyncio.sleep(40+time_now.day*60)
            await client.query(client.gacha)
            print(await client.clan_equip_donation())
            await client.season_ticket()
            # if time_now.day > 12:
            #     await client.query(client.room)
        else:
            await asyncio.sleep(time_now.day*60)
            print(await client.query(client.clan_equip_donation))
            await client.query(client.mission)
    except Exception as e:
        log.exception(e)
        return False


def do_main_cron():
    log = logger('main')
    try:
        async def q_main():
            task_list = []
            task = asyncio.create_task(main_matters())
            task_list.append(task)
            await asyncio.gather(*task_list)
        asyncio.run(q_main())
        save_total()
    except Exception as e:
        log.exception(e)


if __name__ == "__main__":
    scheduler = BlockingScheduler(timezone="Asia/Shanghai", job_defaults={'max_instances': 5})
    scheduler.add_job(do_equip_cron, 'cron', minute='20')
    scheduler.add_job(do_farm_cron, 'cron', hour='6,18', minute='30')
    scheduler.add_job(do_main_cron, 'cron', hour='3,11,19', minute='5')
    scheduler.add_job(clear_daily, 'cron', hour='0', minute='5')
    scheduler.add_job(battle_remove, 'cron', day='22', hour='0', args=[scheduler])
    if 21 < datetime.datetime.today().day < 26:
        battle_remove(scheduler)
    scheduler.add_job(refresh_clan, 'cron', day='last', hour='0, 2, 6, 9', minute='1', args=['after'])
    scheduler.add_job(do_farm_cron, 'cron', day='last', hour='3', minute='25')
    scheduler.start()
