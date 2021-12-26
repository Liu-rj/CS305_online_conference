import struct
from typing import Union, Tuple, List

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
    def __init__(self, service, room_id):
        # initiate the server socket with a client queue
        self.services = [service]
        self.room_id = room_id
        self.video_receiving = []
        self.video_buffer = []
        self.audio_receiving = []
        self.audio_buffer: List[Tuple[str, bytes]] = []
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
        for service in self.services:
            service.meeting = None

    def start_meeting(self):
        threading.Thread(target=self.video_forward, daemon=True).start()
        threading.Thread(target=self.audio_forward, daemon=True).start()
        threading.Thread(target=self.screen_forward, daemon=True).start()

    def add_service(self, service):
        self.services.append(service)

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

    def audio_receive(self, sock, ip):
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
                self.audio_buffer.append((ip, pkt))
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
            ip, data = msg[0], msg[1]
            for other in self.audio_receiving:
                if other[1][0] == ip:
                    continue
                try:
                    other[0].sendall(data)
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
                            try:
                                if other[1][0] == client[1][0]:
                                    continue
                                other[0].sendall(data1)
                            except socket.error as e:
                                print(e)
                                other[0].close()
                                self.screen_receiving.remove(other)
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
                            try:
                                if other[1][0] == client[1][0]:
                                    continue
                                other[0].sendall(data1)
                                other[0].sendall(data2)
                            except socket.error as e:
                                print(e)
                                other[0].close()
                                self.screen_receiving.remove(other)
                except socket.error as e:
                    print(e)
                    client[0].close()
                    self.screen_sharing.remove(client)

    def broadcast(self):
        header = b'clients'
        data = b''
        for service in self.services:
            data += f'ip {service.client[1][0]}\r\n'.encode()
        data = data.strip(b'\r\n')
        msg = header + b'\r\n\r\n' + data
        for service in self.services:
            try:
                service.client[0].send(msg)
            except socket.error as e:
                service.client[0].close()
                self.services.remove(service)

    def set_privilege(self, msg: bytes, ip: str):
        for service in self.services:
            if service.client[1][0] == ip:
                service.client[0].send(msg)

    def close(self, client):
        header = b'close'
        data = b' '
        msg = header + b'\r\n\r\n' + data
        for service in self.services:
            try:
                service.meeting = None
                if service.client is not client:
                    service.client[0].send(msg)
            except socket.error as e:
                service.client[0].close()
                self.services.remove(service)
        del ServerSocket.rooms[self.room_id]


class ServerSocket(threading.Thread):
    rooms = {}
    # clients = {}
    room_index = 0
    alive = True

    def __init__(self, client):
        super().__init__()
        self.client: Tuple[socket.socket, Tuple[str, int]] = client
        self.sock: socket.socket = client[0]
        # self.sock.setblocking(False)
        self.meeting: Union[Meeting, None] = None

    def __del__(self):
        print('enter delete self')
        self.quit_meeting()
        self.sock.close()

    def quit_meeting(self):
        if self.meeting:
            self.meeting.services.remove(self)
            self.meeting.broadcast()
            if not self.meeting.services:
                del ServerSocket.rooms[self.meeting.room_id]
            self.meeting = None
        # print(self.client[1], 'quit room, room info:', ServerSocket.rooms)

    def close_meeting(self):
        if self.meeting:
            self.meeting.close(self.client)
            self.meeting = None

    def run(self):
        # Start listen client action
        while True:
            try:
                header, data, alive = receive_data(self.sock)
                if not alive:
                    print('end of client', self.client[1])
                    self.quit_meeting()
                    self.sock.close()
                    return
            except:
                print('end of client', self.client[1])
                self.quit_meeting()
                self.sock.close()
                return
            # print(f'{header}, {data}')
            if header == 'join room':
                room_id = int(data.split(' ')[1])
                if room_id in self.rooms.keys():
                    self.meeting = ServerSocket.rooms[room_id]
                    with shared_lock:
                        self.meeting.add_service(self)
                        self.sock.send('200 OK\r\n\r\nroomId {}'.format(str(room_id)).encode())
                else:  # TODO: if join a non-existing room, what should we do?
                    self.sock.send('403 NotFound\r\n\r\n '.encode())
            elif header == 'create room':
                room_id = ServerSocket.room_index
                self.meeting = Meeting(self, room_id)
                self.meeting.start_meeting()
                with shared_lock:
                    ServerSocket.room_index += 1
                    ServerSocket.rooms[room_id] = self.meeting
                    self.sock.send('200 OK\r\n\r\nroomId {}'.format(str(room_id)).encode())
            elif header == 'quit room':
                self.quit_meeting()
                self.sock.send('quit\r\n\r\n '.encode())
            elif header == 'close room':
                self.close_meeting()
                self.sock.send('quit\r\n\r\n '.encode())
            elif header == 'set':
                set_type, ip = data.split(':')
                msg = (header + '\r\n\r\n' + set_type).encode()
                self.meeting.set_privilege(msg, ip)
            elif header == '200 OK':
                self.meeting.broadcast()
