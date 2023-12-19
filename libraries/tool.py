import time
import base64
import datetime
import tinify
import os
from nonebot.adapters.qq import MessageSegment
from ..config import *

def hash2(openid: str):
    today_date_str = datetime.datetime.strftime(datetime.datetime.now(), '%Y-%m-%d')
    seed = openid + today_date_str
    print(seed + str(hash(seed)))
    return hash(seed)

def render_forward_msg(msg_list: list, uid: int=10001, name: str='maimaiDX'):
    forward_msg = []
    for msg in msg_list:
        forward_msg.append({
            "type": "node",
            "data": {
                "name": str(name),
                "uin": str(uid),
                "content": msg
            }
        })
    return forward_msg

def save_image_file(img: bytes, filename: str='', format: str='png', tiny: bool=False):
    if filename == '':
        filename = datetime.strftime(datetime.now(), '%Y-%m-%d %H:%M:%S')

    file_path = './imgcache/' + filename + '.' + format
    with open(file_path, 'wb') as f:
        f.write(base64.b64decode(img))

    if os.path.getsize('./imgcache/' + filename + '.' + format) > 1024 * 1024 * 2 or tiny:
        tinify.key = maiconfig.tinifykey
        img = tinify.from_file('./imgcache/' + filename + '.' + format)
        img.to_file('./imgcache/' + filename + '.' + format)

    return image_url + filename + '.'  + format

def set_prober_username(openid: str, username: str):
    with open('./prober/' + openid + '.txt', 'w') as f:
        f.write(username)
    return True

def get_prober_username(openid: str):
    username = ''
    try:
        with open('./prober/' + openid + '.txt', 'r') as f:
            username = f.read()
    except:
        return ''
    return username
    
    
