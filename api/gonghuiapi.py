from .baseapi import BaseApi


class GonghuiApi(BaseApi):

    # 公会踢人
    def remove_members(self, remove_id: int):
        member_list = []
        temp = self.client.callapi(
            'clan/info', {'clan_id': 0, 'get_user_equip': 0})
        if 'clan' in temp:
            leader_id = temp['clan']['detail']['leader_viewer_id']
            for member_data in temp['clan']['members']:
                member_list.append(member_data['viewer_id'])
        if self.viewer_id == leader_id and remove_id in member_list:
            temp = self.client.callapi(
                'clan/remove', {'clan_id': self.clan_id, 'remove_viewer_id': remove_id})
            return ('已移出' + str(remove_id) + '\n')

    # 公会放人
    def accept_members(self, accept_list):
        temp = self.client.callapi('clan/info', {'clan_id': 0, 'get_user_equip': 0})
        if 'clan' in temp:
            request = temp['have_join_request']
        if request:
            temp = self.client.callapi('clan/join_request_list', {'clan_id': self.clan_id, 'page': 0, 'oldest_time': 0})
            for id in accept_list:
                self.client.callapi('clan/join_request_accept', {'request_viewer_id': id, 'clan_id': self.clan_id})
        return True

    # 加入公会
    def join_clan(self, clan_id: int):
        temp = self.client.callapi('clan/join', {'clan_id': clan_id, 'from_invite': 0})
        if 'clan_status' in temp:
            if temp['clan_status'] == 2:
                print('已加入')
            elif temp['clan_status'] == 1:
                print('已申请')

    # 解散工会
    def break_clan(self):
        temp = self.client.callapi('clan/breakup', {'clan_id': self.clan_id})
        if 'add_present_count' in temp:
            print('解散成功')

    # 退出工会
    def leave_clan(self):
        temp = self.client.callapi('clan/leave', {'clan_id': self.clan_id})
        if not temp:
            print('退出成功')

    # 交接会长
    def change_role(self, change_id: int):
        temp = self.client.callapi('clan/change_role', {'role_info': [
                                   {'viewer_id': self.viewer_id, 'role_id': 0}, {'viewer_id': change_id, 'role_id': 40}]})
        if 'members' in temp:
            print('交接成功')

    # 查询公会内成员详情
    def query_clan_member(self, clan_id: int):
        print('  行会id为'+str(clan_id))
        mem_list = []
        members = self.client.callapi(
            'clan/others_info', {'clan_id': clan_id})['clan']['members']
        for mem in members:
            res = self.client.callapi(
                'profile/get_profile', {'target_viewer_id': int(mem['viewer_id'])})
            print(str(res['user_info']['viewer_id']) + ' 用户名: ' + res['user_info']['user_name'] + ' 等级' +
                  str(res['user_info']['team_level']) + ' N图解锁: ' + str(sum(res['quest_info']['normal_quest']))
                  + ' H图解锁: ' + str(sum(res['quest_info']['hard_quest'])))
            # print(str(res['user_info']['viewer_id']) + '场次: ' + str(res['user_info']['arena_group'])) # arena场次
        return mem_list

    # 检查公会成员
    def check_members(self):
        members = self.client.callapi(
            'clan/others_info', {'clan_id': self.clan_id})['clan']['members']
        mem_query = []
        for mem in members:
            mem_query.append(mem['viewer_id'])
        return mem_query
