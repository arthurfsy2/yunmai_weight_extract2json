import os
from datetime import datetime
import base64
import urllib.parse
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_v1_5
import time
import hashlib
import requests
import sys
import os
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import json
from garth.exc import GarthHTTPError
from garminconnect import (
    Garmin,
    GarminConnectConnectionError,
    GarminConnectTooManyRequestsError,
    GarminConnectAuthenticationError,
)
import logging
from jinja2 import Template

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
import re

tokenstore = "~/.garminconnect"
tokenstore_base64 = "~/.garminconnect_base64"
BIN = os.path.dirname(os.path.realpath(__file__))


class SaveRefreshToken:
    def __init__(self, refresh_token, nickname, sign):
        self.nickname = nickname
        self.sign = sign
        self.refresh_token = refresh_token
        self.local_refresh_token_path = os.path.expanduser(
            f"~/.yunmai/{self.nickname}_yunmai_token"
        )

        # 确保目录存在
        os.makedirs(os.path.dirname(self.local_refresh_token_path), exist_ok=True)

    def encrypt_data(self, data):
        """将输入的data进行Base64编码并返回字符串"""
        # 将 data 转换为字节
        data_bytes = data.encode("utf-8")
        # 使用 base64 编码
        encoded_bytes = base64.b64encode(data_bytes)
        # 返回编码后的字符串
        return encoded_bytes.decode("utf-8")

    def save_token(self):
        """保存加密后的 refresh_token 到本地文件"""
        encrypted_token = self.encrypt_data(self.refresh_token)
        try:
            with open(
                self.local_refresh_token_path,
                "w",
                encoding="utf-8",
            ) as f:
                f.write(encrypted_token)  # 写入加密后的字符串
        except Exception as e:
            print(f"保存 token 失败: {str(e)}")

    def load_token(self):
        """从文件读取并解密 refresh_token"""
        try:
            with open(
                self.local_refresh_token_path,
                "r",
                encoding="utf-8",
            ) as f:
                encrypted_token = f.read()  # 这里直接读取字符串
                # return self.decrypt_data(encrypted_token)  # 返回解密后的文本
        except Exception as e:
            print(f"加载本地refresh token 失败: {str(e)}")
            return None
        token_data = json.loads(self.decrypt_data(encrypted_token))
        gaps = (int(time.time()) - token_data.get("timestamp", 0)) / 7 / 24 / 3600
        # print("gaps:", gaps)
        # 验证token是否过期（7天）
        if gaps > 7 * 24 * 3600:
            print("本地yunmai token已过期！")
            return None
        else:
            return token_data

    def decrypt_data(self, encrypted_data):
        """将encrypted_data进行Base64逆编码并还原"""
        try:
            # 使用 base64 解码
            decoded_bytes = base64.b64decode(encrypted_data)
            # 返回解码后的字符串
            return decoded_bytes.decode("utf-8")
        except (base64.binascii.Error, UnicodeDecodeError) as e:
            # 处理 Base64 解码错误或字符串解码错误
            raise ValueError("提供的数据无法解码为有效的字符串") from e


class WeightDataFetcher:
    def __init__(self, account, password, nickname):
        self.account = account
        self.password = password
        self.nickname = nickname
        self.refresh_token = None
        self.user_id_real = None
        self.access_token = None
        self.yunmai_token = None
        self.weight_data = []
        self.local_refresh_token_path = os.path.join(
            BIN, f"{self.nickname}_yunmai_token"
        )

    @staticmethod
    def encrypt_account_password(account, password):
        account_b64 = base64.b64encode(account.encode()).decode()
        account_URI = urllib.parse.quote(account_b64)

        rsakey = RSA.importKey(
            "-----BEGIN PUBLIC KEY-----\n"
            "MFwwDQYJKoZIhvcNAQEBBQADSwAwSAJBAJKcIu+iATe0QPGIVDzMYsMA6kH9FcY9\n"
            "Or0I4WJJfEgw/N2e0Us/9JVV1CwdV6W2XIl4KqTeH3ydw6tagagPkSsCAwEAAQ==\n"
            "-----END PUBLIC KEY-----\n"
        )
        cipher = PKCS1_v1_5.new(rsakey)
        cipher_text = base64.b64encode(cipher.encrypt(password.encode("utf-8")))
        password_RSA = cipher_text.decode("utf-8").replace("\n", "")  # Remove newlines
        password_URI = urllib.parse.quote(password_RSA)

        return account_b64, account_URI, password_RSA, password_URI

    @staticmethod
    def md5(loginsign):
        return hashlib.md5(loginsign.encode("utf-8")).hexdigest()

    def check_cached_token(self):
        """检查是否存在有效的token缓存"""

        if os.path.exists(self.local_refresh_token_path):

            print("正在使用本地 refresh token 获取数据...")
            local_refresh_token = SaveRefreshToken(
                self.refresh_token, self.nickname, f"{self.account}"
            )
            local_data = local_refresh_token.load_token()
            # print("local_data:", local_data)
            if local_data:
                self.refresh_token = local_data.get("refresh_token")
                self.user_id_real = local_data.get("user_id")
                self.yunmai_token = True
                return True
            else:
                print("yunmai: 尝试使用账号密码登录...")
            return None
        else:
            print("yunmai: 尝试使用账号密码登录...")
            return None

    def login(self):
        account_b64, account_URI, password_RSA, password_URI = (
            self.encrypt_account_password(self.account, self.password)
        )

        url = "https://account.iyunmai.com/api/android//user/login.d"
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "google/android(10,29) channel(huawei) app(4.25,42500010)screen(w,h=1080,1794)/scale",
        }
        deviceUUID = "abcd"
        userId = "199999999"

        # loginSign construction
        timestamp = str(int(time.time()))
        code = timestamp[:8] + "00"
        loginsign = (
            f"code={code}&deviceUUID={deviceUUID}&loginType=1&password={password_RSA}\n"
            f"&signVersion=3&userId={userId}&userName={account_b64}\n&versionCode=7&secret=AUMtyBDV3vklBr6wtA2putAMwtmVcD5b"
        )

        payload = (
            f"password={password_URI}%0A&code={code}&loginType=1&userName={account_URI}%0A"
            f"&deviceUUID={deviceUUID}&versionCode=7&userId={userId}&signVersion=3&sign={self.md5(loginsign)}"
        )

        response = requests.post(url, headers=headers, data=payload)
        login_result = response.json()

        if login_result["result"]["code"] == 0:
            self.refresh_token = login_result["data"]["userinfo"]["refreshToken"]

            self.user_id_real = login_result["data"]["userinfo"]["userId"]

        else:
            print(f"登陆状态: {login_result['result']['msg']}")
            sys.exit()

    @staticmethod
    def construct_token_payload(refreshToken):
        timestamp = str(int(time.time()))
        code = timestamp[:8] + "00"
        tokensign = f"code={code}&refreshToken={refreshToken}&signVersion=3&versionCode=2&secret=AUMtyBDV3vklBr6wtA2putAMwtmVcD5b"
        payload = f"code={code}&refreshToken={refreshToken}&sign={WeightDataFetcher.md5(tokensign)}&signVersion=3&versionCode=2"
        return payload

    def get_access_token(self):
        token_url = "https://account.iyunmai.com/api/android///auth/token.d"
        token_headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "google/android(10,29) channel(huawei) app(4.25,42500010)screen(w,h=1080,1794)/scale",
        }
        payload = self.construct_token_payload(self.refresh_token)
        response = requests.post(token_url, headers=token_headers, data=payload)
        token_result = response.json()

        if token_result["result"]["code"] == 0:
            self.access_token = token_result["data"]["accessToken"]
        else:
            print(f"Access_token获取结果: {token_result['result']['msg']}")
            self.access_token = None

    def get_weight_data(self, start_date=None):
        if not self.check_cached_token():
            self.login()
        self.get_access_token()

        code = str(int(time.time()))
        startTime = str(int(time.time()) - 9999 * 24 * 60 * 60)
        if start_date:
            startTime = str(int(datetime.strptime(start_date, "%Y-%m-%d").timestamp()))

        data_url = f"https://data.iyunmai.com/api/ios/scale/chart-list.json?code={code}&signVersion=3&startTime={startTime}&userId={self.user_id_real}&versionCode=2"
        # print("data_url:", data_url)
        data_headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "google/android(10,29) channel(huawei) app(4.25,42500010)screen(w,h=1080,1794)/scale",
            "accessToken": self.access_token,
        }
        response = requests.get(data_url, headers=data_headers)
        weight_data = response.json()["data"]["rows"]
        self.weight_data = weight_data
        # 保存token到本地文件
        token_data = {
            "refresh_token": self.refresh_token,
            "user_id": self.user_id_real,
            "timestamp": int(time.time()),
        }
        # print("token_data:", token_data)
        if not self.yunmai_token:
            local_refresh_token = SaveRefreshToken(
                json.dumps(token_data), self.nickname, f"{self.account}"
            )
            local_refresh_token.save_token()
        return weight_data

    def garmin_login(self, email, password):
        try:
            print(f"尝试使用本地garmin token数据 '{tokenstore}'...\n")
            garmin = Garmin()
            garmin.login(tokenstore)
            print("佳明（cn）登陆成功！")
        except (FileNotFoundError, GarthHTTPError, GarminConnectAuthenticationError):
            # Session is expired. You'll need to log in again
            print(
                "Login tokens not present, login with your Garmin Connect credentials to generate them.\n"
                f"They will be stored in '{tokenstore}' for future use.\n"
            )
            try:
                # Ask for credentials if not set as environment variables

                garmin = Garmin(email=email, password=password, is_cn=True)
                garmin.login()
                # Save Oauth1 and Oauth2 token files to directory for next login
                garmin.garth.dump(tokenstore)
                print(
                    f"Oauth tokens stored in '{tokenstore}' directory for future use. (first method)\n"
                )
                # Encode Oauth1 and Oauth2 tokens to base64 string and safe to file for next login (alternative way)
                token_base64 = garmin.garth.dumps()
                dir_path = os.path.expanduser(tokenstore_base64)
                with open(dir_path, "w") as token_file:
                    token_file.write(token_base64)
                print(
                    f"Oauth tokens encoded as base64 string and saved to '{dir_path}' file for future use. (second method)\n"
                )
            except (
                FileNotFoundError,
                GarthHTTPError,
                GarminConnectAuthenticationError,
                requests.exceptions.HTTPError,
            ) as err:
                logger.error(err)
                return None

        return garmin

    def upload_to_garmin(self, email, password, data):
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
            elif (24 < bmi < 28 and 15 < body_fat < 26) or (
                21 < bmi < 28 and 21 < body_fat < 26
            ):
                return "2"
            elif (28 < bmi and 15 < body_fat) or (21 < bmi and body_fat < 26):
                return "3"
            else:
                return "未知类型"

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
            # try:
            #     garmin_client = Garmin(email, password, is_cn=True)
            #     garmin_client.login()
            #     print("佳明（cn）登陆成功！")  # 添加登录成功的提示
            # except (
            #     GarminConnectConnectionError,
            #     GarminConnectAuthenticationError,
            #     GarminConnectTooManyRequestsError,
            # ) as err:
            #     print("佳明（cn）登陆失败: %s" % err)
            #     quit()
            garmin_client = self.garmin_login(email, password)
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
                bmi=bmi,
            )
            print(f"{createTime} 的体重：{weight}kg，已经上传成功！")

    def get_weekly_data(self, isOnline=0):
        def get_weekly_report(data):
            """
            手动生成的周报
            """
            # print(data)
            # 本周体重数据
            weight_data = [entry["weight"] for entry in data["weight"]["detail"]]
            weight_data_str = ", ".join(map(str, weight_data))
            # BMI 和其他指标
            current_bmi = data["weight"]["bmi"]

            # 本周脂肪、肌肉等其他指标
            weight_change = "-"
            weight_data = "-"

            current_fat = data["weight"]["fat"]
            current_muscle = data["weight"]["muscle"]
            current_water = data["weight"]["water"]
            current_protein = data["weight"]["protein"]
            current_bmr = data["weight"]["bmr"] if data["weight"]["bmr"] else "-"

            user_name = self.nickname

            # 上周脂肪、肌肉等其他指标

            last_week_bmi = {"value": "-"}
            bmi_change = "-"

            last_week_fat = {"value": "-"}
            fat_change = "-"

            last_week_muscle = {"value": "-"}
            muscle_change = "-"

            last_week_water = {"value": "-"}
            water_change = "-"

            last_week_protein = {"value": "-"}
            protein_change = "-"

            last_week_bmr = "-"
            bmr_change = "-"

            # 提取数据
            current_weight = data["weight"]["endWeight"]
            lastWeekWeightReport = data.get("lastWeekWeightReport")

            if lastWeekWeightReport:
                last_week_weight = lastWeekWeightReport["endWeight"]
                weight_change = round(current_weight - last_week_weight, 2)

                # BMI 和其他指标

                last_week_bmi = lastWeekWeightReport["bmi"]
                bmi_change = round(current_bmi["value"] - last_week_bmi["value"], 2)

                # 脂肪、肌肉等其他指标

                last_week_fat = lastWeekWeightReport["fat"]
                fat_change = round(current_fat["value"] - last_week_fat["value"], 2)

                last_week_muscle = lastWeekWeightReport["muscle"]
                muscle_change = round(
                    current_muscle["value"] - last_week_muscle["value"], 2
                )

                last_week_water = lastWeekWeightReport["water"]
                water_change = round(
                    current_water["value"] - last_week_water["value"], 2
                )

                last_week_protein = lastWeekWeightReport["protein"]
                protein_change = round(
                    current_protein["value"] - last_week_protein["value"], 2
                )

                last_week_bmr = (
                    lastWeekWeightReport["bmr"] if lastWeekWeightReport["bmr"] else "-"
                )
                bmr_change = (
                    round(current_bmr - last_week_bmr, 2) if current_bmr != "-" else "-"
                )

            # 处理时间戳
            start_time = datetime.fromtimestamp(data["startTime"]).strftime("%Y/%m/%d")
            end_time = datetime.fromtimestamp(data["endTime"]).strftime("%Y/%m/%d")
            date_range = f"{start_time}~{end_time}"

            # 读取模板
            with open(
                os.path.join(BIN, "template", "weekly_template.html"),
                "r",
                encoding="utf-8",
            ) as f:
                template = Template(f.read())

            # 渲染模板
            output = template.render(
                user_name=user_name,
                current_weight=current_weight,
                weight_change=weight_change,
                weight_data=weight_data_str,
                current_bmi=current_bmi,
                last_week_bmi=last_week_bmi,
                bmi_change=bmi_change,
                current_fat=current_fat,
                last_week_fat=last_week_fat,
                fat_change=fat_change,
                current_muscle=current_muscle,
                last_week_muscle=last_week_muscle,
                muscle_change=muscle_change,
                current_water=current_water,
                last_week_water=last_week_water,
                water_change=water_change,
                current_protein=current_protein,
                last_week_protein=last_week_protein,
                protein_change=protein_change,
                current_bmr=current_bmr,
                last_week_bmr=last_week_bmr,
                bmr_change=bmr_change,
                date_range=date_range,  # 添加日期范围
            )

            # 保存为 HTML 文件
            if isOnline == 1:
                output_path = f"./static/result/{self.account}_weekly.html"
            else:
                output_path = f"./output/weekly_report_{self.nickname}.html"

            with open(output_path, "w", encoding="utf-8") as f:
                f.write(output)
            # os.remove(input_path)

        def get_weekly_report2(
            code,
            year,
            week,
        ):
            """
            获取云麦官网生成的周报
            """
            weekly_report_url = f"https://sq.iyunmai.com/health-weekly/details/?accessToken={self.access_token}&userId={self.user_id_real}&code={code}&signVersion=3&year={year}&week={week}"
            # 读取模板
            with open(
                os.path.join(BIN, "template", "weekly_template2.html"),
                "r",
                encoding="utf-8",
            ) as f:
                template = Template(f.read())

            # 渲染模板
            output = template.render(
                weekly_report_url=weekly_report_url,
            )

            # 保存为 HTML 文件
            if isOnline == 1:
                output_path = f"./static/result/{self.account}_weekly_v2.html"
            else:
                output_path = os.path.join(
                    BIN, "output", f"weekly_report_{self.nickname}_v2.html"
                )

            with open(output_path, "w", encoding="utf-8") as f:
                f.write(output)

        timestamp = str(int(time.time()))
        code = timestamp[:8] + "00"
        # 获取当前年份和周数
        now = datetime.now()
        year, week, _ = now.isocalendar()

        # year= 2024
        # week = 39
        # print(year, week)
        weekly_url = f"https://restapi.iyunmai.com/healthweekly/ios/weekReport/detail.json?accessToken={self.access_token}&userId={self.user_id_real}&code={code}&signVersion=3&year={year}&week={week-1}"
        # print(weekly_url)
        response = requests.get(weekly_url)
        json_data = response.json()
        json_data = json_data["data"]

        json_data = json.dumps(json_data, indent=2, ensure_ascii=False)
        if json.loads(json_data):
            get_weekly_report(json.loads(json_data))
            get_weekly_report2(
                code,
                year,
                week - 1,
            )
            print(f"已生成{self.nickname} {year}年第{week-1}周的周报数据")
        else:
            print(f"无法获取{self.nickname} {year}年第{week-1}周的周报数据")


# local
"payload: code=1734511000&refreshToken=618b04ab892a4947908090f6efb7b0ef&sign=60b3c003edad7d045d7a9d24c161775a&signVersion=3&versionCode=2"

# login
"payload: code=1734511000&refreshToken=668b04ab892a4947908090f6efb7b0ef&sign=8e7437968d434d3ef7188de62c30172c&signVersion=3&versionCode=2"
