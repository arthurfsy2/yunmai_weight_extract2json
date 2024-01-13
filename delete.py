import os
import argparse
import glob


def removeFile(path, account):
    # 构建一个通配符表达式来匹配所有以{account}_开头的文件
    pattern = os.path.join(path, f"{account}_*")
    # 使用glob找到所有匹配的文件
    files_to_remove = glob.glob(pattern)

    # 遍历找到的文件列表并删除每个文件
    for file_path in files_to_remove:
        try:
            os.remove(file_path)
            print(f"Deleted file: {file_path}")
        except OSError as e:
            print(f"Error deleting file {file_path}: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("account", help="input your account")
    options = parser.parse_args()

    account = options.account
    removeFile("./static", account)
