import math
import traceback
from io import BytesIO
from typing import List, Optional, Tuple, Union

import httpx
from nonebot.adapters.qq import MessageSegment
from PIL import Image, ImageDraw, ImageFont
from pydantic import BaseModel

from ..config import *
from .image import DrawText, image_to_base64
from .chunithm_api_data import chuniApi
from .maimaidx_error import *
from .chunithm_music import download_music_pictrue
from .tool import save_image_file

class ChartInfo(BaseModel):

    cid: int
    ds: float
    fc: Optional[str] = ''
    level: str
    level_index: int
    level_label: str
    mid: int
    ra: float
    score: int
    title: str


class Data(BaseModel):

    b30: Optional[List[ChartInfo]] = None
    r10: Optional[List[ChartInfo]] = None


class UserInfo(BaseModel):
    
    nickname: Optional[str]
    rating: Optional[float]
    records: Optional[Data]
    username: Optional[str]


class DrawBest:

    def __init__(self, UserInfo: UserInfo, qqId: Optional[Union[int, str]] = None) -> None:

        self.userName = UserInfo.nickname
        self.Rating = UserInfo.rating
        self.b30Best = UserInfo.records.b30
        self.r10Best = UserInfo.records.r10
        self.qqId = qqId

    async def whiledraw(self, data: List[ChartInfo], isBest: bool) -> Image.Image:
        # y为第一排纵向坐标，dy为各排间距
        y = 303 if isBest else 1929
        dy = 311

        TEXT_COLOR = [(0, 0, 0, 255), (0, 0, 0, 255), (0, 0, 0, 255), (0, 0, 0, 255), (103, 20, 141, 255)]
        i = 0
        for num, info in enumerate(data):
            i = i + 1
            if num % 6 == 0:
                x = 53
                y += dy if num != 0 else 0
            else:
                x += 305


            cover = Image.open(await download_music_pictrue(info.mid)).resize((180, 180))
            if info.score < 500000:
                rate = 'd'
            elif info.score < 600000:
                rate = 'c'
            elif info.score < 700000:
                rate = 'b'
            elif info.score < 800000:
                rate = 'bb'
            elif info.score < 900000:
                rate = 'bbb'
            elif info.score < 925000:
                rate = 'a'
            elif info.score< 950000:
                rate = 'aa'
            elif info.score < 975000:
                rate = 'aaa'
            elif info.score < 990000:
                rate = 's'
            elif info.score < 1000000:
                rate = 'sp'
            elif info.score < 1005000:
                rate = 'ss'
            elif info.score < 1007500:
                rate = 'ssp'
            elif info.score < 1009000:
                rate = 'sss'
            else:
                rate = 'sssp'
            rate = Image.open(chunidir / f'rank_{rate}.png')
            
            self._im.alpha_composite(self._diff[info.level_index], (x, y))

            self._im.alpha_composite(cover, (x + 8, y + 7))
            self._im.alpha_composite(rate, (x + 206, y + 57))

            title = info.title
            if coloumWidth(title) > 25:
                title = changeColumnWidth(title, 24) + '...'

            text_x = x + 20
            text_y = y + 204
            
            r = self._hiragino.get_box(title, 18)
            text_width = r[2]
            text_height = r[3]

            # 计算文本的起始位置，使其在矩形区域内居中
            text_start_x = text_x + (250 - text_width) // 2
            text_start_y = text_y + (30 - text_height) // 2

            self._hiragino.draw(text_start_x, text_start_y,18 , title, TEXT_COLOR[info.level_index], anchor='lm')

            self._hiragino.draw(x + 240,y + 25, 28 ,str('#'+str(i)), (255,255,255,255), anchor='mm')

            self._hiragino.draw(x + 13,y + 260, 14, 'SCORE:', (0, 0, 0, 255), anchor='ld')
            self._hiragino.draw(x + 280,y + 260, 20,format(info.score,',') + ' (' + "{:.2f}".format(info.ra) + ')', (0, 0, 0, 255), anchor='rd')

            self._hiragino.draw(x + 242,y + 154, 28 ,str(info.ds), (255,255,255,255), anchor='mm')
        
    async def draw(self):

        basic = Image.open(chunidir / 'b30_score_basic.png')
        advanced = Image.open(chunidir / 'b30_score_advanced.png')
        expert = Image.open(chunidir / 'b30_score_expert.png')
        master = Image.open(chunidir / 'b30_score_master.png')
        ultima = Image.open(chunidir / 'b30_score_ultima.png')
        self._diff = [basic, advanced, expert, master, ultima]


        # background
        self._im = Image.open(chunidir / 'b30_bg.png').convert('RGBA')

        # text
        text_im = ImageDraw.Draw(self._im)
        self._hiragino = DrawText(text_im, HIRAGINO)
        self._hiragino.draw(348, 125, 60, '中二节奏 玩家成绩表 Player：' + self.userName + '(' + "{:.2f}".format(self.Rating) + ')', (0, 0, 0, 255), 'lm')

        bestra = 0.0
        b30ra = 0.0
        i = 0
        for num, info in enumerate(self.b30Best):
            i = i + 1
            b30ra = b30ra + info.ra
            if bestra < info.ra:
                bestra = info.ra

        bestra = round((b30ra + bestra * 10) / (i + 10),2)
        b30ra = round(b30ra / i, 2)
        
        r10ra = 0.0
        i = 0
        for num, info in enumerate(self.r10Best):
            i = i + 1
            r10ra = r10ra + info.ra
        r10ra = round(r10ra / i, 2)


        self._hiragino.draw(1314, 2280, 40, 'B30 平均Rating：' + "{:.2f}".format(b30ra), (0,0,0,255), 'lm')
        self._hiragino.draw(1314, 2350, 40, 'R10 平均Rating：' + "{:.2f}".format(r10ra), (0,0,0,255), 'lm')
        self._hiragino.draw(1314, 2420, 40, '理论最高Rating：' + "{:.2f}".format(bestra), (0,0,0,255), 'lm')

        await self.whiledraw(self.b30Best, True)
        await self.whiledraw(self.r10Best, False)

        return self._im.resize((1440, 1920))

def getCharWidth(o) -> int:
    widths = [
        (126, 1), (159, 0), (687, 1), (710, 0), (711, 1), (727, 0), (733, 1), (879, 0), (1154, 1), (1161, 0),
        (4347, 1), (4447, 2), (7467, 1), (7521, 0), (8369, 1), (8426, 0), (9000, 1), (9002, 2), (11021, 1),
        (12350, 2), (12351, 1), (12438, 2), (12442, 0), (19893, 2), (19967, 1), (55203, 2), (63743, 1),
        (64106, 2), (65039, 1), (65059, 0), (65131, 2), (65279, 1), (65376, 2), (65500, 1), (65510, 2),
        (120831, 1), (262141, 2), (1114109, 1),
    ]
    if o == 0xe or o == 0xf:
        return 0
    for num, wid in widths:
        if o <= num:
            return wid
    return 1

def coloumWidth(s: str) -> int:
    res = 0
    for ch in s:
        res += getCharWidth(ord(ch))
    return res

def changeColumnWidth(s: str, len: int) -> str:
    res = 0
    sList = []
    for ch in s:
        res += getCharWidth(ord(ch))
        if res <= len:
            sList.append(ch)
    return ''.join(sList)

async def generate_chuni(username: Optional[str] = None) -> str:
    try:

        obj = await chuniApi.query_user('player', qqid=None, username=username)

        chuni_info = UserInfo(**obj)
        draw_best = DrawBest(chuni_info, 3889005734)
        
        pic = await draw_best.draw()

        res = save_image_file(image_to_base64(pic),'b30_' + username[0])
        print(res)
        msg = MessageSegment.image(url=res)
    except UserNotFoundError as e:
        msg = str(e)
    except UserDisabledQueryError as e:
        msg = str(e)
    except Exception as e:
        log.error(traceback.format_exc())
        msg = f'未知错误：{type(e)}\n请联系Bot管理员'
    return msg
