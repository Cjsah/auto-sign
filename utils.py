# -*- coding: utf-8 -*-
# by Cjsah

import random, json, base64, pyaes, smtplib
from datetime import datetime, timezone, timedelta
from pyDes import des, CBC, PAD_PKCS5
from email.mime.text import MIMEText
from os import getenv

DES_KEY = 'b3L26XNL'
AES_KEY = 'ytUQ7l2ZZu8mLvJZ'
HOST = getenv('CONFIG_HOST')
USER_NAME = getenv('CONFIG_USERNAME')
PASSWORD = getenv('CONFIG_PASSWORD')
ADDRESS = getenv('CONFIG_ADDRESS')
LOGIN_URL = getenv('CONFIG_URL')
LON = getenv('CONFIG_LON')
LAT = getenv('CONFIG_LAT')
MAIL_HOST = getenv('MAIL_HOST')
MAIL_USER = getenv('MAIL_USER')
MAIL_PASS = getenv('MAIL_PASS')
MAIL_RECEIVER = getenv('MAIL_RECEIVER')


def log(value):
    """
    输出日志

    :param value: 输出内容
    """
    utc_dt = datetime.utcnow().replace(tzinfo=timezone.utc)
    asia_dt = utc_dt.astimezone(timezone(timedelta(hours=8)))
    print(asia_dt.strftime("[%Y-%m-%d %H:%M:%S]"), value)


def GenDeviceID():
    """
    生成设备id
    根据用户账号生成
    保证同一学号每次执行时 deviceID 不变
    可以避免辅导员看到用新设备签到

    :return: deviceID
    """
    deviceId = ''
    random.seed(USER_NAME.encode('utf-8'))
    for i in range(8):
        num = random.randint(97, 122)
        if (num * i + random.randint(1, 8)) % 3 == 0:
            deviceId = deviceId + str(num % 9)
        else:
            deviceId = deviceId + chr(num)
    deviceId = deviceId + 'OPPO R11 Plus'
    return deviceId


def DESEncrypt(s, salt=DES_KEY):
    """
    DES 加密

    :param s: 加密内容
    :param salt: 秘钥
    :return: 解密结果
    """
    log('Extension加密中...')
    iv = b"\x01\x02\x03\x04\x05\x06\x07\x08"
    k = des(salt, CBC, iv, pad=None, padmode=PAD_PKCS5)
    encrypt_str = k.encrypt(s)
    return base64.b64encode(encrypt_str).decode()


def AESEncrypt(s, salt=AES_KEY):
    """
    AES 加密

    :param s: 加密内容
    :param salt: 秘钥
    :return: 加密结果
    """
    log('bodyString加密中...')
    iv = b"\x01\x02\x03\x04\x05\x06\x07\x08\t\x01\x02\x03\x04\x05\x06\x07"
    encrypter = pyaes.Encrypter(pyaes.AESModeOfOperationCBC(salt.encode('utf-8'), iv))
    encrypted = encrypter.feed(s)
    encrypted += encrypter.feed()
    return base64.b64encode(encrypted).decode()


def uploadPicture(session):
    """
    上传图片并返回图片地址

    :param session:
    :return: url地址
    """
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


def sendEmail(message):
    message = MIMEText(message, 'plain', 'utf-8')
    message['Subject'] = '签到失败通知'
    message['From'] = MAIL_USER
    message['To'] = MAIL_RECEIVER
    log('正在连接邮件服务器...')
    smtpObj = smtplib.SMTP_SSL(MAIL_HOST)
    smtpObj.connect(MAIL_HOST, smtplib.SMTP_SSL_PORT)
    log('正在登陆邮件服务器...')
    smtpObj.login(MAIL_USER, MAIL_PASS)
    log('正在发送邮件...')
    smtpObj.sendmail(MAIL_USER, MAIL_RECEIVER, message.as_string())
    smtpObj.quit()
    log('发送成功')
