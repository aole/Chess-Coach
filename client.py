# client.py

import socket
from _thread import *

class Client:
    def __init__(self, ip, port, username, tab):
        self.username = username
        self.tab = tab
        self.ip = ip
        self.port = port
        self.addr = (ip, port)
        
        self.connected = False
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.connect()
        
        self.send('NEW|'+username)
        start_new_thread(self.listen, ())
        self.connected = True
            
    def connect(self):
        try:
            self.client.connect(self.addr)
        except Exception as e:
            print(e)

    def listen(self):
        while True:
            print('['+self.username+'] listening...')
            try:
                ret = self.client.recv(2048)
                if not ret:
                    break
                    
                ret = ret.decode("utf-8")
                print('['+self.username+']<< ', ret)
                if ret[:9]=='CONNECTED':
                    ret = ret[9:]
                if ret:
                    cmd, value = ret.split('|')
                    if cmd=='USERS':
                        self.tab.clearUsers()
                        for user in eval(value):
                            self.tab.addUser(user)
                
            except socket.error as e:
                print(e)
                break
        
    def send(self, data):
        try:
            print('['+self.username+']>> ', data)
            self.client.send(str.encode(data))
            
        except socket.error as e:
            print(e)
            
    def stop(self):
        self.client.close()
        