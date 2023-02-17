from utils.load_config import proj_path
import configparser
import os


class LatestCache(object):

    def __init__(self):
        self.cache_path = os.path.join(proj_path, "logs")
        self.cache_file = os.path.join(self.cache_path, "latest_cache.ini")

        if not os.path.exists(self.cache_path):
            os.makedirs(self.cache_path)

        if not os.path.exists(self.cache_file):
            os.mknod(self.cache_file) # mknod()方法创建名为filename的文件系统节

        self.cache = configparser.RawConfigParser() # 读取单个配置文件
        self.cache.read(self.cache_file)

    def get(self, section, option):
        if self.cache.has_section(section) and self.cache.has_option(section, option):
            return self.cache.get(section, option) # 得到section中option的值，返回为string类型
        else:
            return ""

    def set(self, section, option, value):
        if not self.cache.has_section(section):
            self.cache.add_section(section)
        self.cache.set(section, option, value)
        return

    def write(self):
        self.cache.write(open(self.cache_file, 'w'))
        return


latestCache = LatestCache()

        