# Add apis for consumer_pattern 
from api_pattern import Response, app
from utils.log import *
from utils.result import *
import consumer_pattern

# post body参数模式，json格式，针对长参数
@app.post("/get_path",  # 接口名，必须
          summary="获取算法节点路径",  #接口基本简介，swagger显示，非必须
          response_model=Response,  # 返回值样例，swagger显示，非必须
          tags=["算法调试接口"])  # 标签，swagger显示，非必须
def get_path():
    logger.info("----------Getpath start---------")
    res_final = result(True, "", 0, consumer_pattern.node_path)
    logger.info(res_final.__dict__)
    logger.info("----------Getpath end---------\n")
    return res_final.__dict__