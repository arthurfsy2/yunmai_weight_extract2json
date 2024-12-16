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

BIN = os.path.dirname(os.path.realpath(__file__))


def get_user_report(weight_data, account, nickname, height, isOnline):
    def get_BMI_status(h):
        s1 = 18.5
        s2 = 24.0
        s3 = 28.0

        def calscore(s, h):
            return h * h * s

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

    def parse_sync_time(sync_time_str):
        return datetime.strptime(sync_time_str, "%Y-%m-%d %H:%M:%S")

    def find_closest_entry(data, target_datetime):
        closest_entry = min(
            data, key=lambda x: abs(parse_sync_time(x["syncTime"]) - target_datetime)
        )
        closest_entry_time = parse_sync_time(closest_entry["syncTime"])
        time_difference = abs(closest_entry_time - target_datetime)

        if time_difference > timedelta(days=6 * 30):  # 近似计算6个月
            return None

        return closest_entry

    def calculate_years_difference(latest_date, oldest_date):
        latest_datetime = datetime.fromtimestamp(latest_date["timeStamp"])
        oldest_datetime = datetime.fromtimestamp(oldest_date["timeStamp"])
        years_difference = latest_datetime.year - oldest_datetime.year
        return years_difference

    def generate_intervals_by_years(num):
        intervals_by_years = {}
        for i in range(1, num + 1):
            intervals_by_years[f"{i}年前"] = relativedelta(years=i)
        return intervals_by_years

    def generate_report(data):
        from dateutil.relativedelta import relativedelta

        latest_date = max(data, key=lambda x: x["timeStamp"])
        oldest_date = min(data, key=lambda x: x["timeStamp"])
        max_weight_data = max(data, key=lambda x: x["weight"])
        min_weight_data = min(data, key=lambda x: x["weight"])
        intervals_by_months = {
            "1个月前": relativedelta(months=1),
            "3个月前": relativedelta(months=3),
            "6个月前": relativedelta(months=6),
            "9个月前": relativedelta(months=9),
        }

        years_diff = calculate_years_difference(latest_date, oldest_date)
        intervals_by_years = generate_intervals_by_years(years_diff)

        report_lines_by_months = []

        for label, interval in intervals_by_months.items():
            time_latest = parse_sync_time(latest_date["syncTime"])
            target_date = time_latest - interval
            closest_entry = find_closest_entry(data, target_date)
            if closest_entry:
                weight_diff = latest_date["weight"] - closest_entry["weight"]
                lose_percent = weight_diff / closest_entry["weight"] * 100
                report_lines_by_months.append(
                    f"<tr><td>{label}</td><td>{closest_entry['syncTime']}</td><td>{closest_entry['weight']} kg</td><td>{weight_diff:.2f} kg</td><td>{lose_percent:.2f} %</td></tr>"
                )

        report_lines_by_years = []

        for label, interval in intervals_by_years.items():
            time_latest = parse_sync_time(latest_date["syncTime"])
            target_date = time_latest - interval
            closest_entry = find_closest_entry(data, target_date)
            if closest_entry:
                weight_diff = latest_date["weight"] - closest_entry["weight"]
                lose_percent = weight_diff / closest_entry["weight"] * 100
                report_lines_by_years.append(
                    f"<tr><td>{label}</td><td>{closest_entry['syncTime']}</td><td>{closest_entry['weight']} kg</td><td>{weight_diff:.2f} kg</td><td>{lose_percent:.2f} %</td></tr>"
                )
        # 假设 data 是一个包含 N 个类似 latest_date 的字典项的列表
        weight_to_rank = latest_date["weight"]
        # weight_to_rank = 64.85
        # 计算排名
        rank = 0  # 初始排名
        for item in data:
            if item["weight"] > weight_to_rank:
                rank += 1  # 如果发现 weight 大于最新的 weight，排名加 1
        rank_percent = f"{round((len(data) - rank)/len(data)*100,2)}"
        latest_desc = f'{latest_date['weight']} kg | {latest_date['syncTime']} | <img src="https://img.shields.io/badge/TOP-{rank_percent}%25-blue" height="20">'
        max_weight_desc = (
            f"{max_weight_data['weight']} kg | {max_weight_data['syncTime']}"
        )
        min_weight_desc = (
            f"{min_weight_data['weight']} kg | {min_weight_data['syncTime']}"
        )
        report_lines_by_months = "\n".join(report_lines_by_months)
        report_lines_by_years = "\n".join(report_lines_by_years)

        return (
            latest_desc,
            max_weight_desc,
            min_weight_desc,
            report_lines_by_months,
            report_lines_by_years,
        )

    json_data = json.dumps(weight_data, indent=2)
    # print(f"weight_data: {weight_data}\n\n")
    if isOnline == 1:
        weight_nicname_path = f"./static/result/{account}_weight.json"
    else:
        weight_nicname_path = os.path.join(BIN, "output", f"weight_{nickname}.json")
    with open(weight_nicname_path, "w", encoding="utf-8") as f:
        f.write(json_data)
        print(f"{weight_nicname_path}写入成功！")
        print("————————————————————")

    weight = json.dumps([item["weight"] for item in weight_data])
    createTime = json.dumps(
        [item["createTime"] for item in weight_data]
    )  # 将列表转换为 JSON 格式的字符串

    def get_avg(arr):
        avg = sum(arr) / len(arr)
        return round(avg, 2)

    average = str(round(get_avg([item["weight"] for item in weight_data]), 2))
    pieces = get_BMI_status(height)
    template_path = os.path.join(BIN, "template", "weight_report_template.html")

    # 读取模板
    with open(template_path, "r", encoding="utf-8") as f:
        template = Template(f.read())
    (
        latest_desc,
        max_weight_desc,
        min_weight_desc,
        report_lines_by_months,
        report_lines_by_years,
    ) = generate_report(weight_data)
    # 渲染模板
    dataNew = template.render(
        weight=weight,
        createTime=createTime,
        nickname=nickname,
        average=average,
        pieces=pieces,
        latest_desc=latest_desc,
        max_weight_desc=max_weight_desc,
        min_weight_desc=min_weight_desc,
        report_lines_by_months=report_lines_by_months,
        report_lines_by_years=report_lines_by_years,
    )

    if isOnline == 1:
        html_name = f"./static/result/{account}_weight.html"
    else:
        html_name = os.path.join(BIN, "output", f"weight_report_{nickname}.html")
    with open(html_name, "w", encoding="utf-8") as f:
        f.write(dataNew)
    print(f"已生成{html_name}")
