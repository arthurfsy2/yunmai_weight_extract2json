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
import zipfile
import os
import re
import shutil,operator
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

# 获取当前文件的绝对路径
file_path = os.path.abspath(__file__)
# 获取当前文件所在的目录
dir_path = os.path.dirname(file_path)


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


def getUserData(accessToken, payload, userId_real, account, nickname, height, isOnline):
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
    if isOnline == 1:
        weight_nicname_path = f'./static/result/{account}_weight.json'
    else:
        weight_nicname_path = f'./weight_{nickname}.json'
    with open(weight_nicname_path, 'w', encoding="utf-8") as f:
        f.write(json_data)
        print(f"{weight_nicname_path}写入成功！")
        print("————————————————————")
    weight = json.dumps([item['weight'] for item in weight_data])
    createTime = json.dumps([item['createTime']
                            for item in weight_data])  # 将列表转换为 JSON 格式的字符串

    def get_avg(arr):
        avg = sum(arr) / len(arr)
        return round(avg, 2)
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
    dataNew = generate_report(dataNew, weight_data, nickname)
    if isOnline == 1:
        html_name = f'./static/result/{account}_weight.html'
    else:
        html_name = f'./weight_report_{nickname}.html'
    with open(html_name, 'w', encoding="utf-8") as f:
        f.write(dataNew)
    print(f'已生成{html_name}')
    return weight_data

def getUserInfo(account, password, nickname, height, garmin_account, garmin_password, isOnline,local_list):
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
    weight_data = getUserData(accessToken, payload, userId_real,
                account, nickname, height, isOnline)
    online_list = [item["timeStamp"] for item in weight_data]
    filtered_data = [item for item in weight_data if item["timeStamp"] not in local_list]
    if garmin_account and garmin_password:
        if filtered_data:
            upload_to_garmin(garmin_account, garmin_password, filtered_data)
        else:
            print("garmin已是最新体重记录")

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
                "label": "偏瘦(<{lte_value})",
                "color": "grey"
            }},
            {{
                "gt": {lte_value},
                "lte": {gt_value},
                "label": "正常({lte_value}~{gt_value})",
                "color": "green"
            }},
            {{
                "gt": {gt_value},
                "lte": {lte_value2},
                "label": "偏胖({gt_value}~{lte_value2})",
                "color": "orange"
            }},
            {{
                "gt": {lte_value2},
                "label": "肥胖(>{lte_value2})",
                "color": "red"
            }}
        
        """
    return content


def parse_string(input_string):
    arr = []
    groups = input_string.split(',')
    for group in groups:
        account, password, nickname, height, *garmin_info = group.split('/')
        account = account.strip()
        password = password.strip()
        nickname = nickname.strip()
        height = height.strip()
        
        if len(garmin_info) == 2:
            garmin_account = garmin_info[0].strip()
            garmin_password = garmin_info[1].strip()
        else:
            garmin_account = ""
            garmin_password = ""
        
        arr.append({
            'account': account,
            'password': password,
            'nickname': nickname,
            'height': height,
            'garmin_account': garmin_account,
            'garmin_password': garmin_password
        })
    return arr


def zipUserFile(account, path):
    # 创建一个正则表达式模式来匹配以账户名开头并以.html结尾的文件
    pattern = re.compile(f"^{re.escape(account)}_(?!.*\\.zip$).*")
    # 创建一个ZIP文件的名称
    zip_filename = f"{path}/{account}_weight.zip"

    with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
        # 使用os.walk遍历目录树
        for root, dirs, files in os.walk(path):
            for filename in files:
                # 检查文件名是否符合模式
                if pattern.match(filename) or root.endswith('src'):
                    filepath = os.path.join(root, filename)
                    # 计算在ZIP文件中的路径
                    zip_path = os.path.relpath(filepath, start=path)
                    # 将文件添加到ZIP文件中
                    zipf.write(filepath, arcname=zip_path)



def get_physique_type(bmi, body_fat):
    if bmi < 18.5 and body_fat < 10:
        return "7"
    elif bmi < 18.5 and 10 < body_fat < 21:
        return "4"
    elif bmi < 18.5 and 21 < body_fat < 26:
        return "1"
    elif 18.5 < bmi < 21 and body_fat < 15:
        return "6"
    elif 21 < bmi < 24 and body_fat < 15:
        return "8"
    elif 18.5 < bmi < 24 and 15 < body_fat < 21:
        return "5"
    elif 24 < bmi < 28 and body_fat < 15:
        return "9"
    elif (24 < bmi < 28 and 15 < body_fat < 26) or (21 < bmi < 28 and 21 < body_fat < 26):
        return "2"
    elif (28 < bmi and 15 < body_fat) or (21 < bmi and body_fat < 26):
        return "3"
    else:
        return "未知类型"


def upload_to_garmin(email, password, data):
    from garminconnect import (
    Garmin,
    GarminConnectConnectionError,
    GarminConnectTooManyRequestsError,
    GarminConnectAuthenticationError,
    )
    from datetime import datetime, timezone, timedelta
    for item in data:
        createTime = item.get("createTime")
        timestamp = item.get("timeStamp")
        weight = item.get("weight")
        percent_fat = item.get("fat")
        percent_hydration = item.get("water")
        visceral_fat_mass = round(item.get("fat") * weight / 100, 2)
        bone_mass = item.get("bone")
        muscle_mass = round(item.get("muscle") * weight / 100, 2)
        basal_met = item.get("bmr")
        metabolic_age = item.get("somaAge")
        visceral_fat_rating = item.get("visFat")
        bmi = item.get("bmi")
        physique_rating = float(get_physique_type(bmi, percent_fat))

        dt = datetime.fromtimestamp(timestamp, tz=timezone.utc)
        # 将时区调整为中国时区
        china_tz = timezone(timedelta(hours=8))
        dt_china = dt.astimezone(china_tz)
        iso_timestamp = dt_china.isoformat()
        try:
            garmin_client = Garmin(email, password, is_cn=True)
            garmin_client.login()
            print("佳明（cn）登陆成功！")  # 添加登录成功的提示
        except (
            GarminConnectConnectionError,
            GarminConnectAuthenticationError,
            GarminConnectTooManyRequestsError,
        ) as err:
            print("佳明（cn）登陆失败: %s" % err)
            quit()
        garmin_client.add_body_composition(
                timestamp=iso_timestamp,
                weight=weight,
                percent_fat=percent_fat,
                percent_hydration=percent_hydration,
                visceral_fat_mass=visceral_fat_mass,
                bone_mass=bone_mass,
                muscle_mass=muscle_mass,
                basal_met=basal_met,
                # active_met=active_met,
                physique_rating=physique_rating,
                metabolic_age=metabolic_age,
                visceral_fat_rating=visceral_fat_rating,
                bmi=bmi
            )       
        print(f"{createTime} 的体重：{weight}kg，已经上传成功！")

def parse_sync_time(sync_time_str):
    return datetime.strptime(sync_time_str, '%Y-%m-%d %H:%M:%S')

def find_closest_entry(data, target_datetime):
    closest_entry = min(data, key=lambda x: abs(parse_sync_time(x['syncTime']) - target_datetime))
    closest_entry_time = parse_sync_time(closest_entry['syncTime'])
    time_difference = abs(closest_entry_time - target_datetime)
    
    if time_difference > timedelta(days=6*30):  # 近似计算6个月
        return None
    
    return closest_entry

def generate_intervals_by_years(num):
    intervals_by_years = {}
    for i in range(1, num + 1):
        intervals_by_years[f"{i}年前"] = relativedelta(years=i)
    return intervals_by_years

def calculate_years_difference(latest_date, oldest_date):
    latest_datetime = datetime.fromtimestamp(latest_date['timeStamp'])
    oldest_datetime = datetime.fromtimestamp(oldest_date['timeStamp'])
    years_difference = latest_datetime.year - oldest_datetime.year
    return years_difference

def generate_report(template, data, nickname):
    latest_date = max(data, key=lambda x: x['timeStamp'])
    oldest_date = min(data, key=lambda x: x['timeStamp'])
    max_weight_data = max(data, key=lambda x: x['weight'])
    min_weight_data = min(data, key=lambda x: x['weight'])
    intervals_by_months = {
        "1个月前": relativedelta(months=1),
        "3个月前": relativedelta(months=3),
        "6个月前": relativedelta(months=6),
        "9个月前": relativedelta(months=9)
    }
    
    years_diff = calculate_years_difference(latest_date, oldest_date)
    intervals_by_years = generate_intervals_by_years(years_diff)
   
    
    report_lines_by_months = []

    for label, interval in intervals_by_months.items():
        time_latest = parse_sync_time(latest_date['syncTime'])
        target_date = time_latest - interval
        closest_entry = find_closest_entry(data, target_date)
        if closest_entry:
            weight_diff = latest_date['weight'] - closest_entry['weight']
            lose_percent = weight_diff / closest_entry['weight'] * 100
            report_lines_by_months.append(
                f"<tr><td>{label}</td><td>{closest_entry['syncTime']}</td><td>{closest_entry['weight']} kg</td><td>{weight_diff:.2f} kg</td><td>{lose_percent:.2f} %</td></tr>"
            )

    
    report_lines_by_years = []

    for label, interval in intervals_by_years.items():
        time_latest = parse_sync_time(latest_date['syncTime'])
        target_date = time_latest - interval
        closest_entry = find_closest_entry(data, target_date)
        if closest_entry:
            weight_diff = latest_date['weight'] - closest_entry['weight']
            lose_percent = weight_diff / closest_entry['weight'] * 100
            report_lines_by_years.append(
                f"<tr><td>{label}</td><td>{closest_entry['syncTime']}</td><td>{closest_entry['weight']} kg</td><td>{weight_diff:.2f} kg</td><td>{lose_percent:.2f} %</td></tr>"
            )

    template = template.replace("{{nickname}}",nickname)
    template = template.replace("{{最近称重}}",f"{latest_date['weight']} kg | {latest_date['syncTime']}")

    template = template.replace("{{历史最重}}",f"{max_weight_data['weight']} kg | {max_weight_data['syncTime']}")

    template = template.replace("{{历史最轻}}",f"{min_weight_data['weight']} kg | {min_weight_data['syncTime']}")

    template = template.replace("{{report_lines_by_months}}","\n".join(report_lines_by_months))
    template = template.replace("{{report_lines_by_years}}","\n".join(report_lines_by_years))
    
    return template

def read_json_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        data = json.load(file)
    return data

def read_html_template(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        template = file.read()
    return template

def save_html_report(nickname, template, report_content, output_file_path):
    html_content = template.replace("{{ report_content }}", report_content).replace("{{ nickname }}", nickname)
    with open(output_file_path, 'w', encoding='utf-8') as file:
        file.write(html_content)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("input_string", help="输入:'用户名/密码/昵称/身高（米）/佳明账号/佳明密码'")
    parser.add_argument(
        "--isOnline", help="check if created by online", type=int, default=0)
    options = parser.parse_args()
    input_string = options.input_string
    isOnline = options.isOnline

    users = parse_string(input_string)
    # print(users)
    for user in users:
        old_file = f'./weight_{user["nickname"]}.json'
        if os.path.exists(old_file):
            shutil.copyfile(old_file, f'{old_file}BAK')
        with open(f'{old_file}BAK', 'r', encoding="utf-8") as f:
            data_old = json.load(f)
            local_list = [item["timeStamp"] for item in data_old]
        getUserInfo(user["account"], user["password"],
                    user["nickname"], float(user["height"]), 
                    user["garmin_account"], user["garmin_password"],
                    isOnline,local_list)
        if isOnline == 1:
            zipUserFile(user["account"], "./static/result")
        os.remove(f'{old_file}BAK')
