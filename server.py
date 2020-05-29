# server.py

import socket
from _thread import *
import sys

class Server:
    def __init__(self, ip, port):
        self.ip = ip
        self.port = port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
        self.users = []
        self.clients = []
        
        self.running = True
        
    def connect(self):
        try:
            self.socket.bind((self.ip, self.port))
        except socket.error as e:
            return False, str(e)
        
        return True, 'Connected'
    
    def listen(self):
        self.socket.listen(2)
        print('[SERVER] listening...')
        while self.running:
            conn, addr = self.socket.accept()
            self.clients.append(conn)
            print("[SERVER] Connected to:", addr)

            start_new_thread(self.threaded_client, (conn,))
    
    def broadcastUserList(self):
        self.sendToAll(str.encode('USERS|'+str(self.users)))
        
    def sendToAll(self, msg):
        print("[SERVER-BROADCAST]>> ", msg)
        for conn in self.clients:
            conn.sendall(msg)
        
    def stop(self):
        #self.socket.shutdown()
        self.running = False
        self.socket.close()
        
    def threaded_client(self, conn):
        conn.sendall(str.encode("CONNECTED"))
        reply = ""
        while True:
            try:
                data = conn.recv(2048)
                reply = data.decode("utf-8")

                if not data:
                    print("Disconnected")
                    break
                else:
                    print("[SERVER]<< ", reply)
                    cmd, username = reply.split('|')
                    if cmd=='NEW':
                        self.users.append(username)
                        self.broadcastUserList()
            except Exception as e:
                print(e)
                break

        print('[SERVER]', username, 'teminated!')
        self.clients.remove(conn)
        self.users.remove(username)
        self.broadcastUserList()
        conn.close()
        