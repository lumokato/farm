import requests
import hashlib
import random
from Crypto.Cipher import AES
import base64
import msgpack
import uuid
from dateutil.parser import parse
from datetime import datetime
from re import search
import time
from json import loads
from os.path import dirname, join, exists
import aiohttp


curpath = dirname(__file__)
config = join(curpath, 'version.txt')
version = "6.2.0"
if exists(config):
    with open(config, encoding='utf-8') as fp:
        version = fp.read().strip()
else:
    with open(config, "w", encoding='utf-8') as fp:
        print(version, file=fp)


# 用于补全下面的text，上面两个网址就是用以下形式补全的
def padding_txt(s):
    return s + (16 - len(s) % 16) * chr(16 - len(s) % 16).encode()


def unpack(decrypted_packet):
    try:
        return msgpack.unpackb(decrypted_packet)
    except msgpack.ExtraData as err:
        return err.unpacked


def decrypt(encrypted):
    mode = AES.MODE_CBC
    try:
        ss2 = base64.b64decode(encrypted)
    except:
        print(encrypted)
    ss2 = base64.b64decode(encrypted)
    vi = b'ha4nBYA2APUD6Uv1'
    key = ss2[-32:]
    ss2 = ss2[:-32]
    cryptor = AES.new(key, mode, vi)
    plain_text = cryptor.decrypt(ss2)
    try:
        return msgpack.unpackb(plain_text[:-plain_text[-1]], strict_map_key=False)
    except msgpack.ExtraData as err:
        return err.unpacked
    except Exception:
        return {"data_headers": {}, "data": {}}


def encrypt_nobase64(decrypted, key):
    mode = AES.MODE_CBC
    vi = b'ha4nBYA2APUD6Uv1'
    cryptor = AES.new(key, mode, vi)
    ss1 = msgpack.packb(decrypted)
    ss1 = padding_txt(ss1)
    plain_text = cryptor.encrypt(ss1)
    return plain_text


def encrypt(decrypted, key):
    mode = AES.MODE_CBC
    vi = b'ha4nBYA2APUD6Uv1'
    cryptor = AES.new(key, mode, vi)
    ss1 = padding_txt(decrypted.encode())
    plain_text = cryptor.encrypt(ss1)
    return base64.b64encode(plain_text + key)


def createkey():
    return base64.b16encode(uuid.uuid1().bytes).lower()


def pack(request, key):
    encrypted = encrypt_nobase64(request, key)
    return encrypted + key


class PCRClient:
    def __init__(self, viewer_id):
        self.viewer_id = viewer_id
        self.request_id = ""
        self.session_id = ""
        self.urlroot = "https://l1-prod-uo-gs-gzlj.bilibiligame.net/"
        self.default_headers = {
            'Accept-Encoding': 'gzip',
            'User-Agent': 'Dalvik/2.1.0 (Linux, U, Android 5.1.1, PCRT00 Build/LMY48Z)',
            'X-Unity-Version': '2021.3.20f1c1',
            'APP-VER': version,
            'BATTLE-LOGIC-VERSION': '4',
            'BUNDLE-VER': '',
            'DEVICE': '2',
            "CHANNEL-ID": "4",
            "PLATFORM-ID": "4",
            'DEVICE-ID': '7b1703a5d9b394e24051d7a5d4818f17',
            'DEVICE-NAME': 'OPPO PCRT00',
            'EXCEL-VER': '1.0.0',
            'GRAPHICS-DEVICE-NAME': 'Adreno (TM) 640',
            'IP-ADDRESS': '10.0.2.15',
            'KEYCHAIN': '',
            'LOCALE': 'CN',
            'PLATFORM-OS-VERSION': 'Android OS 5.1.1 / API-22 (LMY48Z/rel.se.infra.20200612.100533)',
            'REGION-CODE': '',
            'RES-KEY': 'd145b29050641dac2f8b19df0afe0e59',
            'RES-VER': '10002200',
            'SHORT-UDID': '0'
            }
        self.conn = requests.session()
        self.shouldLogin = True

    async def callapi(self, apiurl, request, crypted=True):
        key = createkey()
        try:
            if crypted:
                request['viewer_id'] = encrypt(str(self.viewer_id), key).decode()
            else:
                request['viewer_id'] = str(self.viewer_id)
            req = pack(request, key)
            flag = self.request_id is not None and self.request_id != ''
            flag2 = self.session_id is not None and self.session_id != ''
            headers = self.default_headers
            if flag:
                headers["REQUEST-ID"] = self.request_id
            if flag2:
                headers["SID"] = self.session_id
            resp = None
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=600)) as session:
                for re_post in range(3):
                    response = await session.post(self.urlroot + apiurl, data=req, headers=self.default_headers)
                    if response.status == 200:
                        resp = await response.content.read()
                        break
            if not resp:
                raise Exception("request failed")
            if crypted:
                try:
                    ret = decrypt(resp)
                except Exception:
                    return None                    
            else:
                try:
                    ret = loads(resp.decode())
                except Exception:
                    return None
            ret_header = ret["data_headers"]
            if "check/game_start" == apiurl and "store_url" in ret_header:
                global version
                if ret_header["store_url"].split('_')[1][:-4] != version:
                    version = ret_header["store_url"].split('_')[1][:-4]
                    self.default_headers['APP-VER'] = version
                    with open(config, "w", encoding='utf-8') as fp:
                        print(version, file=fp)
            if "sid" in ret_header:
                if ret_header["sid"] is not None and ret_header["sid"] != "":
                    self.session_id = hashlib.md5((ret_header["sid"] + "c!SID!n").encode()).hexdigest()
            if "request_id" in ret_header:
                if ret_header["request_id"] is not None and ret_header["request_id"] != "" and ret_header["request_id"] != self.request_id:
                    self.request_id = ret_header["request_id"]
            if "viewer_id" in ret_header:
                if ret_header["viewer_id"] is not None and ret_header["viewer_id"] != 0 and ret_header["viewer_id"] != self.viewer_id:
                    self.viewer_id = int(ret_header["viewer_id"])
            answer = ret["data"]
            if answer and 'servertime' in ret['data_headers']:
                answer['servertime'] = ret['data_headers']['servertime']
            return answer
        except Exception:
            self.shouldLogin = True
            raise

    async def login(self, uid, access_key):
        while True:
            self.manifest = await self.callapi('source_ini/get_maintenance_status', {}, False)
            if 'maintenance_message' not in self.manifest:
                break
            try:
                match = search(r'\d\d\d\d-\d\d-\d\d \d\d:\d\d:\d\d', self.manifest['maintenance_message']).group()
                end = parse(match)
                print(f'server is in maintenance until {match}')
                while datetime.now() < end:
                    time.sleep(60)
            except Exception:
                print('server is in maintenance. waiting for 60 secs')
                time.sleep(60)
        ver = self.manifest["required_manifest_ver"]
        self.default_headers["MANIFEST-VER"] = ver
        load = None
        for retry in range(4):
            try:
                await self.callapi('tool/sdk_login', {"uid": uid, "access_key": access_key, "platform": self.default_headers["PLATFORM-ID"], "channel_id": self.default_headers["CHANNEL-ID"]})
                await self.callapi('check/game_start', {"app_type": 0, "campaign_data": "", "campaign_user": random.randint(1, 100000)})
                load = await self.callapi("load/index", {"carrier": "OPPO"})
                home = await self.callapi("home/index", {'message_id': random.randint(1, 5000), 'tips_id_list': [], 'is_first': 1, 'gold_history': 0})
                if 'server_error' not in home:
                    break
            except Exception as e:
                # print(e)
                print('login failed. retrying...')
        if not load:
            return None, None
        self.shouldLogin = False
        return load, home


class ApiException(Exception):
    def __init__(self, message, code):
        super().__init__(message)
        self.code = code
