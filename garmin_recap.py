import json
import os
from jinja2 import Template
from garminconnect import (
    Garmin,
    GarminConnectConnectionError,
    GarminConnectTooManyRequestsError,
    GarminConnectAuthenticationError,
)
from datetime import datetime, timedelta

      
    


def garmin_login(email, password):
    try:
        garmin_client = Garmin(email, password, is_cn=True)
        garmin_client.login()
        print("佳明（cn）登陆成功！")
    except (
        GarminConnectConnectionError,
        GarminConnectAuthenticationError,
        GarminConnectTooManyRequestsError,
    ) as err:
        print("佳明（cn）登陆失败: %s" % err)
        quit()
    return garmin_client

def get_single_metric_data(metric, year, garmin_client):
    monthly_data = []
    for month in range(1, 13):
        start_date = datetime(year, month, 1).date()
        if month == 12:
            end_date = datetime(year, 12, 31).date()
        else:
            end_date = (start_date + timedelta(days=31)).replace(day=1) - timedelta(days=1)
        # recap_result = recap_by_garmin(garmin_client, metric, str(start_date), str(end_date))
        recap_result = garmin_client.get_progress_summary_between_dates(
        str(start_date),
        str(end_date),
        metric,
        True,
    )
        recap_final = recap_result[0]
        recap_final["date"] = f"{year}年{month}月"
        
        default_stat = {metric: {"count": 0, "min": 0, "max": 0, "avg": 0, "sum": 0}}
        default_stats = {
            "running": default_stat,
            "cycling": default_stat,
            "hiking": default_stat,
            "safety": default_stat
        }
        if not recap_final.get("stats"):
            recap_final["stats"] = default_stats
        recap_final_stats = recap_final.get("stats")
        # print(recap_final_stats)
        if recap_final_stats:
            if not recap_final_stats.get("running"):
                recap_final_stats["running"] = default_stat
            if not recap_final_stats.get("cycling"):
                recap_final_stats["cycling"] = default_stat
            if not recap_final_stats.get("hiking"):
                recap_final_stats["hiking"] = default_stat 
        monthly_data.append(recap_final)
    total_year_content[metric] =  monthly_data  
    return total_year_content



def get_summary_html(total_year_content, total_template_content):
    
    # print(total_year_content)
    for metric in ['distance','duration', 'elevationGain']:
        contents = total_year_content.get(metric)
        chart_data = {
            "months": [],
            "cycling": [],
            "running": [],
            "hiking":[]
            }
        for month in contents:
            
            chart_data["months"].append(month["date"])
            cycling_distance = month["stats"]["cycling"][metric]["sum"]
            running_distance = month["stats"]["running"][metric]["sum"]
            hiking_distance = month["stats"]["hiking"][metric]["sum"]
            
            if metric == "distance":
                chart_data["cycling"].append(round(cycling_distance / 100000, 1))
                chart_data["running"].append(round(running_distance/100000, 1))
                chart_data["hiking"].append(round(hiking_distance/100000, 1))
                unit = "km"
                title = "距离"
            elif metric == "elevationGain":
                chart_data["cycling"].append(round(cycling_distance / 100, 1))
                chart_data["running"].append(round(running_distance/100, 1))
                chart_data["hiking"].append(round(hiking_distance/100, 1))
                unit = "m"
                title = "总爬升"
            elif metric == "duration":
                chart_data["cycling"].append(round(cycling_distance / 3600000, 1))
                chart_data["running"].append(round(running_distance/ 3600000, 1))
                chart_data["hiking"].append(round(hiking_distance/ 3600000, 1))
                unit = "h"
                title = "总时间"
        
        render_params = {
                f"{metric}_months": chart_data["months"],
                f"{metric}_cycling": chart_data["cycling"],
                f"{metric}_running": chart_data["running"],
                f"{metric}_hiking": chart_data["hiking"],
                f"{metric}_metrics": metrics,
                f"{metric}_unit": unit,
                f"{metric}_title": title
            }
        # 替换内容
        for key, value in render_params.items():
            # 替换 {key} 为实际值
            total_template_content = total_template_content.replace(f"{key}", str(value))
        # print(render_params,'\n-------\n')
        
    html_path = f'./workouts_recap/{year}.html'
    with open(html_path, 'w', encoding="utf-8") as new_html_file:
        new_html_file.write(total_template_content)


if __name__ == "__main__":
    email = "254904240@qq.com"
    password = "Fsy364115."
    metrics = ["distance","elevationGain","duration"]
    garmin_client = garmin_login(email, password)
    
    for year in range(2020, 2025):
        total_year_content = {
                "distance":[],
                "duration":[],
                "elevationGain":[]
            }
        total_year_json_path = f'./workouts_recap/data/{year}.json'
        for metric in metrics:
            get_single_metric_data(metric, year, garmin_client)
    
        # with open(total_year_json_path, 'w', encoding='utf-8') as json_file:
        #     json.dump(total_year_content, json_file, ensure_ascii=False, indent=4)    
        
        # # 读取原始模板
        # total_year_json_path = f'./workouts_recap/data/{year}.json'
        # with open(total_year_json_path, 'r', encoding="utf-8") as f:
        #     total_year_content = json.loads(f.read())
        # # 读取原始模板
        with open('./workouts_recap/recap_total_template.html', 'r', encoding="utf-8") as total_template_file:
            total_template_content = total_template_file.read()
        get_summary_html(total_year_content, total_template_content)
        
        
    


