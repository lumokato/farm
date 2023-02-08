# 渠道服pcr AutoFarm
光猫开发，与pcr的通信基于pcrjjc2。

## 主要功能
- 农场号日常：每日两次，任务详情可自行至farm.py中daily_matters函数修改
- 玛娜捐赠：随农场号日常进行
- 装备捐赠：每小时进行一次
- 会战前清后人：详情参考farm.py中refresh_clan与battle_remove函数

## 使用前准备

1. 抓取农场号的viewer_id，uid与access_key。网络代理可参考https://github.com/Xiaodx912/PCRoxy。搜索抓取数据包中/tool/sdk_login，
    Request:{"uid":"<uid>","access_key":"<access_key>"}
    Response:{"viewer_id":"<id>"}
2. 在```account.json```中，"access_key"填入抓取的access_key（同一设备抓取的所有账号应该相同）。"clan"填入建好的每个农场的clan_id，农场会长viewer_id，是否开启捐赠玛娜与装备（1为捐赠）。"accounts"中填入每个农场号的viewer_id与uid，以及是否为装备号（1为装备号）。
3. 在```bind.json```中，"users"填入想捐赠装备的用户vid，"clan"填入玛娜农场的clan_id以及想捐赠玛娜的用户vid，在"wechat_bot"中填入企业微信机器人api（如不使用机器人通知可忽略）。



——以下是pcrjjc2的README的抬头——

# pcrjjc2

本插件是[pcrjjc](https://github.com/lulu666lulu/pcrjjc)重置版，不需要使用其他后端api，但是需要自行配置客户端  
[项目地址](https://github.com/qq1176321897/pcrjjc2)

**本项目基于AGPL v3协议开源，由于项目特殊性，禁止基于本项目的任何商业行为**