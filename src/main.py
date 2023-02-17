#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time         :  2021/4/20 10:25
@Author       :  geqh
@file         :  main.py
@introduction :  主入口函数
"""
import api_pattern
import consumer_pattern

if __name__ == '__main__':
    consumer_pattern.run()
    api_pattern.run()
