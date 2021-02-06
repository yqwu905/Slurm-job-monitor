# Slurm job manager

[![test](https://img.shields.io/badge/License-BSD-Green.svg)](https://opensource.org/licenses/BSD-3-Clause)

## Introduction

* 这是什么?
  * 一个用于提交,管理,下载,查询使用`slurm`系统的超算系统上多账户任务的软件

* 怎么使用?
  * 安装相关的包(见[环境配置](#环境配置))之后,从main.py运行
  * 请自行配置`server_list.json`.(用于储存账户密码,见[配置`server_list.json`](#配置`server_list.json`))

* 实现了哪些那些功能?
  * 多账户的储存,登录(`ssh`+`scp`).
  * 一个简单的(非交互式)命令执行器.
  * 选择本地文件夹,自动上传并提交到`slurm`系统.
  * 一个任务管理系统,记录提交过的任务的状态,位置等.并可从服务器更新状态.
  * 下载任务到本地.
  * sock5代理支持

## Quick start

### 环境配置

在`python3.8`下开发.需要额外安装如下包:

* `paramiko`
* `PyQt5`
* `scp`
* `PySocks`

### 配置`server_list.json`

请注意,请**务必确保**`main.py`(或`main.exe`,如果你使用的是release的程序)所在目录有名为`server_list.json`的文件.否则程序将直接退出.

`server_list.json`格式如下:

```json
[
  {"server": "server1", "user": "user1", "passwd": "pwd1", "default_dir": "remote1"},
  {"server": "server2", "user": "user2", "passwd": "pwd2", "default_dir": "remote2"}
]
```

## User manual

**Notion:请尽量等程序进度条达到100%再进行下一操作.**

### 连接服务器

* 从顶端选框中选中你需要连接的服务器.
* 按下connect按钮

### 重新连接服务器

* 从顶端选框中选中你需要连接的服务器.
* 按下connect按钮😅

### 更新任务状态

* 按下Update Jobs Info按钮(不需要先连接服务器).

### 下载任务

* 选中一个任务(选中该行中任意一格就行).

* 按下Download Job按钮(不需要先连接服务器),选择目录.

  > 请不要同时选中多行(后面可能会支持多任务同时下载).
  >
  > 请不要不选中就按下按钮.
  >
  > 进度条不会动的,下载完就会变成100%,请耐心等待(大文件下载还是用专业软件吧).* 

### 提交任务

* 确保在您的任务文件夹中有sbatch后缀名的文件,系统会将该文件作为脚本提交.

* 先连接服务器.
* 设置本地任务文件夹和远程目录(远程目录仅支持直接输入绝对地址).
* 按下Submit按钮.

### 执行指令

* 请不要执行交互式命令(top, etc.)
* 输入指令(右上角的输入框).
* 按下Execute按钮.