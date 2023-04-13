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
