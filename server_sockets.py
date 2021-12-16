from typing import Union, Tuple

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
    def __init__(self, client, room_id):
        # initiate the server socket with a client queue
        self.clients = [client]
        self.room_id = room_id
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

    def broadcast(self):
        header = b'clients'
        data = b''
        for client in self.clients:
            data += f'ip {client[1][0]}\r\n'
        data.strip(b'\r\n')
        msg = header + b'\r\n\r\n' + data
        for client in self.clients:
            client[0].send(msg)


class ServerSocket(threading.Thread):
    rooms = {}
    clients = {}
    room_index = 0
    alive = True

    def __init__(self, client):
        super().__init__()
        self.client: Tuple[socket.socket, Tuple[str, int]] = client
        self.sock: socket.socket = client[0]
        self.sock.setblocking(False)
        self.meeting: Union[Meeting, None] = None

    def __del__(self):
        self.quit_meeting()
        self.sock.close()

    def quit_meeting(self):
        if not self.meeting:
            self.meeting.clients.remove(self.client)
            if not self.meeting.clients:
                del ServerSocket.rooms[self.meeting.room_id]
            self.meeting = None

    def run(self):
        # Start listen client action
        while True:
            try:
                header, data, alive = receive_data(self.sock)
                if not alive:
                    return
            except:
                continue
            if header == 'join room':
                room_id = int(data.split(' ')[1])
                if room_id in self.rooms.keys():
                    self.meeting = ServerSocket.rooms[room_id]
                    with shared_lock:
                        self.meeting.add_client(self.client)
                        self.meeting.broadcast()
                    self.sock.send('200 OK\r\n\r\nroomId {}'.format(str(room_id)).encode())
                else:  # TODO: if join a non-existing room, what should we do?
                    pass
            elif header == 'create room':
                room_id = ServerSocket.room_index
                self.meeting = Meeting(self.client, room_id)
                with shared_lock:
                    ServerSocket.rooms[room_id] = self.meeting
                self.meeting.start_meeting()
                self.sock.send('200 OK\r\n\r\nroomId {}'.format(str(room_id)).encode())
                ServerSocket.room_index += 1
            elif header == 'quit room':
                self.quit_meeting()
