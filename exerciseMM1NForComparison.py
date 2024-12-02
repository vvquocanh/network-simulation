import sys
import numpy as np
import random
import time
import simpy


simulationDuration =  10000000.0

np.random.seed(10)

class queueClass(object):   #a queue class is a buffer + a server
    def __init__(self, env, queueCapa, serviceRate):
        self.env = env
        self.inService = 0
        self.queueLength = 0
        self.queueCapacity = queueCapa
        self.serviceRate = serviceRate

    def service(self):
        self.inService = 1
        yield self.env.timeout(np.random.exponential(1.0/self.serviceRate))
        self.queueLength -= 1
        if self.queueLength > 0:
            self.env.process(self.service())
        else:
            self.inService = 0

    def reception(self,source):
        if self.queueLength + 1 <= self.queueCapacity:    
            self.queueLength += 1
            if self.inService == 0: 
                self.env.process(self.service())
        else:
            source.queueLosses += 1

            
class poissonSource(object):
        def __init__(self, env, rate, q):
            self.env = env
            self.rate = rate
            self.q = q ;# the queue
            self.nbEmissions= 0
            self.queueLosses = 0
            self.action = env.process(self.run())

        def run(self):
            while True:
                yield self.env.timeout(np.random.exponential(scale = 1.0/(self.rate)))
                self.nbEmissions += 1
                self.q.reception(self)
                

start_time = time.time()

env = simpy.Environment()

q = queueClass(env,10,1.0)
ps1 = poissonSource(env,0.9,q)


env.run(until=simulationDuration)

end_time = time.time()

print("(physical) duration of the simulation:", end_time - start_time)
print("Loss rate:",ps1.queueLosses*1.0/ps1.nbEmissions)


