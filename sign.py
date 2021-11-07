# -*- coding: utf-8 -*-
# by Cjsah
import hashlib, requests
import re

from Utils import *
from login import Login


# 全局配置
CONFIG = getYmlConfig()
APP_VERSION = '9.0.12'
DEVICE_ID = GenDeviceID(USER_NAME)
SESSION = requests.session()

print(CONFIG)


# 获取表单md5
def FormMd5(form):
    tosign = {
        "appVersion": APP_VERSION,
        "bodyString": form['bodyString'],
        "deviceId": form["deviceId"],
        "lat": form["lat"],
        "lon": form["lon"],
        "model": form["model"],
        "systemName": form["systemName"],
        "systemVersion": form["systemVersion"],
        "userId": form["userId"],
    }
    signStr = ""
    for i in tosign:
        if signStr:
            signStr += "&"
        signStr += "{}={}".format(i, tosign[i])
    signStr += "&{}".format(AES_KEY)
    return hashlib.md5(signStr.encode()).hexdigest()


# 登陆并获取session
def getSession():
    log('正在登陆并获取cookie...')
    cookie = Login(USER_NAME, PASSWORD, LOGIN_URL, SESSION, HOST).login()
    print(cookie)
    SESSION.cookies = cookie


# 获取最新未签到任务
def getUnSignedTasks():
    headers = {
        'Accept': 'application/json, text/plain, */*',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.97 Safari/537.36',
        'content-type': 'application/json',
        'Accept-Encoding': 'gzip,deflate',
        'Accept-Language': 'zh-CN,en-US;q=0.8',
        'Content-Type': 'application/json;charset=UTF-8'
    }
    log('获取签到任务ID中...')
    # 由于是cas登陆 第一次请求接口获取cookies
    SESSION.post(
        url='https://{host}/wec-counselor-sign-apps/stu/sign/getStuSignInfosInOneDay'.format(host=HOST),
        headers=headers, data=json.dumps({}), verify=False)

    # 获取具体签到任务
    res = SESSION.post(
        url='https://{host}/wec-counselor-sign-apps/stu/sign/getStuSignInfosInOneDay'.format(host=HOST),
        headers=headers, data=json.dumps({}), verify=False)

    if len(res.json()['datas']['unSignedTasks']) < 1:
        raise Exception('当前没有未签到任务')
    latestTask = res.json()['datas']['unSignedTasks'][0]
    return {
        'signInstanceWid': latestTask['signInstanceWid'],
        'signWid': latestTask['signWid']
    }


# 获取签到任务详情
def getDetailTask(params):
    headers = {
        'Accept': 'application/json, text/plain, */*',
        'User-Agent': 'Mozilla/5.0 (Linux; Android 10; EBG-AN00 Build/HUAWEIEBG-AN00; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/78.0.3904.108 Mobile Safari/537.36  cpdaily/8.2.20 wisedu/8.2.20',
        'content-type': 'application/json',
        'Accept-Encoding': 'gzip,deflate',
        'Accept-Language': 'zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7',
        'Content-Type': 'application/json;charset=UTF-8'
    }
    log('获取签到任务内容中...')
    res = SESSION.post(
        url='https://{host}/wec-counselor-sign-apps/stu/sign/detailSignInstance'.format(host=HOST),
        headers=headers, data=json.dumps(params))
    data = res.json()['datas']
    return data


# 填充表单
def fillForm(task):
    log('正在填充签到内容...')
    form = {}
    if task['isPhoto'] == 1:
        form['signPhotoUrl'] = uploadPicture(SESSION)
    else:
        form['signPhotoUrl'] = ''
    if task['isNeedExtra'] == 1:
        form['isNeedExtra'] = 1
        extraFields = task['extraField']

        extraFieldItemValues = []
        for i in range(0, len(extraFields)):
            extraField = extraFields[i]
            if re.match("[早晚]自测体温是否正常", extraField['title']) is None:
                raise Exception('第%d个默认配置项错误，请检查' % (i + 1))
            else:
                extraFieldItems = extraField['extraFieldItems']
                for extraFieldItem in extraFieldItems:
                    if extraFieldItem['content'] == '正常':
                        extraFieldItemValue = {'extraFieldItemValue': '正常', 'extraFieldItemWid': extraFieldItem['wid']}
                        extraFieldItemValues.append(extraFieldItemValue)
        form['extraFieldItems'] = extraFieldItemValues

        # defaults = CONFIG['defaults']
        # extraFieldItemValues = []
        # for i in range(0, len(extraFields)):
        #     default = defaults[i]['default']
        #     extraField = extraFields[i]
        #     if default['title'] != extraField['title']:
        #         raise Exception('第%d个默认配置项错误，请检查' % (i + 1))
        #     extraFieldItems = extraField['extraFieldItems']
        #     for extraFieldItem in extraFieldItems:
        #         if extraFieldItem['content'] == default['value']:
        #             extraFieldItemValue = {'extraFieldItemValue': default['value'],
        #                                    'extraFieldItemWid': extraFieldItem['wid']}
        #             # 其他，额外文本
        #             if extraFieldItem['isOtherItems'] == 1:
        #                 extraFieldItemValue = {'extraFieldItemValue': default['other'],
        #                                        'extraFieldItemWid': extraFieldItem['wid']}
        #             extraFieldItemValues.append(extraFieldItemValue)
        # form['extraFieldItems'] = extraFieldItemValues

    # form['signInstanceWid'] = params['signInstanceWid']
    form['signInstanceWid'] = task['signInstanceWid']
    form['longitude'] = LON
    form['latitude'] = LAT
    form['isMalposition'] = task['isMalposition']
    form['abnormalReason'] = ''
    form['position'] = ADDRESS
    form['signVersion'] = '1.0.0'
    form['uaIsCpadaily'] = True
    realform = {
        'appVersion': APP_VERSION,
        'systemName': "android",
        'bodyString': AESEncrypt(json.dumps(form)),
        'lon': form['longitude'],
        'calVersion': 'firstv',
        'model': 'OPPO R11 Plus',
        'systemVersion': '8.0',
        'userId': USER_NAME,
        'deviceId': DEVICE_ID,
        'version': 'first_v2',
        'lat': form['latitude']
    }
    realform['sign'] = FormMd5(realform)
    return realform


# 提交签到任务
def submitForm(form):
    # Cpdaily-Extension
    extension = {
        "lon": form['lon'],
        "model": "OPPO R11 Plus",
        "appVersion": APP_VERSION,
        "systemVersion": "8.0",
        "userId": USER_NAME,
        "systemName": "android",
        "lat": form['lat'],
        "deviceId": DEVICE_ID
    }

    headers = {
        'User-Agent': 'User-Agent: Mozilla/5.0 (Linux; Android 10; EBG-AN00 Build/HUAWEIEBG-AN00; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/78.0.3904.108 Mobile Safari/537.36 okhttp/3.12.4',
        'CpdailyStandAlone': '0',
        'extension': '1',
        'Cpdaily-Extension': DESEncrypt(json.dumps(extension)),
        'Content-Type': 'application/json; charset=utf-8',
        'Accept-Encoding': 'gzip',
        'Connection': 'Keep-Alive'
    }

    log('正在提交签到任务...')
    res = SESSION.post(url='https://{host}/wec-counselor-sign-apps/stu/sign/submitSign'.format(host=HOST),
                       headers=headers, data=json.dumps(form))
    message = res.json()['message']
    if message == 'SUCCESS':
        log('签到成功')
    else:
        raise Exception('签到失败，原因是：' + message)


# 主函数
def main():
    pass
    # getSession()
    # params = getUnSignedTasks()
    # task = getDetailTask(params)
    # form = fillForm(task)
    # submitForm(form)


if __name__ == '__main__':
    main()
