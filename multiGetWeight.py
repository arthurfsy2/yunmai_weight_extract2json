import subprocess
import argparse

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
        access_token_command = f"python getAccessToken.py {item['nickname']}"
        delete_userinfo_command = f"rm userinfo_{item['nickname']}.json"
        commands.append(login_command)
        commands.append(access_token_command)
        commands.append(delete_userinfo_command)
    return commands


result = parse_string(input_string)
subprocess_commands = generate_subprocess_commands(result)

for command in subprocess_commands:
    subprocess.run(command, shell=True)