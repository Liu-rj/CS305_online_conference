
#客户端代码
import socket
import threading
import cv2
import numpy as np
from PIL import ImageGrab
from pynput.mouse import Button,Controller

#接受服务器返回的数据的函数
m = Controller()
def recvlink(client):
    while True:
        msg=client.recv(1024)
        msg=msg.decode('utf-8')
        print(msg)
        key = msg.split(",")
        xp = int(key[0])
        yp = int(key[1])
        m.position = ((xp,yp))
        m.click(Button.left,1)


def main():
    #创建ipv4的socket对象，使用TCP协议(SOCK_STREAM)
    client=socket.socket(socket.AF_INET,socket.SOCK_STREAM)

    #设置服务器ip地址，注意应该是服务器的公网ip
    host='10.25.10.50'
    #设置要发送到的服务器端口,需要在云服务器管理界面打开对应端口的防火墙
    port=5004

    #建立TCP协议连接,这时候服务器就会监听到到连接请求，并开始等待接受client发送的数据
    client.connect((host,port))

    #建立连接后，服务器端会返回连接成功消息
    start_msg=client.recv(1024)
    print(start_msg.decode('utf-8'))

    #开启一个线程用来接受服务器发来的消息
    t=threading.Thread(target=recvlink,args=(client,))
    t.start()

    p = ImageGrab.grab()#获得当前屏幕
    quality = 25  # 图像的质量
    encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), quality]

    while True:
        im = ImageGrab.grab()
        imm=cv2.cvtColor(np.array(im), cv2.COLOR_RGB2BGR)#转为opencv的BGR格式
        imm = cv2.resize(imm, (1535, 863))
        img_encode = cv2.imencode(".jpg", imm, encode_param)[1]
        data_encode = np.array(img_encode)
        str_encode = data_encode.tostring()
        #print(len(str_encode))
        #输入要发送的信息
        sendmsg="kehu"
        #向服务器发送消息
        client.send(str_encode)
        if sendmsg=='quit':
            break
    #结束时关闭客户端
    client.close()

if __name__ == '__main__':
    while True:
        try:
            main()
        except:
            pass


'''堵塞更改清晰度'''
