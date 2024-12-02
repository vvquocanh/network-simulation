import simpy
import random
import queue
import math
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

simulation_duration = 100
block_size = math.sqrt(simulation_duration)

class QueueClass(object):
    def __init__(self, env, service_rate):
        self.env = env
        self.service_rate = service_rate
        self.buffer = queue.Queue()
        self.in_service = 0

    def service(self):
        pkt = self.buffer.get()
        service_time = float(pkt.packet_size / self.service_rate)
        yield self.env.timeout(service_time) 
        pkt.acknowledge()
        del pkt

        if self.buffer.qsize() > 0:
            self.env.process(self.service())
        else:
            self.in_service = 0

    def reception(self, pkt):
        self.buffer.put(pkt)
        pkt.enter_time = self.env.now
        if self.in_service == 0:
            self.in_service = 1
            self.env.process(self.service())

class Source(object):
    def __init__(self, env, queue, rate):
        self.env = env
        self.queue = queue
        self.rate = rate
        self.processed_packet = 0
        self.total_response_time = 0
        self.processed_packet_block = 0 
        self.response_time_block = 0
        self.interval_count = 0
        self.z = 0  
        self.z_square = 0
        self.action = env.process(self.run())

    def run(self):
        pass

    def acknowledge(self, enter_time):
        self.processed_packet += 1
        new_response_time = self.env.now - enter_time
        self.total_response_time += new_response_time
        self.check_confidence_interval(new_response_time)

    def check_confidence_interval(self, new_response_time):
        if  (self.env.now - block_size * self.interval_count) > block_size:
            new_zi = self.response_time_block / self.processed_packet_block
            self.z += new_zi
            self.z_square += math.pow(new_zi, 2)
            self.processed_packet_block = 0
            self.response_time_block = 0
            self.interval_count += 1

        self.processed_packet_block += 1
        self.response_time_block += new_response_time

    def get_average_response_time(self):
        return float(self.total_response_time / self.processed_packet)

    def calculate_confidence_interval(self):
        standard_deviation = math.sqrt((1 / (self.interval_count - 1)) * (self.z_square - (math.pow(self.z, 2) / self.interval_count)))
        epsilon_torque = 4.5 * standard_deviation
        epsilon_total = epsilon_torque * math.sqrt(block_size / simulation_duration)

        return epsilon_total
class DataSource(Source):
    def run(self):
        while True:
            packet_size = self.get_packet_size()
            sending_time = np.random.exponential(packet_size / self.rate)
            yield self.env.timeout(sending_time)
            new_packet = Packet(self, packet_size)
            self.queue.reception(new_packet)
        
    def get_packet_size(self):
        percentage = random.randint(1, 100)
        if percentage <= 40:
            return 400
        elif percentage > 40 and percentage <= 70:
            return 4000
        else:
            return 12000
        
class VoiceSource(Source):
    def __init__(self, env, queue, packet_size, rate):
        super().__init__(env, queue, rate)
        self.packet_size = packet_size

    def run(self):
        sending_time = float(self.packet_size / self.rate)
        while True:
            yield self.env.timeout(sending_time)
            new_packet = Packet(self, self.packet_size)
            self.queue.reception(new_packet)     

class VideoSource(Source):
    def __init__(self, env, queue, packet_size, burstiness, rate, on_time_average):
        super().__init__(env, queue, rate)
        self.packet_size = packet_size
        self.burstiness = burstiness
        self.on_time_average = on_time_average
    
    def run(self):
        peak_rate = float(self.burstiness * self.rate)
        sending_time = float(self.packet_size / peak_rate)
        off_time_average = float(self.burstiness * self.on_time_average) - self.on_time_average
        is_on = True
        state_time = np.random.exponential(self.on_time_average)
        init_time = self.env.now
        while True:
            if is_on:
                if self.env.now - init_time >= state_time:
                    is_on = False
                    state_time = np.random.exponential(off_time_average)
                    init_time = self.env.now
                else:
                    yield self.env.timeout(sending_time)
                    new_packet = Packet(self, self.packet_size)
                    self.queue.reception(new_packet)
            else:
                if self.env.now - init_time >= state_time:
                    is_on = True
                    state_time = np.random.exponential(self.on_time_average)
                    init_time = self.env.now
                else:
                    yield self.env.timeout(0.00001)


class Packet(object):
    def __init__(self, source, packet_size):
        self.source = source
        self.packet_size = packet_size
        self.enter_time = 0

    def acknowledge(self):
        self.source.acknowledge(self.enter_time)

class PandaFrameResponseTime(object):
    def __init__(self):
        self.source_id_column = "source_id"
        self.burstiness_column = "burstiness"
        self.response_time_column = "response_time"

        self.df = pd.DataFrame(columns=[self.source_id_column, self.burstiness_column, self.response_time_column])

    def add_data(self, source_id, burstiness, response_time):
        self.df.loc[len(self.df)] = {self.source_id_column: source_id, self.burstiness_column: burstiness, self.response_time_column: response_time}

    def print_data(self, source_id):
        plt.plot(self.df[self.df[self.source_id_column] == source_id][self.burstiness_column], self.df[self.df[self.source_id_column] == source_id][self.response_time_column], linewidth=1, label=source_id)

df_response_time = PandaFrameResponseTime()
df_confidence_interval = PandaFrameResponseTime()

for burstiness in np.arange(1.0, 11, 1):
    env = simpy.Environment()

    q = QueueClass(env, 100 * math.pow(10, 6))
    data_source = DataSource(env, q, 30 * math.pow(10, 6))
    voice_source = VoiceSource(env, q, 800, 20 * math.pow(10, 6))
    video_source = VideoSource(env, q, 8000, burstiness,30 * math.pow(10, 6), 0.001)

    env.run(until=simulation_duration)

    df_response_time.add_data("Data Source", burstiness, data_source.get_average_response_time())
    df_response_time.add_data("Voice Source", burstiness, voice_source.get_average_response_time())
    df_response_time.add_data("Video Source", burstiness, video_source.get_average_response_time())

    print(f"Confidence Data Source: {data_source.calculate_confidence_interval() / data_source.get_average_response_time()}")
    print(f"Confidence Voice Source: {voice_source.calculate_confidence_interval() / voice_source.get_average_response_time()}")
    print(f"Confidence Video Source: {video_source.calculate_confidence_interval() / video_source.get_average_response_time()}")

    df_confidence_interval.add_data("Data Source Up", burstiness, data_source.calculate_confidence_interval() + data_source.get_average_response_time())
    df_confidence_interval.add_data("Data Source Down", burstiness, - data_source.calculate_confidence_interval() + data_source.get_average_response_time())
    df_confidence_interval.add_data("Voice Source Up", burstiness, voice_source.calculate_confidence_interval() + voice_source.get_average_response_time())
    df_confidence_interval.add_data("Voice Source Down", burstiness, - voice_source.calculate_confidence_interval() + voice_source.get_average_response_time())
    df_confidence_interval.add_data("Video Source Up", burstiness, video_source.calculate_confidence_interval() + video_source.get_average_response_time())
    df_confidence_interval.add_data("Video Source Down", burstiness, - video_source.calculate_confidence_interval() + video_source.get_average_response_time())

    print(f"Burstiness: {burstiness}")

response_time_figure = plt.figure(1)
df_response_time.print_data("Data Source")
df_response_time.print_data("Voice Source")
df_response_time.print_data("Video Source")
plt.grid(True, which='both', linestyle='dotted')
plt.ylim(ymin=0)
plt.ylabel('Response time')
plt.xlabel('Burstiness')
plt.title('Response time in function of the burstiness')
plt.legend()
response_time_figure.show()

confidence_interval_figure = plt.figure(2)
df_confidence_interval.print_data("Data Source Up")
df_confidence_interval.print_data("Data Source Down")
df_confidence_interval.print_data("Voice Source Up")
df_confidence_interval.print_data("Voice Source Down")
df_confidence_interval.print_data("Video Source Up")
df_confidence_interval.print_data("Video Source Down")
plt.grid(True, which='both', linestyle='dotted')
plt.ylim(ymin=0)
plt.ylabel('Response time')
plt.xlabel('Burstiness')
plt.title('Confidence interval')
plt.legend()
confidence_interval_figure.show()

input()


    