import re
from aiocqhttp import message
import aiohttp
import asyncio
import feedparser
from PIL import Image
from io import BytesIO
import math
import base64
import nonebot
from nonebot import on_command, CommandSession
import hoshino
import traceback
import os
import json
import time
from html.parser import HTMLParser

rss_news = {}

data = {
    'rsshub': 'https://rss.impure.top',
    'proxy': '',
    'proxy_urls': [],
    'white_list': ['bilibili', 'dianping', 'douban', 'jianshu', 'weibo', 'xiaohongshu', 'zhihu', 'gamer', 'yystv', 'vgtime', 'vgn', 'gouhuo', 'fgo', '3dm', 'lolapp', 'xiaoheihe'],
    'last_time': {},
    'group_rss': {},
    'group_mode': {},
}

HELP_MSG = '''rss订阅
rss list : 查看订阅列表
rss add rss地址 : 添加rss订阅
rss addb up主id : 添加b站up主订阅
rss addr route : 添加rsshub route订阅
rss remove 序号 : 删除订阅列表指定项
rss mode 0/1 : 设置消息模式 标准/简略
详细说明见项目主页: https://github.com/zyujs/rss
'''

sv = hoshino.Service('RSS订阅', bundle='pcr订阅', help_= HELP_MSG)

def save_data():
    path = os.path.join(os.path.dirname(__file__), 'data.json')
    try:
        with open(path, 'w', encoding='utf8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except:
        traceback.print_exc()

def load_data():
    path = os.path.join(os.path.dirname(__file__), 'data.json')
    if not os.path.exists(path):
        save_data()
        return
    try:
        with open(path, encoding='utf8') as f:
            d = json.load(f)
            if 'rsshub' in d:
                if d['rsshub'][-1] == '/':
                    d['rsshub'] = d['rsshub'][:-1]
                data['rsshub'] = d['rsshub']
            if 'last_time' in d:
                data['last_time'] = d['last_time']
            if 'group_rss' in d:
                data['group_rss'] = d['group_rss']
            if 'group_mode' in d:
                data['group_mode'] = d['group_mode']
            if 'proxy' in d:
                data['proxy'] = d['proxy']
            if 'proxy_urls' in d:
                data['proxy_urls'] = d['proxy_urls']
            if 'white_list' in d:
                data['white_list'] = d['white_list']
    except:
        traceback.print_exc()
    global default_rss

load_data()
whitelist_chars = '|'.join(data['white_list'])
whitelist_regex = re.compile(f'.*/({whitelist_chars})/.*?')

default_rss = [
    #data['rsshub'] + '/bilibili/user/dynamic/353840826',    #pcr官方号
    ]

async def query_data(url, proxy=''):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, proxy=proxy,timeout=10) as resp:
                return await resp.read()
    except:
        traceback.print_exc()
        return None

def get_image_url(desc):
    imgs = re.findall(r'<img.*?src="(.+?)".+?>', desc)
    return imgs

def remove_html(content):
    #移除html标签
    p = re.compile('<[^>]+>')
    content = p.sub("", content)
    return content

def remove_lf(content):
    text = ''
    for line in content.splitlines():
        line =  line.strip()
        if line:
            text += line + '\n'
    text = text.rstrip()
    return text

async def generate_image(url_list):
    raw_images = []
    num = 0
    for url in url_list:
        url = HTMLParser().unescape(url)
        proxy = ''
        for purl in data['proxy_urls']:
            if purl in url:
                proxy = data['proxy']
        image = await query_data(url, proxy)
        if image:
            try:
                im = Image.open(BytesIO(image))
                im = im.convert("RGBA")
                raw_images.append(im)
                num += 1
            except:
                pass
        if num >= 9:
            break

    if num == 0:
        return None
    elif num == 1:
        io = BytesIO()
        raw_images[0].save(io, 'png')
        return io.getvalue()

    dest_img = None
    box_size = 300
    row = 3
    border = 5
    height = 0
    width = 0
    if num == 3 or num >= 5:    #3列
        width = 900 + border * 2
        height = math.ceil(num / 3) * (300 + border) - border
    else: #2列
        box_size = 400
        row = 2
        width = 800 + border
        height = math.ceil(num / 2) * (400 + border) - border
    dest_img = Image.new('RGBA', (width, height), (255, 255, 255, 0))

    for i in range(num):
        im = raw_images[i]
        if im:
            w, h = im.size
            if w > h:
                x0 = (w // 2) - (h // 2)
                x1 = x0 + h
                im = im.crop((x0, 0, x1, h))
            elif h > w:
                y0 = (h // 2) - (w // 2)
                y1 = y0 + w 
                im = im.crop((0, y0, w, y1))
            im = im.resize((box_size, box_size),Image.ANTIALIAS)
            x = (i % row) * (box_size + border)
            y = (i // row) * (box_size + border)
            dest_img.paste(im, (x, y))
    io = BytesIO()
    dest_img.save(io, 'png')
    return io.getvalue()

def get_published_time(item):
    time_t = 0
    if 'published_parsed' in item:
        time_t = time.mktime(item['published_parsed'])
    if 'updated_parsed' in item:
        time_t = time.mktime(item['updated_parsed'])
    return time_t

def get_latest_time(item_list):
    last_time = 0
    for item in item_list:
        time = get_published_time(item)
        if time > last_time:
            last_time = time
    return last_time

def check_title_in_content(title, content):
    title = title[:len(title)//2]
    title = title.replace('\n', '').replace('\r', '').replace(' ', '')
    content = content.replace('\n', '').replace('\r', '').replace(' ', '')
    if title in content:
        return True
    return False
    

async def get_rss_news(rss_url):
    news_list = []
    proxy = ''
    for purl in data['proxy_urls']:
        if purl in rss_url:
            proxy = data['proxy']
    res = await query_data(rss_url, proxy)
    if not res:
        return news_list
    feed = feedparser.parse(res)
    if feed['bozo'] != 0:
        sv.logger.info(f'RSS解析失败:{rss_url}')
        return news_list
    if len(feed['entries']) == 0:
        return news_list
    if rss_url not in data['last_time']:
        sv.logger.info(f'RSS初始化:{rss_url}')
        data['last_time'][rss_url] = get_latest_time(feed['entries'])
        return news_list

    last_time = data['last_time'][rss_url]

    for item in feed["entries"]:
        if get_published_time(item) > last_time:
            summary = item['summary']
            #移除转发信息
            i = summary.find('//转发自')
            if i > 0:
                summary = summary[:i]
            news = {
                'feed_title': feed['feed']['title'],
                'title': item['title'],
                'content': remove_html(summary),
                'id': item['id'],
                'image': await generate_image(get_image_url(summary)),
                }
            news_list.append(news)

    data['last_time'][rss_url] = get_latest_time(feed['entries'])
    return news_list

async def refresh_all_rss():
    for item in default_rss:
        if item not in rss_news:
            rss_news[item] = []
    for group_rss in data['group_rss'].values():
        for rss_url in group_rss:
            if rss_url not in rss_news:
                rss_news[rss_url] = []
    #删除没有引用的项目的推送进度
    for rss_url in list(data['last_time'].keys()):
        if rss_url not in rss_news:
            data['last_time'].pop(rss_url)
    for rss_url in rss_news.keys():
        rss_news[rss_url] = await get_rss_news(rss_url)
    save_data()

def format_msg(news):
    msg = f"{news['feed_title']}更新:\n{news['id']}"
    if not check_title_in_content(news['title'], news['content']):
        msg += f"\n{news['title']}"
    msg += f"\n----------\n{remove_lf(news['content'])}"
    if news['image']:
        base64_str = f"base64://{base64.b64encode(news['image']).decode()}"
        msg += f'[CQ:image,file={base64_str}]'
    return msg

def format_brief_msg(news):
    msg = f"{news['feed_title']}更新:\n{news['id']}"
    msg += f"\n----------\n{news['title']}"
    return msg

async def group_process():
    bot = hoshino.get_bot()
    groups = await sv.get_enable_groups()
    await refresh_all_rss()

    for gid in groups.keys():
        rss_list = default_rss
        if str(gid) in data['group_rss']:
            rss_list = data['group_rss'][str(gid)]
        else:
            data['group_rss'][str(gid)] = default_rss
        for rss_url in rss_list:
            if rss_url in rss_news:
                news_list = rss_news[rss_url]
                for news in reversed(news_list):
                    msg = None
                    if str(gid) in data['group_mode'] and data['group_mode'][str(gid)] == 1:
                        msg = format_brief_msg(news)
                    else:
                        msg = format_msg(news)
                    try:
                        await bot.send_group_msg(group_id=gid, message=msg)
                    except:
                        sv.logger.info(f'群 {gid} 推送失败')
                await asyncio.sleep(1)

async def rss_add(group_id, rss_url):
    group_id = str(group_id)
    proxy = ''
    for purl in data['proxy_urls']:
        if purl in rss_url:
            proxy = data['proxy']
    res = await query_data(rss_url, proxy)
    feed = feedparser.parse(res)
    if feed['bozo'] != 0:
        return f'无法解析RSS源: {rss_url.replace(data["rsshub"], "")}\n请确认路由地址、RSS地址、订阅参数或关注用户的隐私设置是否正确。如您确信正确，请联系维护组反馈。',1
        
    if group_id not in data['group_rss']:
        data['group_rss'][group_id] = default_rss
    if rss_url not in set(data['group_rss'][group_id]):
        data['group_rss'][group_id].append(rss_url)
    else:
        return '订阅列表中已存在该项目。',1
    save_data()
    return f'订阅 {rss_url.replace(data["rsshub"], "")} 添加成功。',0

def rss_remove(group_id, i):
    group_id = str(group_id)
    if group_id not in data['group_rss']:
        data['group_rss'][group_id] = default_rss
    if i >= len(data['group_rss'][group_id]):
        return '序号不正确，请重试。'
    data['group_rss'][group_id].pop(i)
    save_data()
    return '删除成功。\n当前' + rss_get_list(group_id)

def rss_get_list(group_id):
    group_id = str(group_id)
    if group_id not in data['group_rss']:
        data['group_rss'][group_id] = default_rss
    msg = '订阅列表:'
    num = len(data['group_rss'][group_id])
    for i in range(num): 
        url = data['group_rss'][group_id][i]
        url = re.sub(r'http[s]*?://.*?/', '/', url)
        msg += f"\n{i}. {url}"
    if num == 0:
        msg += "\n空"
    return msg

def rss_set_mode(group_id, mode):
    group_id = str(group_id)
    mode = int(mode)
    if mode > 0:
        data['group_mode'][group_id] = 1
        msg = '已设置为简略模式。'
    else:
        data['group_mode'][group_id] = 0
        msg = '已设置为标准模式。'
    save_data()
    return msg



@sv.on_prefix('简略模式')
async def simply_mode(bot,ev):
    msg = ''
    group_id = ev.group_id
    args = ev.message.extract_plain_text().split()
    is_admin = hoshino.priv.check_priv(ev, hoshino.priv.ADMIN)
    
    if not is_admin:
        msg = '权限不足，更改推送模式需群管理员以上权限。'

    if args[0] in ['open','enable','开启','启用','打开']:
        msg = rss_set_mode(group_id, 1)
    elif args[0] in ['close','disable','关闭','禁用']:
        msg = rss_set_mode(group_id, 0)
    
    await bot.send(ev, msg)


@sv.on_prefix('订阅列表')
async def subscribe_list(bot,ev):
    group_id = ev.group_id

    await bot.send(ev,rss_get_list(group_id))


@sv.on_prefix('删除订阅')
async def delete_subscribe(bot,ev):
    msg = ''
    group_id = ev.group_id
    args = ev.message.extract_plain_text().split()
    is_admin = hoshino.priv.check_priv(ev, hoshino.priv.ADMIN)

    if not is_admin:
        msg = '权限不足，删除需群管理员以上权限。'
    elif len(args) == 1 and args[0].isdigit():
            msg = rss_remove(group_id, int(args[0]))
    else:
            msg = '请提供要删除RSS订阅的正确序号。'

    await bot.send(ev, msg)

@sv.on_prefix('添加订阅')
async def add_subscribe(bot,ev):
    msg = ''
    rss_url = None
    group_id = ev.group_id
    args = ev.message.extract_plain_text().split()
    is_admin = hoshino.priv.check_priv(ev, hoshino.priv.ADMIN)
    if not is_admin:
        await bot.send(ev, '权限不足，添加需群管理员以上权限。')
        return
    if len(args) == 0:
        await bot.send(ev, '请提供需订阅的RSS地址、路由地址或参数。')
        return
    elif len(args) == 1:
        if args[0] in ['明日方舟', 'mrfz', '方舟', '粥游']:
            rss_url = data['rsshub'] + '/arknights/news'
        elif args[0] in ['原神', 'ys', '国产手游之光', '国产塞尔达']:
            rss_url = data['rsshub'] + '/yuanshen'
        elif whitelist_regex.fullmatch(args[0]):
            if re.match(r'http[s]*?://.*',args[0]):
                rss_url = args[0]
            else:
                rss_url = data['rsshub'] + args[0]
        elif re.match(r'.*/.*/.*', args[0]):
            await bot.send(ev, f'您所添加的路由/RSS不在白名单内，请等待维护组审核后为您添加。\n目前的白名单：\n{whitelist_chars}')
            await bot.send_private_msg(user_id=hoshino.config.__bot__.SUPERUSERS[0], message=f'群{group_id}尝试添加如下不在白名单的订阅：\n{args[0]}\n请使用如下命令批准添加：')
            await asyncio.sleep(1.5)
            await bot.send_private_msg(user_id=hoshino.config.__bot__.SUPERUSERS[0], message=f'批准订阅 {group_id} {args[0]}')
            return
        else:
            msg = '请输入正确的订阅参数。'
    elif len(args) == 2:
        if args[0] == '动态' and args[1].isdigit():
            rss_url = data['rsshub'] + '/bilibili/user/dynamic/' + str(args[1])

        elif args[0] == '追番' and args[1].isdigit():
            rss_url = data['rsshub'] + '/bilibili/user/bangumi/' + str(args[1])

        elif args[0] == '投稿' and args[1].isdigit():
            rss_url = data['rsshub'] + '/bilibili/user/video/' + str(args[1])

        elif args[0] == '专栏' and args[1].isdigit():
            rss_url = data['rsshub'] + '/bilibili/user/article/' + str(args[1])

        elif args[0] == '番剧' and args[1].isdigit():
            rss_url = data['rsshub'] + \
                '/bilibili/bangumi/media/' + str(args[1])

        elif args[0] == '排行榜' and args[1].isdigit():
            rss_url = data['rsshub'] + '/bilibili/ranking/' + str(args[1])

        elif args[0] == '漫画' and args[1].isdigit():
            rss_url = data['rsshub'] + '/bilibili/manga/update/' + str(args[1])

        elif args[0] == '直播' and args[1].isdigit():
            rss_url = data['rsshub'] + '/bilibili/live/room/' + str(args[1])
            
        elif args[0] in ['PCR','公主连结','公主联结','公主链接','公主连结','pcr']:
            if args[1] == '台服动态':
                rss_url = data['rsshub'] + '/pcr/news-tw'
            if args[1] == '日服动态':
                rss_url = data['rsshub'] + '/pcr/news'
            if args[1] == '国服动态' or 'B服动态':
                rss_url = data['rsshub'] + '/pcr/news-cn'
        else:
            msg = '请输入正确的订阅参数。' 
    else:
        msg = '请输入正确的订阅参数。'

    if rss_url:
        msg, status_code = await rss_add(group_id, rss_url)

    await bot.send(ev, msg)


@on_command('批准订阅')
async def approve_subscribe(session: CommandSession):
    args=session.current_arg.split()
    bot = nonebot.get_bot()
    if session.event.user_id not in hoshino.config.__bot__.SUPERUSERS:
        return
    if re.match(r'http[s]*?://.*', args[1]):
        rss_url = args[1]
    else:
        rss_url = data['rsshub'] + args[1]
    msg ,status_code = await rss_add(args[0], rss_url)
    if status_code == 0:
        await bot.send_group_msg(group_id=args[0],message=msg)
    await session.send(msg)

 
@sv.scheduled_job('interval', minutes=10)
async def job():
    await group_process()
