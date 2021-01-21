# RSS 订阅

适用于Hoshino v2的rss订阅插件, 支持推送完整消息内容及图片.


## 安装方法:

1. 在HoshinoBot的插件目录modules下clone本项目
2. 在 `config/__bot__.py`的模块列表里加入 `rss`
3. 进入本项目根目录,执行 `pip3 install -r requirements.txt` 安装依赖
4. 重启HoshinoBot


可以修改插件运行后生成的 `data.json` 文件的 `rsshub` 项自定义rsshub服务器地址, 为保证推送时效性和稳定性, 推荐自行部署RSSHub服务, 部署方式见官方文档 https://docs.rsshub.app/install/

如需使用代理, 需修改 `data.json` 中的 `proxy` 和 `proxy_urls` 部分, 以下为使用代理订阅 rsshub.app 官方演示源和下载推特图片的范例:

```json
  "proxy": "http://127.0.0.1:1081",
  "proxy_urls": [
    "https://rsshub.app",
    "https://pbs.twimg.com"
  ]
```
如需修改订阅白名单,请修改 `data.json`中的`white_list`部分，根路由名称请见[docs.rsshub.app](https://docs.rsshub.app/)
## 指令列表 :
### 所有人都可以使用 :
- `订阅列表` : 查看订阅列表
### 仅限群管理员 :
- `添加订阅 路由地址/RSS地址` : 添加一般的RSS订阅或路由订阅
- `添加订阅 动态/追番/投稿/专栏 up主uid` : 添加b站up主订阅
- `添加订阅 排行榜 分区id` : 添加b站排行榜订阅
- `添加订阅 直播 房间号` : 添加b站直播间开播订阅
- `添加订阅 漫画 漫画id` : 添加b站漫画订阅(漫画id:可在 URL 中找到, 支持带有mc前缀)
- `添加订阅 明日方舟/原神` : 添加明日方舟/原神新闻订阅
- `添加订阅 pcr 国/台/日服动态` : 添加公主连结国/台/日服动态订阅
- `删除订阅 订阅序号`: 删除订阅列表指定项
- `简略模式 启用/禁用` : 设置推送消息模式:启用,推送消息仅包含标题;禁用,推送消息包含详情及图片
### 仅限超级管理员 :
- `批准订阅 群号 订阅地址` : 批准一个位于白名单之外的订阅

## 许可

本插件以GPL-v3协议开源
