# [yunmai_weight_extract2json](https://github.com/arthurfsy2/yunmai_weight_extract2json/tree/main)

一个可以输入账号、密码即可获取云麦好轻数据的脚本。

# 使用方法

1. clone本项目到本地，并在当前路径下运行终端
2. 运行以下代码获取体重数据：

   需要在后面加入“你的手机号/密码/自定义的昵称”，如果有多组数据，则以逗号隔开

多个举例： `python multiGetWeight.py 186XXXXX123/12xxx4/nickname1,136XXXXX123/12XXX1/nickname2`

单个举例：`python multiGetWeight.py 186XXXXX123/12xxx4/nickname1`

如果账号、密码无误的话，即可在当前路径下生成“userinfo\_自定义昵称.json”文件，里面包括userId_real、refreshToken、account_b64、password_RSA，以供getAccessToken.py使用。当getAccessToken.py正常运行后，会生成`weight\_自定义昵称.json`，记录了该账号的体重信息。如果输入了多个账号的信息，则批量生成weight\_自定义昵称.json文件

# Github Action

如果你想通过Github Action来实现定时获取数据，可进行以下步骤

1. fork本项目到你自己的仓库，然后修改fork仓库内的 `.github/workflows/run_data_sync.yml`文件，以下内容改为你自己的github信息。

```
env:
  GITHUB_NAME: arthurfsy2 （修改成你的github名称）
  GITHUB_EMAIL: fsyflh@gmail.com （修改为你的github账号邮箱）
```
 	默认执行时间是每天10:00（北京时间）会自动执行脚本。

​	如需修改时间，可修改以下代码的`cron`

```
on:
  workflow_dispatch:
  schedule:
    - cron: '0 2 * * *'
```



2. 为 GitHub Actions 添加代码提交权限 访问repo  Settings > Actions > General页面，找到Workflow permissions的设置项，将选项配置为Read and write permissions，支持 CI 将运动数据更新后提交到仓库中。

3. 在 repo Settings > Security > Secrets > secrets and variables > Actions  > New repository secret > 增加:
   name填写为：account，Secret填写为：“你的手机号/密码/自定义的昵称”（不需要双引号），如`186XXXXX123/12xxx4/nickname1`
   ![](/img/添加变量.png)

   