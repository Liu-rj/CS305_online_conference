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

#receive data from server
def parse_data(raw_data):
    raw_data = raw_data.split(b'\r\n\r\n')
    header = raw_data[0]
    data = raw_data[1]
    return header, data

#Create a socket to handle incoming messages from clients' VedioSocket
def video_sock_listen():
    print('video socket start listen...')
    video_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    video_sock.bind((XXIP, XXVIDEOPORT))
    video_sock.listen(5)
    while True:
        sock, address = video_sock.accept()
        header, data, _ = receive_data(sock)
        print(f'video listener receive from {address}, header: {header}, data: {data}')
        room_id = int(data.split(' ')[1])
        with shared_lock:
            if room_id in ServerSocket.rooms.keys():
                print('new video client connect: {} to room {}, action: {}'.format(address, str(room_id), header))
                if header == 'share':
                    sock.send(b'200 OK\r\n\r\n ')
                    room = ServerSocket.rooms[room_id]
                    threading.Thread(target=room.video_receive, args=(sock,), daemon=True).start()
                elif header == 'receive':
                    ServerSocket.rooms[room_id].video_receiving.append((sock, address))
            else:  # TODO: if join a non-existing room, what should we do?
                print(f'{address} not pass test, header: {header}, data: {data}, rooms: {ServerSocket.rooms.keys()}')

#Create a socket to handle incoming messages from clients' AudioSocket
def audio_sock_listen():
    print('audio socket start listen...')
    audio_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    audio_sock.bind((XXIP, XXAUDIOPORT))
    audio_sock.listen(5)
    while True:
        sock, address = audio_sock.accept()
        header, data, _ = receive_data(sock)
        print(f'audio listener receive from {address}, header: {header}, data: {data}')
        room_id = int(data.split(' ')[1])
        with shared_lock:
            if room_id in ServerSocket.rooms.keys():
                print('new audio client connect: {} to room {}, action: {}'.format(address, str(room_id), header))
                if header == 'share':
                    sock.send(b'200 OK\r\n\r\n ')
                    room = ServerSocket.rooms[room_id]
                    threading.Thread(target=room.audio_receive, args=(sock, address[0]), daemon=True).start()
                elif header == 'receive':
                    ServerSocket.rooms[room_id].audio_receiving.append((sock, address))
            else:  # TODO: if join a non-existing room, what should we do?
                pass

#Create a socket to handle incoming messages from clients' ScreenSocket
def screen_sock_listen():
    print('screen socket start listen...')
    screen_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    screen_sock.bind((XXIP, XXSCREEENPORT))
    screen_sock.listen(5)
    while True:
        sock, address = screen_sock.accept()
        header, data, _ = receive_data(sock)
        print(f'screen listener receive from {address}, header: {header}, data: {data}')
        room_id = int(data.split(' ')[1])
        with shared_lock:
            if room_id in ServerSocket.rooms.keys():
                print('new screen client connect: {} to room {}, action: {}'.format(address, str(room_id), header))
                if header == 'share':
                    if len(ServerSocket.rooms[room_id].screen_sharing)==0:
                        ServerSocket.rooms[room_id].screen_sharing.append((sock, address))
                        sock.send(b'200 OK\r\n\r\n ')
                    else:
                        sock.send(b'500 Not\r\n\r\n ')
                        print("There is someone sharing screen!")
                elif header == 'receive':
                    ServerSocket.rooms[room_id].screen_receiving.append((sock, address))
                    sock.send(b'200 OK\r\n\r\n ')
            else:  # TODO: if join a non-existing room, what should we do?
                pass

#The main thread listens for new client to join
def main_sock_listen():
    print('main socket start listen...')
    video = threading.Thread(target=video_sock_listen)
    video.setDaemon(True)
    audio = threading.Thread(target=audio_sock_listen)
    audio.setDaemon(True)
    screen = threading.Thread(target=screen_sock_listen)
    screen.setDaemon(True)
    video.start()
    audio.start()
    screen.start()
    # Create a socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    # Bind the address
    sock.bind((XXIP, XXPORT))
    # Socket listen
    sock.listen(5)
    # Start to listen
    while True:
        # Wait for client to connect
        conn, address = sock.accept()
        client = (conn, address)
        server_socket = ServerSocket(client)
        # ServerSocket.clients[client] = server_socket
        server_socket.start()


if __name__ == "__main__":
    main_sock_listen()
