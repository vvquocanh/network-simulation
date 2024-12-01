import sys
import numpy as np
import random
import matplotlib
import matplotlib.pyplot as plt
from matplotlib import colors
import math

import pandas as pd
import simpy

import queue

simulation_duration = 100000
periodPrintLR = 100
df_lossRates = pd.DataFrame(columns=['sourceId', 'time', 'lossRate'])

torque = math.sqrt(simulation_duration)

np.random.seed(10)

def printLossRate(env, source):
    global df_lossRates
    source.cpterPrintLR += 1
    if source.cpterPrintLR == periodPrintLR:
        source.cpterPrintLR = 0
        #print("loss", env.now, source.ident, source.queueLosses/source.nbEmmissions)
        df_lossRates.loc[len(df_lossRates)] = {'sourceId':source.ident, 'time':env.now, 'lossRate': source.queueLosses/source.nbEmmissions}

def printConfidenceInterval(queue):
    standardDeviation = math.sqrt((1 / (queue.intervalCount - 1)) * (queue.zSquare - ((queue.z ** 2) / queue.intervalCount)))
    epsilonTorque = 4.5 * standardDeviation
    epsilonTotal = epsilonTorque * math.sqrt(torque / queue.env.now)
    lossRate = queue.packetLossTotal / queue.packetReceivedTotal

    df_lossRates.loc[len(df_lossRates)] = {'sourceId': 'ConfidenceIntervalUp', 'time': queue.env.now, 'lossRate': epsilonTotal + lossRate}
    df_lossRates.loc[len(df_lossRates)] = {'sourceId': 'ConfidenceIntervalDown', 'time': queue.env.now, 'lossRate': lossRate - epsilonTotal}

class packet(object):
    def __init__(self, t, ident, pktSize):
        self.t = t
        self.ident = ident
        self.pktSize = pktSize

class queueClass(object):
    def __init__(self, env, queueCapa, serviceRate):
        self.env = env
        self.inService = 0
        self.buffer = queue.Queue(maxsize=queueCapa)
        self.queueLength = 0
        self.queueCapacity = queueCapa
        self.serviceRate = serviceRate
        self.lastChange = 0
        self.cpterPrintLR = 0
        self.packetReceivedTotal = 0
        self.packetLossTotal = 0
        self.packetReceivedBlock = 0
        self.packetLossBlock = 0 
        self.intervalCount = 0
        self.z = 0  
        self.zSquare = 0

    def service(self):
        p = self.buffer.get()
        self.queueLength -= p.pktSize
        service_time = np.random.exponential(scale=1/self.serviceRate)
        yield self.env.timeout(service_time)
        #print('Process packet at: %d' % self.env.now)
        del p
        if self.queueLength > 0:
            self.env.process(self.service())
        else:
            self.inService = 0

    def reception(self, source, pkt):
        self.packetReceivedTotal += 1

        if  (self.env.now - torque * self.intervalCount) > torque:
            newZi = self.packetLossBlock / self.packetReceivedBlock
            self.z += newZi
            self.zSquare += newZi ** 2
            self.packetReceivedBlock = 0
            self.packetLossBlock = 0
            self.intervalCount += 1
            if self.intervalCount > 1:
                printConfidenceInterval(self)
                

        self.packetReceivedBlock += 1

        if self.queueLength + pkt.pktSize <= self.queueCapacity:
            self.queueLength += pkt.pktSize
            self.buffer.put(pkt)
            if self.inService == 0:
                self.inService = 1
                self.env.process(self.service())
        else:
            source.queueLosses += 1
            self.packetLossTotal += 1
            self.packetLossBlock += 1
            printLossRate(self.env, source)

class poissonSource(object):
    def __init__(self, env, rate, q, ident, pktSize):
        self.env = env
        self.rate = rate
        self.q = q
        self.ident = ident
        self.pktSize = pktSize
        self.nbEmmissions = 0
        self.queueLosses = 0
        self.cpterPrintLR = 0
        self.action = env.process(self.run())
    
    def run(self):
        while True:
            sending_time = np.random.exponential(scale=1/self.rate)
            yield self.env.timeout(sending_time)
            #print('Send packet at: %d' % self.env.now)
            self.nbEmmissions += 1
            p = packet(self.env.now, self.ident, self.pktSize)
            q.reception(self, p)

env = simpy.Environment()

q = queueClass(env, 10, 1.0)
ps1 = poissonSource(env, 0.1, q, 1, 1)
ps2 = poissonSource(env, 0.7, q, 2, 1)

env.run(until=simulation_duration)

plt.plot(df_lossRates[df_lossRates['sourceId'] == 1]['time'], df_lossRates[df_lossRates['sourceId'] == 1]['lossRate'], linewidth=1, label='Source 1')
plt.plot(df_lossRates[df_lossRates['sourceId'] == 2]['time'], df_lossRates[df_lossRates['sourceId'] == 2]['lossRate'], linewidth=1, label='Source 2')
plt.plot(df_lossRates[df_lossRates['sourceId'] == 'ConfidenceIntervalUp']['time'], df_lossRates[df_lossRates['sourceId'] == 'ConfidenceIntervalUp']['lossRate'], linewidth=1, label='Confidence Interval Up')
plt.plot(df_lossRates[df_lossRates['sourceId'] == 'ConfidenceIntervalDown']['time'], df_lossRates[df_lossRates['sourceId'] == 'ConfidenceIntervalDown']['lossRate'], linewidth=1, label='Confidence Interval Down')
plt.grid(True, which='both', linestyle='dotted')
plt.ylim(ymin=0)
plt.ylabel('Loss rate')
plt.xlabel('Time units')
plt.title('Loss rate in function of the time')
plt.legend()
plt.show()