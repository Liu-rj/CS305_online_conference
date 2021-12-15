from typing import Union, List

from CONSTANTS import *
import threading
import socket

VIDEO_CHUNK_SIZE = 32768
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
    def __init__(self, service, room_id: int):
        self.room_id = room_id
        # initiate the server socket with a client queue
        self.services = [service]
        self.audio_sharing = []
        self.audio_receiving = []
        self.screen_sharing = []
        self.screen_receiving = []
        self.video_buffer: List[bytes] = []
        # udp socket binding
        self.v_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.v_sock.bind(('', XXVIDEOPORT + self.room_id))

    def __del__(self):
        for audio in self.audio_sharing:
            audio[0].close()
        for audio in self.audio_receiving:
            audio[0].close()
        for screen in self.screen_sharing:
            screen[0].close()
        for screen in self.screen_receiving:
            screen[0].close()

    def start_meeting(self):
        threading.Thread(target=self.video_receiving, daemon=True).start()
        threading.Thread(target=self.video_forwarding, daemon=True).start()
        threading.Thread(target=self.audio_forward, daemon=True).start()
        threading.Thread(target=self.screen_forward, daemon=True).start()

    def add_client(self, service):
        self.services.append(service)

    def video_receiving(self):
        while True:
            try:
                self.video_buffer.append(self.v_sock.recv(VIDEO_CHUNK_SIZE))
            except socket.error as e:
                print(e)
                continue

    def video_forwarding(self):
        while True:
            if self.video_buffer:
                pkt = self.video_buffer.pop(0)
                for service in self.services:
                    self.v_sock.sendto(pkt, (service.client_ip, service.video_port))

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
    room_index = 0
    alive = True

    def __init__(self, client_conn: socket.socket, client_address: tuple[str, int]):
        super().__init__()
        self.client_ip = client_address[0]
        self.sock: socket.socket = client_conn
        self.sock.setblocking(False)
        self.meeting: Union[None, Meeting] = None
        self.video_port: Union[None, int] = None
        self.audio_port: Union[None, int] = None
        self.screen_port: Union[None, int] = None
        self.room_id: Union[None, int] = None

    def __del__(self):
        self.sock.close()

    def parse_data(self, data):
        for seg in data.split('\r\n'):
            signal, content = seg.split(' ')
            if signal == 'video':
                self.video_port = int(content)
            elif signal == 'audio':
                self.audio_port = int(content)
            elif signal == 'screen':
                self.screen_port = int(content)
            elif signal == 'roomId':
                self.room_id = int(content)

    def run(self):
        # Start listen client action
        while True:
            try:
                header, data, alive = receive_data(self.sock)
                if not alive:
                    if self.meeting:
                        self.meeting.services.remove(self)
                    self.sock.close()
                    return
            except:
                continue
            if header == 'join room':
                self.parse_data(data)
                if self.room_id in self.rooms.keys():
                    self.meeting = ServerSocket.rooms[self.room_id]
                    with shared_lock:
                        self.meeting.add_client(self)
                    self.sock.send('200 OK\r\n\r\nroomId {}'.format(str(self.room_id)).encode())
                else:  # TODO: if join a non-existing room, what should we do?
                    pass
            elif header == 'create room':
                self.parse_data(data)
                self.room_id = ServerSocket.room_index
                ServerSocket.room_index += 1
                self.meeting = Meeting(self, self.room_id)
                with shared_lock:
                    ServerSocket.rooms[self.room_id] = self.meeting
                self.meeting.start_meeting()
                self.sock.send('200 OK\r\n\r\nroomId {}'.format(str(self.room_id)).encode())
            elif header == 'quit room':
                self.meeting.services.remove(self)
                self.room_id = None
