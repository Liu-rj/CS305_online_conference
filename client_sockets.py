import socket
import threading
from typing import Tuple, Union
import cv2
import struct
import pickle
import zlib
import numpy as np
import pyaudio
from PIL import ImageGrab, ImageTk, Image
import mouse
import keyboard

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


def parse_data(raw_data):
    raw_data = raw_data.decode().split('\r\n\r\n')
    header = raw_data[0]
    data = raw_data[1]
    return header, data


def send_data(sock, header, data):
    pack = header + b'\r\n\r\n' + data
    sock.sendall(pack)


class VideoSock(object):
    def __init__(self, server: Tuple[str, int], client):
        self.server = server
        self.client = client
        self.room_id = None
        self.interval = 1
        self.fx = 1 / (self.interval + 1)
        if self.fx < 0.3:
            self.fx = 0.3

        self.sharing = False
        self.receiving = False

    def __del__(self):
        self.sharing = False
        self.receiving = False

    def start_sharing(self):
        threading.Thread(target=self.share_video, daemon=True).start()

    def start_receiving(self):
        threading.Thread(target=self.receive_video, daemon=True).start()

    def end_receiving(self):
        self.room_id = None
        self.receiving = False
        self.sharing = False

    def share_video(self):
        self.sharing = True
        cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        while True:
            try:
                sock.connect(self.server)
                raw_data = b''
                while not raw_data:
                    send_data(sock, b'share', 'roomId {}'.format(str(self.room_id)).encode())
                    raw_data = sock.recv(2048)
                    # print(raw_data)
                header, data = parse_data(raw_data)
                break
            except socket.error as e:
                # print(e)
                print("Could not connect to the server" + str(self.server))
        ip_b = sock.getsockname()[0].encode()
        if header == '200 OK':
            print("VIDEO sender starts...")
            while self.sharing and cap.isOpened():
                ret, frame = cap.read()
                sframe = cv2.resize(frame, (0, 0), fx=self.fx, fy=self.fx)
                data = pickle.dumps(sframe)
                zdata = zlib.compress(data, zlib.Z_BEST_COMPRESSION)
                try:
                    sock.sendall(struct.pack("L", len(ip_b)) + ip_b + struct.pack("L", len(zdata)) + zdata)
                except:
                    break
                for i in range(self.interval):
                    cap.read()
        sock.sendall(struct.pack("L", len(ip_b)) + ip_b + struct.pack("L", 0))
        sock.close()
        cap.release()

    def receive_video(self):
        self.receiving = True
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        while True:
            try:
                sock.connect(self.server)
                send_data(sock, b'receive', 'roomId {}'.format(str(self.room_id)).encode())
                break
            except socket.error as e:
                # print(e)
                print("Could not connect to the server" + str(self.server))
        print("VIDEO receiver starts...")
        data = b''
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
                self.client.video_update_frame(ip, None)
                # cv2.destroyWindow(ip)
                continue
            while len(data) < msg_size:
                data += sock.recv(81920)
            zframe_data = data[:msg_size]
            data = data[msg_size:]
            frame_data = zlib.decompress(zframe_data)
            frame = pickle.loads(frame_data)
            self.client.video_update_frame(ip, frame)
        sock.close()


class AudioSock(object):
    def __init__(self, server):
        self.server = server
        self.room_id: Union[None, int] = None
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
        threading.Thread(target=self.share_audio, daemon=True).start()

    def start_receiving(self):
        threading.Thread(target=self.receive_audio, daemon=True).start()

    def end_receiving(self):
        self.room_id = None
        self.receiving = False
        self.sharing = False

    def share_audio(self):
        self.sharing = True
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        while True:
            try:
                sock.connect(self.server)
                raw_data = b''
                while not raw_data:
                    send_data(sock, b'share', f'roomId {self.room_id}'.encode())
                    raw_data = sock.recv(2048)
                header, data = parse_data(raw_data)
                break
            except socket.error as e:
                # print(e)
                print("Could not connect to the server" + str(self.server))
        if header == '200 OK':
            print("AUDIO sender starts...")
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
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        while True:
            try:
                sock.connect(self.server)
                send_data(sock, b'receive', f'roomId {self.room_id}'.encode())
                break
            except socket.error as e:
                # print(e)
                print("Could not connect to the server" + str(self.server))
        print("AUDIO receiver starts...")
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
        threading.Thread(target=self.share_screen, daemon=True).start()

    def start_receiving(self):
        threading.Thread(target=self.receive_screen, daemon=True).start()

    def end_receiving(self):
        self.room_id = None
        self.receiving = False
        self.sharing = False

    def share_screen(self):
        self.sharing = True
        print("SCREEN sender starts...")
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        while True:
            try:
                sock.connect(self.server)
                raw_data = b''
                while not raw_data:
                    send_data(sock, b'share', 'roomId {}'.format(str(self.room_id)).encode())
                    raw_data = sock.recv(2048)
                header, data = parse_data(raw_data)
                break
            except Exception as e:
                # print(e)
                print("Could not connect to the server" + str(self.server))
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
            sock.sendall(struct.pack(">BI", 2, 0))
        sock.close()

    def receive_screen(self):
        self.receiving = True
        print("SCREEN receiver starts...")
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        while True:
            try:
                sock.connect(self.server)
                raw_data = b''
                while not raw_data:
                    send_data(sock, b'receive', 'roomId {}'.format(str(self.room_id)).encode())
                    raw_data = sock.recv(2048)
                header, data = parse_data(raw_data)
                break
            except socket.error as e:
                print("Could not connect to the server" + str(self.server))
        while self.receiving:
            lenb = sock.recv(5)
            imtype, le = struct.unpack(">BI", lenb)
            imb = sock.recv(le)
            data = np.frombuffer(imb, dtype=np.uint8)
            self.img = cv2.imdecode(data, cv2.IMREAD_COLOR)
            imsh = cv2.cvtColor(self.img, cv2.COLOR_BGR2RGB)
            cv2.namedWindow('Screen', cv2.WINDOW_NORMAL)
            cv2.imshow('Screen', imsh)
            cv2.waitKey(10)
            lenb = sock.recv(5)
            imtype, le = struct.unpack(">BI", lenb)
            while imtype != 2:
                try:
                    imb = sock.recv(le)
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
                    cv2.waitKey(10)
                    lenb = sock.recv(5)
                    imtype, le = struct.unpack(">BI", lenb)
                except:
                    break
            cv2.destroyWindow('Screen')
        sock.close()


class beCtrlSock(object):

    def __init__(self, addr, client):
        self.img = None
        self.imbyt = None
        self.IMQUALITY = 50  # 压缩比 1-100 数值越小，压缩比越高，图片质量损失越严重
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.bind(addr)
        self.conn = None
        self.beCtrl = False
        self.owner = client

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
            self.owner.stats.client_meeting.ctrl_signal.emit(addr[0])
            # self.stats.handle_control_msg(addr)
            # self.handle_confirm()
            # print("accept")

    def handle_confirm(self):
        self.beCtrl = True
        send_data(self.conn, b'accept', (str(self.conn.getsockname()[0])).encode())
        threading.Thread(target=self.handle, args=(self.conn,)).start()
        threading.Thread(target=self.control, args=(self.conn,)).start()

    def handle_cancel(self):
        send_data(self.conn, b'refuse', ("").encode())
        self.conn.close()

    # 读取控制命令，并在本机还原操作
    def control(self, conn):
        official_virtual_keys = {
            0x08: 'backspace',
            0x09: 'tab',
            0x0d: 'enter',
            0x20: 'space',
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
            0x61: 'a',
            0x62: 'b',
            0x63: 'c',
            0x64: 'd',
            0x65: 'e',
            0x66: 'f',
            0x67: 'g',
            0x68: 'h',
            0x69: 'i',
            0x6a: 'j',
            0x6b: 'k',
            0x6c: 'l',
            0x6d: 'm',
            0x6e: 'n',
            0x6f: 'o',
            0x70: 'p',
            0x71: 'q',
            0x72: 'r',
            0x73: 's',
            0x74: 't',
            0x75: 'u',
            0x76: 'v',
            0x77: 'w',
            0x78: 'x',
            0x79: 'y',
            0x7a: 'z',
            # 0x60: '0',
            # 0x61: '1',
            # 0x62: '2',
            # 0x63: '3',
            # 0x64: '4',
            # 0x65: '5',
            # 0x66: '6',
            # 0x67: '7',
            # 0x68: '8',
            # 0x69: '9',
            0x2a: '*',
            0x3d: '=',
            0x2f: '/',
            0x2b: '+',
            0x2c: ',',
            0x2d: '-',
            0x2e: '.',
            0x3b: ';',
            0x5b: '[',
            0x5d: ']',
            0x60: '`',
            0x3c: '<',
            0x3e: '>',
            0x3a: ':',
            0xae: '\'',
            0xaf: '\'',
            0xa2: '\\',
        }

        def Op(key, op, ox, oy):
            # print(key, op, ox, oy)
            if key == 1:
                if op == 100:
                    # 左键按下
                    # mouse.move(ox, oy)
                    mouse.press(button=mouse.LEFT)
                elif op == 117:
                    # 左键弹起
                    # x, y = mouse.get_position()
                    # if ox != x or oy != y:
                    #     if not mouse.is_pressed():
                    #         mouse.press(button=mouse.LEFT)
                    #     mouse.move(ox, oy)
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
                    # mouse.move(ox, oy)
                    mouse.press(button=mouse.RIGHT)
                elif op == 117:
                    # 右键弹起
                    # mouse.move(ox, oy)
                    mouse.release(button=mouse.RIGHT)
            elif key == 4 and op == 4:
                mouse.move(ox, oy)
            else:
                k = official_virtual_keys.get(key)
                if k is not None:
                    print(k)
                    keyboard.press(k)
                    # keyboard.release(k)

        try:
            base_len = 6
            while self.beCtrl:
                cmd = b''
                rest = base_len - 0
                while rest > 0:
                    cmd += conn.recv(rest)
                    rest -= len(cmd)
                key = cmd[0]
                op = cmd[1]
                x = struct.unpack('>H', cmd[2:4])[0]
                y = struct.unpack('>H', cmd[4:6])[0]
                if key == 0 and op == 0 and x == 0 and y == 0:
                    self.beCtrl = False
                    break
                else:
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
        while self.beCtrl:
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
            try:
                if l1 > l2:
                    # 传差异化图像
                    lenb = struct.pack(">BI", 0, l2)
                    if self.beCtrl:
                        conn.sendall(lenb)
                        conn.sendall(imb)
                else:
                    # 传原编码图像
                    lenb = struct.pack(">BI", 1, l1)
                    if self.beCtrl:
                        conn.sendall(lenb)
                        conn.sendall(self.imbyt)
            except socket.error as e:
                print(e)
                conn.close()
                return
        conn.close()


class CtrlSock(object):

    def __init__(self, beCtrlHost, client):
        self.img = None
        self.imbyt = None
        self.bufsize = 10240  # socket缓冲区大小
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # hs = beCtrlHost.split(":")
        # if len(hs) == 2:
        self.beCtrlHost = beCtrlHost
        self.owner = client

    def __del__(self):
        self.sock.close()

    def run(self):
        thread = threading.Thread(target=self.startCtrl)
        thread.setDaemon(True)
        thread.start()

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
                if flags < 0:
                    EventDo(struct.pack('>BBHH', 2, 0, x, y))
                else:
                    EventDo(struct.pack('>BBHH', 2, 1, x, y))
            elif event == cv2.EVENT_MOUSEMOVE:
                EventDo(struct.pack('>BBHH', 4, 4, x, y))

        cv2.setMouseCallback("Control", mouseEvent)

    def startCtrl(self):
        while True:
            try:
                self.sock.connect(self.beCtrlHost)
                raw_data = b''
                while not raw_data:
                    raw_data = self.sock.recv(2048)
                header, data = parse_data(raw_data)
                break
            except Exception as e:
                print("Could not connect to the client" + str(self.beCtrlHost))
                return
        if header == "accept":
            lenb = self.sock.recv(5)
            imtype, le = struct.unpack(">BI", lenb)
            # imb = b''
            # while le > self.bufsize:
            #     t = self.sock.recv(self.bufsize)
            #     imb += t
            #     le -= len(t)
            # while le > 0:
            #     t = self.sock.recv(le)
            #     imb += t
            #     le -= len(t)
            imb = self.sock.recv(le)
            data = np.frombuffer(imb, dtype=np.uint8)
            self.img = cv2.imdecode(data, cv2.IMREAD_COLOR)
            imsh = cv2.cvtColor(self.img, cv2.COLOR_BGR2RGB)
            cv2.namedWindow('Control', cv2.WINDOW_NORMAL)
            cv2.imshow('Control', imsh)
            self.BindEvents()
            while True:
                try:
                    lenb = self.sock.recv(5)
                    imtype, le = struct.unpack(">BI", lenb)
                    # imb = b''
                    # while le > self.bufsize:
                    #     t = self.sock.recv(self.bufsize)
                    #     imb += t
                    #     le -= len(t)
                    # while le > 0:
                    #     t = self.sock.recv(le)
                    #     imb += t
                    #     le -= len(t)
                    imb = self.sock.recv(le)
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
                    keyNum = cv2.waitKey(10)
                    if keyNum == 27:
                        self.sock.sendall(struct.pack('>BBHH', 0, 0, 0, 0))
                        break
                    elif 0 <= keyNum <= 255:
                        self.sock.sendall(struct.pack('>BBHH', keyNum, 100, 0, 0))
                except Exception as e:
                    break
            cv2.destroyWindow('Control')
        elif header == "refuse":
            self.owner.stats.client_meeting.denied_signal.emit(self.beCtrlHost[0])