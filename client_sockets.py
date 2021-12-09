import socket
import threading
import tkinter

import cv2
import struct
import pickle
import zlib

import numpy as np
import pyaudio
from PIL import ImageGrab, ImageTk
from PIL.Image import Image

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

    # def analyze_receive_data(self, header, data):
    #     """
    #         Analyze the received data
    #         You can also combine this function within
    #         the "receive_server_data", so you can ignore this function
    #     """
    #     pass

    def send_data(self, header, data):
        """
            This function is used to send data to the server
            It can be a threading or a normal function depent
            on different purpose
        """
        pack = header + b'\r\n\r\n' + data
        self.sock.sendall(pack)

    # def construct_sending_data(self, *args):
    #     """
    #         Construct the sending data
    #         @Returns
    #             header: The header of the msg
    #             data: The data of the msg
    #     """
    #     pass


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

class ScreenSock(object):
    def __init__(self, server):
        self.server = server
        self.room_id = None
        self.img = None
        self.imbyt = None
        self.showcan = None
        self.bufsize = 10240# socket缓冲区大小
        self.IMQUALITY = 50# 压缩比 1-100 数值越小，压缩比越高，图片质量损失越严重
        self.share_screen = threading.Thread(target=self.share_screen)
        self.share_screen.setDaemon(True)
        self.receive_screen = threading.Thread(target=self.receive_screen)
        self.receive_screen.setDaemon(True)

    def __del__(self):
        if self.showcan is not None:
            self.showcan.destroy()
        pass

    def share_screen(self):
        print("SCREEN sender starts...")
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        while True:
            try:
                sock.connect(self.server)
                break
            except:
                print("Could not connect to the server" + str(self.server))
        if self.imbyt is None:
            imorg = np.asarray(ImageGrab.grab())
            _, self.imbyt = cv2.imencode(".jpg", imorg, [cv2.IMWRITE_JPEG_QUALITY, self.IMQUALITY])
            imnp = np.asarray(self.imbyt, np.uint8)
            self.img = cv2.imdecode(imnp, cv2.IMREAD_COLOR)
        lenb = struct.pack(">BI", 1, len(self.imbyt))
        sock.sendall(lenb)
        sock.sendall(self.imbyt)
        while True:
            cv2.waitKey(100)
            gb = ImageGrab.grab()
            imgnpn = np.asarray(gb)
            _, timbyt = cv2.imencode(".jpg", imgnpn, [cv2.IMWRITE_JPEG_QUALITY, self.IMQUALITY])
            self.imnp = np.asarray(timbyt, np.uint8)
            imgnew = cv2.imdecode(self.imnp, cv2.IMREAD_COLOR)
            # 计算图像差值
            imgs = imgnew - self.img
            if (imgs != 0).any():
                # 画质改变
                pass
            else:
                continue
            self.imbyt = timbyt
            self.img = imgnew
            # 无损压缩
            _, imb = cv2.imencode(".png", imgs)
            l1 = len(self.imbyt)  # 原图像大小
            l2 = len(imb)  # 差异图像大小
            if l1 > l2:
                # 传差异化图像
                lenb = struct.pack(">BI", 0, l2)
                sock.sendall(lenb)
                sock.sendall(imb)
            else:
                # 传原编码图像
                lenb = struct.pack(">BI", 1, l1)
                sock.sendall(lenb)
                sock.sendall(self.imbyt)
        sock.close()

    def receive_screen(self):
        print("SCREEN receiver starts...")
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        while True:
            try:
                sock.connect(self.server)
                break
            except:
                print("Could not connect to the server" + str(self.server))
        send_data(sock, b'receive', 'roomId {}'.format(str(self.room_id)).encode())
        lenb = sock.recv(5)
        imtype, le = struct.unpack(">BI", lenb)
        imb = b''
        while le > self.bufsize:
            t = sock.recv(self.bufsize)
            imb += t
            le -= len(t)
        while le > 0:
            t = sock.recv(le)
            imb += t
            le -= len(t)
        data = np.frombuffer(imb, dtype=np.uint8)
        img = cv2.imdecode(data, cv2.IMREAD_COLOR)
        h, w, _ = img.shape
        fixh, fixw = h, w
        imsh = cv2.cvtColor(img, cv2.COLOR_BGR2RGBA)
        imi = Image.fromarray(imsh)
        imgTK = ImageTk.PhotoImage(image=imi)
        if self.showcan is None:
            self.showcan = tkinter.Tk()
        cv = tkinter.Canvas(self.showcan, width=w, height=h, bg="white")
        cv.focus_set()
        cv.pack()
        cv.create_image(0, 0, anchor=tkinter.NW, image=imgTK)
        while True:
            try:
                lenb = sock.recv(5)
                imtype, le = struct.unpack(">BI", lenb)
                imb = b''
                while le > self.bufsize:
                    t = sock.recv(self.bufsize)
                    imb += t
                    le -= len(t)
                while le > 0:
                    t = sock.recv(le)
                    imb += t
                    le -= len(t)
                data = np.frombuffer(imb, dtype=np.uint8)
                ims = cv2.imdecode(data, cv2.IMREAD_COLOR)
                if imtype == 1:
                    # 全传
                    img = ims
                else:
                    # 差异传
                    img = img + ims
                imt = cv2.resize(img, (w, h))
                imsh = cv2.cvtColor(imt, cv2.COLOR_RGB2RGBA)
                imi = Image.fromarray(imsh)
                imgTK.paste(imi)
            except:
                self.showcan = None
                break
        sock.close()
