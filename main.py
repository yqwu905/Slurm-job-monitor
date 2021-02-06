import logging
from PyQt5.QtWidgets import QApplication, QMainWindow
import sys
from gui import main_ui


if __name__ == '__main__':
    app = QApplication(sys.argv)
    MainWindow = QMainWindow()
    ui = main_ui()
    logging.basicConfig(stream=ui, format='%(asctime)s - %(levelname)s: %(message)s',
                        level=logging.INFO)
    ui.setupUi(MainWindow)
    MainWindow.show()
    sys.exit(app.exec_())

