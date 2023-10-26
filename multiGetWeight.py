import subprocess
import argparse
import os

parser = argparse.ArgumentParser()
parser.add_argument("input_string", help="输入该体重的用户名")        
options = parser.parse_args()


input_string = options.input_string
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


result = parse_string(input_string)
#print(result)

def generate_subprocess_commands(data):
    commands = []
    for item in data:
        login_command = f"python login.py {item['account']} {item['password']} {item['nickname']}"
        access_token_command = f"python getWeightData.py {item['nickname']}"
        commands.append(login_command)
        commands.append(access_token_command)
    return commands


result = parse_string(input_string)
subprocess_commands = generate_subprocess_commands(result)
for command in subprocess_commands:
    subprocess.run(command, shell=True)


def deleteUserInfo(data):
    for item in data:
        removePath = f"userinfo_{item['nickname']}.json"
        if os.path.exists(removePath):  # 检查文件是否存在
            os.remove(removePath) 
        print(f"\n已删除：userinfo_{item['nickname']}.json")


#如果想保留个人账号信息，请注释以下代码
deleteUserInfo(result)