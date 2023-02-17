#!/usr/bin/env python
# -*- coding: utf-8 -*-

import threading
import os
import sys
import ast
import uuid
import time
import numpy as np

from utils.log import *
from utils.result import *
from utils.load_config import cfg
from utils.minio_utils import MinioUtil
from utils.auto_cleaning import autocleaning
os.environ["CUDA_VISIBLE_DEVICES"] = cfg.device
curr_path = os.path.split(os.path.abspath(__file__))[0]
sys.path.append(curr_path)


class AlarmImpl:

    def __init__(self):
        self.mc_url = os.path.join("http://"+MinioUtil.host+":"+str(MinioUtil.port), MinioUtil.bucket)
        self.memory_dict = dict()
        
        self.default_alarmLabel = cfg.default_alarmLabel if isinstance(cfg.default_alarmLabel, list) else \
                                  ast.literal_eval(cfg.default_alarmLabel)

        self.delayed = cfg.alarm_delayed
        self.keep_time = cfg.alarm_keep_time
        self.alive_threshold = cfg.alarm_alive_threshold

        autocleaning.mp_watcher_list.append(self.memory_dict)

        # run one
        _ = uuid.uuid1()
        

    def alarm_proc(self, task, task_res):
        alarm_res = []
        img_data = []

        # 封装告警
        def alarm_canning(alarm_info):
            previous_task, previous_res = alarm_info

            im0 = previous_task["images"][0]
            imId = str(previous_task["imgIds"][0])
            
            folder = os.path.join(self.mc_url, time.strftime("%Y%m/%d"), cfg.algorithm_name)
            curr_time = str(time.time()*1000).split(".")[0][-8:]
            objImageUrl = os.path.join(folder, imId+"_"+previous_res["track_id"]+"_"+curr_time+".jpg")
            imageUrl = objImageUrl[:-4] + "_full.jpg"
            alarm_res.append({
                    "score":previous_res["score"],
                    "box":previous_res["box"],
                    "label":previous_res["label"],
                    "label_cn":previous_res["label_cn"],
                    "objImageUrl":objImageUrl,
                    "imageUrl":imageUrl
                })
            img_data.append({
                    "ori_img":im0,
                    "box":previous_res["box"],
                    "color":previous_res["color"],
                })

        tId = task["taskId"]
        alarm_label = task["param"].get("alarm_label", self.default_alarmLabel)
        if isinstance(alarm_label, str):
            alarm_label = ast.literal_eval(alarm_label)

        if tId:
            memory, info = self.memory_dict.setdefault(tId, [dict(),list([0])])
            for ind, t in enumerate(task_res):
                if t["label"] not in alarm_label:
                    continue
                if t["track_id"] not in memory:
                    memory[t["track_id"]] = list([None, t["label"], time.time() + self.delayed, list([task, t, 0])])
                # [目标最新更新时间,缓存标签,告警时间,告警缓存[task, res, 是否告警]]
                # get pointer/深度访问共享资源性能很差
                memory_track = memory[t["track_id"]]
                alarm_cache = memory_track[3]
                memory_track[0] = time.time()

                # 标签更改告警
                if t["label"] != memory_track[1]:
                    if not alarm_cache[2]:
                        alarm_canning(alarm_cache[:2])
                    memory_track[1] = t["label"]
                    memory_track[2] = time.time() + self.delayed
                    alarm_cache[0] = task
                    alarm_cache[1] = t
                    alarm_cache[2] = 0

                # 告警延时告警
                if time.time() > memory_track[2]:
                    alarm_canning(alarm_cache[:2])
                    memory_track[2] = float('inf')
                    alarm_cache[2] = 1

                else:
                    max_box = alarm_cache[1]["box"]
                    if t["box"][2]*t["box"][3] > max_box[2]*max_box[3]:
                        alarm_cache[0] = task
                        alarm_cache[1] = t

            for Id in list(memory.keys()):
                memory_track = memory[Id]
                if time.time() - memory_track[0] > self.keep_time:
                    alarm_cache = memory_track[3]
                    # 存活时间=最后更新时间-初始化时间    初始化时间=告警时间-告警延时
                    if memory_track[0] + self.delayed - memory_track[2] > self.alive_threshold and alarm_cache[2] == 0:
                        alarm_canning(alarm_cache[:2])
                    memory.pop(Id)

        return alarm_res, img_data



