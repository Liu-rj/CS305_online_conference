import cv2
from PySide2.QtWidgets import *
from PySide2.QtCore import Qt, QSize
from PySide2.QtGui import *
from PIL.ImageQt import ImageQt
from PIL import Image

class Stats():

    def __init__(self, client=None):
        self.client = client
        self.window = MainWindow()
        self.window.setFixedSize(1080, 718)
        self.resolution = QGuiApplication.primaryScreen().availableGeometry()
        self.window.move((self.resolution.width() / 2) - (self.window.frameSize().width() / 2),
                         (self.resolution.height() / 2) - (self.window.frameSize().height() / 2))
        self.window.setWindowTitle('SUSTech Online Meeting')
        palette = QPalette()
        palette.setBrush(QPalette.Background, QBrush(QPixmap("ui/bg.jpg")))
        self.window.setPalette(palette)

        self.create_button = QPushButton('Create Meeting', self.window)
        self.create_button.move(240, 400)
        self.create_button.clicked.connect(self.handle_create)
        self.create_button.setFont(QFont("Times New Roman", 18))
        self.create_button.resize(200, 100)
        self.create_button.setStyleSheet("""QPushButton {
            border: 2px solid #8f8f91;
            border-radius: 6px;
            background-color: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                      stop: 0 #F9680F, stop: 1 #C25919);
            min-width: 80px;
        }
        QPushButton:pressed {
            background-color: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                      stop: 0 #C25919, stop: 1 #F9680F);
        }
        QPushButton:flat {
            border: none; /* no border for a flat push button */
        }
        QPushButton:default {
            border-color: navy; /* make the default button prominent */
        }""")

        self.join_button = QPushButton('Join Meeting', self.window)
        self.join_button.move(640, 400)
        self.join_button.clicked.connect(self.handle_join)
        self.join_button.setFont(QFont("Times New Roman", 18))
        self.join_button.resize(200, 100)
        self.join_button.setStyleSheet("""QPushButton {
            border: 2px solid #8f8f91;
            border-radius: 6px;
            background-color: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                      stop: 0 #94F017, stop: 1 #79C01A);
            min-width: 80px;
        }
        QPushButton:pressed {
            background-color: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                      stop: 0 #79C01A, stop: 1 #94F017);
        }
        QPushButton:flat {
            border: none; /* no border for a flat push button */
        }
        QPushButton:default {
            border-color: navy; /* make the default button prominent */
        }""")

        self.meeting_window = MeetingWindow()
        self.meeting_window.setFixedSize(1200, 900)
        self.meeting_window.move((self.resolution.width() / 2) - (self.meeting_window.frameSize().width() / 2),
                                 (self.resolution.height() / 2) - (self.meeting_window.frameSize().height() / 2))
        self.meeting_window.setWindowTitle('SUSTech Online Meeting')

    def handle_join(self):
        self.join_window = QLineEdit()
        self.join_window.setPlaceholderText('Please input the meeting id')
        self.join_window.setStyleSheet("color: blue;"
                                       "background-color: yellow;"
                                       "selection-color: yellow;"
                                       "selection-background-color: blue;")
        self.join_window.setFixedSize(QSize(400, 50))
        self.join_window.setWindowTitle('Join Meeting')
        self.join_window.setFont(QFont("Times New Roman", 18))
        self.join_window.returnPressed.connect(self.on_join)
        self.join_window.show()

    def init_meeting_window_buttons(self):
        self.voice_button = QToolButton(self.meeting_window)
        self.voice_button.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        self.voice_button.setIcon(QIcon('ui/open_voice.png'))
        self.voice_button.setIconSize(QSize(50, 50))
        self.voice_button.setText('Mute')
        self.voice_button.setFont(QFont("Times New Roman", 18))
        self.voice_button_status = 1  # 1 for open, 0 for close
        self.voice_button.clicked.connect(self.handle_voice_button)
        self.voice_button.move(0, 800)
        self.voice_button.resize(200, 100)
        self.voice_button.setStyleSheet("QToolButton{border:none;color:rgb(0, 0, 0);}"
                                        "QToolButton:hover{background-color: rgb(20, 62, 134);border:none;color:rgb(255, 255, 255);}"
                                        "QToolButton:checked{background-color: rgb(20, 62, 134);border:none;color:rgb(255, 255, 255);}")
        self.client.audio_sharing()

        self.video_button = QToolButton(self.meeting_window)
        self.video_button.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        self.video_button.setIcon(QIcon('ui/closed_video.png'))
        self.video_button.setIconSize(QSize(50, 50))
        self.video_button.setText('Open Video')
        self.video_button.setFont(QFont("Times New Roman", 18))
        self.video_button_status = 0  # 1 for open, 0 for close
        self.video_button.clicked.connect(self.handle_video_button)
        self.video_button.move(200, 800)
        self.video_button.resize(200, 100)
        self.video_button.setStyleSheet("QToolButton{border:none;color:rgb(0, 0, 0);}"
                                        "QToolButton:hover{background-color: rgb(20, 62, 134);border:none;color:rgb(255, 255, 255);}"
                                        "QToolButton:checked{background-color: rgb(20, 62, 134);border:none;color:rgb(255, 255, 255);}")

        self.screen_share_button = QToolButton(self.meeting_window)
        self.screen_share_button.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        self.screen_share_button.setIcon(QIcon('ui/open_share.png'))
        self.screen_share_button.setIconSize(QSize(50, 50))
        self.screen_share_button.setText('Start Sharing')
        self.screen_share_button.setFont(QFont("Times New Roman", 18))
        self.screen_share_button_status = 1  # 1 for open, 0 for close
        self.screen_share_button.clicked.connect(self.handle_screen_share_button)
        self.screen_share_button.move(400, 800)
        self.screen_share_button.resize(200, 100)
        self.screen_share_button.setStyleSheet("QToolButton{border:none;color:rgb(0, 0, 0);}"
                                               "QToolButton:hover{background-color: rgb(20, 62, 134);border:none;color:rgb(255, 255, 255);}"
                                               "QToolButton:checked{background-color: rgb(20, 62, 134);border:none;color:rgb(255, 255, 255);}")

        self.screen_control_button = QToolButton(self.meeting_window)
        self.screen_control_button.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        self.screen_control_button.setIcon(QIcon('ui/control.png'))
        self.screen_control_button.setIconSize(QSize(50, 50))
        self.screen_control_button.setText('Desktop Control')
        self.screen_control_button.setFont(QFont("Times New Roman", 18))
        self.screen_control_button.clicked.connect(self.handle_screen_control_button)
        self.screen_control_button.move(600, 800)
        self.screen_control_button.resize(200, 100)
        self.screen_control_button.setStyleSheet("QToolButton{border:none;color:rgb(0, 0, 0);}"
                                                 "QToolButton:hover{background-color: rgb(20, 62, 134);border:none;color:rgb(255, 255, 255);}"
                                                 "QToolButton:checked{background-color: rgb(20, 62, 134);border:none;color:rgb(255, 255, 255);}")

        self.invite_button = QToolButton(self.meeting_window)
        self.invite_button.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        self.invite_button.setIcon(QIcon('ui/invite.png'))
        self.invite_button.setIconSize(QSize(50, 50))
        self.invite_button.setText('Invite')
        self.invite_button.setFont(QFont("Times New Roman", 18))
        self.invite_button.clicked.connect(self.handle_invite_button)
        self.invite_button.move(800, 800)
        self.invite_button.resize(200, 100)
        self.invite_button.setStyleSheet("QToolButton{border:none;color:rgb(0, 0, 0);}"
                                         "QToolButton:hover{background-color: rgb(20, 62, 134);border:none;color:rgb(255, 255, 255);}"
                                         "QToolButton:checked{background-color: rgb(20, 62, 134);border:none;color:rgb(255, 255, 255);}")

        self.more_button = QToolButton(self.meeting_window)
        self.more_button.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        self.more_button.setIcon(QIcon('ui/more.png'))
        self.more_button.setIconSize(QSize(50, 50))
        self.more_button.setText('More')
        self.more_button.setFont(QFont("Times New Roman", 18))
        self.more_button.clicked.connect(self.handle_more_button)
        self.more_button.move(1000, 800)
        self.more_button.resize(200, 100)
        self.more_button.setStyleSheet("QToolButton{border:none;color:rgb(0, 0, 0);}"
                                       "QToolButton:hover{background-color: rgb(20, 62, 134);border:none;color:rgb(255, 255, 255);}"
                                       "QToolButton:checked{background-color: rgb(20, 62, 134);border:none;color:rgb(255, 255, 255);}")

    def on_join(self):
        meeting_id = self.join_window.text()
        if not self.client.join_meeting(meeting_id):
            # TODO: add pop up
            pass
        self.join_window.close()
        self.meeting_window = MeetingWindow()
        self.meeting_window.setFixedSize(1200, 900)
        self.meeting_window.move((self.resolution.width() / 2) - (self.meeting_window.frameSize().width() / 2),
                                 (self.resolution.height() / 2) - (self.meeting_window.frameSize().height() / 2))
        self.meeting_window.setWindowTitle('SUSTech Online Meeting ' + str(self.client.room_id))
        self.init_meeting_window_buttons()
        self.meeting_window.show()

    def handle_create(self):
        self.client.create_meeting()
        self.meeting_window = MeetingWindow()
        self.meeting_window.setFixedSize(1200, 900)
        self.meeting_window.move((self.resolution.width() / 2) - (self.meeting_window.frameSize().width() / 2),
                                 (self.resolution.height() / 2) - (self.meeting_window.frameSize().height() / 2))
        self.meeting_window.setWindowTitle('SUSTech Online Meeting ' + str(self.client.room_id))
        self.init_meeting_window_buttons()
        self.update_all_clients()
        self.meeting_window.show()
        self.window.close()

    def handle_voice_button(self):
        if self.voice_button_status == 1:
            self.voice_button.setIcon(QIcon('ui/closed_voice.png'))
            self.voice_button_status = 0
            self.voice_button.setText('Unmute')
            self.client.audio_sock.sharing = False
        else:
            self.voice_button.setIcon(QIcon('ui/open_voice.png'))
            self.voice_button_status = 1
            self.voice_button.setText('Mute')
            self.client.audio_sharing()

    def handle_video_button(self):
        if self.video_button_status == 1:
            self.video_button.setIcon(QIcon('ui/closed_video.png'))
            self.video_button_status = 0
            self.video_button.setText('Open Video')
            self.client.video_sock.sharing = False
        else:
            self.video_button.setIcon(QIcon('ui/open_video.png'))
            self.video_button_status = 1
            self.video_button.setText('Close Video')
            self.client.video_sharing()

    def handle_screen_share_button(self):
        if self.screen_share_button_status == 1:
            self.screen_share_button.setIcon(QIcon('ui/closed_share.png'))
            self.screen_share_button_status = 0
            self.screen_share_button.setText('Start Sharing')
            self.client.screen_sock.sharing = False
        else:
            self.screen_share_button.setIcon(QIcon('ui/open_share.png'))
            self.screen_share_button_status = 1
            self.screen_share_button.setText('Close Sharing')
            self.client.screen_sharing()

    def handle_screen_control_button(self):
        self.control_window = QMainWindow()
        self.control_window.setFixedSize(225, 220)
        self.control_window.move((self.resolution.width() / 2) - (self.control_window.frameSize().width() / 2),
                                 (self.resolution.height() / 2) - (self.control_window.frameSize().height() / 2))
        self.control_window.setWindowTitle('Participant list')
        self.control_confirm_button = QPushButton(self.control_window)
        self.control_confirm_button.resize(100, 50)
        self.control_confirm_button.move(10, 170)
        self.control_confirm_button.setText("Confirm")
        self.control_confirm_button.setFont(QFont("Times New Roman", 18))
        self.control_confirm_button.setStyleSheet("QToolButton{border:none;color:rgb(0, 0, 0);}"
                                                  "QToolButton:hover{background-color: rgb(20, 62, 134);border:none;color:rgb(255, 255, 255);}"
                                                  "QToolButton:checked{background-color: rgb(20, 62, 134);border:none;color:rgb(255, 255, 255);}")
        self.control_confirm_button.clicked.connect(self.handle_control_confirm)
        self.control_cancel_button = QPushButton(self.control_window)
        self.control_cancel_button.resize(100, 50)
        self.control_cancel_button.move(115, 170)
        self.control_cancel_button.setText("Cancel")
        self.control_cancel_button.setFont(QFont("Times New Roman", 18))
        self.control_cancel_button.setStyleSheet("QToolButton{border:none;color:rgb(0, 0, 0);}"
                                                 "QToolButton:hover{background-color: rgb(20, 62, 134);border:none;color:rgb(255, 255, 255);}"
                                                 "QToolButton:checked{background-color: rgb(20, 62, 134);border:none;color:rgb(255, 255, 255);}")
        self.control_cancel_button.clicked.connect(self.handle_control_cancel)
        self.init_control_list()
        self.control_confirm = False
        self.control_window.show()

    def handle_control_confirm(self):
        self.control_confirm = True
        self.control_window.close()
        self.client.remote_control(self.to_control_ip)
        print("close")

    def handle_control_cancel(self):
        self.control_confirm = False
        self.control_window.close()

    def init_control_list(self):
        n = len(self.client.clients)
        self.cs_group = QButtonGroup(self.control_window)
        self.to_control_ip = None
        for i in range(n):
            cs = QRadioButton(self.client.clients[i], self.control_window)
            cs.move(10, 10 + 40 * i)
            cs.resize(200, 40)
            cs.setFont(QFont("Times New Roman", 18))
            self.cs_group.addButton(cs)
        self.cs_group.buttonClicked.connect(self.handle_button_group)

    def handle_button_group(self):
        self.to_control_ip = self.cs_group.checkedButton().text()
        print(self.cs_group.checkedButton().text())

    def handle_invite_button(self):
        self.client.remote_control()
        # self.invite_window = QLineEdit()
        # self.invite_window.setText('The meeting id is')
        # self.invite_window.setStyleSheet("color: blue;"
        #                                  "background-color: yellow;"
        #                                  "selection-color: yellow;"
        #                                  "selection-background-color: blue;")
        # self.invite_window.setFixedSize(QSize(300, 50))
        # self.invite_window.setWindowTitle('Meeting Info')
        # self.invite_window.setFont(QFont("Times New Roman", 18))
        # self.invite_window.setReadOnly(True)
        # self.invite_window.show()

    def handle_more_button(self):
        print(1)

    def update_all_clients(self):
        num = len(self.client.clients)
        self.all_frames = {}
        for i in range(num):
            frame = QLabel(self.meeting_window)
            frame.resize(400, 400)
            if i < 3:
                frame.move(i * 400, 0)
            else:
                frame.move((i - 3) * 400, 400)
            image = Image.open('ui/user.png')
            image = image.resize((400, 400), Image.ANTIALIAS)
            pix = QPixmap.fromImage(ImageQt(image).copy())
            frame.setPixmap(pix)
            frame.show()
            self.all_frames.update({self.client.clients[i]:frame})

    def update_image(self, ip, frame):
        pix = None
        if frame is not None:
            frame = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            frame = frame.resize((400, 400), Image.ANTIALIAS)
            pix = QPixmap.fromImage(ImageQt(frame).copy())
        else:
            frame = Image.open('ui/user.png')
            frame = frame.resize((400, 400), Image.ANTIALIAS)
            pix = QPixmap.fromImage(ImageQt(frame).copy())
        self.all_frames[ip].setPixmap(pix)

    def handle_control_msg(self, ip):
        self.control_msg_window = QMainWindow()
        self.control_msg_window.setFixedSize(600, 200)
        self.resolution = QGuiApplication.primaryScreen().availableGeometry()
        self.control_msg_window.move((self.resolution.width() / 2) - (self.control_msg_window.frameSize().width() / 2),
                                     (self.resolution.height() / 2) - (
                                             self.control_msg_window.frameSize().height() / 2))
        self.control_msg_window.setWindowTitle('Control Message')
        self.msg_area = QLineEdit(self.control_msg_window)
        self.msg_area.setStyleSheet("color: blue;"
                                    "background-color: yellow;"
                                    "selection-color: yellow;"
                                    "selection-background-color: blue;")
        self.msg_area.setFixedSize(QSize(550, 50))
        self.msg_area.setWindowTitle('Meeting Info')
        self.msg_area.setFont(QFont("Times New Roman", 18))
        self.msg_area.setReadOnly(True)
        self.msg_area.move(25, 30)
        self.be_control_confirm_button = QPushButton(self.control_msg_window)
        self.be_control_confirm_button.setIconSize(QSize(50, 50))
        self.be_control_confirm_button.setText('Confirm')
        self.be_control_confirm_button.setFont(QFont("Times New Roman", 18))
        self.be_control_confirm_button.clicked.connect(self.handle_be_control_confirm)
        self.be_control_confirm_button.move(50, 90)
        self.be_control_confirm_button.resize(200, 80)
        self.be_control_confirm_button.setStyleSheet("QToolButton{border:none;color:rgb(0, 0, 0);}"
                                          "QToolButton:hover{background-color: rgb(20, 62, 134);border:none;color:rgb(255, 255, 255);}"
                                          "QToolButton:checked{background-color: rgb(20, 62, 134);border:none;color:rgb(255, 255, 255);}")
        self.be_control_cancel_button = QPushButton(self.control_msg_window)
        self.be_control_cancel_button.setIconSize(QSize(50, 50))
        self.be_control_cancel_button.setText('Confirm')
        self.be_control_cancel_button.setFont(QFont("Times New Roman", 18))
        self.be_control_cancel_button.clicked.connect(self.handle_be_control_cancel)
        self.be_control_cancel_button.move(300, 90)
        self.be_control_cancel_button.resize(200, 80)
        self.be_control_cancel_button.setStyleSheet("QToolButton{border:none;color:rgb(0, 0, 0);}"
                                         "QToolButton:hover{background-color: rgb(20, 62, 134);border:none;color:rgb(255, 255, 255);}"
                                         "QToolButton:checked{background-color: rgb(20, 62, 134);border:none;color:rgb(255, 255, 255);}")
        self.msg_area.setText('ip' + str(ip) +' wants to control your PC!')
        self.control_msg_window.show()

    def handle_be_control_confirm(self):
        self.client.sock.handle_confirm()
        self.control_msg_window.close()

    def handle_be_control_cancel(self):
        self.client.sock.handle_cancel()
        self.control_msg_window.close()

class MainWindow(QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()

    def closeEvent(self, event):
        print(1)
        event.accept()

class MeetingWindow(QMainWindow):
    def __init__(self):
        super(MeetingWindow, self).__init__()

    def closeEvent(self, event):
        print(2)
        event.accept()

# app = QApplication([])
# stats = Stats()
# stats.window.show()
# app.exec_()
