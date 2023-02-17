from pydantic import BaseSettings
import os

curr_path = os.path.split(os.path.abspath(__file__))[0]
proj_path = os.path.dirname(os.path.dirname(curr_path))  # 返回绝对路径

class MyConfig(BaseSettings):

    # 算法配置
    #modelPath = os.path.join(proj_path, "model", "helmet_head_person_m.pt")
    modelPath = os.path.join(proj_path, "model", "mask_v2.pt")
    img_size = 640
    conf_thres = 0.5
    iou_thres = 0.5
    device = '0'
    classes = 0
    augment = False
    agnostic_nms = False

    # 后处理配置
    font_path = os.path.join(curr_path, "simfang.ttf")
    font_color = [255, 255, 255]
    #color_map = {"default":[255, 0, 0], "person":[255, 0, 0], "helmet":[0, 255, 0], "head":[0, 0, 255]} #   BGR
    #label_map = {"person":"人", "helmet":"已戴安全帽", "head":"未戴安全帽"}
    label_map = {"NoMask": "未带口罩", "Mask": "戴口罩"}
    color_map = {"default": [255, 0, 0], "NoMask": [0, 0, 255],"Mask":[0, 255, 0]}
    default_alarmLabel = ["NoMask"]
    max_interval = 7200  # 最大时间间隔
    tracker_class_filter = []
    tracker_max_iou_distance = 0.7
    tracker_max_age = 30
    tracker_n_init = 3
    tracker_r_times = 0
    alarm_delayed = 2
    alarm_keep_time = 2
    alarm_alive_threshold = 0.1
    img_upload_mode = 1   #0：同步；1：异步

    # 是否开启消费者模式
    is_consumer_open = True
    algorithm_name = "Facemask_Detect_gpu"
    is_track = True

    schedule_host = "10.110.63.23"
    schedule_port = 11011
    zk_root = "/task_infer"

    redis_host = "10.110.63.23"
    redis_port = 6379  #默认端口为 6379，作者在自己的一篇博文中解释了为什么选用 6379 作为默认端口，因为 6379 在手机按键上 MERZ 对应的号码，而 MERZ 取自意大利歌女 Alessia Merz 的名字
    redis_user = ""
    redis_passwd = "redis!23"

    rabbitmq_host = "10.110.63.23"
    rabbitmq_port = 5672
    rabbitmq_user = "rabbitmq"
    rabbitmq_passwd = "rabbitmq!23"

    minio_host = "10.110.63.23"
    minio_port = 9004
    minio_user = "minio"
    minio_passwd = "minio!23"

    zookeeper_host = "10.110.63.23"
    zookeeper_port = 2181
    zookeeper_timeout = 5
    

    # 环境变量设置
    class Config:
        fields = {
            'conf_thres': {'env': 'conf_thres'.upper()},
            'iou_thres': {'env': 'iou_thres'.upper()},
            'device': {'env': 'device'.upper()},
            'font_color': {'env': 'font_color'.upper()},
            'color_map': {'env': 'color_map'.upper()},
            'label_map': {'env': 'label_map'.upper()},
            'default_alarmLabel': {'env': 'default_alarmLabel'.upper()},
            'max_interval': {'env': 'max_interval'.upper()},
            'tracker_class_filter': {'env': 'tracker_class_filter'.upper()},
            'tracker_max_iou_distance': {'env': 'tracker_max_iou_distance'.upper()},
            'tracker_max_age': {'env': 'tracker_max_age'.upper()},
            'tracker_n_init': {'env': 'tracker_n_init'.upper()},
            'tracker_r_times': {'env': 'tracker_r_times'.upper()},
            'alarm_delayed': {'env': 'alarm_delayed'.upper()},
            'alarm_keep_time': {'env': 'alarm_keep_time'.upper()},
            'alarm_alive_threshold': {'env': 'alarm_alive_threshold'.upper()},
            'img_upload_mode': {'env': 'img_upload_mode'.upper()},

            'is_consumer_open': {'env': 'is_consumer_open'.upper()},
            'algorithm_name': {'env': 'algorithm_name'.upper()},
            'schedule_url': {'env': 'schedule_url'.upper()},
            'is_track': {'env': 'is_track'.upper()},
            'zk_root': {'env': 'zk_root'.upper()},

            'redis_host': {'env': 'redis_host'.upper()},
            'redis_port': {'env': 'redis_port'.upper()},
            'redis_user': {'env': 'redis_user'.upper()},
            'redis_passwd': {'env': 'redis_passwd'.upper()},
            'rabbitmq_host': {'env': 'rabbitmq_host'.upper()},
            'rabbitmq_port': {'env': 'rabbitmq_port'.upper()},
            'rabbitmq_user': {'env': 'rabbitmq_user'.upper()},
            'rabbitmq_passwd': {'env': 'rabbitmq_passwd'.upper()},
            'minio_host': {'env': 'minio_host'.upper()},
            'minio_port': {'env': 'minio_port'.upper()},
            'minio_user': {'env': 'minio_user'.upper()},
            'minio_passwd': {'env': 'minio_passwd'.upper()},
            'zookeeper_host': {'env': 'zookeeper_host'.upper()},
            'zookeeper_port': {'env': 'zookeeper_port'.upper()},
            'zookeeper_timeout': {'env': 'zookeeper_timeout'.upper()},
        }


cfg = MyConfig()
