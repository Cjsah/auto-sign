# -*- coding: utf-8 -*-
# by Cjsah

##########################
#   此自动填表已好久没更新   #
#     想使用请自己修改      #
##########################

import json, yaml, uuid
from sign import getCookie, getenv, DESEncrypt


# 读取yml配置
def getYmlConfig(yaml_file='config.yml'):
    with open(yaml_file, 'r', encoding="utf-8")as f:
        return dict(yaml.load(f.read(), Loader=yaml.FullLoader))


# 全局配置
config = getYmlConfig(yaml_file='config.yml')
host = getenv('CONFIG_HOST')


# 获取最新未填写表单
def getUnSignedTasks(session):
    headers = {
        'Accept': 'application/json, text/plain, */*',
        'User-Agent': 'Mozilla/5.0 (Linux; Android 10; EBG-AN00 Build/HUAWEIEBG-AN00; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/78.0.3904.108 Mobile Safari/537.36  cpdaily/8.2.14 wisedu/8.2.14',
        'content-type': 'application/json',
        'Accept-Encoding': 'gzip,deflate',
        'Accept-Language': 'zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7',
        'Content-Type': 'application/json;charset=UTF-8'
    }
    # 第一次请求表单列表，获取id
    res = session.post(
        url='https://{host}/wec-counselor-collector-apps/stu/collector/queryCollectorProcessingList'.format(host=host),
        headers=headers, data=json.dumps({})).json()['datas']
    if res['totalSize'] == 0:
        raise Exception('当前没有未提交表单')
    for i in res['rows']:
        if i['subject'].endswith("疫情防控健康信息统计"):
            res = i
    formWid = res['formWid']
    collectorWid = res['wid']
    schoolTaskWid = "118127"
    # 第二次请求请求表单内容，拿到具体的表单
    res = session.post(
        url='https://{host}/wec-counselor-collector-apps/stu/collector/getFormFields'.format(host=host),
        headers=headers, data=json.dumps({"formWid": formWid, "collectorWid": collectorWid})).json()['datas']['rows']
    return {'formWid': formWid, 'collectWid': collectorWid, 'schoolTaskWid': schoolTaskWid, 'form': res}


# 填充表单
def fillForm(params):
    newparams = {
        'address': getenv('CONFIG_ADDRESS'),
        'formWid': params['formWid'],
        'collectWid': params['collectWid'],
        'schoolTaskWid': params['schoolTaskWid'],
        'uaIsCpadaily': True
    }
    test = {'form': []}
    for param in params['form']:
        for i in param['fieldItems']:
            if i['isSelected'] == 1:
                param['fieldItems'] = [i]
                param['value'] = i['itemWid']
        if param['title'] == '目前所在地区':
            param['area1'] = param['value'].split("/")[0]
            param['area2'] = param['value'].split("/")[1]
            param['area3'] = param['value'].split("/")[2]
        test['form'].append(param)
    newparams['form'] = params['form']
    return newparams


# 提交表单
def submitForm(session, form):
    extension = {
        "lon": getenv('CONFIG_LON'),
        "model": "OPPO R11 Plus",
        "appVersion": "8.1.14",
        "systemVersion": "8.0",
        "userId": getenv('CONFIG_USERNAME'),
        "systemName": "android",
        "lat": getenv('CONFIG_LAT'),
        "deviceId": str(uuid.uuid1())
    }

    headers = {
        'User-Agent': 'Mozilla/5.0 (Linux; Android 4.4.4; OPPO R11 Plus Build/KTU84P) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/33.0.0.0 Safari/537.36 okhttp/3.12.4',
        'CpdailyStandAlone': '0',
        'extension': '1',
        # 不知道能用多久
        'Cpdaily-Extension': DESEncrypt(json.dumps(extension)),
        'Content-Type': 'application/json; charset=utf-8',
        'Accept-Encoding': 'gzip',
        'Connection': 'Keep-Alive'
    }
    message = session.post(url='https://{host}/wec-counselor-collector-apps/stu/collector/submitForm'.format(host=host),
                           headers=headers, data=json.dumps(form)).json()['message']
    if message == 'SUCCESS':
        print('表单提交成功')
    else:
        raise Exception('表单提交失败，原因是：' + message)


# 主函数
def main():
    session = getCookie()
    params = getUnSignedTasks(session)
    form = fillForm(params)
    submitForm(session, form)


if __name__ == '__main__':
    main()
