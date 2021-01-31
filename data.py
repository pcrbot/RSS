import math
import re
import time
from html.parser import HTMLParser
from io import BytesIO
from typing import Dict, Optional

import feedparser
import hoshino
import peewee as pw
from feedparser import FeedParserDict

try:
    from hoshino.config.__bot__ import (MySQL_host, MySQL_password, MySQL_port,
                                        MySQL_username)
except ImportError:
    from .config import MySQL_host, MySQL_password, MySQL_username, MySQL_port

from PIL import Image

from .aiohttpx import get
from .config import MySQL_database


class RSS:
    def __init__(self, url: str, limit: int = 1) -> None:
        super().__init__()
        self.url = url
        self.limit = limit
        
    async def feed(self) -> FeedParserDict:
        ret = await get(self.url, params={'limit': self.limit,'timeout':5})
        self.feed_content = feedparser.parse(ret.content)
        self.feed_bozo = self.feed_content['bozo']
        self.feed_entries = self.feed_content.entries if len(self.feed_content.entries) != 0 else None
        self.feed_link = self.feed_content.feed.link if len(
            self.feed_content.entries) != 0 else None
        self.has_entries = True if len(self.feed_content.entries) != 0 else False
        self.feed_title = self.feed_content.feed.title if len(
            self.feed_content.entries) != 0 else None
        self.feed_update = self.format_time(
            self.feed_content['entries'][0]['published']) if self.has_entries else 0
        
        
    def remove_html(content):
        #移除html标签
        p = re.compile('<[^>]+>')
        content = p.sub("", content)
        return content

    async def generate_image(url_list):
        raw_images = []
        num = 0
        for url in url_list:
            url = HTMLParser().unescape(url)
            image = (await get(url, params={'timeout': 5})).content
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
        if num == 3 or num >= 5:  # 3列
            width = 900 + border * 2
            height = math.ceil(num / 3) * (300 + border) - border
        else:  # 2列
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
                im = im.resize((box_size, box_size), Image.ANTIALIAS)
                x = (i % row) * (box_size + border)
                y = (i // row) * (box_size + border)
                dest_img.paste(im, (x, y))
        io = BytesIO()
        dest_img.save(io, 'png')
        return io.getvalue()

    @staticmethod
    def format_time(timestr: str) -> int:
        try:
            struct_time = time.strptime(timestr, '%a, %d %b %Y %H:%M:%S %Z')
        except:
            struct_time = time.strptime(timestr, '%Y-%m-%dT%H:%M:%SZ')
            
        dt = time.mktime(struct_time)+28800
        return dt

    def get_image_url(desc):
        imgs = re.findall(r'<img.*?src="(.+?)".+?>', desc)
        return imgs

    @staticmethod
    async def _get_rssdic(entry: FeedParserDict) -> Dict:
        ret = {'title': entry.title,
               'time': entry.updated,
               'content': RSS.remove_html(entry.summary).replace('//转发自:', '\n//转发自:'),
               'image': await RSS.generate_image(RSS.get_image_url(entry.summary)),
               'link': entry.link}
        return ret

    async def get_new_entry_info(self) -> Optional[Dict]:
        try:
            entries = self.feed_entries
            return await RSS._get_rssdic(entries[0])
        except:
            return None

    def should_update(self,time:float) -> bool:
            return(self.feed_update > time)


db = pw.MySQLDatabase(
    host=MySQL_host,
    port=MySQL_port,
    user=MySQL_username,
    password=MySQL_password,
    database=MySQL_database,
    charset='utf8',
    autocommit=True
)


class rssdata(pw.Model):
    id = pw.AutoField(primary_key=True)
    url = pw.CharField()
    date = pw.BigIntegerField()
    group = pw.BigIntegerField()
    simply = pw.BooleanField(default=False)

    class Meta:
        database = db


def init():
    try:
        db.connect()
        if not rssdata.table_exists():
            db.create_tables([rssdata])
        db.close()
        hoshino.logger.info("初始化RSS订阅数据库成功")
    except Exception as e:
        hoshino.logger.error(f"初始化RSS订阅数据库失败{type(e)}")
        hoshino.logger.exception(e)


init()
