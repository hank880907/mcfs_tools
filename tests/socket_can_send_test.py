from mcfs_tools.ymodem import Ymodem
from mcfs_tools.socketcan_stream import SocketCanStream
import os

# FILEPATH = "/home/hank/Documents/scripts/myactuator_firmware_update/RH20-P100 24060401.bin"
FILEPATH = "/home/hank/catkin_ws/src/myactuator_firmware_update/RH20-P100 24060401.bin"

def main():

    with open(FILEPATH, 'rb') as f:
        data = f.read()

    filename = os.path.basename(FILEPATH)

    print("Sending file: ", filename, " with size: ", len(data))

    with SocketCanStream(0, "can0") as stream:

        stream.initiate_ota()

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
    main()