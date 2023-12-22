from .pcrclient import PCRClient
import time
import datetime
from json import load
import asyncio

with open('account.json', encoding='utf-8') as fp:
    total_api = load(fp)

with open('unit_id.json', encoding='utf-8') as fp:
    unit_id_dict = load(fp)

with open('equip_id.json', encoding="utf-8") as fp:
    equip2name = load(fp)

lck = asyncio.Lock()


def all_account(func):
    async def single_account(account, func_single, sem):
        async with sem:
            client = BaseApi(account['vid'], account['uid'], total_api['access_key'])
            await client.query(client.load_index)
            await func_single(client)

    async def all_main():
        task_list = []
        sem = asyncio.Semaphore(10)
        for account in total_api["accounts"]:
            task = asyncio.create_task(single_account(account, func, sem))
            task_list.append(task)
        await asyncio.gather(*task_list)
    asyncio.run(all_main())


class BaseApi:
    def __init__(self, viewer_id, uid=None, access_key=None):
        if not uid:
            for account in total_api['accounts']:
                if account['vid'] == viewer_id:
                    uid = account['uid']
        if not access_key:
            access_key = total_api['access_key']
        self.uid = uid
        self.viewer_id = viewer_id
        self.access_key = access_key
        self.client = PCRClient(viewer_id)
        self.load = None
        self.home = None
        self.unit_id_dict = unit_id_dict
        # print('已登录账号'+str(viewer_id))

    async def query(self, func, *args):
        # try:
        # async with lck:
        for re_login in range(2):
            while self.client.shouldLogin:
                self.load, self.home = await self.client.login(self.uid, self.access_key)
                await self.load_index()
                await self.home_index()
            ret = await func(*args)
            if not ret:
                self.client.shouldLogin = True
            else:
                return ret
        # except Exception as e:
        #     print(repr(e))
        #     return repr(e)

    # 账号基本信息
    async def load_index(self, requery=False):
        if requery:
            self.load = await self.client.callapi("load/index", {"carrier": "google"})
        self.tower_coin = self.arena_coin = self.grand_arena_coin = self.clan_battle_coin = 0  # 初始化
        self.user_stamina = self.load['user_info']['user_stamina']
        self.viewer_id = self.load['user_info']['viewer_id']
        self.clan_like = self.load['clan_like_count']  # 0为未点赞，1为已点赞
        for item in self.load['item_list']:
            if item['id'] == 23001:  # 扫荡券
                self.num_ticket = item['stock']
            elif item['id'] == 90002:  # 地下城币
                self.tower_coin = item['stock']
            elif item['id'] == 90003:  # 竞技场币
                self.arena_coin = item['stock']
            elif item['id'] == 90004:  # 公主竞技场币
                self.grand_arena_coin = item['stock']
            elif item['id'] == 90006:  # 会战币
                self.clan_battle_coin = item['stock']
        self.gold = self.load['user_gold']['gold_id_free']  # 玛那数
        self.user_jewel = self.load['user_jewel']['free_jewel']
        self.paid_jewel = self.load['user_jewel']['paid_jewel']
        self.recovery = self.load['shop']['recover_stamina']['exec_count']
        self.free_gacha_time = self.load['can_free_gacha']
        self.compaign_gacha_time = self.load['can_campaign_gacha']
        self.team_level = self.load['user_info']['team_level']
        self.room_item_level = int(self.team_level / 10) + 1
        # print('已登录账号' + str(self.viewer_id) + ",账号等级为" + str(self.team_level) + ',现有体力为' +
        #       str(self.user_stamina) + ',免费钻量' + str(self.user_jewel))
        # 活动id,暂时不用
        # if 'event_id' in self.load['event_statuses'][0]:
        #     self.event_id = self.load['event_statuses'][0]['event_id']
        #     self.event_period = self.load['event_statuses'][0]['period']
        #     if self.event_period == 2:
        #         self.event_dict()
        if 'cf' in self.load:
            self.fortune_id = self.load['cf']['fortune_id']
            self.fortune_unit_list = self.load['cf']['unit_list']
            await self.chara_fortune()
        self.unit_list = []
        for unit in self.load['unit_list']:
            self.unit_list.append(unit['id'])
        self.read_story_ids = self.load['read_story_ids']

    # 账号推图完成情况
    async def home_index(self, requery=False):
        if requery:
            self.home = await self.client.callapi("home/index", {'message_id': 1, 'tips_id_list': [], 'is_first': 1,
                                                                 'gold_history': 0})
        if 'quest_list' not in self.home:
            self.load, self.home = await self.client.login(self.uid, self.access_key)
        self.quest_dict = {}
        for _quest in self.home['quest_list']:
            if _quest['clear_flg'] == 3 and _quest['result_type'] == 2:
                self.quest_dict[_quest['quest_id']] = _quest['daily_clear_count']
        self.gold_quest = self.home['training_quest_count']['gold_quest']
        self.clan_id = self.home['user_clan']['clan_id']
        self.donation_num = self.home['user_clan']['donation_num']
        self.exp_quest = self.home['training_quest_count']['exp_quest']
        # 地下城进入情况与剩余次数
        self.dungeon_enter = self.home['dungeon_info']['enter_area_id']
        self.dungeon_rest = self.home['dungeon_info']['rest_challenge_count'][0]['count']
        # print(self.dungeon_enter, self.dungeon_rest)

    # 行会聊天室
    async def chat_monitor(self):
        temp = await self.client.callapi('clan/chat_info_list', {'clan_id': self.clan_id, 'start_message_id': 0,
                                                                 'search_date': '2099-12-31', 'direction': 1,
                                                                 'count': 10, 'wait_interval': 3,
                                                                 'update_message_ids': []})
        if 'users' not in temp:
            return False
        return temp

    # 点赞
    async def like(self, clan_id: int, viewer_id: int):
        temp = await self.client.callapi('clan/like', {'clan_id': clan_id, 'target_viewer_id': viewer_id})
        if 'stamina_info' not in temp:
            return False
        return temp['stamina_info']['user_stamina']

    # 任务查看与收取
    async def mission(self):
        temp = await self.client.callapi('mission/index', {'request_flag': {'quest_clear_rank': 0}})
        if 'missions' not in temp:
            return False
        await asyncio.sleep(2)
        wait_accept = 0
        for mission in temp['missions']:
            if mission is not None:
                if mission['mission_status'] == 1 and mission['mission_id'] < 20000000:
                    wait_accept = 1
                    break
        if wait_accept:
            temp1 = await self.client.callapi('mission/accept', {'type': 1, 'id': 0, 'buy_id': 0})
            if 'rewards' not in temp1:
                return False
            await asyncio.sleep(2)
        return True

    # 礼物查看与收取
    async def present(self):
        temp = await self.client.callapi('present/index',
                                         {'time_filter': -1, 'type_filter': 0, 'desc_flag': True, 'offset': 0})
        if 'present_info_list' not in temp:
            return False
        await asyncio.sleep(2)
        if len(temp['present_info_list']):
            temp1 = await self.client.callapi('present/receive_all',
                                              {'time_filter': -1, 'type_filter': 0, 'desc_flag': True})
            if 'rewards' not in temp1:
                return False
            print('  已收取礼物')
            await asyncio.sleep(2)
        return True

    # 进入公会小屋，收取体力
    async def room(self):
        if self.viewer_id == 1423390712318:
            print('账号' + str(self.viewer_id) + '跳过小屋,账号等级为' + str(self.team_level) + ',免费钻量' +
                  str(self.user_jewel) + ',时间为' + time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()))
            return True
        temp = await self.client.callapi('room/start', {"wac_auto_option_flag": 1})
        if 'user_room_item_list' in temp:
            for item in temp['user_room_item_list']:
                for serial_id in range(4, 8):  # 4:扫荡券, 5:体力, 6:药剂, 7:玛娜
                    if item['serial_id'] == serial_id:
                        # 如果家具等级过低，进行升级
                        if item['room_item_level'] < self.room_item_level:
                            temp1 = await self.client.callapi('room/level_up_start',
                                                              {'floor_number': 1, 'serial_id': serial_id})
                            print('  升级家具' + str(serial_id))
            print('账号' + str(self.viewer_id) + '已进入小屋,账号等级为' + str(self.team_level) + ',免费钻量' +
                  str(self.user_jewel) + ',时间为' + time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()))
        await asyncio.sleep(2)
        temp1 = await self.client.callapi('room/receive_all', {})
        if 'reward_list' in temp1:
            for item in temp1['reward_list']:
                if item['id'] == 23001:  # 扫荡券
                    self.num_ticket = item['stock']
                if item['id'] == 93001:  # 体力
                    self.user_stamina = item['stock']
        await asyncio.sleep(2)
        return True

    # 免费扭蛋
    async def gacha(self):
        temp = await self.client.callapi('gacha/index', {})
        if 'gacha_info' not in temp:
            return False
        for gacha in temp['gacha_info']:
            if gacha['id'] < 20000:
                free_gacha_id = gacha['id']
            # 公主祭典id为500xx
            if 30000 < gacha['id'] < 70000:
                campaign_gacha_id = gacha['id']
                exchange_id = gacha['exchange_id']
        if 'campaign_info' in temp:
            self.campaign_id = temp['campaign_info']['campaign_id']
        if self.free_gacha_time:
            await self.client.callapi('gacha/exec', {'gacha_id': free_gacha_id, 'gacha_times': 10,
                                                            'exchange_id': 0, 'draw_type': 1, 'current_cost_num': -1,
                                                            'campaign_id': 0})
        await asyncio.sleep(2)
        if self.compaign_gacha_time:
            time_now = datetime.datetime.now()
            # 免费扭蛋设定在下午抽取
            if time_now.hour > 12:
                await self.gacha_compaign(campaign_gacha_id, exchange_id)
        # if 'ticket_gacha_info' in temp:
        #     await self.gacha_ticket()
        return True

    # 抽取免费十连
    async def gacha_compaign(self, gacha_id, exchange_id):
        temp = await self.client.callapi('gacha/exec', {'gacha_id': gacha_id, 'gacha_times': 10,
                                                        'exchange_id': exchange_id, 'draw_type': 6,
                                                        'current_cost_num': 1, 'campaign_id': self.campaign_id})
        if 'reward_info_list' in temp:
            chara_list = ''
            for chara in temp['reward_info_list']:
                if chara['id'] == 90005:
                    chara_id = int(chara['exchange_data']['unit_id'])
                else:
                    chara_id = int(chara['id'])
                if chara['id'] != 90005 or chara['exchange_data']['rarity'] == '3':
                    chara_list += self.unit_id_dict[str(chara_id)] + '(3)，'
                else:
                    chara_list += self.unit_id_dict[str(chara_id)] + '，'
            print('  免费十连扭蛋结果为：' + str(chara_list) + '时间为' +
                  time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(temp['servertime'])) + '。')
        if 'prize_reward_info' in temp:
            prize_list = ''
            for prize in temp['prize_reward_info'].values():
                prize_list += str(prize['rarity']) + '，'
            print('  附奖等级为：' + str(prize_list))
        return True

    # 复刻池选取碎片（临时）
    async def gacha_select(self):
        temp = await self.client.callapi('gacha/select_prize', {'prizegacha_id': 100024, 'item_id': 31097})
        return temp

    # 抽取当期up
    async def gacha_up(self, gacha_total, gacha_id, exchange_id):
        check_up = -1
        temp = await self.client.callapi('gacha/exec', {'gacha_id': gacha_id, 'gacha_times': 10,
                                                        'exchange_id': exchange_id, 'draw_type': 2,
                                                        'current_cost_num': self.user_jewel + self.paid_jewel})
        if 'reward_info_list' in temp:
            self.user_jewel -= 1500
            chara_list = ''
            for chara in temp['reward_info_list']:
                if chara['id'] == 90005:
                    chara_id = int(chara['exchange_data']['unit_id'])
                else:
                    chara_id = chara['id']
                    if chara_id == 107001:
                        print('已抽到当期up')
                        check_up = 1
                chara_list += self.unit_id_dict[str(chara_id)] + '，'
        print('第' + str(gacha_total) + '次扭蛋结果为：' +
              str(chara_list) + '剩余免费钻' + str(self.user_jewel))
        return check_up

    # 抽取纪念券
    async def gacha_ticket(self):
        temp = await self.client.callapi('gacha/exec', {'gacha_id': 80005, 'gacha_times': 1, 'exchange_id': 0,
                                                        'draw_type': 9, 'current_cost_num': 1, 'campaign_id': 0})
        if 'reward_info_list' in temp:
            chara_list = ''
            for chara in temp['reward_info_list']:
                if chara['id'] == 90005:
                    chara_id = int(chara['exchange_data']['unit_id'])
                else:
                    chara_id = int(chara['id'])
                if chara['id'] != 90005:
                    chara_list += self.unit_id_dict[str(chara_id)] + '(new)'
                else:
                    chara_list += self.unit_id_dict[str(chara_id)] + ''
            print('纪念券扭蛋结果为：' + str(chara_list) + '时间为' +
                  time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(temp['servertime'])) + '。')

    # 地下城
    async def dungeon(self, donate_id):
        # 查询捐赠角色
        mem_list = []
        members = await self.client.callapi('clan/others_info', {'clan_id': self.clan_id})
        if 'clan' not in members:
            return False
        members = members['clan']['members']
        for mem in members:
            mem_list.append(mem['viewer_id'])
        # 选择捐献的id
        user_unit = [0, 0]
        if donate_id in mem_list:
            user_unit = [0, 0]
            profile = await self.client.callapi('/profile/get_profile', {'target_viewer_id': int(donate_id)})
            if 'clan_support_units' in profile:
                for unit in profile['clan_support_units']:
                    if unit['position'] < 3 and int(unit['unit_data']['unit_level']) > user_unit[1] and int(
                            unit['unit_data']['unit_level']) - self.team_level < 31:
                        # 添加角色id与等级
                        user_unit = [int(unit['unit_data']['id']), int(
                            unit['unit_data']['unit_level'])]
        if user_unit[1] == 0:
            return -1
        # 地下城流程
        temp = await self.client.callapi('dungeon/info', {})
        if 'rest_challenge_count' not in temp:
            return False
        dungeon = temp['enter_area_id']
        dungeon_rest = temp['rest_challenge_count'][0]['count']
        dungeon_id = 31001
        # dungeon_id = temp['dungeon_area'][0]['dungeon_area_ids'][0]
        # 如果已进入地下城, 直接撤退
        if dungeon:
            await self.client.callapi('dungeon/reset', {'dungeon_area_id': dungeon})
        await asyncio.sleep(2)

        if dungeon_rest:
            temp = await self.client.callapi('dungeon/enter_area', {'dungeon_area_id': dungeon_id})
            quest_id = int(temp['quest_id'])
            dispatch_unit_list = []
            temp1 = await self.client.callapi('dungeon/dispatch_unit_list_2', {'dungeon_area_id': dungeon_id})
            for unit in temp1['dispatch_unit_list']:
                dispatch_unit_list.append([unit['unit_data']['id'], unit['owner_viewer_id']])
            if [user_unit[0], donate_id] in dispatch_unit_list:
                await self.client.callapi('deck/update', {'deck_number': 4, 'unit_id_1': 1,
                                                          'unit_id_2': 0, 'unit_id_3': 0, 'unit_id_4': 0,
                                                          'unit_id_5': 0})
                temp3 = await self.client.callapi('dungeon/battle_start', {'quest_id': quest_id, 'unit_list': [
                    {'owner_viewer_id': donate_id, 'unit_id': user_unit[0]},
                    {'owner_viewer_id': self.viewer_id, 'unit_id': 0}, {
                        'owner_viewer_id': self.viewer_id, 'unit_id': 0},
                    {'owner_viewer_id': self.viewer_id, 'unit_id': 0},
                    {'owner_viewer_id': self.viewer_id, 'unit_id': 0}], 'disable_skin': 1, 'support_battle_rarity': 0})
                print('已捐赠给' + str(donate_id) + '角色' + unit_id_dict[str(user_unit[0])])
            if 'battle_log_id' in temp3:
                return 1
        return -1

    # 赛马
    async def chara_fortune(self):
        unit_id = self.fortune_unit_list[3]
        temp = await self.client.callapi('chara_fortune/draw', {'fortune_id': self.fortune_id, 'unit_id': unit_id})
        if 'reward_list' not in temp:
            return False
        print('赛马获得' + str(temp['reward_list'][0]['received']) + '钻')

    # 收取双场币
    async def arena_reward(self):
        temp = await self.client.callapi('arena/info', {})
        if 'reward_info' in temp:
            temp0 = await self.client.callapi('arena/time_reward_accept', {})
            if 'reward_info' in temp0:
                self.arena_coin = temp0['reward_info']['stock']
        temp = await self.client.callapi('grand_arena/info', {})
        if 'reward_info' in temp:
            temp0 = await self.client.callapi('grand_arena/time_reward_accept', {})
            if 'reward_info' in temp0:
                self.grand_arena_coin = temp0['reward_info']['stock']
        return True

    # 获取竞技场信息
    async def arena_info(self):
        temp = await self.client.callapi('arena/info', {})
        if 'arena_info' in temp:
            group_id = temp['arena_info']['group']
            print(str(self.viewer_id) + '所在竞技场组别为' + str(group_id))
        else:
            print(str(self.viewer_id) + '未进入竞技场')
        return True

    # 获取公主竞技场信息
    async def grand_arena_info(self):
        temp = await self.client.callapi('grand_arena/info', {})
        if 'grand_arena_info' in temp:
            group_id = temp['grand_arena_info']['group']
            print(str(self.viewer_id) + '所在公主竞技场组别为' + str(group_id))
        else:
            print(str(self.viewer_id) + '未进入公主竞技场')
        return True

    # 商店购买
    async def shop_item(self):
        temp = await self.client.callapi('shop/item_list', {})
        if 'shop_list' in temp:
            for shop in temp['shop_list']:
                if shop['system_id'] == 201:
                    gold_sold_out = shop['item_list'][0]['sold']
                if shop['system_id'] == 202:
                    arena_sold_out = shop['item_list'][5]['sold']
                if shop['system_id'] == 203:
                    grand_sold_out = shop['item_list'][2]['sold']
                if shop['system_id'] == 204:
                    tower_sold_out = shop['item_list'][4]['sold']
                if shop['system_id'] == 205:
                    clan_sold_out = shop['item_list'][3]['sold']
        if self.gold > 50000000 and not gold_sold_out:
            buy_data = await self.client.callapi(
                'shop/buy_multiple', {'system_id': 201, 'slot_ids': [1, 2, 3, 4], 'current_currency_num': self.gold})
            if 'purchase_list' in buy_data:
                print("  购买特级药水" +
                      str(buy_data['purchase_list'][0]['received']) + '瓶')
        if self.tower_coin > 800 and not tower_sold_out:
            buy_data = await self.client.callapi(
                'shop/buy_multiple', {'system_id': 204, 'slot_ids': [5], 'current_currency_num': self.tower_coin})
            if 'purchase_list' in buy_data:
                print("  购买黄骑碎片" +
                      str(buy_data['purchase_list'][0]['received']) + '片')
        if self.arena_coin > 800 and not arena_sold_out:
            buy_data = await self.client.callapi(
                'shop/buy_multiple', {'system_id': 202, 'slot_ids': [6], 'current_currency_num': self.arena_coin})
            if 'purchase_list' in buy_data:
                print("  购买莫妮卡碎片" +
                      str(buy_data['purchase_list'][0]['received']) + '片')
        if self.grand_arena_coin > 800 and not grand_sold_out:
            buy_data = await self.client.callapi('shop/buy_multiple', {'system_id': 203, 'slot_ids': [
                3], 'current_currency_num': self.grand_arena_coin})
            if 'purchase_list' in buy_data:
                print("  购买布丁碎片" +
                      str(buy_data['purchase_list'][0]['received']) + '片')
        if self.clan_battle_coin > 800 and not clan_sold_out:
            buy_data = await self.client.callapi('shop/buy_multiple', {'system_id': 205, 'slot_ids': [
                4], 'current_currency_num': self.clan_battle_coin})
            if 'purchase_list' in buy_data:
                print("  购买真琴碎片" +
                      str(buy_data['purchase_list'][0]['received']) + '片')
        return True

    # 查box
    async def check_box(self, chara_id):
        if chara_id in self.unit_list:
            print(str(self.viewer_id) + '已抽到' + self.unit_id_dict[str(chara_id)])
            return -1
        else:
            print(str(self.viewer_id) + '未抽到')
            return 1

    async def exchange_gacha(self, exchange_id):
        temp = await self.client.callapi(
            'gacha/exchange_point', {'exchange_id': exchange_id, 'unit_id': 107001, 'current_point': 300})
        if 'reward_info_list' in temp:
            print('   已交换')
        return True

    # 升级家具
    async def room_up(self):
        temp = await self.client.callapi('room/start', {})
        if 'user_room_item_list' in temp:
            item_level_str = '，家具等级为：'
            for item in temp['user_room_item_list']:
                for serial_id in range(4, 8):  # 4:扫荡券, 5:体力, 6:药剂, 7:玛娜
                    if item['serial_id'] == serial_id:
                        item_level_str += str(item['room_item_level']) + ','
                        # 如果家具等级过低，进行升级
                        if item['room_item_level'] < self.room_item_level:
                            temp1 = await self.client.callapi(
                                'room/level_up_start', {'floor_number': 1, 'serial_id': serial_id})
                            print('  升级家具' + str(serial_id))
            print('  已进入小屋,时间为' + time.strftime("%Y-%m-%d %H:%M:%S",
                                                        time.localtime()) + item_level_str[:-1])
        await asyncio.sleep(2)

    # 霸瞳活动
    async def kaiser_battle(self):
        temp = await self.client.callapi('kaiser_battle/top', {})
        jewel_accept = 0
        if 'sub_boss_reward' in temp:
            for reward in temp['sub_boss_reward']:
                if int(reward['id']) == 91002:
                    jewel_accept += int(reward['count'])
        print('    活动已获得钻石' + str(jewel_accept))
        return True

    # 主线任务与称号收取
    async def mission_plus(self):
        temp = await self.client.callapi('mission/accept', {'type': 2, 'id': 0, 'buy_id': 0})
        jewel_accept = 0
        if 'rewards' in temp:
            for reward in temp['rewards']:
                if int(reward['id']) == 91002:
                    jewel_accept += int(reward['count'])
        print('    任务已获得钻石' + str(jewel_accept))
        await asyncio.sleep(2)
        await self.client.callapi('mission/accept', {'type': 4, 'id': 0, 'buy_id': 0})
        await asyncio.sleep(2)
        return True

    # 女神祭
    async def season_ticket(self):
        temp = await self.client.callapi('season_ticket_new/index', {'season_id': 10002})
        if 'missions' in temp:
            temp1 = await self.client.callapi('season_ticket_new/accept', {'season_id': 10002, 'mission_id': 0})
            if 'seasonpass_level' in temp1:
                print('    当前女神祭解锁等级为' + str(temp1['seasonpass_level']))
        return True

    # 女神祭收取
    async def season_ticket_reward(self):
        if 'season_ticket' in self.home:
            level = self.home['season_ticket']['seasonpass_level']
            print('    女神祭等级为' + str(level))
            temp = await self.client.callapi(
                'season_ticket_new/reward', {'season_id': 10002, 'level': 0, 'index': 0})
            if 'received_rewards' in temp:
                print('    已收取女神祭等级' + str(temp['received_rewards']))
        return True

    async def check_equip_num(self):
        for equip in self.load['user_equip']:
            if equip['id'] == 115192:
                print(str(self.viewer_id)+'碎片数'+str(equip['stock']))

    # 地下城跳过
    async def dungeon_sweep(self, mode: str):  # enum("passed", "max")
        if mode == "disabled":
            return
        dungeon_name = {
            31001: "云海的山脉",
            31002: "密林的大树",
            31003: "断崖的遗迹",
            31004: "沧海的孤塔",
            31005: "毒瘴的暗棱",
            31006: "绿龙的骸岭",
            31007: "天上的浮城"
        }
        try:
            data = await self.client.callapi("/dungeon/info", {})
            enter_area_id = data["enter_area_id"]
            rest_challenge_count = [x["count"] for x in data["rest_challenge_count"] if x["dungeon_type"] == 1][0]
            dungeon_cleared_area_id_list = data.get("dungeon_cleared_area_id_list", [])
        except Exception as e:
            return f'Fail. 获取今日地下城状态失败：{e}'
        if enter_area_id != 0:
            msg = [f'当前已位于地下城 {dungeon_name.get(enter_area_id, enter_area_id)}']
            if enter_area_id in dungeon_cleared_area_id_list:
                try:
                    res = await self.client.callapi("/dungeon/skip", {"dungeon_area_id": enter_area_id})
                except Exception as e:
                    msg.append(f'Fail. 尝试扫荡失败：{e}')
                else:
                    msg.append(f'Succeed. 扫荡成功')
            else:
                msg.append(f'Warn. 您尚未通关过该等级，无法扫荡。')
            return " ".join(msg)
        if rest_challenge_count == 0:
            return f'Skip. 今日地下城已挑战完毕'
        if len(dungeon_cleared_area_id_list) == 0:
            return f'Skip. 您未通关任何地下城地图'
        if mode not in ["passed", "max"]:
            return f'Warn. 无法识别的mode：{mode}'
        if mode == "max":
            max_dungeon_id = max(dungeon_name.keys())
            if max_dungeon_id not in dungeon_cleared_area_id_list:
                return f'Warn. 您设置仅尝试扫荡当前开放的最高等级地下城({dungeon_name[max_dungeon_id]})，但尚未通关。'

        dungeon_area_id = max(dungeon_cleared_area_id_list)
        dungeon_area_name = dungeon_name.get(dungeon_area_id, dungeon_area_id)

        try:
            res = await self.client.callapi("/dungeon/skip", {"dungeon_area_id": dungeon_area_id})
        except Exception as e:
            return f'Fail. 尝试扫荡地下城 {dungeon_area_name} 失败：{e}'
        return f'Succeed. 扫荡地下城 {dungeon_area_name} 成功'

    # 查box
    async def get_box(self):
        """
        {
            1001: {...}
            ...,
            1137: {                         # 以下字段的value为拼凑而成，主要作说明用
            "id": 113701,                   # 六位id
            "unit_rarity": 3,               # 星级
            "battle_rarity": 0,             # 当前设定星级，0表示为默认星级
            "unit_level": 184,              # 等级
            "promotion_level": 4,           # 好感度
            "promotion_level_actual": 0,    # 实际已阅读的剧情数
            "unit_exp": 5583000,            # 角色当前经验值
            "get_time": 1665408176,         # 角色获取时间
            "union_burst": [{"skill_id": 1137001, "skill_level": 184}], # 注意是list
            "main_skill": [{"skill_id": 117002, "skill_level": 184}, {"skill_id": 1137003, "skill_level": 4}],
            "ex_skill": [{"skill_id": 1059511, "skill_level": 172}],    # 注意是list
            "free_skill": [],
            "equip_slot": [
                {"id": 999999, "is_slot": 0, "enhancement_level": 0, "enhancement_pt": 0}, # 999999表示当前未实装的装备
                {"id": 103221, "is_slot": 0, "enhancement_level": 0, "enhancement_pt": 0},
                {"id": 103521, "is_slot": 1, "enhancement_level": 1, "enhancement_pt": 60},
                {"id": 103521, "is_slot": 0, "enhancement_level": 0, "enhancement_pt": 0},
                {"id": 102613, "is_slot": 1, "enhancement_level": 1, "enhancement_pt": 20},
                {"id": 102613, "is_slot": 1, "enhancement_level": 1, "enhancement_pt": 20}
            ],
            "unique_equip_slot": [{"id": 130911, "is_slot": 1, "enhancement_level": 160, "enhancement_pt": 19990, "rank": 9}], # 注意是list；为空表示游戏未实装该角色专武；不为空但"is_slot"==0表示用户未装专武
            "unlock_rarity_6_item": {"slot_1": 0, "slot_2": 1, "slot_3": 5}, # 只有5x待开花角色才有此字段。
            # slot_1==纯净记忆碎片是否安装(1/0)；slot_2==记忆碎片是否安装(1/0)；slot_3==星球杯强化([0,5])
            "power": 9181, # 战力
            "skin_data": {"icon_skin_id": 0, "sd_skin_id": 0, "still_skin_id": 0, "motion_id": 0},
            "favorite_flag": 0 # 是否置为收藏角色
            },
            ...
        }
        """
        load_index = self.load
        box = {}
        for unit in load_index["unit_list"]:  # unit:dict
            unit.pop(None, None)
            for entry in ["union_burst", "main_skill", "ex_skill"]:
                for x in unit.get(entry, []):
                    x.pop(None, None)
            unit_id = unit["id"] // 100
            box[unit_id] = unit
            box[unit_id]["promotion_level_actual"] = 0

        for story_id in load_index["read_story_ids"]:
            unit_id = story_id // 1000
            if unit_id > 2000:
                break
            if unit_id not in box:
                continue
            love = story_id % 1000
            box[unit_id]["promotion_level_actual"] = max(box[unit_id]["promotion_level_actual"], love)
        return box

    async def get_item_dict(self):
        """
        :returns: {id(int): stock(int)}
        """
        await self.load_index(requery=True)
        item_list = self.load["item_list"]
        item_dic = {}
        for item in item_list:
            item_dic[item["id"]] = item["stock"]
        return item_dic

    async def get_item_stock(self, item_id: int):
        """
        :param id: 五位数
        :returns: {id(int): stock(int)}
        """
        dic = await self.get_item_dict()
        return dic.get(int(item_id), 0)

    async def get_new_event_id_list(self, event_id_list):
        '''
        返回的活动列表中将过滤掉复刻活动，且新活动按从新到旧排序
        '''

        import datetime
        from os.path import dirname, join, exists
        from json import dump
        def getNowtime() -> int:
            return int(datetime.datetime.timestamp(datetime.datetime.now()))
        curpath = dirname(__file__)
        cache_path = join(curpath, "new_event_list.json")
        if exists(cache_path):
            with open(cache_path, "r", encoding="utf-8") as fp:
                cache = load(fp)
                if getNowtime() - cache.get("time", 0) < 3600:
                    if len(cache.get("new_event_id_list", [])):
                        return cache["new_event_id_list"]

        story_id_list = [-1] * len(event_id_list)
        for i, event_id in enumerate(event_id_list):
            try:
                data = await self.client.callapi("/event/hatsune/top", {"event_id": event_id})
                if data.get("opening", {}).get("story_id", 0):
                    story_id_list[i] = int(data["opening"]["story_id"]) // 1000 % 100
                elif len(data.get("stories", [])):
                    story_id_list[i] = int(data["stories"][0].get("story_id", 0)) // 1000 % 100
            except Exception as e:
                raise Exception(f'Fail. 获取活动{event_id}信息失败：{e}')

        ew_list = sorted(zip(event_id_list, story_id_list), key=lambda x: x[1], reverse=True)
        new_event_id_list = [ew[0] for ew in ew_list if ew_list[0][1] - ew[1] < 5]

        with open(cache_path, "w", encoding="utf-8") as fp:
            dump({"new_event_id_list": new_event_id_list, "time": getNowtime()}, fp, ensure_ascii=False, indent=4)

        return new_event_id_list

    async def get_event_id_list(self, sweep_type: str = "all", only_open: bool = True, return_close_msg: bool = False):
        '''
        sweep_type: enum("old", "new", "all")
        return event_id_list:List[int], msg:List[str]
        '''

        event_id_list = []
        msg = []

        try:
            for event in self.load["event_statuses"]:
                if event["event_type"] == 1:
                    if only_open:
                        if event["period"] == 2:
                            event_id_list.append(event["event_id"])
                        else:
                            msg.append(f'活动{event["event_id"]}未开放')
                    else:
                        event_id_list.append(event["event_id"])

        except Exception as e:
            raise Exception(f'Fail. 获取当前活动列表失败：{e}')

        if not event_id_list:
            raise Exception("Abort. 当前无开放的活动")

        if sweep_type != "all":
            new_event_id_list = await self.get_new_event_id_list(event_id_list)
            old_event_id_list = list(set(event_id_list) - set(new_event_id_list))
            if len(new_event_id_list) and len(old_event_id_list):
                if sweep_type == "new":
                    event_id_list = new_event_id_list
                elif sweep_type == "old":
                    event_id_list = old_event_id_list

        return event_id_list, msg if return_close_msg else []

    async def buy_exp(self):
        exp_id2name = {
            20001: "迷你经验药剂",
            20002: "经验药剂",
            20003: "高级经验药剂",
            20004: "超级经验药剂"
        }

        try:
            data = await self.client.callapi("/shop/item_list")
            shop_list = data["shop_list"]
            mana_shop = list(filter(lambda x: x["system_id"] == 201, shop_list))[0]
            mana_shop = mana_shop["item_list"]  # list
        except Exception as e:
            return f'Fail. 获取商店物品失败：{e}'
        slot = []
        for item in mana_shop:
            if int(item["sold"]) == 0 and int(item["item_id"]) in exp_id2name:  # 逆天pcr有时候返回int有时候返回string
                slot.append(item["slot_id"])
        if slot == []:
            return f'Skip. 已购买通常商店所有经验瓶，请等待下次刷新。'
        try:
            ret = await self.client.callapi("/shop/buy_multiple", {
                    "system_id": 201,
                    "slot_ids": slot,
                    "current_currency_num": self.gold
                })
        except Exception as e:
            print(f'Fail. 商店购买经验瓶失败：{e}')
            return 0
        try:
            outp = []
            purchase_list = sorted(ret["purchase_list"], key=lambda x: x["id"])
            for dic in purchase_list:
                outp.append(f'{exp_id2name[int(dic["id"])]}{int(dic["stock"]) - int(dic["received"])}->{dic["stock"]}')
        except Exception as e:
            print(f'Succeed. 商店购买经验瓶成功，但获取购买结果失败：{e}')

        print(f'Succeed. 购买当期通常商店所有经验瓶成功：{" ".join(outp)}')

    async def get_user_equip_dict(self) -> dict:
        """
        :returns: {id(int): stock(int)}
        """
        await self.load_index(True)
        user_equip_list = self.load["user_equip"]
        user_equip_dict = {}
        for equip in user_equip_list:
            user_equip_dict[equip["id"]] = equip["stock"]
        return user_equip_dict

    async def get_user_equip_stock(self, id: int) -> int:
        """
        :param id: 六位数，1打头
        :returns: {id(int): stock(int)}
        """
        dic = await self.get_user_equip_dict()
        return dic.get(int(id), 0)

    async def buy_shop(self, cnt, buy_chara_frag, buy_equip_frag, shop_name, shop_id, coin_id, chara_coin_threshold, equip_coin_threshold, equip_cnt_threshold):
        '''
        暂不支持刷角色碎片，因为从shop/item_list中看不出是否可以购买
        '''
        if buy_chara_frag == False and buy_equip_frag == False:
            return f'Warn. 您开启了{shop_name}商店购买，但未选择购买任何类型的物品（角色碎片或装备碎片）'

        try:
            data = await self.client.callapi("/shop/item_list", {})
            shop_list = data["shop_list"]
            target_shop = list(filter(lambda x: x["system_id"] == shop_id, shop_list))[0]  # dict # 地下城204 JJC币202 PJJC币203
            already_buy_cnt = target_shop["reset_count"]  # 获取的是重置次数，因此即使今日已触发过地下城购买，依然会比cnt的值小1
        except Exception as e:
            return f'Fail. 获取今日重置{shop_name}商店次数失败：{e}'
        if already_buy_cnt == cnt - 1 and cnt > 1:
            return f'Skip. 今日已购买{already_buy_cnt + 1}次{shop_name}商店'
        if already_buy_cnt >= cnt:
            return f'Skip. 今日已重置{already_buy_cnt}次{shop_name}商店'

        try:
            for item in self.load['item_list']:
                if item['id'] == coin_id:  # 地下城币90002 竞技场币90003 公主竞技场币90004
                    shop_coin = item['stock']
            shop_coin_old = shop_coin
        except Exception as e:
            return f'Fail. 获取{shop_name}币数量失败：{e}'

        msg = []

        bought_equip_frag = {}

        class abort(Exception):
            pass
        try:
            for i in range(already_buy_cnt, cnt):
                # print(f'\n第{i+1}次购买 当前{shop_name}币={shop_coin}')  # test
                if shop_coin < chara_coin_threshold:
                    msg.append(f'Abort. {shop_name}币数量{shop_coin}低于阈值{chara_coin_threshold}，不执行购买')
                    raise abort(i)
                if shop_coin < equip_coin_threshold and buy_equip_frag:
                    if buy_chara_frag == False:
                        msg.append(f'Abort. {shop_name}币数量{shop_coin}低于阈值{equip_coin_threshold}，不执行购买')
                        raise abort(i)
                    msg.append(f'Warn. {shop_name}币数量{shop_coin}高于角色碎片购买阈值{chara_coin_threshold}但低于装备碎片购买阈值{equip_coin_threshold}，将仅购买角色碎片。')
                    buy_equip_frag = False
                try:
                    target_shop = target_shop["item_list"]  # List[Dict]
                except Exception as e:
                    return f'Fail. 获取{shop_name}商品列表失败：{e}'
                slot = []
                for item in target_shop:
                    if int(item.get("sold", "1")) != 0:
                        continue
                    item_id_str = str(item.get("item_id", 0))
                    if buy_equip_frag:
                        # "type" == 4 | "item_id" == 10xxxxx: 整装
                        # "type" == 4 | "item_id" == 11xxxxx/12xxxx: 装备碎片
                        if int(item.get("type", -1)) == 4 and len(item_id_str) == 6 and item_id_str[1] != "0":  # 是装备碎片
                            equip_id_str = f'10{item_id_str[2:]}'
                            try:
                                stock = await self.get_user_equip_stock(int(item_id_str))
                            except Exception as e:
                                msg.append(f'Abort. 获取{equip2name.get(equip_id_str, equip_id_str)}({item_id_str})存量失败：{e}')
                                raise abort(i)

                            # print(f'slot={item["slot_id"]:2d} item_id={item_id_str} stock={stock:5d} equip_name={equip2name.get(equip_id_str, equip_id_str)} ')  # test
                            if stock < equip_cnt_threshold:
                                try:
                                    slot.append(int(item["slot_id"]))
                                except Exception as e:
                                    msg.append(f'Abort. 尝试将{equip2name.get(equip_id_str, equip_id_str)}({item_id_str})加入购买列表失败：{e}')
                                    raise abort(i)
                    if buy_chara_frag:
                        # "type" == 2 | "item_id" == 3xxxx：角色碎片
                        if int(item.get("type", -1)) == 2 and len(item_id_str) == 5 and item_id_str[0] == "3":  # 是角色碎片
                            pass
                            # 暂不支持刷角色碎片，因为从shop/item_list中看不出是否可以购买
                            # 角色碎片会有一个available_num，表示当前你总共可以持有的碎片数。该数量为角色从1x到5x/6x、满专（若有专），所需的总碎片数。
                            # 若想要实装，需要一个计算模块，根据该角色当前星级、专武、开6x时是否已装入碎片、当前拥有碎片数量，来计算actual_num。
                            # 若actual_num < available_num 则可购买

                slot = list(set(slot))
                # print(f'选择购买的slot：{slot if len(slot) else "无"}')  # test
                if len(slot):
                    try:  # 购买
                        ret = await self.client.callapi("/shop/buy_multiple", {
                                "system_id": shop_id,
                                "slot_ids": slot,
                                "current_currency_num": shop_coin
                            })
                    except Exception as e:
                        msg.append(f'Abort. 购买失败：{e}')
                        raise abort(i)
                    try:
                        for item in ret["purchase_list"]:  # 维护购买列表
                            item_id_str = f'10{str(item["id"])[2:]}'
                            bought_equip_frag[item_id_str] = bought_equip_frag.get(item_id_str, 0) + int(item["received"])
                        # print(f'购买花费：{shop_coin - int(ret["item_data"][0]["stock"])}')  # test
                        shop_coin = int(ret["item_data"][0]["stock"])
                    except Exception as e:
                        msg.append(f'Abort. 获取购买结果失败：{e}')
                        raise abort(i)

                if i == cnt - 1:  # 最后一次循环不需要浪费{shop_name}币去刷新
                    if len(bought_equip_frag) == 0 and cnt == 1 and already_buy_cnt == 0:
                        return f'Skip. 未购买任何商品'
                    msg.append(f'Succeed. 实际购买{cnt-already_buy_cnt}次 今日共购买{cnt}次')
                else:  # 刷新{shop_name}
                    try:
                        data = await self.client.callapi("/shop/reset", {"system_id": shop_id, "current_currency_num": shop_coin})
                        # print(f'重置花费：{data["shop"]["reset_cost"]}')  # test
                        shop_coin = int(data["item_data"][0]["stock"])
                        target_shop = data["shop"]
                        # shop_coin -= target_shop["reset_cost"]
                    except Exception as e:
                        msg.append(f'Abort. 刷新{shop_name}失败：{e}')
                        raise abort(i)
        except abort as e:
            e = int(str(e))
            msg.append(f'本次触发第{e-already_buy_cnt+1}次 今日共计第{e+1}次')

        bought_equip_frag_outp = []
        if len(bought_equip_frag):
            bought_equip_frag_outp.append(f'共花费{shop_coin_old - shop_coin}{shop_name}币 购得物品：')
            bought_equip_frag = list(sorted(bought_equip_frag.items(), key=lambda x: x[0], reverse=True))
            for item in bought_equip_frag:
                bought_equip_frag_outp.append(f'{equip2name.get(item[0], item[0])}*{item[1]}')

        return '\n'.join(msg) + '\n' + '\n'.join(bought_equip_frag_outp)

    async def buy_jjc_shop(self, cnt=4, buy_chara_frag=False, buy_equip_frag=True):
        return await self.buy_shop(cnt, buy_chara_frag, buy_equip_frag, "竞技场", 202, 90003, 20000, 50000, 300)

    async def buy_pjjc_shop(self, cnt=4, buy_chara_frag=False, buy_equip_frag=True):
        return await self.buy_shop(cnt, buy_chara_frag, buy_equip_frag, "公主", 203, 90004, 20000, 50000, 300)

    async def buy_dungeon_shop(self, cnt=7, buy_chara_frag=False, buy_equip_frag=True):
        return await self.buy_shop(cnt, buy_chara_frag, buy_equip_frag, "地下城", 204, 90002, 50000, 100000, 300)
