from mcfs_tools.ymodem import Ymodem
from mcfs_tools.ros_stream import ROSStream
import os

# FILEPATH = "/home/hank/Documents/scripts/myactuator_firmware_update/RH20-P100 24060401.bin"
FILEPATH = "/home/greentech/catkin_ws/src/myactuator_firmware_update/RH20-P100 24060401.bin"

def main():

    with open(FILEPATH, 'rb') as f:
        data = f.read()

    filename = os.path.basename(FILEPATH)

    print("Sending file: ", filename, " with size: ", len(data))

    with ROSStream(0, "/A/if/can") as stream:

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

