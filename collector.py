# -*- coding: utf-8 -*-
import json, yaml, requests
from urllib.parse import urlparse


# 读取yml配置
def getYmlConfig(yaml_file='config.yml'):
    with open(yaml_file, 'r', encoding="utf-8")as f:
        return dict(yaml.load(f.read(), Loader=yaml.FullLoader))


# 全局配置
config = getYmlConfig(yaml_file='config.yml')


# 获取今日校园api
def getCpdailyApis(user):
    apis = {}
    user = user['user']
    schools = requests.get(url='https://mobile.campushoy.com/v6/config/guest/tenant/list').json()['data']
    flag = True
    for one in schools:
        if one['name'] == user['school']:
            if one['joinType'] == 'NONE':
                raise Exception(user['school'] + ' 未加入今日校园')
            flag = False
            data = requests.get(url='https://mobile.campushoy.com/v6/config/guest/tenant/info', params={'ids': one['id']}).json()['data'][0]
            for i in " 2":
                ampUrl = data['ampUrl' + i.replace(" ", "")]
                if 'campusphere' in ampUrl or 'cpdaily' in ampUrl:
                    parse = urlparse(ampUrl)
                    host = parse.netloc
                    res = requests.get(parse.scheme + '://' + host)
                    parse = urlparse(res.url)
                    apis['login-url'] = data['idsUrl'] + '/login?service=' + parse.scheme + r"%3A%2F%2F" + host + r'%2Fportal%2Flogin'
                    apis['host'] = host
            break
    if flag:
        raise Exception(user['school'] + ' 未找到该院校信息，请检查是否是学校全称错误')
    return apis


# 登陆并获取session
def getSession(user, apis):
    user = user['user']
    params = {
        'login_url': apis['login-url'],
        'needcaptcha_url': '',
        'captcha_url': '',
        'username': user['username'],
        'password': user['password']
    }

    cookies = {}
    while True:
        res = requests.post(url=config['login']['api'], data=params).json()
        if res['cookies'] is not None:
            break
    # 可以手动抓包，有效期未知
    cookieStr = str(res['cookies'])

    # 解析cookie
    for line in cookieStr.split(';'):
        name, value = line.strip().split('=', 1)
        cookies[name] = value
    session = requests.session()
    session.cookies = requests.utils.cookiejar_from_dict(cookies, cookiejar=None, overwrite=True)
    return session


# 获取最新未填写表单
def getUnSignedTasks(session, apis):
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
        url='https://{host}/wec-counselor-collector-apps/stu/collector/queryCollectorProcessingList'.format(host=apis['host']),
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
        url='https://{host}/wec-counselor-collector-apps/stu/collector/getFormFields'.format(host=apis['host']),
        headers=headers, data=json.dumps({"formWid": formWid, "collectorWid": collectorWid})).json()['datas']['rows']
    return {'formWid': formWid, 'collectWid': collectorWid, 'schoolTaskWid': schoolTaskWid, 'form': res}


# 填充表单
def fillForm(params, user):
    newparams = {
        'address': user['user']['address'],
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
def submitForm(session, form, apis):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Linux; Android 4.4.4; OPPO R11 Plus Build/KTU84P) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/33.0.0.0 Safari/537.36 okhttp/3.12.4',
        'CpdailyStandAlone': '0',
        'extension': '1',
        # 不知道能用多久
        'Cpdaily-Extension': '6XkC1UAk07fK0uTaGPUu77i/+r7j/o1JQ/XygRxee2LMiX5H+w/BOrLr7jYWHhkJVNPbxAQdqNhuzxEyfNoRXXrh5mFDOJl8lBoTx0ZrJpwswz5Y2eq/12kdxcLSc3ZwDKxhb0YJRgCTKSPUZYeMkzWN5hhJfaCFH07yuG70CLuXweFyEA2OjaGBokHe2+T55dvzqWoQbisSBVBm8vTe5RByGWyCQHQarTT1rroogTzSR7HjobDgMA==',
        'Content-Type': 'application/json; charset=utf-8',
        'Accept-Encoding': 'gzip',
        'Connection': 'Keep-Alive'
    }
    message = session.post(url='https://{host}/wec-counselor-collector-apps/stu/collector/submitForm'.format(host=apis['host']),
                           headers=headers, data=json.dumps(form)).json()['message']
    if message == 'SUCCESS':
        print('表单提交成功')
    else:
        raise Exception('表单提交失败，原因是：' + message)


# 主函数
def main():
    for user in config['users']:
        apis = getCpdailyApis(user)
        session = getSession(user, apis)
        params = getUnSignedTasks(session, apis)
        form = fillForm(params, user)
        submitForm(session, form, apis)


# 给腾讯云
# noinspection PyUnusedLocal
def main_handler(event, context):
    while True:
        try:
            main()
        except Exception as e:
            raise e
        else:
            return 'success'


if __name__ == '__main__':
    # print(extension)
    print(main_handler({}, {}))
