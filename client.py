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
        self.beCtrlSock = beCtrlSock((self.ip, BECTRLPORT), self)
        # self.beCtrlHost = "10.25.10.50:80"
        self.ctrlSock = None
        self.room_id: Union[int, None] = None
        self.app = QApplication()
        self.stats = Stats(self)
        self.stats.window.show()
        self.host: Union[True, False] = False
        self.admin: Union[True, False] = False

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

    def stop_screen_sharing(self):
        self.screen_sock.sharing = False

    def screen_sharing(self):
        self.screen_sock.start_sharing()

    def screen_receiving(self):
        self.screen_sock.start_receiving()

    def beControl(self):
        self.beCtrlSock.run()

    def remote_control(self, beCtrlIp):
        self.ctrlSock = CtrlSock((str(beCtrlIp), BECTRLPORT),self)
        self.ctrlSock.run()

    def setup(self):
        self.video_sock.room_id = self.room_id
        self.audio_sock.room_id = self.room_id
        self.screen_sock.room_id = self.room_id
        self.video_receiving()
        self.audio_receiving()
        self.audio_sharing()
        self.screen_receiving()
        self.beControl()

    def create_meeting(self):
        header = b'create room'
        data = b' '
        self.sock.send_data(header, data)
        header, data = self.sock.receive_server_data()
        print(header, data)
        if header == '200 OK':
            reply_header = b'200 OK'
            reply_data = b' '
            self.sock.send_data(reply_header, reply_data)
            self.room_id = int(data.split(' ')[1])
            self.setup()
            self.host = True
            # threading.Thread(target=self.update_all_clients, daemon=True).start()
        else:
            pass

    def join_meeting(self, rid):
        header = b'join room'
        data = b'roomId ' + str(rid).encode()
        self.sock.send_data(header, data)
        header, data = self.sock.receive_server_data()
        if header == '200 OK':
            reply_header = b'200 OK'
            reply_data = b' '
            self.sock.send_data(reply_header, reply_data)
            self.room_id = int(data.split(' ')[1])
            self.setup()
            # threading.Thread(target=self.update_all_clients, daemon=True).start()
            return True
        else:
            return False

    def quit_meeting(self):
        if self.room_id is not None:
            print('enter quit meeting')
            header = b'quit room'
            data = b' '
            self.sock.send_data(header, data)
            self.video_sock.end_receiving()
            self.audio_sock.end_receiving()
            self.screen_sock.end_receiving()
            self.room_id = None
            self.host = False
            self.admin = False

    def close_meeting(self):
        if self.room_id is not None and (self.host or self.admin):
            print('enter close meeting')
            header = b'close room'
            data = b' '
            self.sock.send_data(header, data)
            self.video_sock.end_receiving()
            self.audio_sock.end_receiving()
            self.screen_sock.end_receiving()
            self.room_id = None
            self.host = False
            self.admin = False

    def set_admin(self, ip: str):
        if self.room_id is not None and self.host:
            header = b'set'
            data = f'admin:{ip}'.encode()
            self.sock.send_data(header, data)

    def transfer_host(self, ip: str):
        if self.room_id is not None and self.host:
            header = b'set'
            data = f'host:{ip}'.encode()
            self.sock.send_data(header, data)
            self.host = False


if __name__ == "__main__":
    # init server info
    client = Client()
    client.app.exec_()
    del client
    print("client connection lost...")
