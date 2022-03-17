# from multiprocessing.sharedctypes import Value
import sys
import os
import numpy as np
import threading
os.system("color")
import inspect

#from qtpy.QtCore import QThread,Signal,Qt
from qtpy.QtCore import Qt
from qtpy.QtWidgets import (QApplication,QMainWindow,QVBoxLayout,QWidget,
                            QAction,QListWidget,QFormLayout,QComboBox,QLineEdit,
                            QTextEdit,QPushButton,QFileDialog,QAbstractItemView,
                            QTableWidget,QTableWidgetItem,QLabel)
from qtpy.QtGui import QIcon,QIntValidator,QDoubleValidator,QColor

from . import qrc_resources
from .networking.client import PyClient
from .strtypes import error, warning, info

from mwcomm import Communicator

if __name__ == '__main__':
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class MainWindow(QMainWindow):
    def __init__(self,dev_mode=False):
        super().__init__()
        if dev_mode:
            self.tcp_client = PyClient(host='localhost',port=9000,name='mwcontrol')
        else:
            self.tcp_client = PyClient(host='129.234.190.164',port=9000,name='mwcontrol')
        self.tcp_client.start()
        self.last_MWparam_folder = '.'
        self.num_freqs = 0
        self.comm = Communicator()

        self.data = {'freq (MHz)': [6000],
                     'amp (dBm)': [8]}

        self.setWindowTitle("microwave control")
        self.layout = QVBoxLayout()

        widget = QWidget()
        widget.setLayout(self.layout)
        self.setCentralWidget(widget)

        self._createNumberRowsBox()

        self.freqTable = QTableWidget()
        self.freqTable.setRowCount(10)
        self.freqTable.setColumnCount(5)
        self.populate_table()
        self.layout.addWidget(self.freqTable)

        self._createSendButton()

        self._createActions()
        self._createMenuBar()
        # self._createToolBars()
        # self._createContextMenu()
        self._connectActions()

    def _createNumberRowsBox(self):
        layout = QFormLayout()
        self.num_rows_box = QLineEdit()
        self.num_rows_box.setValidator(QIntValidator())
        self.num_rows_box.setText(str(self.get_num_freqs()))
        layout.addRow(QLabel('# rows'),self.num_rows_box)
        self.freq_equation_box = QLineEdit()
        layout.addRow(QLabel('freq. eqn.'),self.freq_equation_box)
        self.amp_equation_box = QLineEdit()
        layout.addRow(QLabel('amp. eqn.'),self.amp_equation_box)
        self.layout.addLayout(layout)

    def _createSendButton(self):
        self.send_button = QPushButton()
        self.send_button.setText('send to MW gen.')
        self.layout.addWidget(self.send_button)

    def _createActions(self):
        self.loadParamsAction = QAction(self)
        self.loadParamsAction.setText("Load MWparam")

        self.saveParamsAction = QAction(self)
        self.saveParamsAction.setText("Save MWparam")

    def _createMenuBar(self):
        menuBar = self.menuBar()
        mainMenu = menuBar.addMenu("Menu")
        mainMenu.addAction(self.loadParamsAction)
        mainMenu.addAction(self.saveParamsAction)

    def _connectActions(self):
        self.freqTable.itemChanged.connect(self.update_data)
        self.num_rows_box.textEdited.connect(self.update_data)
        self.freq_equation_box.returnPressed.connect(self.evaluate_freqs)
        self.amp_equation_box.returnPressed.connect(self.evaluate_amps)
        self.loadParamsAction.triggered.connect(self.load_params_file_dialogue)
        self.saveParamsAction.triggered.connect(self.save_params_file_dialogue)
        self.send_button.pressed.connect(self.send_data)

    def get_num_freqs(self):
        return len(self.data[list(self.data.keys())[0]])

    def populate_table(self):
        self.freqTable.blockSignals(True)
        try:
            num_rows = int(self.num_rows_box.text())
        except ValueError:
            pass
        else:
            print(num_rows)
            self.num_freqs = len(self.data[list(self.data.keys())[0]])
            if num_rows > self.num_freqs:
                 for key in self.data.keys():
                     self.data[key] = self.data[key][:num_rows]
            self.freqTable.setRowCount(num_rows)
            self.freqTable.setColumnCount(len(list(self.data.keys())))
            headers = []
            rows = ['{:0>4}'.format(x) for x in range(num_rows)]
            for n, key in enumerate((self.data.keys())):
                headers.append(key)
                for m in range(num_rows):
                    if key == 'freq (MHz)':
                        newVal = QTableWidgetItem(str(1000))
                    else:
                        newVal = QTableWidgetItem(str(0))
                    self.freqTable.setItem(m, n, newVal)
                for m, item in enumerate(self.data[key]):
                    if m < num_rows:
                        newVal = QTableWidgetItem(str(item))
                        self.freqTable.setItem(m, n, newVal)
            self.freqTable.setHorizontalHeaderLabels(headers)
            self.freqTable.setVerticalHeaderLabels(rows)
            if num_rows != self.get_num_freqs():
                self.update_data()
        self.freqTable.blockSignals(False)

    def update_data(self):
        column_count = self.freqTable.columnCount()
        row_count = self.freqTable.rowCount()
        new_data = {}
        try:
            for column in range(column_count):
                key = self.freqTable.horizontalHeaderItem(column).text()
                values = []
                for row in range(row_count):
                    values.append(float(self.freqTable.item(row,column).text()))
                new_data[key] = [float(x) for x in values]
            self.data = new_data
        except ValueError as e:
            error('All cells must be populated with float values. Data will be left unchanged.',e)
        self.populate_table()
        print(self.data)

    def send_data(self):
        num_freqs = self.get_num_freqs()
        # print(self.comm.query('*IDN?'))
        if num_freqs < 1:
            print('no freqs!')
        elif num_freqs == 1:
            freq = self.data['freq (MHz)'][0]
            power = self.data['amp (dBm)'][0]
            send_str = 'F1 {} HZ P1 {} DM CF1'.format(int(freq*1e6),int(power))
            send_str = 'CF0 {} HZ L0 {} DM'.format(int(freq*1e6),int(power))
            # self.comm.write(':FREQ:MODE CW')
            # send_str = ':FREQ {} MHz'.format(freq)
            # self.comm.write(send_str)
            # send_str = ':POW {} dBm'.format(power)
            self.comm.write(send_str)
            
        else:
            freqs_str = ''
            powers_str = ''
            for freq, power in zip(self.data['freq (MHz)'],self.data['amp (dBm)']):
                freqs_str += '{:.7f} GH, '.format(freq/1e3)
                powers_str += '{:.2f} DM, '.format(power)
            freqs_str = freqs_str[:-2]
            powers_str = powers_str[:-2]
            data_str = 'LF {} LP {} '.format(freqs_str,powers_str)
            
            #Note that these can't all be send together otherwise a timeout error occurs and nothing happens on the MW gen.
            # self.comm.write('CF0 6 GZ L0 8 DM') # go back into CW mode whilst the params are being loaded. Seems to prevent some crashes on the gen.
            
            
            # self.comm.write('LST')
            # self.comm.write('EXT')
            # self.comm.write('ELN0') # activate list mode, select list 0, index 0000
            # self.comm.write('ELI0000') # activate list mode, select list 0, index 0000
            # self.comm.write('LIB0000') # set list playback indicies start=0000, end=table_len-1
            # self.comm.write('LIE{:0>4}'.format(num_freqs-1)) # set list playback indicies start=0000, end=table_len-1
            # self.comm.write('LF {}'.format(freqs_str)) # populate table
            # self.comm.write('LP {}'.format(powers_str)) # populate table
            # self.comm.write('LEA') # calculate list
            # self.comm.write('MNT') # change trigger mode to manual so that each TTL moves onto the next freq
            
            send_str = ('LST EXT ELN0 ELI0000 LIB0000 LIE{:0>4} LF {} LP {} LEA MNT'.format(num_freqs-1,freqs_str,powers_str))
            self.comm.write(send_str,timeout=10000000)
            
            info('Frequencies loaded into microwave generator.')
            # print(send_str)
            # send_str = 'LST ELN0 ELI0000 LIB0000 LIE0002 LF 3000000001 HZ, 6000000001 HZ, 5000000001 HZ LP 8 DM, 5 DM, 2 DM MNT LEA'
            
            # freqs_str = ''
            # powers_str = ''
            # for freq, power in zip(self.data['freq (MHz)'],self.data['amp (dBm)']):
            #     freqs_str += '{} Hz, '.format(int(freq*1e6))
            #     powers_str += '{} dBm, '.format(int(power))
            # freqs_str = freqs_str[:-2]
            # powers_str = powers_str[:-2]
            # # data_str = 'LF {} LP {} '.format(freqs_str,powers_str)
            
            # self.comm.write(':TRIG:SOUR HOLD')
            # self.comm.write(':FREQ:MODE LIST')
            # self.comm.write(':LIST:IND 0')
            # self.comm.write(':LIST:FREQ {}'.format(freqs_str))
            # self.comm.write(':LIST:POW {}'.format(powers_str))
            # self.comm.write(':LIST:STAR 0')
            # self.comm.write(':LIST:STOP {}'.format(num_freqs-1))

            # print(send_str)
            # self.comm.write(send_str)

    def evaluate_freqs(self):
        try:
            try:
                freqs = list(eval(self.freq_equation_box.text()))
            except TypeError:
                freqs = [eval(self.freq_equation_box.text())]*self.freqTable.rowCount()
        except Exception as e:
            error('Amplitudes could not be evaluated.',e)
        else:
            self.data['freq (MHz)'] = freqs
            self.populate_table()
            
    def evaluate_amps(self):
        try:
            try:
                amps = list(eval(self.amp_equation_box.text()))
            except TypeError:
                amps = [eval(self.amp_equation_box.text())]*self.freqTable.rowCount()
        except Exception as e:
            error('Amplitudes could not be evaluated.',e)
        else:
            self.data['amp (dBm)'] = amps
            self.populate_table()

    def save_params_file(self,filename):
        msg = self.data
        with open(filename, 'w') as f:
            f.write(str(msg))
        info('MWparams saved to "{}"'.format(filename))

    def save_params_file_dialogue(self):
        filename = QFileDialog.getSaveFileName(self, 'Save MWparam',self.last_MWparam_folder,"Text documents (*.txt)")[0]
        if filename != '':
            self.save_params_file(filename)
            self.last_MWparam_folder = os.path.dirname(filename)
            print(self.last_MWparam_folder)

    def recieved_tcp_msg(self,msg):
        info('TCP message recieved: "'+msg+'"')
        split_msg = msg.split('=')
        command = split_msg[0]
        arg = split_msg[1]
        if command == 'save':
            pass
        elif command == 'save_all':
            self.save_params_file(arg)
        elif command == 'load_all':
            self.load_params_file(arg)
        elif command == 'set_data':
            for update in eval(arg):
                    ind,arg_name,arg_val = update
                    info('Updating frequency {:0>4} with {} = {}'.format(ind,arg_name,arg_val))
                    try:
                        arg_val = float(arg_val)
                    except ValueError as e:
                        error('Value must be a float values. Data will be left unchanged.',e)
                    else:
                        try:
                            self.data[arg_name][ind] = arg_val
                            self.populate_table()
                        except IndexError as e: 
                            error('Frequency {:0>4} does not exist\n'.format(ind),e)
                        except KeyError as e: 
                            error('Argument {} does not exist\n'.format(arg_name),e)
    
    def load_params_file_dialogue(self):
        filename = QFileDialog.getOpenFileName(self, 'Load MWparam',self.last_MWparam_folder,"Text documents (*.txt)")[0]
        if filename != '':
            self.load_params_file(filename)
            self.last_MWparam_folder = os.path.dirname(filename)

    def load_params_file(self,filename):
        try:
            with open(filename, 'r') as f:
                msg = f.read()
        except FileNotFoundError:
            error('"{}" does not exist'.format(filename))
            return
        try:
            msg = eval(msg)
            self.data = msg
            self.populate_table()
            info('MWparam and holograms loaded from "{}"'.format(filename))
        except (SyntaxError, IndexError) as e:
            error('Failed to evaluate file "{}". Is the format correct?'.format(filename),e)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    app.exec()