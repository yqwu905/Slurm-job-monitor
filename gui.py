import time
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtGui import QStandardItemModel, QStandardItem, QFont, QBrush, QColor
import job_control
import server
import json
import logging
from mainWin import Ui_Form
import tool


class update_jobs(QtCore.QThread):
    finishSignal = QtCore.pyqtSignal(int)

    def __init__(self, proxy, proxy_host, proxy_port, server, parent=None):
        logging.debug("Thread update_jobs created.")
        super(update_jobs, self).__init__(parent)
        self.proxy = proxy
        self.proxy_port = proxy_port
        self.proxy_host = proxy_host
        self.server = server
        with open('server_list.json', 'r') as fp:
            self.server_list = json.load(fp)
        self.jobs = job_control.jobs()

    def get_server(self, job):
        for s in self.server_list:
            if s['user'] == job['user'] and s['server'] == job['server']:
                return s
        return None

    def run(self):
        logging.debug("Updating job info.")
        connected_server = self.server
        job_list = self.jobs.job_list.copy()
        compare = job_list.copy()
        total = len(job_list)
        idx = 0
        while len(job_list) != 0:
            for job in compare:
                if job['status'] in ['COMPLETED', "CANCELED"]:
                    job_list.remove(job)
                    continue
                logging.debug(job_list)
                logging.debug("Processing job {}.".format(job['id']))
                s = self.get_server(job)
                if s is None:
                    logging.warning("No match server found for job {}.".format(job['id']))
                    job_list.remove(job)
                    idx += 1
                    self.finishSignal.emit(int(100 * idx / total))
                else:
                    if connected_server is None:
                        connected_server = server.server(s, proxy=self.proxy, proxy_host=self.proxy_host,
                                                         proxy_port=self.proxy_port)
                    if connected_server.data['user'] == s['user'] and connected_server.data['server'] == s['server']:
                        logging.debug("Same")
                        res = connected_server.update_job_status(job['id'])
                        if res == job['status']:
                            logging.debug("Job {} state not change.".format(job['id']))
                        else:
                            logging.info("Job {} status change from {} to {}.".format(job['id'], job['status'],
                                                                                      res))
                            self.jobs.update_job_status(job['id'], res)
                        job_list.remove(job)
                        idx += 1
                        self.finishSignal.emit(int(100 * idx / total))
                    else:
                        logging.debug("Connecting to another server, job {} skip.".format(job['id']))
            logging.debug("Connection closed.")
            connected_server = None
            compare = job_list.copy()

        self.finishSignal.emit(100)


class download_job(QtCore.QThread):
    finishSignal = QtCore.pyqtSignal(int)

    def __init__(self, data, proxy, proxy_host, proxy_port, remote, local, download_list, parent=None):
        logging.debug("Thread download_job created.")
        super(download_job, self).__init__(parent)
        self.data = data
        self.proxy = proxy
        self.proxy_port = proxy_port
        self.proxy_host = proxy_host
        self.remote = remote
        self.local = local
        self.download_list = download_list

    def run(self):
        logging.info("Connect to {}@{}".format(self.data['user'], self.data['server']))
        s = server.server(self.data, self.proxy, self.proxy_host, self.proxy_port)
        for i in self.download_list:
            stdin, stdout, stderr = s.ssh.exec_command(f"ls {self.remote}/{i}")
            res, err = stdout.read().decode(), stderr.read().decode()
            if err != '':
                logging.error(f"Failed to list file:{err}")
                continue
            for file in res.split('\n'):
                if file == '':
                    continue
                else:
                    logging.info("Downloading {}@{}:{}/{} to {}.".format(s.data['user'], s.data['server'], file,
                                                                         self.remote, self.local))
                    s.download(f"{file}", self.local)
        self.finishSignal.emit(0)


class submit_job(QtCore.QThread):
    finishSignal = QtCore.pyqtSignal(int)

    def __init__(self, s, remote, local, dos2unix, parent=None):
        logging.debug("Thread submit_job created.")
        super(submit_job, self).__init__(parent)
        self.s = s
        self.remote = remote
        self.local = local
        self.dos2unix = dos2unix

    def run(self):
        self.s.submit_job(self.remote, self.local, self.dos2unix)
        self.finishSignal.emit(0)


class exec_cmd(QtCore.QThread):
    finishSignal = QtCore.pyqtSignal(tuple)

    def __init__(self, s, cmd, parent=None):
        logging.debug("Thread execute_cmd created.")
        super(exec_cmd, self).__init__(parent)
        self.cmd = cmd
        self.s = s

    def run(self):
        logging.info("Executing command {}.".format(self.cmd))
        stdin, stdout, stderr = self.s.ssh.exec_command(self.cmd)
        res, err = stdout.read().decode(), stderr.read().decode()
        self.finishSignal.emit((res, err))


class connect_thread(QtCore.QThread):
    finishSignal = QtCore.pyqtSignal(server.server)

    def __init__(self, data, proxy, proxy_host, proxy_port, parent=None):
        logging.debug("Thread start")
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
        self.th = None
        self.dlg = None
        self.job_list = None
        self.server_data_list = None
        self.job_data = None

    def setupUi(self, Form):
        super().setupUi(Form)
        flag, s = tool.check_update()
        if flag:
            for i in s:
                self.write(i)
        tool.init()
        self.btn_initial_()
        self.checkBox_3.stateChanged.connect(self.load_job)
        self.progressBar.setValue(100)
        self.load_job()
        self.btn_load()

    def load_job(self):
        logging.debug("Load job info.")
        show_hide = self.checkBox_3.isChecked()
        logging.debug("Show hide job:{}".format(show_hide))
        status_color_list = {"COMPLETED": [72, 209, 204],
                             "CANCELLED": [255, 165, 0],
                             "CANCELLED+": [255, 165, 0],
                             "RUNNING": [0, 255, 127],
                             "PENDING": [255, 255, 0],
                             "FAILED": [255, 0, 0],
                             }
        self.job_list = job_control.jobs().job_list
        self.job_data = QStandardItemModel(len(self.job_list), 3)
        self.job_data.setHorizontalHeaderLabels(["Id", "server", "status"])
        for i in range(len(self.job_list)):
            self.job_data.setItem(i, 0, QStandardItem(self.job_list[i]['id']))
            self.job_data.setItem(i, 1,
                                  QStandardItem("{}@{}".format(self.job_list[i]['user'], self.job_list[i]['server'])))
            self.job_data.setItem(i, 2, QStandardItem(self.job_list[i]['status']))
            if self.job_list[i]['status'] in status_color_list.keys():
                color = status_color_list[self.job_list[i]['status']]
                for j in range(0, 3):
                    self.job_data.item(i, j).setBackground(QBrush(QColor(color[0], color[1], color[2])))
        self.tableView.setModel(self.job_data)
        for i in range(len(self.job_list)):
            self.tableView.showRow(i)
            if (show_hide is False) and self.job_list[i]['hide']:
                logging.debug("Hide job {}.".format(self.job_list[i]['id']))
                self.tableView.hideRow(i)

    def write(self, text):
        self.textBrowser.append(text)

    def flush(self):
        pass

    def btn_initial_(self):
        self.pushButton_8.clicked.connect(self.btn_load)
        self.pushButton_6.clicked.connect(self.btn_connect)
        self.pushButton_7.clicked.connect(self.btn_reconnect)
        self.pushButton_3.clicked.connect(self.btn_logging_level_update)
        self.pushButton_9.clicked.connect(self.btn_exec)
        self.pushButton_4.clicked.connect(self.btn_select_local_folder)
        self.pushButton_5.clicked.connect(self.btn_submit_job)
        self.pushButton_2.clicked.connect(self.btn_download)
        self.pushButton.clicked.connect(self.btn_update_jobs)
        self.pushButton_10.clicked.connect(self.btn_hide)

    def btn_load(self):
        logging.debug("Button Load clicked.")
        self.progressBar.setValue(0)
        with open('./server_list.json', 'r') as fp:
            self.server_data_list = json.load(fp)
        self.comboBox.clear()
        for i in self.server_data_list:
            self.comboBox.addItem("{}@{}".format(i['user'], i['server']))
        self.progressBar.setValue(100)

    def btn_connect(self):
        logging.debug("Button Connect clicked.")
        self.progressBar.setValue(0)
        self.th = connect_thread(data=self.server_data_list[self.comboBox.currentIndex()],
                                 proxy=self.checkBox.isChecked(), proxy_host=self.lineEdit.text(),
                                 proxy_port=self.spinBox.value())
        self.th.finishSignal.connect(self.btn_connect_finish)
        logging.debug("Thread for connect start.")
        self.th.start()

    def btn_connect_finish(self, s):
        self.server = s
        self.lineEdit_4.setText(s.data['default_dir'])
        logging.debug("Set remote dir to {}".format(s.data['default_dir']))
        logging.info("Successfully connect to {}@{}.".format(self.server.data['user'], self.server.data['server']))
        self.progressBar.setValue(100)

    def btn_reconnect(self):
        logging.debug("Button Reconnect clicked.")
        self.progressBar.setValue(0)
        del self.server
        logging.debug("Old server release.")
        self.th = connect_thread(data=self.server_data_list[self.comboBox.currentIndex()],
                                 proxy=self.checkBox.isChecked(), proxy_host=self.lineEdit.text(),
                                 proxy_port=self.spinBox.value())
        self.th.finishSignal.connect(self.btn_reconnect_finish)
        logging.debug("Thread for connect start.")
        self.th.start()

    def btn_reconnect_finish(self, s):
        self.server = s
        logging.info("Successfully reconnect to {}@{}.".format(self.server.data['user'], self.server.data['server']))
        self.progressBar.setValue(100)

    def btn_logging_level_update(self):
        logging.debug("Button Logging level update clicked.")
        self.progressBar.setValue(0)
        logging.info("Change logging level to {}".format(self.comboBox_2.currentText()))
        level = [logging.DEBUG, logging.INFO]
        logging.getLogger().setLevel(level=level[self.comboBox_2.currentIndex()])
        self.progressBar.setValue(100)

    def btn_exec(self):
        logging.debug("Button Execute clicked.")
        self.progressBar.setValue(0)
        self.textBrowser_3.append("<font color='blue'>{}<font>".format(self.lineEdit_2.text()))
        self.textBrowser_3.moveCursor(self.textBrowser_3.textCursor().End)
        self.th = exec_cmd(self.server, self.lineEdit_2.text())
        self.th.finishSignal.connect(self.btn_exec_finish)
        self.th.start()

    def btn_exec_finish(self, s):
        logging.info("Command Result: {}".format(s[0]))
        logging.info("Command Error: {}".format(s[1]))
        self.textBrowser_3.append(s[0])
        self.textBrowser_3.moveCursor(self.textBrowser_3.textCursor().End)
        if len(s[1]) != 0:
            self.textBrowser_3.append("<font color='red'>Error: {}<font>".format(s[1]))
            self.textBrowser_3.moveCursor(self.textBrowser_3.textCursor().End)
        logging.info("Successfully execute cmd.")
        self.progressBar.setValue(100)

    def btn_select_local_folder(self):
        self.progressBar.setValue(0)
        logging.debug("Start QFileDialog.")
        directory = QtWidgets.QFileDialog.getExistingDirectory(None, "选取文件夹", "./")
        self.lineEdit_3.setText(directory)
        logging.debug("Set local folder to {}".format(directory))
        self.progressBar.setValue(100)

    def btn_submit_job(self):
        self.progressBar.setValue(0)
        logging.debug("Button submit clicked.")
        self.th = submit_job(self.server, self.lineEdit_4.text(), self.lineEdit_3.text(), self.checkBox_2.isChecked())
        self.th.finishSignal.connect(self.btn_submit_job_finish)
        self.th.start()

    def btn_submit_job_finish(self):
        logging.debug("Submit finished.")
        self.progressBar.setValue(90)
        logging.info("Update local job info.")
        self.load_job()
        self.progressBar.setValue(100)

    def btn_download(self):
        self.progressBar.setValue(0)
        idx = self.tableView.currentIndex().row()
        logging.debug("Select index:{}".format(idx))
        logging.debug("Job info:{}".format(self.job_list[idx]))
        data = None
        for i in self.server_data_list:
            if i['user'] == self.job_list[idx]['user'] and i['server'] == self.job_list[idx]['server']:
                logging.debug("Found server {}@{}".format(i['user'], i['server']))

                data = i
                break
        if data is None:
            logging.error("No proper server found.")
            return False
        local = QtWidgets.QFileDialog.getExistingDirectory(None, "选取文件夹", "./")
        download_list = self.lineEdit_5.text().split(" ")
        self.th = download_job(data, proxy=self.checkBox.isChecked(), proxy_host=self.lineEdit.text(),
                               proxy_port=self.spinBox.value(), remote=self.job_list[idx]['work_dir'], local=local,
                               download_list=download_list)
        self.th.finishSignal.connect(self.btn_download_finished)
        self.th.start()

    def btn_download_finished(self, i):
        logging.info("Download finished.")
        self.progressBar.setValue(100)

    def btn_update_jobs(self):
        logging.debug("Button update_jobs clicked.")
        self.progressBar.setValue(0)
        self.th = update_jobs(proxy=self.checkBox.isChecked(), proxy_host=self.lineEdit.text(),
                              proxy_port=self.spinBox.value(), server=self.server)
        self.th.finishSignal.connect(self.btn_update_jobs_update)
        self.th.start()

    def btn_update_jobs_update(self, p):
        self.progressBar.setValue(p)
        if p == 100:
            self.load_job()
            logging.info("Update jobs info success")

    def btn_hide(self):
        self.progressBar.setValue(0)
        idx = self.tableView.currentIndex().row()
        logging.debug("Select row {}.".format(idx))
        job = job_control.jobs()
        job.hide(idx)
        logging.debug("Reload tableview.")
        self.load_job()
        self.progressBar.setValue(100)
