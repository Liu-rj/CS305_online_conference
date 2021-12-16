from CONSTANTS import *
import threading
import socket

shared_lock = threading.Lock()


def receive_data(sock):
    raw_data = sock.recv(2048).decode()
    if not raw_data:
        sock.close()
        return '', '', False
    raw_data = raw_data.split('\r\n\r\n')
    header = raw_data[0]
    data = raw_data[1]
    return header, data, True


class Meeting(object):
    def __init__(self, client):
        # initiate the server socket with a client queue
        self.clients = [client]
        self.video_sharing = []
        self.video_receiving = []
        self.audio_sharing = []
        self.audio_receiving = []
        self.screen_sharing = []
        self.screen_receiving = []

    def __del__(self):
        for video in self.video_sharing:
            video[0].close()
        for video in self.video_receiving:
            video[0].close()
        for audio in self.audio_sharing:
            audio[0].close()
        for audio in self.audio_receiving:
            audio[0].close()
        for screen in self.screen_sharing:
            screen[0].close()
        for screen in self.screen_receiving:
            screen[0].close()
        for client in self.clients:
            ServerSocket.clients[client].meeting = None

    def start_meeting(self):
        video = threading.Thread(target=self.video_forward)
        video.setDaemon(True)
        video.start()
        audio = threading.Thread(target=self.audio_forward)
        audio.setDaemon(True)
        audio.start()
        screen = threading.Thread(target=self.screen_forward)
        screen.setDaemon(True)
        screen.start()

    def add_client(self, client):
        self.clients.append(client)

    def video_forward(self):
        while True:
            for client in self.video_sharing:
                try:
                    data = client[0].recv(81920)
                    if data == '':
                        self.video_sharing.remove(client)
                        continue
                    for other in self.video_receiving:
                        other[0].sendall(data)
                except:
                    continue

    def audio_forward(self):
        while True:
            for client in self.audio_sharing:
                try:
                    data = client[0].recv(81920)
                    if data == '':
                        self.audio_sharing.remove(client)
                        continue
                    for other in self.audio_receiving:
                        if other[1][0] == client[1][0]:
                            continue
                        other[0].sendall(data)
                except:
                    continue

    def screen_forward(self):
        while True:
            for client in self.screen_sharing:
                try:
                    data = client[0].recv(81920)
                    if data == '':
                        self.screen_sharing.remove(client)
                        continue
                    for other in self.screen_receiving:
                        if other[1][0] == client[1][0]:
                            continue
                        other[0].sendall(data)
                except:
                    continue


class ServerSocket(threading.Thread):
    rooms = {}
    clients = {}
    room_index = 0
    alive = True

    def __init__(self, client):
        super().__init__()
        self.client = client
        self.sock = client[0]
        self.sock.setblocking(False)
        self.meeting = None

    def __del__(self):
        self.sock.close()

    def run(self):
        # Start listen client action
        while True:
            try:
                header, data, alive = receive_data(self.sock)
                if not alive:
                    return
            except:
                continue
            # if header == 'login':
            #     data = data.split('\r\n')
            #     name = data[0].split(' ')[1]
            #     pwd = data[1].split(' ')[1]
            #     if name in USERS.keys() and USERS[name]['pwd'] == pwd:
            #         self.sock.send(b'200 OK\r\n\r\n ')
            #     else:  # TODO: login failed, and then?
            #         self.sock.send(b'400 Error\r\n\r\nUser Name or Password Not Match!')
            #         self.sock.close()
            #         return
            #     print('new client login: ', self.client[1])
            #     ServerSocket.clients[self.client] = self
            # # the second action is to join room or create room
            # el
            if header == 'join room':
                room_id = int(data.split(' ')[1])
                if room_id in self.rooms.keys():
                    self.meeting = ServerSocket.rooms[room_id]
                    with shared_lock:
                        self.meeting.add_client(self.client)
                    self.sock.send('200 OK\r\n\r\nroomId {}'.format(str(room_id)).encode())
                else:  # TODO: if join a non-existing room, what should we do?
                    pass
            elif header == 'create room':
                self.meeting = Meeting(self.client)
                with shared_lock:
                    ServerSocket.rooms[ServerSocket.room_index] = self.meeting
                self.meeting.start_meeting()
                self.sock.send('200 OK\r\n\r\nroomId {}'.format(str(ServerSocket.room_index)).encode())
                ServerSocket.room_index += 1
            else:  # TODO: if nor join room or create room, what should we do?
                pass
