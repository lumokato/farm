'''
一些一次性任务实现
'''
from api.baseapi import BaseApi
from api.friendapi import FriendApi
from api.gonghuiapi import GonghuiApi
from log import logger
from json import load, dump
from os.path import exists
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


# 世界Boss活动全部收取
def jewel_plus_all():
    log = logger('jewel-')
    try:
        for account in total["accounts"]:
            print('已登录账号'+str(account))
            App = BaseApi(account['vid'], account['uid'], total['access_key'])
            App.load_index()
            App.kaiser_battle()
            App.mission_plus()
            App.season_ticket()
            # App.season_ticket_reward()
    except Exception as e:
        log.exception(e)


# 免费十连批量选择附奖
def prize_gacha():
    log = logger('farm-')
    try:
        for account in total["accounts"]:
            print('已登录账号'+str(account['vid']))
            App = BaseApi(account['vid'], account['uid'], total['access_key'])
            App.load_index()
            App.gacha_select()
    except Exception as e:
        log.exception(e)


# 农场新手活动全解锁
def farm_mission_all():
    log = logger('friend-')
    try:
        clan_ids = []
        for clan in total['clan']:
            clan_ids.append(clan['clan_id'])
        for clan_id in clan_ids:
            for friend_account in friend["accounts"]:
                App = FriendApi(friend_account['vid'], friend_account['uid'], total['access_key'])
                App.friend_remove_all()
                for account in total["accounts"]:
                    if account['clan_id'] == clan_id:
                        App.friend_request(account['uid'])
            for account in total["accounts"]:
                if account['clan_id'] == clan_id:
                    App = FriendApi(account['vid'], account['uid'], total['access_key'])
                    for i, friend_account in enumerate(friend["accounts"]):
                        App.friend_accept(friend_account['vid'])
                        friend["accounts"][i]['total_friend'] += 1
                    for friend_account in friend["accounts"]:
                        App.friend_remove(friend_account['vid'])
                    print('已登录账号'+str(App.viewer_id))
                    App.freshman_mission()
        save_friend()
    except Exception as e:
        log.exception(e)


# 按vid完成新手活动
def user_mission(vid):
    log = logger('friend-')
    try:
        for i, friend_account in enumerate(friend["accounts"]):
            App = FriendApi(friend_account['vid'], friend_account['uid'], total['access_key'])
            # if i > 0:
            #     App.rename()
            App.friend_remove_all()
            App.friend_request(vid)
            friend["accounts"][i]['total_friend'] += 1
        save_friend()
    except Exception as e:
        log.exception(e)


def farm_back():
    '''会战结束手动捐一次'''
    start_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    account_finish = {}
    farm_list = total["accounts"]
    # first routine
    for i, account in enumerate(farm_list):
        for j, clan in enumerate(bind['clan']):
            if clan['clan_id'] == account['clan_id'] and clan['donate_user']:
                try:
                    App = BaseApi(account["vid"], account["uid"], total['access_key'])
                    dun = App.dungeon(clan['donate_user'])
                    if dun:
                        bind['clan'][j]['donate_times'] += 1
                        account_finish[i] = 1
                except Exception:
                    continue
    finish_count = sum(account_finish.values())
    fail_account = []
    # second routine
    for i, account in enumerate(farm_list):
        for j, clan in enumerate(bind['clan']):
            if clan['clan_id'] == account['clan_id'] and clan['donate_user']:
                if i not in account_finish.keys():
                    try:
                        App = BaseApi(account["vid"], account["uid"], total['access_key'])
                        dun = App.dungeon(clan['donate_user'])
                        if dun:
                            bind['clan'][j]['donate_times'] += 1
                            account_finish[i] = 1
                        else:
                            fail_account.append(account["vid"])
                    except Exception:
                        fail_account.append(account["vid"])
    finish_count_plus = sum(account_finish.values())
    end_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    save_bind()
    with open('./log/total.txt', 'a', encoding='utf-8') as f:
        f.write('本次手动捐赠共成功处理'+str(finish_count)+'个账号, 后续补充处理'+str(finish_count_plus - finish_count)+'个账号, 开始时间为'+start_time+', 结束时间为'+end_time+'\n')
        if fail_account:
            f.write('未成功处理账号共'+str(len(fail_account))+'个')


# 移动人员
def move_member(mem_dict):
    message = ''
    move_list = []
    clan_remove = {}
    for account in total["accounts"]:
        if account['vid'] in mem_dict.keys():
            move_list.append(account)
            if account['clan_id'] not in clan_remove.keys():
                clan_remove[account['clan_id']] = [account['vid']]
            else:
                clan_remove[account['clan_id']].append(account['vid'])

    for clan in total['clan']:
        if clan['clan_id'] in clan_remove.keys():
            App = GonghuiApi(clan['owner'])
            mem_clan = clan_remove[clan['clan_id']]
            for mem in mem_clan:
                msg = App.remove_members(mem)
                if msg:
                    message += msg
    for move_mem in move_list:
        App = GonghuiApi(move_mem['vid'])
        msg = App.join_clan(mem_dict[move_mem['vid']])
        if msg:
            message += msg
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


if __name__ == '__main__':
    farm_back()
