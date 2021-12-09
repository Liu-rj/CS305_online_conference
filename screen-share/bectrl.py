import struct
import socket
from PIL import ImageGrab
from cv2 import cv2
import numpy as np
import threading

bufsize = 1024

host = ('10.26.139.226', 80)
soc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
soc.bind(host)
soc.listen(1)
# 压缩比 1-100 数值越小，压缩比越高，图片质量损失越严重
IMQUALITY = 50

lock = threading.Lock()

# 压缩后np图像
img = None
# 编码后的图像
imbyt = None

def handle(conn):
    global img, imbyt
    lock.acquire()
    if imbyt is None:
        imorg = np.asarray(ImageGrab.grab())
        _, imbyt= cv2.imencode(".jpg", imorg, [cv2.IMWRITE_JPEG_QUALITY,IMQUALITY])
        imnp = np.asarray(imbyt, np.uint8)
        img = cv2.imdecode(imnp, cv2.IMREAD_COLOR)
    lock.release()
    lenb = struct.pack(">BI", 1, len(imbyt))
    conn.sendall(lenb)
    conn.sendall(imbyt)
    while True:
        cv2.waitKey(100)
        gb = ImageGrab.grab()
        imgnpn = np.asarray(gb)
        _, timbyt= cv2.imencode(".jpg", imgnpn, [cv2.IMWRITE_JPEG_QUALITY,IMQUALITY])
        imnp = np.asarray(timbyt, np.uint8)
        imgnew = cv2.imdecode(imnp, cv2.IMREAD_COLOR)
        # 计算图像差值
        imgs = imgnew - img
        if (imgs!=0).any():
            # 画质改变
            pass
        else:
            continue
        imbyt = timbyt
        img = imgnew
        # 无损压缩
        _, imb = cv2.imencode(".png", imgs)
        l1 = len(imbyt) # 原图像大小
        l2 = len(imb) # 差异图像大小
        if l1 > l2:
            # 传差异化图像
            lenb = struct.pack(">BI", 0, l2)
            conn.sendall(lenb)
            conn.sendall(imb)
        else:
            # 传原编码图像
            lenb = struct.pack(">BI", 1, l1)
            conn.sendall(lenb)
            conn.sendall(imbyt)


while True:
    conn, addr = soc.accept()
    threading.Thread(target=handle, args=(conn,)).start()
