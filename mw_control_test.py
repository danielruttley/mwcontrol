import time
# import easy_scpi as scpi

# # Connect to an instrument
# inst = scpi.Instrument('TCPIP0::129.234.190.42')
# inst.sour.freq.cw(6000000000)

import pyvisa
rm = pyvisa.ResourceManager()
# print(rm.list_resources())
inst = rm.open_resource('TCPIP0::129.234.190.42::inst0::INSTR')
# inst.read_termination = '\r'
# inst.write_termination = '\r'
# inst.timeout = 10000
print(inst.query('*IDN?'))
# print(inst.query('*OPC?'))

# inst.close()
# time.sleep(5)
# inst.query(':SOUR:FREQ:CW?')
# inst.write(':DISP:TEXT:STAT OFF')

#%%

inst.write('F1 2.7 GH CF1')

#%% populate a frequency table with specific frequencies and powers

print('waiting')
# time.sleep(5)
freqs = [10,6]#,8] # frequencies in GHz
powers = [8,4,1] # powers in dBm

# create the strings to send to the generator
freqs_str = ''
powers_str = ''
for freq, power in zip(freqs,powers):
    freqs_str += '{} GH, '.format(freq)
    powers_str += '{} DM, '.format(power)
freqs_str = freqs_str[:-2]
powers_str = powers_str[:-2]

table_len = min([len(freqs),len(powers)])

inst.write('LST ELN0 ELI0000') # activate list mode, select list 0, index 0000
inst.write('LIB0000 LIE{:0>4}'.format(table_len-1)) # set list playback indicies start=0000, end=table_len-1
inst.write('LF {} LP {}'.format(freqs_str,powers_str)) # populate table
inst.write('MNT') # change trigger mode to manual so that each TTL moves onto the next freq
inst.write('LEA')
# inst.write('UP')
# inst.write('UP')

# while True:
#     time.sleep(2)
#     inst.write('UP')
#     print('.\n')