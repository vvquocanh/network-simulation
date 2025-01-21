import csv
import simpy
import random
import queue
import math
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

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
    def __init__(self, env, queue, rate, result):
        self.env = env
        self.queue = queue
        self.rate = rate
        self.sent_packet = 0
        self.processed_packet = 0
        self.total_response_time = 0
        self.processed_packet_block = 0 
        self.response_time_block = 0
        self.interval_count = 0
        self.z = 0  
        self.z_square = 0
        self.result = result
        self.action = env.process(self.run())

    def run(self):
        pass

    def acknowledge(self, enter_time):
        self.processed_packet += 1
        self.result.total_processed_packet += 1
        new_response_time = self.env.now - enter_time
        self.total_response_time += new_response_time
        self.result.total_response_time += new_response_time
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

        self.result.check_confidence_interval(new_response_time)

    def get_average_response_time(self):
        if self.processed_packet <= 0:
            return 1

        return float(self.total_response_time / self.processed_packet)

    def calculate_confidence_interval(self):
        if self.interval_count <= 1: 
            return 1

        standard_deviation = math.sqrt((1 / (self.interval_count - 1)) * (self.z_square - (math.pow(self.z, 2) / self.interval_count)))
        epsilon_torque = 4.5 * standard_deviation
        epsilon_total = epsilon_torque * math.sqrt(block_size / self.env.now)

        return epsilon_total
    
    def get_total_processed_packet(self):
        return self.processed_packet
    
    def get_total_sent_packet(self):
        return self.sent_packet
    
class DataSource(Source):
    def run(self):
        while True:
            packet_size = self.get_packet_size()
            sending_time = np.random.exponential(packet_size / self.rate)
            yield self.env.timeout(sending_time)
            new_packet = Packet(self, packet_size)
            self.queue.reception(new_packet)
            self.sent_packet += 1
            self.result.total_sent_packet += 1
        
    def get_packet_size(self):
        percentage = random.randint(1, 100)
        if percentage <= 40:
            return 400
        elif percentage > 40 and percentage <= 70:
            return 4000
        else:
            return 12000
        
class VoiceSource(Source):
    def __init__(self, env, queue, packet_size, rate, result):
        super().__init__(env, queue, rate, result)
        self.packet_size = packet_size

    def run(self):
        sending_time = float(self.packet_size / self.rate)
        while True:
            yield self.env.timeout(sending_time)
            new_packet = Packet(self, self.packet_size)
            self.queue.reception(new_packet)
            self.sent_packet += 1    
            self.result.total_sent_packet += 1 

class VideoSource(Source):
    def __init__(self, env, queue, packet_size, burstiness, rate, on_time_average, result):
        super().__init__(env, queue, rate, result)
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
                    self.sent_packet += 1
                    self.result.total_sent_packet += 1
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

class Result(object):
    def __init__(self, env):
        self.env = env
        self.total_response_time = 0
        self.total_processed_packet = 0
        self.total_sent_packet = 0
        self.interval_count = 0
        self.z = 0
        self.z_square = 0

        self.processed_packet_block = 0
        self.response_time_block = 0

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
        if self.total_processed_packet <= 0:
            return 1

        return float(self.total_response_time / self.total_processed_packet)

    def calculate_confidence_interval(self):
        if self.interval_count <= 1: 
            return 1

        standard_deviation = math.sqrt((1 / (self.interval_count - 1)) * (self.z_square - (math.pow(self.z, 2) / self.interval_count)))
        epsilon_torque = 4.5 * standard_deviation
        epsilon_total = epsilon_torque * math.sqrt(block_size / self.env.now)

        return epsilon_total
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

def check_stopping_condition(env, burstiness, sources, result):
    while True:
        confidence_data_source = sources['Data Source'].calculate_confidence_interval() / sources['Data Source'].get_average_response_time()
        confidence_voice_source = sources['Voice Source'].calculate_confidence_interval() / sources['Voice Source'].get_average_response_time()
        confidence_video_source = sources['Video Source'].calculate_confidence_interval() / sources['Video Source'].get_average_response_time()
        confidence_total = result.calculate_confidence_interval() / result.get_average_response_time()

        print(f"Time {env.now:.2f}: Confidence Data Source: {confidence_data_source}")
        print(f"Time {env.now:.2f}: Confidence Voice Source: {confidence_voice_source}")
        print(f"Time {env.now:.2f}: Confidence Video Source: {confidence_video_source}")
        print(f"Time {env.now:.2f}: Confidence Total: {confidence_total}")

        if env.now < min_simulation_duration:
            yield env.timeout(block_size)
            continue

        if (
            confidence_data_source < confidence_threshold and
            confidence_voice_source < confidence_threshold and
            confidence_video_source < confidence_threshold and
            confidence_total < confidence_threshold
        ):
            data = [burstiness, env.now, 
                    sources['Data Source'].get_average_response_time(), 
                    sources['Voice Source'].get_average_response_time(), 
                    sources['Video Source'].get_average_response_time(), 
                    result.get_average_response_time(), 
                    sources['Data Source'].get_total_sent_packet(), 
                    sources['Voice Source'].get_total_sent_packet(), 
                    sources['Video Source'].get_total_sent_packet(), 
                    result.total_sent_packet, 
                    sources['Data Source'].get_total_processed_packet(), 
                    sources['Voice Source'].get_total_processed_packet(), 
                    sources['Video Source'].get_total_processed_packet(), 
                    result.total_processed_packet, 
                    confidence_data_source, 
                    confidence_voice_source, 
                    confidence_video_source,
                    confidence_total]
            
            write_to_file(data)
            print("Stopping simulation: All confidence intervals are below the threshold.")
            break

        yield env.timeout(block_size)  # Check every simulation time unit

def init_file():
    with open("data.csv", "w") as file:
        writer = csv.writer(file)
        writer.writerow(headers)

def write_to_file(data):
    with open("data.csv", "a") as file:
        writer = csv.writer(file)
        writer.writerow(data)

headers = ["burstiness", 
           "time",
           "data_response_time", 
           "voice_response_time", 
           "video_response_time", 
           "total_response_time", 
           "data_sent_packet", 
           "voice_sent_packet", 
           "video_sent_packet", 
           "total_sent_packet", 
           "data_processed_packet", 
           "voice_processed_packet", 
           "video_processed_packet", 
           "total_processed_packet", 
           "data_confidence_interval", 
           "voice_confidence_interval", 
           "video_confidence_interval",
           "total_confidence_interval"]

init_file()

min_simulation_duration = 1000
max_simulation_duration = 100000
block_size = 50
confidence_threshold = 0.05

for burstiness in np.arange(20.0, 101, 10):
    print(f"Burstiness: {burstiness}")

    env = simpy.Environment()
    result = Result(env)
    q = QueueClass(env, 100 * math.pow(10, 6))
    data_source = DataSource(env, q, 30 * math.pow(10, 6), result)
    voice_source = VoiceSource(env, q, 800, 20 * math.pow(10, 6), result)
    video_source = VideoSource(env, q, 8000, burstiness,30 * math.pow(10, 6), 0.001, result)
    
    sources = {
        "Data Source": data_source,
        "Voice Source": voice_source,
        "Video Source": video_source
    }

    proc = env.process(check_stopping_condition(env, burstiness, sources, result))

    env.run(until=proc)

    print("")


    