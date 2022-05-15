from .baseapi import BaseApi
import time


class ZhuangbeiApi(BaseApi):

    # 单次捐赠装备
    def donate(self, clan_id: int, message_id: int, current_equip_num: int, donation_num: int):
        temp = self.client.callapi('equipment/donate', {'clan_id': clan_id, 'message_id': message_id,
                                                        'donation_num': donation_num, 'current_equip_num': current_equip_num})
        if 'donation_num' not in temp:
            self.client.login(self.uid, self.access_key)
            temp = self.client.callapi('equipment/donate', {'clan_id': clan_id, 'message_id': message_id,
                                                            'donation_num': donation_num, 'current_equip_num': current_equip_num})
        return temp

    # 会长号判断是否需要捐赠
    def donate_check(self, bind):
        temp = self.chat_monitor()
        message_time = {}
        # 记录所有chat创建时间
        if temp['clan_chat_message']:
            for message in temp['clan_chat_message']:
                message_time[message['message_id']] = message['create_time']
        # 返回需要捐献的人物id与装备id
        donate_list = []
        if temp['equip_requests']:
            for message in temp['equip_requests']:
                message_id = message['message_id']
                if message['donation_num'] < 10 and time.time() - message_time[message_id] < 28800 and str(message['viewer_id']) in bind['users'].keys():
                    donate_list.append([message['viewer_id'], message['message_id'], message['equip_id']])
        return donate_list

    # 账号捐赠流程
    def donate_message(self, message_id):
        temp = self.chat_monitor()
        donate_continue = 0
        message_time = {}
        self.equip_stock = {}
        if temp['clan_chat_message']:
            for message in temp['clan_chat_message']:
                message_time[message['message_id']] = message['create_time']
        # 需要检测装备数量是否可以捐赠
        if temp['user_equip_data']:
            for equip in temp['user_equip_data']:
                self.equip_stock[equip['equip_id']] = equip['equip_count']
        if temp['equip_requests']:
            for message in temp['equip_requests']:
                # 按id选取指定的message
                if message['message_id'] == message_id:
                    donate_continue = 1
                    msg_donate_num = 0
                    # 检查是否已捐赠此message
                    if 'user_donation_num' in message:
                        msg_donate_num = message['user_donation_num']
                    equip_id = message['equip_id']
                    # 如果已捐赠完,返回0
                    if 'donation_num' in message:
                        if message['donation_num'] == 10:
                            return 0, self.donation_num
                    # 如果账号已捐赠超过8,切换账号
                    if int(self.donation_num) > 8:
                        # print(str(self.viewer_id)+'已捐献' +
                        #       str(self.donation_num)+'个，切换账号')
                        return donate_continue, self.donation_num
                    if equip_id in self.equip_stock.keys():
                        if self.equip_stock[equip_id] >= 2 and msg_donate_num < 2:
                            temp1 = self.donate(
                                self.clan_id, message_id, self.equip_stock[equip_id], 2 - msg_donate_num)
                            if 'donation_num' not in temp1:
                                return donate_continue, self.donation_num
                            self.donation_num = int(temp1['donation_num'])
                            self.equip_stock['equip_id'] = temp1['donate_equip']['stock']
                            # print(str(self.viewer_id)+'已捐献'+str(self.donation_num) +
                            #       '个,时间为'+time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()))
                            # 如果每次只捐一个账号，在此处取消注释
                            return donate_continue, self.donation_num
        return donate_continue, self.donation_num
