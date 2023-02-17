## 基本介绍
```
该工程为安全帽检测算法，主要用于算法接口发布，依赖框架fastapi。
```
## 开发原则
```
* 工程命名规则[工程名-api]，工程名需要体现该接口主要功能
* 日志规则参见utils/log.py，使用:from utils.log import *
* 配置文件读取utils/load_config.py，使用:from utils.load_config import cfg
* api.py为接口文件，可直接运行测试
```
## 目录结构
```
├─ src
    ├─ impl # 算法流程实现目录
    │  └─ algo_impl.py  # 算法具体实现
    ├─ utils # 常用函数定义目录
    │  └─ log.py # 日志定义
    │  └─ load_config.py  # 配置文件
    │  └─ result.py  # 结果结构定义目录，内置错误码、状态信息等（根据需要自行增减）
    ├─ api_pattern.py # 接口实现
    ├─ consumer_pattern.py # 消费者模式实现
    ├─ main.py # 主程序入口
    
├─ docker-compose # docker-compose部署文件存放位置
     ├─ cpu # 模型文件
     │  └─ docker-compose.yml # cpu版本docker compose配置
     ├─ gpu # 模型文件
     │  └─ docker-compose.yml # gpu版本docker compose配置
├─ README.md
├─ Makefile # linux镜像构建、推送、启动、停止脚本
├─ requirements.txt # 依赖包
├─ Dockerfile_cpu # cpu版本docker镜像构建依赖文件
├─ Dockerfile_gpu # gpu版本docker镜像构建依赖文件
```
## 开发配置
```
1. 安装python3环境，设置环境变量；安装docker（前提条件）

2. 获取工程目录，根据相应功能自行重命名（可依赖前端自行配置）
    2.1 windows环境（pycharm）
        * 配置虚拟环境（隔离其他工程）
            File | Settings | Project: xxx | Project Interpreter
            add >> 填写虚拟环境目录（默认工程内部venv目录）>> base Interpreter(已经安装的基础Python环境)
        * 安装依赖环境 （demo工程中requirements.txt指定了基础环境，例如flask框架，如不需要，请自行安装所需包）
            Terminal窗口中 
            pip install -r requirements.txt
    2.2 linux 环境
        * pip install virtualenv
        * 在工程目录下，创建虚拟环境env  
            virtualenv env
            
        * 启用此环境，后续命令行前面出现（env）代表此时环境已切换，
            source ./env/bin/activate
            
        * 之后执行pip python 等指令，相当于是在此环境中执行
            pip install -r requirements.txt -i https://pypi.douban.com/simple
            
3. 后续自行开发相关功能
    注意配置文件src/utils/load_config.py，可直接配置配置项，环境变量形式
    对应docker-compose.yml中环境变量
                      
4. 开发完成，生成requirements.txt（用以部署）
    # 工程环境隔离的意义也体现于此，生成的requirements.txt文件中只包含本工程所需环境，无额外无关内容
    # 每次提交代码工程之前需要重新生成requirements.txt，然后提交
    生成方式，Terminal窗口中 
    pip freeze > requirements.txt
    
5. 编译打包
    5.1 docker模式编译打包
        5.1.1 编写Dockerfile
              Dockerfile参见demo
        5.1.2 构建镜像 
              docker build [OPTIONS] 上下文路径|URL
　　              • [OPTIONS]：通常指令包括-t，用来指定image的名字。-f指定Dockfile的上下文路径。
　　              • 上下文路径|URL：上下文路径， "." 代表当前目录。
                  例如： docker build --rm -f Dockerfile_cpu -t 10.110.63.25/iai/hello_api:v1.0-cpu .
        5.2.3 编写docker-compose.yml，用以docker启动
        5.2.4 镜像打包
              创建目标路径：target
              docker save -o <镜像包名> <镜像名>
              docker save -o target/hello_api.tar 10.110.63.25/iai/hello_api:v1.0-cpu
        5.2.5 镜像包加载
              docker load < hello_api.tar
              验证：docker images
              结果：
              REPOSITORY                  TAG                 IMAGE ID            CREATED             SIZE
              hello_api           latest              17c0f65cd69b        4 hours ago         59.7MB       
        5.2.6 启动
              在docker-compose.yml所在目录下
              pip install docker-compose -i https://pypi.douban.com/simple
              docker-compose up 
              
    5.2 docker镜像推送
        标签名格式：v1.0
        docker login -u <用户名> -p <密码> <镜像仓库地址>
        docker tag <镜像名>:<标签名> <镜像仓库地址>/<项目名>/<镜像名>:<标签名>
        docker push <镜像仓库地址>/<项目名>/<镜像名>:<标签名>

        docker login -u <用户名> -p <密码> 10.110.63.25
        docker push 10.110.63.25/iai/hello_api:v1.0-cpu     
```
## 安装部署
```
由于Python版本不好控制，因此仅支持docker方式安装部署
安装目录：/opt/interface/hello-api
mkdir -p /opt/interface/hello-api
docker模式：
    docker环境安装部署
    1.1 直接拉取镜像（可直接拉取镜像情况下）
        将docker-compose.yml迁移到/opt/interface/hello-api
        修改docker-compose.yml中对应配置

        docker pull 10.110.63.25/iai/hello_api:v1.0-cpu
        验证：docker images
              结果：
              REPOSITORY                  TAG                 IMAGE ID            CREATED             SIZE
              hello_api           latest              17c0f65cd69b        4 hours ago         59.7MB
        启动
              pip install docker-compose -i https://pypi.douban.com/simple
              docker-compose up
        
    1.2 依据镜像文件加载（内网，不可直接拉取镜像情况下）
        将docker-compose.yml及镜像文件hello_api.tar迁移到/opt/interface/hello-api
        修改docker-compose.yml中对应配置
                
        镜像包加载
              docker load < hello_api.tar
              验证：docker images
              结果：
              REPOSITORY                  TAG                 IMAGE ID            CREATED             SIZE
              hello_api           latest              17c0f65cd69b        4 hours ago         59.7MB
        启动
              pip install docker-compose -i https://pypi.douban.com/simple
              docker-compose up
```

## 接口定义
* 输入

| 参数 | 类型 | 是否必须 |详细说明 |
| ------ | ------ | ------ | ------ |
| base64_strs | string | 是 | 图片base64编码 |

* 输出

| 参数 | 类型 | 详细说明 |
| ------ | ------ | ------ |
| isSuc | boolean | 是否调用成功 |
| msg | string | 调用结果信息 |
| code | int | 调用结果码 |
| res | string | 最终结果 |

```
##请根据需要自行解释res结构意义

```

##接口使用示例
* swagger 地址
```
可查看接口基本情况及在线测试
http://127.0.0.1:8019/docs#/
```
* post参数模式
```
import requests

url="http://127.0.0.1:8019/interface_param"

if __name__ == "__main__":
    param_request = {"text": "world"}
    response = requests.post(url, params=param_request)
    print(response.json())
```
* post body json模式
```
import requests

url="http://127.0.0.1:8019/interface_body"

if __name__ == "__main__":
    param_request = {"text": "world"}
    response = requests.post(url, json=param_request)
    print(response.json())
```

