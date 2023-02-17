#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time         :  2021/4/19 16:34
@Author       :  geqh
@file         :  consumer_pattern.py
@introduction :  
"""
import threading, _thread
from utils.load_config import cfg
from utils.log import *
from utils.redis_utils import RedisUtil
from utils.alarm_upload import Uploader
from utils.zookeeper_utils import ZookeeperUtil
from utils.task_pb2 import task_info
from impl.algo_impl import algoImpl
from utils.result import *
from utils.rabbitmq_utils import RabbitMQUtil
from utils.latest_cache import latestCache
import urllib.request
import numpy as np
import cv2
import base64
import json
import time
import requests

# Add apis for consumer_pattern 
import utils.add_apis
node_path = ""


def pro2buf_decode(task):

    def img_decode(img_bytes):
        # frombuffer将data以流的形式读入转化成ndarray对象
        # 用opencv处理图像时，可以发现获得的矩阵类型都是dtype=uint8
        nparr = np.frombuffer(img_bytes, np.uint8)
        # cv2.imdecode():从内存中的缓冲区读取图像
        # cv2.IMREAD_COLOR：默认参数，读入一副彩色图片，忽略alpha通道
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        return img # img:[H,W,C],

    def BIN_decode(img_info):
        img_bytes = img_info.data
        return img_decode(img_bytes)

    def URL_decode(img_info):
        resp = urllib.request.urlopen(img_info.data) #url:链接对应的图像
        return img_decode(resp.read())

    def B64_decode(img_info):
        img_bytes = base64.b64decode(img_info.data)
        return img_decode(img_bytes)

    def BGR_decode(img_info): #RGB格式符合我们预期数据格式不需要进行img_decode()解码
        img_bytes = img_info.data
        nparr = np.frombuffer(img_bytes, np.uint8)
        img = nparr.reshape((int(img_info.height), int(img_info.width), int(img_info.channelNum)))
        return img  # img:[H,W,C]

    switch = {
        1:BIN_decode,
        2:BGR_decode,
        3:URL_decode,
        4:B64_decode,
    }
    
    img_type = task.type
    imgs = list()
    img_Ids = list()
    for img_info in task.image:
        img_Ids.append(img_info.imageId)
        img = switch[img_type](img_info)   # img_type:1、2、3、4    获得数字对应的解码函数->BGR_decide(img_info)
        imgs.append(img)

    return imgs, img_Ids


def process():
    print("进入函数")
    global node_path
    #  ------ 第三方工具初始化
    try:
        redis_util = RedisUtil()
        rabbit_mq_util = RabbitMQUtil()
        zookeeper_util = ZookeeperUtil(ban_retry=True)
    except:
        logger.error("Middleware init Error")
        raise Exception("Middleware_init Error")

    # ------ 从调度端获取该算法容器对应队列名称
    # parameter
    schedule_host = cfg.schedule_host
    schedule_port = cfg.schedule_port  #11011
    schedule_url = "http://"+schedule_host+":"+str(schedule_port)+"/schedule/register"
    # {"isSuc":false,"code":-1,"msg":"Not Found","res":""}
    algorithm_name = cfg.algorithm_name
    is_track = cfg.is_track
    zk_root = cfg.zk_root
    connect_times = int(latestCache.get("Connection", "connect_times")) + 1 if latestCache.get("Connection", "connect_times") else 1
    latest_node = latestCache.get("Connection", "latest_node")
    param_request = {"algorithm_name": algorithm_name, "is_track": is_track, "recMaxsideLength": cfg.img_size, \
                     "redis_IP":redis_util.host, "redis_port":redis_util.port, "redis_user":redis_util.username, \
                     "redis_passwd":redis_util.password, "latest_node": latest_node,}
    logger.info("----consumer pattern get queue_name from schedule_url:" + schedule_url
                + "param:" + str(param_request))
    # request
    try:  # schedule_url对应的信息：{"isSuc":false,"code":-1,"msg":"Not Found","res":""}
        response = requests.post(schedule_url, params=param_request)
        print("5")
        # 使用requests.post发送请求 返回请求数据格式为json
    except:
        logger.error("get queue_name from schedule_url failed:"+schedule_url)
        raise Exception("Get_queue Error")
    # response process
    if response is None or len(response.json()) == 0:
        logger.error("get queue_name from schedule_url failed:"+schedule_url)
        raise Exception("Get_queue Error")
    r_dict = response.json()
    if not r_dict["isSuc"]:
        logger.error("get queue_name from schedule_url failed:"+str(r_dict["msg"]))
        raise Exception("Get_queue Error")
    queue_name = r_dict["res"]
    latestCache.set("Connection", "connect_times", str(connect_times))
    latestCache.set("Connection", "latest_time", time.strftime("%Y-%m-%d %H:%M:%S"))
    latestCache.set("Connection", "latest_node", queue_name)  # 更改最近节点的值为queue_name
    latestCache.write()  # 当作log日志写入latest_cache.ini
    logger.info("get queue_name from schedule_url success, queue_name:"+queue_name)

    # ------ 创建算法容器临时节点，用以监控容器停止，将队列置为无监听队列，方便新启动的算法容器接管
    queue_nodepath = os.path.join(zk_root, algorithm_name, queue_name) # /task_infer/SafetyHat_Detection_test/res:XXX
    a_path = os.path.join(queue_nodepath,"algo","algo") # /task_infer/SafetyHat_Detection_test/res:XXX/algo/algo
    node_path = zookeeper_util.zk_create(a_path, value=b"", ephemeral=True, sequence=True, makepath=False)
    stat = zookeeper_util.get_node_to_dict(queue_nodepath)["status"]
    child_num = zookeeper_util.zk_get(os.path.split(node_path)[0])[1].numChildren  #
    # os.path.split('PATH')按照路径将路径和文件名分割开  stat.numChildren
    if is_track:
        if stat == "P" and child_num == 1:
            zookeeper_util.set_node_status(queue_nodepath, "W")
        elif stat == "U":
            logger.error("Error the track algo:{algo} in zookeeper is untrack".format(algo=algorithm_name))
            raise Exception("Algo_type Error")
        else:
            logger.error("Error the track algo:{algo}'s zookeeper_queue_node:{path} is Working".format(algo=algorithm_name, \
                                                                                                        path=queue_nodepath))
            raise Exception("Queue_state Error")
    else:
        if stat != "U":
            logger.error("Error the untrack algo:{algo} in zookeeper is track".format(algo=algorithm_name))
            raise Exception("Algo_type Error")
    logger.info("----consumer pattern build znode in zookeeper:" + node_path)

    # ------ 持续轮询对应队列，获取任务信息，解析并处理，最终吐到rabbitmq队列
    count = 0
    while True:
        tic = time.time()
        if not zookeeper_util.zk_connected():
            logger.error("Zookeeper Error, Maybe there was a disconnection")
            raise Exception("Zookeeper Error")

        try:
            task_value = redis_util.r_rpop(queue_name)
        except:
            logger.error("Redis get task failed, Maybe there was a disconnection")
            raise Exception("Redis Error")

        if task_value is None or len(task_value) == 0:
            time.sleep(0.1)
            continue
        
        try:
            task = task_info()
            b = task.ParseFromString(task_value)
            print('b:',b)
        except:
            logger.info("----protobuf load Error----")
            continue

        taskId = task.taskId
        taskParm = {t.key:t.value for t in task.param}
        extra = task.extra
        taskImgs, img_Ids = pro2buf_decode(task)   # return : imgs, img_Ids

        if taskImgs is None:
            logger.info("----Img Decode Error:imgId-{imgId}----".format(imgId=img_Ids))
            res_final = result(False, "Img Decode Error:imgId-{imgId}".format(imgId=img_Ids), Code.InvalidParameter, None, \
                               alarm=None, extra=extra, imageId=None)
            '''
                self.isSuc = isSuc
                self.code = code
                self.msg = msg
                self.res = res
                self.alarm = alarm
                self.extra = extra
                self.imageId = imageId
            '''
            try:
                rabbit_mq_util.publish(taskId, json.dumps(res_final.__dict__)) # rabbit_mq作用? publish what?
            except:
                logger.error("rabbitmq publish task_res failed")
                raise Exception("Rabbitmq Error")
            continue

        task = {
            "taskId":taskId,
            "imgIds":img_Ids,
            "images":taskImgs,
            "param":taskParm # 其他参数
        }

        # ------ 调用算法处理函数进行任务处理(前处理，一般和api接口模式保持一致)
        code, task_res = algoImpl.task_proc(task)

        if code != Code.OK:
            res_final = result(False, res, code, None, alarm=None, extra=extra)
        else:
            # ------ 告警、异步上传
            alarm = Uploader.upload([task, task_res])
            res_final = result(True, Status.OK.get_value(), code, task_res, alarm=alarm, \
                extra=extra, imageId=img_Ids)
        logger.info(res_final.__dict__)
        
        # write result to rabbitMQ, taskId is exchange_name
        try:
            rabbit_mq_util.publish(taskId, json.dumps(res_final.__dict__))
        except:
            logger.error("rabbitmq publish task_res failed")
            raise Exception("Rabbitmq Error")
        logger.info("infer_time: " + str(time.time()-tic))
        count += 1


def main():
    # ------ 断连重启，如Debug可取消try
    #try:
    process()
    #except Exception as e:
        #logger.error(e.__str__())
        #_thread.interrupt_main()


def run():
    if not cfg.is_consumer_open:
        return
    logger.info("----consumer pattern open----")
    t = threading.Thread(target=main)
    t.setDaemon(True)   #设置为True 主线程结束，子线程立马结束
    t.start()
