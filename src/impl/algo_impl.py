#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time   :  2021/5/11 16:48
@Author :  zhuhd
"""
import threading
import os
import sys
import ast
from multiprocessing.sharedctypes import synchronized

from utils.log import *
from utils.result import *
from utils.load_config import cfg
from utils.minio_utils import MinioUtil
from utils.auto_cleaning import autocleaning
os.environ["CUDA_VISIBLE_DEVICES"] = cfg.device
curr_path = os.path.split(os.path.abspath(__file__))[0]
sys.path.append(curr_path)

import torch
import numpy as np
import cv2
import time
from PIL import Image, ImageDraw, ImageFont
from impl.models.experimental import attempt_load
from impl.utils.general import (
    check_img_size, non_max_suppression, apply_classifier, scale_coords,
    xyxy2xywh, strip_optimizer, set_logging)
from impl.utils.torch_utils import select_device, load_classifier
from impl.utils.datasets import letterbox

from impl.tracker.sort_v2.sort_v2 import Sort_v2 as Tracker


class AlgoImpl:
    model = None
    __instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if not hasattr(cls, '_instance'):
            with cls._lock:
                if not hasattr(cls, '_instance'):
                    cls._instance = super(AlgoImpl, cls).__new__(cls, *args, **kwargs)
        return cls._instance

    def __init__(self):
        weights, imgsz = cfg.modelPath, cfg.img_size
        set_logging()
        self.mc_url = os.path.join("http://"+MinioUtil.host+":"+str(MinioUtil.port), MinioUtil.bucket)
        self.device = select_device(cfg.device)
        self.augment, self.conf_thres, self.iou_thres, self.classes, self.agnostic_nms =\
            False, cfg.conf_thres, cfg.iou_thres, cfg.classes, cfg.agnostic_nms
        self.half = self.device.type != 'cpu'   # 使用GPU训练，model.half()模型可以改成半精度

        self.model = attempt_load(weights, map_location=self.device)
        self.imgsz = check_img_size(imgsz, s=self.model.stride.max())  # model.stride???
        if self.half:
            self.model.half()
        #hasattr() 函数用于判断对象是否包含对应的属性，返回布尔类型
        #self.names = self.model.module.names if hasattr(self.model, 'module') else self.model.names
        self.names = {0: 'NoMask',1: 'Mask'}

        self.tracker_class_filter = cfg.tracker_class_filter if isinstance(cfg.tracker_class_filter, list) else \
                                    ast.literal_eval(cfg.tracker_class_filter)  #ast.literal_eval()对字符串进行类型转换
        self.color_map = cfg.color_map if isinstance(cfg.color_map, dict) else ast.literal_eval(cfg.color_map)
        self.label_map = cfg.label_map if isinstance(cfg.label_map, dict) else ast.literal_eval(cfg.label_map)


        # run one           shape:[1,3,640,640]
        image = torch.rand((1, 3, self.imgsz, self.imgsz), device=self.device)
        _ = self.model(image.half() if self.half else image) if self.device.type != 'cpu' else None

        '''
        # build video tracker_pool
        # class_filter for don't track; if list is empty, track all classes
        # max_interval for tracking validity; if max_interval is int(-1), tracking never expires
        # max_interval用于跟踪有效性;如果max_interval为int(-1)，跟踪永不过期
        '''
        self.tracker = Tracker(class_filter=self.tracker_class_filter, max_iou_distance=cfg.tracker_max_iou_distance, 
                               max_age=cfg.tracker_max_age, n_init=cfg.tracker_n_init, r_times=cfg.tracker_r_times, 
                               a_cleaning=autocleaning)

    '''
    task:
        "taskId":taskId,
        "imgIds":img_Ids,
        "images":taskImgs,
        "param":taskParm # 其他参数
    '''
    def task_proc(self, task):
        tId = task["taskId"]
        im0 = task["images"][0]   # [h,w,channel]
        h,w = im0.shape[:2]
        img = letterbox(im0, new_shape=self.imgsz)[0]    # letterbox输出： img, ratio, (dw, dh)
        img = img[:, :, ::-1].transpose(2, 0, 1)
        # ascontiguousarray函数将一个内存不连续存储的数组转换为内存连续存储的数组，使得运行速度更快
        img = np.ascontiguousarray(img)

        img = torch.from_numpy(img).to(self.device)
        img = img.half() if self.half else img.float()   # 相应的输入数据也可以改成半精度
        img /= 255.0
        if img.ndimension() == 3:   # Tensor.ndimension()，返回tensor的维度（整数）
            img = img.unsqueeze(0)  # 维度加一

        pred = self.model(img, augment=self.augment)[0] # 预测值已经得到了？？
        #torch.Size([1, 15120, 8])
        pred = non_max_suppression(pred, self.conf_thres, self.iou_thres, classes=self.classes, agnostic=self.agnostic_nms)
        res = []
        det = pred[0]  # det:[,:]  第二维度:x1+y1+x2+y2+置信度+类别代码
        if det is not None and len(det):
            # scale_coords 这个函数是将坐标coords(x1y1x2y2)从img1_shape尺寸缩放到img0_shape尺寸
            det[:, :4] = scale_coords(img.shape[2:], det[:, :4], im0.shape).round() # .round()返回浮点数x的四舍五入值
            det = det.detach().cpu().numpy()
            tracks, _ = self.tracker.update(det, tId, None, im0)
            # updata()函数输出：outputs, goods_out
            # outputs：[np.array([x1, y1, x2, y2, conf, class_id, track_id]).reshape(1,-1),...,..]

            for trk in tracks:  # 多个tracks的意义
                score = '%.2f' %trk[4] # 置信度
                label = self.names[int(trk[5])] # 类别
                box = trk[:4]
                box[2:4] -= box[0:2]
                color = self.color_map[label] if label in self.color_map else self.color_map["default"]
                label_cn = self.label_map[label] if label in self.label_map else ""
                track_id = str(int(trk[6]))
                res.append({
                    "score":score,
                    "label": label,
                    "box":box.astype(np.int).tolist(),
                    "color":color,
                    "label_cn":label_cn,
                    "track_id":track_id
                })
        return Code.OK, res

algoImpl = AlgoImpl()

