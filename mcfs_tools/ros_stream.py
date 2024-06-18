from .socketcan_stream import SocketCanStream

from queue import Queue
import queue

import rospy
from can_msgs.msg import Frame
import can
import time


class ROSSocketCanAdapter:

    def __init__(self, motor_id: int, rx_topic = "can_rx", tx_topic = "can_tx") -> None:
        rospy.init_node('mcfs_tools', anonymous=True)
        self.rx_queue = Queue()
        self.tx = rospy.Publisher(tx_topic, Frame, queue_size=10)
        self.rx = rospy.Subscriber(rx_topic, Frame, lambda msg: self.rx_queue.put(msg))


    def recv(self, timeout):
        try:
            ros_msg: Frame = self.rx_queue.get(timeout=timeout)
            return can.Message(arbitration_id=ros_msg.id, data=ros_msg.data, dlc=ros_msg.dlc, is_extended_id=ros_msg.is_extended, is_remote_frame=ros_msg.is_rtr, is_error_frame=ros_msg.is_error)
        except queue.Empty:
            return None


    def send(self, msg: can.Message):
        ros_msg = Frame()
        ros_msg.id = msg.arbitration_id
        ros_msg.data = msg.data
        ros_msg.dlc = msg.dlc
        ros_msg.is_extended = msg.is_extended_id
        ros_msg.is_rtr = msg.is_remote_frame
        ros_msg.is_error = msg.is_error_frame
        time.sleep(0.001)
        self.tx.publish(ros_msg)


class ROSStream(SocketCanStream):

    def __init__(self, motor_id: int, channel: str, **kwarg) -> None:
        super().__init__(motor_id, channel, custom_bus=ROSSocketCanAdapter(motor_id, rx_topic=channel + "_rx", tx_topic=channel + "_tx"))
        time.sleep(0.3)