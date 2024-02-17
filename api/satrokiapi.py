import requests
import json


class WebClient:
    def __init__(self):
        self.url_root = "https://pci.satroki.tech/"
        self.default_headers = {
            "Host": "pci.satroki.tech",
            "Content-Type": "application/json; charset=utf-8",
            "Origin": "https://pci.satroki.tech",
            "Referer": "https://pci.satroki.tech/",
            "Accept-Language": "zh-CN,zh",
            "Accept": "*/*",
            "Connection": "close"
        }
        self.conn = requests.session()

    def get_api(self, api_url):
        headers = self.default_headers
        resp = self.conn.get(url=self.url_root + api_url, headers=headers)
        ret = json.loads(resp.content.decode())
        return ret

    def get_unit_name(self, unit_id: int):
        req = self.get_api('api/Unit/GetUnitInfo/' + str(unit_id) + '?s=cn&withNo=True')
        if 'unitName' in req:
            return req['unitName']

    def post_api(self, api_url, request):
        headers = self.default_headers
        resp = self.conn.post(url= self.url_root + api_url,
                        headers = headers, json = request)
        try:
            ret = json.loads(resp.content.decode())
        except:
            ret = None
        return ret

    def get_api(self, api_url):
        headers = self.default_headers
        resp = self.conn.get(url= self.url_root + api_url,
                        headers = headers)
        ret = json.loads(resp.content.decode())
        return ret

    def put_api(self, api_url, request):
        headers = self.default_headers
        resp = self.conn.put(url= self.url_root + api_url,
                        headers = headers, json = request)
        try:
            ret = json.loads(resp.content.decode())
        except:
            ret = None
        return ret

    def login(self):
        with open('bind.json', encoding='utf-8') as fp:
            bind_data = json.load(fp)
        ret = self.post_api('api/Login', {"userName": bind_data["satroki"]["username"], "password": bind_data["satroki"]["password"],"newPassword": "","email": "","nickName": ""})
        self.default_headers["Authorization"] = 'Bearer '+ ret['token']

    def get_box(self):
        self.box_list = self.get_api('api/Box/GetUserBoxResult?s=cn&mr=13&ms=4&ma=True')["box"]
    
    def add_user(self, unitid_list: list):
        resp = self.post_api('api/Box/AddUserBoxLines?s=cn', unitid_list)
        self.box_list = resp

    def delete_user(self, id_list: list):
        self.post_api('api/Box/DeleteUserBoxLines', id_list)

    def get_unit(self, unitid: int, pro_level: int):
        equip_list = self.get_api('api/Unit/GetUnitSourceData/' + str(unitid))["unitPromotions"]
        for equip in equip_list:
            if equip["promotionLevel"] == pro_level:
                return equip

    def edit_user(self, unit_dict):
        for unit in self.box_list:
            if unit["unitId"] == unit_dict["unitId"]:
                req = unit
        req.update(unit_dict)
        if 'uniqueEquipRank' in req.keys():
            req["targetUniqueEquipRank"] = req['uniqueEquipRank']
        if 'rarity' in req.keys():
            req["targetRarity"] = req['rarity']
        req["targetLoveLevel"] = 8
        req["unitPromotion"] = self.get_unit(req["unitId"], req['promotion'])
        if req["targetPromotion"] == 1:
            req["targetPromotion"] = 24
        self.put_api('api/Box/EditUserBoxLine?mr=13&ms=4&ma=True', req)

    def save_equip(self, stock_list):
        self.post_api('api/Equipment/SaveUserEquipStock?s=cn', {"id":0,"userId":0,"server":"cn","stocks": stock_list})
