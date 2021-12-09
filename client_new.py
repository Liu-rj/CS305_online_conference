import time

from CONSTANTS import *
from client_sockets import *
import sys


'''
    We provide the main client class here. It is a free
    framework where you can implenment whatever you want.

    We also provide a simple CLI menu which cantains two menus:
        1. Main menu: If you are not in a meeting, you should use this menu
            1.1 Create a meeting
            1.2 Join a meeting
        2. Meeting menu: If you are in a meeting, you should use this menu
            2.1. (Stop) Share screen
            2.2. (Stop) Control other's screen
            2.3. (Stop) Control my screen
            2.4. (Stop) Share video
            2.5. (Stop) Share audio
            2.6. Leave a meeting
            2.7. Show current meeting members
        It is a simple meeting menu. Taking the first action for example,
        if you have not shared the screen, you start to share.
        Otherwise, you would stop video_sharing.
    You can use the variable of (client.state) and (client.changed) together to determine the
    CIL menu.

    If you want to implement the GUI directly, you can delete the CLI menu
    related code.
'''


class Client(object):
    """
        This is a client class.
        Feel free to define functions that you need here.
        The client would contain the ClientSocket(or its subclasses)
    """

    def __init__(self):
        self.sock = ClientSocket((XXIP, XXPORT))
        self.video_sock = VideoSock((XXIP, XXVIDEOPORT))
        self.audio_sock = AudioSock((XXIP, XXAUDIOPORT))
        self.screen_sock = ScreenSock((XXIP,XXSCREEENPORT))
        self.beCtrlSock = beCtrlSock()
        self.beCtrlHost = "127.0.0.1:80"
        self.ctrlSock = None
        # Here we define two variables for CIL menu
        self.state = MAIN
        self.changed = True
        self.is_alive = True
        self.name = '11911808'
        self.pwd = '123456'
        self.room_id = None

    def __del__(self):
        self.sock.close_conn()
        self.is_alive = False

    # # Here we define an action function to change the CIL menu
    # # based on different actions
    # def action(self, action):
    #     if self.state == MAIN:
    #         if action == '1':
    #             self.create_meeting()
    #         elif action == '2':
    #             sid = input("Please input the meeting id:")
    #             while not str.isdigit(sid):
    #                 sid = input("Please input the meeting id:")
    #             sid = int(sid)
    #             self.join_meeting(sid)
    #     elif self.state == MEETING:
    #         '''
    #             Please complete following codes
    #         '''
    #         if action == '1':
    #             pass
    #         elif action == '2':
    #             pass

    def login(self):
        self.sock.connect()
        header = b'login'
        data = 'username {}\r\npwd {}'.format(self.name, self.pwd).encode()
        self.sock.send_data(header, data)
        header, data = self.sock.receive_server_data()
        if header == '200 OK':
            return True
        else:
            return False

    def video_sharing(self):
        self.video_sock.share_video.start()

    def video_receiving(self):
        self.video_sock.receive_video.start()

    def audio_sharing(self):
        self.audio_sock.share_audio.start()

    def audio_receiving(self):
        self.audio_sock.receive_audio.start()

    def screen_sharing(self):
        self.screen_sock.share_screen().start()

    def screen_receiving(self):
        self.screen_sock.receive_screen().start()

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
            time.sleep(5)
            self.video_sharing()
            # self.video_receiving()
            # self.audio_sharing()
            self.audio_receiving()
            # self.screen_sharing()
            # self.screen_receiving()
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
            self.audio_sharing()
            # self.audio_receiving()
            # self.screen_sharing()
            # self.screen_receiving()
        else:
            return False


if __name__ == "__main__":
    # init server info
    client = Client()
    status = client.login()
    if status:
        print('successfully login!')
        client.join_meeting(0)
    while True:
        time.sleep(1)
        if not client.is_alive:
            print("Video connection lost...")
            sys.exit(0)
    # # A CIL menu loop
    # while True:
    #     if client.changed and client.state == MAIN:
    #         client.changed = False
    #         # Main menu
    #         print("1. Create a meeting")
    #         print("2. Join a meeting")
    #         action = input("Action:")
    #         client.action(action)
    #     elif client.changed and client.state == MEETING:
    #         client.changed = False
    #         print("You are in the meeting: %d" % client.sid)
    #         # meeting menu
    #         print("1. (Stop) Share screen")
    #         print("2. (Stop) Control other's screen")
    #         print("3. (Stop) Control my screen")
    #         print("4. (Stop) Share video")
    #         print("5. (Stop) Share audio")
    #         print("6. Leave a meeting")
    #         print("7. Show current meeting members")
    #         action = input("Action:")
    #         client.action(action)
