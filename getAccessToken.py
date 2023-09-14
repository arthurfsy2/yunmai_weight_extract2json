import time
import hashlib
import requests
import argparse
import json
import sys

parser = argparse.ArgumentParser()
parser.add_argument("nickname", help="输入该体重的用户名")        
options = parser.parse_args()


nickname = options.nickname

# 读取JSON文件内容
with open(f"userinfo_{nickname}.json", "r",encoding="utf-8") as f:
    content = f.read()

# 将内容解析为字典
arr = json.loads(content)

# 提取字段值
userId_real = arr.get("userId_real")
refreshToken = arr.get("refreshToken")
realName = arr.get("realName")
account_b64 = arr.get("account_b64")
password_RSA = arr.get("password_RSA")



#构建tokenSign
def construct_tokensign(account_b64, password_RSA):
    timestamp = str(int(time.time()))
    code = timestamp[:8] + "00"
    tokensign = "code=" + code + "&refreshToken=" + refreshToken + "&signVersion=3&versionCode=2&secret=AUMtyBDV3vklBr6wtA2putAMwtmVcD5b"

    return tokensign
tokensign = construct_tokensign(account_b64, password_RSA)
#print(f"tokensign: {tokensign}\n\n")

#对tokensign进行md5加密
def md5(tokensign):
    md5 = hashlib.md5()
    md5.update(tokensign.encode('utf-8'))
    encrypted_string = md5.hexdigest()
    return encrypted_string


#构建token.d请求头参数data:payload
def construct_payload(tokensign):
    timestamp = str(int(time.time()))
    code = timestamp[:8] + "00"
    payload = (
        
        "code=" + code + "&refreshToken=" + refreshToken + "&sign="+md5(tokensign)+"&signVersion=3&versionCode=2"
    )
    return payload
payload = construct_payload(tokensign)
#print(f"payload: {payload}\n\n")

token_url = "https://account.iyunmai.com/api/android///auth/token.d"


token_headers = {
    'Host': 'account.iyunmai.com',
    'Content-Type': 'application/x-www-form-urlencoded',
    'Accept-Encoding': 'gzip',
    'Connection':'keep-alive',
    'Accept': '*/*',
    'User-Agent': 'google/android(10,29) channel(huawei) app(4.25,42500010)screen(w,h=1080,1794)/scale',
    'IssignV1': 'open',
    'Accept-Language': 'zh-Hans-CN;q=1, en-CN;q=0.9',
}

#构建token.d请求参数
def getAccesstoken_request(url, headers,payload):
    
    response = requests.post(url, headers=headers, data=payload)
    json_data = response.json()
    return json_data

#获取Access_token数据并保存结果
getAccesstoken_result = getAccesstoken_request(token_url, token_headers,payload)
#print(getAccesstoken_result)
getAccesstoken_stat = getAccesstoken_result['result']['msg']


if getAccesstoken_result['result']['code'] ==0:
    print(f"Access_token获取结果: {getAccesstoken_stat}\n\n")
    accessToken = getAccesstoken_result['data']['accessToken']
else:
    print(f"Access_token获取结果: {getAccesstoken_stat}\n\n")
    sys.exit()

timestamp = str(int(time.time()))
timestamp_past = str(int(time.time()) - 9999 * 24 * 60 * 60) #取当前时间前9999天为需要截取的时间段
code = timestamp
startTime = timestamp_past

#构建chart-list.json请求链接
data_url = f"https://data.iyunmai.com/api/ios/scale/chart-list.json?code={code}&signVersion=3&startTime={startTime}&userId={userId_real}&versionCode=2"

#print(f"data_url: {data_url}\n\n")

#构建chart-list.json请求头
data_headers = {
    'Host': 'account.iyunmai.com',
    'Content-Type': 'application/x-www-form-urlencoded',
    'Accept-Encoding': 'gzip',
    'Connection':'keep-alive',
    'Accept': '*/*',
    'User-Agent': 'google/android(10,29) channel(huawei) app(4.25,42500010)screen(w,h=1080,1794)/scale',
    'accessToken': accessToken,
    'IssignV1': 'open',
    'Accept-Language': 'zh-Hans-CN;q=1, en-CN;q=0.9',
}

#构建chart-list.json获取重量数据请求参数
def getWeight_request(url, headers,payload):
    
    response = requests.get(url, headers=headers, data=payload)
    json_data = response.json()
    json_data = json_data
    
    return json_data

#获取体重数据并保存结果
getWeight_stat = getWeight_request(data_url, data_headers,payload)
weight_data = getWeight_stat['data']['rows']
json_data = json.dumps(weight_data)

#print(f"weight_data: {weight_data}\n\n")

with open(f'weight_{nickname}.json', 'w',encoding="utf-8") as f:
    #json_data = black.format_str(json_data, mode=black.FileMode())
    f.write(json_data)
    print(f"weight_{nickname}.json写入成功！")
