import simpy
import random
import queue
import math
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

class queueClass(object):
    def __init__(self, env, service_rate):
        self.env = env
        self.service_rate = service_rate
        self.buffer = queue.Queue()
        self.in_service = 0

    def service(self):
        pkt = self.buffer.get()
        service_time = float(pkt.packet_size / self.service_rate)
        yield self.env.timeout(service_time) 
        pkt.acknowledge(self.env.now)
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

class DataSource(object):
    def __init__(self, env, queue, rate):
        self.env = env
        self.queue = queue
        self.rate = rate
        self.processed_packet = 0
        self.total_response_time = 0
        self.action = env.process(self.run())

    def run(self):
        while True:
            packet_size = self.get_packet_size()
            sending_time = float(packet_size / self.rate)
            yield self.env.timeout(sending_time)
            new_packet = packet(self, packet_size)
            self.queue.reception(new_packet)
        
    def get_packet_size(self):
        percentage = random.randint(1, 100)
        if percentage <= 40:
            return 400
        elif percentage > 40 and percentage <= 70:
            return 4000
        else:
            return 12000
        
class VoiceSource(object):
    def __init__(self, env, queue, packet_size, rate):
        self.env = env
        self.queue = queue
        self.packet_size = packet_size
        self.rate = rate
        self.processed_packet = 0
        self.total_response_time = 0
        self.action = env.process(self.run())

    def run(self):
        sending_time = float(self.packet_size / self.rate)
        while True:
            yield self.env.timeout(sending_time)
            new_packet = packet(self, self.packet_size)
            self.queue.reception(new_packet)            

class VideoSource(object):
    def __init__(self, env, queue, packet_size, burstiness, average_rate, on_time_average):
        self.env = env
        self.queue = queue
        self.packet_size = packet_size
        self.burstiness = burstiness
        self.average_rate = average_rate
        self.on_time_average = on_time_average
        self.processed_packet = 0
        self.total_response_time = 0
        self.action = env.process(self.run())
    
    def run(self):
        peak_rate = float(self.burstiness * self.average_rate)
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
                    new_packet = packet(self, self.packet_size)
                    self.queue.reception(new_packet)
            else:
                if self.env.now - init_time >= state_time:
                    is_on = True
                    state_time = np.random.exponential(self.on_time_average)
                    init_time = self.env.now
                else:
                    yield self.env.timeout(0.00001)


class packet(object):
    def __init__(self, source, packet_size):
        self.source = source
        self.packet_size = packet_size
        self.enter_time = 0

    def acknowledge(self, current_time):
        self.source.processed_packet += 1
        self.source.total_response_time += current_time - self.enter_time

df_response_time = pd.DataFrame(columns=['source_id', 'burstiness', 'response_time'])

for burstiness in np.arange(1.0, 11, 1):
    simulation_duration = 20

    env = simpy.Environment()

    q = queueClass(env, 100 * math.pow(10, 6))
    data_source = DataSource(env, q, 30 * math.pow(10, 6))
    voice_source = VoiceSource(env, q, 800, 20 * math.pow(10, 6))
    video_source = VideoSource(env, q, 8000, burstiness,30 * math.pow(10, 6), 0.001)

    env.run(until=simulation_duration)

    df_response_time.loc[len(df_response_time)] = {'source_id': 'data_source', 'burstiness': burstiness, 'response_time': float(data_source.total_response_time / data_source.processed_packet)}
    df_response_time.loc[len(df_response_time)] = {'source_id': 'voice_source', 'burstiness': burstiness, 'response_time': float(voice_source.total_response_time / voice_source.processed_packet)}
    df_response_time.loc[len(df_response_time)] = {'source_id': 'video_source', 'burstiness': burstiness, 'response_time': float(video_source.total_response_time / video_source.processed_packet)}
    df_response_time.loc[len(df_response_time)] = {'source_id': 'total', 'burstiness': burstiness, 'response_time': float((data_source.total_response_time + video_source.total_response_time + voice_source.total_response_time) / (data_source.processed_packet + voice_source.processed_packet + video_source.processed_packet))}

    print(f"Burstiness: {burstiness}")

plt.plot(df_response_time[df_response_time['source_id'] == 'data_source']['burstiness'], df_response_time[df_response_time['source_id'] == 'data_source']['response_time'], linewidth=1, label='Data Source')
plt.plot(df_response_time[df_response_time['source_id'] == 'voice_source']['burstiness'], df_response_time[df_response_time['source_id'] == 'voice_source']['response_time'], linewidth=1, label='Voice Source')
plt.plot(df_response_time[df_response_time['source_id'] == 'video_source']['burstiness'], df_response_time[df_response_time['source_id'] == 'video_source']['response_time'], linewidth=1, label='Video Source')
plt.plot(df_response_time[df_response_time['source_id'] == 'total']['burstiness'], df_response_time[df_response_time['source_id'] == 'total']['response_time'], linewidth=1, label='Total')
plt.grid(True, which='both', linestyle='dotted')
plt.ylim(ymin=0)
plt.ylabel('Response time')
plt.xlabel('Burstiness')
plt.title('Response time in function of the burstiness')
plt.legend()
plt.show()

    