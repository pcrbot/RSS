BASE_URL = "" # RSSHub 根目录
USE_PROXY = False # 是否使用代理


if USE_PROXY:
    proxy = 'http://127.0.0.1:7890' # 代理地址
    proxies = {
        "https://pbs.twimg.com" : proxy,
        "https://rsshub.app" : proxy
    } # 需要使用代理访问的域名，请按域名:proxy填写
else:
    proxies ={
        "all://" : None
    }


# MySQL相关配置
MySQL_host = ''
MySQL_port = 3306
MySQL_password = ''
MySQL_username = ''
MySQL_database = "rss"
