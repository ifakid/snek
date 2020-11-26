# Grab packet one by one

import socket
import sys
import math
import time
import wave
import threading
from Packet import AudioPacket

connections = []
sender_socket = None
CHUNK_SIZE = 32767
FILE_NAME = ""
listening = True
packets = None


def keep_listening():
    global connections
    print(f"Listening on {sender_socket.getsockname()[1]}")
    while listening:
        try:
            received, client_addr = sender_socket.recvfrom(1024)
            sender_socket.settimeout(5)
            print(f"Received request from {client_addr}: {received}")
            rate = int.from_bytes(received, 'big')
            if rate > packets.frame_rate:
                rate = packets.frame_rate

            sender_socket.sendto(packets.get_meta(rate), client_addr)
            connections.append((client_addr, rate if received else None))
        except socket.timeout:
            pass


def send_files():
    global listening
    global packets
    f = wave.open(FILE_NAME, 'rb')

    n_channel = f.getnchannels()
    sample_width = f.getsampwidth()
    frame_rate = f.getframerate()

    frame_size = n_channel * sample_width
    frame_count_per_chunk = math.floor(CHUNK_SIZE / frame_size)

    chunk_time = 1000 * frame_count_per_chunk / frame_rate

    while packets.next_packet():
        start = int(round(time.time()*1000))
        for connection, rate in connections:
            sender_socket.sendto(packets.down_sample(rate)
                                 if rate else packets.get_current_packet(),
                                 connection)
        end = int(round(time.time()*1000))
        elapse = end-start
        if elapse < chunk_time:
            time.sleep((chunk_time-elapse)/1000)
    print("Stream's over!")
    listening = False


if __name__ == '__main__':
    if len(sys.argv) != 3:
        print("Usage: python sender.py port target_file")
        sys.exit()

    sender_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sender_socket.bind(('', int(sys.argv[1])))
    print(socket.gethostbyname(socket.gethostname()))
    FILE_NAME = sys.argv[2]
    packets = AudioPacket(FILE_NAME)

    listener = threading.Thread(target=keep_listening, daemon=True)
    listener.start()
    send_files()
    packets.file.close()

