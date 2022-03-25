# from multiprocessing.sharedctypes import Value
import sys
import os
import numpy as np
import threading
import time
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
from .networking.server import PyServer
from .strtypes import error, warning, info

from mwcomm import Communicator

if __name__ == '__main__':
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class MainWindow(QMainWindow):
    def __init__(self,dev_mode=False):
        super().__init__()
        self.tcp_client = PyClient(host='129.234.190.164',port=8631,name='mwcontrol')
        # self.tcp_client = PyClient(host='localhost',port=8631,name='MWG')
        self.tcp_client.start()

        self.tcp_server = PyServer(host='', port=8632, name='MWG recv') # MW generator resumes PyDex when loaded
        self.tcp_server.start()

        self.last_MWGparam_folder = '.'
        self.num_freqs = 0
        self.comm = Communicator()

        self.data = {'freq (MHz)': [6000],
                     'amp (dBm)': [8]}

        self.setWindowTitle("MWG control")
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

        self.load_params_file('./gui/default_MWGparam.txt')

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
        self.loadParamsAction.setText("Load MWGparam")

        self.saveParamsAction = QAction(self)
        self.saveParamsAction.setText("Save MWGparam")

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
        self.tcp_client.textin.connect(self.recieved_tcp_msg)

    def get_num_freqs(self):
        return len(self.data[list(self.data.keys())[0]])

    def populate_table(self):
        self.freqTable.blockSignals(True)
        try:
            num_rows = int(self.num_rows_box.text())
        except ValueError:
            pass
        else:
            # print(num_rows)
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
        # print(self.data)

    def send_data(self):
        num_freqs = self.get_num_freqs()
        # print(self.comm.query('*IDN?'))
        if num_freqs < 1:
            print('no freqs!')
        elif num_freqs == 1:
            freq = self.data['freq (MHz)'][0]
            power = self.data['amp (dBm)'][0]
            send_str = 'CF0 {:.7f} GH L0 {:.2f} DM'.format(freq/1e3,power)
            
        else:
            freqs_str = ''
            powers_str = ''
            for freq, power in zip(self.data['freq (MHz)'],self.data['amp (dBm)']):
                freqs_str += '{:.7f} GH, '.format(freq/1e3)
                powers_str += '{:.2f} DM, '.format(power)
            freqs_str = freqs_str[:-2]
            powers_str = powers_str[:-2]
            
            send_str = ('LST EXT ELN0 ELI0000 LIB0000 LIE{:0>4} LF {} LP {} LEA MNT'.format(num_freqs-1,freqs_str,powers_str))

        self.comm.write(send_str,timeout=10000000)

        sleep_time = self.get_num_freqs()/100
        if sleep_time < 2:
            sleep_time = 2
        info('{} tones sent. Sleeping for {:.1f}s to allow for MWG calculations.'.format(self.get_num_freqs(),sleep_time))
        time.sleep(sleep_time)

        info('Calculations probably complete. Unlocking controls.')

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
        try:
            os.makedirs(os.path.dirname(filename),exist_ok=True)
        except FileExistsError as e:
            warning('FileExistsError thrown when saving MWGParams file',e)
        with open(filename, 'w') as f:
            f.write(str(msg))
        info('MWGparam saved to "{}"'.format(filename))

    def save_params_file_dialogue(self):
        filename = QFileDialog.getSaveFileName(self, 'Save MWGparam',self.last_MWGparam_folder,"Text documents (*.txt)")[0]
        if filename != '':
            self.save_params_file(filename)
            self.last_MWGparam_folder = os.path.dirname(filename)
            # print(self.last_MWGparam_folder)

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
                    info('Updating tone {:0>4} with {} = {}'.format(ind,arg_name,arg_val))
                    try:
                        arg_val = float(arg_val)
                    except ValueError as e:
                        error('Value must be a float values. Data will be left unchanged.',e)
                    else:
                        try:
                            self.data[arg_name][ind] = arg_val
                            self.populate_table()
                        except IndexError as e: 
                            error('Tone {:0>4} does not exist\n'.format(ind),e)
                        except KeyError as e: 
                            error('Argument {} does not exist\n'.format(arg_name),e)
            self.send_data()
            self.tcp_server.add_message(1,'go'*1000)

    def load_params_file_dialogue(self):
        filename = QFileDialog.getOpenFileName(self, 'Load MWGparam',self.last_MWGparam_folder,"Text documents (*.txt)")[0]
        if filename != '':
            self.load_params_file(filename)
            self.last_MWGparam_folder = os.path.dirname(filename)

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
            self.num_rows_box.setText(str(self.get_num_freqs()))
            self.populate_table()
            info('MWGparam loaded from "{}"'.format(filename))
        except (SyntaxError, IndexError) as e:
            error('Failed to evaluate file "{}". Is the format correct?'.format(filename),e)
        self.send_data()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    app.exec()