#!/usr/bin/env python
# -*- coding: utf-8 -*-

import threading
import os
import queue
from concurrent.futures import ThreadPoolExecutor

from utils.log import *
from utils.result import *
from utils.load_config import cfg

import numpy as np
import cv2
import time
from PIL import Image, ImageDraw, ImageFont

from utils.auto_cleaning import autocleaning
from utils.minio_utils import MinioUtil
from impl.alarm_impl import AlarmImpl

class MinioUpload:
    __instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if not hasattr(cls, '_instance'):
            with cls._lock:
                if not hasattr(cls, '_instance'):
                    cls._instance = super(MinioUpload, cls).__new__(cls, *args, **kwargs)
        return cls._instance


    def __init__(self):
        self.mc = MinioUtil()
        self.fontcolor = cfg.font_color if isinstance(cfg.font_color, list) else ast.literal_eval(cfg.font_color)

        self.queue = queue.Queue()
        self.alarm_dict = dict()

        self.executor = ThreadPoolExecutor(max_workers=100)
        autocleaning.mp_watcher_list.append(self.alarm_dict)
        
        self.upload_consumer = self.async_upload if cfg.img_upload_mode else self.upload_img

        t = threading.Thread(target=self.upload_processing)
        t.setDaemon(True)
        t.start()


    def upload(self, task_zip):
        task_name = task_zip[0]["taskId"]
        self.queue.put(task_zip)
        if task_name in self.alarm_dict:
            res_list = self.alarm_dict[task_name]
        else:
            res_list = list()
            self.alarm_dict[task_name] = res_list

        if len(res_list):
            return res_list.pop(0)
        else:
            return list()


    def upload_img(self, alarm_res, img_data):
        for ind, obj in enumerate(alarm_res):
            im0 = img_data[ind]["ori_img"]
            l,t,w,h = img_data[ind]["box"]
            color = img_data[ind]["color"][::-1]
            
            img_corp = im0[t:t+h,l:l+w]
            imc_url = self.mc.upload_img(obj["objImageUrl"], img_corp)
            img_PIL = Image.fromarray(cv2.cvtColor(im0, cv2.COLOR_BGR2RGB))
            img_draw = ImageDraw.Draw(img_PIL)
            tl = round(0.002 * (im0.shape[0] + im0.shape[1]) / 2) + 1  # 线/字体大小
            font = ImageFont.truetype(cfg.font_path, tl*10, encoding="utf-8")
            img_draw = ImageDraw.Draw(img_PIL)

            # 画图
            draw_text = " ".join([obj["label_cn"], obj["score"]])
            c1, c2 = (l, t), (l+w, t+h)
            img_draw.rectangle(xy=(c1[0], c1[1], c2[0], c2[1]), fill=None, outline=tuple(color), width=tl)
            fw,fh = font.getsize(draw_text)

            img_draw.rectangle(xy=(c1[0], c1[1], c1[0]+fw, c1[1]-fh), fill=tuple(color), outline=tuple(color), width=tl)
            position = (c1[0], c1[1] - tl*10)
            img_draw.text(position,draw_text,font=font,fill=tuple(self.fontcolor[::-1]))
            image_url = self.mc.upload_pil_img(obj["imageUrl"], img_PIL)


    def async_upload(self, alarm_res, img_data):
        self.executor.submit(self.upload_img, alarm_res, img_data)


    def upload_processing(self):
        alarmImpl = AlarmImpl()
        while True:
            task_zip = self.queue.get()
            task_name = task_zip[0]["taskId"]
            autocleaning.update(task_name)
            alarm_res, img_data = alarmImpl.alarm_proc(task_zip[0], task_zip[1])
            if alarm_res:
                logger.info("----Uploading task:{task_id}, img:{img_id}----".format(
                    task_id=task_name, img_id=task_zip[0]["imgIds"]))
                self.upload_consumer(alarm_res, img_data)
                self.alarm_dict[task_name].append(alarm_res)

Uploader = MinioUpload()

