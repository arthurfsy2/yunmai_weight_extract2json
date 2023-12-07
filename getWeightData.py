import base64
import urllib.parse
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_v1_5
import time
import hashlib
import requests
import json
import argparse
import sys

parser = argparse.ArgumentParser()
parser.add_argument("input_string", help="输入:'用户名/密码/昵称'")        
options = parser.parse_args()
input_string = options.input_string

#对原始密码进行加密
def encrypt_account_password(account, password):
    # 账号加密
    account_b64 = base64.b64encode(account.encode()).decode()
    account_URI = urllib.parse.quote(account_b64)

    # 密码RSA公钥加密加密
    rsakey = RSA.importKey('-----BEGIN PUBLIC KEY-----\n'
                           'MFwwDQYJKoZIhvcNAQEBBQADSwAwSAJBAJKcIu+iATe0QPGIVDzMYsMA6kH9FcY9\n'
                           'Or0I4WJJfEgw/N2e0Us/9JVV1CwdV6W2XIl4KqTeH3ydw6tagagPkSsCAwEAAQ==\n'
                           '-----END PUBLIC KEY-----\n')
    cipher = PKCS1_v1_5.new(rsakey)
    cipher_text = base64.b64encode(cipher.encrypt(password.encode('utf-8')))
    password_RSA_orgin = cipher_text.decode('utf-8')
    password_RSA = password_RSA_orgin[:76] + "\n" + password_RSA_orgin[76:88]
    password_URI = urllib.parse.quote(password_RSA)

    return account_b64, account_URI, password_RSA, password_URI

#构建loginSign
def construct_loginsign(account_b64, password_RSA, deviceUUID, userId):
    timestamp = str(int(time.time()))
    code = timestamp[:8] + "00"
    
    userName = account_b64
    password = password_RSA


    loginsign = "code=" + code + "&deviceUUID=" + deviceUUID + "&loginType=1&password=" + password + "\n&signVersion=3&userId=" + userId + "&userName=" + userName + "\n&versionCode=7&secret=AUMtyBDV3vklBr6wtA2putAMwtmVcD5b"


    return loginsign


#对loginsign进行md5加密
def md5(loginsign):
    md5 = hashlib.md5()
    md5.update(loginsign.encode('utf-8'))
    encrypted_string = md5.hexdigest()
    return encrypted_string

#构建login请求头data:payload
def construct_login_payload(password_URI, account_URI, deviceUUID, userId, loginsign):
    timestamp = str(int(time.time()))
    code = timestamp[:8] + "00"
    payload = (
        "password=" + password_URI + "%0A" +
        "&code=" + code +
        "&loginType=1&userName=" + account_URI + "%0A" +
        "&deviceUUID=" + deviceUUID +
        "&versionCode=7&userId=" + userId +
        "&signVersion=3&sign=" + md5(loginsign)
    )
    return payload

#构建tokenSign
def construct_token_payload(refreshToken):
    timestamp = str(int(time.time()))
    code = timestamp[:8] + "00"
    tokensign = "code=" + code + "&refreshToken=" + refreshToken + "&signVersion=3&versionCode=2&secret=AUMtyBDV3vklBr6wtA2putAMwtmVcD5b"
    timestamp = str(int(time.time()))
    code = timestamp[:8] + "00"
    payload = (
        
        "code=" + code + "&refreshToken=" + refreshToken + "&sign="+md5(tokensign)+"&signVersion=3&versionCode=2"
    )
    return payload

#构建token.d请求参数
def get_accesstoken_request(url, headers,payload):
    
    response = requests.post(url, headers=headers, data=payload)
    json_data = response.json()
    return json_data

#构建请求参数
def send_post_request(url, headers,payload):
    
    response = requests.post(url, headers=headers, data=payload)
    json_data = response.json()
    return json_data


#构建chart-list.json获取重量数据请求参数
def get_Weight_request(url, headers,payload):
    
    response = requests.get(url, headers=headers, data=payload)
    json_data = response.json()
    json_data = json_data
    return json_data

def get_refresh_token(account_b64, account_URI, password_RSA, password_URI,nickname):
    url = "https://account.iyunmai.com/api/android//user/login.d"
    headers = {
        'Host': 'account.iyunmai.com',
        'Content-Type': 'application/x-www-form-urlencoded',
        'Accept-Encoding': 'gzip',
        'Connection':'keep-alive',
        'Accept': '*/*',
        'User-Agent': 'google/android(10,29) channel(huawei) app(4.25,42500010)screen(w,h=1080,1794)/scale',
        'IssignV1': 'open',
        'Accept-Language': 'zh-Hans-CN;q=1, en-CN;q=0.9',
    }
    #首次登陆，使用虚拟deviceUUID、userId
    deviceUUID = "abcd"
    userId = "199999999"

    loginsign = construct_loginsign(account_b64, password_RSA, deviceUUID, userId)
    #print(f"loginsign: {loginsign}\n")
    
    payload = construct_login_payload(password_URI, account_URI, deviceUUID, userId, loginsign)
    login_result = send_post_request(url, headers, payload)
    #取返回结果数值
    login_stat= login_result['result']['msg']
    print("————————————————————")  
    if login_result['result']['code'] == 0:   
        print(f"{nickname}登陆状态: {login_stat}")
        userId_real= login_result['data']['userinfo']['userId']
        #print(f"userId_real: {userId_real}\n")
        realName= login_result['data']['userinfo']['realName']
        #print(f"realName: {realName}\n")
        refreshToken = login_result['data']['userinfo']['refreshToken']
        #print(f"refreshToken: {refreshToken}\n")
        
    else:
        print(f"登陆状态: {login_stat}")
        print(f"获取数据失败，已退出")
        sys.exit()
    return refreshToken,userId_real

def get_access_token(payload):
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
    #获取Access_token数据并保存结果
    getAccesstoken_result = get_accesstoken_request(token_url, token_headers,payload)
    #print(getAccesstoken_result)
    getAccesstoken_stat = getAccesstoken_result['result']['msg']

    # 获取accessToken
    if getAccesstoken_result['result']['code'] ==0:
        print(f"Access_token获取结果: {getAccesstoken_stat}")
        accessToken = getAccesstoken_result['data']['accessToken']
    else:
        print(f"Access_token获取结果: {getAccesstoken_stat}")
        accessToken = None

    #print("accessToken",accessToken)
    return accessToken

def getUserData(accessToken,payload,userId_real,nickname):
    timestamp = str(int(time.time()))
    timestamp_past = str(int(time.time()) - 9999 * 24 * 60 * 60) #取当前时间前9999天为需要截取的时间段
    code = timestamp
    startTime = timestamp_past
    #构建chart-list.json请求链接
    data_url = f"https://data.iyunmai.com/api/ios/scale/chart-list.json?code={code}&signVersion=3&startTime={startTime}&userId={userId_real}&versionCode=2"

    #print(f"data_url: {data_url}\n\n")
    # tokensign = construct_token_sign(account_b64, password_RSA, refreshToken)
    # payload = construct_token_payload(tokensign, refreshToken)
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
    # 获取体重数据并保存结果
    
    getWeight_stat = get_Weight_request(data_url, data_headers,payload)
    weight_data = getWeight_stat['data']['rows']
    json_data = json.dumps(weight_data,indent=2)

    #print(f"weight_data: {weight_data}\n\n")

    with open(f'weight_{nickname}.json', 'w',encoding="utf-8") as f:
        #json_data = black.format_str(json_data, mode=black.FileMode())
        f.write(json_data)
        print(f"weight_{nickname}.json写入成功！")
        print("————————————————————")

def getUserInfo(account, password,nickname):
    account_b64, account_URI, password_RSA, password_URI = encrypt_account_password(account, password)
    # 获取refreshToken
    refreshToken,userId_real = get_refresh_token(account_b64, account_URI, password_RSA, password_URI,nickname)
    payload = construct_token_payload(refreshToken)
    accessToken = get_access_token(payload)
    getUserData(accessToken,payload,userId_real,nickname)



if __name__ == "__main__":
    
    def parse_string(input_string):
        arr = []
        groups = input_string.split(',')
        for group in groups:
            account, password,nickname = group.split('/')
            account = account.strip()
            password = password.strip()
            nickname = nickname.strip()
            arr.append({'account': account, 'password': password, 'nickname': nickname})
        return arr
    users = parse_string(input_string)
    #print(users)
    for user in users:
        getUserInfo(user["account"], user["password"], user["nickname"])