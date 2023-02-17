#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time         :  2021/5/8 11:37
@Author       :  zhuhd
@file         :  zookeeper_utils.py
@introduction :  
"""

import os
import json

from kazoo.client import KazooClient
from utils.load_config import cfg


class ZookeeperUtil:

    def __init__(self, ban_retry=False):
        # Zookeeper地址
        host = cfg.zookeeper_host
        # Zookeeper端口
        port = cfg.zookeeper_port
        timeout = cfg.zookeeper_timeout
        retry_defaults = dict(max_tries=0) if ban_retry else None
        self.zkc = KazooClient(hosts=host+":"+str(port), timeout=timeout, connection_retry=retry_defaults)
        self.zkc.start(timeout=timeout)

    # ------------------------------------通用方法------------------------------------
    # -------------------------------------------------------------------------------
    # 判断节点是否存在
    def znode_exists(self, path):
        return self.zkc.exists(path)

    # 创建节点
    '''
    path：      节点路径
    value：     节点对应的值，注意值的类型是 bytes
    ephemeral短暂的： 若为 True 则创建一个临时节点，session 中断后自动删除该节点 默认 False
    sequence:   若为 True 则在创建节点名后面增加10位数字（例如：创建一个 test/test 节点，实际创建的是 test/test0000000003，字顺序递增） 默认 False
    makepath：  若为 False 父节点不存在时抛 NoNodeError。若为 True 父节点不存在则创建父节点。默认 False
    '''
    def zk_create(self, path, value=b"", ephemeral=False, sequence=False, makepath=False):
        if not isinstance(value, bytes):
            value = value.encode("UTF-8")
        return self.zkc.create(path, value, ephemeral=ephemeral, sequence=sequence, makepath=makepath)
        # 返回新节点的真实路径

    # 获取节点信息
    '''
    value：             节点对应的值，注意值的类型是 bytes
    stat.version:       节点修改次数
    stat.data_length:   节点值长度
    stat.numChildren：  子节点数量
    '''
    def zk_get(self, path):
        value, stat = self.zkc.get(path)
        if value is None:
            return None, stat
        value = value.decode("UTF-8")
        return value, stat

    # 获取节点下所有子节点（list）
    def zk_get_children(self, path):
        child_list = self.zkc.get_children(path)
        return child_list

    # 更改节点值
    def zk_set(self, path, value):
        if not isinstance(value, bytes):
            value = value.encode("UTF-8")
        self.zkc.set(path, value)

    # 删除节点
    '''
    recursive：若为 False，当需要删除的节点存在子节点，抛异常 NotEmptyError 若为True，则删除 此节点 以及 删除该节点的所有子节点
    '''
    def zk_delete(self, path, recursive=False):
        self.zkc.delete(path, recursive=recursive)

    # 判断是否在连接
    def zk_connected(self):
        return self.zkc.connected


    # -----------------------------消费者模式自定义方法-------------------------------
    # --------------------------------Custom Method---------------------------------
    # 获取节点字典
    def get_node_to_dict(self, queue_nodepath):
        value, _ = self.zk_get(queue_nodepath)
        return json.loads(value)

    # 设定队列节点状态
    def set_node_status(self, queue_nodepath, status):
        _dict = self.get_node_to_dict(queue_nodepath)
        _dict["status"] = status
        _value = json.dumps(_dict)  # 将数据结构转为JSON
        self.zk_set(queue_nodepath, _value)

    # 创建元节点
    '''
    元节点值类型: Dict={"status":"W", "IP":"0.0.0.0", "port":"6379", "user":"", "passwd":"redis!23"}
    status: W--工作状态，P--准备状态，U--非追踪态
    元节点值用于监控和初始化监控
    元节点下有“algo”，“video”节点，都为永久节点，用于挂载算法端和视频端
    '''
    def build_queue_znode(self, algo_path, value_dict):
        value = json.dumps(value_dict).encode("UTF-8")
        node_name = algo_path.split("/")[-1]
        queue_nodepath = os.path.join(algo_path, node_name)
        queue_nodepath = self.zk_create(queue_nodepath, value=value, ephemeral=False, sequence=True, makepath=True)
        a_nodepath = os.path.join(queue_nodepath, "algo")
        v_nodepath = os.path.join(queue_nodepath, "video")
        self.zk_create(a_nodepath, value=b"", ephemeral=False, sequence=False, makepath=True)
        self.zk_create(v_nodepath, value=b"", ephemeral=False, sequence=False, makepath=True)
        return queue_nodepath

