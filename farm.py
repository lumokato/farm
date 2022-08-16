from apscheduler.schedulers.background import BlockingScheduler
import time
import random
from api.gonghuiapi import GonghuiApi
from api.shuatuapi import ShatuApi
from api.zhuangbeiapi import ZhuangbeiApi
import api.bilievent as bilievent
from log import logger
from json import load, dump
from os.path import exists
import datetime
from wechat import send_wechat


if exists('account.json'):
    with open('account.json', encoding='utf-8') as fp:
        total = load(fp)

if exists('bind.json'):
    with open('bind.json', encoding='utf-8') as fp:
        bind = load(fp)

with open('equip_id.json', encoding='utf-8') as fp:
    equip_id = load(fp)


def save_total():
    global total
    with open('account.json', 'w', encoding='utf-8') as fp:
        dump(total, fp, indent=4, ensure_ascii=False)


def save_bind():
    global bind
    with open('bind.json', 'w', encoding='utf-8') as fp:
        dump(bind, fp, indent=4, ensure_ascii=False)


# 每小时捐赠装备
def equip_donate():
    log = logger('equip')
    try:
        for clan in total['clan']:
            if clan['equip'] == 1:
                donate_account = {}
                for i, account in enumerate(total["accounts"]):
                    if account['clan_id'] == clan['clan_id'] and account['equip'] == 1:
                        donate_account[i] = account['today_donate']
                # 随机选取一个账号检测是否需要捐赠
                check_account = total["accounts"][random.choice(list(donate_account.keys()))]
                App = ZhuangbeiApi(
                    check_account['vid'], check_account['uid'], total['access_key'])
                App.load_index()
                donate_list = App.donate_check(bind)
                for donate in donate_list:
                    for account in sorted(donate_account.items(), key=lambda x: x[1]):
                        App = ZhuangbeiApi(
                            total["accounts"][account[0]]['vid'], total["accounts"][account[0]]['uid'], total['access_key'])
                        App.load_index()
                        donate_continue, donation_num = App.donate_message(
                            donate[1])
                        total["accounts"][account[0]]['today_donate'] = donation_num
                        donate_account[account[0]] = donation_num
                        if not donate_continue:
                            break
                    donate_name = bind['users'][str(donate[0])]
                    if str(donate[2]) in equip_id:
                        equip_name = equip_id[str(donate[2])]
                    else:
                        equip_name = str(donate[2])
                    print('已向 ' + donate_name + ' 捐赠装备 ' + equip_name)
        save_total()
    except Exception as e:
        log.exception(e)


# 账号日常
def daily_matters(vid, uid, N_event):
    log = logger('farm')
    try:
        App = ShatuApi(vid, uid, total['access_key'])
        App.load_index()    # 获取账户信息
        App.room()  # 公会小屋
        if datetime.datetime.now().weekday() == 0:
            App.arena_reward()  # 收取双场币
            # App.shop_item()  # 商店购买
        App.gacha()     # 扭蛋
        App.alchemy()   # 购买扫荡券
        App.training_skip()     # 探索本
        App.mission()   # 收取任务
        App.present()   # 收取礼物
        App.shuatu_daily(N_event)  # 刷图
        App.mission()   # 收取任务
        # 如果收取任务时升级，再次执行刷图函数
        App.load_index()
        if App.user_stamina > 80:
            App.shuatu_daily(N_event)
        # 地下城捐赠
        if not bilievent.load_battle_bilibili():
            for i, clan in enumerate(bind['clan']):
                if clan['clan_id'] == App.clan_id and clan['donate_user']:
                    dun = App.dungeon(clan['donate_user'])
                    if dun:
                        bind['clan'][i]['donate_times'] += 1
        return True
    except Exception as e:
        log.exception(e)
        time.sleep(30)
        return False


def farm_daily():
    start_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    N_event = bilievent.load_event_bilibili(datetime.datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S"))
    account_finish = {}
    farm_list = total["accounts"]
    # first routine
    for i, account in enumerate(farm_list):
        try:
            finish_status = daily_matters(account["vid"], account["uid"], N_event)
            if finish_status:
                account_finish[i] = 1
                print('已完成账号数'+str(sum(account_finish.values()))+'个')
        except Exception:
            continue
    finish_count = sum(account_finish.values())
    # second routine
    fail_account = []
    for i, account in enumerate(farm_list):
        if i not in account_finish.keys():
            try:
                finish_status = daily_matters(account["vid"], account["uid"], N_event)
                if finish_status:
                    account_finish[i] = 1
                else:
                    fail_account.append(account["vid"])
            except Exception:
                fail_account.append(account["vid"])
    finish_count_plus = sum(account_finish.values())
    end_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    save_bind()
    with open('./log/total.txt', 'a', encoding='utf-8') as f:
        f.write('本次共成功处理'+str(finish_count)+'个账号, 后续补充处理'+str(finish_count_plus -
                                                              finish_count)+'个账号, 开始时间为'+start_time+', 结束时间为'+end_time+'\n')
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


# 移除人员
def refresh_clan(seq='before'):
    message = "移除人员:\n"
    for clan in total['clan']:
        if clan['equip']:
            App = GonghuiApi(clan['owner'])
            mem_clan = App.check_members()
            mem_farm = []
            for account in total['accounts']:
                if account['clan_id'] == App.clan_id:
                    mem_farm.append(account['vid'])
            if seq == 'after':
                for account in list(bind['users'].keys()):
                    mem_farm.append(int(account))
            for mem in mem_clan:
                if mem not in mem_farm:
                    msg = App.remove_members(mem)
                    message += msg
    print(message)
    send_wechat(message)
    with open('./log/total.txt', 'a', encoding='utf-8') as f:
        f.write(message)


# 会战前后移除过程
def battle_remove(scheduler):
    clan_time = bilievent.time_battle_bilibili(datetime.datetime.now())
    if clan_time:
        scheduler.add_job(refresh_clan, 'date', run_date=clan_time[0]-datetime.timedelta(hours=9.5), args=['before'])
        scheduler.add_job(refresh_clan, 'date', run_date=clan_time[1]+datetime.timedelta(minutes=2), args=['after'])
        scheduler.add_job(refresh_clan, 'date', run_date=clan_time[1]+datetime.timedelta(hours=7), args=['after'])


if __name__ == "__main__":
    scheduler = BlockingScheduler(timezone="Asia/Shanghai")
    scheduler.add_job(equip_donate, 'cron', minute='20')
    scheduler.add_job(farm_daily, 'cron', hour='6,18', minute='30')
    scheduler.add_job(clear_daily, 'cron', hour='0', minute='5')
    scheduler.add_job(battle_remove, 'cron', day='23', hour='12', args=[scheduler])
    # farm_daily()
    scheduler.start()
