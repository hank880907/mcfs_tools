from mcfs_tools.ymodem import Ymodem
from mcfs_tools.socketcan_stream import SocketCanStream

def main():

    with SocketCanStream(0, "can0") as stream:
        ymodem = Ymodem(stream)

        stream.wait_for_ota()

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



if __name__ == "__main__":
    main()
