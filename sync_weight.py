import requests
import json
import argparse
from datetime import datetime
import hashlib
import time
import base64
import urllib
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_v1_5
import os
import getpass


class WeightSync:
    def __init__(self, region="cn"):
        self.yunmai_base_url = "http://intl.yunmai.com/app/"
        self.region = region  # 保存region参数
        # 根据地区选择佳明API地址
        if region == "cn":
            self.garmin_base_url = "https://cn.garmin.com/modern/weight/"
        else:
            self.garmin_base_url = "https://connect.garmin.com/modern/weight/"
        self.token_file = "yunmai_token.json"
        self.garmin_file = "garmin_token.json"  # 新增佳明账号缓存文件

    def encrypt_account_password(self, account, password):
        """使用RSA加密账号密码"""
        if not account or not password:
            raise ValueError("账号和密码不能为空")

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

    def save_token(self, phone, refresh_token, user_id):
        """保存token到本地文件"""
        token_data = {
            "phone": phone,
            "refresh_token": refresh_token,
            "user_id": user_id,
            "timestamp": int(time.time()),
        }
        try:
            with open(self.token_file, "w") as f:
                json.dump(token_data, f)
        except Exception as e:
            print(f"保存token失败: {str(e)}")

    def load_token(self, phone):
        """从本地文件加载token"""
        try:
            if not os.path.exists(self.token_file):
                return None, None

            with open(self.token_file, "r") as f:
                token_data = json.load(f)

            # 验证token是否属于前用户
            if token_data.get("phone") != phone:
                return None, None

            # 验证token是否过期（7天）
            if int(time.time()) - token_data.get("timestamp", 0) > 7 * 24 * 3600:
                return None, None

            return token_data.get("refresh_token"), token_data.get("user_id")
        except Exception as e:
            print(f"加载token失败: {str(e)}")
            return None, None

    def get_weight_data(
        self,
        session,
        headers,
        code,
        user_id,
        access_token,
        start_time=None,
        end_time=None,
    ):
        """获取体重数据的独立方法"""
        try:
            # 如果没有指定开始时间，默认获取全部数据（从2000年开始）
            if start_time is None:
                start_time = str(int(datetime(2000, 1, 1).timestamp()))

            weight_url = "https://data.iyunmai.com/api/android/scale/list.json"

            weight_sign = f"code={code}&signVersion=3&startTime={start_time}&userId={user_id}&versionCode=2&secret=AUMtyBDV3vklBr6wtA2putAMwtmVcD5b"
            sign = hashlib.md5(weight_sign.encode()).hexdigest()

            weight_params = {
                "code": code,
                "signVersion": "3",
                "startTime": start_time,
                "userId": user_id,
                "versionCode": "2",
                "sign": sign,
            }

            headers["accessToken"] = access_token
            weight_resp = session.get(
                weight_url, params=weight_params, headers=headers, timeout=10
            )

            print(f"获取体重数据URL: {weight_resp.url}")
            print(f"获取体重数据响应状态码: {weight_resp.status_code}")

            weight_json = weight_resp.json()
            if weight_json.get("result", {}).get("code") != 0:
                print(f"获取体重数据失败: {weight_json.get('result', {}).get('msg')}")
                return None

            # 转换数据格式
            weight_list = []
            for item in weight_json["data"]["rows"]:
                try:
                    measure_time = int(item["timeStamp"])
                    # 如果指定了结束时间，跳过超出范围的数据
                    if end_time and measure_time > int(end_time):
                        continue

                    weight = float(item["weight"])
                    height = float(item.get("height", 170)) / 100  # 高，默认170cm

                    # 计算各项指标
                    weight_list.append(
                        {
                            "measureTime": measure_time,
                            "weight": weight,
                            "bodyFat": float(item.get("fat", 0)),  # 体脂率
                            "bodyWater": float(item.get("water", 0)),  # 水分率
                            "muscleMass": float(item.get("muscle", 0)),  # 肌肉量
                            "boneMass": float(item.get("bone", 0)),  # 骨量
                            "bmr": float(item.get("bmr", 0)),  # 基础代谢
                            "protein": float(item.get("protein", 0)),  # 蛋白质
                            "bodyAge": float(item.get("bodyAge", 0)),  # 体年龄
                            "visceralFat": float(item.get("visFat", 0)),  # 内脏脂肪等级
                            "bmi": round(weight / (height * height), 1),  # BMI
                            "bodyShape": int(item.get("bodyShape", 0)),  # 体型
                            "fatMass": round(
                                weight * float(item.get("fat", 0)) / 100, 2
                            ),  # 脂肪量
                            "muscleMassWeight": round(
                                weight * float(item.get("muscle", 0)) / 100, 2
                            ),  # 肌肉重量
                        }
                    )
                except (KeyError, ValueError) as e:
                    print(f"解析记录时错，过此条记录: {str(e)}")
                    continue

            return weight_list

        except Exception as e:
            print(f"获取体重数据异常: {str(e)}")
            return None

    def get_yunmai_data(self, phone, password=None, start_time=None, end_time=None):
        """从云麦获取体重数据"""
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "google/android(10,29) channel(huawei) app(4.25,42500010)screen(w,h=1080,1794)/scale",
        }

        timestamp = str(int(time.time()))
        code = timestamp[:8] + "00"

        # 尝试从本地加载token
        refresh_token, user_id = self.load_token(phone)

        if not refresh_token and not password:
            print("没有有效的token且未提供密码，无法进行认证")
            return None

        session = requests.Session()
        session.verify = False
        requests.packages.urllib3.disable_warnings()

        if refresh_token and user_id:
            print("使用缓存的refreshToken...")
            print(f"当前user_id: {user_id}")
            # 尝试用缓��的token
            # 尝试用缓存的token
            token_sign = f"code={code}&refreshToken={refresh_token}&signVersion=3&versionCode=2&secret=AUMtyBDV3vklBr6wtA2putAMwtmVcD5b"
            token_data = (
                f"code={code}&refreshToken={refresh_token}&sign={hashlib.md5(token_sign.encode()).hexdigest()}"
                f"&signVersion=3&versionCode=2"
            )

            try:
                print("正在请求新的accessToken...")
                token_resp = session.post(
                    "https://account.iyunmai.com/api/android/auth/token.d",
                    data=token_data,
                    headers=headers,
                    timeout=10,
                )

                print(f"Token响应状态码: {token_resp.status_code}")
                print(f"Token响应内容: {token_resp.text}")

                token_json = token_resp.json()
                if token_json["result"]["code"] == 0:
                    access_token = token_json["data"]["accessToken"]
                    print("refreshToken有效，获取accessToken成功")
                    # 将start_time和end_time传递给get_weight_data方法
                    return self.get_weight_data(
                        session,
                        headers,
                        code,
                        user_id,
                        access_token,
                        start_time,
                        end_time,
                    )
                else:
                    print("refreshToken已失效，需要重新登录")
                    try:
                        os.remove(self.token_file)
                    except:
                        pass
                    refresh_token = None
            except Exception as e:
                print(f"使用refreshToken获取accessToken失败: {str(e)}")
                refresh_token = None

        # 只有在需要重新登录时才打印签名细节
        print("开始云麦登录流程...")
        deviceUUID = "abcd"
        userId = "199999999"

        account_b64, account_URI, password_RSA, password_URI = (
            self.encrypt_account_password(phone, password)
        )

        print("\n=== 签名细节 ===")
        print(f"手机号: {phone}")
        print(f"手机号Base64编码: {account_b64}")
        print(f"手机号URI编码: {account_URI}")
        print(f"密码RSA: {password_RSA}")
        print(f"密码URI编码: {password_URI}")

        loginsign = (
            f"code={code}&deviceUUID={deviceUUID}&loginType=1&password={password_RSA}\n"
            f"&signVersion=3&userId={userId}&userName={account_b64}\n"
            f"&versionCode=7&secret=AUMtyBDV3vklBr6wtA2putAMwtmVcD5b"
        )

        print("\n=== 登录签名字符��详情 ===")
        print("原始签名字符串:")
        print(loginsign)
        print("\n字节编码:")
        print(loginsign.encode("utf-8"))
        print("\nMD5签名:")
        sign = hashlib.md5(loginsign.encode("utf-8")).hexdigest()
        print(sign)

        login_data = (
            f"password={password_URI}%0A&code={code}&loginType=1&userName={account_URI}%0A"
            f"&deviceUUID={deviceUUID}&versionCode=7&userId={userId}&signVersion=3&sign={sign}"
        )

        print("\n=== 最终请求数据 ===")
        print("编码前:")
        print(urllib.parse.unquote(login_data))
        print("\n编码后:")
        print(login_data)

        print("\n登录云麦请求:")
        print(f"URL: https://account.iyunmai.com/api/android/user/login.d")
        print("Headers:")
        print(json.dumps(headers, indent=2, ensure_ascii=False))
        print("Params:")
        print(f"  code: {code}")
        print(f"  deviceUUID: {deviceUUID}")
        print(f"  userId: {userId}")
        print(f"  sign: {sign}")
        print("————————————————————")

        try:
            session = requests.Session()
            session.verify = False
            requests.packages.urllib3.disable_warnings()

            login_resp = session.post(
                "https://account.iyunmai.com/api/android/user/login.d",
                data=login_data,
                headers=headers,
                timeout=10,
            )

            login_json = login_resp.json()
            print(f"登录响应: {login_json}")

            if login_json["result"]["code"] != 0:
                print(f"登录失败: {login_json['result']['msg']}")
                return None

            refresh_token = login_json["data"]["userinfo"]["refreshToken"]
            user_id = login_json["data"]["userinfo"]["userId"]

            # 保存token到本地文件
            self.save_token(phone, refresh_token, user_id)

            # 获取access token
            token_sign = f"code={code}&refreshToken={refresh_token}&signVersion=3&versionCode=2&secret=AUMtyBDV3vklBr6wtA2putAMwtmVcD5b"
            token_data = (
                f"code={code}&refreshToken={refresh_token}&sign={hashlib.md5(token_sign.encode()).hexdigest()}"
                f"&signVersion=3&versionCode=2"
            )

            print("\n=== Token请求详情 ===")
            print("URL:", "https://account.iyunmai.com/api/android/auth/token.d")
            print("Method: POST")
            print("Headers:")
            for key, value in headers.items():
                print(f"  {key}: {value}")
            print("Request Data (decoded):")
            print("  " + urllib.parse.unquote(token_data))
            print("Request Data (encoded):")
            print("  " + token_data)

            token_resp = session.post(
                "https://account.iyunmai.com/api/android/auth/token.d",
                data=token_data,
                headers=headers,
                timeout=10,
            )

            print("\n=== Token响应详情 ===")
            print(f"Status Code: {token_resp.status_code}")
            print("Response Headers:")
            for key, value in token_resp.headers.items():
                print(f"  {key}: {value}")
            print("Response Body:")
            print("  " + token_resp.text)

            token_json = token_resp.json()
            if token_json["result"]["code"] != 0:
                print(f"获取token失败: {token_json['result']['msg']}")
                return None

            access_token = token_json["data"]["accessToken"]

            # 获取体重数据
            return self.get_weight_data(
                session, headers, code, user_id, access_token, start_time, end_time
            )

        except requests.exceptions.RequestException as e:
            print(f"网络请求错误: {str(e)}")
            return None
        except json.JSONDecodeError as e:
            print(f"JSON解析错误: {str(e)}")
            print(
                f"响应内容: {login_resp.text if 'login_resp' in locals() else '未获得响应'}"
            )
            return None
        except Exception as e:
            print(f"其他错误: {str(e)}")
            return None

    def sync_to_garmin(self, weight_data, garmin_email, garmin_password):
        """同步数据到佳明"""
        try:
            from garminconnect import (
                Garmin,
                GarminConnectConnectionError,
                GarminConnectTooManyRequestsError,
                GarminConnectAuthenticationError,
            )
            from datetime import timezone, timedelta

            # 创建Garmin客户端实例
            try:
                garmin_client = Garmin(
                    garmin_email, garmin_password, is_cn=(self.region == "cn")
                )
                garmin_client.login()
                print(f"佳明（{'国内' if self.region == 'cn' else '国际'}）登录成功！")
            except (
                GarminConnectConnectionError,
                GarminConnectAuthenticationError,
                GarminConnectTooManyRequestsError,
            ) as err:
                print(
                    f"佳明（{'国内' if self.region == 'cn' else '国际'}）登录失败: {err}"
                )
                return False

            # 上传数据
            success_count = 0
            for record in weight_data:
                try:
                    # 转换时间戳为ISO格式
                    dt = datetime.fromtimestamp(record["measureTime"], tz=timezone.utc)
                    # 将区调整为中国时区
                    china_tz = timezone(timedelta(hours=8))
                    dt_china = dt.astimezone(china_tz)
                    iso_timestamp = dt_china.isoformat()

                    # 准备体重数据
                    garmin_client.add_body_composition(
                        timestamp=iso_timestamp,
                        weight=record["weight"],
                        percent_fat=record.get("bodyFat", 0),
                        percent_hydration=record.get("bodyWater", 0),
                        visceral_fat_mass=record.get(
                            "fatMass", 0
                        ),  # 使用计算出的脂肪量
                        bone_mass=record.get("boneMass", 0),  # 使用骨量数据
                        muscle_mass=record.get(
                            "muscleMassWeight", 0
                        ),  # 使用计算出的肌肉重量
                        basal_met=record.get("bmr", 0),  # 基础代谢
                        physique_rating=record.get("bodyShape", 0),  # 体型评分
                        metabolic_age=record.get("bodyAge", 0),  # 体年龄
                        visceral_fat_rating=record.get("visceralFat", 0),  # 脏脂肪等级
                        bmi=record.get("bmi", 0),  # BMI
                    )

                    success_count += 1
                    print(f"成功同步体重记录: {dt_china.strftime('%Y-%m-%d %H:%M:%S')}")
                    time.sleep(1)  # 避免请求过快

                except Exception as e:
                    print(
                        f"同步记录失败: {dt_china.strftime('%Y-%m-%d %H:%M:%S') if 'dt_china' in locals() else '未知时间'}"
                    )
                    print(f"错误信息: {str(e)}")
                    continue

            print(f"同步完成，成功: {success_count}/{len(weight_data)}")
            return success_count > 0

        except Exception as e:
            print(f"同步到佳明失败: {str(e)}")
            return False

    def check_cached_token(self):
        """检查是否存在有效的token缓存"""
        try:
            if not os.path.exists(self.token_file):
                return None, None

            with open(self.token_file, "r") as f:
                token_data = json.load(f)

            # 验证token是否过期（7天）
            if int(time.time()) - token_data.get("timestamp", 0) > 7 * 24 * 3600:
                return None, None

            return token_data.get("phone"), token_data.get("refresh_token")
        except Exception:
            return None, None

    def save_garmin_account(self, email, password, region):
        """保存佳明账号信息到本地文件"""
        account_data = {
            "email": email,
            "password": password,
            "region": region,
            "timestamp": int(time.time()),
        }
        try:
            with open(self.garmin_file, "w") as f:
                json.dump(account_data, f)
        except Exception as e:
            print(f"保存佳明账号信息失败: {str(e)}")

    def load_garmin_account(self):
        """从本地文件加载佳明账号信息"""
        try:
            if not os.path.exists(self.garmin_file):
                return None, None, None

            with open(self.garmin_file, "r") as f:
                account_data = json.load(f)

            # 验证缓存是否过期（30天）
            if int(time.time()) - account_data.get("timestamp", 0) > 30 * 24 * 3600:
                return None, None, None

            return (
                account_data.get("email"),
                account_data.get("password"),
                account_data.get("region"),
            )
        except Exception as e:
            print(f"加载佳明账号信息失败: {str(e)}")
            return None, None, None


def main():
    parser = argparse.ArgumentParser(description="云麦好轻体重数据同步到佳明")
    parser.add_argument("--start-date", help="开始日期，格式：YYYY-MM-DD")
    parser.add_argument(
        "--end-date", help="结束日期，格式：YYYY-MM-DD，不传则使用当前时间"
    )

    args = parser.parse_args()

    syncer = WeightSync()

    # 检查是否有缓存的token和账号信息
    cached_phone, cached_token = syncer.check_cached_token()
    cached_email, cached_password, cached_region = syncer.load_garmin_account()

    # 交互式输入云麦账号信息
    if cached_phone and cached_token:
        print(f"\n发现缓存的云麦账号: {cached_phone}")
        phone = cached_phone
        password = None
    else:
        print("\n=== 云麦账号信息 ===")
        phone = input("请输入云麦手机号: ").strip()
        password = getpass.getpass("请输入云麦密码: ").strip()

    # 交互式输入佳明账号信息
    if cached_email and cached_password and cached_region:
        print(f"\n发现缓存的佳明账号: {cached_email}")
        print(f"账号区域: {'中国区' if cached_region == 'cn' else '国际区'}")
        garmin_email = cached_email
        garmin_password = cached_password
        region = cached_region
    else:
        print("\n=== 佳明账号信息 ===")
        garmin_email = input("请输入佳明邮箱: ").strip()
        garmin_password = getpass.getpass("请输入佳明密码: ").strip()

        # 交互式选择佳明区域
        while True:
            region = input("\n请选择佳明账号区域 [1:中国区(默认) 2:国际区]: ").strip()
            if not region or region == "1":
                region = "cn"
                break
            elif region == "2":
                region = "global"
                break
            else:
                print("无效的选择，请重新输入")

        # 保存佳明账号信息
        syncer.save_garmin_account(garmin_email, garmin_password, region)

    syncer = WeightSync(region=region)

    # 转换日期为时间戳
    start_time = None
    end_time = None
    if args.start_date:
        start_time = int(datetime.strptime(args.start_date, "%Y-%m-%d").timestamp())
    if args.end_date:
        end_time = (
            int(datetime.strptime(args.end_date, "%Y-%m-%d").timestamp()) + 24 * 60 * 60
        )  # 加一天
    else:
        end_time = int(time.time())  # 使用当前时间作为结束时间

    # 获取云麦数据
    print("\n正在获取云麦数据...")
    weight_data = syncer.get_yunmai_data(phone, password, start_time, end_time)

    if not weight_data:
        if cached_token:
            print("使用缓存token失败，请重新运行程序并输入完整账号信息")
        else:
            print("获取云麦数据失败")
        return

    print(f"获取到 {len(weight_data)} 条体重记录")

    # 同步到佳明
    print("\n正在同步到佳明...")
    if syncer.sync_to_garmin(weight_data, garmin_email, garmin_password):
        print("同步完成")
    else:
        print("同步失败")


if __name__ == "__main__":
    main()
