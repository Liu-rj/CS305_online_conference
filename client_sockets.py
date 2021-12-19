import socket
import threading
import tkinter
from typing import Tuple

import cv2
import struct
import pickle
import zlib
import numpy as np
import pyaudio
# import qtpy
from PIL import ImageGrab, ImageTk, Image, ImageQt
import mouse
import keyboard
from PySide2.QtWidgets import *
from PySide2.QtCore import Qt, QSize
from PySide2.QtGui import *

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
        self.connect()
        self.ip = self.sock.getsockname()[0]
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

    def send_data(self, header, data):
        """
            This function is used to send data to the server
            It can be a threading or a normal function depent
            on different purpose
        """
        pack = header + b'\r\n\r\n' + data
        self.sock.sendall(pack)


def receive_data(sock):
    raw_data = sock.recv(2048).decode().split('\r\n\r\n')
    header = raw_data[0]
    data = raw_data[1]
    return header, data


def parse_data(raw_data):
    raw_data = raw_data.decode().split('\r\n\r\n')
    header = raw_data[0]
    data = raw_data[1]
    return header, data


def send_data(sock, header, data):
    pack = header + b'\r\n\r\n' + data
    sock.sendall(pack)


class VideoSock(object):
    def __init__(self, server: Tuple[str, int], stats):
        self.server = server
        self.stats = stats
        self.room_id = None
        self.interval = 1
        self.fx = 1 / (self.interval + 1)
        if self.fx < 0.3:
            self.fx = 0.3
        self.cap = cv2.VideoCapture(0)
        self.sharing = False
        self.receiving = False

    def __del__(self):
        self.sharing = False
        self.receiving = False
        self.cap.release()

    def start_sharing(self):
        thread = threading.Thread(target=self.share_video)
        thread.setDaemon(True)
        thread.start()

    def start_receiving(self):
        thread = threading.Thread(target=self.receive_video)
        thread.setDaemon(True)
        thread.start()

    def end_receiving(self):
        self.receiving = False
        self.sharing = False

    def share_video(self):
        self.sharing = True
        print("VIDEO sender starts...")
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        while True:
            try:
                sock.connect(self.server)
                break
            except:
                print("Could not connect to the server" + str(self.server))
        ip_b = sock.getsockname()[0].encode()
        send_data(sock, b'share', 'roomId {}'.format(str(self.room_id)).encode())
        header, data = receive_data(sock)
        if header == '200 OK':
            while self.sharing and self.cap.isOpened():
                ret, frame = self.cap.read()
                sframe = cv2.resize(frame, (0, 0), fx=self.fx, fy=self.fx)
                data = pickle.dumps(sframe)
                zdata = zlib.compress(data, zlib.Z_BEST_COMPRESSION)
                try:
                    sock.sendall(struct.pack("L", len(ip_b)) + ip_b + struct.pack("L", len(zdata)) + zdata)
                except:
                    break
                for i in range(self.interval):
                    self.cap.read()
        sock.sendall(struct.pack("L", len(ip_b)) + ip_b + struct.pack("L", 0))
        sock.close()

    def receive_video(self):
        self.receiving = True
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
            while self.receiving:
                while len(data) < payload_size:
                    data += sock.recv(81920)
                ip_size = struct.unpack("L", data[:payload_size])[0]
                data = data[payload_size:]
                while len(data) < ip_size:
                    data += sock.recv(81920)
                ip = data[:ip_size].decode()
                data = data[ip_size:]
                while len(data) < payload_size:
                    data += sock.recv(81920)
                msg_size = struct.unpack("L", data[:payload_size])[0]
                data = data[payload_size:]
                if msg_size == 0:
                    self.stats.update_image(ip, None)
                    # cv2.destroyWindow(ip)
                    continue
                while len(data) < msg_size:
                    data += sock.recv(81920)
                zframe_data = data[:msg_size]
                data = data[msg_size:]
                frame_data = zlib.decompress(zframe_data)
                frame = pickle.loads(frame_data)
                # frame = cv2.cvtColor(frame, cv2.COLOR_RGB2RGBA)
                self.stats.update_image(ip, frame)
                # cv2.namedWindow(ip, cv2.WINDOW_NORMAL)
                # cv2.imshow(ip, frame)
                # if cv2.waitKey(1) & 0xFF == 27:
                #     break
        sock.close()


class AudioSock(object):
    def __init__(self, server):
        self.server = server
        self.room_id = None
        self.p = pyaudio.PyAudio()
        self.out_stream = None
        self.in_stream = None
        self.sharing = False
        self.receiving = False

    def __del__(self):
        if self.out_stream is not None:
            self.out_stream.stop_stream()
            self.out_stream.close()
        if self.in_stream is not None:
            self.in_stream.stop_stream()
            self.in_stream.close()
        self.p.terminate()

    def start_sharing(self):
        thread = threading.Thread(target=self.share_audio)
        thread.setDaemon(True)
        thread.start()

    def start_receiving(self):
        thread = threading.Thread(target=self.receive_audio)
        thread.setDaemon(True)
        thread.start()

    def end_receiving(self):
        self.receiving = False
        self.sharing = False

    def share_audio(self):
        self.sharing = True
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
            while self.sharing and self.in_stream.is_active():
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
        self.receiving = True
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
            while self.receiving:
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
        # self.root = root
        self.server = server
        self.room_id = None
        self.img = None
        self.imbyt = None
        self.bufsize = 10240  # socket缓冲区大小
        self.IMQUALITY = 50  # 压缩比 1-100 数值越小，压缩比越高，图片质量损失越严重
        self.sharing = False
        self.receiving = False

    def __del__(self):
        self.sharing = False
        self.receiving = False

    def start_sharing(self):
        thread = threading.Thread(target=self.share_screen)
        thread.setDaemon(True)
        thread.start()

    def start_receiving(self):
        thread = threading.Thread(target=self.receive_screen)
        thread.setDaemon(True)
        thread.start()

    def end_receiving(self):
        self.receiving = False
        self.sharing = False

    def share_screen(self):
        self.sharing = True
        print("SCREEN sender starts...")
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        while True:
            try:
                sock.connect(self.server)
                break
            except Exception as e:
                print(e)
                exit()
                print("Could not connect to the server" + str(self.server))
        send_data(sock, b'share', 'roomId {}'.format(str(self.room_id)).encode())
        header, data = receive_data(sock)
        if header == '200 OK':
            if self.imbyt is None:
                imorg = np.asarray(ImageGrab.grab())
                _, self.imbyt = cv2.imencode(".jpg", imorg, [cv2.IMWRITE_JPEG_QUALITY, self.IMQUALITY])
                imnp = np.asarray(self.imbyt, np.uint8)
                self.img = cv2.imdecode(imnp, cv2.IMREAD_COLOR)
            lenb = struct.pack(">BI", 1, len(self.imbyt))
            sock.sendall(lenb)
            sock.sendall(self.imbyt)
            while self.sharing:
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
        self.receiving = True
        print("SCREEN receiver starts...")
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
            self.img = cv2.imdecode(data, cv2.IMREAD_COLOR)
            imsh = cv2.cvtColor(self.img, cv2.COLOR_BGR2RGB)
            cv2.namedWindow('Screen', cv2.WINDOW_NORMAL)
            cv2.imshow('Screen', imsh)
            while self.receiving:
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
                        self.img = ims
                    else:
                        # 差异传
                        self.img = self.img + ims
                    imsh = cv2.cvtColor(self.img, cv2.COLOR_BGR2RGB)
                    cv2.imshow('Screen', imsh)
                except:
                    break
        sock.close()


class beCtrlSock(object):

    def __init__(self,stats,addr):
        self.img = None
        self.imbyt = None
        self.stats = stats
        self.IMQUALITY = 50  # 压缩比 1-100 数值越小，压缩比越高，图片质量损失越严重
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.bind(addr)
        self.conn = None
        self.official_virtual_keys = {
            0x08: 'backspace',
            0x09: 'tab',
            0x0c: 'clear',
            0x0d: 'enter',
            0x10: 'shift',
            0x11: 'ctrl',
            0x12: 'alt',
            0x13: 'pause',
            0x14: 'caps lock',
            0x15: 'ime kana mode',
            0x15: 'ime hanguel mode',
            0x15: 'ime hangul mode',
            0x17: 'ime junja mode',
            0x18: 'ime final mode',
            0x19: 'ime hanja mode',
            0x19: 'ime kanji mode',
            0x1b: 'esc',
            0x1c: 'ime convert',
            0x1d: 'ime nonconvert',
            0x1e: 'ime accept',
            0x1f: 'ime mode change request',
            0x20: 'spacebar',
            0x21: 'page up',
            0x22: 'page down',
            0x23: 'end',
            0x24: 'home',
            0x25: 'left',
            0x26: 'up',
            0x27: 'right',
            0x28: 'down',
            0x29: 'select',
            0x2a: 'print',
            0x2b: 'execute',
            0x2c: 'print screen',
            0x2d: 'insert',
            0x2e: 'delete',
            0x2f: 'help',
            0x30: '0',
            0x31: '1',
            0x32: '2',
            0x33: '3',
            0x34: '4',
            0x35: '5',
            0x36: '6',
            0x37: '7',
            0x38: '8',
            0x39: '9',
            0x41: 'a',
            0x42: 'b',
            0x43: 'c',
            0x44: 'd',
            0x45: 'e',
            0x46: 'f',
            0x47: 'g',
            0x48: 'h',
            0x49: 'i',
            0x4a: 'j',
            0x4b: 'k',
            0x4c: 'l',
            0x4d: 'm',
            0x4e: 'n',
            0x4f: 'o',
            0x50: 'p',
            0x51: 'q',
            0x52: 'r',
            0x53: 's',
            0x54: 't',
            0x55: 'u',
            0x56: 'v',
            0x57: 'w',
            0x58: 'x',
            0x59: 'y',
            0x5a: 'z',
            0x5b: 'left windows',
            0x5c: 'right windows',
            0x5d: 'applications',
            0x5f: 'sleep',
            0x60: '0',
            0x61: '1',
            0x62: '2',
            0x63: '3',
            0x64: '4',
            0x65: '5',
            0x66: '6',
            0x67: '7',
            0x68: '8',
            0x69: '9',
            0x6a: '*',
            0x6b: '=',
            0x6c: 'separator',
            0x6d: '-',
            0x6e: 'decimal',
            0x6f: '/',
            0x70: 'f1',
            0x71: 'f2',
            0x72: 'f3',
            0x73: 'f4',
            0x74: 'f5',
            0x75: 'f6',
            0x76: 'f7',
            0x77: 'f8',
            0x78: 'f9',
            0x79: 'f10',
            0x7a: 'f11',
            0x7b: 'f12',
            0x7c: 'f13',
            0x7d: 'f14',
            0x7e: 'f15',
            0x7f: 'f16',
            0x80: 'f17',
            0x81: 'f18',
            0x82: 'f19',
            0x83: 'f20',
            0x84: 'f21',
            0x85: 'f22',
            0x86: 'f23',
            0x87: 'f24',
            0x90: 'num lock',
            0x91: 'scroll lock',
            0xa0: 'left shift',
            0xa1: 'right shift',
            0xa2: 'left ctrl',
            0xa3: 'right ctrl',
            0xa4: 'left menu',
            0xa5: 'right menu',
            0xa6: 'browser back',
            0xa7: 'browser forward',
            0xa8: 'browser refresh',
            0xa9: 'browser stop',
            0xaa: 'browser search key',
            0xab: 'browser favorites',
            0xac: 'browser start and home',
            0xad: 'volume mute',
            0xae: 'volume down',
            0xaf: 'volume up',
            0xb0: 'next track',
            0xb1: 'previous track',
            0xb2: 'stop media',
            0xb3: 'play/pause media',
            0xb4: 'start mail',
            0xb5: 'select media',
            0xb6: 'start application 1',
            0xb7: 'start application 2',
            0xbb: '+',
            0xbc: ',',
            0xbd: '-',
            0xbe: '.',
            0xe5: 'ime process',
            0xf6: 'attn',
            0xf7: 'crsel',
            0xf8: 'exsel',
            0xf9: 'erase eof',
            0xfa: 'play',
            0xfb: 'zoom',
            0xfc: 'reserved ',
            0xfd: 'pa1',
            0xfe: 'clear',
            0xba: ';',
            0xde: '\'',
            0xdb: '[',
            0xdd: ']',
            0xbf: '/',
            0xc0: '`',
            0xdc: '\\',
        }


    def __del__(self):
        self.sock.close()

    def run(self):
        thread = threading.Thread(target=self.wait)
        thread.setDaemon(True)
        thread.start()

    def wait(self):
        print("beCtrl open")
        self.sock.listen(2)
        while True:
            self.conn, addr = self.sock.accept()
            # self.stats.handle_control_msg(addr)
            self.handle_confirm()
            print("accept")

    def handle_confirm(self):
        send_data(self.conn,b'accept',(str(self.conn.getsockname()[0])).encode())
        threading.Thread(target=self.handle, args=(self.conn,)).start()
        threading.Thread(target=self.control, args=(self.conn,)).start()
        #TODO: Bug may exist

    def handle_cancel(self):
        send_data(self.conn,b'refuse',("").encode())
        self.conn.close()

    # 读取控制命令，并在本机还原操作
    def control(self, conn):
        def Op(key, op, ox, oy):
            # print(key, op, ox, oy)
            if key == 1:
                if op == 100:
                    # 左键按下
                    mouse.move(ox, oy)
                    mouse.press(button=mouse.LEFT)
                elif op == 117:
                    # 左键弹起
                    x, y = mouse.get_position()
                    if ox != x or oy != y:
                        if not mouse.is_pressed():
                            mouse.press(button=mouse.LEFT)
                        mouse.move(ox, oy)
                    mouse.release(button=mouse.LEFT)
            elif key == 2:
                # 滚轮事件
                if op == 0:
                    # 向上
                    mouse.move(ox, oy)
                    mouse.wheel(delta=-1)
                else:
                    # 向下
                    mouse.move(ox, oy)
                    mouse.wheel(delta=1)
            elif key == 3:
                # 鼠标右键
                if op == 100:
                    # 右键按下
                    mouse.move(ox, oy)
                    mouse.press(button=mouse.RIGHT)
                elif op == 117:
                    # 右键弹起
                    mouse.move(ox, oy)
                    mouse.release(button=mouse.RIGHT)
            # elif key == 4:
            #     mouse.move(ox,oy)
            else:
                k = self.official_virtual_keys.get(key)
                if k is not None:
                    keyboard.press(k)
                    keyboard.release(k)

        try:
            base_len = 6
            while True:
                cmd = b''
                rest = base_len - 0
                while rest > 0:
                    cmd += conn.recv(rest)
                    rest -= len(cmd)
                key = cmd[0]
                op = cmd[1]
                # x = struct.unpack('>H', cmd[2:4])[0]
                # y = struct.unpack('>H', cmd[4:6])[0]
                x = cmd[2]
                y = cmd[3]
                Op(key, op, x, y)
        except:
            return

    # 传输屏幕信息
    def handle(self, conn):
        if self.imbyt is None:
            imorg = np.asarray(ImageGrab.grab())
            _, self.imbyt = cv2.imencode(".jpg", imorg, [cv2.IMWRITE_JPEG_QUALITY, self.IMQUALITY])
            imnp = np.asarray(self.imbyt, np.uint8)
            self.img = cv2.imdecode(imnp, cv2.IMREAD_COLOR)
        lenb = struct.pack(">BI", 1, len(self.imbyt))
        conn.sendall(lenb)
        conn.sendall(self.imbyt)
        print("3")
        while True:
            # cv2.waitKey(0)
            gb = ImageGrab.grab()
            imgnpn = np.asarray(gb)
            _, timbyt = cv2.imencode(".jpg", imgnpn, [cv2.IMWRITE_JPEG_QUALITY, self.IMQUALITY])
            imnp = np.asarray(timbyt, np.uint8)
            imgnew = cv2.imdecode(imnp, cv2.IMREAD_COLOR)
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
                conn.sendall(lenb)
                conn.sendall(imb)
            else:
                # 传原编码图像
                lenb = struct.pack(">BI", 1, l1)
                conn.sendall(lenb)
                conn.sendall(self.imbyt)
            print("4")


class CtrlSock(object):

    def __init__(self, beCtrlHost):
        self.img = None
        self.imbyt = None
        self.bufsize = 10240  # socket缓冲区大小
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # hs = beCtrlHost.split(":")
        # if len(hs) == 2:
        self.beCtrlHost = beCtrlHost

    def __del__(self):
        self.sock.close()

    def run(self):
        thread = threading.Thread(target=self.startCtrl)
        thread.setDaemon(True)
        thread.start()

    # def request(self):
    #     self.sock.connect(self.beCtrlHost)
    #     print("request")
    #     header, data = receive_data(self.sock)
    #     if header == "accept":
    #         self.startCtrl()
    #     else:
    #         self.__del__()

    # 绑定事件
    # def BindEvents(self, canvas):
    #     def EventDo(data):
    #         self.sock.sendall(data)
    #
    #     # 鼠标左键
    #     def LeftDown(e):
    #         return EventDo(struct.pack('>BBHH', 1, 100, e.x, e.y))
    #
    #     def LeftUp(e):
    #         return EventDo(struct.pack('>BBHH', 1, 117, e.x, e.y))
    #
    #     canvas.bind(sequence="<1>", func=LeftDown)
    #     canvas.bind(sequence="<ButtonRelease-1>", func=LeftUp)
    #
    #     # 鼠标右键
    #     def RightDown(e):
    #         return EventDo(struct.pack('>BBHH', 3, 100, e.x, e.y))
    #
    #     def RightUp(e):
    #         return EventDo(struct.pack('>BBHH', 3, 117, e.x, e.y))
    #
    #     canvas.bind(sequence="<3>", func=RightDown)
    #     canvas.bind(sequence="<ButtonRelease-3>", func=RightUp)
    #
    #     # 鼠标滚轮
    #     def Wheel(e):
    #         if e.delta < 0:
    #             return EventDo(struct.pack('>BBHH', 2, 0, e.x, e.y))
    #         else:
    #             return EventDo(struct.pack('>BBHH', 2, 1, e.x, e.y))
    #
    #     canvas.bind(sequence="<MouseWheel>", func=Wheel)
    #
    #     # 键盘
    #     def KeyDown(e):
    #         return EventDo(struct.pack('>BBHH', e.keycode, 100, e.x, e.y))
    #
    #     def KeyUp(e):
    #         return EventDo(struct.pack('>BBHH', e.keycode, 117, e.x, e.y))
    #
    #     canvas.bind(sequence="<KeyPress>", func=KeyDown)
    #     canvas.bind(sequence="<KeyRelease>", func=KeyUp)

    def BindEvents(self):

        def EventDo(data):
            self.sock.sendall(data)

        def mouseEvent(event, x, y, flags, param):
            if event == cv2.EVENT_LBUTTONDOWN:
                EventDo(struct.pack('>BBHH', 1, 100, x, y))
            elif event == cv2.EVENT_LBUTTONUP:
                EventDo(struct.pack('>BBHH', 1, 117, x, y))
            elif event == cv2.EVENT_RBUTTONDOWN:
                EventDo(struct.pack('>BBHH', 3, 100, x, y))
            elif event == cv2.EVENT_RBUTTONUP:
                EventDo(struct.pack('>BBHH', 3, 117, x, y))
            elif event == cv2.EVENT_MOUSEWHEEL:
                EventDo(struct.pack('>BBHH', 2, 0, x, y))
            elif event == cv2.EVENT_MOUSEHWHEEL:
                EventDo(struct.pack('>BBHH', 2, 1, x, y))
            # elif event == cv2.EVENT_MOUSEMOVE:
            #     EventDo(struct.pack('>BBHH', 4, 4, x, y))

        cv2.setMouseCallback("Control", mouseEvent)

    def startCtrl(self):
        while True:
            try:
                self.sock.connect(self.beCtrlHost)
                break
            except Exception as e:
                print("Could not connect to the client" + str(self.server))
        header, data = receive_data(self.sock)
        if header == "accept":
            lenb = self.sock.recv(5)
            imtype, le = struct.unpack(">BI", lenb)
            imb = b''
            while le > self.bufsize:
                t = self.sock.recv(self.bufsize)
                imb += t
                le -= len(t)
            while le > 0:
                t = self.sock.recv(le)
                imb += t
                le -= len(t)
            data = np.frombuffer(imb, dtype=np.uint8)
            self.img = cv2.imdecode(data, cv2.IMREAD_COLOR)
            # h, w, _ = img.shape
            # imsh = cv2.cvtColor(img, cv2.COLOR_BGR2RGBA)
            # imi = Image.fromarray(imsh)
            # imgTK = ImageTk.PhotoImage(imi)
            imsh = cv2.cvtColor(self.img, cv2.COLOR_BGR2RGB)
            cv2.namedWindow('Control', cv2.WINDOW_NORMAL)
            cv2.imshow('Control', imsh)
            print("1")
            self.BindEvents()
            print("2")
            while True:
                try:
                    lenb = self.sock.recv(5)
                    imtype, le = struct.unpack(">BI", lenb)
                    imb = b''
                    while le > self.bufsize:
                        t = self.sock.recv(self.bufsize)
                        imb += t
                        le -= len(t)
                    while le > 0:
                        t = self.sock.recv(le)
                        imb += t
                        le -= len(t)
                    data = np.frombuffer(imb, dtype=np.uint8)
                    ims = cv2.imdecode(data, cv2.IMREAD_COLOR)
                    if imtype == 1:
                        # 全传
                        self.img = ims
                    else:
                        # 差异传
                        self.img = self.img + ims
                    imsh = cv2.cvtColor(self.img, cv2.COLOR_BGR2RGB)
                    cv2.imshow('Control', imsh)
                    print("5")
                    keyNum = cv2.waitKey(1)
                    if 0<=keyNum<=255:
                        print("6")
                        self.sock.sendall(struct.pack('>BBHH', hex(keyNum), 100, 0, 0))
                        # self.sock.sendall(struct.pack('>BBHH', hex(keyNum), 117, 0, 0))
                except:
                    break
            # cv2.destroyAllWindows()