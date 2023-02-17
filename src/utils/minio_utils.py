#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time         :  2021/5/13 15:31
@Author       :  zhuhd
@file         :  minio_utils.py
@introduction :  
"""

import os
import io
import cv2
import uuid
import json
import numpy as np
from minio import Minio
from utils.load_config import cfg

class MinioUtil:
    host = cfg.minio_host
    port = cfg.minio_port
    bucket = "taskinfer"

    def __init__(self):
        # Minio地址
        self.host = MinioUtil.host
        # Minio端口
        self.port = MinioUtil.port
        access_key = cfg.minio_user
        secret_key = cfg.minio_passwd

        self.bucket = MinioUtil.bucket #Minio中文件夹名称
        # 本句代码是与Minio建立连接 ；secure=False 不适用Https连接
        self.mc = Minio(endpoint=self.host+":"+str(self.port), access_key=access_key, secret_key=secret_key, secure=False)


        if not self.mc.bucket_exists(self.bucket):
            self.mc.make_bucket(self.bucket)  # 文件夹不存在则新建文件夹
            policy = {
                    "Version":"2012-10-17",
                    "Statement":[{
                                "Effect":"Allow",
                                "Principal":{"AWS":["*"]},
                                "Action":["s3:GetBucketLocation","s3:ListBucket"],
                                "Resource":["arn:aws:s3:::{bucket}".format(bucket=self.bucket)]
                                },
                                {
                                "Effect":"Allow",
                                "Principal":{"AWS":["*"]},
                                "Action":["s3:GetObject"],
                                "Resource":["arn:aws:s3:::{bucket}/*".format(bucket=self.bucket)]
                                }]
                    }
            # minio是支持Amazon S3的策略的，使用set_bucket_policy()函数设置桶策略，可能是作者从哪抄来的吧
            self.mc.set_bucket_policy(bucket_name=self.bucket, policy=json.dumps(policy))


    def upload_img(self, img_url, img):
        img = cv2.imencode(".jpg", img)[1]  # cv2.imencode()将图像编码到内存缓冲区  '.jpg'表示把当前图片img按照jpg格式编码，按照不同格式编码的结果不一样
        img = np.array(img).tobytes()
        img_path = "/".join(img_url.split("/")[-4:])
        try:
            # file_data=io.BytesIO(img) 将字节对象转为Byte字节流数据；  file_stat.st_size=len(img)   content_type=image/jpeg
            self.mc.put_object(self.bucket, img_path, io.BytesIO(img), len(img), "image/jpeg")
            img_url = os.path.join("http://"+self.host+":"+str(self.port), self.bucket, img_path)
        except:
            img_url = None

        return img_url
    '''
    cv2打开的图像是‘numpy.ndarray’类型；
    Image打开的图像是'PIL.Image.Image'类型；
    '''

    def upload_pil_img(self, img_url, img):
        img_bytes = io.BytesIO()
        img.save(img_bytes, format="JPEG")
        imagebytes = img_bytes.getvalue()
        img_path = "/".join(img_url.split("/")[-4:])
        try:
            self.mc.put_object(self.bucket, img_path, io.BytesIO(imagebytes), len(imagebytes), "image/jpeg")
            img_url = os.path.join("http://"+self.host+":"+str(self.port), self.bucket, img_path)
        except:
            img_url = None

        return img_url


    '''
    用opencv处理图像时，可以发现获得的矩阵类型都是uint8
    uint8是专门用于存储各种图像的（包括RGB，灰度图像等），范围是从0–255
    '''
    def download_img(self, algo_name, img_name):
        img_path = os.path.join(algo_name, img_name)
        try:
            response = self.mc.get_object(self.bucket, img_path)
            img_bytes = response.read()
            nparr = np.frombuffer(img_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR) # 从内存中的缓冲区读取图像
            response.close()
            response.release_conn() #释放连接
        except:
            img = None
        return img


