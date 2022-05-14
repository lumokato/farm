from .baseapi import BaseApi


class FriendApi(BaseApi):
    # 好友申请
    def friend_request(self, viewer_id: int):
        temp = self.Client.Callapi('friend/request', {'target_viewer_id': viewer_id})
        if 'favorite_unit' in temp:
            # print('发送好友申请成功')
            return True

    # 好友批准
    def friend_accept(self, viewer_id: int):
        self.Client.Callapi('friend/accept', {'target_viewer_id': viewer_id})

    # 好友移除
    def friend_remove(self, viewer_id: int):
        self.Client.Callapi('friend/remove', {'target_viewer_id': viewer_id})

    # 好友列表
    def friend_list(self):
        flist = []
        temp = self.Client.Callapi('friend/friend_list', {})
        if 'friend_list' in temp:
            for friend in temp['friend_list']:
                if 'viewer_id' in friend:
                    flist.append(friend['viewer_id'])
        return flist

    # 好友列表全移除
    def friend_remove_all(self):
        flist = self.friend_list()
        for friend in flist:
            self.friend_remove(friend)
            print('  已移除'+str(friend))

    # 新手活动
    def freshman_mission(self):
        temp = self.Client.Callapi('friend/mission_accept', {'campaign_id': 1, 'type': 10, 'id': 0})
        jewel_accept = 0
        if 'rewards' in temp:
            for reward in temp['rewards']:
                if int(reward['id']) == 91002:
                    jewel_accept += int(reward['count'])
        print('    任务已获得钻石' + str(jewel_accept))
