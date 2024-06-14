from .stream import StreamAbstract
import can
from queue import Queue

class SocketCanStream(StreamAbstract):

    OTA_TRIGGER = 0x14

    def __init__(self, motor_id, interface = "can0") -> None:
        super().__init__()
        self.can_bus = can.Bus(interface, interface="socketcan")
        self.motor_id = motor_id
        self.recv_queue = Queue()

    def recv_byte(self) -> int:

        if not self.recv_queue.empty():
            return self.recv_queue.get()

        msg = self.can_bus.recv(timeout=0.001)

        if msg is None:
            return -1
        
        # check if message is for us.
        if (msg.arbitration_id >> 6 == self.motor_id):
            for i in range(msg.dlc):
                self.recv_queue.put(msg.data[i]) 

        if not self.recv_queue.empty():
            return self.recv_queue.get()
        
        return -1
    
    
    def send(self, data: bytes) -> None:
        chunk_size = 8
        num_chunks = len(data) + chunk_size - 1 // chunk_size
        for i in range(num_chunks):
            chunk = data[i * chunk_size : (i + 1) * chunk_size]
            msg = can.Message(arbitration_id=self.motor_id << 6 | 0x1F << 1 | 1, data=chunk, dlc=len(chunk))
            self.can_bus.send(msg)


    def initiate_ota(self):
        msg = can.Message(arbitration_id=self.motor_id << 6 | SocketCanStream.OTA_TRIGGER << 1 | 1, data=bytes([0]), dlc=1)
        self.can_bus.send(msg)