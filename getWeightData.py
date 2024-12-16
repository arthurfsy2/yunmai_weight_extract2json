import time
import requests
import json
import argparse
import sys
import zipfile
import os
import re
import shutil, operator
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from jinja2 import Template
from fetcher import WeightDataFetcher
from getUserReport import get_user_report

BIN = os.path.dirname(os.path.realpath(__file__))


def getUserInfo(
    account,
    password,
    nickname,
    height,
    garmin_account,
    garmin_password,
    isOnline,
    local_list,
):

    fetcher = WeightDataFetcher(account, password, nickname)
    weight_data = fetcher.get_weight_data()
    # sys.exit()

    online_list = [item["timeStamp"] for item in weight_data]
    fetcher.get_weekly_data(isOnline)
    filtered_data = []
    if local_list:
        filtered_data = [
            item for item in weight_data if item["timeStamp"] not in local_list
        ]
    # print("filtered_data:", filtered_data)
    if garmin_account and garmin_password:
        if filtered_data:
            fetcher.upload_to_garmin(garmin_account, garmin_password, filtered_data)
        else:
            print("garmin已是最新体重记录")
    get_user_report(weight_data, account, nickname, height, isOnline)


def parse_string(input_string):
    arr = []
    groups = input_string.split(",")
    for group in groups:
        try:
            account, password, nickname, height, *garmin_info = group.split("/")
        except Exception:
            print(
                "请检查以下内容是否有误：'用户名/密码/昵称/身高（米）/佳明账号（可选）/佳明密码（可选）'"
            )
            sys.exit()
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

        arr.append(
            {
                "account": account,
                "password": password,
                "nickname": nickname,
                "height": height,
                "garmin_account": garmin_account,
                "garmin_password": garmin_password,
            }
        )
    return arr


def zipUserFile(account, path):
    # 创建一个正则表达式模式来匹配以账户名开头并以.html结尾的文件
    pattern = re.compile(f"^{re.escape(account)}_(?!.*\\.zip$).*")
    # 创建一个ZIP文件的名称
    zip_filename = f"{path}/{account}_weight.zip"

    with zipfile.ZipFile(zip_filename, "w", zipfile.ZIP_DEFLATED) as zipf:
        # 使用os.walk遍历目录树
        for root, dirs, files in os.walk(path):
            for filename in files:
                # 检查文件名是否符合模式
                if pattern.match(filename) or root.endswith("src"):
                    filepath = os.path.join(root, filename)
                    # 计算在ZIP文件中的路径
                    zip_path = os.path.relpath(filepath, start=path)
                    # 将文件添加到ZIP文件中
                    zipf.write(filepath, arcname=zip_path)


def calculate_years_difference(latest_date, oldest_date):
    latest_datetime = datetime.fromtimestamp(latest_date["timeStamp"])
    oldest_datetime = datetime.fromtimestamp(oldest_date["timeStamp"])
    years_difference = latest_datetime.year - oldest_datetime.year
    return years_difference


def read_json_file(file_path):
    with open(file_path, "r", encoding="utf-8") as file:
        data = json.load(file)
    return data


def read_html_template(file_path):
    with open(file_path, "r", encoding="utf-8") as file:
        template = file.read()
    return template


def save_html_report(nickname, template, report_content, output_file_path):
    html_content = template.replace("{{ report_content }}", report_content).replace(
        "{{ nickname }}", nickname
    )
    with open(output_file_path, "w", encoding="utf-8") as file:
        file.write(html_content)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "input_string",
        help="输入:'用户名/密码/昵称/身高（米）/佳明账号（可选）/佳明密码（可选）'",
    )
    parser.add_argument(
        "--isOnline", help="check if created by online", type=int, default=0
    )
    options = parser.parse_args()
    input_string = options.input_string
    isOnline = options.isOnline

    users = parse_string(input_string)
    # print(users)
    for user in users:
        old_file = os.path.join(BIN, "output", f'weight_{user["nickname"]}.json')
        if os.path.exists(old_file):
            shutil.copyfile(old_file, f"{old_file}BAK")
            with open(f"{old_file}BAK", "r", encoding="utf-8") as f:
                data_old = json.load(f)
                local_list = [item["timeStamp"] for item in data_old]
        else:
            local_list = []
        getUserInfo(
            user["account"],
            user["password"],
            user["nickname"],
            float(user["height"]),
            user["garmin_account"],
            user["garmin_password"],
            isOnline,
            local_list,
        )
        if isOnline == 1:
            zipUserFile(user["account"], "./static/result")
        if os.path.exists(f"{old_file}BAK"):
            os.remove(f"{old_file}BAK")
