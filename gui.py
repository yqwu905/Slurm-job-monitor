import time

from PyQt5 import QtCore, QtGui, QtWidgets
import job_control
import tool
import server
import sys
import json
import logging
from PyQt5.QtWidgets import QApplication, QMainWindow
from mainWin import Ui_Form
import threading


class connect_thread(QtCore.QThread):
    finishSignal = QtCore.pyqtSignal(server.server)

    def __init__(self, data, proxy, proxy_host, proxy_port, parent=None):
        super(connect_thread, self).__init__(parent)
        self.data = data
        self.proxy = proxy
        self.proxy_port = proxy_port
        self.proxy_host = proxy_host

    def run(self):
        logging.debug("Button Connect clicked.")
        logging.debug(
            "Proxy status:{},{}:{}".format(self.proxy, self.proxy_host, self.proxy_port))
        logging.debug("{}".format(self.data))
        s = server.server(self.data, proxy=self.proxy, proxy_host=self.proxy_host, proxy_port=self.proxy_port)
        self.finishSignal.emit(s)


class main_ui(Ui_Form):
    def __init__(self):
        self.server = None

    def setupUi(self, Form):
        super().setupUi(Form)
        self.btn_initial_()

    def write(self, text):
        if text[-1] == '\n':
            text = text[:-1]
        self.textBrowser.append(text)
        self.textBrowser.moveCursor(self.textBrowser.textCursor().End)

    def flush(self):
        pass

    def btn_initial_(self):
        self.pushButton_8.clicked.connect(self.btn_load)
        self.pushButton_6.clicked.connect(self.btn_connect)

    def btn_load(self):
        logging.debug("Button Load clicked.")
        with open('./server_list.json', 'r') as fp:
            self.server_data_list = json.load(fp)
        self.comboBox.clear()
        for i in self.server_data_list:
            self.comboBox.addItem("{}@{}".format(i['user'], i['server']))

    def btn_connect(self):
        self.th = connect_thread(data=self.server_data_list[self.comboBox.currentIndex()],
                                 proxy=self.checkBox.isChecked(), proxy_host=self.lineEdit.text(),
                                 proxy_port=self.spinBox.value())
        self.th.finishSignal.connect(self.btn_connect_finish)
        logging.debug("Thread for connect start.")
        self.th.start()

    def btn_connect_finish(self, s):
        self.server = s
        logging.info("Successfully connect to {}@{}.".format(self.server.data['user'], self.server.data['server']))
