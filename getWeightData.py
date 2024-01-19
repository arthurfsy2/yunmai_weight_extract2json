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
import os


# 获取当前文件的绝对路径
file_path = os.path.abspath(__file__)
# 获取当前文件所在的目录
dir_path = os.path.dirname(file_path)

# 对原始密码进行加密


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

# 构建loginSign


def construct_loginsign(account_b64, password_RSA, deviceUUID, userId):
    timestamp = str(int(time.time()))
    code = timestamp[:8] + "00"

    userName = account_b64
    password = password_RSA

    loginsign = "code=" + code + "&deviceUUID=" + deviceUUID + "&loginType=1&password=" + password + \
        "\n&signVersion=3&userId=" + userId + "&userName=" + userName + \
        "\n&versionCode=7&secret=AUMtyBDV3vklBr6wtA2putAMwtmVcD5b"

    return loginsign


# 对loginsign进行md5加密
def md5(loginsign):
    md5 = hashlib.md5()
    md5.update(loginsign.encode('utf-8'))
    encrypted_string = md5.hexdigest()
    return encrypted_string

# 构建login请求头data:payload


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

# 构建tokenSign


def construct_token_payload(refreshToken):
    timestamp = str(int(time.time()))
    code = timestamp[:8] + "00"
    tokensign = "code=" + code + "&refreshToken=" + refreshToken + \
        "&signVersion=3&versionCode=2&secret=AUMtyBDV3vklBr6wtA2putAMwtmVcD5b"
    timestamp = str(int(time.time()))
    code = timestamp[:8] + "00"
    payload = (

        "code=" + code + "&refreshToken=" + refreshToken +
        "&sign="+md5(tokensign)+"&signVersion=3&versionCode=2"
    )
    return payload

# 构建token.d请求参数


def get_accesstoken_request(url, headers, payload):

    response = requests.post(url, headers=headers, data=payload)
    json_data = response.json()
    return json_data


# 构建chart-list.json获取重量数据请求参数
def get_Weight_request(url, headers, payload):

    response = requests.get(url, headers=headers, data=payload)
    json_data = response.json()
    json_data = json_data
    return json_data


def get_refresh_token(account_b64, account_URI, password_RSA, password_URI, nickname):
    url = "https://account.iyunmai.com/api/android//user/login.d"
    headers = {
        'Host': 'account.iyunmai.com',
        'Content-Type': 'application/x-www-form-urlencoded',
        'Accept-Encoding': 'gzip',
        'Connection': 'keep-alive',
        'Accept': '*/*',
        'User-Agent': 'google/android(10,29) channel(huawei) app(4.25,42500010)screen(w,h=1080,1794)/scale',
        'IssignV1': 'open',
        'Accept-Language': 'zh-Hans-CN;q=1, en-CN;q=0.9',
    }
    # 首次登陆，使用虚拟deviceUUID、userId
    deviceUUID = "abcd"
    userId = "199999999"

    # 1. 构建loginSign
    timestamp = str(int(time.time()))
    code = timestamp[:8] + "00"
    userName = account_b64
    password = password_RSA
    loginsign = "code=" + code + "&deviceUUID=" + deviceUUID + "&loginType=1&password=" + password + \
        "\n&signVersion=3&userId=" + userId + "&userName=" + userName + \
        "\n&versionCode=7&secret=AUMtyBDV3vklBr6wtA2putAMwtmVcD5b"

    # 2. 构建login请求头data:payload
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

    # 3. 解析登陆结果，获取refreshToken、userId_real
    response = requests.post(url, headers=headers, data=payload)
    login_result = response.json()
    login_stat = login_result['result']['msg']
    print("————————————————————")
    if login_result['result']['code'] == 0:
        print(f"{nickname}登陆状态: {login_stat}")
        userId_real = login_result['data']['userinfo']['userId']
        realName = login_result['data']['userinfo']['realName']
        refreshToken = login_result['data']['userinfo']['refreshToken']
    else:
        print(f"登陆状态: {login_stat}")
        print(f"获取数据失败，已退出")
        sys.exit()
    return refreshToken, userId_real


def get_access_token(payload):
    token_url = "https://account.iyunmai.com/api/android///auth/token.d"
    token_headers = {
        'Host': 'account.iyunmai.com',
        'Content-Type': 'application/x-www-form-urlencoded',
        'Accept-Encoding': 'gzip',
        'Connection': 'keep-alive',
        'Accept': '*/*',
        'User-Agent': 'google/android(10,29) channel(huawei) app(4.25,42500010)screen(w,h=1080,1794)/scale',
        'IssignV1': 'open',
        'Accept-Language': 'zh-Hans-CN;q=1, en-CN;q=0.9',
    }
    # 获取Access_token数据并保存结果
    getAccesstoken_result = get_accesstoken_request(
        token_url, token_headers, payload)
    # print(getAccesstoken_result)
    getAccesstoken_stat = getAccesstoken_result['result']['msg']

    # 获取accessToken
    if getAccesstoken_result['result']['code'] == 0:
        print(f"Access_token获取结果: {getAccesstoken_stat}")
        accessToken = getAccesstoken_result['data']['accessToken']
    else:
        print(f"Access_token获取结果: {getAccesstoken_stat}")
        accessToken = None

    # print("accessToken",accessToken)
    return accessToken


def getUserData(accessToken, payload, userId_real, acount, nickname, height, isOnline):
    code = str(int(time.time()))
    startTime = str(int(time.time()) - 9999 * 24 *
                    60 * 60)  # 取当前时间前9999天为需要截取的时间段
    data_url = f"https://data.iyunmai.com/api/ios/scale/chart-list.json?code={code}&signVersion=3&startTime={startTime}&userId={userId_real}&versionCode=2"
    # 1. 构建chart-list.json请求头
    data_headers = {
        'Host': 'account.iyunmai.com',
        'Content-Type': 'application/x-www-form-urlencoded',
        'Accept-Encoding': 'gzip',
        'Connection': 'keep-alive',
        'Accept': '*/*',
        'User-Agent': 'google/android(10,29) channel(huawei) app(4.25,42500010)screen(w,h=1080,1794)/scale',
        'accessToken': accessToken,
        'IssignV1': 'open',
        'Accept-Language': 'zh-Hans-CN;q=1, en-CN;q=0.9',
    }
    # 2. 获取体重数据
    response = requests.get(data_url, headers=data_headers, data=payload)
    getWeight_stat = response.json()
    # 3. 解析体重数据并保存
    weight_data = getWeight_stat['data']['rows']
    json_data = json.dumps(weight_data, indent=2)
    # print(f"weight_data: {weight_data}\n\n")
    weight_nicname_path = os.path.join(dir_path, f'weight_{nickname}.json')
    with open(weight_nicname_path, 'w', encoding="utf-8") as f:
        # json_data = black.format_str(json_data, mode=black.FileMode())
        f.write(json_data)
        print(f"weight_{nickname}.json写入成功！")
        print("————————————————————")
    weight = json.dumps([item['weight'] for item in weight_data])
    createTime = json.dumps([item['createTime']
                            for item in weight_data])  # 将列表转换为 JSON 格式的字符串

    def get_avg(arr):
        avg = sum(arr) / len(arr)
        return round(avg, 2)

    # 调用函数并传入数组 a
    # 假设你已经计算了平均值并四舍五入到两位小数
    average = str(round(get_avg([item['weight'] for item in weight_data]), 2))
    pieces = get_BMI_status(height)
    template_path = os.path.join(dir_path, 'template.html')
    with open(template_path, 'r', encoding="utf-8") as f:
        data = f.read()
        dataNew = data.replace("$weight$", weight).replace(
            "$createTime$", createTime).replace(
            "$nickname$", nickname).replace(
            "$average$", average).replace(
            "$pieces$", pieces)

    if isOnline == 1:
        account_weight_path = os.path.join(
            dir_path, f'./static/{acount}_weight.html')
        with open(account_weight_path, 'w', encoding="utf-8") as f:
            f.write(dataNew)
        print(f'已生成./static/{acount}_weight.html')
        print(weight_nicname_path)
        os.remove(weight_nicname_path)


def getUserInfo(account, password, nickname, height, isOnline):
    # 1. 加密账号密码
    account_b64, account_URI, password_RSA, password_URI = encrypt_account_password(
        account, password)
    # 2. 获取refreshToken
    refreshToken, userId_real = get_refresh_token(
        account_b64, account_URI, password_RSA, password_URI, nickname)
    payload = construct_token_payload(refreshToken)
    # 3. accessToken
    accessToken = get_access_token(payload)
    # 4. 获取体重数据
    getUserData(accessToken, payload, userId_real,
                account, nickname, height, isOnline)


def get_BMI_status(h):
    s1 = 18.5
    s2 = 24.0
    s3 = 28.0

    def calscore(s, h):
        return h*h*s
    lte_value = round(calscore(s1, h), 2)
    gt_value = round(calscore(s2, h), 2)
    lte_value2 = round(calscore(s3, h), 2)

    content = f"""
        
            {{
                "lte": {lte_value},
                "label": "偏瘦",
                "color": "grey"
            }},
            {{
                "gt": {lte_value},
                "lte": {gt_value},
                "label": "正常",
                "color": "green"
            }},
            {{
                "gt": {gt_value},
                "lte": {lte_value2},
                "label": "偏胖",
                "color": "orange"
            }},
            {{
                "gt": {lte_value2},
                "label": "肥胖",
                "color": "red"
            }}
        
        """
    return content


def parse_string(input_string, isOnline):
    arr = []
    groups = input_string.split(',')
    for group in groups:
        account, password, nickname, height = group.split('/')
        account = account.strip()
        password = password.strip()
        nickname = nickname.strip()
        height = height.strip()
        arr.append(
            {'account': account, 'password': password, 'nickname': nickname, 'height': height})
    return arr


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("input_string", help="输入:'用户名/密码/昵称'")
    parser.add_argument(
        "--isOnline", help="check if created by online", type=int, default=0)
    options = parser.parse_args()
    input_string = options.input_string
    isOnline = options.isOnline

    users = parse_string(input_string, isOnline)
    # print(users)
    for user in users:
        getUserInfo(user["account"], user["password"],
                    user["nickname"], float(user["height"]), isOnline)
