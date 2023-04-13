from apscheduler.schedulers.background import BlockingScheduler
from api.friendapi import FriendApi
from log import logger
from json import load, dump
from os.path import exists

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


def friend_mission():
    log = logger('friend')
    blacklist = friend['blacklist']
    try:
        for i, friend_account in enumerate(friend["accounts"]):
            App = FriendApi(friend_account['vid'], friend_account['uid'], total['access_key'])
            pending_list, friend_num = App.pending_list()
            if i == 0:
                if friend_num > 25:
                    App.friend_remove_all()
            else:
                App.friend_remove_all()
            if pending_list:
                print(str(App.viewer_id)+'通过好友'+str(pending_list))
            for pd_user in pending_list:
                if pd_user not in blacklist:
                    App.friend_accept(pd_user)
                    friend["accounts"][i]['total_friend'] += 1
                else:
                    print(str(App.viewer_id)+'拒绝'+str(pd_user))
        save_friend()
    except Exception as e:
        log.exception(e)


if __name__ == "__main__":
    scheduler = BlockingScheduler(timezone="Asia/Shanghai")
    scheduler.add_job(friend_mission, 'cron', second='5')
    scheduler.start()
