from .baseapi import BaseApi


class FriendApi(BaseApi):
    # 好友申请
    async def friend_request(self, viewer_id: int):
        temp = await self.client.callapi('friend/request', {'target_viewer_id': viewer_id})
        if 'favorite_unit' in temp:
            # print('发送好友申请成功')
            return True

    # 好友申请列表
    async def pending_list(self):
        pending_list = []
        friend_num = 0
        temp = await self.client.callapi('friend/pending_list', {})
        if 'pending_list' in temp:
            for user in temp['pending_list']:
                pending_list.append(user['viewer_id'])
            friend_num = temp['friend_num']
        return pending_list, friend_num

    # 好友批准
    async def friend_accept(self, viewer_id: int):
        await self.client.callapi('friend/accept', {'target_viewer_id': viewer_id})

    # 好友移除
    async def friend_remove(self, viewer_id: int):
        await self.client.callapi('friend/remove', {'target_viewer_id': viewer_id})

    # 好友列表
    async def friend_list(self):
        flist = []
        temp = await self.client.callapi('friend/friend_list', {})
        if 'friend_list' in temp:
            for friend in temp['friend_list']:
                if 'viewer_id' in friend:
                    flist.append(friend['viewer_id'])
        return flist

    # 好友列表全移除
    async def friend_remove_all(self):
        flist = await self.friend_list()
        for friend in flist:
            await self.friend_remove(friend)
            print('  已移除'+str(friend))

    # 新手活动
    async def freshman_mission(self):
        temp = await self.client.callapi('friend/mission_accept', {'campaign_id': 1, 'type': 10, 'id': 0})
        jewel_accept = 0
        if 'rewards' in temp:
            for reward in temp['rewards']:
                if int(reward['id']) == 91002:
                    jewel_accept += int(reward['count'])
        print('    任务已获得钻石' + str(jewel_accept))

    # 改名
    async def rename(self):
        await self.client.callapi('profile/rename', {'user_name': '佑树'})

    # 改简介
    async def update_comment(self, comment):
        await self.client.callapi('profile/update_comment', {'user_comment': comment})
