import struct
import wave
import math
import audioop


class PacketType:
    DATA = b"\x00"
    ACK = b"\x01"
    FIN = b"\x02"
    FINACK = b"\x03"
    META = b"\x04"
    METAACK = b"\x05"


class Packet:
    def __init__(self, tipe: bytes, length: int, seq_num: int, data):
        self.setType(tipe)
        self.setLength(length)
        self.setLengthB()
        self.setSeqNum(seq_num)
        self.setData(data)
        self.setCheckSum()
        self.setPacket()

    def setType(self, _type):
        self.type = struct.pack('s', _type)

    def setLength(self, _length):
        self.length = _length

    def setLengthB(self):
        self.lengthB = struct.pack(
            '2s', (self.length).to_bytes(2, byteorder="big"))

    def setSeqNum(self, _seqnum):
        self.seq_num = struct.pack('2s', _seqnum.to_bytes(2, byteorder="big"))

    def setCheckSum(self):
        # packet with dummy checksum
        prototype_packet = struct.pack('s2s2s2s{}s'.format(
            self.length), self.type, self.lengthB, self.seq_num, b'\x00\x00', self.data)

        self.checksum = Packet.calcCheckSum(prototype_packet)

    def setData(self, _data):
        if (len(_data) > 32767):
            raise Exception("Data segmentation too big.")

        self.data = struct.pack('{}s'.format(self.length), _data)

    def setPacket(self):
        self.packet = struct.pack('s2s2s2s{}s'.format(
            self.length), self.type, self.lengthB, self.seq_num, self.checksum, self.data)

    @staticmethod
    def calcCheckSum(packet):

        tipe = int.from_bytes(bytes(1) + packet[:1], byteorder="big")
        length = int.from_bytes(packet[1:3], byteorder="big")
        seq_num = int.from_bytes(packet[3:5], byteorder="big")
        data = int.from_bytes(packet[7:], byteorder="big")

        checksum = tipe ^ length ^ seq_num

        while (data):
            # print(data)
            tempData = data & 0xffff
            checksum = tempData ^ checksum
            data = data >> 16

        return checksum.to_bytes(2, byteorder="big")

    @staticmethod
    # Print iterations progress
    def printProgressBar(iteration, total, prefix='', suffix='', decimals=1, length=100, fill='█', printEnd="\r"):
        """
        Call in a loop to create terminal progress bar
        @params:
            iteration   - Required  : current iteration (Int)
            total       - Required  : total iterations (Int)
            prefix      - Optional  : prefix string (Str)
            suffix      - Optional  : suffix string (Str)
            decimals    - Optional  : positive number of decimals in percent complete (Int)
            length      - Optional  : character length of bar (Int)
            fill        - Optional  : bar fill character (Str)
            printEnd    - Optional  : end character (e.g. "\r", "\r\n") (Str)
        """
        percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
        filledLength = int(length * iteration // total)
        bar = fill * filledLength + '-' * (length - filledLength)
        print(f'\r{prefix} |{bar}| {percent}% {suffix}', end=printEnd)
        # Print New Line on Complete
        if iteration == total:
            print()

    # Isi meta :
    # samplewidth, framerate, nchannel

    @staticmethod
    def wavToPackets(filename):
        with wave.open(filename, 'rb') as f:
            count = 1
            packets = []
            chunk_size = 32767
            sampwidth = f.getsampwidth()
            framerate = f.getframerate()
            nchannel = f.getnchannels()
            nframe = f.getnframes()
            frame_size = nchannel * sampwidth
            frame_count_per_chunk = math.floor(chunk_size/frame_size)

            meta = Packet.getMeta(f)
            packets.append(meta)

            while f.tell() < nframe:
                buffer = f.readframes(frame_count_per_chunk)
                packet = Packet(PacketType.DATA, len(
                    buffer), count, buffer).packet
                packets.append(packet)
                count += 1
                Packet.printProgressBar((count-1)*frame_count_per_chunk, nframe)
        return packets

    @staticmethod
    def getMeta(wav, rate=None):
        sampwidth = wav.getsampwidth()
        framerate = rate or wav.getframerate()
        nchannel = wav.getnchannels()

        b_nchannel = struct.pack(
            '2s', nchannel.to_bytes(2, byteorder='big'))
        b_sampwidth = struct.pack(
            '2s', sampwidth.to_bytes(2, byteorder='big'))
        b_framerate = struct.pack(
            '4s', framerate.to_bytes(4, byteorder='big'))

        b_meta = struct.pack('2s2s4s', b_nchannel,
                             b_sampwidth, b_framerate)

        meta = Packet(PacketType.META, len(b_meta), 0, b_meta).packet

        return meta

    @staticmethod
    def extractMeta(packet):
        nchannel = int.from_bytes(packet[7:9], byteorder="big")
        sampwidth = int.from_bytes(packet[9:11], byteorder="big")
        framerate = int.from_bytes(packet[11:15], byteorder="big")

        return nchannel, sampwidth, framerate


class AudioPacket:
    def __init__(self, file_name):
        self.file_name = file_name
        self.packet = None
        self.file = wave.open(self.file_name, 'rb')
        self.sample_width = self.file.getsampwidth()
        self.frame_rate = self.file.getframerate()
        self.n_channel = self.file.getnchannels()
        self.frame_size = self.n_channel * self.sample_width
        self.frame_count_per_chunk = math.floor(32767 / self.frame_size)
        self.count = 1
        self.buffer = None

    def next_packet(self):
        if self.file.tell() < self.file.getnframes():
            self.buffer = self.file.readframes(self.frame_count_per_chunk)
            self.count += 1
            return True
        else:
            return False

    def get_current_packet(self, rate=None):
        if rate:
            converted = self.down_sample(rate)
            return Packet(PacketType.DATA, len(converted), self.count, converted).packet
        return Packet(PacketType.DATA, len(self.buffer), self.count, self.buffer).packet

    def get_meta(self, rate=None):
        return Packet.getMeta(self.file, rate)

    def down_sample(self, to_rate):
        packet = audioop.ratecv(self.buffer, self.sample_width, self.n_channel, self.frame_rate, to_rate, None)[0]
        return Packet(PacketType.DATA, len(packet), self.count, packet).packet
