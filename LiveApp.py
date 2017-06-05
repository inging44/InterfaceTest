#!/usr/bin/env python
# coding=utf-8

# 接口自动化测试

import model
import logging
import os

# 打印日志
log_file = os.path.join(os.getcwd(),'log/liveappapi.log')
log_format = '[%(asctime)s] [%(levelname)s] %(message)s'
logging.basicConfig(format=log_format,filename=log_file,filemode='w',level=logging.DEBUG)
console = logging.StreamHandler()
console.setLevel(logging.DEBUG)
formatter = logging.Formatter(log_format)
console.setFormatter(formatter)
logging.getLogger('').addHandler(console)

def main():
    errorTest = model.runTest('TestCase/TestCase.xlsx')
    if len(errorTest) > 0:
        html = '<html><body>接口自动化定期扫描，共有 ' + str(len(errorTest)) + ' 个异常接口，列表如下：' + '</p><table><tr><th style="width:100px;">接口</th><th style="width:50px;">状态</th><th style="width:200px;">接口地址</th><th>接口返回值</th></tr>'
        for test in errorTest:
            html = html + '<tr><td>' + test[0] + '</td><td>' + test[1] + '</td><td>' + test[2] + '</td><td>' + test[3] + '</td></tr>'
        html = html + '</table></body></html>'
        # model.sendMail(html)
    else:
        print('成功！')

if __name__ == '__main__':
    main()
