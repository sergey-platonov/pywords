#!/usr/bin/python
# -*- coding: utf-8 -*-
import os
import sys
import httplib
import pickle
import random

from PyQt4 import QtGui
from PyQt4 import QtCore
from PyQt4 import QtNetwork
from PyQt4.QtCore import pyqtSignal


# Network related code
class Translator:
    'Connect to a google translate or just lookup in local cahce'

    __words = {}
    __path = os.path.expanduser('~') + '/.pywords/'
    __filename = __path + 'db'

    def __init__(self):
        if not os.path.exists(self.__path):
            os.makedirs(self.__path)

        try:
            inputfile = open(self.__filename, 'rb')
            self.__words = pickle.load(inputfile)
        except:
            pass

    def getword(self, word):
        translation = ''
        if (word in self.__words):
            translation = self.__words[word]
        else:
            translation = self.__tr(word)
            self.__words[word] = translation
            self.__words[translation] = word
            outfile = open(self.__filename, 'wb')
            pickle.dump(self.__words, outfile)

        return translation

    def getkey(self, num):
        keys = list(self.__words.keys())
        return keys[num]

    def size(self):
        return len(self.__words)

    def __tr(self, word):
        connection = httplib.HTTPConnection('translate.google.com')
        connection.request('GET', 'http://translate.google.com/translate_a/t?client=t&text='
            + word + '&sl=auto&tl=ru', '', {'User-Agent': 'Mozilla/5.0'})
        response = connection.getresponse()
        data = response.read()
        i0 = data.index('"') + 1
        i1 = data.index('"', i0)
        return data[i0: i1]


class QWordsServer(QtNetwork.QTcpServer):
    'Receivec connections from a local clients and reads word to translate'

    dataReceived = pyqtSignal('QString')
    port = 13899

    def __init__(self):
        super(QtNetwork.QTcpServer, self).__init__()

        self.listen(QtNetwork.QHostAddress.LocalHost, self.port)
        self.newConnection.connect(self.__session)

    def __session(self):
        socket = self.nextPendingConnection()
        socket.waitForReadyRead(-1)
        word = QtCore.QString.fromUtf8(socket.readAll())
        socket.close()
        self.dataReceived.emit(word)


class QWordsClient(QtNetwork.QTcpSocket):
    'Sends word to a server'

    def __init__(self):
        super(QtNetwork.QTcpSocket, self).__init__()

    def sendWord(self, word):
        self.connectToHost(QtNetwork.QHostAddress.LocalHost, QWordsServer.port)
        self.write(word)
        self.waitForBytesWritten(-1)


# GUI related code
class QWordsWidget(QtGui.QDialog):
    'Widget to check word knowledge'

    def __init__(self):
        super(QWordsWidget, self).__init__()
        self.__initGui()

    def __initGui(self):
        self.label = QtGui.QLabel()
        self.label.setStyleSheet('font: 12pt "Ubuntu";')
        self.edit = QtGui.QLineEdit()
        # create layout
        layout = QtGui.QGridLayout(self)
        # add widgets to layout
        layout.addWidget(self.label, 0, 0)
        layout.addWidget(self.edit, 1, 0)

    def showWord(self, word):
        self.label.setText(word)
        self.show()

    def closeEvent(self, event):
        'just hide dialog'
        event.ignore()
        self.hide()

    def onEnterPressed(self):
        'process inputed text'


class QStatusIcon(QtGui.QSystemTrayIcon):
    'System tray for menu and status checking'

    quitSignal = pyqtSignal()
    showSignal = pyqtSignal()

    def __init__(self, parent):
        path = os.path.expanduser('~') + '/.pywords/pywords.png'
        icon = QtGui.QIcon(path)

        super(QStatusIcon, self).__init__(icon, parent)
        menu = QtGui.QMenu()
        self.showWidgetAction = menu.addAction('Random word')
        self.showWidgetAction.triggered.connect(self.showSignal)
        self.quitAction = menu.addAction('Quit')
        self.quitAction.triggered.connect(self.quitSignal)

        menu.addAction(self.showWidgetAction)
        menu.addAction(self.quitAction)

        self.setContextMenu(menu)


class QGuiCore(QtCore.QObject):

    quitSignal = pyqtSignal()
    showWord = pyqtSignal('QString')
    __translator = Translator()

    def __init__(self):
        super(QGuiCore, self).__init__()
        self.__createIcon()

    def __createIcon(self):
        self.__icon = QStatusIcon(self)
        self.__icon.showSignal.connect(self.askRandomWord)
        self.__icon.quitSignal.connect(self.quitSignal)
        self.__icon.show()

    def translate(self, word):
        tr = self.__translator.getword(str(word))
        self.__icon.showMessage(word, QtCore.QString.fromUtf8(tr),
                QtGui.QSystemTrayIcon.Information, 5000)

    def askRandomWord(self):
        random.seed()
        rnum = random.randrange(self.__translator.size())
        word = self.__translator.getkey(rnum)
        self.showWord.emit(QtCore.QString.fromUtf8(word))


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--server':
        app = QtGui.QApplication(sys.argv)
        gui = QGuiCore()
        gui.quitSignal.connect(app.quit)

        widget = QWordsWidget()
        gui.showWord.connect(widget.showWord)

        server = QWordsServer()
        server.dataReceived.connect(gui.translate)

        sys.exit(app.exec_())
    else:
        sel = os.popen('xsel').read()
        client = QWordsClient()
        client.sendWord(sel)