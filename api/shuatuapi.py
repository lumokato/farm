from api.normallist import shuatu_list
from .baseapi import BaseApi
import time
import random


# 按图号计算所需体力
def quest_stamina(quest_id: int):
    if quest_id == 11001001:
        return 6
    elif quest_id > 11001001 and quest_id < 11004001:
        return 8
    elif quest_id >= 11004001 and quest_id < 11007001:
        return 9
    elif quest_id >= 11007001 and quest_id < 11099001:
        return 10
    elif quest_id >= 12001001 and quest_id < 12004001:
        return 16
    elif quest_id >= 12004001 and quest_id < 12007001:
        return 18
    elif quest_id >= 12007001 and quest_id < 12099001:
        return 20
    elif quest_id >= 18001001 and quest_id <= 19001002:
        return 15
    elif quest_id < 11000000:
        return 8


class ShatuApi(BaseApi):

    # 图号与图id互转
    def tu_num_str(self, input):
        # 图号转id
        if type(input) == int:
            if input >= 11001001 and input < 11099001:
                return str(int((input - 11000000)/1000)) + '-' + str((input - 11000000) % 1000)
            elif input >= 12001001 and input < 12099001:
                return 'H' + str(int((input - 12000000)/1000)) + '-' + str((input - 12000000) % 1000)
            elif input > 18001000:
                return 'S' + str(input - 18001000)
            else:
                return 'E' + str(input % 100)
        # id转图号
        elif type(input) == str:
            if input[0] == "H":
                tu = input[1:]
                lst = tu.split("-")
                return 12000000 + 1000 * int(lst[0]) + int(lst[1])
            elif input[0] == "S":   # 圣迹
                tu = input[-1]
                return 18001000 + int(tu)
            elif input[0] == "E":  # 活动
                tu = input[-1]
                return self.event_id * 1000 + 100 + int(tu)
            else:
                lst = input.split("-")
                return 11000000 + 1000 * int(lst[0]) + int(lst[1])
        else:
            print('输入错误')
            return None

    # 扫荡跳过
    def quest_skip(self, quest_id: int, random_count: int, current_ticket_num: int):
        if random_count > 99:
            random_count = 99
        # 刷主线
        if quest_id > 11000000:
            temp = self.client.callapi('quest/quest_skip', {'quest_id': quest_id, 'random_count': random_count, 'current_ticket_num': current_ticket_num})
            if 'quest_result_list' not in temp:
                self.client.login(self.uid, self.access_key)
                temp = self.client.callapi('quest/quest_skip', {'quest_id': quest_id, 'random_count': random_count, 'current_ticket_num': current_ticket_num})
        # 刷活动图
        else:
            temp = self.client.callapi('event/hatsune/quest_skip', {'event_id': self.event_id, 'quest_id': quest_id, 'use_ticket_num': random_count, 'current_ticket_num': current_ticket_num})
            if 'quest_result_list' not in temp:
                self.client.login(self.uid, self.access_key)
                temp = self.client.callapi('event/hatsune/quest_skip', {'event_id': self.event_id, 'quest_id': quest_id, 'use_ticket_num': random_count, 'current_ticket_num': current_ticket_num})
        if 'item_list' in temp:
            self.num_ticket = temp['item_list'][0]['stock']
            self.user_stamina = temp['user_info']['user_stamina']
        else:
            self.load_index()
            print('重新加载')
        print('  刷图' + self.tu_num_str(quest_id) + '共' + str(random_count) + '次,剩余体力' +
              str(self.user_stamina)+',剩余扫荡券'+str(self.num_ticket))
        # time.sleep(random.randint(3, 6))
        time.sleep(2)

    # 购买体力
    def buy_stamina(self, times: int):
        self.load_index()
        if times > self.recovery:
            for i in range(times - self.recovery):
                if self.user_stamina < 878:
                    temp1 = self.client.callapi('shop/recover_stamina', {'current_currency_num': self.user_jewel+self.paid_jewel})
                    self.user_jewel = temp1['user_jewel']['free_jewel']
                    self.user_stamina = temp1['user_info']['user_stamina']
                    time.sleep(3)
                else:
                    print('  体力已满，无法继续购买')
                    break
        else:
            print('  今日已买过'+str(self.recovery)+'次')
        return self.user_stamina

    # 按图号扫荡,如果刷图过程未完成，返回True
    def quest(self, tu_num, quest_num, buy_count):
        if tu_num in self.quest_dict.keys():
            quest_num = quest_num - self.quest_dict[tu_num]
        else:
            # print("此图未解锁")
            return True
        if quest_num < 1:
            return True
        while quest_num > 0:  # 修正1-1超过100次
            if quest_stamina(tu_num) * min(99, quest_num) < self.user_stamina:
                self.quest_skip(tu_num, quest_num, self.num_ticket)
            else:
                self.buy_stamina(buy_count)
                if quest_stamina(tu_num) * min(99, quest_num) < self.user_stamina:
                    self.quest_skip(tu_num, quest_num, self.num_ticket)
                else:
                    quest_num = int(self.user_stamina/quest_stamina(tu_num))
                    if quest_num:
                        self.quest_skip(tu_num, quest_num, self.num_ticket)
                    return False
            quest_num -= 99
        return True

    # 每日经验与玛那本(已注释掉log)
    def training_skip(self):
        gold_num = 21001007
        while gold_num > 21001000:
            if gold_num in self.quest_dict:
                break
            gold_num -= 1
        if gold_num == 21001000:
            # print("  未解锁玛那本")
            return False
        gold_count = 2 - self.gold_quest
        if gold_count:
            temp = self.client.callapi('/training_quest/quest_skip', {
                                       'quest_id': gold_num, 'random_count': gold_count, 'current_ticket_num': self.num_ticket})
            if 'quest_result_list' not in temp:
                self.client.login(self.uid, self.access_key)
                temp = self.client.callapi('/training_quest/quest_skip', {
                                           'quest_id': gold_num, 'random_count': gold_count, 'current_ticket_num': self.num_ticket})
            self.num_ticket = temp['item_list'][0]['stock']
            # print("  刷玛那本"+str(gold_num - 21001000)+"共"+str(gold_count)+"次")
            time.sleep(5)
        exp_num = 21002007
        while exp_num > 21002000:
            if exp_num in self.quest_dict:
                break
            exp_num -= 1
        if exp_num == 21002000:
            # print("  未解锁经验本")
            return False
        exp_count = 2 - self.exp_quest
        if exp_count:
            temp = self.client.callapi('/training_quest/quest_skip', {
                                       'quest_id': exp_num, 'random_count': exp_count, 'current_ticket_num': self.num_ticket})
            if 'quest_result_list' not in temp:
                self.client.login(self.uid, self.access_key)
                temp = self.client.callapi('/training_quest/quest_skip', {
                                           'quest_id': exp_num, 'random_count': exp_count, 'current_ticket_num': self.num_ticket})
            self.num_ticket = temp['item_list'][0]['stock']
            # print("  刷经验本"+str(exp_num - 21002000)+"共"+str(exp_count)+"次")
            time.sleep(5)

    # 购买扫荡券
    def alchemy(self):
        # 钻量大于3000时购买扫荡券
        if self.num_ticket < 200 and self.user_jewel > 3000:
            temp = self.client.callapi(
                'shop/alchemy', {'multiple_count': 10, 'pay_or_free': 2, 'current_currency_num': self.user_jewel})
            if 'alchemy_reward_list' not in temp:
                self.client.login(self.uid, self.access_key)
                temp = self.client.callapi(
                    'shop/alchemy', {'multiple_count': 10, 'pay_or_free': 2, 'current_currency_num': self.user_jewel})
            self.num_ticket = temp['alchemy_reward_list'][0]['reward_info_list'][0]['stock']
            self.user_jewel = temp['free_jewel']
        # print("  剩余钻/消耗钻"+str(self.user_jewel))

    # 查活动图状态
    def event_dict(self):
        temp0 = self.client.callapi(
            'event/hatsune/top', {'event_id': self.event_id})
        if 'event_status' not in temp0:
            self.client.login(self.uid, self.access_key)
            temp0 = self.client.callapi(
                'event/hatsune/top', {'event_id': self.event_id})
        temp = self.client.callapi(
            'event/hatsune/quest_top', {'event_id': self.event_id})
        if 'quest_list' in temp:
            for quest in temp['quest_list']:
                if quest['clear_flag'] == 3 and quest['result_type'] == 2:
                    self.quest_dict[quest['quest_id']
                                    ] = quest['daily_clear_count']

    # 显示账号基本信息
    def show_account_status(self):
        quest_N = []
        quest_H = []
        for tu_num in self.quest_dict.keys():
            if tu_num >= 11001001 and tu_num < 11099001:
                quest_N.append(tu_num)
            elif tu_num >= 12001001 and tu_num < 12099001:
                quest_H.append(tu_num)
        if len(quest_N) > 0:
            max_N = self.tu_num_str(max(quest_N))
        else:
            max_N = '未解锁'
        if len(quest_H) > 0:
            max_H = self.tu_num_str(max(quest_H))
        else:
            max_H = '未解锁'
        self.load_index()
        print('id为'+str(self.viewer_id)+', 等级为'+str(self.team_level)+', 所在行会id为'+str(self.clan_id)+', N图最高进度为'+max_N+', H图最高进度为'+max_H)

    # 刷所有已解锁H图,返回值为是否继续刷N图
    def shuatu_allH(self):
        quest_H = []
        for tu_num in self.quest_dict.keys():
            if tu_num >= 12001001 and tu_num < 12099001:
                quest_H.append(tu_num)
        for tu in quest_H:
            if not self.quest(tu, 3, 0):
                return False
        return self.user_stamina > 20

    # 按账号解锁状态刷N图
    def shuatu_N(self, N_event):
        if N_event == 3:
            buy_stamina = 6
        else:
            buy_stamina = 0
        quest_N = []
        for tu_num in self.quest_dict.keys():
            if tu_num >= 11001001 and tu_num < 11099001:
                quest_N.append(tu_num)
        shuatu_base = shuatu_list(max(quest_N))
        shuatu = []
        for tu_base in shuatu_base:
            tu_num = self.tu_num_str(tu_base)
            if tu_num in self.quest_dict.keys():
                shuatu.append(tu_num)
        stamina_base = 0
        for tu in shuatu:
            stamina_base += quest_stamina(tu)
        shuatu_count = int(2500/stamina_base)
        random.shuffle(shuatu)
        for tu_num in shuatu:
            # 买体力次数更改为0
            if not self.quest(tu_num, shuatu_count, buy_stamina):
                return False
        return self.user_stamina > 20

    # 按N2状态刷图
    def shuatu_daily(self, N_event, max_level):
        self.home_index()    # 刷图前读取一次刷图列表
        if self.num_ticket < 50:
            print('扫荡券过少,请检查账号状态')
            return True
        if N_event or max_level - self.team_level > 20:
            print('    刷N图')
            self.shuatu_N(N_event)
        else:
            # 非N2时只刷H图
            self.shuatu_allH()
