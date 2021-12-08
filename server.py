from CONSTANTS import *
from server_sockets import *
import socket
import threading

'''
    The main server file implements the concurrency via multi-threading.
    You can only modify the total ports and related server socket initiation here.

    If you want to implement the concurrency with other methods,
    you can create a new file to replace this file.
'''


def video_sock_listen():
    print('video socket start listen...')
    video_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    video_sock.bind(('', XXVIDEOPORT))
    video_sock.listen(2)
    while True:
        sock, address = video_sock.accept()
        header, data, _ = receive_data(sock)
        room_id = int(data.split(' ')[1])
        if room_id in ServerSocket.rooms.keys():
            print('new video client connect: {} to room {}, action: {}'.format(address, str(room_id), header))
            sock.send(b'200 OK\r\n\r\n ')
            with shared_lock:
                if header == 'share':
                    ServerSocket.rooms[room_id].video_sharing.append((sock, address))
                elif header == 'receive':
                    ServerSocket.rooms[room_id].video_receiving.append((sock, address))
        else:  # TODO: if join a non-existing room, what should we do?
            pass


def audio_sock_listen():
    print('audio socket start listen...')
    audio_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    audio_sock.bind(('', XXAUDIOPORT))
    audio_sock.listen(2)
    while True:
        sock, address = audio_sock.accept()
        header, data, _ = receive_data(sock)
        room_id = int(data.split(' ')[1])
        if room_id in ServerSocket.rooms.keys():
            print('new audio client connect: {} to room {}, action: {}'.format(address, str(room_id), header))
            with shared_lock:
                if header == 'share':
                    ServerSocket.rooms[room_id].audio_sharing.append((sock, address))
                elif header == 'receive':
                    ServerSocket.rooms[room_id].audio_receiving.append((sock, address))
            sock.send(b'200 OK\r\n\r\n ')
        else:  # TODO: if join a non-existing room, what should we do?
            pass


def main_sock_listen():
    print('main socket start listen...')
    video = threading.Thread(target=video_sock_listen)
    video.setDaemon(True)
    audio = threading.Thread(target=audio_sock_listen)
    audio.setDaemon(True)
    video.start()
    audio.start()
    # Create a socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    # Bind the address
    sock.bind(('', XXPORT))
    # Socket listen
    sock.listen(2)
    # Start to listen
    while True:
        # Wait for client to connect
        conn, address = sock.accept()
        ServerSocket((conn, address)).start()


if __name__ == "__main__":
    main_sock_listen()
