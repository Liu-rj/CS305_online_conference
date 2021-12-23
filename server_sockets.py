import struct
from typing import Union, Tuple

from CONSTANTS import *
import threading
import socket

shared_lock = threading.Lock()


def receive_data(sock):
    raw_data = sock.recv(2048).decode()
    if not raw_data:
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
        self.video_receiving = []
        self.video_buffer = []
        self.audio_receiving = []
        self.audio_buffer = []
        self.screen_sharing = []
        self.screen_receiving = []

    def __del__(self):
        for video in self.video_receiving:
            video[0].close()
        for audio in self.audio_receiving:
            audio[0].close()
        for screen in self.screen_sharing:
            screen[0].close()
        for screen in self.screen_receiving:
            screen[0].close()
        for client in self.clients:
            ServerSocket.clients[client].meeting = None

    def start_meeting(self):
        threading.Thread(target=self.video_forward, daemon=True).start()
        threading.Thread(target=self.audio_forward, daemon=True).start()
        threading.Thread(target=self.screen_forward, daemon=True).start()

    def add_client(self, client):
        self.clients.append(client)

    def video_receive(self, sock):
        data = b''
        payload_size = struct.calcsize("L")
        try:
            while True:
                while len(data) < payload_size:
                    data += sock.recv(81920)
                ip_size = struct.unpack("L", data[:payload_size])[0]
                while len(data[payload_size:]) < ip_size:
                    data += sock.recv(81920)
                while len(data[payload_size + ip_size:]) < payload_size:
                    data += sock.recv(81920)
                msg_size = struct.unpack("L", data[payload_size + ip_size:payload_size + ip_size + payload_size])[0]
                while len(data[payload_size + ip_size + payload_size:]) < msg_size:
                    data += sock.recv(81920)
                length = payload_size + ip_size + payload_size + msg_size
                pkt = data[:length]
                self.video_buffer.append(pkt)
                data = data[length:]
        except socket.error as e:
            print(e)
            # print('remove', sock)
            sock.close()

    def video_forward(self):
        while True:
            if not self.video_buffer:
                continue
            msg = self.video_buffer.pop(0)
            for other in self.video_receiving:
                try:
                    other[0].sendall(msg)
                except socket.error as e:
                    print(e)
                    other[0].close()
                    self.video_receiving.remove(other)

    def audio_receive(self, sock):
        data = b''
        payload_size = struct.calcsize("L")
        try:
            while True:
                while len(data) < payload_size:
                    data += sock.recv(81920)
                msg_size = struct.unpack("L", data[:payload_size])[0]
                while len(data[payload_size:]) < msg_size:
                    data += sock.recv(81920)
                length = payload_size + msg_size
                pkt = data[:length]
                self.audio_buffer.append(pkt)
                data = data[length:]
        except socket.error as e:
            print(e)
            # print('remove', sock)
            sock.close()

    def audio_forward(self):
        while True:
            if not self.audio_buffer:
                continue
            msg = self.audio_buffer.pop(0)
            for other in self.audio_receiving:
                try:
                    other[0].sendall(msg)
                except socket.error as e:
                    print(e)
                    other[0].close()
                    self.audio_receiving.remove(other)

    def screen_forward(self):
        bufsize = 81920
        while True:
            for client in self.screen_sharing:
                try:
                    data1 = client[0].recv(5)
                    imtype, le = struct.unpack(">BI", data1)
                    if imtype == 2:
                        print("someone stop screen sharing!")
                        self.screen_sharing.remove(client)
                        for other in self.screen_receiving:
                            # if other[1][0] == client[1][0]:
                            #     continue
                            other[0].sendall(data1)
                    else:
                        data2 = b''
                        while le > bufsize:
                            t = client[0].recv(bufsize)
                            data2 += t
                            le -= len(t)
                        while le > 0:
                            t = client[0].recv(le)
                            data2 += t
                            le -= len(t)
                        for other in self.screen_receiving:
                            # if other[1][0] == client[1][0]:
                            #     continue
                            other[0].sendall(data1)
                            other[0].sendall(data2)
                except:
                    continue

    def broadcast(self):
        header = b'clients'
        data = b''
        for client in self.clients:
            data += f'ip {client[1][0]}\r\n'.encode()
        data = data.strip(b'\r\n')
        msg = header + b'\r\n\r\n' + data
        for client in self.clients:
            try:
                client[0].send(msg)
            except socket.error as e:
                client[0].close()
                self.clients.remove(client)


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
        if self.meeting:
            self.meeting.clients.remove(self.client)
            if not self.meeting.clients:
                del ServerSocket.rooms[self.meeting.room_id]
            self.meeting = None
        print(self.client[1], 'quit room, room info:', ServerSocket.rooms)

    def run(self):
        # Start listen client action
        while True:
            try:
                header, data, alive = receive_data(self.sock)
                if not alive:
                    print('end of client', self.client[1])
                    return
            except:
                continue
            if header == 'join room':
                room_id = int(data.split(' ')[1])
                if room_id in self.rooms.keys():
                    self.meeting = ServerSocket.rooms[room_id]
                    with shared_lock:
                        self.meeting.add_client(self.client)
                        self.sock.send('200 OK\r\n\r\nroomId {}'.format(str(room_id)).encode())
                        self.meeting.broadcast()
                else:  # TODO: if join a non-existing room, what should we do?
                    pass
            elif header == 'create room':
                room_id = ServerSocket.room_index
                self.meeting = Meeting(self.client, room_id)
                self.meeting.start_meeting()
                with shared_lock:
                    ServerSocket.room_index += 1
                    ServerSocket.rooms[room_id] = self.meeting
                    self.sock.send('200 OK\r\n\r\nroomId {}'.format(str(room_id)).encode())
                    self.meeting.broadcast()
            elif header == 'quit room':
                self.quit_meeting()
