#!/usr/bin/env python
# coding=utf-8

import json
import http.client,mimetypes
from urllib.parse import urlencode
import random
import time
import re
import logging
import os,sys
import xlrd
from pyDes import *
import hashlib
import base64
import smtplib
from email.mime.text import MIMEText



# # 打印日志
# log_file = os.path.join(os.getcwd(),'log/liveappapi.log')
# log_format = '[%(asctime)s] [%(levelname)s] %(message)s'
# logging.basicConfig(format=log_format,filename=log_file,filemode='w',level=logging.DEBUG)
# console = logging.StreamHandler()
# console.setLevel(logging.DEBUG)
# formatter = logging.Formatter(log_format)
# console.setFormatter(formatter)
# logging.getLogger('').addHandler(console)


# 反转字典的键和值
def invert_dict(d):
    return dict((v, k) for k, v in d.iteritems())


# 获取用例并执行测试用例
def runTest(testCase_file, sheet_name):
    # 读取文件
    testCaseFile = os.path.join(os.getcwd(), testCase_file)
    if not os.path.exists(testCaseFile):
        logging.error('测试用例文件不存在！！！')
        sys.exit()
    testCase = xlrd.open_workbook(testCaseFile)
    # 读取第一个sheet
    table = testCase.sheet_by_name(sheet_name)
    # 初始化失败case
    errorCase = []
    correlationDict = {}
    correlationDict['${hashPassword}'] = hash1Encode('123456')
    correlationDict['${session}'] = None

    # 将列名组装成字典（列名为键，列数为值）
    row_name = table.row_values(1)
    row_val = []
    for i in range(0, len(row_name)):
        row_val.append(i)
    # 将row_name、row_val两个列表组合成字典
    rows = dict(zip(row_name, row_val))

    for i in range(2, table.nrows):
        correlationDict['${randomEmail}'] = ''.join(random.sample('abcdefghijklmnopqrstuvwxyz', 6)) + '@automation.test'
        correlationDict['${randomTel}'] = '186' + str(random.randint(10000000, 99999999))
        correlationDict['${timestamp}'] = int(time.time())
        if table.cell(i, rows['Active']).value.replace('\n', '').replace('\r', '') != 'Yes':
            continue
        request_url = table.cell(i, rows['Request URL']).value.replace('\n', '').replace('\r', '')
        num = table.cell(i, rows['No.']).value.replace('\n', '').replace('\r', '')
        if request_url == '' or num == '':
            print('sth empty')
            continue
        api_purpose = table.cell(i, rows['API Purpose']).value.replace('\n', '').replace('\r', '')
        api_host = table.cell(i, rows['API Host']).value.replace('\n', '').replace('\r', '')

        request_method = table.cell(i, rows['Request Method']).value.replace('\n', '').replace('\r', '')
        request_data_type = table.cell(i, rows['Request Data Type']).value.replace('\n', '').replace('\r', '')
        request_data = table.cell(i, rows['Request Data']).value.replace('\n', '').replace('\r', '')
        encryption = table.cell(i, rows['Encryption']).value.replace('\n', '').replace('\r', '')
        check_point = table.cell(i, rows['Check Point']).value
        correlation = table.cell(i, rows['Correlation']).value.replace('\n', '').replace('\r', '').split(';')
        isContains = table.cell(i, rows['isContains']).value.replace('\n', '').replace('\r', '')
        for key in correlationDict:
            if request_url.find(key) > 0:
                request_url = request_url.replace(key, str(correlationDict[key]))
        if request_data_type == 'Form':
            dataFile = request_data
            if os.path.exists(dataFile):
                fopen = open(dataFile, encoding='utf-8')
                request_data = fopen.readline()
                fopen.close()
            for keyword in correlationDict:
                if request_data.find(keyword) > 0:
                    request_data = request_data.replace(keyword, str(correlationDict[keyword]))
            try:
                if encryption == 'MD5':
                    request_data = json.loads(request_data)
                    status, md5 = getMD5(api_host, urlencode(request_data).replace("%27", "%22"))
                    if status != 200:
                        logging.error(num + ' ' + api_purpose + "[ " + str(status) + " ], 获取md5验证码失败！！！")
                        continue
                    request_data = dict(request_data, **{"sign": md5.decode("utf-8")})
                    request_data = urlencode(request_data).replace("%27", "%22")
                elif encryption == 'DES':
                    request_data = json.loads(request_data)
                    request_data = urlencode({'param': encodePostStr(request_data)})
                else:
                    request_data = urlencode(json.loads(request_data))
            except Exception as e:
                logging.error(num + ' ' + api_purpose + ' 请求的数据有误，请检查[Request Data]字段是否是标准的json格式字符串！')
                continue
        elif request_data_type == 'Data':
            dataFile = request_data
            if os.path.exists(dataFile):
                fopen = open(dataFile, encoding='utf-8')
                request_data = fopen.readline()
                fopen.close()
            for keyword in correlationDict:
                if request_data.find(keyword) > 0:
                    request_data = request_data.replace(keyword, str(correlationDict[keyword]))
            request_data = request_data.encode('utf-8')
        elif request_data_type == 'File':
            dataFile = request_data
            if not os.path.exists(dataFile):
                logging.error(num + ' ' + api_purpose
                              + ' 文件路径配置无效，请检查[Request Data]字段配置的文件路径是否存在！！！')
                continue
            fopen = open(dataFile, 'rb')
            data = fopen.read()
            fopen.close()
            request_data = '''
                ------WebKitFormBoundaryDf9uRfwb8uzv1eNe
                Content-Disposition:form-data;name="file";filename="%s"
                Content-Type:
                Content-Transfer-Encoding:binary
                %s
                ------WebKitFormBoundaryDf9uRfwb8uzv1eNe--
            ''' % (os.path.basename(dataFile), data)
        status, resp = interfaceTest(num, api_purpose, api_host, request_url, request_data, check_point, request_method,
                                     request_data_type, correlationDict['${session}'], isContains)
        # 判断请求结果
        if status != 200:
            errorCase.append((num + ' ' + api_purpose, str(status), 'http://' + api_host + request_url, resp))
            continue
        for j in range(len(correlation)):
            param = correlation[j].split('=')
            if len(param) == 2:
                if param[1] == '' or not re.search(r'^\[', param[1]) or not re.search(r'\]$', param[1]):
                    logging.error(num + ' ' + api_purpose + ' 关联参数设置有误，请检查[Correlation]字段参数格式是否正确！！！')
                    continue
                value = resp
                for key in param[1][1:-1].split(']['):
                    try:
                        temp = value[int(key)]
                    except:
                        try:
                            temp = value[key]
                        except:
                            break
                    value = temp
                correlationDict[param[0]] = value
    return errorCase


# 接口测试
def interfaceTest(num, api_purpose, api_host, request_url, request_data, check_point, request_method, request_data_type,
                  session,isContains):
    headers = {'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
               'X-Requested-With': 'XMLHttpRequest',
               'Connection': 'keep-alive',
               'CLIENT': 'WEB',
               'Referer': 'http://' + api_host,
               'sign': 'AAA',
               'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 9_1 like Mac OS X) AppleWebKit/601.1.46 (KHTML, like Gecko) Version/9.0 Mobile/13B143 Safari/601.1'}
    if session is not None:
        headers['Cookie'] = 'session=' + session
        if request_data_type == 'File':
            headers[
                'Content-Type'] = 'multipart/form-data;boundary=----WebKitFormBoundaryDf9uRfwb8uzv1eNe;charset=UTF-8'
        elif request_data_type == 'Data':
            headers['Content-Type'] = 'text/plain; charset=UTF-8'

    conn = http.client.HTTPConnection(api_host)
    if request_method == 'POST':
        conn.request('POST', request_url, request_data, headers=headers)
    elif request_method == 'GET':
        conn.request('GET', request_url + '?' + request_data, headers=headers)
    else:
        logging.error(num + ' ' + api_purpose + ' HTTP请求方法错误，请确认[Request Method]字段是否正确！！！')
        return 400, request_method
    response = conn.getresponse()
    status = response.status
    resp = response.read()
    if status == 200:
        resp = resp.decode('utf-8').replace('\n\t\t', '').replace(' ', '')
        result = str(resp).find(check_point.replace(' ', ''))
        if result == 1 if isContains == 'Yes' else result == -1:
            logging.info(num + ' ' + api_purpose + ' 成功, ' + str(status) + ', ' + str(resp))
            return status, json.loads(resp)
        else:
            logging.error(num + ' ' + api_purpose + ' 操作失败！！！, [ ' + str(status) + ' ], ' + str(resp))
            return 2001, resp
    else:
        logging.error(num + ' ' + api_purpose + ' 请求失败！！！, [ ' + str(status) + ' ], ' + str(resp))
        return status, resp.decode('utf-8')


# 获取md5验证码
def getMD5(url, postData):
    headers = {'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
               'X-Requested-With': 'XMLHttpRequest'}
    conn = http.client.HTTPConnection('this.ismyhost.com')
    conn.request('POST', '/get_isignature', postData, headers=headers)
    response = conn.getresponse()
    return response.status, response.read()


# hash1加密
def hash1Encode(codeStr):
    hashobj = hashlib.sha1()
    hashobj.update(codeStr.encode('utf-8'))
    return hashobj.hexdigest()


# DES加密
def desEncode(desStr):
    k = des('secretKEY', padmode=PAD_PKCS5)
    encodeStr = base64.b64encode(k.encrypt(json.dumps(desStr)))
    return encodeStr


# 字典排序
def encodePostStr(postData):
    keyDict = {'key': 'secretKEY'}
    mergeDict = dict(postData, **keyDict)
    mergeDict = sorted(mergeDict.items())
    postStr = ''
    for i in mergeDict:
        postStr = postStr + i[0] + '=' + i[1] + '&'
    postStr = postStr[:-1]
    hashobj = hashlib.sha1()
    hashobj.update(postStr.encode('utf-8'))
    token = hashobj.hexdigest()
    postData['token'] = token
    return desEncode(postData)


# 发送通知邮件
def sendMail(text):
    sender = '13990122270@163.com'
    receiver = ['huanglanting@kuaijiankang.com']
    mailToCc = ['738631563@qq.com']
    subject = '接口自动化测试报告通知'
    smtpserver = 'smtp.163.com'
    username = '13990122270@163.com'
    password = 'qwertyuioplmn123'

    msg = MIMEText(text, 'html', 'utf-8')
    msg['Subject'] = subject
    msg['From'] = sender
    msg['To'] = ';'.join(receiver)
    msg['Cc'] = ';'.join(mailToCc)
    try:
        smtp = smtplib.SMTP(smtpserver)
        # smtp.docmd("EHLO server")
        # smtp.starttls()
        # smtp.EnableSsl = True
        # smtp.set_debuglevel(1)
        # smtp.connect(smtpserver)
        # smtp.docmd("AUTH LOGIN")
        smtp.login(username, password)
        smtp.sendmail(sender, receiver + mailToCc, msg.as_string())
        print('email success!!!!!!!!!!')
        smtp.quit()
    except Exception as e:  # 如果 try 中的语句没有执行，则会执行下面的 ret=False
        print(e)
        print('email wrong')


