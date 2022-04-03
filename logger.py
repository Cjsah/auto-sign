# -*- coding: utf-8 -*-
# by Cjsah
from datetime import datetime, timezone, timedelta


def log(value):
    """
    输出日志

    :param value: 输出内容
    """
    utc_dt = datetime.utcnow().replace(tzinfo=timezone.utc)
    asia_dt = utc_dt.astimezone(timezone(timedelta(hours=8)))
    print(asia_dt.strftime("[%Y-%m-%d %H:%M:%S]"), value)


def err(value):
    """
    输出日志

    :param value: 输出内容
    """
    utc_dt = datetime.utcnow().replace(tzinfo=timezone.utc)
    asia_dt = utc_dt.astimezone(timezone(timedelta(hours=8)))
    print(asia_dt.strftime("[%Y-%m-%d %H:%M:%S] [ERROR]"), value)
    exit(-1)
