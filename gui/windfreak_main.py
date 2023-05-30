# from multiprocessing.sharedctypes import Value
import sys
import os
import numpy as np
import threading
import time
os.system("color")
import inspect
from datetime import datetime

#from qtpy.QtCore import QThread,Signal,Qt
from qtpy.QtCore import Qt,Slot
from qtpy.QtWidgets import (QApplication,QMainWindow,QVBoxLayout,QWidget,
                            QAction,QListWidget,QFormLayout,QComboBox,QLineEdit,
                            QTextEdit,QPushButton,QFileDialog,QAbstractItemView,
                            QTableWidget,QTableWidgetItem,QLabel,QGridLayout,
                            QTabWidget,QToolButton,QStatusBar,QHBoxLayout,
                            QButtonGroup,QRadioButton)
from qtpy.QtGui import QIcon,QIntValidator,QDoubleValidator,QColor



non_neg_validator = QDoubleValidator()    # integers
non_neg_validator.setBottom(0) # don't allow -ve numbers

red = '#FFCCCC'
green = '#CCDDAA'
blue = '#BBCCEE'

if __name__ == '__main__':
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from .networking.client import PyClient
from .networking.server import PyServer
from .strtypes import error, warning, info

from windfreak import SynthHD
import serial

class WindfreakWindow(QMainWindow):
    def __init__(self,**kwargs):
        """Initialise the main interface for the controller.
        """
        super().__init__()
        self.title = 'Windfreak Control Centre'
        self.left = 0
        self.top = 0
        self.width = 300
        self.height = 200
        self.setWindowTitle(self.title)
        self.setGeometry(self.left, self.top, self.width, self.height)

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        self.windfreaks = []

        self.table_widget = TabContainer(self)
        self.setCentralWidget(self.table_widget)
        
        self.show()

        self.tcp_client = PyClient(host='129.234.190.164',port=8631,name='mwcontrol')
        # self.tcp_client = PyClient(host='localhost',port=8631,name='MWG')

        self.tcp_client.start()
        self.tcp_client.textin.connect(self.recieved_tcp_msg)

        self.tcp_server = PyServer(host='', port=8632, name='MWG recv') # MW generator resumes PyDex when loaded
        self.tcp_server.start()

    def set_status_message(self,message):
        self.status_bar.setStyleSheet(f'background-color : {blue}')
        time_str = datetime.now().strftime('%H:%M:%S')
        self.status_bar.showMessage('{}: {}'.format(time_str,message))
        print('{}: {}'.format(time_str,message))

    def set_status_error(self,message):
        self.status_bar.setStyleSheet(f'background-color : {red}')
        time_str = datetime.now().strftime('%H:%M:%S')
        self.status_bar.showMessage('{}: {}'.format(time_str,message))
        print('{}: {}'.format(time_str,message))

    def recieved_tcp_msg(self,msg):
        self.set_status_message('TCP message recieved: "'+msg+'"')
        split_msg = msg.split('=')
        command = split_msg[0]
        arg = split_msg[1]
        # if command == 'save':
        #     pass
        # elif command == 'save_all':
        #     pass
        # elif command == 'load_all':
        #     pass
        if command == 'set_data':
            for update in eval(arg):
                    com_port_channel,arg_name,arg_val,tone_index = update
                    self.set_status_message('Updating {:0>4} tone {} with {} = {}'.format(com_port_channel,tone_index,arg_name,arg_val))
                    if tone_index > 0:
                        error('Multiple frequency mode not currently implemented. Will change tone index 0.')
                        tone_index = 0
                    try:
                        arg_val = float(arg_val)
                    except ValueError as e:
                        error('Value must be a float values. Data will be left unchanged.',e)
                    else:
                        try:
                            com_port = com_port_channel.split(' ')[0]
                            channel_index = ['A','B'].index(com_port_channel.split(' ')[1])

                            open_coms = [w.com_port for w in self.windfreaks]

                            try:
                                windfreak_index = open_coms.index(com_port)
                            except ValueError:
                                error('Not connected to Windfreak on {}'.format(com_port))
                                self.set_status_message('Nothing has been updated.')
                                continue

                            try:
                                self.windfreaks[windfreak_index].channels[channel_index].set_parameter(arg_name,arg_val,tone_index)
                            except KeyError as e:
                                error('Could not set parameter\n',e)
                                self.set_status_message('Nothing has been updated.')

                        except Exception as e:
                            error('Error when parsing set_data TCP message\n',e)
                            self.set_status_message('Nothing has been updated.')

            self.tcp_server.add_message(1,'go'*1000)
    
class TabContainer(QWidget):
    def __init__(self,main_window):
        super().__init__()
        self.main_window = main_window
        self.windfreaks = main_window.windfreaks
        self.layout = QVBoxLayout()
        
        # Initialize tab screen
        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        self.tabs.resize(300,200)
        
        # Add tabs
        self.tabs.addTab(QWidget(),"Placeholder")
        
        # Add tabs to widget
        self.layout.addWidget(self.tabs)
        self.setLayout(self.layout)

        self.button_new_tab = QToolButton(self)
        self.button_new_tab.setText('+')
        self.tabs.setCornerWidget(self.button_new_tab)
        self.button_new_tab.clicked.connect(self.open_new_tab_window)
    
    def open_new_tab_window(self):
        self.new_tab_window = NewTabWindow(self)
        self.new_tab_window.show()
    
    def new_tab(self,com_port):
        """Open a new connection to a Windfreak and add a new tab."""
        self.new_tab_window = None
        try:
            windfreak = WindfreakController(com_port)
        except TimeoutError: # triggers if COM port is not a valid connection
            self.main_window.set_status_error(f'Could not connect to {com_port}.')
        else:
            self.windfreaks.append(windfreak)
            self.tabs.addTab(windfreak,windfreak.com_port)

    def close_tab(self,tab_index):
        if tab_index == 0:
            return # don't close the placeholder tab
        self.tabs.removeTab(tab_index)
        self.windfreaks[tab_index-1].close()
        del self.windfreaks[tab_index-1]
        print(self.windfreaks)

class NewTabWindow(QWidget):
    def __init__(self, tab_container):
        super().__init__()
        self.tab_container = tab_container
        self.setWindowTitle("New Windfreak connnection")

        layout = QVBoxLayout()
        self.setLayout(layout)

        available_com_ports = self.get_com_ports()

        self.com_selector = QComboBox()
        self.com_selector.addItems(available_com_ports)

        layout.addWidget(QLabel('Choose COM port to connect to:'))
        layout.addWidget(self.com_selector)

        connect_button = QPushButton('Connect')
        connect_button.clicked.connect(self.connect_to_com)
        layout.addWidget(connect_button)

    def get_com_ports(self):
        if sys.platform.startswith('win'):
            ports = ['COM%s' % (i + 1) for i in range(256)]
        else:
            raise EnvironmentError('Unsupported platform, sorry. Use Windows.')

        result = []
        for port in ports:
            try:
                s = serial.Serial(port)
                s.close()
                result.append(port)
            except (OSError, serial.SerialException) as e:
                pass
        return result
    
    def connect_to_com(self):
        """Attempt connection to the selected COM port and close the window."""
        self.tab_container.new_tab(self.com_selector.currentText())

class WindfreakController(QWidget):
    def close(self):
        self.synth.close()

    def __init__(self,com_port):
        """Stores and handles the connections to a SynthHD."""
        super().__init__()
        self.com_port = com_port
        self.synth = SynthHD(self.com_port)
        # self.synth.init()

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        self.layout.addWidget(QLabel(f' {com_port}: Windfreak SynthHD #{self.synth.serial_number}'))

        layout_synth = QFormLayout()

        self.trigger_mode_selector = QComboBox()
        self.trigger_mode_selector.addItems(list(self.synth.trigger_modes))
        self.trigger_mode_selector.currentTextChanged.connect(self.set_trigger_mode)
        layout_synth.addRow('trigger mode',self.trigger_mode_selector)

        self.reference_mode_selector = QComboBox()
        self.reference_mode_selector.addItems(list(self.synth.reference_modes))
        self.reference_mode_selector.currentTextChanged.connect(self.set_reference_mode)
        layout_synth.addRow('reference mode',self.reference_mode_selector)

        self.box_reference_frequency = QLineEdit('1')
        self.box_reference_frequency.setValidator(non_neg_validator)
        self.box_reference_frequency.setText(str(self.synth.reference_frequency/1e6))
        self.box_reference_frequency.editingFinished.connect(self.set_reference_frequency)
        layout_synth.addRow('ref. freq. (MHz)',self.box_reference_frequency)

        self.layout.addLayout(layout_synth)

        layout_synth_modes = QHBoxLayout()
        self.group_modes = QButtonGroup()
        self.button_mode_single = QRadioButton('single frequency')
        self.group_modes.addButton(self.button_mode_single)
        self.button_mode_multi = QRadioButton('multiple frequencies')
        self.group_modes.addButton(self.button_mode_multi)
        self.button_mode_multi.setEnabled(False)
        self.button_mode_single.setChecked(True)
        layout_synth_modes.addWidget(self.button_mode_single)
        layout_synth_modes.addWidget(self.button_mode_multi)
        self.group_modes.buttonClicked.connect(self.set_number_frequencies)

        self.layout.addLayout(layout_synth_modes)

        self.button_save_to_eeprom = QPushButton('Save settings to EEPROM')
        self.button_save_to_eeprom.clicked.connect(self.save_to_eeprom)
        self.layout.addWidget(self.button_save_to_eeprom)

        self.layout.addWidget(QLabel('<h3></h3>'))

        self.channels = [ChannelController(self.synth[0]),ChannelController(self.synth[1])]
        self.layout.addWidget(QLabel('<h3>Channel A</h3>'))
        self.layout.addWidget(self.channels[0])
        self.layout.addWidget(QLabel('<h3></h3>'))
        self.layout.addWidget(QLabel('<h3>Channel B</h3>'))
        self.layout.addWidget(self.channels[1])

        self.update_gui_from_device()

    def update_gui_from_device(self):
        """Gets the current settings from the Synth and updates the GUI."""
        [x.update_gui_from_device() for x in self.channels]

        self.trigger_mode_selector.blockSignals(True)
        self.trigger_mode_selector.setCurrentText(self.synth.trigger_mode)
        self.trigger_mode_selector.blockSignals(False)

        self.reference_mode_selector.blockSignals(True)
        self.reference_mode_selector.setCurrentText(self.synth.reference_mode)
        self.reference_mode_selector.blockSignals(False)

        self.box_reference_frequency.setText(str(self.synth.reference_frequency/1e6))

    def set_trigger_mode(self):
        self.synth.trigger_mode = self.trigger_mode_selector.currentText()
        self.update_gui_from_device()

    def set_reference_mode(self):
        self.synth.reference_mode = self.reference_mode_selector.currentText()
        self.update_gui_from_device()

    def set_reference_frequency(self):
        self.synth.reference_frequency = float(self.box_reference_frequency.text())*1e6
        self.update_gui_from_device()

    def set_number_frequencies(self):
        if self.button_mode_single.isChecked():
            [x.set_number_frequencies('single') for x in self.channels]
        else:
            [x.set_number_frequencies('multiple') for x in self.channels]

    def save_to_eeprom(self):
        self.synth.save()

class ChannelController(QWidget):
    def __init__(self,channel):
        """Stores and handles the channels for a particular SynthHD."""
        super().__init__()
        self.channel = channel

        self.layout = QGridLayout()
        self.setLayout(self.layout)
        
        self.layout.addWidget(QLabel('RF frequency (MHz)'),0,0,1,2)
        self.layout.addWidget(QLabel('Phase (deg)'),0,2,1,1)
        self.layout.addWidget(QLabel('Power (dBm)'),0,3,1,1)

        self.box_frequency = QLineEdit('freq')
        self.box_frequency.setValidator(non_neg_validator)
        
        self.layout.addWidget(self.box_frequency,1,0,1,2)

        self.box_phase = QLineEdit('phase')
        self.box_phase.setValidator(non_neg_validator)
        self.layout.addWidget(self.box_phase,1,2,1,1)

        self.box_power = QLineEdit('power')
        self.box_power.setValidator(QDoubleValidator())
        self.layout.addWidget(self.box_power,1,3,1,1)

        self.button_rf_enable = QPushButton('RF off')
        self.button_rf_enable.setCheckable(True)
        self.layout.addWidget(self.button_rf_enable,2,0,1,2)
        self.button_rf_enable.clicked.connect(self.toggle_rf_enable)

        self.box_levelled = QLineEdit('Levelled?')
        self.box_levelled.setReadOnly(True)
        self.layout.addWidget(self.box_levelled,2,2,1,1)

        self.box_pll = QLineEdit('PLL?')
        self.box_pll.setReadOnly(True)
        self.layout.addWidget(self.box_pll,2,3,1,1)

        # self.channel.sweep_type = 1 # set sweep type to tabular mode

        self.box_frequency.editingFinished.connect(self.set_frequency)
        self.box_phase.editingFinished.connect(self.set_phase)
        self.box_power.editingFinished.connect(self.set_power)

        

    def update_gui_from_device(self):
        self.get_number_frequencies()

        self.box_frequency.setText(str(self.channel.frequency/1e6))
        self.box_phase.setText(str(self.channel.phase))
        self.box_power.setText(str(self.channel.power))

        self.button_rf_enable.blockSignals(True)
        if self.channel.enable:
            self.button_rf_enable.setChecked(True)
            self.button_rf_enable.setText('RF on')
            self.button_rf_enable.setStyleSheet(f'background-color: {red}')
        else:
            self.button_rf_enable.setChecked(False)
            self.button_rf_enable.setText('RF off')
            self.button_rf_enable.setStyleSheet('')
        self.button_rf_enable.blockSignals(False)

        if self.channel.calibrated:
            self.box_levelled.setText('Level')
            self.box_levelled.setStyleSheet(f'background-color: {green}')
        else:
            self.box_levelled.setText('Unlevel')
            self.box_levelled.setStyleSheet(f'background-color: {red}')

        if self.channel.lock_status:
            self.box_pll.setText('PLL ok')
            self.box_pll.setStyleSheet(f'background-color: {green}')
        else:
            self.box_pll.setText('no PLL')
            self.box_pll.setStyleSheet(f'background-color: {red}')

        # print('final list',self.channel.sweep_list)

    def set_parameter(self,parameter,value,tone_index=0):
        """Sets a certain parameter for the channel. This is normally triggered
        by a TCP message from PyDex."""
        #TODO add handling for multiple tones by doing something with tone_index
        if 'freq' in parameter:
            self.set_frequency(value)
        elif ('amp' in parameter) or ('power' in parameter):
            self.set_power(value)
        elif 'phase' in parameter:
            self.set_phase(value)
        else:
            raise KeyError('Parameter {} is not recognised'.format(parameter))

    def set_frequency(self,value=None):
        try:
            if value is None:
                self.channel.frequency = float(self.box_frequency.text())*1e6
            else:
                self.channel.frequency = float(value)*1e6
        except:
            pass
        self.update_gui_from_device()

    def set_phase(self,value=None):
        try:
            if value is None:
                self.channel.phase = float(self.box_phase.text())
            else:
                self.channel.phase = float(value)
        except:
            pass
        self.update_gui_from_device()

    def set_power(self,value=None):
        try:
            if value is None:
                self.channel.power = float(self.box_power.text())
            else:
                self.channel.power = float(value)
        except:
            pass
        self.update_gui_from_device()

    def toggle_rf_enable(self):
        self.channel.enable = not self.channel.enable
        self.update_gui_from_device()

    def get_number_frequencies(self):
        """Read the frequency mode from the SynthHD device."""
        self.mode = 'single'

    def set_number_frequencies(self,mode):
        """Set the mode that the channel should operate in.
        
        Parameters
        ----------
        mode : ['single','multiple']
            Whether the channel should be in single frequency mode or multiple
            frequency mode.
        """
        if mode not in ['single','multiple']:
            return
        elif mode == self.mode:
            return
        
        activate_single = (mode == 'single')

        self.box_frequency.setEnabled(activate_single)
        self.box_phase.setEnabled(activate_single)
        self.box_power.setEnabled(activate_single)
        # self.box_frequency.setEnabled(activate_single)
        # self.box_frequency.setEnabled(activate_single)
        # self.box_frequency.setEnabled(activate_single)

        self.get_number_frequencies()
        self.mode = mode
        

'''
        super().__init__()
        self.tcp_client = PyClient(host='129.234.190.164',port=8631,name='mwcontrol')
        # self.tcp_client = PyClient(host='localhost',port=8631,name='MWG')
        self.tcp_client.start()

        self.tcp_server = PyServer(host='', port=8632, name='MWG recv') # MW generator resumes PyDex when loaded
        self.tcp_server.start()

        self.last_MWGparam_folder = '.'
        self.num_freqs = 0

        self.data = {'freq (MHz)': [6000],
                     'amp (dBm)': [8]}

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
    
        try:
            self.send_data()
        except AttributeError: # communicator/SynthHD object not created yet
            pass
            # info('Did not send data yet because object does not exist')

class AnritsuWindow(MainWindow):
    def __init__(self):
        """Initialise the main interface for the controller if in Anritsu mode.
        """    
        super().__init__()

        self.setWindowTitle(f"MWG control: Anritsu")
        self.send_button.setText('send to Anritsu')
        self.comm = Communicator()

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

class WindfreakWindow(MainWindow):
    def __init__(self,com_port='COM19',channel=0):
        """Initialise the main interface for the controller if in Windfreak mode.

        Parameters
        ----------
        com_port : str, optional
            COM port to use to connect to the Windfreak, by default 'COM19'
        channel : [0,1], optional
            The channel to control on the Windfreak. Channel 0 = A, channel 
            B= 1. By default 0
        """    
        super().__init__()

        self.com_port = com_port
        self.channel = 0
        self.setWindowTitle(f"MWG control: Windfreak {self.com_port} Ch{['A','B'][self.channel]}")
        self.send_button.setText('send to Windfreak')

        # self.data = {'Ch A: freq (MHz)': [6000],
        #              'Ch A: amp (dBm)': [1],
        #              'Ch B: freq (MHz)': [5000],
        #              'Ch B: amp (dBm)': [0],} # change data to be 4 columns for channel A and channel B
        # self.populate_table()

        self.synth = SynthHD(self.com_port)
        self.synth.init()

        # # Set channel 0 power and frequency
        # synth[0].power = 10.
        # synth[0].frequency = 101.e6

        # # Enable channel 0 output
        # synth[0].enable = True

    def send_data(self):
        num_freqs = self.get_num_freqs()
        # print(self.comm.query('*IDN?'))
        if num_freqs < 1:
            print('no freqs!')
        elif num_freqs == 1:
            self.synth[self.channel].power = self.data['amp (dBm)'][0]
            self.synth[self.channel].frequency = self.data['freq (MHz)'][0]*1e6    
            self.synth[self.channel].enable = True       
        else:
            self.synth[self.channel].enable = False
            self.synth[self.channel].sweep_type = 1
            print('initial list',self.synth[self.channel].sweep_list)
            list_string = ''
            for index,(freq,amp) in enumerate(zip(self.data['freq (MHz)'],self.data['amp (dBm)'])):
                list_string += f'L{index:02d}f{freq}L{index:02d}a{amp}'
            print('list to send',list_string)
            self.synth[self.channel].sweep_list = list_string
            print('final list',self.synth[self.channel].sweep_list)
            self.synth[self.channel].enable = True
            self.synth[self.channel].sweep_direction = 1 # set to normal sweep direction
            self.synth[self.channel].sweep_single = 1
            
            # self.synth[self.channel].enable = False
'''

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = WindfreakWindow()
    window.show()
    app.exec()