#!/usr/bin/env python
# -*- coding:utf-8 -*-

import re
import time
import urllib
import urllib2
import hashlib
import datetime

class Srun:
    def __init__(self, host, username, password, interval):
        self.username = username
        self.password = hashlib.md5(password).hexdigest()[8:-8]
        self.interval = interval
        self.host = host
        self.headers = {
            "Host": self.host,
            "Connection": "keep-alive",
            "Content-Length": "60",
            "Origin": "http://" + self.host,
            "User-Agent": "Mozilla/5.0 (Windows NT 6.1) Chrome/25.0.1364.172",
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "*/*",
            "Referer": "http://" + self.host + "/index.html",
            "Accept-Language": "zh-CN,zh;q=0.8",
            "Accept-Charset": "GBK,utf-8;q=0.7,*;q=0.3"
        }
        self.parameters = {
            "username": self.username,
            "password": self.password,
            "drop": "0",
            "type": "1",
            "n": "100"
        }
        self.login_url = "http://%s/cgi-bin/do_login" % self.host
        self.logout_url = "http://%s/cgi-bin/do_logout" % self.host
        
    def __get_param_len(self):
        res = 0
        for k,v in self.parameters.items():
            res += len(k) + len(v) + 1
        return res-1
        
    def __connect(self, url, param):
        self.parameters["n"] = "%d" % param
        self.headers["Content-Length"] = "%d" % self.__get_param_len()
        try:
            data = urllib.urlencode(self.parameters)
            req = urllib2.Request(url, data, self.headers)
            res = urllib2.urlopen(req)
            return res.read()
        except Exception, e:
            print e
        return None
        
    def __login(self):
        data = self.__connect(self.login_url, 100)
        if data == "ip_exist_error":
            self.__log("IP still online, sleeping 30 seconds")
            time.sleep(30)
            return self.__login()
            
        pattern = re.compile(r"\s*\d+[^\S]*")
        res = pattern.findall(data)
        if res != None and len(res) > 0:
            return True
        return False
        
    def __logout(self):
        data = self.__connect(self.logout_url, 1)
        if data == "logout_ok":
            return True
        return False
        
    def __checkOnline(self):
        req = urllib2.Request("http://www.baidu.com/")
        res = urllib2.urlopen(req)
        if res.read().find(self.host) != -1:
            return False
        return True
        
    def __log(self, msg):
        _time = datetime.datetime.now().strftime("%H:%M:%S")
        print "[%s] %s" % (_time, msg)
        
    def run(self):
        while True:
            if self.__checkOnline() == True:
                self.__log("online")
                self.__log("sleeping %d seconds" % self.interval)
                time.sleep(self.interval)
                continue
                
            self.__log("offline, try login now...")
            if self.__login() == True:
                self.__log("login success")
            else:
                self.__log("login failure, try logout now...")
                self.__log("sleeping 60 seconds after logout")
                self.__logout()
                time.sleep(60)
                
def main():
    while True:
        try:
            srun = Srun("{server_ip}", "{username}", "{password}", 30)
            #srun = Srun("{1.1.1.1}", "{22user}", "{33pwd}", 30)
            srun.run()
        except Exception, e:
            print e
            time.sleep(10)
            
if __name__ == "__main__":
    main()
    