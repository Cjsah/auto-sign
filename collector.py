# -*- coding: utf-8 -*-
# by Cjsah

import requests
from json import JSONDecodeError
from login import Login
from utils import *

# 全局配置
__name__ = '信息收集'
APP_VERSION = '9.0.20'
DEVICE_ID = GenDeviceID()
CONFIG = getYmlConfig('collector')
SESSION = requests.session()
HEADERS = {
    'Accept': 'application/json, text/plain, */*',
    'Accept-Encoding': 'gzip,deflate',
    'Accept-Language': 'zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.97 Safari/537.36',
    'Content-Type': 'application/json;charset=UTF-8'
}


def getCookie():
    """
    登陆并获取cookie
    """
    log('正在登陆并获取cookie...')
    cookie = Login(USER_NAME, PASSWORD, LOGIN_URL, SESSION).login()
    SESSION.cookies = cookie


def getUnfilledCollector():
    """
    获取最新未填充收集任务

    :return: 收集任务wid <dict>
    """
    log('获取收集任务ID中...')
    # 由于是cas登陆 第一次请求接口获取cookies
    SESSION.post(
        url='https://{host}/wec-counselor-collector-apps/stu/collector/queryCollectorProcessingList'.format(host=HOST),
        headers=HEADERS, data=json.dumps({}), verify=False)

    # 获取具体收集任务
    count = 3
    for i in range(count):
        res = SESSION.post(
            url='https://{host}/wec-counselor-collector-apps/stu/collector/queryCollectorProcessingList'.format(host=HOST),
            headers=HEADERS, data=json.dumps({}), verify=False)
        try:
            tasks = res.json()['datas']['rows']
            if len(tasks) < 1:
                raise Exception('当前没有未填表单')
            for task in tasks:
                if task['subject'] == CONFIG['name']:
                    return {
                        'collectorWid': task['wid'],
                        'instanceWid': task['instanceWid'],
                        'formWid': task['formWid']
                    }
        except JSONDecodeError:
            if i == count - 1:
                raise Exception('获取收集任务失败')
            continue
        raise Exception(str([i['subject'] for i in tasks]) + ' 中未找到此收集任务: ' + CONFIG['name'])


def getSchoolWid(params):
    """
    获取学校信息

    :param params: 收集任务wid
    """
    log('获取学校id中...')
    data = {
        'collectorWid': params['collectorWid'],
        'instanceWid': params['instanceWid']
    }

    res = SESSION.post(
        url='https://{host}/wec-counselor-collector-apps/stu/collector/detailCollector'.format(host=HOST),
        headers=HEADERS, data=json.dumps(data))
    params['schoolTaskWid'] = res.json()['datas']['collector']['schoolTaskWid']


def getDetailCollector(params):
    """
    获取收集任务详情

    :param params: 收集任务wid
    :return: 表单列表 <list>
    """
    log('获取表单内容中...')
    data = params.copy()
    data['pageNumber'] = 1
    data['pageSize'] = 9999
    res = SESSION.post(
        url='https://{host}/wec-counselor-collector-apps/stu/collector/getFormFields'.format(host=HOST),
        headers=HEADERS, data=json.dumps(data))
    return res.json()['datas']['rows']


def fillForm(params, collectors):
    """
    填充表单

    :param params: 收集任务ID等信息
    :param collectors: 表单列表
    :return: 填充后表单 <dict>
    """
    log('正在填充表单...')

    params['collectWid'] = params.pop('collectorWid')
    form = {
        'address': ADDRESS,
        'uaIsCpadaily': True,
        'longitude': LON,
        'latitude': LAT
    }
    form.update(params)

    forms = []
    logic = []
    for param in collectors:
        param['formType'] = '0'
        param['sortNum'] = str(param['sort'])
        selected = False
        itemWid = ""
        content = {}
        if len(logic) == 0 or param['logicWid'] in logic:
            param['show'] = True
            value = CONFIG.get(param['title'])
            if value is None:
                raise Exception("未找到名为 '{}' 的配置文件, 请检查".format(param['title']))
            for item in param['fieldItems']:
                if value == item['content']:
                    item['isSelected'] = 1
                    selected = True
                    itemWid = item['itemWid']
                    content = item.copy()
                    if item['showLogic'] != '':
                        for logic_str in item['showLogic'].split(','):
                            logic.append(int(logic_str))
            if not selected:
                raise Exception("{} 中未找到名为 '{}' 的选项, 请检查".format([p['content'] for p in param['fieldItems']], value))
        param['fieldItems'].clear()
        if selected:
            param['fieldItems'].append(content)
            param['value'] = itemWid

        forms.append(param)

    form['form'] = forms

    realform = {
        'appVersion': APP_VERSION,
        'bodyString': AESEncrypt(json.dumps(form)),
        'calVersion': 'firstv',
        'deviceId': DEVICE_ID,
        'lon': form['longitude'],
        'lat': form['latitude'],
        'model': PHONE,
        'systemName': "android",
        'systemVersion': PHONE_VERSION,
        'userId': USER_NAME,
        'version': 'first_v3',
    }
    return realform


def submitForm(task, form):
    """
    提交表单

    :param task: 表单ID
    :param form: 表单
    """
    # Cpdaily-Extension
    extension = {
        "lon": form['lon'],
        "model": PHONE,
        "appVersion": APP_VERSION,
        "systemVersion": PHONE_VERSION,
        "userId": USER_NAME,
        "systemName": "android",
        "lat": form['lat'],
        "deviceId": DEVICE_ID
    }

    headers = {
        'Cpdaily-Extension': DESEncrypt(json.dumps(extension)),
        'Content-Type': 'application/json; charset=utf-8',
        'Connection': 'Keep-Alive',
        'CpdailyStandAlone': '0',
        'tenantId': 'hlju',
        'extension': '1',
        'sign': '1',
    }

    log('正在提交表单...')
    res = SESSION.post(url='https://{host}/wec-counselor-collector-apps/stu/collector/submitForm'.format(host=HOST),
                       headers=headers, data=json.dumps(form))
    message = res.json()['message']
    if message == 'SUCCESS':
        log('提交成功')
    else:
        raise Exception(task['taskName'] + ' 提交失败，原因是：' + message)


def run():
    """
    运行函数
    """
    try:
        getCookie()
        params = getUnfilledCollector()
        collectors = getDetailCollector(params)
        getSchoolWid(params)
        form = fillForm(params, collectors)
        submitForm(collectors, form)
    except Exception as e:
        errMsg = e.__str__()
        log('出现错误: ' + errMsg)
        log('正在发送提醒邮件...')
        sendEmail(errMsg, __name__)


if __name__ == '__main__':
    run()
