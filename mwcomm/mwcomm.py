"""
Defines the Communicator wrapper class that handles updates to the microwave generator.
"""

import numpy as np
import pyvisa

class Communicator():

    def __init__(self,ip='129.234.190.42'):
        """
        Parameters
        ----------
        ip : int
            the ip address of the microwave generator
        """
        self.ip = ip
        self.rm = pyvisa.ResourceManager()
        # print(rm.list_resources())

    def write(self,message,timeout=5000):
        try:
            self.inst = self.rm.open_resource('TCPIP0::{}::inst0::INSTR'.format(self.ip))
            print(message)
            self.inst.timeout = timeout
            self.inst.write(message)
        except Exception as e:
            print(e)
        self.inst.close()

    def query(self,message):
        try:
            self.inst = self.rm.open_resource('TCPIP0::{}::inst0::INSTR'.format(self.ip))
            response = self.inst.query(message)
        except Exception as e:
            print(e)
        self.inst.close()
        return response