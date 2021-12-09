import time
import tkinter

from client import Client
import sys


if __name__ == "__main__":
    # init server info
    client = Client()
    status = client.login()
    if status:
        print('successfully login!')
        client.join_meeting(0)
    # show_btn = tkinter.Button(root, text="Show", command=Client.screen_receiving)
    # show_btn.grid(row=2, column=1, padx=0, pady=10, ipadx=30, ipady=0)
    # root.mainloop()
    while True:
        time.sleep(1)
        if not client.is_alive:
            print("Video connection lost...")
            sys.exit(0)
    # # A CIL menu loop
    # while True:
    #     if client.changed and client.state == MAIN:
    #         client.changed = False
    #         # Main menu
    #         print("1. Create a meeting")
    #         print("2. Join a meeting")
    #         action = input("Action:")
    #         client.action(action)
    #     elif client.changed and client.state == MEETING:
    #         client.changed = False
    #         print("You are in the meeting: %d" % client.sid)
    #         # meeting menu
    #         print("1. (Stop) Share screen")
    #         print("2. (Stop) Control other's screen")
    #         print("3. (Stop) Control my screen")
    #         print("4. (Stop) Share video")
    #         print("5. (Stop) Share audio")
    #         print("6. Leave a meeting")
    #         print("7. Show current meeting members")
    #         action = input("Action:")
    #         client.action(action)
