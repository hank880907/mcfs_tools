from .stream import StreamAbstract
import can
from queue import Queue

class SocketCanStream(StreamAbstract):

    OTA_TRIGGER = 0x14

    def __init__(self, motor_id, channel = "can0", custom_bus = None) -> None:
        super().__init__()
        self.motor_id = motor_id
        self.recv_queue = Queue()
        self.using_custom_bus = custom_bus is not None
        if custom_bus is not None:
            self.can_bus = custom_bus
        else:
            self.can_bus = can.Bus(channel, interface="socketcan")

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
        num_chunks = (len(data) + chunk_size - 1) // chunk_size
        for i in range(num_chunks):
            chunk = data[i * chunk_size : (i + 1) * chunk_size]
            msg = can.Message(arbitration_id=self.motor_id << 6 | 0x1F << 1 | 1, data=chunk, dlc=len(chunk), is_extended_id=False, is_remote_frame=False)
            self.can_bus.send(msg)


    def initiate_ota(self):
        msg = can.Message(arbitration_id=self.motor_id << 6 | SocketCanStream.OTA_TRIGGER << 1 | 1, data=bytes([0]), dlc=1, is_extended_id=False, is_remote_frame=False)
        self.can_bus.send(msg)

    def wait_for_ota(self):
        while True:
            msg = self.can_bus.recv(0.3)

            if msg is None:
                continue

            if msg.arbitration_id >> 6 == self.motor_id and (msg.arbitration_id >> 1 & 0xff) == 0x14:
                print("Received OTA trigger")
                return
            else:
                print("Received message: ", msg)

    def __exit__(self, exc_type, exc_value, traceback):
        if not self.using_custom_bus:
            self.can_bus.shutdown()
        return super().__exit__(exc_type, exc_value, traceback)