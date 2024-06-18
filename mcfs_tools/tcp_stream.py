from .stream import StreamAbstract

import socket
import threading
from queue import Queue
import random

class TCPClientStream(StreamAbstract):
    
        def __init__(self, ip: str, port: int, **kwarg) -> None:
            super().__init__()
            self.ip = ip
            self.port = port
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.recv_queue = Queue()
            self.thread = threading.Thread(target=self.recv_task)
            self.shutdown_event = threading.Event()

        def recv_task(self) -> None:
            while not self.shutdown_event.is_set():
                try:
                    data = self.socket.recv(4096)
                    if len(data) == 0:
                        break
                    for byte in data:
                        self.recv_queue.put(byte)
                except socket.timeout:
                    continue
                except OSError:
                    break


        def __enter__(self):
            self.connect()
            return self
        
        def __exit__(self, exc_type, exc_value, traceback):
            self.disconnect()
            return False
            

        def connect(self) -> None:
            self.socket.connect((self.ip, self.port))
            self.socket.settimeout(1)
            self.thread.start()


        def disconnect(self) -> None:
            self.shutdown_event.set()
            self.socket.close()
            self.thread.join()

        def recv_byte(self) -> int:
            if (self.recv_queue.empty()):
                return -1
            return self.recv_queue.get()

        def send(self, data: bytes) -> None:
            self.socket.send(data)


class TCPServerStream(StreamAbstract):

    def __init__(self, port: int, **kwarg) -> None:
        super().__init__()
        self.port = port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.bind(('', port))
        self.socket.listen(5)
        self.recv_queue = Queue()
        self.thread = threading.Thread(target=self.recv_task)
        self.shutdown_event = threading.Event()

    def recv_task(self) -> None:
        while not self.shutdown_event.is_set():
            try:
                data = self.client_socket.recv(4096)
                if len(data) == 0:
                    break
                for byte in data:
                    self.recv_queue.put(byte)
            except socket.timeout:
                continue
            except OSError:
                break

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.disconnect()
        return False
    
    def connect(self):
        print(f"Waiting connection on 0.0.0.0:{self.port}.")
        self.client_socket, self.addr = self.socket.accept()
        print("Got connection from", self.addr)
        self.client_socket.settimeout(1)
        self.thread.start()

    def disconnect(self) -> None:
        self.shutdown_event.set()
        self.client_socket.close()
        self.socket.close()
        self.thread.join()

    def recv_byte(self) -> int:
        if (self.recv_queue.empty()):
            return -1
        return self.recv_queue.get()

    def send(self, data: bytes) -> None:
        self.client_socket.send(data)



class UnreliableTCPClientStream(TCPClientStream):

    def __init__(self, ip: str, port: int) -> None:
        super().__init__(ip, port)
        random.seed(10)

    def recv_byte(self) -> int:
        b = super().recv_byte()
        if b == -1:
            return -1
        
        if random.uniform(0,1) < 0.002:
            
            # simulate lost packet
            if random.randint(0, 1) == 0:
                # print("Simulating lost packet")
                return -1
            # print("simulating corrupted packet")
            # simulate corrupted packet
            return random.randint(0, 255)
        
        return b