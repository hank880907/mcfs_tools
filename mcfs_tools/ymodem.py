"""
This program is used to update the firmware of the MyActuator using Ymodem protocol.
"""

from .streams import StreamAbstract

import logging
import logzero
import time
from tqdm import tqdm

log_format = "%(color)s[%(levelname)s]%(end_color)s %(message)s"
formatter = logzero.LogFormatter(fmt=log_format)
logzero.formatter(formatter)
Logger = logzero.logger


def update_crc16(pre_crc: int, byte: int) -> int:
    crc = pre_crc
    in_byte = byte | 0x100
    while True:
        crc <<= 1
        in_byte <<= 1
        if in_byte & 0x100:
            crc += 1
        if crc & 0x10000:
            crc ^= 0x1021

        if (in_byte & 0x10000):
            break

    return crc & 0xffff    

def cal_crc16(data: bytes) -> int:
    crc = 0
    for byte in data:
        crc = update_crc16(crc, byte)
    crc = update_crc16(crc, 0)
    crc = update_crc16(crc, 0)
    return crc & 0xffff


class Ymodem:

    SOH = 0x01
    STX = 0x02
    EOT = 0x04
    ACK = 0x06
    NAK = 0x15
    CAN = 0x18
    C   = 0x43
    NH  = 0xF1
    NON_DATA_LEN = 5
    DATA_LEN = {SOH: 128, STX: 1024}

    def __init__(self, stream: StreamAbstract) -> None:

        if not isinstance(stream, StreamAbstract):
            raise TypeError("stream must be an instance of StreamAbstract.")
        
        self.stream: StreamAbstract = stream
        self.retransmission_count = 0

    def compute_crc(self, data_bytes) -> int:
        checksum = cal_crc16(data_bytes) & 0xffff
        return checksum

    def parse_data_packet(self, packet_number, data) -> bytes:
        """
        Send a packet using Ymodem protocol.
        :param header: SOH or STX
        :param packet_number: packet number
        :param bytes: data to be sent. The length of the data must be less than 1024 bytes.
        :return: True if the packet was sent successfully, False otherwise.
        """
        packet_type = Ymodem.SOH # < 128 bytes
        if len(data) > 128:
            packet_type = Ymodem.STX # > 128 bytes, < 1024 bytes
        
        if len(data) > 1024:
            raise ValueError("Packet size is too large.")

        packet = bytearray()
        packet.append(packet_type)               # SOH or STX
        packet_number = packet_number % 256
        packet.append(packet_number)  # packet number
        packet.append(0xFF - packet_number) # 1's complement of packet number

        padding_bytes_num = Ymodem.DATA_LEN[packet_type] - len(data)
        padding_bytes = bytes([0x1A] * padding_bytes_num)
        data_bytes = data + padding_bytes
        packet.extend(data_bytes)           # data

        checksum = self.compute_crc(data_bytes)
        packet.append(checksum >> 8)        # checksum high byte
        packet.append(checksum & 0xFF)      # checksum low byte
        return packet
    
    def is_packet_valid(self, packet: bytes) -> bool:

        single_byte_packets = [Ymodem.EOT, Ymodem.ACK, Ymodem.NAK, Ymodem.CAN, Ymodem.C]
        if packet[0] in single_byte_packets:
            return True
        
        # data packet
        if packet[0] == Ymodem.SOH or packet[0] == Ymodem.STX:
            
            if len(packet) != Ymodem.DATA_LEN[packet[0]] + Ymodem.NON_DATA_LEN:
                Logger.debug("Invalid packet. Packet length is incorrect.")
                return False

            if packet[1] + packet[2] != 0xFF:
                Logger.debug("Invalid packet. Packet number and its complement do not match.")
                return False
            
            checksum = self.compute_crc(packet[3:-2])
            if checksum != int.from_bytes(packet[-2:], byteorder='big'):
                Logger.debug("Invalid packet. Checksum does not match.")
                return False
        
        return True
        
        
    def serve_packet(self, packet: bytes, timeout = 5.0) -> bool:

        if (not self.is_packet_valid(packet)):
            raise ValueError("Invalid packet.")
        
        start_time = time.time()
        while True:

            if timeout > 0 and time.time() - start_time > timeout:
                Logger.debug("Timeout while waiting for response.")
                return False

            # clear the receive buffer before sending the packet.
            while self.stream.recv_byte() != -1:
                pass

            self.stream.send(packet)
            response = self.stream.wait_recv_byte(timeout)
            if response == Ymodem.ACK:
                Logger.debug("Received ACK.")
                return True
            elif response == Ymodem.NAK:
                self.retransmission_count += 1
                Logger.debug("Received NAK.")
            elif response == Ymodem.CAN:
                cancel_packet_count = 1
                for i in range(1):
                    response = self.stream.wait_recv_byte(0.1)
                    if response == Ymodem.CAN:
                        cancel_packet_count += 1
                    else:
                        break
                if cancel_packet_count == 2:
                    raise ConnectionError("Transfer canceled by the receiver.")
                
            elif response == -1:
                Logger.debug("Timeout while waiting for response.")
                return False

    
    def parse_initial_packet(self, filename: str, filesize: int) -> bool:
        initial_packet = bytearray()
        initial_packet.extend(bytes(filename.encode('ascii')))
        initial_packet.append(0)
        initial_packet.extend(bytes(str(filesize).encode('ascii')))
        initial_packet.append(0)
        if len(initial_packet) > 128:
            raise ValueError("Initial packet is too large.")
        padding_bytes_num = 128 - len(initial_packet)
        initial_packet.extend(bytes([0x00] * padding_bytes_num))
        return self.parse_data_packet(0, initial_packet)

    
    def parse_final_packet(self) -> bool:
        return bytes([Ymodem.EOT])
    
    def wait_for_request(self, timeout) -> bool:
        return self.stream.try_wait_for_byte(Ymodem.C, timeout)

    def send(self, filename, file_data:bytes, show_bar: bool = False) -> bool:
        """
        Send the file using Ymodem protocol.
        This function does not trigger the transfer.
        It waits for the receiver to send the initial C character.

        :return: True if the transfer was successful, False otherwise.
        """

        self.retransmission_count = 0

        if not self.wait_for_request(1.0):
            Logger.error("Timeout while waiting for the request.")
            return False
        
        initiate_transfer_packet = self.parse_initial_packet(filename, len(file_data))
        if not self.serve_packet(initiate_transfer_packet):
            Logger.error("Failed to send the initial packet.")
            return False
        
        
        chunk_size = 1024
        total_chunks = (len(file_data) + chunk_size - 1) // chunk_size
        chunk_num = 0

        # wait for second handshake
        if not self.stream.try_wait_for_byte(Ymodem.C, 5.0):
            Logger.error("Timeout while waiting for the second handshake.")
            return False

        with tqdm(total=len(file_data), disable=(not show_bar), unit="Byte") as pbar:
            while True:

                if chunk_num > total_chunks:
                    break

                packet = self.parse_data_packet(chunk_num + 1, file_data[chunk_num * chunk_size: (chunk_num + 1) * chunk_size])

                if not self.serve_packet(packet):
                    Logger.error("Failed to send packet.")
                    return False
                
                pbar.update(len(file_data[chunk_num * chunk_size: (chunk_num + 1) * chunk_size]))
                chunk_num += 1
                

        # send the final packet
        final_packet = self.parse_final_packet()
        if not self.serve_packet(final_packet):
            Logger.error("Failed to send the final packet.")
            return False
        
        Logger.info("File transfer completed.")
        return True
    
    def try_recv_packet(self, timeout) -> bytes:

        single_byte_packets = [Ymodem.EOT, Ymodem.ACK, Ymodem.NAK, Ymodem.CAN, Ymodem.C]
        start_time = time.time()
        while True:

            if timeout > 0 and time.time() - start_time > timeout:
                Logger.debug("Timeout while waiting for response.")
                return None

            header = self.stream.wait_recv_byte()
            if header in single_byte_packets:
                return bytes([header])
            
            expected_bytes_num = 0
            if header == -1:
                return None
            elif header == Ymodem.SOH:
                expected_bytes_num = Ymodem.DATA_LEN[Ymodem.SOH] + Ymodem.NON_DATA_LEN
            elif header == Ymodem.STX:
                expected_bytes_num = Ymodem.DATA_LEN[Ymodem.STX] + Ymodem.NON_DATA_LEN
            else:
                Logger.debug(f"Invalid packet header. {header}")
                expected_bytes_num = Ymodem.DATA_LEN[Ymodem.SOH] + Ymodem.NON_DATA_LEN # clears the recv buffer.

            packet = bytearray()
            packet.append(header)
            for _ in range(expected_bytes_num - 1): # less the header byte.
                byte = self.stream.wait_recv_byte(0.01)
                if byte == -1:
                    return None
                packet.append(byte)
            
            if self.is_packet_valid(packet):
                return packet
            
            return None
            
    def initiate_recv(self):
        # initiate transfer.
        self.stream.send(bytes([Ymodem.C]))
        while True:
            
            initial_packet = self.try_recv_packet(1.0)
            if initial_packet is None:
                Logger.warn("Failed to receive the initial packet.")
                self.stream.send(bytes([Ymodem.NAK]))
                time.sleep(1)
            else:
                break

        self.stream.send(bytes([Ymodem.ACK]))
        filename = initial_packet[3:initial_packet.find(0, 3)].decode('ascii')
        filesize = int(initial_packet[initial_packet.find(0, 3)+1:initial_packet.find(0, initial_packet.find(0, 3)+1)].decode('ascii'))
        return filename, filesize
        
    
    def recv(self, filesize: int = 0, show_bar = False) -> bytes:

        file_data = bytearray()
        chunk_num = 0

        self.stream.send(bytes([Ymodem.C])) # send the second handshake

        with tqdm(total=filesize, disable=(not show_bar), unit="Byte", ) as pbar:
            while True:

                packet = self.try_recv_packet(0.2)
                if packet is None:
                    Logger.debug("Failed to receive the packet. NAK sent.")
                    self.stream.send(bytes([Ymodem.NAK]))
                    continue

                if packet[0] == Ymodem.EOT:
                    self.stream.send(bytes([Ymodem.ACK]))
                    break

                if packet[0] == Ymodem.CAN:
                    cancel_packet_count = 1
                    for i in range(1):
                        packet = self.try_recv_packet(0.1)
                        if packet[0] == Ymodem.CAN:
                            cancel_packet_count += 1
                        else:
                            break
                    if cancel_packet_count == 2:
                        raise ConnectionError("Transfer canceled by the sender.")
                    else:
                        continue

                if packet[0] == Ymodem.SOH or packet[0] == Ymodem.STX:

                    if packet[1] != chunk_num % 256:
                        Logger.debug(f"Invalid chunk number. Expected: {chunk_num}, Received: {packet[1]}. NAK sent.")
                        self.stream.send(bytes([Ymodem.NAK]))
                        continue
                    
                    file_data.extend(packet[3:-2])
                    self.stream.send(bytes([Ymodem.ACK]))
                    Logger.debug(f"Received chunk {chunk_num}. ACK sent.")
                    chunk_num += 1
                    if len(file_data) < filesize:
                        pbar.update(len(packet[3:-2]))
                    else:
                        pbar.n = filesize
                        pbar.update(0)


        file_data = bytes(file_data[:filesize])
        Logger.debug("File transfer completed.")
        return file_data
    
    def cancel_transfer(self):
        self.stream.send(bytes([Ymodem.CAN]*2))