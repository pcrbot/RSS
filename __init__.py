import base64
import re
from random import choice

import hoshino
from hoshino import Service
from nonebot import CommandSession, on_command

from .config import BASE_URL
from .data import RSS, rssdata

sv = Service('RSS订阅', enable_on_default=True)

BASE_URL = BASE_URL.rstrip('/') if BASE_URL.endswith('/') else BASE_URL

async def add_subscribe(url,group_id):
    try:
        if rssdata.select().where(rssdata.url == url, rssdata.group == group_id).exists():
            msg = "新增订阅失败：本群已存在相同订阅。"
            return msg
        else:
            pass
    except Exception as e:
        sv.logger.exception(e)
        sv.logger.error(type(e))
        msg = '新增订阅失败：订阅数据库操作失败，请稍后再试。若反复出现，请联系维护组反馈。'
        return msg

    rss = RSS(url)
    await rss.feed()

    if (not rss.has_entries) or rss.feed_bozo != 0:
        msg = '新增订阅失败：无法解析该RSS。请确认路由地址、RSS地址、订阅参数或关注用户的隐私设置是否正确。如您确信正确，请联系维护组反馈。'
        return msg

    try:
        rssdata.replace(url = rss.url, group = group_id,
                        date = rss.feed_update).execute()
    except Exception as e:
        sv.logger.exception(e)
        sv.logger.error(type(e))
        msg = '新增订阅失败：订阅数据库操作失败，请稍后再试。若反复出现，请联系维护组反馈。'
        return msg

    msg = f'新增订阅{url.replace(BASE_URL,"")}成功。'
    return msg


def check_title_in_content(title, content):
    title = title[:len(title)//2]
    title = title.replace('\n', '').replace('\r', '').replace(' ', '')
    content = content.replace('\n', '').replace('\r', '').replace(' ', '')
    if title in content:
        return True
    return False


def remove_lf(content):
    text = ''
    for line in content.splitlines():
        line = line.strip()
        if line:
            text += line + '\n'
    text = text.rstrip()
    return text


def format_msg(news):
    msg = ''
    if not check_title_in_content(news['title'], news['content']):
        msg += f"\n{news['title']}"
    msg += f"----------\n{remove_lf(news['content'])}"
    if news['image']:
        base64_str = f"base64://{base64.b64encode(news['image']).decode()}"
        msg += f'[CQ:image,file={base64_str}]'
    return msg


def format_brief_msg(news):
    msg = f"----------\n{news['title']}"
    return msg


@sv.on_prefix('添加订阅')
async def addrss(bot, ev):
    msg = ''
    group_id = ev.group_id
    rss_url = None
    args = ev.message.extract_plain_text().split()
    is_admin = hoshino.priv.check_priv(ev, hoshino.priv.ADMIN)
    if not is_admin:
        await bot.send(ev, '新增订阅失败：权限不足，添加需群管理员以上权限。')
        return
    if len(args) == 0:
        await bot.send(ev, '新增订阅失败：请提供需订阅的RSS地址、路由地址或参数。')
        return
    elif len(args) == 1:
        if args[0] in ['明日方舟', 'mrfz', '方舟', '粥游']:
            rss_url = BASE_URL + '/arknights/news'
        elif args[0] in ['原神', 'ys', '国产手游之光', '国产塞尔达']:
            rss_url = BASE_URL + '/yuanshen'
        else:
            msg = '新增订阅失败：请输入正确的订阅参数。'
    elif len(args) == 2:
        if args[0] == '动态' and args[1].isdigit():
            rss_url = BASE_URL + '/bilibili/user/dynamic/' + str(args[1])

        elif args[0] == '追番' and args[1].isdigit():
            rss_url = BASE_URL + '/bilibili/user/bangumi/' + str(args[1])

        elif args[0] == '投稿' and args[1].isdigit():
            rss_url = BASE_URL + '/bilibili/user/video/' + str(args[1])

        elif args[0] == '专栏' and args[1].isdigit():
            rss_url = BASE_URL + '/bilibili/user/article/' + str(args[1])

        elif args[0] == '番剧' and args[1].isdigit():
            rss_url = BASE_URL + \
                '/bilibili/bangumi/media/' + str(args[1])

        elif args[0] == '排行榜' and args[1].isdigit():
            rss_url = BASE_URL + '/bilibili/ranking/' + str(args[1])

        elif args[0] == '漫画' and args[1].isdigit():
            rss_url = BASE_URL + '/bilibili/manga/update/' + str(args[1])

        elif args[0] == '直播' and args[1].isdigit():
            rss_url = BASE_URL + '/bilibili/live/room/' + str(args[1])
            
        elif args[0] == '微博' and args[1].isdigit():
            rss_url = BASE_URL + '/weibo/user/' + str(args[1])

        elif args[0] in ['PCR', '公主连结', '公主联结', '公主链接', '公主连结', 'pcr']:
            if args[1] == '台服动态':
                rss_url = BASE_URL + '/pcr/news-tw'
            if args[1] == '日服动态':
                rss_url = BASE_URL + '/pcr/news'
            if args[1] == '国服动态' or 'B服动态':
                rss_url = BASE_URL + '/pcr/news-cn'
        elif args[0] == '斗鱼直播' and args[1].isdigit():
            rss_url = BASE_URL + '/douyu/room/' + str(args[1])
        elif args[0] == '虎牙直播' and args[1].isdigit():
            rss_url = BASE_URL + '/huya/live/' + str(args[1])
        else:
            msg = '新增订阅失败：请输入正确的订阅参数。'
    else:
        msg = '新增订阅失败：请输入正确的订阅参数。'

    if rss_url:
        msg = await add_subscribe(rss_url, group_id)

    await bot.send(ev, msg)


@sv.on_prefix('删除订阅')
async def delrss(bot,ev):
    args = ev.message.extract_plain_text().split()
    is_admin = hoshino.priv.check_priv(ev, hoshino.priv.ADMIN)
    if not is_admin:
        await bot.send(ev, '删除订阅失败：权限不足，删除需群管理员以上权限。')
        return
    if not args:
        await bot.send(ev, '删除订阅失败：请提供要删除订阅的序号。')
        return
    try:
        if rssdata.select().where(rssdata.id == args[0], rssdata.group == ev.group_id).exists():
            rssdata.delete().where(rssdata.id == args[0], rssdata.group ==
                                   ev.group_id).execute()
            await bot.send(ev, '删除订阅成功。')

        else:
            await bot.send(ev,'删除订阅失败：未找到该订阅，请确认序号是否正确。')
    except Exception as e:
        sv.logger.exception(e)
        sv.logger.error(type(e))
        await bot.send(ev, '删除订阅失败：订阅数据库操作失败，请稍后再试。若反复出现，请联系维护组反馈。')


@sv.on_command('订阅列表', aliases=('查看本群订阅'))
async def lookrsslist(session: CommandSession):
    try:
        res = rssdata.select(rssdata.url, rssdata.id, rssdata.simply).where(rssdata.group ==
                                                              session.event.group_id)
        msg = ['本群订阅如下:']
        if not res:
            msg.append('空')
        else:
            for r in res:
                rss = RSS(r.url)
                await rss.feed()
                msg.append(f'{r.id}. {rss.feed_link} (简略模式：{"开" if r.simply else "关"})\n')
    except Exception as e:
        sv.logger.exception(e)
        sv.logger.error(type(e))
        session.finish('查询订阅列表失败：订阅数据库操作失败，请稍后再试。若反复出现，请联系维护组反馈。')
    session.finish('\n'.join(msg))


@sv.on_prefix('简略模式')
async def simply_mode(bot,ev):
    args = ev.message.extract_plain_text().split()
    sid = args[0]
    mode = True if args[1] in ['开','开启','启用','打开'] else False
    is_admin = hoshino.priv.check_priv(ev, hoshino.priv.ADMIN)
    if not is_admin:
        await bot.send(ev, '变更推送模式失败：权限不足，变更推送模式需群管理员以上权限。')
        return
    if len(args) != 2 or (not sid.isdigit()):
        await bot.send(ev, '变更推送模式订阅失败：请提供要变更推送模式订阅的序号。')
        return
    try:
        if rssdata.select().where(rssdata.id == args[0], rssdata.group == ev.group_id).exists():
            rssdata.update(simply=mode).where(
                rssdata.id == args[0], rssdata.group == ev.group_id).execute()
            await bot.send(ev, f"变更推送模式成功，当前模式：{'简略模式' if args[1] in ['开','开启','启用','打开'] else '标准模式'}。")
        else:
            await bot.send(ev, '变更推送模式失败：未找到该订阅，请确认序号是否正确。')
    except Exception as e:
        sv.logger.exception(e)
        sv.logger.error(type(e))
        await bot.send(ev, '变更推送模式失败：订阅数据库操作失败，请稍后再试。若反复出现，请联系维护组反馈。')


@on_command('写入订阅',only_to_me=False)
async def approve_subscribe(session: CommandSession):
    if session.event.user_id not in hoshino.config.__bot__.SUPERUSERS:
        return
    args = session.current_arg.split()
    if re.match(r'http[s]*?://.*', args[1]):
        rss_url = args[1]
    else:
        rss_url = BASE_URL + args[1]
    msg = await add_subscribe(rss_url, args[0])
    await session.send(msg)

@sv.scheduled_job('interval', minutes=5, jitter=10)
#@sv.scheduled_job('interval', minutes=.1)
async def push_rss():
    bot = sv.bot
    glist = await sv.get_enable_groups()
    for gid, selfids in glist.items():
        res = rssdata.select(rssdata.url, rssdata.date, rssdata.simply).where(
            rssdata.group == gid)
        for r in res:
            rss = RSS(r.url)
            await rss.feed()
            if not (rss.has_entries):
                continue
            if rss.should_update(time=r.date):
                try:
                    newsinfo = await rss.get_new_entry_info()
                    msg = [f'{rss.feed_title} 更新啦！']
                    msg.append(f'{format_msg(newsinfo) if not r.simply else format_brief_msg(newsinfo)}')
                    msg.append(f'原文: {newsinfo["link"]}')
                    rssdata.update(date=rss.feed_update).where(
                        rssdata.group == gid, rssdata.url == r.url).execute()
                    await bot.send_group_msg(message=('\n'.join(msg)).strip(), group_id=gid, self_id=choice(selfids))
                except Exception as e:
                    sv.logger.exception(e)
                    sv.logger.error(f'{type(e)} occured when pushing rss')
