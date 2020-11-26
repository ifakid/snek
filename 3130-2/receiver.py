import socket
import sys
import pyaudio
from Packet import Packet
from queue import Queue
import threading

MAX_LENGTH = 32774
packet = Queue()
listening = True

HOST = "0.0.0.0"
PORT = int(sys.argv[1])
RATE = int(sys.argv[2]) if len(sys.argv) == 3 else None

RECEIVER_ADDR = (HOST, PORT)
receiver_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
receiver_socket.bind(RECEIVER_ADDR)
connection = receiver_socket.sendto(RATE.to_bytes(2, 'big') if RATE else b'', ('', 8000))

received, sender_addr = receiver_socket.recvfrom(MAX_LENGTH)
n_channel, sample_width, frame_rate = Packet.extractMeta(received)
audio = pyaudio.PyAudio()
print(f"Playing at {frame_rate} rate")
stream = audio.open(
    format=audio.get_format_from_width(sample_width),
    channels=n_channel,
    rate=frame_rate,
    output=True
)


def play_audio():
    global stream
    global listening
    print("Playing...")
    while listening:
        if not packet.empty():
            stream.write(packet.get())


player = threading.Thread(target=play_audio)
player.start()

try: 
    while True:
        received, sender_addr = receiver_socket.recvfrom(MAX_LENGTH)
        receiver_socket.settimeout(5)
        data = received[7:]
        packet.put(data)
except (socket.timeout, KeyboardInterrupt, SystemExit):
    print("Stream's over!")
    listening = False
    receiver_socket.close()
except Exception as e:
    print(e)
