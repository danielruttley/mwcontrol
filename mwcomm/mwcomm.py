"""
Defines the Communicator wrapper class that handles updates to the microwave generator.
"""

import numpy as np
import pyvisa
import time

class Communicator():

    def __init__(self,ip='129.234.190.42'):
        """
        Parameters
        ----------
        ip : int
            the ip address of the microwave generator
        """
        self.ip = ip
        self.termination = '\r'
        self.rm = pyvisa.ResourceManager()
        # self.inst = self.rm.open_resource('TCPIP0::{}::inst0::INSTR'.format(self.ip))
        # print(rm.list_resources())

    def connect_to_instrument(self):
        self.inst = self.rm.open_resource('TCPIP0::{}::inst0::INSTR'.format(self.ip),write_termination=self.termination, read_termination=self.termination)

    def write(self,message,timeout=5000):
        print(message)
        try:
            self.connect_to_instrument()
            self.inst.timeout = timeout
            print(self.inst.write(message))
            print('sleeping for 1 second...')
            time.sleep(1)
        except Exception as e:
            print(e)
            self.connect_to_instrument()
            self.inst.write('?')
        self.inst.close()

    def query(self,message):
        try:
            self.connect_to_instrument()
            response = self.inst.query(message)
        except Exception as e:
            print(e)
        self.inst.close()
        return response