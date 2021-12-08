import socket
import threading
import cv2
import struct
import pickle
import zlib
import pyaudio

'''
    We provide a base class here.
    You can create new sub classes based on it.
'''

CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 2
RATE = 44100
RECORD_SECONDS = 0.5


class ClientSocket(object):
    """
        The main process of the ClientSocket is:
        Receive: receive data -> analyze the data -> take actions (send data or others)
        Send: construct data -> send data -> (optional) wait for reply (i.e., receive data)
    """

    def __init__(self, server):
        self.server = server
        # Create socket
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # Create a receive_server_data threading
        # self.receive_thread = threading.Thread(target=self.receive_server_data)

    def connect(self):
        # If you want to connect to the server right now
        while True:
            try:
                self.sock.connect(self.server)
                print("Connected")
                break
            except:
                print("Could not connect to the server" + str(self.server))

    def close_conn(self):
        self.sock.close()

    def receive_server_data(self):
        raw_data = self.sock.recv(2048).decode().split('\r\n\r\n')
        header = raw_data[0]
        data = raw_data[1]
        return header, data

    def analyze_receive_data(self, header, data):
        """
            Analyze the received data
            You can also combine this function within
            the "receive_server_data", so you can ignore this function
        """
        pass

    def send_data(self, header, data):
        """
            This function is used to send data to the server
            It can be a threading or a normal function depent
            on different purpose
        """
        pack = header + b'\r\n\r\n' + data
        self.sock.sendall(pack)

    def construct_sending_data(self, *args):
        """
            Construct the sending data
            @Returns
                header: The header of the msg
                data: The data of the msg
        """
        pass


def receive_data(sock):
    raw_data = sock.recv(2048).decode().split('\r\n\r\n')
    header = raw_data[0]
    data = raw_data[1]
    return header, data


def send_data(sock, header, data):
    pack = header + b'\r\n\r\n' + data
    sock.sendall(pack)


class VideoSock(object):
    def __init__(self, server):
        self.server = server
        self.room_id = None
        self.interval = 1
        self.fx = 1 / (self.interval + 1)
        if self.fx < 0.3:
            self.fx = 0.3
        self.cap = cv2.VideoCapture(0)
        self.share_video = threading.Thread(target=self.share_video)
        self.share_video.setDaemon(True)
        self.receive_video = threading.Thread(target=self.receive_video)
        self.receive_video.setDaemon(True)

    def __del__(self):
        self.cap.release()

    def share_video(self):
        print("VIDEO sender starts...")
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        while True:
            try:
                sock.connect(self.server)
                break
            except:
                print("Could not connect to the server" + str(self.server))
        send_data(sock, b'share', 'roomId {}'.format(str(self.room_id)).encode())
        header, data = receive_data(sock)
        if header == '200 OK':
            while self.cap.isOpened():
                ret, frame = self.cap.read()
                sframe = cv2.resize(frame, (0, 0), fx=self.fx, fy=self.fx)
                data = pickle.dumps(sframe)
                zdata = zlib.compress(data, zlib.Z_BEST_COMPRESSION)
                try:
                    sock.sendall(struct.pack("L", len(zdata)) + zdata)
                except:
                    break
                for i in range(self.interval):
                    self.cap.read()
        sock.close()

    def receive_video(self):
        print("VIDEO receiver starts...")
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        while True:
            try:
                sock.connect(self.server)
                break
            except:
                print("Could not connect to the server" + str(self.server))
        send_data(sock, b'receive', 'roomId {}'.format(str(self.room_id)).encode())
        header, data = receive_data(sock)
        if header == '200 OK':
            data = "".encode("utf-8")
            payload_size = struct.calcsize("L")
            cv2.namedWindow('Remote', cv2.WINDOW_NORMAL)
            while True:
                while len(data) < payload_size:
                    data += sock.recv(81920)
                packed_size = data[:payload_size]
                data = data[payload_size:]
                msg_size = struct.unpack("L", packed_size)[0]
                while len(data) < msg_size:
                    data += sock.recv(81920)
                zframe_data = data[:msg_size]
                data = data[msg_size:]
                frame_data = zlib.decompress(zframe_data)
                frame = pickle.loads(frame_data)
                cv2.imshow('Remote', frame)
                if cv2.waitKey(1) & 0xFF == 27:
                    break
        sock.close()


class AudioSock(object):
    def __init__(self, server):
        self.server = server
        self.room_id = None
        self.p = pyaudio.PyAudio()
        self.out_stream = None
        self.in_stream = None
        self.share_audio = threading.Thread(target=self.share_audio)
        self.share_audio.setDaemon(True)
        self.receive_audio = threading.Thread(target=self.receive_audio)
        self.receive_audio.setDaemon(True)

    def __del__(self):
        if self.out_stream is not None:
            self.out_stream.stop_stream()
            self.out_stream.close()
        if self.in_stream is not None:
            self.in_stream.stop_stream()
            self.in_stream.close()
        self.p.terminate()

    def share_audio(self):
        print("AUDIO sender starts...")
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        while True:
            try:
                sock.connect(self.server)
                break
            except:
                print("Could not connect to the server" + str(self.server))
        send_data(sock, b'share', 'roomId {}'.format(str(self.room_id)).encode())
        header, data = receive_data(sock)
        if header == '200 OK':
            self.in_stream = self.p.open(format=FORMAT,
                                          channels=CHANNELS,
                                          rate=RATE,
                                          input=True,
                                          frames_per_buffer=CHUNK)
            while self.in_stream.is_active():
                frames = []
                for i in range(0, int(RATE / CHUNK * RECORD_SECONDS)):
                    data = self.in_stream.read(CHUNK)
                    frames.append(data)
                senddata = pickle.dumps(frames)
                try:
                    sock.sendall(struct.pack("L", len(senddata)) + senddata)
                except:
                    break
        sock.close()

    def receive_audio(self):
        print("AUDIO receiver starts...")
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        while True:
            try:
                sock.connect(self.server)
                break
            except:
                print("Could not connect to the server" + str(self.server))
        send_data(sock, b'receive', 'roomId {}'.format(str(self.room_id)).encode())
        header, data = receive_data(sock)
        if header == '200 OK':
            data = "".encode("utf-8")
            payload_size = struct.calcsize("L")
            self.out_stream = self.p.open(format=FORMAT,
                                          channels=CHANNELS,
                                          rate=RATE,
                                          output=True,
                                          frames_per_buffer=CHUNK
                                          )
            while True:
                while len(data) < payload_size:
                    data += sock.recv(81920)
                packed_size = data[:payload_size]
                data = data[payload_size:]
                msg_size = struct.unpack("L", packed_size)[0]
                while len(data) < msg_size:
                    data += sock.recv(81920)
                frame_data = data[:msg_size]
                data = data[msg_size:]
                frames = pickle.loads(frame_data)
                for frame in frames:
                    self.out_stream.write(frame, CHUNK)
        sock.close()
