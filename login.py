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
parser.add_argument("account", help="输入手机号码")
parser.add_argument("password", help="输入密码")
parser.add_argument("nickname", help="输入该体重的用户名")        
options = parser.parse_args()


account = options.account
password = options.password
nickname = options.nickname

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


global account_b64, account_URI, password_RSA, password_URI 
account_b64, account_URI, password_RSA, password_URI = encrypt_account_password(account, password)



#print(f"account_b64: {account_b64}\n")
#print(f"account_URI: {account_URI}\n")
#print(f"password_RSA: {password_RSA}\n")
#print(f"password_URI: {password_URI}\n")

#首次登陆，使用虚拟deviceUUID、userId
deviceUUID = "abcd"
userId = "199999999"

#构建loginSign
def construct_loginsign(account_b64, password_RSA):
    timestamp = str(int(time.time()))
    code = timestamp[:8] + "00"
    
    userName = account_b64
    password = password_RSA


    loginsign = "code=" + code + "&deviceUUID=" + deviceUUID + "&loginType=1&password=" + password + "\n&signVersion=3&userId=" + userId + "&userName=" + userName + "\n&versionCode=7&secret=AUMtyBDV3vklBr6wtA2putAMwtmVcD5b"


    return loginsign
loginsign = construct_loginsign(account_b64, password_RSA)
#print(f"loginsign: {loginsign}\n")

#对loginsign进行md5加密
def md5(loginsign):
    md5 = hashlib.md5()
    md5.update(loginsign.encode('utf-8'))
    encrypted_string = md5.hexdigest()
    return encrypted_string

#构建login请求头data:payload
def construct_payload(password_URI, account_URI, deviceUUID, userId, loginsign):
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
payload = construct_payload(password_URI, account_URI, deviceUUID, userId, loginsign)
#print(f"payload: {payload}\n")




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

#构建请求参数
def send_post_request(url, headers,payload):
    
    response = requests.post(url, headers=headers, data=payload)
    json_data = response.json()
    return json_data


login_result = send_post_request(url, headers,payload)


#取返回结果数值
login_stat= login_result['result']['msg']
if login_result['result']['code'] == 0:     
    print(f"{nickname}登陆状态: {login_stat}\n")
    userId_real= login_result['data']['userinfo']['userId']
#print(f"userId_real: {userId_real}\n")
    realName= login_result['data']['userinfo']['realName']
#print(f"realName: {realName}\n")
    refreshToken = login_result['data']['userinfo']['refreshToken']
#print(f"refreshToken: {refreshToken}\n")
else:
    print(f"登陆状态: {login_stat}\n")
    sys.exit()  #登陆失败后停止执行后续命令


#保存userId、refreshToken、realName
arr = {
    "userId_real": userId_real,
    "refreshToken": refreshToken,
    "nickname": nickname,  
    "userId_real":userId_real,
    "refreshToken":refreshToken,
    "account_b64" :account_b64,
    "password_RSA":password_RSA,
}


#保存refreshToken
with open(f'userinfo_{nickname}.json', 'w',encoding="utf-8") as file:
    file.write(json.dumps(arr, ensure_ascii=False))
    print(f"userinfo_{nickname}.json写入成功！")