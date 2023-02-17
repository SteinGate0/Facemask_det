#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time         :  2021/4/19 16:59
@Author       :  geqh
@file         :  redis_utils.py
@introduction :  
"""

import redis


class RedisUtil:
    __pool = None

    def __init__(self, host=None, port=None, username=None, password=None, socket_connect_timeout=None):
        # Redis地址
        self.host = host if host else ""

        # Redis端口
        self.port = port if port else ""
        self.username = username if username else ""
        self.password = password if password else ""
        self.__pool = redis.ConnectionPool(host=self.host, port=self.port, username=self.username, password=self.password, \
                                           socket_connect_timeout=socket_connect_timeout)

    # 保存数据
    # expire：过期时间，单位秒
    def r_set(self, key, value, expire=None):
        redi = redis.Redis(connection_pool=self.__pool)
        redi.set(key, value, ex=expire)

    # 获取数据
    def r_get(self, key):
        redi = redis.Redis(connection_pool=self.__pool)
        value = redi.get(key)
        if value is None:
            return None
        # value = value.decode("UTF-8")
        return value

    # 存队列数据lpush
    def r_lpush(self, key, value):
        redi = redis.Redis(connection_pool=self.__pool)
        value = redi.lpush(key, value)

    # 获取队列数据rpop
    def r_rpop(self, key):
        redi = redis.Redis(connection_pool=self.__pool)
        value = redi.rpop(key)
        if value is None:
            return None
        # value = value.decode("UTF-8")
        return value

    # 删除数据
    def r_del(self, key):
        redi = redis.Redis(connection_pool=self.__pool)
        redi.delete(key)

    # 判断key是否存在
    def r_exists(self, key):
        redi = redis.Redis(connection_pool=self.__pool)
        return redi.exists(key)

    # 获取队列长度
    def r_llen(self, key):
        redi = redis.Redis(connection_pool=self.__pool)
        return redi.llen(key)
