# Multi-person Online Conference

This is the repo for a simple multi-person online conference based on client-server model currently via TCP.

## How to run?

* Alter the __XXIP__ to your desktop IPv4 address in `CONSTANTS.py ` for both client and server.
* In the terminal, cd to the server directory, run the command `python server.py`
* In another terminal, cd to the client directory, run the command `python client.py`
* Then happy conferencing!

During the conference, you can:

* Create a room, get a room id
* Join a room with a room id
* Open or close audio
* Open or close video
* Share your screen to others
* Request remote control to others
* Invite: show the room info (room id currently)

If you are a host, you can:

* Transfer you host privilege to another conferee
* Assign other conferees to be administrators
* End the whole meeting

If you are a administrator, you can:

* End the whole meeting

## Further information

for further information, please refer to the report.pdf where the detailed structure, protocol and mechanism are shown.
