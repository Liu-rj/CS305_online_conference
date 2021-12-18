
#服务器端
import socket
import threading
import numpy as np
import cv2
import os
#接受客户端消息函数

print("等待连接---")
def mouse_click(event, x, y, flags, para):
    if event == cv2.EVENT_LBUTTONDOWN:  # 左边鼠标点击
        f=open("1.txt","w")
        f.write(str(x)+","+str(y))
        f.close()
        
        
def recv_msg(clientsocket):
    while True:
        # 接受客户端消息,设置一次最多接受10240字节的数据
        recv_msg = clientsocket.recv(102400)
        # 把接收到的东西解码
        msg = np.fromstring(recv_msg, np.uint8)
        img_decode = cv2.imdecode(msg, cv2.IMREAD_COLOR)
        try:
            s=img_decode.shape
            img_decode=img_decode
            temp=img_decode
        except:
            img_decode=temp
            pass
        cv2.imshow('SERVER', img_decode)
        cv2.setMouseCallback("SERVER", mouse_click)
        try:
            f=open("1.txt")
            txt=f.read()
            f.close()
            reply=txt
            print(reply)
            clientsocket.send(reply.encode('utf-8'))
            os.remove("1.txt")
        except:
            pass
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

def main():
    socket_server=socket.socket(socket.AF_INET,socket.SOCK_STREAM)

    host='10.25.10.50'
    #设置被监听的端口号,小于1024的端口号不能使用
    port=5004

    socket_server.bind((host,port))
    #设置最大监听数，也就是最多可以同时响应几个客户端请求，一般配合多线程使用
    socket_server.listen(5)
    #等待客户端连接,一旦有了连接就立刻向下执行，否则等待
    #accept()函数会返回一个元组，第一个元素是客户端socket对象，第二个元素是客户端地址（ip地址+端口号）
    clientsocket,addr=socket_server.accept()

    # 有了客户端连接后之后才能执行以下代码，我们先向客户端发送连接成功消息
    clientsocket.send('连接成功'.encode('utf-8'))

    # 和客户端一样开启一个线程接受客户端的信息
    t=threading.Thread(target=recv_msg,args=(clientsocket,))
    t.start()
    
    

    
if __name__=='__main__':
    main()
