#!/usr/bin/python
# -*- coding: UTF-8 -*-
import sys
import cv2

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import QPalette, QBrush, QPixmap
import os
import socket
import threading
import cv2
import numpy as np
from PIL import ImageGrab
from pynput.mouse import Button,Controller
import time
m = Controller()
def mouse_click(event, x, y, flags, para):
    if event == cv2.EVENT_LBUTTONDOWN:  # 左边鼠标点击
        print( x, y)

        m.position = (x, y)
        time.sleep(0.1)
        m.click(Button.left, 1)

class Ui_MainWindow(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super(Ui_MainWindow, self).__init__(parent)

        # self.face_recong = face.Recognition()
        self.timer_camera = QtCore.QTimer()
        self.cap = cv2.VideoCapture()
        self.CAM_NUM = 0
        self.set_ui()
        self.slot_init()
        self.__flag_work = 0
        self.x = 0
        self.count = 0

    def set_ui(self):

        self.__layout_main = QtWidgets.QHBoxLayout()
        self.__layout_fun_button = QtWidgets.QVBoxLayout()
        self.__layout_data_show = QtWidgets.QVBoxLayout()

        self.button_open_camera = QtWidgets.QPushButton(u'远程桌面')

        self.button_close = QtWidgets.QPushButton(u'退出')

        # Button 的颜色修改
        button_color = [self.button_open_camera, self.button_close]
        for i in range(2):
            button_color[i].setStyleSheet("QPushButton{color:black}"
                                          "QPushButton:hover{color:red}"
                                          "QPushButton{background-color:rgb(78,255,255)}"
                                          "QPushButton{border:2px}"
                                          "QPushButton{border-radius:10px}"
                                          "QPushButton{padding:2px 4px}")

        self.button_open_camera.setMinimumHeight(50)
        self.button_close.setMinimumHeight(50)

        # move()方法移动窗口在屏幕上的位置到x = 300，y = 300坐标。
        self.move(500, 500)

        # 信息显示
        self.label_show_camera = QtWidgets.QLabel()
        self.label_move = QtWidgets.QLabel()
        self.label_move.setFixedSize(100, 100)

        self.label_show_camera.setFixedSize(1530,863)
        self.label_show_camera.setAutoFillBackground(False)

        self.__layout_fun_button.addWidget(self.button_open_camera)
        self.__layout_fun_button.addWidget(self.button_close)
        self.__layout_fun_button.addWidget(self.label_move)

        self.__layout_main.addLayout(self.__layout_fun_button)
        self.__layout_main.addWidget(self.label_show_camera)

        self.setLayout(self.__layout_main)
        self.label_move.raise_()
        self.setWindowTitle(u'远控桌面GUI')

        '''
        # 设置背景图片
        palette1 = QPalette()
        palette1.setBrush(self.backgroundRole(), QBrush(QPixmap('background.jpg')))
        self.setPalette(palette1)
        '''
    def mousePressEvent(self,event):
        if event.buttons() & QtCore.Qt.LeftButton:
            x = event.x()-120
            y = event.y()-10
            text = "x: {0},y: {1}".format(x,y)
            if x>=0 and y>=0:
                m.position = (x, y)
                time.sleep(0.1)
                m.click(Button.left, 1)
            print(text)
    def slot_init(self):
        self.button_open_camera.clicked.connect(self.button_open_camera_click)
        self.timer_camera.timeout.connect(self.show_camera)
        self.button_close.clicked.connect(self.close)

    def button_open_camera_click(self):
        if self.timer_camera.isActive() == False:


            self.timer_camera.start(30)

            self.button_open_camera.setText(u'关闭')
        else:
            self.timer_camera.stop()
            self.cap.release()
            self.label_show_camera.clear()
            self.button_open_camera.setText(u'远程桌面')

    def show_camera(self):
        im = ImageGrab.grab()
        imm = cv2.cvtColor(np.array(im), cv2.COLOR_RGB2BGR)  # 转为opencv的BGR格式
        #imm = cv2.resize(imm, (1535, 863))
        self.image = imm
        # face = self.face_detect.align(self.image)
        # if face:
        #     pass
        show =cv2.resize(self.image, (1536,863))
        show = cv2.cvtColor(show, cv2.COLOR_BGR2RGB)
        print(show.shape[1], show.shape[0])
        # show.shape[1] = 640, show.shape[0] = 480

        showImage = QtGui.QImage(show.data, show.shape[1], show.shape[0], QtGui.QImage.Format_RGB888)
        self.label_show_camera.setPixmap(QtGui.QPixmap.fromImage(showImage))
        #cv2.setMouseCallback(showImage, mouse_click)
        # self.x += 1
        # self.label_move.move(self.x,100)

        # if self.x ==320:
        #     self.label_show_camera.raise_()

    def closeEvent(self, event):
        ok = QtWidgets.QPushButton()
        cacel = QtWidgets.QPushButton()

        msg = QtWidgets.QMessageBox(QtWidgets.QMessageBox.Warning, u"关闭", u"是否关闭！")

        msg.addButton(ok, QtWidgets.QMessageBox.ActionRole)
        msg.addButton(cacel, QtWidgets.QMessageBox.RejectRole)
        ok.setText(u'确定')
        cacel.setText(u'取消')
        # msg.setDetailedText('sdfsdff')
        if msg.exec_() == QtWidgets.QMessageBox.RejectRole:
            event.ignore()
        else:
            #             self.socket_client.send_command(self.socket_client.current_user_command)
            if self.cap.isOpened():
                self.cap.release()
            if self.timer_camera.isActive():
                self.timer_camera.stop()
            event.accept()


if __name__ == "__main__":
    App = QApplication(sys.argv)
    ex = Ui_MainWindow()
    ex.show()
    sys.exit(App.exec_())