import sys

from qtpy.QtWidgets import QApplication
from gui import AnritsuWindow, WindfreakWindow

app = QApplication(sys.argv)
window = AnritsuWindow()
window.show()
app.exec()