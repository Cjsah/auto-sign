# -*- coding: utf-8 -*-
# by Cjsah
import hashlib, requests, re
from json import JSONDecodeError

from login import Login
from utils import *

# 全局配置
__name__ = '签到'
APP_VERSION = '9.0.20'
DEVICE_ID = GenDeviceID()
SESSION = requests.session()
HEADERS = {
    'Accept': 'application/json, text/plain, */*',
    'User-Agent': 'Mozilla/5.0 (Linux; Android 10; EBG-AN00 Build/HUAWEIEBG-AN00; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/78.0.3904.108 Mobile Safari/537.36  cpdaily/9.0.20 wisedu/9.0.20',
    'content-type': 'application/json',
    'Accept-Encoding': 'gzip,deflate',
    'Accept-Language': 'zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7',
    'Content-Type': 'application/json;charset=UTF-8'
}


def FormMd5(form):
    """
    表单md5

    :param form: 表单
    :return: 填充结果
    """
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


def getCookie():
    """
    登陆并获取cookie
    """
    log('正在登陆并获取cookie...')
    cookie = Login(USER_NAME, PASSWORD, LOGIN_URL, SESSION).login()
    SESSION.cookies = cookie


def getUnSignedTasks():
    """
    获取最新未签到任务

    :return: 签到wid
    """
    log('获取签到任务ID中...')
    # 由于是cas登陆 第一次请求接口获取cookies
    SESSION.post(
        url='https://{host}/wec-counselor-sign-apps/stu/sign/getStuSignInfosInOneDay'.format(host=HOST),
        headers=HEADERS, data=json.dumps({}), verify=False)

    # 获取具体签到任务
    count = 3
    for i in range(count):
        res = SESSION.post(
            url='https://{host}/wec-counselor-sign-apps/stu/sign/getStuSignInfosInOneDay'.format(host=HOST),
            headers=HEADERS, data=json.dumps({}), verify=False)
        try:
            tasks = res.json()['datas']['unSignedTasks']
            if len(tasks) < 1:
                raise Exception('当前没有未签到任务')
            return {
                'signInstanceWid': tasks[0]['signInstanceWid'],
                'signWid': tasks[0]['signWid']
            }
        except JSONDecodeError:
            if i == count - 1:
                raise Exception('获取签到任务失败')
            continue


def getDetailTask(params):
    """
    获取签到任务详情

    :param params: 签到任务wid
    :return: 签到内容列表
    """
    log('获取签到任务内容中...')
    res = SESSION.post(
        url='https://{host}/wec-counselor-sign-apps/stu/sign/detailSignInstance'.format(host=HOST),
        headers=HEADERS, data=json.dumps(params))
    return res.json()['datas']


def fillForm(task):
    """
    填充签到内容

    :param task: 签到内容列表
    :return: 签到表单
    """
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
        'model': PHONE,
        'systemVersion': PHONE_VERSION,
        'userId': USER_NAME,
        'deviceId': DEVICE_ID,
        'version': 'first_v2',
        'lat': form['latitude']
    }
    realform['sign'] = FormMd5(realform)
    return realform


# 提交签到任务
def submitForm(task, form):
    """
    提交签到任务

    :param task: 签到信息
    :param form: 签到表单
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
        raise Exception(task['taskName'] + ' 签到失败，原因是：' + message)


def run():
    """
    运行函数
    """
    try:
        getCookie()
        params = getUnSignedTasks()
        task = getDetailTask(params)
        form = fillForm(task)
        submitForm(task, form)
    except Exception as e:
        errMsg = e.__str__()
        log(errMsg)
        log('正在发送提醒邮件...')
        sendEmail(errMsg, '签到')


if __name__ == '__main__':
    run()
