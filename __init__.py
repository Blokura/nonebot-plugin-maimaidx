import asyncio
import re
from pathlib import Path
from random import sample
from string import ascii_uppercase, digits
from textwrap import dedent
from typing import Optional, Tuple

import aiofiles
import nonebot
from nonebot import get_bot, on_command, on_endswith, on_message, on_regex, require
from nonebot.adapters.qq import (
    Bot,
    Message,
    MessageEvent,
    MessageSegment,
)
from nonebot.matcher import Matcher
from nonebot.params import CommandArg, Endswith, RegexGroup, RegexMatched
from nonebot.permission import SUPERUSER
from nonebot.plugin import PluginMetadata

from .config import *
from .libraries.image import to_bytes_io
from .libraries.maimaidx_api_data import maiApi
from .libraries.maimaidx_best_50 import *
from .libraries.chunithm_best_30 import *
from .libraries.maimaidx_music import alias, guess, mai, update_local_alias
from .libraries.maimaidx_music_info import *
from .libraries.maimaidx_player_score import *
from .libraries.tool import hash2, set_prober_username, get_prober_username
from .libraries.maimaidx_map import generate_map

__plugin_meta__ = PluginMetadata(
    name='nonebot-plugin-maimaidx',
    description='移植自 mai-bot 开源项目，基于 nonebot2 的街机音游 舞萌DX 的查询插件',
    usage='请使用 帮助maimaiDX 指令查看使用方法',
    type='application',
    config=Config,
    homepage='https://github.com/Yuri-YuzuChaN/nonebot-plugin-maimaidx',
    supported_adapters={'~onebot.v11'}
)

sub_plugins = nonebot.load_plugins(
    str(Path(__file__).parent.joinpath('plugins').resolve())
)

scheduler = require('nonebot_plugin_apscheduler')

from nonebot_plugin_apscheduler import scheduler


manual = on_command('帮助maimaiDX', aliases={'帮助maimaidx'}, priority=5)
repo = on_command('README', aliases={'readme','帮助','help','menu','?'}, priority=5)
search_base = on_command('定数查歌', aliases={'search base'}, priority=5)
search_bpm = on_command('bpm查歌', aliases={'search bpm'}, priority=5)
search_artist = on_command('曲师查歌', aliases={'search artist'}, priority=5)
search_charter = on_command('谱师查歌', aliases={'search charter'}, priority=5)
random_song = on_regex(r'^[随来给]个((?:dx|sd|标准))?([绿黄红紫白]?)([0-9]+\+?)$', priority=5)
mai_what = on_regex(r'.*mai.*什么', priority=5)
# search = on_command('查歌', aliases={'search'}, priority=5)  # 注意 on 响应器的注册顺序，search 应当优先于 search_* 之前注册
query_chart = on_regex(r'^id\s?([0-9]+)$', re.IGNORECASE, priority=5)
mai_today = on_command('今日mai', aliases={'今日舞萌', '今日运势'}, priority=5)
what_song = on_command('是什么歌', priority=5)
alias_song = on_regex(r'^(id)?\s?(.+)\s?有什么别[名称]$', re.IGNORECASE, priority=5)
score = on_command('分数线', priority=5)
best50 = on_command('b50', aliases={'B50', '舞萌b50'}, priority=5)
minfo = on_command('minfo', aliases={'minfo', 'Minfo', 'MINFO', '查歌'}, priority=5)
ginfo = on_command('ginfo', aliases={'ginfo', 'Ginfo', 'GINFO'}, priority=5)
rating_table = on_regex(r'([0-9]+\+?)定数表', priority=5)
rating_table_pf = on_regex(r'([0-9]+\+?)完成表', priority=5)
rise_score = on_regex(r'^我要在?([0-9]+\+?)?上([0-9]+)分\s?(.+)?', priority=5)
plate_process = on_regex(r'^([真超檄橙暁晓桃櫻樱紫菫堇白雪輝辉熊華华爽舞霸星宙祭祝])([極极将舞神者]舞?)进度\s?(.+)?', priority=5)
level_process = on_regex(r'^([0-9]+\+?)\s?(.+)进度\s?(.+)?', priority=5)
level_achievement_list = on_regex(r'^([0-9]+\+?)分数列表\s?([0-9]+)?\s?(.+)?', priority=5)
rating_ranking = on_command('查看排名', aliases={'查看排行'}, priority=5)
set_username = on_command('设置查分器账号', priority=5)
area = on_command('区域', aliases={'map'}, priority=5)

best30 = on_command('b30', aliases={'B30', '中二b30'}, priority=5)


def song_level(ds1: float, ds2: float, stats1: str = None, stats2: str = None) -> list:
    result = []
    music_data = mai.total_list.filter(ds=(ds1, ds2))
    if stats1:
        if stats2:
            stats1 = stats1 + ' ' + stats2
            stats1 = stats1.title()
        for music in sorted(music_data, key=lambda i: int(i.id)):
            for i in music.diff:
                result.append((music.id, music.title, music.ds[i], diffs[i], music.level[i]))
    else:
        for music in sorted(music_data, key=lambda i: int(i.id)):
            for i in music.diff:
                result.append((music.id, music.title, music.ds[i], diffs[i], music.level[i]))
    return result


def get_at_qq(message: Message) -> Optional[int]:
    for item in message:
        if isinstance(item, MessageSegment) and item.type == 'at' and item.data['qq'] != 'all':
            return int(item.data['qq'])


@driver.on_startup
async def get_music():
    """
    bot启动时开始获取所有数据
    """
    maiApi.load_token()
    guess.load_config()
    alias.load_config()
    log.info('正在获取maimai所有曲目信息')
    await mai.get_music()
    log.info('正在获取maimai所有曲目别名信息')
    await mai.get_music_alias()
    log.success('maimai数据获取完成')
    mai.guess()


@manual.handle()
async def _():
    async with aiofiles.open(Root / 'maimaidxhelp.png', 'rb') as f:
        help_image = await f.read()
    await manual.finish(MessageSegment.image(help_image), reply_message=True)


@repo.handle()
async def _():
    await repo.finish('\n感谢您使用maibot！\nmaibot是基于Yuri-YuzuChaN/maimaiDX项目修改的一个机器人，由@Blokura完成对群机器人的适配，并在项目的基础上新增了几个功能。\n欢迎您将maibot添加至您自己的群组内，您只需要点击maibot头像-添加到群聊，即可将maibot添加至您的群内。\n如有建议或反馈，可以联系QQ：30751625\n\n以下是目前支持的指令列表：\n/舞萌b50 /中二b30 /区域\n/是什么歌 /今日舞萌 /查歌\n/设置查分器账号 /帮助')


@search_base.handle()
async def _(args: Message = CommandArg()):
    args = args.extract_plain_text().strip().split()
    if len(args) > 4 or len(args) == 0:
        await search_base.finish('命令格式为\n定数查歌 <定数>\n定数查歌 <定数下限> <定数上限>', reply_message=True)
    if len(args) == 1:
        result = song_level(float(args[0]), float(args[0]))
    elif len(args) == 2:
        try:
            result = song_level(float(args[0]), float(args[1]))
        except:
            result = song_level(float(args[0]), float(args[0]), str(args[1]))
    elif len(args) == 3:
        try:
            result = song_level(float(args[0]), float(args[1]), str(args[2]))
        except:
            result = song_level(float(args[0]), float(args[0]), str(args[1]), str(args[2]))
    else:
        result = song_level(float(args[0]), float(args[1]), str(args[2]), str(args[3]))
    if not result:
        await search_base.finish('没有找到这样的乐曲。', reply_message=True)
    if len(result) >= 60:
        await search_base.finish(f'结果过多（{len(result)} 条），请缩小搜索范围', reply_message=True)
    msg = ''
    for i in result:
        msg += f'{i[0]}. {i[1]} {i[3]} {i[4]}({i[2]})\n'
    await search_base.finish(MessageSegment.image(to_bytes_io(msg)), reply_message=True)


@search_bpm.handle()
async def _(event: MessageEvent, args: Message = CommandArg()):
    args = args.extract_plain_text().strip().split()
    page = 1
    if len(args) == 1:
        music_data = mai.total_list.filter(bpm=int(args[0]))
    elif len(args) == 2:
        music_data = mai.total_list.filter(bpm=(int(args[0]), int(args[1])))
    elif len(args) == 3:
        music_data = mai.total_list.filter(bpm=(int(args[0]), int(args[1])))
        page = int(args[2])
    else:
        await search_bpm.finish('命令格式为：\nbpm查歌 <bpm>\nbpm查歌 <bpm下限> <bpm上限> (<页数>)', reply_message=True)
    if not music_data:
        await search_bpm.finish('没有找到这样的乐曲。', reply_message=True)
    msg = ''
    page = max(min(page, len(music_data) // SONGS_PER_PAGE + 1), 1)
    for i, m in enumerate(sorted(music_data, key=lambda i: int(i.basic_info.bpm))):
        if (page - 1) * SONGS_PER_PAGE <= i < page * SONGS_PER_PAGE:
            msg += f'No.{i + 1} {m.id}. {m.title} bpm {m.basic_info.bpm}\n'
    msg += f'第{page}页，共{len(music_data) // SONGS_PER_PAGE + 1}页'
    await search_bpm.finish(MessageSegment.image(to_bytes_io(msg)), reply_message=True)


@search_artist.handle()
async def _(event: MessageEvent, args: Message = CommandArg()):
    args = args.extract_plain_text().strip().split()
    page = 1
    if len(args) == 1:
        name: str = args[0]
    elif len(args) == 2:
        name: str = args[0]
        if args[1].isdigit():
            page = int(args[1])
        else:
            await search_artist.finish('命令格式为：\n曲师查歌 <曲师名称> (<页数>)', reply_message=True)
    else:
        name = ''
        await search_artist.finish('命令格式为：\n曲师查歌 <曲师名称> (<页数>)', reply_message=True)
    if not name:
        return
    music_data = mai.total_list.filter(artist_search=name)
    if not music_data:
        await search_artist.finish('没有找到这样的乐曲。', reply_message=True)
    msg = ''
    page = max(min(page, len(music_data) // SONGS_PER_PAGE + 1), 1)
    for i, m in enumerate(music_data):
        if (page - 1) * SONGS_PER_PAGE <= i < page * SONGS_PER_PAGE:
            msg += f'No.{i + 1} {m.id}. {m.title} {m.basic_info.artist}\n'
    msg += f'第{page}页，共{len(music_data) // SONGS_PER_PAGE + 1}页'
    await search_artist.finish(MessageSegment.image(to_bytes_io(msg)), reply_message=True)


@search_charter.handle()
async def _(event: MessageEvent, args: Message = CommandArg()):
    args = args.extract_plain_text().strip().split()
    page = 1
    if len(args) == 1:
        name: str = args[0]
    elif len(args) == 2:
        name: str = args[0]
        if args[1].isdigit():
            page = int(args[1])
        else:
            await search_charter.finish('命令格式为：\n谱师查歌 <谱师名称> (<页数>)', reply_message=True)
    else:
        name = ''
        await search_charter.finish('命令格式为：\n谱师查歌 <谱师名称> (<页数>)', reply_message=True)
    if not name:
        return
    music_data = mai.total_list.filter(charter_search=name)
    if not music_data:
        await search_charter.finish('没有找到这样的乐曲。', reply_message=True)
    msg = ''
    page = max(min(page, len(music_data) // SONGS_PER_PAGE + 1), 1)
    for i, m in enumerate(music_data):
        if (page - 1) * SONGS_PER_PAGE <= i < page * SONGS_PER_PAGE:
            diff_charter = zip([diffs[d] for d in m.diff], [m.charts[d].charter for d in m.diff])
            msg += f'No.{i + 1} {m.id}. {m.title} {" ".join([f"{d}/{c}" for d, c in diff_charter])}\n'
    msg += f'第{page}页，共{len(music_data) // SONGS_PER_PAGE + 1}页'
    await search_charter.finish(MessageSegment.image(to_bytes_io(msg)), reply_message=True)


@random_song.handle()
async def _(match: Tuple = RegexGroup()):
    try:
        diff = match[0]
        if diff == 'dx':
            tp = ['DX']
        elif diff == 'sd' or diff == '标准':
            tp = ['SD']
        else:
            tp = ['SD', 'DX']
        level = match[2]
        if match[1] == '':
            music_data = mai.total_list.filter(level=level, type=tp)
        else:
            music_data = mai.total_list.filter(level=level, diff=['绿黄红紫白'.index(match[1])], type=tp)
        if len(music_data) == 0:
            msg = '没有这样的乐曲哦。'
        else:
            msg = await new_draw_music_info(music_data.random())
    except:
        msg = '随机命令错误，请检查语法'

    await random_song.send(msg)
    await random_song.finish()


@mai_what.handle()
async def _():
    await mai_what.finish(await new_draw_music_info(mai.total_list.random()), reply_message=True)


#@search.handle()
async def _(args: Message = CommandArg()):
    name = args.extract_plain_text().strip()
    if not name:
        await search.finish('请在指令后面接上你要搜索的歌曲关键词哦~例如：qzk')
    result = mai.total_list.filter(title_search=name)
    if len(result) == 0:
        await search.finish('没有找到这样的乐曲。')
    elif len(result) == 1:
        msg = await new_draw_music_info(result.random())
        await search.send(msg)
        await search.finish()
    elif len(result) < 50:
        search_result = ''
        for music in sorted(result, key=lambda i: int(i.id)):
            search_result += f'{music.id}. {music.title}\n'
        await search.finish(MessageSegment.image(to_bytes_io(search_result)))
    else:
        await search.finish(f'结果过多（{len(result)} 条），请缩小查询范围。')


@query_chart.handle()
async def _(match = RegexMatched()):
    id = match.group(1)
    music = mai.total_list.by_id(id)
    if not music:
        msg = f'未找到ID为[{id}]的乐曲'
    else:
        msg = await new_draw_music_info(music)
    await query_chart.send(msg)


@mai_today.handle()
async def _(event: MessageEvent):
    wm_list = ['拼机', '推分', '越级', '下埋', '夜勤', '练底力', '练手法', '打旧框', '干饭', '抓绝赞', '收歌']
    uid = event.get_user_id()
    h = hash2(uid)
    rp = h % 100
    wm_value = []
    for i in range(11):
        wm_value.append(h & 3)
        h >>= 2
    msg = f'\n今日人品值：{rp}\n'
    for i in range(11):
        if wm_value[i] == 3:
            msg += f'宜 {wm_list[i]}\n'
        elif wm_value[i] == 0:
            msg += f'忌 {wm_list[i]}\n'
    msg += f'{maiconfig.botName} Bot提醒您：打机时不要大力拍打或滑动哦'
    music = mai.total_list[h % len(mai.total_list)]

    msg = f'的今日推荐歌曲：' + music.title + "\n" + msg
    
    await mai_today.finish(msg + await new_draw_music_info(music))


@what_song.handle()
async def _(args: Message = CommandArg()):
    name = args.extract_plain_text().strip()

    data = mai.total_alias_list.by_alias(name)
    if not data:
        await what_song.finish('未找到此歌曲\n可以使用 添加别名 指令给该乐曲添加别名')
    if len(data) != 1:
        msg = f'找到{len(data)}个相同别名的曲目：\n'
        for songs in data:
            msg += f'{songs.ID}：{songs.Name}\n'
        await what_song.finish(msg.strip())

    music = mai.total_list.by_id(str(data[0].ID))
    await what_song.finish('您要找的是不是：' + await new_draw_music_info(music))


@alias_song.handle()
async def _(match = RegexMatched()):
    findid = bool(match.group(1))
    name = match.group(2)
    if findid and name.isdigit():
        alias_id = mai.total_alias_list.by_id(name)
        if not alias_id:
            await alias_song.finish('未找到此歌曲\n可以使用 添加别名 指令给该乐曲添加别名', reply_message=True)
        else:
            aliases = alias_id
    else:            
        aliases = mai.total_alias_list.by_alias(name)
        if not aliases:
            if name.isdigit():
                alias_id = mai.total_alias_list.by_id(name)
                if not alias_id:
                    await alias_song.finish('未找到此歌曲\n可以使用 添加别名 指令给该乐曲添加别名', reply_message=True)
                else:
                    aliases = alias_id
            else:
                await alias_song.finish('未找到此歌曲\n可以使用 添加别名 指令给该乐曲添加别名', reply_message=True)
    if len(aliases) != 1:
        msg = []
        for songs in aliases:
            alias_list = '\n'.join(songs.Alias)
            msg.append(f'ID：{songs.ID}\n{alias_list}')
        await alias_song.finish(f'找到{len(aliases)}个相同别名的曲目：\n' + '\n======\n'.join(msg), reply_message=True)

    if len(aliases[0].Alias) == 1:
        await alias_song.finish('该曲目没有别名', reply_message=True)

    msg = f'该曲目有以下别名：\nID：{aliases[0].ID}\n'
    msg += '\n'.join(aliases[0].Alias)
    await alias_song.finish(msg, reply_message=True)


@score.handle()
async def _(arg: Message = CommandArg()):
    arg = arg.extract_plain_text().strip()
    args = arg.split()
    if args and args[0] == '帮助':
        msg = dedent('''\
            此功能为查找某首歌分数线设计。
            命令格式：分数线 <难度+歌曲id> <分数线>
            例如：分数线 紫799 100
            命令将返回分数线允许的 TAP GREAT 容错以及 BREAK 50落等价的 TAP GREAT 数。
            以下为 TAP GREAT 的对应表：
            GREAT/GOOD/MISS
            TAP\t1/2.5/5
            HOLD\t2/5/10
            SLIDE\t3/7.5/15
            TOUCH\t1/2.5/5
            BREAK\t5/12.5/25(外加200落)''')
        await score.finish(MessageSegment.image(to_bytes_io(msg)), reply_message=True)
    else:
        try:
            result = re.search(r'([绿黄红紫白])\s?([0-9]+)', arg)
            level_labels = ['绿', '黄', '红', '紫', '白']
            level_labels2 = ['Basic', 'Advanced', 'Expert', 'Master', 'Re:MASTER']
            level_index = level_labels.index(result.group(1))
            chart_id = result.group(2)
            line = float(args[-1])
            music = mai.total_list.by_id(chart_id)
            chart = music.charts[level_index]
            tap = int(chart.notes.tap)
            slide = int(chart.notes.slide)
            hold = int(chart.notes.hold)
            touch = int(chart.notes.touch) if len(chart.notes) == 5 else 0
            brk = int(chart.notes.brk)
            total_score = tap * 500 + slide * 1500 + hold * 1000 + touch * 500 + brk * 2500
            break_bonus = 0.01 / brk
            break_50_reduce = total_score * break_bonus / 4
            reduce = 101 - line
            if reduce <= 0 or reduce >= 101:
                raise ValueError
            msg = dedent(f'''\
                {music.title} {level_labels2[level_index]}
                分数线 {line}% 允许的最多 TAP GREAT 数量为 {(total_score * reduce / 10000):.2f}(每个-{10000 / total_score:.4f}%),
                BREAK 50落(一共{brk}个)等价于 {(break_50_reduce / 100):.3f} 个 TAP GREAT(-{break_50_reduce / total_score * 100:.4f}%)''')
            await score.finish(MessageSegment.image(to_bytes_io(msg)), reply_message=True)
        except (AttributeError, ValueError) as e:
            log.exception(e)
            await score.finish('格式错误，输入“分数线 帮助”以查看帮助信息', reply_message=True)


@best50.handle()
async def _(event: MessageEvent, matcher: Matcher, arg: Message = CommandArg()):
    username = arg.extract_plain_text().split()
    if len(username) == 0:
        openid = event.get_user_id()
        username = [get_prober_username(openid)]

    if username[0] == '':
        await matcher.finish('请先使用"/设置查分器账号"指令设置你的查分器账号，或在本指令后接需要查询的查分器账号，才可以生成图片哦~')
    
    await matcher.send(await generate(username))
    await matcher.finish()


@best30.handle()
async def _(event: MessageEvent, matcher: Matcher, arg: Message = CommandArg()):
    username = arg.extract_plain_text().split()
    if len(username) == 0:
        openid = event.get_user_id()
        username = [get_prober_username(openid)]

    if username[0] == '':
        await matcher.finish('请先使用"/设置查分器账号"指令设置你的查分器账号，或在本指令后接需要查询的查分器账号，才可以生成图片哦~')
    
    await matcher.send(await generate_chuni(username))
    await matcher.finish()


@set_username.handle()
async def _(event: MessageEvent, args: Message = CommandArg()):
    username = args.extract_plain_text().strip()
    if not username:
        await set_username.finish('请在指令后面接上水鱼查分器的账号哦~')
    if set_prober_username(event.get_user_id(), username):
        await set_username.finish('设置保存成功！~')
    else:
        await set_username.finish('设置保存失败！！')


@minfo.handle()
async def _(event: MessageEvent, arg: Message = CommandArg()):
    openid = event.get_user_id()
    username = get_prober_username(openid)
    if not username:
        await minfo.finish('请先使用"/设置查分器账号"指令设置你的查分器账号哦~')
    args = arg.extract_plain_text().strip()
    if not args:
        await minfo.finish('请输入曲目id或曲名')

    if mai.total_list.by_id(args):
        songs = args
    elif by_t := mai.total_list.by_title(args):
        songs = by_t.id
    else:
        aliases = mai.total_alias_list.by_alias(args)
        if not aliases:
            await minfo.finish('未找到曲目')
        elif len(aliases) != 1:
            msg = '找到相同别名的曲目，请使用以下ID查询：\n'
            for songs in aliases:
                msg += f'{songs.ID}：{songs.Name}\n'
            await minfo.finish(msg.strip())
        else:
            songs = str(aliases[0].ID)

    pic = await music_play_data(username, songs)

    await minfo.finish(pic)


@area.handle()
async def _(event: MessageEvent, arg: Message = CommandArg()):
    args = arg.extract_plain_text().strip()
    if not args:
        await area.finish('\n欢迎使用查询地图信息功能\n\n请在指令后接区域ID或关键词\n使用all作为关键词时，可以列出所有区域')
    msg = await generate_map(args)
    await area.send(msg)
    await area.finish()
    


@ginfo.handle()
async def _(event: MessageEvent, arg: Message = CommandArg()):
    args = arg.extract_plain_text().strip()
    if not args:
        await ginfo.finish('请输入曲目id或曲名', reply_message=True)
    if args[0] not in '绿黄红紫白':
        level_index = 3
    else:
        level_index = '绿黄红紫白'.index(args[0])
        args = args[1:].strip()
        if not args:
            await ginfo.finish('请输入曲目id或曲名', reply_message=True)
    if mai.total_list.by_id(args):
        id = args
    elif by_t := mai.total_list.by_title(args):
        id = by_t.id
    else:
        alias = mai.total_alias_list.by_alias(args)
        if not alias:
            await ginfo.finish('未找到曲目', reply_message=True)
        elif len(alias) != 1:
            msg = '找到相同别名的曲目，请使用以下ID查询：\n'
            for songs in alias:
                msg += f'{songs.ID}：{songs.Name}\n'
            await ginfo.finish(msg.strip(), reply_message=True)
        else:
            id = str(alias[0].ID)
    music = mai.total_list.by_id(id)
    if not music.stats:
        await ginfo.finish('该乐曲还没有统计信息', reply_message=True)
    if len(music.ds) == 4 and level_index == 4:
        await ginfo.finish('该乐曲没有这个等级', reply_message=True)
    if not music.stats[level_index]:
        await ginfo.finish('该等级没有统计信息', reply_message=True)
    stats = music.stats[level_index]
    await ginfo.finish(await music_global_data(music, level_index) + dedent(f'''\
        游玩次数：{round(stats.cnt)}
        拟合难度：{stats.fit_diff:.2f}
        平均达成率：{stats.avg:.2f}%
        平均 DX 分数：{stats.avg_dx:.1f}
        谱面成绩标准差：{stats.std_dev:.2f}
        '''), reply_message=True)


@rating_table.handle()
async def _(match: Tuple = RegexGroup()):
    args = match[0].strip()
    if args in levelList[:5]:
        await rating_table.send('只支持查询lv6-15的定数表', reply_message=True)
    elif args in levelList[5:]:
        if args in levelList[-3:]:
            img = ratingdir / '14.png'
        else:
            img = ratingdir / f'{args}.png'
        await rating_table.send(MessageSegment.image(f'''file:///{img}'''))
    else:
        await rating_table.send('无法识别的定数', reply_message=True)


@rating_table_pf.handle()
async def _(event: MessageEvent, match: Tuple = RegexGroup()):
    qqid = event.user_id
    args: str = match[0].strip()
    if args in levelList[:5]:
        await rating_table_pf.send('只支持查询lv6-15的完成表', reply_message=True)
    elif args in levelList[5:]:
        img = await rating_table_draw(qqid, args)
        await rating_table_pf.send(img, reply_message=True)
    # else:
    #     await rating_table_pf.send('无法识别的定数', reply_message=True)


@rise_score.handle()  # 慎用，垃圾代码非常吃机器性能
async def _(bot: Bot, event: MessageEvent, match: Tuple = RegexGroup()):
    qqid = get_at_qq(event.get_message()) or event.user_id
    nickname = ''
    username = None
    
    rating = match[0]
    score = match[1]
    
    if rating and rating not in levelList:
        await rise_score.finish('无此等级', reply_message=True)
    elif match[2]:
        nickname = match[2]
        username = match[2].strip()

    if qqid != event.user_id:
        nickname = (await bot.get_stranger_info(user_id=qqid))['nickname']

    data = await rise_score_data(qqid, username, rating, score, nickname)
    await rise_score.finish(data, reply_message=True)


@plate_process.handle()
async def _(bot: Bot, event: MessageEvent, match: Tuple = RegexGroup()):
    qqid = get_at_qq(event.get_message()) or event.user_id
    nickname = ''
    username = None
    
    ver = match[0]
    plan = match[1]
    if f'{ver}{plan}' == '真将':
        await plate_process.finish('真系没有真将哦', reply_message=True)
    elif match[2]:
        nickname = match[2]
        username = match[2].strip()

    if qqid != event.user_id:
        nickname = (await bot.get_stranger_info(user_id=qqid))['nickname']

    data = await player_plate_data(qqid, username, ver, plan, nickname)
    await plate_process.finish(data, reply_message=True)


@level_process.handle()
async def _(bot: Bot, event: MessageEvent, match: Tuple = RegexGroup()):
    qqid = get_at_qq(event.get_message()) or event.user_id
    nickname = ''
    username = None
    
    rating = match[0]
    rank = match[1]
    
    if rating not in levelList:
        await level_process.finish('无此等级', reply_message=True)
    if rank.lower() not in scoreRank + comboRank + syncRank:
        await level_process.finish('无此评价等级', reply_message=True)
    if levelList.index(rating) < 11 or (rank.lower() in scoreRank and scoreRank.index(rank.lower()) < 8):
        await level_process.finish('兄啊，有点志向好不好', reply_message=True)
    elif match[2]:
        nickname = match[2]
        username =  match[2].strip()

    if qqid != event.user_id:
        nickname = (await bot.get_stranger_info(user_id=qqid))['nickname']

    data = await level_process_data(qqid, username, rating, rank, nickname)
    await level_process.finish(data, reply_message=True)


@level_achievement_list.handle()
async def _(bot: Bot, event: MessageEvent, match: Tuple = RegexGroup()):
    qqid = get_at_qq(event.get_message()) or event.user_id
    nickname = ''
    username = None
    
    rating = match[0]
    page = match[1]
    
    if rating not in levelList:
        await level_achievement_list.finish('无此等级', reply_message=True)
    elif match[2]:
        nickname = match[2]
        username = match[2].strip()

    if qqid != event.user_id:
        nickname = (await bot.get_stranger_info(user_id=qqid))['nickname']

    data = await level_achievement_list_data(qqid, username, rating, page, nickname)
    await level_achievement_list.finish(data, reply_message=True)


async def data_update_daily():
    await mai.get_music()
    mai.guess()
    log.info('maimaiDX数据更新完毕')


scheduler.add_job(data_update_daily, 'cron', hour=4)
