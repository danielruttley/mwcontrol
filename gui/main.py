# from multiprocessing.sharedctypes import Value
import sys
import os
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

        self.setWindowTitle("MW control")
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
        self.num_rows_box.returnPressed.connect(self.update_data)
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
        print(self.comm.query('*IDN?'))
        if num_freqs < 1:
            print('no freqs!')
        elif num_freqs == 1:
            freq = self.data['freq (MHz)'][0]
            power = self.data['amp (dBm)'][0]
            send_str = 'F1 {} HZ P1 {} DM CF1'.format(int(freq*1e6),int(power))
            send_str = 'CF0 {} HZ L0 {} DM'.format(int(freq*1e6),int(power))
            print(send_str)
            self.comm.write(send_str)
        else:
            header = 'LST ELN0 ETI0000 LIB0000 LIE{:0>4} '.format(num_freqs-1)
            
            
            freqs_str = ''
            powers_str = ''
            for freq, power in zip(self.data['freq (MHz)'],self.data['amp (dBm)']):
                freqs_str += '{} HZ, '.format(int(freq*1e6))
                powers_str += '{} DM, '.format(int(power))
            freqs_str = freqs_str[:-2]
            powers_str = powers_str[:-2]
            data_str = 'LF {} LP {} '.format(freqs_str,powers_str)
    
            footer = ('MNT')
    
            send_str = header+data_str+footer
            
            #Note that these can't all be send together otherwise a timeout error occurs and nothing happens on the MW gen.
            self.comm.write('LST')
            self.comm.write('EXT')
            self.comm.write('ELN0 ELI0000') # activate list mode, select list 0, index 0000
            self.comm.write('LIB0000 LIE{:0>4}'.format(num_freqs-1)) # set list playback indicies start=0000, end=table_len-1
            self.comm.write('LF {} LP {}'.format(freqs_str,powers_str)) # populate table
            self.comm.write('MNT') # change trigger mode to manual so that each TTL moves onto the next freq
            self.comm.write('LEA')
            info('Frequencies loaded into microwave generator.')
            # print(send_str)
            # send_str = 'LST ELN0 ELI0000 LIB0000 LIE0002 LF 3000000001 HZ, 6000000001 HZ, 5000000001 HZ LP 8 DM, 5 DM, 2 DM MNT LEA'
            

            # print(send_str)
            # self.comm.write(send_str)

    def open_new_holo_window(self):
        self.w = HoloCreationWindow(self)
        self.w.show()

    def up_holo(self):
        selectedRows = [x.row() for x in self.holoList.selectedIndexes()]
        if len(selectedRows) == 0:
            error('A hologram must be selected before it can be moved.')
        elif len(selectedRows) > 1:
            error('Only one hologram can be moved at once.')
        else:
            currentRow = selectedRows[0]
            if currentRow != 0:
                self.holos[currentRow],self.holos[currentRow-1] = self.holos[currentRow-1],self.holos[currentRow]
                self.update_holo_list()
                self.holoList.setCurrentRow(currentRow-1)

    def down_holo(self):
        selectedRows = [x.row() for x in self.holoList.selectedIndexes()]
        if len(selectedRows) == 0:
            error('A hologram must be selected before it can be moved.')
        elif len(selectedRows) > 1:
            error('Only one hologram can be moved at once.')
        else:
            currentRow = selectedRows[0]
            if currentRow != self.holoList.count()-1:
                self.holos[currentRow],self.holos[currentRow+1] = self.holos[currentRow+1],self.holos[currentRow]
                self.update_holo_list()
                self.holoList.setCurrentRow(currentRow+1)

    def open_slm_settings_window(self):
        self.slm_settings_window = SLMSettingsWindow(self,self.slm_settings)
        self.slm_settings_window.show()

    def get_slm_settings(self):
        return self.slm_settings
    
    def update_slm_settings(self,slm_settings):
        old_slm_settings = self.slm_settings
        new_slm_settings = {**self.slm_settings,**slm_settings}
        for setting in slm_settings.keys():
            old_value = old_slm_settings[setting]
            new_value = new_slm_settings[setting]
            if new_value != old_value:
                warning('Changed global SLM setting {} from {} to {}'.format(setting,old_value,new_value))
                if setting == 'monitor':
                    try:
                        self.slm
                    except AttributeError:
                        pass
                    else:
                        error('SLM monitor cannot be updated once the display has been created.\n\t'
                              'Change the monitor in gui/default_gui_state.txt and restart the program.\n\t'
                              'Resetting monitor back to {}'.format(old_value))
                        new_slm_settings[setting] = old_value
            if setting == 'orientation':
                if new_value == 'horizontal':
                    aperture_functions['horizontal aperture'] = hg.apertures.vert
                    aperture_functions['vertical aperture'] = hg.apertures.hori
                else:
                    aperture_functions['horizontal aperture'] = hg.apertures.hori
                    aperture_functions['vertical aperture'] = hg.apertures.vert
        for setting in new_slm_settings.keys():
            self.slm_settings[setting] = new_slm_settings[setting]
        self.update_global_holo_params()
        try:
            self.slm
        except AttributeError:
            pass
        else:
            self.update_holo_list()
        self.slm_settings_window = None

    def update_global_holo_params(self):
        try:
            self.global_holo_params
        except AttributeError:
            self.global_holo_params = {}
        self.global_holo_params['beam_center'] = (self.slm_settings['beam x0'],self.slm_settings['beam y0'])
        self.global_holo_params['beam_waist'] = self.slm_settings['beam waist (pixels)']
        self.global_holo_params['pixel_size'] = self.slm_settings['pixel size (m)']
        self.global_holo_params['shape'] = (self.slm_settings['x size'],self.slm_settings['y size'])
        self.global_holo_params['wavelength'] = self.slm_settings['wavelength']
        for holo in self.holos:
            holo.force_recalculate = True

    def get_global_holo_params(self):
        return self.global_holo_params

    def add_holo(self,holo_params):
        holo_params = {**holo_params,**self.global_holo_params}
        try:
            holo = get_holo_container(holo_params,self.global_holo_params)
            self.holos.append(holo)
            self.holoList.addItem(holo.get_label())
            self.w = None
            self.update_holo_list()
        except Exception as e:
            error('Error when generating {} hologram:'.format(holo_params['name']),e)

    def edit_holo(self):
        selectedRows = [x.row() for x in self.holoList.selectedIndexes()]
        if len(selectedRows) == 0:
            error('A hologram must be selected before it can be edited.')
        elif len(selectedRows) > 1:
            error('Only one hologram can be edited at once.')
        else:
            self.w = HoloCreationWindow(self,selectedRows[0])
            self.w.show()

    def remove_holo(self):
        selectedRows = [x.row() for x in self.holoList.selectedIndexes()]
        if len(selectedRows) != 0:
            selectedRows.sort(reverse=True)
            for row in selectedRows:
                try:
                    del self.holos[row]
                except IndexError:
                    pass
            self.update_holo_list()
    
    def update_holo_list(self):
        currentRow = self.holoList.currentRow()
        labels = []
        types = []
        for i,holo in enumerate(self.holos):
            labels.append(str(i)+': '+holo.get_label())
            types.append(holo.get_type())
        for i in range(self.holoList.count()):
            self.holoList.takeItem(0)
        self.holoList.addItems(labels)
        # for i in range(self.holoList.count()):
        #     self.holoList.item(i).setForeground(red)
        try:
            last_holo = types[::-1].index('holo')
            last_aperture = types[::-1].index('aperture')
            if last_aperture > last_holo:
                warning('A hologram is applied after the final aperture')
        except ValueError:
            pass
        if currentRow >= self.holoList.count():
            currentRow = self.holoList.count()-1
        self.holoList.setCurrentRow(currentRow)
        self.calculate_total_holo()
        # print(self.holos)

    def calculate_total_holo(self):
        self.total_holo = hg.blank(phase=0,shape=self.global_holo_params['shape'])
        #self.total_holo = self.total_holo + hg.misc.load('zernike_phase_correction.png')
        for holo in self.holos:
            if holo.get_type() == 'aperture':
                self.total_holo = holo.apply_aperture(self.total_holo)
            elif holo.get_type() == 'cam':
                self.total_holo = holo.get_cam_holo(self.total_holo)
            else:
                self.total_holo += holo.get_holo()
        # print(self.total_holo)
        self.slm.apply_hologram(self.total_holo)

    def set_holos_from_list(self,holo_list):
        """
        Set holograms from a list.

        Parameters
        ----------
        holos : list
            Should be a list of sublists containing the holo name and a dict 
            containing the holo arguments in the form [[holo1_name,{holo1_args}],...]
        """
        self.holos = []
        for i,(name,args) in enumerate(holo_list):
            try:
                holo_params = {'name':name}
                holo_params['type'],holo_params['function'] = get_holo_type_function(name)
                holo_params = {**holo_params,**args}
                holo = get_holo_container(holo_params,self.global_holo_params)
                self.holos.append(holo)
            except Exception as e:
                error('Error when creating Hologram {}. The hologram has been skipped.\n'.format(i),e)
        self.update_holo_list()
        self.w = None

    def generate_holo_list(self):
        holo_list = []
        for holo in self.holos:
            name = holo.get_name()
            args = holo.get_local_args()
            holo_list.append([name,args])
        return holo_list

    def save_params_file(self,filename):
        msg = self.data
        with open(filename, 'w') as f:
            f.write(str(msg))
        info('MWparams saved to "{}"'.format(filename))
    
    def save_current_holo_dialogue(self):
        filename = QFileDialog.getSaveFileName(self, 'Save hologram',self.last_MWparam_folder,"PNG (*.png);;24-bit Bitmap (*.bmp)")[0]
        if filename != '':
            hg.misc.save(self.total_holo,filename)

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
                            error('Frequency {:0>4} does not exist\n'.format(ind))
                        except KeyError as e: 
                            error('Argument {} does not exist\n'.format(arg_name))
    
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

class SLMSettingsWindow(QWidget):
    def __init__(self,mainWindow,slm_settings):
        super().__init__()
        self.mainWindow = mainWindow
        self.slm_settings = slm_settings
        self.setWindowTitle("SLM settings")

        layout = QVBoxLayout()

        self.slmParamsLayout = QFormLayout()
        for key in list(self.slm_settings.keys()):
            if key == 'orientation':
                widget = QComboBox()
                widget.addItems(['horizontal','vertical'])
                widget.setCurrentText(self.slm_settings[key])
            else:
                widget = QLineEdit()
                widget.setText(str(self.slm_settings[key]))
                if (key == 'pixel size (m)') or (key == 'wavelength'):
                    widget.setValidator(QDoubleValidator())
                elif key == 'monitor':
                    widget.setReadOnly(True)
                else:
                    widget.setValidator(QIntValidator())
            self.slmParamsLayout.addRow(key, widget)
        layout.addLayout(self.slmParamsLayout)

        self.saveButton = QPushButton("Save")
        layout.addWidget(self.saveButton)

        self.setLayout(layout)

        self._createActions()
        self._connectActions()

    def _createActions(self):
        self.saveAction = QAction(self)
        self.saveAction.setText("Save")

    def _connectActions(self):
        self.saveButton.clicked.connect(self.saveAction.trigger)
        self.saveAction.triggered.connect(self.update_slm_settings)
    
    def update_slm_settings(self):
        new_slm_settings = self.slm_settings.copy()
        for row in range(self.slmParamsLayout.rowCount()):
            key = self.slmParamsLayout.itemAt(row,0).widget().text()
            widget = self.slmParamsLayout.itemAt(row,1).widget()
            if key == 'orientation':
                value = widget.currentText()
            elif (key == 'pixel size (m)') or (key == 'wavelength'):
                value = float(widget.text())
            else:
                value = int(widget.text())
            new_slm_settings[key] = value
        self.mainWindow.update_slm_settings(new_slm_settings)

    def get_slm_settings(self):
        return self.slm_settings

class HoloCreationWindow(QWidget):
    def __init__(self,mainWindow,edit_holo=None):
        super().__init__()
        self.mainWindow = mainWindow
        if edit_holo is None:
            self.setWindowTitle("New Hologram")
            self.editing = False
        else:
            self.setWindowTitle("Edit Hologram {}".format(edit_holo))
            self.editing = True
            self.edit_holo = edit_holo
            self.current_holo_list = self.mainWindow.generate_holo_list()
            self.current_name = self.current_holo_list[edit_holo][0]
            self.current_params = self.current_holo_list[edit_holo][1]
        layout = QVBoxLayout()
        
        self.holoSelector = QComboBox()
        self.holoSelector.addItems(list(hologram_functions.keys()))
        self.holoSelector.addItems(list(aperture_functions.keys()))
        self.holoSelector.addItems(list(cam_functions.keys()))
        layout.addWidget(self.holoSelector)

        if self.editing == True:
            self.holoSelector.setCurrentText(self.current_name)

        self.holoParamsLayout = QFormLayout()
        layout.addLayout(self.holoParamsLayout)

        if self.editing == False:
            self.holoAddButton = QPushButton("Add")
        else:
            self.holoAddButton = QPushButton("Edit")
        layout.addWidget(self.holoAddButton)

        self.holoDocBox = QTextEdit()
        self.holoDocBox.setReadOnly(True)
        self.holoDocBox.setLineWrapMode(False)
        # self.holoDocBox.setCurrentFont(QFont("Courier",4))
        layout.addWidget(self.holoDocBox)
        self.setLayout(layout)

        self._connectActions()
        self.update_holo_arguments()

    def _connectActions(self):
        self.holoAddButton.clicked.connect(self.return_holo_params)
        self.holoSelector.currentTextChanged.connect(self.update_holo_arguments)

    def update_holo_arguments(self):
        self.clear_holo_params()
        slm_settings = self.mainWindow.get_slm_settings()
        current = self.holoSelector.currentText()
        self.type,self.function = get_holo_type_function(current)
        arguments,_,_,defaults = inspect.getfullargspec(self.function)[:4]
        if len(arguments) != len(defaults):
            pad = ['']*(len(arguments)-len(defaults))
            defaults = pad + list(defaults)
        global_holo_params = self.mainWindow.get_global_holo_params()
        slm_settings = self.mainWindow.get_slm_settings()
        for argument,default in zip(arguments,defaults):
            if default != '':
                if argument not in global_holo_params.keys():
                    self.holoParamsLayout.addRow(argument, QLineEdit())
                    text_box = self.holoParamsLayout.itemAt(self.holoParamsLayout.rowCount()-1, 1).widget()
                    text_box.returnPressed.connect(self.return_holo_params)
                    if (self.editing == True) and (current == self.current_name):
                        text_box.setText(str(self.current_params[argument]))
                    else:
                        if argument == 'x0':
                            text_box.setText(str(slm_settings['beam x0']))
                        elif argument == 'y0':
                            text_box.setText(str(slm_settings['beam y0']))
                        elif argument == 'radius':
                            radius = min([slm_settings['x size']-slm_settings['beam x0'],
                                        slm_settings['y size']-slm_settings['beam y0'],
                                        slm_settings['beam x0'],slm_settings['beam y0']])
                            text_box.setText(str(radius))
                        else:
                            text_box.setText(str(default))
        self.holoDocBox.setText(self.function.__doc__.split('Returns')[0])

    def clear_holo_params(self):
        for i in range(self.holoParamsLayout.rowCount()):
            # print(i)
            self.holoParamsLayout.removeRow(0)
    
    def return_holo_params(self):
        holo_params = {'name':self.holoSelector.currentText()}
        holo_params['function'] = self.function
        holo_params['type'] = self.type
        if self.editing == True:
            holo_params = {}
        for row in range(self.holoParamsLayout.rowCount()):
            key = self.holoParamsLayout.itemAt(row,0).widget().text()
            widget = self.holoParamsLayout.itemAt(row,1).widget()
            value = widget.text()
            if (value.lower() == 'none') or (value == ''):
                value = None
            elif value.lower() == 'true':
                value = True
            elif value.lower() == 'false':
                value = False
            else:
                try:
                    value = int(value)
                except ValueError:
                    try:
                        value = float(value)
                    except ValueError:
                        pass
            holo_params[key] = value
        if self.editing == True:
            holo_list = self.current_holo_list.copy()
            holo_list[self.edit_holo] = [self.holoSelector.currentText(),holo_params]
            # print(holo_list)
            self.mainWindow.set_holos_from_list(holo_list)
        else:
            self.mainWindow.add_holo(holo_params)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    app.exec()