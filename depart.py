# -*- coding: utf-8 -*-
# by Cjsah
import re, sys
from logger import err, log

if len(sys.argv) == 1:
    err('请输入要分割的代码块(daily/holiday)')

files = ['sign.py']

start = '# # # # # <- {} -> # # # # #\n'.format(sys.argv[1])
match = '# # # # # <- (.*?) -> # # # # #\n'
end = '# # # # # <- end -> # # # # #\n'

for file in files:
    with open(file, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    result = []

    put = True
    for line in lines:
        putLine = True
        if re.match(match, line):
            putLine = False
        if re.match(match, line) and line != start and line != end:
            put = False
        if putLine and put:
            result.append(line)
        if line == end:
            put = True

    with open(file, 'w+', encoding='utf-8') as f:
        for line in result:
            f.write(line)

log('完成')
