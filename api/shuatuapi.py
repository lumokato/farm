import asyncio
import json

from api.normallist import shuatu_list
from .baseapi import BaseApi
import time
import random


# 按图号计算所需体力
def quest_stamina(quest_id: int):
    if quest_id == 11001001:
        return 6
    elif 11001001 < quest_id < 11004001:
        return 8
    elif 11004001 <= quest_id < 11007001:
        return 9
    elif 11007001 <= quest_id < 11099001:
        return 10
    elif 12001001 <= quest_id < 12004001:
        return 16
    elif 12004001 <= quest_id < 12007001:
        return 18
    elif 12007001 <= quest_id < 13099001:
        return 20
    elif 18001001 <= quest_id <= 19001002:
        return 15
    elif quest_id < 11000000:
        identify_code = quest_id % 1000
        if identify_code in [101, 102, 103, 104, 105]:
            return 8
        elif identify_code in [106, 107, 108, 109, 110]:
            return 9
        elif identify_code in [111, 112, 113, 114, 115]:
            return 10
        elif identify_code in [201, 202]:
            return 16
        elif identify_code in [203, 204]:
            return 18
        elif identify_code in [205]:
            return 20


class ShuatuApi(BaseApi):

    # 图号与图id互转
    def tu_num_str(self, tu):
        # 图号转id
        if type(tu) == int:
            if 11001001 <= tu < 11099001:
                return str(int((tu - 11000000) / 1000)) + '-' + str((tu - 11000000) % 1000)
            elif 12001001 <= tu < 12099001:
                return 'H' + str(int((tu - 12000000) / 1000)) + '-' + str((tu - 12000000) % 1000)
            elif tu > 18001000:
                return 'S' + str(tu - 18001000)
            else:
                return 'E' + str(tu % 100)
        # id转图号
        elif type(tu) == str:
            if tu[0] == "H":
                tu = tu[1:]
                lst = tu.split("-")
                return 12000000 + 1000 * int(lst[0]) + int(lst[1])
            elif tu[0] == "S":   # 圣迹
                tu = tu[-1]
                return 18001000 + int(tu)
            elif tu[0] == "E":  # 活动
                tu = tu[-1]
                return self.event_id * 1000 + 100 + int(tu)
            else:
                lst = tu.split("-")
                return 11000000 + 1000 * int(lst[0]) + int(lst[1])
        else:
            print('输入错误')
            return None

    # 扫荡跳过
    async def quest_skip(self, quest_id: int, random_count: int, current_ticket_num: int):
        if random_count > 99:
            random_count = 99
        # 刷主线
        if quest_id > 11000000:
            temp = await self.client.callapi('quest/quest_skip', {'quest_id': quest_id, 'random_count': random_count, 'current_ticket_num': current_ticket_num})
            if 'quest_result_list' not in temp:
                return False
        # 刷活动图
        else:
            temp = await self.client.callapi('event/hatsune/quest_skip', {'event_id': self.event_id, 'quest_id': quest_id, 'use_ticket_num': random_count, 'current_ticket_num': current_ticket_num})
            if 'quest_result_list' not in temp:
                return False
        if 'item_list' in temp:
            self.num_ticket = temp['item_list'][0]['stock']
            self.user_stamina = temp['user_info']['user_stamina']
        else:
            await self.load_index(requery=True)
            print('重新加载')
        print('  刷图' + self.tu_num_str(quest_id) + '共' + str(random_count) + '次,剩余体力' +
              str(self.user_stamina)+',剩余扫荡券'+str(self.num_ticket))
        await asyncio.sleep(2)
        return True

    # 购买体力
    async def buy_stamina(self, times: int):
        await self.load_index(requery=True)
        if times > self.recovery:
            for i in range(times - self.recovery):
                if self.user_stamina < 878:
                    temp1 = await self.client.callapi('shop/recover_stamina', {'current_currency_num': self.user_jewel+self.paid_jewel})
                    if 'user_info' not in temp1:
                        return False
                    self.user_jewel = temp1['user_jewel']['free_jewel']
                    self.user_stamina = temp1['user_info']['user_stamina']
                    await asyncio.sleep(2)
                else:
                    # print('  体力已满，无法继续购买')
                    break
        # else:
        #     print('  今日已买过'+str(self.recovery)+'次')
        return self.user_stamina

    # 按图号扫荡,如果刷图过程未完成，返回-1
    async def quest(self, tu_num, quest_num, buy_count):
        if tu_num in self.quest_dict.keys():
            quest_num = quest_num - self.quest_dict[tu_num]
        else:
            # print("此图未解锁")
            return True
        if quest_num < 1:
            return True
        while quest_num > 0:  # 修正1-1超过100次
            if quest_stamina(tu_num) * min(99, quest_num) < self.user_stamina:
                await self.query(self.quest_skip, tu_num, quest_num, self.num_ticket)
            else:
                await self.query(self.buy_stamina, buy_count)
                if quest_stamina(tu_num) * min(99, quest_num) < self.user_stamina:
                    await self.query(self.quest_skip, tu_num, quest_num, self.num_ticket)
                else:
                    quest_num = int(self.user_stamina/quest_stamina(tu_num))
                    if quest_num:
                        await self.query(self.quest_skip, tu_num, quest_num, self.num_ticket)
                    return False
            quest_num -= 99
        return True

    # 每日经验与玛那本(已注释掉log)
    async def training_skip(self):
        gold_num = 21001007
        while gold_num > 21001000:
            if gold_num in self.quest_dict:
                break
            gold_num -= 1
        if gold_num == 21001000:
            # print("  未解锁玛那本")
            return -1
        gold_count = 2 - self.gold_quest
        if gold_count:
            temp = await self.client.callapi('/training_quest/quest_skip', {
                                       'quest_id': gold_num, 'random_count': gold_count, 'current_ticket_num': self.num_ticket})
            if 'quest_result_list' not in temp:
                return False
            self.num_ticket = temp['item_list'][0]['stock']
            # print("  刷玛那本"+str(gold_num - 21001000)+"共"+str(gold_count)+"次")
            await asyncio.sleep(3)
        exp_num = 21002007
        while exp_num > 21002000:
            if exp_num in self.quest_dict:
                break
            exp_num -= 1
        if exp_num == 21002000:
            # print("  未解锁经验本")
            return -1
        exp_count = 2 - self.exp_quest
        if exp_count:
            temp = await self.client.callapi('/training_quest/quest_skip', {
                                       'quest_id': exp_num, 'random_count': exp_count, 'current_ticket_num': self.num_ticket})
            if 'quest_result_list' not in temp:
                return False
            self.num_ticket = temp['item_list'][0]['stock']
            # print("  刷经验本"+str(exp_num - 21002000)+"共"+str(exp_count)+"次")
            await asyncio.sleep(3)
        return True

    # 购买扫荡券
    async def alchemy(self):
        # 钻量大于3000时购买扫荡券
        if self.num_ticket < 200 and self.user_jewel > 3000:
            temp = await self.client.callapi(
                'shop/alchemy', {'multiple_count': 10, 'pay_or_free': 2, 'current_currency_num': self.user_jewel})
            if 'alchemy_reward_list' not in temp:
                return False
            self.num_ticket = temp['alchemy_reward_list'][0]['reward_info_list'][0]['stock']
            self.user_jewel = temp['free_jewel']
        # print("  剩余钻/消耗钻"+str(self.user_jewel))
        return True

    # 查活动图状态
    async def event_dict(self):
        temp0 = await self.client.callapi('event/hatsune/top', {'event_id': self.event_id})
        if 'event_status' not in temp0:
            return False
        temp = await self.client.callapi('event/hatsune/quest_top', {'event_id': self.event_id})
        if 'quest_list' in temp:
            for quest in temp['quest_list']:
                if quest['clear_flag'] == 3 and quest['result_type'] == 2:
                    self.quest_dict[quest['quest_id']] = quest['daily_clear_count']

    # 显示账号基本信息
    async def show_account_status(self):
        quest_n = []
        quest_h = []
        for tu_num in self.quest_dict.keys():
            if 11001001 <= tu_num < 11099001:
                quest_n.append(tu_num)
            elif 12001001 <= tu_num < 12099001:
                quest_h.append(tu_num)
        if len(quest_n) > 0:
            max_n = self.tu_num_str(max(quest_n))
        else:
            max_n = '未解锁'
        if len(quest_h) > 0:
            max_h = self.tu_num_str(max(quest_h))
        else:
            max_h = '未解锁'
        await self.load_index()
        print('id为'+str(self.viewer_id)+', 等级为'+str(self.team_level)+', 所在行会id为'+str(self.clan_id)+', N图最高进度为'+max_n+', H图最高进度为'+max_h)

    # 刷所有已解锁H图,返回值为是否继续刷N图
    async def shuatu_allH(self):
        quest_h = []
        for tu_num in self.quest_dict.keys():
            if 12001001 <= tu_num < 12099001:
                quest_h.append(tu_num)
        for tu in quest_h:
            if not await self.quest(tu, 3, 0):
                return False
        return self.user_stamina > 20

    # 按账号解锁状态刷N图
    async def shuatu_N(self, n_event):
        if n_event == 3:
            buy_stamina = 6
        else:
            buy_stamina = 0
        quest_n = []
        for tu_num in self.quest_dict.keys():
            if 11001001 <= tu_num < 11099001:
                quest_n.append(tu_num)
        shuatu_base = shuatu_list(max(quest_n))
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
            if not await self.quest(tu_num, shuatu_count, buy_stamina):
                return False
        return self.user_stamina > 20

    # 按N2状态刷图
    async def shuatu_daily(self, n_event, max_level):
        await self.home_index()    # 刷图前读取一次刷图列表
        if self.num_ticket < 50:
            print('扫荡券过少,请检查账号状态')
            return True
        if n_event or max_level - self.team_level > 20:
            # print('    刷N图')
            await self.shuatu_N(n_event)
        else:
            # 非N2时只刷H图
            await self.shuatu_allH()

    # 主号经验本
    async def sweep_explore_exp(self):
        x_remain = self.home["training_quest_max_count"]["exp_quest"] - self.home["training_quest_count"]["exp_quest"]
        if x_remain == 0:
            return f'Skip. 今日已完成EXP探索'
        else:
            for i in range(21002013, 21002000, -1):
                if i in self.quest_dict and self.quest_dict[i]["clear_flg"] == 3:
                    try:
                        temp = await self.client.callapi('/training_quest/quest_skip', {
                            'quest_id': i, 'random_count': x_remain, 'current_ticket_num': self.num_ticket})
                        if 'quest_result_list' not in temp:
                            return False
                        self.num_ticket = temp['item_list'][0]['stock']
                        print(f'Succeed. 成功进行EXP探索({i%100}级，{x_remain}次)')
                        break
                    except Exception as e:
                        print(f'Fail. EXP探索({i%100}级，{x_remain}次)失败：{e}')
                        break

    async def sweep_explore_mana(self):
        x_remain = self.home["training_quest_max_count"][
            "gold_quest"] - self.home["training_quest_count"]["gold_quest"]
        if x_remain == 0:
            return f'Skip. 今日已完成MANA探索'
        else:
            for i in range(21001013, 21001000, -1):
                if i in self.quest_dict and self.quest_dict[i]["clear_flg"] == 3:
                    try:
                        temp = await self.client.callapi('/training_quest/quest_skip', {
                            'quest_id': i, 'random_count': x_remain, 'current_ticket_num': self.num_ticket})
                        if 'quest_result_list' not in temp:
                            return False
                        self.num_ticket = temp['item_list'][0]['stock']
                        print(f'Succeed. 成功进行MANA探索({i % 100}级，{x_remain}次)')
                        break
                    except Exception as e:
                        print(f'Fail. MANA探索({i % 100}级，{x_remain}次)失败：{e}')
                        break

    async def star6_sweep(self, map_id):
        with open('unit_id.json', encoding='utf-8') as fp:
            unit_dict = json.load(fp)
        with open('star6.json', encoding='utf-8') as fp:
            star6_dict = json.load(fp)
        item_id = star6_dict[str(map_id)]
        chara_id = f'1{str(item_id)[-3:]}01'
        chara_name = unit_dict[chara_id]
        stamina_before = self.user_stamina
        try:
            await self.quest(map_id, 3, 0)
            if self.user_stamina < stamina_before:
                chara_pure_frag_stock = await self.get_item_stock(item_id)
                print(f'Success. {chara_name} 的纯净记忆碎片共{chara_pure_frag_stock}片')
        except Exception as e:
            print(e)

    async def event_hard_sweep(self, sweep_type: str, map_list=[1, 3, 5]):
        '''
        sweep_type: enum("old", "new", "all")
        '''

        try:
            event_id_list, msg = await self.get_event_id_list(sweep_type)
        except Exception as e:
            print(e)

        for event_id in event_id_list:
            print(f'活动{event_id}')
            try:
                event_quest = await self.client.callapi("/event/hatsune/quest_top", {"event_id": event_id})
                quest_list = event_quest["quest_list"]
                for _quest in quest_list:
                    if _quest['clear_flag'] == 3 and _quest['result_type'] == 2:
                        self.quest_dict[_quest['quest_id']] = _quest['daily_clear_count']
            except Exception as e:
                print(f'Fail. 获取活动{event_id}通关信息失败：{e}')
                break
            self.event_id = event_id
            for i in map_list:
                # msg.append(f'H1-{i}: ')
                f = False
                quest_id = int(f'{event_id}2{i:02d}')
                for _quest in quest_list:
                    if _quest["quest_id"] == quest_id:
                        f = True
                        if _quest["clear_flag"] != 3:
                            print(f'Abort. H1-{i}为{_quest["clear_flag"]}星通关，无法扫荡')
                            break
                        if _quest["daily_clear_count"] == 3:
                            print(f'Skip. H1-{i}已扫荡')
                            break
                        await self.quest(quest_id, 3 - _quest["daily_clear_count"], 0)
                if not f:
                    print(f'Abort. H1-{i} Unlock')
                    break
