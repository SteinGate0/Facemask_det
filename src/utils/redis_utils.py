#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time         :  2021/4/19 16:59
@Author       :  geqh
@file         :  redis_utils.py
@introduction :  
"""

import redis
from utils.load_config import cfg


class RedisUtil:
    __pool = None

    def __init__(self, host=None, port=None, username=None, password=None, socket_connect_timeout=None):
        # Redis地址
        self.host = host if host else cfg.redis_host
        
        # Redis端口
        self.port = port if port else cfg.redis_port
        self.username = username if username else cfg.redis_user
        self.password = password if password else cfg.redis_passwd
        self.__pool = redis.ConnectionPool(host=self.host, port=self.port, username=self.username, password=self.password, \
                                           socket_connect_timeout=socket_connect_timeout)
        # redis-py 使用 connection pool 来管理对一个 redis server 的所有连接，避免每次建立、释放连接的开销。
        # 默认，每个Redis实例都会维护一个自己的连接池。可以直接建立一个连接池，然后作为参数 Redis，这样就可以实现多个 Redis 实例共享一个连接池。


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
        value = redi.lpush(key, value)  #将key对应的value插入到列表头部

    # 获取队列数据rpop
    def r_rpop(self, key):
        redi = redis.Redis(connection_pool=self.__pool)
        value = redi.rpop(key)  #移除列表key对应的value
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

    # 判断连接状态
    def r_ping(self):
        try:
            redi = redis.Redis(connection_pool=self.__pool)
            redi.ping()
            return True
        except:
            return False

    def r_bgsave(self):
        redi = redis.Redis(connection_pool=self.__pool)
        try:
            return redi.bgsave()
        # Redis Bgsave 命令用于在后台异步保存当前数据库的数据到磁盘。
        # BGSAVE 命令执行之后立即返回 OK ，然后 Redis fork 出一个新子进程，
        # 原来的 Redis 进程(父进程)继续处理客户端请求，而子进程则负责将数据保存到磁盘，然后退出
        except:
            return False

    def r_lrange(self, key, start=0, end=-1):
        redi = redis.Redis(connection_pool=self.__pool)
        return redi.lrange(key, start, end)  # 返回列表中指定区间内的元素

    def r_lrem(self, key, value, num=0):
        redi = redis.Redis(connection_pool=self.__pool)
        return redi.lrem(key, num, value)
        # Redis Lrem 根据参数 COUNT 的值，移除列表中与参数 VALUE 相等的元素。
