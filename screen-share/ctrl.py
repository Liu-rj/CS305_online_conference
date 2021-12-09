import tkinter
import tkinter.messagebox
import struct
import socket
import numpy as np
from PIL import Image, ImageTk
import threading
from cv2 import cv2

root = tkinter.Tk()

# 10.16.22.173
# 放缩大小
scale = 1

# 原传输画面尺寸
fixw, fixh = 0, 0

# 放缩标志
wscale = False

# 屏幕显示画布
showcan = None

# socket缓冲区大小
bufsize = 10240

# 线程
th = None

# socket
soc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)


# 初始化socket
def SetSocket():
    global soc, host_en
    host = host_en.get()
    if host is None:
        tkinter.messagebox.showinfo('提示', 'Host设置错误！')
        return
    hs = host.split(":")
    if len(hs) != 2:
        tkinter.messagebox.showinfo('提示', 'Host设置错误！')
        return
    soc.connect((hs[0], int(hs[1])))


def SetScale(x):
    global scale, wscale
    scale = float(x) / 100
    wscale = True


def ShowScreen():
    global showcan, root, soc, th, wscale
    if showcan is None:
        wscale = True
        showcan = tkinter.Toplevel(root)
        th = threading.Thread(target=run)
        th.start()
    else:
        soc.close()
        showcan.destroy()


val = tkinter.StringVar()
host_lab = tkinter.Label(root, text="Host:")
host_en = tkinter.Entry(root, show=None, font=('Arial', 14), textvariable=val)
sca_lab = tkinter.Label(root, text="Scale:")
sca = tkinter.Scale(root, from_=10, to=100, orient=tkinter.HORIZONTAL, length=100,
                    showvalue=100, resolution=0.1, tickinterval=50, command=SetScale)
show_btn = tkinter.Button(root, text="Show", command=ShowScreen)

host_lab.grid(row=0, column=0, padx=10, pady=10, ipadx=0, ipady=0)
host_en.grid(row=0, column=1, padx=0, pady=0, ipadx=40, ipady=0)
sca_lab.grid(row=1, column=0, padx=10, pady=10, ipadx=0, ipady=0)
sca.grid(row=1, column=1, padx=0, pady=0, ipadx=100, ipady=0)
show_btn.grid(row=2, column=1, padx=0, pady=10, ipadx=30, ipady=0)
sca.set(100)
val.set('127.0.0.1:80')


def run():
    global wscale, fixh, fixw, soc, showcan
    SetSocket()
    lenb = soc.recv(5)
    imtype, le = struct.unpack(">BI", lenb)
    imb = b''
    while le > bufsize:
        t = soc.recv(bufsize)
        imb += t
        le -= len(t)
    while le > 0:
        t = soc.recv(le)
        imb += t
        le -= len(t)
    data = np.frombuffer(imb, dtype=np.uint8)
    img = cv2.imdecode(data, cv2.IMREAD_COLOR)
    h, w, _ = img.shape
    fixh, fixw = h, w
    imsh = cv2.cvtColor(img, cv2.COLOR_BGR2RGBA)
    imi = Image.fromarray(imsh)
    imgTK = ImageTk.PhotoImage(image=imi)
    cv = tkinter.Canvas(showcan, width=w, height=h, bg="white")
    cv.focus_set()
    cv.pack()
    cv.create_image(0, 0, anchor=tkinter.NW, image=imgTK)
    h = int(h * scale)
    w = int(w * scale)
    while True:
        if wscale:
            h = int(fixh * scale)
            w = int(fixw * scale)
            cv.config(width=w, height=h)
            wscale = False
        try:
            lenb = soc.recv(5)
            imtype, le = struct.unpack(">BI", lenb)
            imb = b''
            while le > bufsize:
                t = soc.recv(bufsize)
                imb += t
                le -= len(t)
            while le > 0:
                t = soc.recv(le)
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
            showcan = None
            ShowScreen()
            return


root.mainloop()