from mcfs_tools import Ymodem
from mcfs_tools.tcp_stream import TCPServerStream
import os
import argparse

def main(file_path: str, port: int):

    if (not os.path.exists(file_path)):
        print(f"File {file_path} does not exist")
        return

    with open(file_path, 'rb') as f:
        data = f.read()

    filename = os.path.basename(file_path)



    print("Sending file: ", filename, " with size: ", len(data))

    with TCPServerStream(port) as stream:

        ymodem = Ymodem(stream)
        success = False
        try:
            success = ymodem.send(filename, data, show_bar=True)
        except KeyboardInterrupt:
            ymodem.cancel_transfer()
            print("Transfer canceled")
        except ConnectionError as e:
            print("Connection error: ", e)
            return

    if not success:
        print("failed to send file")
        return
    
    print("File transfer completed. Total retransmissions: ", ymodem.retransmission_count)


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='Send a file using Ymodem protocol over TCP.')
    parser.add_argument('file', type=str, help='The file to send.')
    parser.add_argument('-p', '--port', type=int, help='The port to listen on.', default=5005)
    args = parser.parse_args()
    port = args.port
    FILEPATH = args.file
    main(FILEPATH, port)

