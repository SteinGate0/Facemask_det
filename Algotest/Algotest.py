import cv2
import os
import time
import json
import base64
import numpy as np
import threading

import consumer_pb2

from redis_utils import RedisUtil

redis_util = RedisUtil("10.110.63.23", "6379", "", "redis!23")

queue_name = "Play_Phone_Sleep_Detection_gpu0000000004"
#queue_name = "Leave_detecetion_gpu10000000000"
#queue_name = "Facemask_Detect_gpu0000000008"
#queue_name = "Mask_Detection_cpu0000000000"

VIDEO_PATH = "phone_sleep.mp4"
sleep_time = 0.04


# 图片存入protobuf
def corver_img_to_pro2buf(img, counter):
    img = cv2.resize(img, (1920, 1080))
    # bytes_img = cv2.imencode(".jpg", img)[1].tobytes() #type 1 ，二进制传输
    bytes_img = img.tobytes()  # type 2，bgr24格式传输
    h, w, c = img.shape
    # 添加数据
    task = consumer_pb2.task_info()

    # 添加值
    task.taskId = "1"
    task.type = 2  # 修改图片传输类型

    # 添加一张图片，图片信息如下
    image = task.image.add()
    image.imageId = str(counter)
    image.data = bytes_img
    image.height = h
    image.width = w
    image.channelNum = c

    #p0 = task.param.add()
    #p0.key = "time_interval"
    #p0.value = "3"
    # 添加param1
    # p0 = task.param.add()
    # p0.key = "regions"
    # p0.value = "[[0.5,0],[0.5,1],[1,1],[1,0]]]"
    # # 添加param2
    # p1 = task.param.add()
    # p1.key = "person_th"
    # p1.value = "5"

    # 序列化
    res = task.SerializeToString()

    return res


# 视频抽帧
def push_img_from_video(VIDEO_PATH, sleep_time, _max=None):
    cap = cv2.VideoCapture(VIDEO_PATH)
    counter = 0
    _time = 0
    while True:
        print("push", counter)
        ret, image = cap.read()
        if not ret:
            cap = cv2.VideoCapture(VIDEO_PATH)
            ret, image = cap.read()
        tic = time.time()
        # _str = corver_img_to_json(image, counter)
        _str = corver_img_to_pro2buf(image, counter)
        _time += time.time() - tic
        redis_util.r_lpush(queue_name, _str)
        time.sleep(sleep_time)
        counter += 1
        if _max and counter == _max:
            break
    print("push", _time / _max)


if __name__ == "__main__":
    push_img_from_video(VIDEO_PATH, sleep_time)
