# -*- coding: utf-8 -*-
# by Cjsah
import sys

from logger import err, log
import sign, collector

if __name__ == '__main__':
    if len(sys.argv) == 1:
        err('请输入要实现的功能(sign/collector)')
    type = sys.argv[1]
    exe = None
    if type == 'sign':
        exe = sign
    elif type == 'collector':
        exe = collector
    else:
        err("功能 '{}' 不存在".format(type))
    log('正在执行 {} 功能...'.format(exe.__name__))
    exe.run()

