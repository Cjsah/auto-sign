# -*- coding: utf-8 -*-
# by Cjsah
import json, yaml, base64, requests, pyaes, random, hashlib
from pyDes import des, CBC, PAD_PKCS5
from datetime import datetime, timedelta
from os import getenv


# 读取yml配置
def getYmlConfig(file='config.yml'):
    with open(file, 'r', encoding="utf-8") as f:
        return dict(yaml.load(f.read(), Loader=yaml.FullLoader))


# 生成设备id，根据用户账号生成,保证同一学号每次执行时deviceID不变，可以避免辅导员看到用新设备签到
def GenDeviceID(username):
    deviceId = ''
    random.seed(username.encode('utf-8'))
    for i in range(8):
        num = random.randint(97, 122)
        if (num * i + random.randint(1, 8)) % 3 == 0:
            deviceId = deviceId + str(num % 9)
        else:
            deviceId = deviceId + chr(num)
    deviceId = deviceId + 'XiaomiMI6'
    return deviceId


# 全局配置
CONFIG = getYmlConfig()
HOST = getenv('CONFIG_HOST')
APP_VERSION = '9.0.12'
DES_KEY = 'b3L26XNL'
AES_KEY = 'ytUQ7l2ZZu8mLvJZ'
USER_NAME = getenv('CONFIG_USERNAME')
DEVICE_ID = GenDeviceID(USER_NAME)


def log(value):
    bj_time = datetime.now() + timedelta(hours=8)
    print(bj_time.strftime("[%Y-%m-%d %H:%M:%S]"), value)


# DES加密
def DESEncrypt(s):
    log('Extension加密中...')
    iv = b"\x01\x02\x03\x04\x05\x06\x07\x08"
    k = des(DES_KEY, CBC, iv, pad=None, padmode=PAD_PKCS5)
    encrypt_str = k.encrypt(s)
    return base64.b64encode(encrypt_str).decode()


# AES加密
def AESEncrypt(s):
    log('bodyString加密中...')
    iv = b"\x01\x02\x03\x04\x05\x06\x07\x08\t\x01\x02\x03\x04\x05\x06\x07"
    encrypter = pyaes.Encrypter(pyaes.AESModeOfOperationCBC(AES_KEY.encode('utf-8'), iv))
    encrypted = encrypter.feed(s)
    encrypted += encrypter.feed()
    return base64.b64encode(encrypted).decode()


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


# 获取图片上传位置
def uploadPicture(session):
    url = 'https://{host}/wec-counselor-sign-apps/stu/oss/getUploadPolicy'.format(host=HOST)
    res = session.post(url=url, headers={'content-type': 'application/json'}, data=json.dumps({'fileType': 1}))
    datas = res.json().get('datas')
    fileName = datas.get('fileName') + '.png'
    accessKeyId = datas.get('accessid')
    xhost = datas.get('host')
    # xdir = datas.get('dir')
    xpolicy = datas.get('policy')
    signature = datas.get('signature')
    url = xhost + '/'
    data = {
        'key': fileName,
        'policy': xpolicy,
        'OSSAccessKeyId': accessKeyId,
        'success_action_status': '200',
        'signature': signature
    }
    data_file = {
        'file': ('blob', open(getenv('CONFIG_PHOTO'), 'rb'), 'image/jpg')
    }
    session.post(url=url, data=data, files=data_file)
    url = 'https://{host}/wec-counselor-sign-apps/stu/sign/previewAttachment'.format(host=HOST)
    data = {
        'ossKey': fileName
    }
    res = session.post(url=url, headers={'content-type': 'application/json'}, data=json.dumps(data))
    photoUrl = res.json().get('datas')
    return photoUrl


# 登陆并获取session
def getSession():
    params = {
        'login_url': getenv('CONFIG_URL'),
        'needcaptcha_url': '',
        'captcha_url': '',
        'username': USER_NAME,
        'password': getenv('CONFIG_PASSWORD')
    }

    cookies = {}
    log('正在登陆并获取cookie...')
    res = requests.post(url=getenv('CONFIG_API'), data=params).json()
    # cookieStr可以使用手动抓包获取到的cookie，有效期暂时未知，请自己测试
    cookieStr = str(res['cookies'])
    if cookieStr == 'None':
        raise Exception(res['msg'])
    # 解析cookie
    for line in cookieStr.split(';'):
        name, value = line.strip().split('=', 1)
        cookies[name] = value
    session = requests.session()
    session.cookies = requests.utils.cookiejar_from_dict(cookies, cookiejar=None, overwrite=True)
    return session


# 获取最新未签到任务
def getUnSignedTasks(session):
    headers = {
        'Accept': 'application/json, text/plain, */*',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.97 Safari/537.36',
        'content-type': 'application/json',
        'Accept-Encoding': 'gzip,deflate',
        'Accept-Language': 'zh-CN,en-US;q=0.8',
        'Content-Type': 'application/json;charset=UTF-8'
    }
    # 请求每日签到任务接口
    log('获取签到任务ID中...')
    res = session.post(
        url='https://{host}/wec-counselor-sign-apps/stu/sign/getStuSignInfosInOneDay'.format(host=HOST),
        headers=headers, data=json.dumps({}))

    if len(res.json()['datas']['unSignedTasks']) < 1:
        raise Exception('当前没有未签到任务')
    latestTask = res.json()['datas']['unSignedTasks'][0]
    return {
        'signInstanceWid': latestTask['signInstanceWid'],
        'signWid': latestTask['signWid']
    }


# 获取签到任务详情
def getDetailTask(session, params):
    headers = {
        'Accept': 'application/json, text/plain, */*',
        'User-Agent': 'Mozilla/5.0 (Linux; Android 10; EBG-AN00 Build/HUAWEIEBG-AN00; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/78.0.3904.108 Mobile Safari/537.36  cpdaily/8.2.20 wisedu/8.2.20',
        'content-type': 'application/json',
        'Accept-Encoding': 'gzip,deflate',
        'Accept-Language': 'zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7',
        'Content-Type': 'application/json;charset=UTF-8'
    }
    log('获取签到任务内容中...')
    res = session.post(
        url='https://{host}/wec-counselor-sign-apps/stu/sign/detailSignInstance'.format(host=HOST),
        headers=headers, data=json.dumps(params))
    data = res.json()['datas']
    return data


# 填充表单
def fillForm(task, session):
    log('正在填充签到内容...')
    form = {}
    if task['isPhoto'] == 1:
        form['signPhotoUrl'] = uploadPicture(session)
    else:
        form['signPhotoUrl'] = ''
    if task['isNeedExtra'] == 1:
        form['isNeedExtra'] = 1
        extraFields = task['extraField']

        defaults = CONFIG['cpdaily']['defaults']
        extraFieldItemValues = []
        for i in range(0, len(extraFields)):
            default = defaults[i]['default']
            extraField = extraFields[i]
            if default['title'] != extraField['title']:
                raise Exception('第%d个默认配置项错误，请检查' % (i + 1))
            extraFieldItems = extraField['extraFieldItems']
            for extraFieldItem in extraFieldItems:
                if extraFieldItem['content'] == default['value']:
                    extraFieldItemValue = {'extraFieldItemValue': default['value'],
                                           'extraFieldItemWid': extraFieldItem['wid']}
                    # 其他，额外文本
                    if extraFieldItem['isOtherItems'] == 1:
                        extraFieldItemValue = {'extraFieldItemValue': default['other'],
                                               'extraFieldItemWid': extraFieldItem['wid']}
                    extraFieldItemValues.append(extraFieldItemValue)
        form['extraFieldItems'] = extraFieldItemValues

    # form['signInstanceWid'] = params['signInstanceWid']
    form['signInstanceWid'] = task['signInstanceWid']
    form['longitude'] = getenv('CONFIG_LON')
    form['latitude'] = getenv('CONFIG_LAT')
    form['isMalposition'] = task['isMalposition']
    form['abnormalReason'] = ''
    form['position'] = getenv('CONFIG_ADDRESS')
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
def submitForm(session, form):
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
    res = session.post(url='https://{host}/wec-counselor-sign-apps/stu/sign/submitSign'.format(host=HOST),
                       headers=headers, data=json.dumps(form))
    message = res.json()['message']
    if message == 'SUCCESS':
        log('签到成功')
    else:
        raise Exception('签到失败，原因是：' + message)


# 主函数
def main():
    session = getSession()
    params = getUnSignedTasks(session)
    task = getDetailTask(session, params)
    form = fillForm(task, session)
    submitForm(session, form)


if __name__ == '__main__':
    main()
