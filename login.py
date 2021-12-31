# -*- coding: utf-8 -*-
# by Cjsah
import requests
from bs4 import BeautifulSoup
from urllib3.exceptions import InsecureRequestWarning

# noinspection PyUnresolvedReferences
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)


class Login:
    def __init__(self, username, password, login_url, session):
        """
        初始化登陆信息

        :param username: 用户名
        :param password: 密码
        :param login_url: 登陆网址
        :param session: session
        """
        self.username = username
        self.password = password
        self.url = login_url
        self.session = session

    def login(self):
        """
        登陆

        :return: cookie
        """
        res = self.session.get(url=self.url)  # 获取cookie和表单
        soup = BeautifulSoup(res.text, 'lxml')
        form = soup.select('#casLoginForm')
        if len(form) == 0:
            raise Exception('出错啦！网页中没有找到casLoginForm')
        params = {}
        soup = BeautifulSoup(str(form[0]), 'lxml')  # 读取网页中的表单
        form = soup.select('input')
        for item in form:
            if None is not item.get('name') and len(item.get('name')) > 0:
                if item.get('name') != 'rememberMe':
                    if None is item.get('value'):
                        params[item.get('name')] = ''
                    else:
                        params[item.get('name')] = item.get('value')
        params['username'] = self.username  # 更新用户名密码
        params['password'] = self.password
        res = self.session.post(url=self.url, data=params, allow_redirects=False)   # 登陆
        if res.status_code == 302:  # 如果是302强制跳转代表登陆成功
            jump_url = res.headers['Location']
            self.session.get(jump_url, verify=False)    # 更新cookie
            return self.session.cookies
        else:
            raise Exception('登录失败, 请重试!')
