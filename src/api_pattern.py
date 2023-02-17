# !/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time   :  2019/7/4 10:50
@Author :  geqh
@file   :  api.py
"""
from impl.algo_impl import algoImpl
from utils.log import *
from utils.result import *
from utils.auto_cleaning import autocleaning
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Any
from swagger_ui import make_swagger_offline
import numpy as np
import base64
import cv2

app = FastAPI(docs_url=None) #
make_swagger_offline(app)


# 参数有效性检查，重定义返回结构，必要，无需修改
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    res = result(False, exc.errors(), Code.InvalidParameter, None)
    logger.error(res.__dict__)
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=res.__dict__,
    )


# 返回值结构及样例定义
class Response(BaseModel):
    isSuc: bool = Field(..., example=True)
    code: int = Field(..., example=0)
    msg: str = Field(..., example="success")
    res: Any = Field(..., example="dict")


# post body参数结构定义
class Item(BaseModel):
    base64_strs: str = Field(..., example="world")   # 必须参数
    task_name: str = ""


# post body参数模式，json格式，针对长参数
@app.post("/Facemask/detect",  # 接口名，必须
          summary="口罩检测，post body参数模式",  # 接口基本简介，swagger显示，非必须
          response_model=Response,  # 返回值样例，swagger显示，非必须
          tags=["口罩检测接口"])  # 标签，swagger显示，非必须
def interface(item: Item):
    logger.info("----------interface start---------")
    try:
        item_dict = item.dict()
        img_bytes = base64.b64decode(item_dict.get("base64_strs"))
        nparr = np.frombuffer(img_bytes, np.uint8)
        taskImg = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        taskImgs = [taskImg]
    except:
        res_final = result(False, "Img Decode Error", Code.InvalidParameter, None)
        logger.info(res_final.__dict__)
        logger.info("----------interface end---------\n")
        return res_final.__dict__

    taskId = item_dict.get("task_name")
    task = {
        "taskId":taskId,   # 任务id，追踪算法会有此参数，其他无
        "imgIds":[""],   # 图片id，api模式下无用
        "images":taskImgs,
        "param":{     # 其他参数，顺序添入即可 
        }
    }

    # ------ 清理器更新时间
    autocleaning.update(taskId)

    # ------ 调用算法处理函数进行任务处理
    code, res = algoImpl.task_proc(task)
    if code == Code.OK:
        res_final = result(True, Status.OK.get_value(), code, res)
    else:
        res_final = result(False, res, code, None)
    logger.info(res_final.__dict__)
    logger.info("----------interface end---------\n")
    return res_final.__dict__


def run():
    port = 8018
    logger.info("----api pattern open----port is " + str(port))

    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=port, log_config=None, access_log=False)
