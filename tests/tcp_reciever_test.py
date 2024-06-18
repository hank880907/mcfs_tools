from mcfs_tools.ymodem import Ymodem
from mcfs_tools.tcp_stream import TCPClientStream, UnreliableTCPClientStream
import argparse

def main(ip: str, port: int):

    print(f"Receiving file from {ip}:{port}")

    with TCPClientStream(ip, port) as stream:
        ymodem = Ymodem(stream)

        file_info = ymodem.initiate_recv()
        if file_info is None:
            print("failed to initiate transfer")
            return
        
        filename, filesize = file_info
        print(f"Receiving file: {filename} with size: {filesize}")
        try:
            data = ymodem.recv(filesize, show_bar=True)
        except KeyboardInterrupt:
            ymodem.cancel_transfer()
            print("Transfer canceled")
            return
        except ConnectionError as e:
            print("Connection error: ", e)
            return

        if data is None:
            print("failed to receive file")
            return
        
    with open("recieved_" + filename, 'wb') as f:
        f.write(data)

    print("File transfer completed.")
    print("Saved to: ", "recieved_" + filename)



if __name__ == "__main__":
    arg_parser = argparse.ArgumentParser(description='Receive a file using Ymodem protocol over TCP.')
    arg_parser.add_argument('--ip', type=str, help='The ip to connect to.', default="localhost")
    arg_parser.add_argument('-p', '--port', type=int, help='The port to connect to.', default=5005)
    args = arg_parser.parse_args()
    ip = args.ip
    port = args.port
    main(ip, port)