from ..config import *
from PIL import Image, ImageFont, ImageDraw
from nonebot.adapters.qq import MessageSegment
from .tool import save_image_file
import json
import datetime
import math
import io
import base64
import os


def is_number(s):
    try:
        float(s)
        return True
    except ValueError:
        pass

    try:
        import unicodedata
        unicodedata.numeric(s)
        return True
    except (TypeError, ValueError):
        pass

    return False


def cImg(text):
    font = ImageFont.truetype("simhei.ttf", 30, encoding="utf-8")
    padding = 10
    margin = 4
    text_list = text.split('\n')
    add = 10 - len(text_list)
    while add > 0:
        add = add - 1
        text_list.append(" ")

    max_width = 0
    for text in text_list:
        x, y, w, h = font.getbbox(text)
        max_width = max(max_width, w)
    wa = max_width + padding * 2
    ha = h * len(text_list) + margin * (len(text_list) - 1) + padding * 2
    im = Image.new('RGB', (wa, ha), color=(255, 255, 255))
    dr = ImageDraw.Draw(im)
    # 文字颜色
    for j in range(len(text_list)):
        text = text_list[j]
        dr.text((padding, padding + j * (margin + h)), text, font=font, fill=(0, 0, 0))
    im.save('output.png')
    image_data = io.BytesIO()
    im.save(image_data, format="JPEG")
    image_data_bytes = image_data.getvalue()
    encoded_image = base64.b64encode(image_data_bytes).decode('utf-8')
    return encoded_image


def image_splicing(pic01, pic02):
    """
    图片拼接
    :param pic01: 图片1路径
    :param pic02: 图片2路径
    :return: 保存路径
    """
    with Image.open(pic01) as img_01, Image.open(pic02) as img_02:
        img1_size, img2_size = img_01.size, img_02.size
        width = max([img1_size[0], img2_size[0]])
        height = img1_size[1] + img2_size[1]
        instance = Image.new('RGB', (width, height), (255, 255, 255))  # 创建背景为白色的空图片
        instance.paste(img_01)  # 以坐标(0,0)为基准粘贴第一张图片
        width = int(width / 2 - img2_size[0] / 2)
        instance.paste(img_02, (width, img1_size[1]))  # 以坐标(0,第一张图片的高)为基准粘贴第二张图片

        save_path = 'output.png'
        instance.save(save_path)

        return save_path


def str_treasuretype(type):
    if type == "MapTaskMusic":
        return "课题曲"
    elif type == "Character":
        return "旅行伙伴"
    elif type == "Frame":
        return "背景"
    elif type == "Title":
        return "称号"
    elif type == "NamePlate":
        return "姓名框"
    elif type == "Icon":
        return "头像"
    elif type == "MusicNew":
        return "乐曲"
    elif type == "Challenge":
        return "完美挑战曲"
    else:
        return type


async def generate_map(name: str = None) -> str:
    try:
        with open(static / 'map.json', 'r', encoding='utf-8') as f:
            map_data = json.load(f)

        search = False
        if not is_number(name):
            search = True
        elif map_data.get(int(name)) is None:
            search = True

        if search:
            result = []
            for map in map_data:
                if int(map_data.get(map).get("netId")) > int(datetime.datetime.now().strftime("%y%m%d")):
                    continue
                map_now = {
                    "id": map,
                    "name": map_data.get(map).get("map_name")
                }
                if name in map:
                    result.append(map_now)
                    continue
                if name.lower() in map_data.get(map).get("map_name").lower():
                    result.append(map_now)
                    continue
                if name == "all" and '区域' in map_data.get(map).get("map_name"):
                    result.append(map_now)
                    continue

            if len(result) == 0:
                return '没有找到匹配的区域，需要原来的原本的区域名称才能匹配成功，可以试试减少关键词再查询。'
            elif len(result) >= 2:
                text = '您可能正在寻找以下区域：'
                for map in result:
                    text = text + '\n' + map["id"] + '  ' + map["name"]
                text = text + '\n请使用"/区域 id"以查询区域信息'
                return text
            else:
                name = result[0]["id"]

        if os.path.exists('./imgcache/map_' + name + '.jpg'):
            url = image_url + 'map_' + name + '.jpg'
            msg = MessageSegment.image(url=url)
            return msg

        mapId = name
        text = "区域ID：" + mapId + "\n区域名称：" + map_data.get(mapId).get(
            "map_name") + "\n联动区域：" + str(map_data.get(mapId).get("isCollabo")) + "\n无限区域：" + str(map_data.get(
            mapId).get("isInfinity")) + "\n底层岛屿：" + map_data.get(mapId).get("island") + "\nnetID：" + str(
            map_data.get(mapId).get("netId")) + "\n地图奖励："

        i = -1
        maxDistance = 0  # 最长东西的距离
        last_distance = 0  # 上一次加的距离
        mapParter = 0  # 地图擅长旅行伙伴
        distance = 0  # 单首歌可以跑的最长距离 单位Km
        totaldistance = 0  # 现在已经累计的距离 单位m
        need_double_pc = 0  # 需要的双人pc数量
        need_double_pc_all = 0
        kaguan = ""  # 这个过程里面出现了跑图课题曲卡关 溢出被重置
        xinjuese = ""  # 这个过程里面出现了获得角色 导致距离变化

        for treasure in map_data.get(mapId).get("treasure"):
            i = i + 1

            if not map_data.get(mapId).get("isInfinity"):
                if mapParter >= 4:
                    distance = 4 + 2 * 4 + 1  # 最后的加1是因为在正常游戏过程中大概率会有加成 平均值可能是1Km的情况 比较接近现实
                else:
                    distance = 4 + 1 * 4 + mapParter + 1

                need_double_pc = math.ceil(((treasure["distance"] - totaldistance) / 1000) / (distance * 4))
                if need_double_pc < 0:
                    need_double_pc = 0
                if i == 0:
                    if treasure["type"] == "Character":
                        distance = distance + 1
                        mapParter = 1
                    totaldistance = totaldistance + (1 * distance * 4) * 1000
                    need_double_pc = 1
                else:
                    if need_double_pc == 0 and treasure["type"] == "Character":
                        mapParter = mapParter + 1
                    if treasure["type"] == "MapTaskMusic" or treasure["type"] == "Challenge":
                        pc = 1
                        while pc <= need_double_pc:
                            track = 1
                            while track <= 4:
                                totaldistance = totaldistance + distance * 1000
                                if totaldistance > treasure["distance"] and kaguan == "":
                                    totaldistance = treasure["distance"]
                                    kaguan = " *"
                                track = track + 1
                            pc = pc + 1
                    elif treasure["type"] == "Character":
                        pc = 1
                        while pc <= need_double_pc:
                            track = 1
                            while track <= 4:
                                totaldistance = totaldistance + distance * 1000
                                if totaldistance >= treasure["distance"] and xinjuese == "":
                                    mapParter = mapParter + 1
                                    if mapParter >= 4:
                                        distance = 4 + 2 * 4 + 1
                                    else:
                                        distance = 4 + 1 * 4 + mapParter + 1
                                    xinjuese = "+"
                                track = track + 1
                            pc = pc + 1
                    else:
                        totaldistance = totaldistance + (need_double_pc * last_distance * 4) * 1000

                need_double_pc_all = need_double_pc_all + need_double_pc
                if xinjuese != "":
                    if mapParter <= 4:
                        xinjuese = " +"
                    else:
                        xinjuese = ""

            if map_data.get(mapId).get("isInfinity"):
                text = text + "\n【" + str(treasure["distance"] / 1000).rstrip("0").rstrip(
                    ".") + " Km】【" + str_treasuretype(
                    treasure["type"]) + "】 " + treasure["name"] + "(" + str(treasure["item_id"]) + ")"
            else:
                text = text + "\n【" + str(treasure["distance"] / 1000).rstrip("0").rstrip(".") + " Km】【" + str(
                    need_double_pc) + "pc 累计" + str(int(totaldistance / 1000)) + "Km 单次" + str(
                    distance) + "Km" + kaguan + xinjuese + "】【" + str_treasuretype(
                    treasure["type"]) + "】 " + treasure["name"] + "(" + str(treasure["item_id"]) + ")"

            if treasure["distance"] > maxDistance:
                maxDistance = treasure["distance"]
            last_distance = distance
            kaguan = ""
            xinjuese = ""

        if map_data.get(mapId).get("isInfinity"):
            track = int(maxDistance / 13000)
            pc3 = int(track / 3)
            pc4 = int(track / 4)

            ptrack = int(maxDistance / 39000)
            ppc3 = int(ptrack / 3)
            ppc4 = int(ptrack / 4)
            text = text + "\n\n在无任何成绩加成下全部使用地图旅行伙伴跑完该区域所有奖励预计需要游玩 " + str(
                track) + " 首歌，单人游玩需要 " + str(pc3) + "pc，双人游玩需要" + str(
                pc4) + "pc。\n在不考虑卡关的情况下，使用3倍票预计需要游玩 " + str(
                ptrack) + " 首歌，单人游玩需要 " + str(ppc3) + "pc，双人游玩需要" + str(
                ppc4) + "pc。\n以上数据仅供参考，请以实际为准。\nGenerated by " + botname
        else:
            text = text + (
                "\n\n上图注明的PC数和单次Km数指的是在国服没有卡关溢出存距离功能、全部双人游玩、只要有擅长的旅行伙伴就组队\n在旅行伙伴距离之外算每次1Km的加成（双人拼机就有1Km，FC或AP还有更多暂不考虑）\n且不游玩地图奖励乐曲的理想情况下、课题曲卡关下一track立刻打完的时候\n跑图预计总共需要  ") + str(
                need_double_pc_all) + "  次双人游戏。\n有\"*\"号的代表在前面所述的pc游玩中有课题曲，导致跑到歌曲后溢出部分不计。\n有\"+\"号的代表在前面所述的pc游玩中获得了新的旅行伙伴，导致此PC中获得角色后的track距离发生变化。\n以上数据仅供参考，请以实际为准。\nGenerated by " + maiconfig.botName + " & Special thanks to 09"

        b64 = cImg(text)
        if os.path.exists(maiconfig.maimaidxpath + "/mai/map/"+ str(mapId) + ".png"):
            path = image_splicing('output.png', maiconfig.maimaidxpath +"/mai/map/"+ str(mapId) + ".png")
            with open(path, "rb") as f:
                b64 = base64.b64encode(f.read()).decode('utf-8')
        res = save_image_file(b64, 'map_' + name, 'jpg', True)
        print(res)
        msg = MessageSegment.image(url=res)
        return msg

    except Exception as e:
        log.error(traceback.format_exc())
        msg = f'未知错误：{type(e)}\n请联系Bot管理员'
    return msg
