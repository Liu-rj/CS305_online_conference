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
        self.sock.connect()
        self.video_sock = VideoSock((XXIP, XXVIDEOPORT))
        self.audio_sock = AudioSock((XXIP, XXAUDIOPORT))
        self.screen_sock = ScreenSock((XXIP, XXSCREEENPORT))
        self.beCtrlSock = beCtrlSock()
        self.beCtrlHost = "10.25.10.50:80"
        self.ctrlSock = None
        self.room_id = None

    def __del__(self):
        self.sock.close_conn()
        del self.video_sock, self.audio_sock, self.screen_sock, self.beCtrlSock

    def video_sharing(self):
        self.video_sock.share_video.start()

    def video_receiving(self):
        self.video_sock.receive_video.start()

    def audio_sharing(self):
        self.audio_sock.share_audio.start()

    def audio_receiving(self):
        self.audio_sock.receive_audio.start()

    def screen_sharing(self):
        self.screen_sock.share_screen.start()

    def screen_receiving(self):
        self.screen_sock.receive_screen.start()

    def beControl(self):
        self.beCtrlSock.run()

    def remote_control(self):
        self.ctrlSock = CtrlSock(self.beCtrlHost)

    def create_meeting(self):
        header = b'create room'
        data = b''
        self.sock.send_data(header, data)
        header, data = self.sock.receive_server_data()
        if header == '200 OK':
            self.room_id = int(data.split(' ')[1])
            self.video_sock.room_id = self.room_id
            self.audio_sock.room_id = self.room_id
            self.screen_sock.room_id = self.room_id
            self.video_receiving()
            self.audio_receiving()
        else:
            pass

    def join_meeting(self, rid):
        header = b'join room'
        data = b'roomId ' + str(rid).encode()
        self.sock.send_data(header, data)
        header, data = self.sock.receive_server_data()
        if header == '200 OK':
            self.room_id = int(data.split(' ')[1])
            self.video_sock.room_id = self.room_id
            self.audio_sock.room_id = self.room_id
            self.screen_sock.room_id = self.room_id
            self.video_receiving()
            self.audio_receiving()
            return True
        else:
            return False


if __name__ == "__main__":
    # init server info
    client = Client()
    app = QApplication([])
    stats = Stats(client)
    stats.window.show()
    app.exec_()
    del client
    print("Video connection lost...")
