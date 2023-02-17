#!/usr/bin/env python
# -*- coding: utf-8 -*-

import threading
import os
import time

from utils.log import *
from utils.result import *
from utils.load_config import cfg

class AutoCleaning:
    __instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if not hasattr(cls, '_instance'):
            with cls._lock:
                if not hasattr(cls, '_instance'):
                    cls._instance = super(AutoCleaning, cls).__new__(cls, *args, **kwargs)
        return cls._instance


    def __init__(self):
        self.schedule_dict = {}
        self.mp_watcher_list = []
        max_interval = cfg.max_interval

        if max_interval > 0:
            t = threading.Thread(target=self.clean_process, args=(max_interval,))
            t.setDaemon(True) # 设置该线程为守护线程,表示该线程是不重要的,进程退出时不需要等待这个线程执行完成
            t.start()


    def update(self, task_name):
        if task_name:
            task_info = self.schedule_dict.setdefault(task_name, [0, 0])
            task_info[0] = time.time()


    def clean_process(self, max_interval=600):
        while True:
            time.sleep(max_interval/2)
            logger.info("---- start clean processing...----")

            for key in list(self.schedule_dict.keys()):
                if abs(self.schedule_dict.get(key, [time.time(), 0])[0] - time.time()) > max_interval:
                    logger.info("---- Cleaning schedule pop task:{} which latest update time exceed max_interval----".format(key))
                    for ind, _dict in enumerate(self.mp_watcher_list):
                        try:
                            _dict.pop(key)
                            logger.info("---- Pop _dict:{}-{} Done----".format("mainProcess", str(ind)))
                        except:
                            logger.info("---- Pop _dict:{}-{} Fail----".format("mainProcess", str(ind)))

                    try:
                        self.schedule_dict.pop(key)
                        logger.info("---- Pop _dict:{} Done----".format("TimeSchedule"))
                    except:
                        logger.info("---- Pop _dict:{} Fail----".format("TimeSchedule"))


autocleaning = AutoCleaning()