from typing import Union

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
        self.sock = ClientSocket((XXIP, XXPORT))
        self.ip = self.sock.ip
        self.clients = [self.ip]
        self.app = QApplication()
        self.stats = Stats(self)
        self.stats.window.show()
        self.video_sock = VideoSock((XXIP, XXVIDEOPORT), self.stats)
        self.audio_sock = AudioSock((XXIP, XXAUDIOPORT))
        self.screen_sock = ScreenSock((XXIP, XXSCREEENPORT))
        self.beCtrlSock = beCtrlSock((self.ip, 5004))
        self.beCtrlHost = "10.25.10.50:5004"
        self.ctrlSock = None
        self.room_id: Union[int, None] = None

    def __del__(self):
        self.sock.close_conn()
        del self.video_sock, self.audio_sock, self.screen_sock, self.beCtrlSock

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

    def beControl(self):
        self.beCtrlSock.run()

    def remote_control(self):
        self.ctrlSock = CtrlSock(self.beCtrlHost)

    def setup(self):
        self.video_sock.room_id = self.room_id
        self.audio_sock.room_id = self.room_id
        self.screen_sock.room_id = self.room_id
        self.video_receiving()
        self.audio_receiving()

    def create_meeting(self):
        header = b'create room'
        data = b''
        self.sock.send_data(header, data)
        header, data = self.sock.receive_server_data()
        if header == '200 OK':
            self.room_id = int(data.split(' ')[1])
            self.setup()
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
            return True
        else:
            return False

    def update_all_clients(self):
        self.sock.sock.setblocking(False)
        while self.room_id:
            try:
                header, data = self.sock.receive_server_data()
            except:
                continue
            if header == 'clients':
                clients_list = []
                clients = data.split('\r\n')
                for seg in clients:
                    clients_list.append(seg[1])
                self.clients = clients_list
                self.stats.update_all_clients()
        self.sock.sock.setblocking(True)

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
