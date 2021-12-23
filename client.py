import threading
from typing import Union, List
from CONSTANTS import *
from client_sockets import *
from PySide2.QtWidgets import *
from ui.qt_test import Stats


class Client(object):
    """
        This is a client class.
        Feel free to define functions that you need here.
        The client would contain the ClientSocket(or its subclasses)
    """

    def __init__(self):
        super().__init__()
        self.sock = ClientSocket((XXIP, XXPORT))
        self.ip = self.sock.ip
        self.video_sock = VideoSock((XXIP, XXVIDEOPORT), self)
        self.audio_sock = AudioSock((XXIP, XXAUDIOPORT))
        self.screen_sock = ScreenSock((XXIP, XXSCREEENPORT))
        self.beCtrlSock = beCtrlSock((self.ip, BECTRLPORT))
        # self.beCtrlHost = "10.25.10.50:80"
        self.ctrlSock = None
        self.room_id: Union[int, None] = None
        self.app = QApplication()
        self.stats = Stats(self)
        self.stats.window.show()

    def __del__(self):
        self.sock.close_conn()
        del self.video_sock, self.audio_sock, self.screen_sock, self.beCtrlSock

    def video_update_frame(self, ip, frame):
        self.stats.update_image(ip, frame)

    def video_sharing(self):
        self.video_sock.start_sharing()

    def video_receiving(self):
        self.video_sock.start_receiving()

    def audio_sharing(self):
        self.audio_sock.start_sharing()

    def audio_receiving(self):
        self.audio_sock.start_receiving()

    def screen_sharing(self):
        self.screen_sock.start_sharing()

    def screen_receiving(self):
        self.screen_sock.start_receiving()

    # def beControl(self):
    #     self.beCtrlSock.run()
    #
    # def remote_control(self,beCtrlIp):
    #     self.ctrlSock = CtrlSock((str(beCtrlIp),BECTRLPORT))
    #     self.ctrlSock.run()

    def setup(self):
        self.video_sock.room_id = self.room_id
        self.audio_sock.room_id = self.room_id
        self.screen_sock.room_id = self.room_id
        self.video_receiving()
        self.audio_receiving()
        # self.audio_sharing()
        self.screen_receiving()
        # self.beControl()


    def create_meeting(self):
        header = b'create room'
        data = b''
        self.sock.send_data(header, data)
        header, data = self.sock.receive_server_data()
        if header == '200 OK':
            self.room_id = int(data.split(' ')[1])
            self.setup()
            # threading.Thread(target=self.update_all_clients, daemon=True).start()
        else:
            pass

    def join_meeting(self, rid):
        header = b'join room'
        data = b'roomId ' + str(rid).encode()
        self.sock.send_data(header, data)
        header, data = self.sock.receive_server_data()
        if header == '200 OK':
            self.room_id = int(data.split(' ')[1])
            self.setup()
            # threading.Thread(target=self.update_all_clients, daemon=True).start()
            return True
        else:
            return False

    def quit_meeting(self):
        header = b'quit room'
        data = b' '
        self.sock.send_data(header, data)
        self.video_sock.end_receiving()
        self.audio_sock.end_receiving()
        self.screen_sock.end_receiving()


if __name__ == "__main__":
    # init server info
    client = Client()
    client.app.exec_()
    del client
    print("client connection lost...")
