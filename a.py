from flask import Flask, jsonify, request
from flask_cors import CORS
import subprocess
import os

app = Flask(__name__, static_folder='static')


@app.route('/run-script', methods=['POST'])
def run_script():

    # 获取用户输入的账号、密码和语言选项
    username = request.form.get('account')
    password = request.form.get('password')
    lang = request.form.get('lang')

    # 执行Python脚本并捕获输出
    login_result = subprocess.run(
        ['python', './login.py', username, password], capture_output=True, text=True)
    recap_result = subprocess.run(
        ['python', './postcrossingrecap.py', lang, username], capture_output=True, text=True)

    # 将标准输出和标准错误合并
    output = login_result.stderr + recap_result.stdout

    # 返回响应
    return jsonify(success=True, output=output)


@app.route('/list-recap-files', methods=['POST'])
def list_recap_files():
    # 获取用户输入的账号
    username = request.form.get('account')
    recap_folder = os.path.join(app.static_folder, 'recap')
    files = os.listdir(recap_folder)
    # 筛选出以username开头且以.html结尾的文件
    user_html_files = [f for f in files if f.startswith(
        username) and (f.endswith('.html') or f.endswith('.zip'))]
    return jsonify(user_html_files)

# 定义删除文件的路由


@app.route('/delete-endpoint', methods=['POST'])
def delete_files():
    username = request.form.get('account')
    delete_result = subprocess.run(
        ['python', './delete.py', username], capture_output=True, text=True)
    output = delete_result.stderr + delete_result.stdout
    return jsonify(success=True, output=output)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=4568)
    CORS(app)
