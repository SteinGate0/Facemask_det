#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time         :  2021/4/28 14:19
@Author       :  geqh
@file         :  rabbitmq_utils.py
@introduction :  
"""
import pika
import sys
from utils.load_config import cfg
from utils.log import *


class RabbitMQUtil:
    __conn = None

    def __init__(self, heartbeat=0):
        # mq用户名和密码
        self.credentials = pika.PlainCredentials(cfg.rabbitmq_user, cfg.rabbitmq_passwd)  # 登陆凭证：用户名和密码
        self.parameters = pika.ConnectionParameters(host=cfg.rabbitmq_host, credentials=self.credentials,
                                        port=cfg.rabbitmq_port, heartbeat=heartbeat)
        # 心跳：0 为关闭 连接调整期间协商的AMQP连接心跳超时值或连接调整期间调用的可调用值
        self.makeChannel()

    def makeChannel(self):
        # Create a new instance of the Connection object
        self.__conn = pika.BlockingConnection(self.parameters)
        self.channel = self.__conn.channel()

    def publish(self, exchange_name, message):
        # 声明exchange，由exchange指定消息在哪个队列传递，如不存在，则创建。
        # durable = True 代表exchange持久化存储，False 非持久化存储
        # 2022/7/20  exchange_declare：该方法声明交换机。exchange:交换机名称
        # passive:执行检察或者只是检察是否存在， 默认为false， 即是，如果不存在则会创建交换机
        self.channel.exchange_declare(exchange=exchange_name, passive=False, durable=True, exchange_type='fanout')
        # fanout：输出

        # 向队列插入数值 routing_key是队列名。delivery_mode = 2 声明消息在队列中持久化，
        # delivery_mod = 1 消息非持久化。routing_key 不需要配置
        # 2022/7/20 routing_key:"",fanout则可以使用空字符"",广播到交换机下的队列
        # properties (pika.spec.BasicProperties) – Basic.properties 消息属性
        # body=message消息内容
        self.channel.basic_publish(exchange=exchange_name, routing_key='', body=message,
                              properties=pika.BasicProperties(delivery_mode=2))

    def publish_or_remakeChannel(self, exchange_name, message):
        if self.__conn.is_open:
            self.publish(exchange_name, message)
        else:
            sys.stdout.write("Warning: There may occur channel disconection in rabbitmq")
            try:
                self.makeChannel()
            except:
                pass

    # callback(ch, method, properties, body)
    def receive(self, exchange_name, callback, exception_back=None, auto_delete=True):
        self.channel.exchange_declare(exchange=exchange_name, passive=False, durable=True, exchange_type='fanout')
        if auto_delete:
            self.channel.queue_delete(queue=exchange_name)
        self.channel.queue_declare(queue=exchange_name, auto_delete=auto_delete) # auto_delete:断开连接时候是否自动删除
        self.channel.queue_bind(exchange=exchange_name, queue=exchange_name)  # queue_bind():将队列绑定到交换机
        self.channel.basic_consume(exchange_name, callback, auto_ack=True)  # auto_ack:是否自动确认， 默认不自动确认消息
        try:
            self.channel.start_consuming()  #尝试通道启动接受数据
        except Exception as e:
            sys.stderr.write(str(e.__repr__()))
            if exception_back:
                exception_back()

    def close(self):
        self.__conn.close()

    def __del__(self):
        if self.__conn:
            self.close()


