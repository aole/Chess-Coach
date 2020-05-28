# server.py

import socket
from _thread import *
import sys

class Server:
    def __init__(self, ip, port):
        self.ip = ip
        self.port = port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
    def connect(self):
        try:
            self.socket.bind((self.ip, self.port))
        except socket.error as e:
            return False, str(e)
        
        return True, 'Connected'
    
    def listen(self):
        self.socket.listen(2)
        print('listening...')
        while True:
            conn, addr = self.socket.accept()
            print("Connected to:", addr)

            start_new_thread(self.threaded_client, (conn,))
    
    def threaded_client(self, conn):
        conn.send(str.encode("Connected"))
        reply = ""
        while True:
            try:
                data = conn.recv(2048)
                reply = data.decode("utf-8")

                if not data:
                    print("Disconnected")
                    break
                else:
                    print("Received: ", reply)
                    print("Sending : ", reply)

                conn.sendall(str.encode(reply))
            except:
                break

        print("Lost connection")
        conn.close()
            