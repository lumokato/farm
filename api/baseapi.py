from .pcrclient import PCRClient
import time
from json import load


with open('account.json', encoding='utf-8') as fp:
    total_api = load(fp)

with open('unit_id.json', encoding='utf-8') as fp:
    unit_id_dict = load(fp)


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
        self.load, self.home = self.client.login(uid, access_key)
        self.home_index()
        self.unit_id_dict = unit_id_dict
        # print('已登录账号'+str(viewer_id))

    # 账号基本信息
    def load_index(self):
        self.tower_coin = self.arena_coin = self.grand_arena_coin = self.clan_battle_coin = 0   # 初始化
        self.load = self.client.callapi("load/index", {"carrier": "google"})
        self.user_stamina = self.load['user_info']['user_stamina']
        self.viewer_id = self.load['user_info']['viewer_id']
        self.clan_like = self.load['clan_like_count']   # 0为未点赞，1为已点赞
        for item in self.load['item_list']:
            if item['id'] == 23001:     # 扫荡券
                self.num_ticket = item['stock']
            elif item['id'] == 90002:   # 地下城币
                self.tower_coin = item['stock']
            elif item['id'] == 90003:   # 竞技场币
                self.arena_coin = item['stock']
            elif item['id'] == 90004:   # 公主竞技场币
                self.grand_arena_coin = item['stock']
            elif item['id'] == 90006:   # 会战币
                self.clan_battle_coin = item['stock']
        self.gold = self.load['user_gold']['gold_id_free']  # 玛那数
        self.user_jewel = self.load['user_jewel']['free_jewel']
        self.paid_jewel = self.load['user_jewel']['paid_jewel']
        self.recovery = self.load['shop']['recover_stamina']['exec_count']
        self.free_gacha_time = self.load['can_free_gacha']
        self.compaign_gacha_time = self.load['can_campaign_gacha']
        self.team_level = self.load['user_info']['team_level']
        self.room_item_level = int(self.team_level/10) + 1
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
            self.chara_fortune()
        self.unit_list = []
        for unit in self.load['unit_list']:
            self.unit_list.append(unit['id'])
        self.read_story_ids = self.load['read_story_ids']

    # 账号推图完成情况
    def home_index(self):
        self.home = self.client.callapi("home/index", {'message_id': 1, 'tips_id_list': [], 'is_first': 1, 'gold_history': 0})
        self.quest_dict = {}
        for quest in self.home['quest_list']:
            if quest['clear_flg'] == 3 and quest['result_type'] == 2:
                self.quest_dict[quest['quest_id']] = quest['daily_clear_count']
        self.gold_quest = self.home['training_quest_count']['gold_quest']
        self.clan_id = self.home['user_clan']['clan_id']
        self.donation_num = self.home['user_clan']['donation_num']
        self.exp_quest = self.home['training_quest_count']['exp_quest']
        # 地下城进入情况与剩余次数
        self.dungeon_enter = self.home['dungeon_info']['enter_area_id']
        self.dungeon_rest = self.home['dungeon_info']['rest_challenge_count'][0]['count']
        # print(self.dungeon_enter, self.dungeon_rest)

    # 行会聊天室
    def chat_monitor(self):
        temp = self.client.callapi('clan/chat_info_list', {'clan_id': self.clan_id, 'start_message_id': 0,
                                                           'search_date': '2099-12-31', 'direction': 1, 'count': 10, 'wait_interval': 3, 'update_message_ids': []})
        if 'users' not in temp:
            self.client.login(self.uid, self.access_key)
            temp = self.client.callapi('clan/chat_info_list', {'clan_id': self.clan_id, 'start_message_id': 0,
                                                               'search_date': '2099-12-31', 'direction': 1, 'count': 10, 'wait_interval': 3, 'update_message_ids': []})
        return temp

    # 点赞
    def like(self, clan_id: int, viewer_id: int):
        temp = self.client.callapi(
            'clan/like', {'clan_id': clan_id, 'target_viewer_id': viewer_id})
        if 'stamina_info' not in temp:
            self.client.login(self.uid, self.access_key)
            temp = self.client.callapi(
                'clan/like', {'clan_id': clan_id, 'target_viewer_id': viewer_id})
        # return temp['stamina_info']['user_stamina']

    # 任务查看与收取
    def mission(self):
        temp = self.client.callapi(
            'mission/index', {'request_flag': {'quest_clear_rank': 0}})
        if 'missions' not in temp:
            self.client.login(self.uid, self.access_key)
            temp = self.client.callapi(
                'mission/index', {'request_flag': {'quest_clear_rank': 0}})
        time.sleep(4)
        wait_accept = 0
        for mission in temp['missions'].keys():
            if mission is not None:
                if temp['missions'][mission]['mission_status'] == 1:
                    wait_accept = 1
                    break
        if wait_accept:
            temp1 = self.client.callapi(
                'mission/accept', {'type': 1, 'id': 0, 'buy_id': 0})
            if 'rewards' not in temp1:
                self.client.login(self.uid, self.access_key)
                temp1 = self.client.callapi(
                    'mission/accept', {'type': 1, 'id': 0, 'buy_id': 0})
            time.sleep(3)

    # 礼物查看与收取
    def present(self):
        temp = self.client.callapi(
            'present/index', {'time_filter': -1, 'type_filter': 0, 'desc_flag': True, 'offset': 0})
        if 'present_info_list' not in temp:
            self.client.login(self.uid, self.access_key)
            temp = self.client.callapi(
                'present/index', {'time_filter': -1, 'type_filter': 0, 'desc_flag': True, 'offset': 0})
        time.sleep(3)
        if len(temp['present_info_list']):
            temp1 = self.client.callapi(
                'present/receive_all', {'time_filter': -1, 'type_filter': 0, 'desc_flag': True})
            if 'rewards' not in temp1:
                self.client.login(self.uid, self.access_key)
                temp1 = self.client.callapi(
                    'present/receive_all', {'time_filter': -1, 'type_filter': 0, 'desc_flag': True})
            print('  已收取礼物')
            time.sleep(4)

    # 进入公会小屋，收取体力
    def room(self):
        if self.viewer_id == 1423390712318:
            print('账号'+str(self.viewer_id)+'跳过小屋,账号等级为'+str(self.team_level)+',免费钻量'+str(self.user_jewel)+',时间为'+time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()))
            return 0
        temp = self.client.callapi('room/start', {})
        if 'user_room_item_list' in temp:
            for item in temp['user_room_item_list']:
                for serial_id in range(4, 8):   # 4:扫荡券, 5:体力, 6:药剂, 7:玛娜
                    if item['serial_id'] == serial_id:
                        # 如果家具等级过低，进行升级
                        if item['room_item_level'] < self.room_item_level:
                            temp1 = self.client.callapi(
                                'room/level_up_start', {'floor_number': 1, 'serial_id': serial_id})
                            print('  升级家具' + str(serial_id))
            print('账号'+str(self.viewer_id)+'已进入小屋,账号等级为'+str(self.team_level)+',免费钻量'+str(self.user_jewel)+',时间为'+time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()))
            # print('账号'+str(self.viewer_id)+'已进入小屋,时间为'+time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()))
        time.sleep(2)
        temp1 = self.client.callapi('room/receive_all', {})
        if 'reward_list' in temp1:
            for item in temp1['reward_list']:
                if item['id'] == 23001:     # 扫荡券
                    self.num_ticket = item['stock']
                if item['id'] == 93001:     # 体力
                    self.user_stamina = item['stock']
        time.sleep(3)

    # 免费扭蛋
    def gacha(self):
        temp = self.client.callapi('gacha/index', {})
        if 'gacha_info' not in temp:
            self.client.login(self.uid, self.access_key)
            temp = self.client.callapi('gacha/index', {})
        for gacha in temp['gacha_info']:
            if gacha['id'] < 20000:
                free_gacha_id = gacha['id']
            # 公主祭典id为500xx
            if gacha['id'] > 30000 and gacha['id'] < 70000:
                campaign_gacha_id = gacha['id']
                exchange_id = gacha['exchange_id']
        if 'campaign_info' in temp:
            self.campaign_id = temp['campaign_info']['campaign_id']
        if self.free_gacha_time:
            temp = self.client.callapi('gacha/exec', {'gacha_id': free_gacha_id, 'gacha_times': 10,
                                                      'exchange_id': 0, 'draw_type': 1, 'current_cost_num': -1, 'campaign_id': 0})
        time.sleep(2)
        if self.compaign_gacha_time:
            self.gacha_compaign(campaign_gacha_id, exchange_id)

    # 地下城
    def dungeon(self, donate_id):
        # 查询捐赠角色
        mem_list = []
        members = self.client.callapi(
            'clan/others_info', {'clan_id': self.clan_id})['clan']['members']
        for mem in members:
            mem_list.append(mem['viewer_id'])
        # 选择捐献的id
        user_unit = [0, 0]
        if donate_id in mem_list:
            user_unit = [0, 0]
            profile = self.client.callapi('/profile/get_profile', {'target_viewer_id': int(donate_id)})
            if 'clan_support_units' in profile:
                for unit in profile['clan_support_units']:
                    if unit['position'] < 3 and int(unit['unit_data']['unit_level']) > user_unit[1] and int(unit['unit_data']['unit_level']) - self.team_level < 31:
                        # 添加角色id与等级
                        user_unit = [int(unit['unit_data']['id']), int(unit['unit_data']['unit_level'])]
        if user_unit[1] == 0:
            return False
        # 地下城流程
        temp = self.client.callapi('dungeon/info', {})
        if 'dungeon_area' not in temp:
            self.client.login(self.uid, self.access_key)
            temp = self.client.callapi('dungeon/info', {})
        dungeon = temp['enter_area_id']
        dungeon_rest = temp['rest_challenge_count'][0]['count']
        dungeon_id = temp['dungeon_area'][0]['dungeon_area_ids'][0]
        # 如果已进入地下城, 直接撤退
        if dungeon:
            self.client.callapi('dungeon/reset', {'dungeon_area_id': dungeon})

        time.sleep(2)
        if dungeon_rest:
            temp = self.client.callapi(
                'dungeon/enter_area', {'dungeon_area_id': dungeon_id})
            quest_id = int(temp['quest_id'])
            dispatch_unit_list = []
            temp1 = self.client.callapi(
                'dungeon/dispatch_unit_list_2', {'dungeon_area_id': dungeon_id})
            for unit in temp1['dispatch_unit_list']:
                dispatch_unit_list.append(
                    [unit['unit_data']['id'], unit['owner_viewer_id']])
            if [user_unit[0], donate_id] in dispatch_unit_list:
                self.client.callapi(
                    'deck/update', {'deck_number': 4, 'unit_id_1': 1, 'unit_id_2': 0, 'unit_id_3': 0, 'unit_id_4': 0, 'unit_id_5': 0})
                temp3 = self.client.callapi('dungeon/battle_start', {'quest_id': quest_id, 'unit_list': [{'owner_viewer_id': donate_id, 'unit_id': user_unit[0]}, {'owner_viewer_id': self.viewer_id, 'unit_id': 0}, {
                                            'owner_viewer_id': self.viewer_id, 'unit_id': 0}, {'owner_viewer_id': self.viewer_id, 'unit_id': 0}, {'owner_viewer_id': self.viewer_id, 'unit_id': 0}], 'disable_skin': 1, 'support_battle_rarity': 0})
                print('已捐赠给'+str(donate_id)+'角色'+unit_id_dict[str(user_unit[0])])
            if 'battle_log_id' in temp3:
                return True
                # self.client.callapi('dungeon/reset', {'dungeon_area_id': dungeon_id})
            return False

    # 赛马
    def chara_fortune(self):
        unit_id = self.fortune_unit_list[0]
        temp = self.client.callapi(
            'chara_fortune/draw', {'fortune_id': self.fortune_id, 'unit_id': unit_id})
        if 'reward_list' not in temp:
            self.client.login(self.uid, self.access_key)
            temp = self.client.callapi(
                'chara_fortune/draw', {'fortune_id': self.fortune_id, 'unit_id': unit_id})
        print('赛马获得'+str(temp['reward_list'][0]['received'])+'钻')

    # 收取双场币
    def arena_reward(self):
        temp = self.client.callapi('arena/info', {})
        if 'reward_info' in temp:
            temp0 = self.client.callapi('arena/time_reward_accept', {})
            if 'reward_info' in temp0:
                self.arena_coin = temp0['reward_info']['stock']
        temp = self.client.callapi('grand_arena/info', {})
        if 'reward_info' in temp:
            temp0 = self.client.callapi('grand_arena/time_reward_accept', {})
            if 'reward_info' in temp0:
                self.grand_arena_coin = temp0['reward_info']['stock']

    # 获取竞技场信息
    def arena_info(self):
        temp = self.client.callapi('arena/info', {})
        if 'arena_info' in temp:
            group_id = temp['arena_info']['group']
            print(str(self.viewer_id) + '所在竞技场组别为' + str(group_id))
        else:
            print(str(self.viewer_id) + '未进入竞技场')

    # 获取公主竞技场信息
    def grand_arena_info(self):
        temp = self.client.callapi('grand_arena/info', {})
        if 'grand_arena_info' in temp:
            group_id = temp['grand_arena_info']['group']
            print(str(self.viewer_id) + '所在公主竞技场组别为' + str(group_id))
        else:
            print(str(self.viewer_id) + '未进入公主竞技场')

    # 获取公主竞技场排名
    def grand_arena_ranking(self):
        temp = self.client.callapi('grand_arena/ranking', {'limit': 20, 'page': 1})
        if 'ranking' in temp:
            group_id = temp['grand_arena_info']['group']
            print(str(self.viewer_id) + '所在公主竞技场组别为' + str(group_id))
        else:
            print(str(self.viewer_id) + '未进入公主竞技场')

    # 商店购买
    def shop_item(self):
        temp = self.client.callapi('shop/item_list', {})
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
            buy_data = self.client.callapi(
                'shop/buy_multiple', {'system_id': 201, 'slot_ids': [1, 2, 3, 4], 'current_currency_num': self.gold})
            if 'purchase_list' in buy_data:
                print("  购买特级药水" +
                      str(buy_data['purchase_list'][0]['received']) + '瓶')
        if self.tower_coin > 800 and not tower_sold_out:
            buy_data = self.client.callapi(
                'shop/buy_multiple', {'system_id': 204, 'slot_ids': [5], 'current_currency_num': self.tower_coin})
            if 'purchase_list' in buy_data:
                print("  购买黄骑碎片" +
                      str(buy_data['purchase_list'][0]['received']) + '片')
        if self.arena_coin > 800 and not arena_sold_out:
            buy_data = self.client.callapi(
                'shop/buy_multiple', {'system_id': 202, 'slot_ids': [6], 'current_currency_num': self.arena_coin})
            if 'purchase_list' in buy_data:
                print("  购买莫妮卡碎片" +
                      str(buy_data['purchase_list'][0]['received']) + '片')
        if self.grand_arena_coin > 800 and not grand_sold_out:
            buy_data = self.client.callapi('shop/buy_multiple', {'system_id': 203, 'slot_ids': [
                                           3], 'current_currency_num': self.grand_arena_coin})
            if 'purchase_list' in buy_data:
                print("  购买布丁碎片" +
                      str(buy_data['purchase_list'][0]['received']) + '片')
        if self.clan_battle_coin > 800 and not clan_sold_out:
            buy_data = self.client.callapi('shop/buy_multiple', {'system_id': 205, 'slot_ids': [
                                           4], 'current_currency_num': self.clan_battle_coin})
            if 'purchase_list' in buy_data:
                print("  购买真琴碎片" +
                      str(buy_data['purchase_list'][0]['received']) + '片')

    # 抽取免费十连
    def gacha_compaign(self, gacha_id, exchange_id):
        temp = self.client.callapi('gacha/exec', {'gacha_id': gacha_id, 'gacha_times': 10,
                                                  'exchange_id': exchange_id, 'draw_type': 6, 'current_cost_num': 1, 'campaign_id': self.campaign_id})
        if 'reward_info_list' in temp:
            chara_list = ''
            for chara in temp['reward_info_list']:
                if chara['id'] == 90005:
                    chara_id = int(chara['exchange_data']['unit_id'])
                else:
                    chara_id = int(chara['id'])
                if chara['id'] != 90005 or chara['exchange_data']['rarity'] == '3':
                    chara_list += self.unit_id_dict[str(chara_id)]+'(3)，'
                else:
                    chara_list += self.unit_id_dict[str(chara_id)]+'，'
            print('  免费十连扭蛋结果为：'+str(chara_list)+'时间为'+time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(temp['servertime'])))
        if 'prize_reward_info' in temp:
            prize_list = ''
            for prize in temp['prize_reward_info'].values():
                prize_list += str(prize['rarity']) + '，'
            print('  附奖等级为：'+str(prize_list))

    # 复刻池选取碎片（临时）
    def gacha_select(self):
        # temp = self.client.callapi('gacha/prizegacha_data', {})
        temp = self.client.callapi('gacha/select_prize', {'prizegacha_id': 100024, 'item_id': 31097})
        return temp

    # 抽取当期up
    def gacha_up(self, gacha_total, gacha_id, exchange_id):
        check_up = 0
        temp = self.client.callapi('gacha/exec', {'gacha_id': gacha_id, 'gacha_times': 10,
                                                  'exchange_id': exchange_id, 'draw_type': 2, 'current_cost_num': self.user_jewel+self.paid_jewel})
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
                chara_list += self.unit_id_dict[str(chara_id)]+'，'
        print('第'+str(gacha_total)+'次扭蛋结果为：' +
              str(chara_list)+'剩余免费钻'+str(self.user_jewel))
        return check_up

    # 查box
    def check_box(self, chara_id):
        if chara_id in self.unit_list:
            print(str(self.viewer_id)+'已抽到'+self.unit_id_dict[str(chara_id)])
            return 0
        else:
            print(str(self.viewer_id)+'未抽到')
            return 1

    def gacha_nnk(self):
        if self.check_box(107001):
            if self.user_jewel < 45000:
                print('   已不足一井！')
            else:
                gacha_total = 1
                while not self.gacha_up(gacha_total, 50047):
                    gacha_total += 1
                print('   共抽取'+str(gacha_total)+'次')

    def exchange_gacha(self, exchange_id):
        temp = self.client.callapi(
            'gacha/exchange_point', {'exchange_id': exchange_id, 'unit_id': 107001, 'current_point': 300})
        if 'reward_info_list' in temp:
            print('   已交换')

    # 升级家具
    def room_up(self):
        temp = self.client.callapi('room/start', {})
        if 'user_room_item_list' in temp:
            item_level_str = '，家具等级为：'
            for item in temp['user_room_item_list']:
                for serial_id in range(4, 8):   # 4:扫荡券, 5:体力, 6:药剂, 7:玛娜
                    if item['serial_id'] == serial_id:
                        item_level_str += str(item['room_item_level']) + ','
                        # 如果家具等级过低，进行升级
                        if item['room_item_level'] < self.room_item_level:
                            temp1 = self.client.callapi(
                                'room/level_up_start', {'floor_number': 1, 'serial_id': serial_id})
                            print('  升级家具' + str(serial_id))
            print('  已进入小屋,时间为'+time.strftime("%Y-%m-%d %H:%M:%S",
                                              time.localtime())+item_level_str[:-1])
        time.sleep(2)
        temp1 = self.client.callapi('room/receive_all', {})
        if 'reward_list' in temp1:
            for item in temp1['reward_list']:
                if item['id'] == 23001:     # 扫荡券
                    self.num_ticket = item['stock']
                if item['id'] == 93001:     # 体力
                    self.user_stamina = item['stock']
        time.sleep(3)

    # 霸瞳活动
    def kaiser_battle(self):
        temp = self.client.callapi('kaiser_battle/top', {})
        jewel_accept = 0
        if 'sub_boss_reward' in temp:
            for reward in temp['sub_boss_reward']:
                if int(reward['id']) == 91002:
                    jewel_accept += int(reward['count'])
        print('    活动已获得钻石' + str(jewel_accept))

    # 主线任务与称号收取
    def mission_plus(self):
        temp = self.client.callapi('mission/accept', {'type': 2, 'id': 0, 'buy_id': 0})
        jewel_accept = 0
        if 'rewards' in temp:
            for reward in temp['rewards']:
                if int(reward['id']) == 91002:
                    jewel_accept += int(reward['count'])
        print('    任务已获得钻石' + str(jewel_accept))
        time.sleep(3)
        self.client.callapi('mission/accept', {'type': 4, 'id': 0, 'buy_id': 0})
        time.sleep(3)

    # 女神祭
    def season_ticket(self):
        temp = self.client.callapi('season_ticket_new/index', {'season_id': 10002})
        if 'missions' in temp:
            temp1 = self.client.callapi('season_ticket_new/accept', {'season_id': 10002, 'mission_id': 0})
            if 'seasonpass_level' in temp1:
                print('    当前女神祭解锁等级为' + str(temp1['seasonpass_level']))

    # 女神祭收取
    def season_ticket_reward(self):
        if 'season_ticket' in self.home:
            level = self.home['season_ticket']['seasonpass_level']
            print('    女神祭等级为' + str(level))
            temp = self.client.callapi('season_ticket_new/reward', {'season_id': 10002, 'level': 0, 'index': 0})
            if 'received_rewards' in temp:
                print('    已收取女神祭等级' + str(temp['received_rewards']))
