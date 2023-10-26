# [yunmai_weight_extract2json](https://github.com/arthurfsy2/yunmai_weight_extract2json/tree/main)

一个可以输入账号、密码即可获取云麦好轻数据的脚本。

# 步骤

1. clone本项目到本地，并在当前路径下运行终端
2. 运行以下代码获取体重数据：

   需要在后面加入“你的手机号/密码/自定义的昵称”，如果有多组数据，则以逗号隔开

多个举例： `python multiGetWeight.py "186XXXXX123/12xxx4/nickname1,136XXXXX123/12XXX1/nickname2"`

单个举例：`python multiGetWeight.py "186XXXXX123/12xxx4/nickname1"`

如果账号、密码无误的话，即可在当前路径下生成“userinfo_自定义昵称.json”文件，里面包括userId_real、refreshToken、account_b64、password_RSA，以供getWeightData.py使用。当getWeightData.py正常运行后，会生成 `weight_自定义昵称.json`，记录了该账号的体重信息。如果输入了多个账号的信息，则批量生成weight_自定义昵称.json文件

# Github Action

如果你想通过Github Action来实现定时获取数据，可进行以下步骤

1. fork本项目到你自己的仓库，然后修改fork仓库内的 `.github/workflows/run_data_sync.yml`文件，以下内容改为你自己的github信息。

```
env:
  GITHUB_NAME: arthurfsy2 （修改成你的github名称）
  GITHUB_EMAIL: fsyflh@gmail.com （修改为你的github账号邮箱）
```

    默认执行时间是每天10:00（北京时间）会自动执行脚本。

    如需修改时间，可修改以下代码的`cron`

```
on:
  workflow_dispatch:
  schedule:
    - cron: '0 2 * * *'
```

2. 为 GitHub Actions 添加代码提交权限 访问repo  Settings > Actions > General页面，找到Workflow permissions的设置项，将选项配置为Read and write permissions，支持 CI 将运动数据更新后提交到仓库中。
   **不设置允许的话，会导致workflows无法写入文件**
3. 在 repo Settings > Security > Secrets > secrets and variables > Actions  > New repository secret > 增加:
   name填写为：account，Secret填写为：“你的手机号/密码/自定义的昵称”（不需要双引号），如 `186XXXXX123/12xxx4/nickname1`
   ![img](/img/添加变量.png)

# 使用方法

## 1.CDN

1、成功获取体重的json文件,r如果希望国内网络流畅访问，且对数据更新没那么敏感的话，可考虑通过CDN加速一下，

### 推荐1.jsdelivr

* 格式为：`https://cdn.jsdelivr.net/gh/你的账号名/你的仓库名@分支名称/文件名称`
  如本仓库json链接：`https://cdn.jsdelivr.net/gh/arthurfsy2/yunmai_weight_extract2json@master/weight_fsy.json`

### 推荐2.gitmirror

可直接将 `raw.githubusercontent.com/XXX`换成 `raw.gitmirror.com/XXX`，即可实现免费CDN

上述2种方法获取的json文件为直链，可以通过python或javascript直接http的get请求，直接获取到数据

## 2、可通过echarts表格引入该json文件画出图表。

详见：[获取云麦好轻体重数据并在vuepress上通过echarts折线图展示](https://blog.4a1801.life/%E7%BB%8F%E9%AA%8C%E6%80%BB%E7%BB%93/IT%E6%80%BB%E7%BB%93/%E8%8E%B7%E5%8F%96%E4%BA%91%E9%BA%A6%E5%A5%BD%E8%BD%BB%E6%95%B0%E6%8D%AE%E5%B9%B6%E5%9C%A8vuepress%E4%B8%8A%E5%B1%95%E7%A4%BA.html)

# 备注
本脚本运行时，会产生中间文件"userinfo_{item['nickname']}.json"，保存了账户的login信息以供获取体重时使用。为了保证数据的安全，默认在执行完毕后进行删除。
如需保留，可以注释掉`multiGetWeight.py`的最后一行
`deleteUserInfo(result)`