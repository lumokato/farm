from .baseapi import BaseApi
import random
import time
import asyncio


class SceneApi(BaseApi):
    # 解锁主线章节
    async def release_all(self, chapter: int):
        temp = await self.client.callapi('/story/force_release', {'story_group_id': chapter + 2000})
        if 'server_error' not in temp:
            print('    已解锁主线章节' + str(chapter))

    # 按id读取剧情
    async def storycheck(self, storyid: int):
        try:
            res = await self.client.callapi('/story/check', {'story_id': storyid})
            await asyncio.sleep(random.randint(3, 9))
            res = await self.client.callapi('/story/start', {'story_id': storyid})
            if 'server_error' in res:
                return False
            if 'reward_info' in res:
                print('    解锁剧情'+str(storyid)+',现有钻'+str(res['reward_info'][0]['stock']))
            return res
        except Exception:
            return False

    # 读取主线剧情
    async def scene_zhuxian(self):
        await self.load_index(requery=True)
        print('已登录账号' + str(self.viewer_id) + ",账号等级为" + str(self.team_level) + ',现有体力为' +
              str(self.user_stamina) + ',免费钻量' + str(self.user_jewel))
        reads = self.read_story_ids
        zhuxian_read = []
        for i in reads:
            if i < 3000000:
                zhuxian_read.append(i)
        chapter_read = int((max(zhuxian_read) - 2000000)/1000)
        if max(zhuxian_read) == 2015006:
            print('    已解锁全部主线')
            return True
        scene_zhuxian = {
            0: [1, 2],
            1: [0, 1, 2, 3, 4, 5, 6],
            2: [1, 2, 3, 4, 5, 6],
            3: [1, 2, 3, 4, 5, 10],
            4: [1, 2, 3, 4, 5, 10],
            5: [1, 2, 3, 4, 5, 6, 10],
            6: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 99],
            7: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 99],
            8: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 99],
            9: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 99],
            10: [1, 2, 3, 4, 5, 6, 7, 8, 99],
            11: [1, 2, 3, 4, 5, 6, 7, 8, 99],
            12: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 99],
            13: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 99],
            14: [1, 2, 3, 4, 5, 6, 7, 8, 9, 98, 99],
            15: [1, 2, 3, 4, 5, 6],
        }
        for i in scene_zhuxian.keys():
            if i > chapter_read - 1:
                await self.release_all(i)
            for j in scene_zhuxian[i]:
                zhuxian_id = 2000000 + i * 1000 + j
                if zhuxian_id not in reads:
                    if not await self.storycheck(zhuxian_id):
                        break
        return True

    # 周年剧情解锁
    async def annicheck(self):
        # try:
        await self.load_index(requery=True)
        for event in self.load['event_sub_story']:
            if event['event_id'] == 10084:
                for sub_story in event['sub_story_info_list']:
                    print(sub_story)
                    if int(sub_story['status']) == 1: # 未解锁
                        res = await self.client.callapi('/story/check', {'story_id': sub_story['sub_story_id']})
                        await asyncio.sleep(random.randint(3, 9))
                        res = await self.client.callapi('/sub_story/ysn/read_story', {'sub_story_id': sub_story['sub_story_id']})
                        if 'server_error' in res:
                            return False
                        else:
                            print('已阅读'+str(sub_story['sub_story_id']))
        # except Exception:
        #     return False
