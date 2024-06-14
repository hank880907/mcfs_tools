from abc import ABC, abstractmethod
import time

class StreamAbstract(ABC):

    @abstractmethod
    def send(self, bytes) -> None:
        """
        Send data to the stream.
        :param bytes: data to be sent
        :return: number of bytes sent
        """
        pass


    @abstractmethod
    def recv_byte(self) -> int:
        """
        recieve a byte from the stream.
        return the byte received or -1 if the stream is closed.
        """
        pass


    def wait_recv_byte(self, timeout = 0.1) -> int:
        start_time = time.time()
        while True:
            byte = self.recv_byte()
            if byte != -1:
                return byte
            if time.time() - start_time > timeout:
                break
        return -1


    def try_wait_for_byte(self, byte:int, timeout) -> bool:
        start_time = time.time()
        while True:
            recv_byte = self.recv_byte()
            if recv_byte == byte:
                return True
            if time.time() - start_time > timeout:
                break
            time.sleep(0.001)
        return False

    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_value, traceback):
        pass