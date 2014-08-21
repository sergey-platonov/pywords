#!/usr/bin/python
# -*- coding: utf-8 -*-
import os
import sys
import httplib
import pickle
import random
import string
import Xlib.display

from PyQt4 import QtGui
from PyQt4 import QtCore
from PyQt4 import QtNetwork
from PyQt4.QtCore import Qt, QString, pyqtSignal

g_homedir = os.path.expanduser('~') 
g_confdir = g_homedir + '/.pywords/'
g_lang = 'ru'

if not os.path.exists(g_confdir):
    os.makedirs(g_confdir)

# Network related code
class Translator:
    'Connect to a google translate or just lookup in local cahce'

    __words = {}
    __filename = g_confdir + 'db'

    def __init__(self):
        try:
            inputfile = open(self.__filename, 'rb')
            self.__words = pickle.load(inputfile)
        except:
            pass

    def getword(self, word):
        if word == '':
            return ''

        translation = ''
        if word in self.__words:
            translation = self.__words[word]['tr']
        else:
            translation = self.__tr(word)
            if translation != '':
                self.__words[word] = {'tr': translation, 'weight': 1}
                self.__words[translation] = {'tr': word, 'weight': 1}
                self.__store()

        return translation

    def __store(self):
        outfile = open(self.__filename, 'wb')
        pickle.dump(self.__words, outfile)


    def __getkey(self, num):
        keys = list(self.__words.keys())
        return keys[num]

    def size(self):
        return len(self.__words)

    def __tr(self, word):
        lang = g_lang
        if not self.__is_ascii(word):
            lang = 'en'

        connection = httplib.HTTPConnection('translate.google.com')
        connection.request('GET', 'http://translate.google.com/translate_a/t?client=t&text='
            + word + '&sl=auto&tl=' + lang, '', {'User-Agent': 'Mozilla/5.0'})
        response = connection.getresponse()
        data = response.read()
        i0 = data.index('"') + 1
        i1 = data.index('"', i0)
        return data[i0: i1]

    def answer(self, word, correct):
        'if answer is correct weight of the word decreasing, otherwise increasing'

        weight = 0
        if correct:
            weight = self.__words[word]['weight'] - 0.2
        else:
            weight = self.__words[word]['weight'] + 0.2

        if weight <= 0:
            weight = 0.01

        tr = self.__words[word]['tr']
        self.__words[word] = {'tr': tr, 'weight': weight}

    # http://eli.thegreenplace.net/2010/01/22/weighted-random-generation-in-python/
    def randomword(self):
        weights = map(lambda t: self.__words[t]['weight'], self.__words)
        #print weights
        rnd = random.random() * sum(weights)
        for i, w in enumerate(weights):
            rnd -= w
            if rnd < 0:
                return self.__getkey(i)

    def __is_ascii(self, word):
        return all(ord(c) < 128 for c in word)

    def delete(self, word):
        tr = self.getword(word)
        self.__words.pop(tr, None)
        self.__words.pop(word, None)
        self.__store()

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
        data = socket.readAll()
        word = QtCore.QString.fromUtf8(data)
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

    answer = pyqtSignal('QString', bool)
    showed = pyqtSignal(bool)
    delete = pyqtSignal('QString')

    def __init__(self):
        super(QWordsWidget, self).__init__()
        self.__initGui()
        self.__translationVisible = False
        self.__answerGiven = False

    def __initGui(self):
        self.setWindowTitle('Translate')
        self.setMaximumSize(240, 180)
        self.setMinimumSize(240, 80)

        self.label = QtGui.QLabel(self)
        self.label.setStyleSheet('font: 11pt "Ubuntu";')
        self.label.setSizePolicy(QtGui.QSizePolicy.Fixed, QtGui.QSizePolicy.Fixed)

        self.lbutton = QtGui.QPushButton(self)
        self.lbutton.setSizePolicy(QtGui.QSizePolicy.Fixed, QtGui.QSizePolicy.Fixed)
        self.lbutton.setFlat(True)
        self.lbutton.setText('>')
        self.lbutton.setMaximumWidth(30)
        self.lbutton.pressed.connect(self.onButtonPressed)

        self.delbutton = QtGui.QPushButton(self)
        self.delbutton.setSizePolicy(QtGui.QSizePolicy.Fixed, QtGui.QSizePolicy.Fixed)
        self.delbutton.setFlat(True)
        self.delbutton.setText('x')
        self.delbutton.setToolTip('Do not ask this word again')
        self.delbutton.pressed.connect(self.onDeleteWord)

        self.translation = QtGui.QLabel(self)
        self.translation.setStyleSheet('font: 11pt "Ubuntu";')
        self.translation.setSizePolicy(QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Minimum)
        self.translation.setVisible(False)

        self.edit = QtGui.QLineEdit(self)
        self.edit.setStyleSheet('font: 11pt "Ubuntu";')
        #self.edit.setSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Expanding)
        self.edit.installEventFilter(self)

        # create layout
        self.layout = QtGui.QGridLayout(self)
        self.layout.setVerticalSpacing(6)
        # add widgets to layout
        self.layout.addWidget(self.label, 0, 0, 1, 2)
        self.layout.addWidget(self.edit, 1, 0, 1, 2)
        self.layout.addWidget(self.lbutton, 2, 0)
        self.layout.addWidget(self.delbutton, 2, 1)

        self.setLayout(self.layout)

    def showWord(self, word, tr):
        if not self.isVisible():
            self.label.setText(word)
            self.translation.setText(tr)
            self.edit.setText('')
            self.edit.setStyleSheet('font: 11pt "Ubuntu";')
            self.edit.setFocus()
            self.__answerGiven = False
            self.show()
            self.showed.emit(True)

    def closeEvent(self, event):
        'just hide dialog'

        if event != None: 
            event.ignore()

        self.__hideTranslation()
        self.hide()
        self.showed.emit(False)

    def onEnterPressed(self):
        'process inputed text'
        self.__showTranslation()

    def onButtonPressed(self):
        'show translation if button was pressed'

        if self.__translationVisible:
            self.__hideTranslation()
        else:
            self.__showTranslation()

        self.edit.setFocus()

    def onDeleteWord(self):
        word = self.label.text()
        self.delete.emit(word)
        self.close()

    def reject(self):
        self.close()


    def eventFilter(self, receiver, event):
        'event filter to get enter press event'
        if (event.type() == QtCore.QEvent.KeyPress and (event.key() == Qt.Key_Return
                    or event.key() == Qt.Key_Enter)):
            self.onEnterPressed()
            return True
        else:
            return super(QWordsWidget, self).eventFilter(receiver, event)

    def __showTranslation(self):
        if not self.__translationVisible:
            self.setFixedHeight(self.height() + 30)
            self.layout.addWidget(self.translation, 3, 0, 1, 2)
            self.translation.setVisible(True)
            self.lbutton.setText('v')
            self.__translationVisible = True
            correct = self.edit.text() == self.translation.text()
            self.__giveAnswer(correct)

    def __hideTranslation(self):
        if self.__translationVisible:
            self.translation.setVisible(False)
            self.layout.removeWidget(self.translation)
            self.setFixedHeight(self.height() - 30)
            self.lbutton.setText('>')
            self.__translationVisible = False

    def __giveAnswer(self, correct):
        if not self.__answerGiven:
            self.__answerGiven = True
            self.answer.emit(self.label.text(), correct)
            css = self.edit.styleSheet()
            if correct:
                css = css + 'background-color: rgb(148, 220, 135);'  # green
                QtCore.QTimer.singleShot(1000, self.close)
            else:
                css = css + 'background-color: rgb(237, 121, 121);'  # red
            self.edit.setStyleSheet(css)


class QStatusIcon(QtGui.QSystemTrayIcon):
    'System tray for menu and status checking'

    quitSignal = pyqtSignal()
    showSignal = pyqtSignal()

    def __init__(self, parent):
        path = os.path.expanduser('~') + g_confdir
        icon_main = QtGui.QIcon(path + '/pywords.png')
        icon_quit = QtGui.QIcon(path + '/quit.png')
        icon_question = QtGui.QIcon(path + '/question.png')

        super(QStatusIcon, self).__init__(icon_main, parent)
        menu = QtGui.QMenu()
        self.showWidgetAction = menu.addAction(icon_question, 'Random word')
        self.showWidgetAction.triggered.connect(self.showSignal)
        self.quitAction = menu.addAction(icon_quit, 'Quit')
        self.quitAction.triggered.connect(self.quitSignal)

        menu.addAction(self.showWidgetAction)
        menu.addAction(self.quitAction)

        self.setContextMenu(menu)

    def setShowActionEnabled(self, vis):
        self.showWidgetAction.setEnabled(vis)


class QGuiCore(QtCore.QObject):

    quitSignal = pyqtSignal()
    showWord = pyqtSignal('QString', 'QString')
    translator = Translator()

    def __init__(self):
        super(QGuiCore, self).__init__()
        self.__createIcon()
        random.seed()
        self.__timer = QtCore.QTimer()
        self.__timer.timeout.connect(self.askRandomWord)
        self.__timer.start(30 * 60 * 1000)  # ms

    def __createIcon(self):
        self.__icon = QStatusIcon(self)
        self.__icon.showSignal.connect(self.askRandomWord)
        self.__icon.quitSignal.connect(self.quitSignal)
        self.__icon.show()

    def translate(self, word):
        tr = self.translator.getword(str(word.toUtf8()))
        self.__icon.showMessage(word, QtCore.QString.fromUtf8(tr),
                QtGui.QSystemTrayIcon.Information, 5000)

    def askRandomWord(self):
        if self.translator.size() == 0 or self.__isFullscreen():
            return

        word = self.translator.randomword()

        tr = self.translator.getword(word)
        self.showWord.emit(QString.fromUtf8(word), QString.fromUtf8(tr))

    def answer(self, word, correct):
        self.translator.answer(str(word.toUtf8()), correct)

    def deleteWord(self, word):
        self.translator.delete(str(word.toUtf8()))

    def __isFullscreen(self):
        'detect if system working in fullscreen, so wee do not want to interupt it'
        screen = Xlib.display.Display().screen()
        root_win = screen.root

        num_of_fs = 0
        for window in root_win.query_tree()._data['children']:
            width = window.get_geometry()._data["width"]
            height = window.get_geometry()._data["height"]
            if width == screen.width_in_pixels and height == screen.height_in_pixels:
                num_of_fs += 1

        return num_of_fs > 1

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--server':
        app = QtGui.QApplication(sys.argv)
        gui = QGuiCore()
        gui.quitSignal.connect(app.quit)

        widget = QWordsWidget()
        gui.showWord.connect(widget.showWord)
        widget.answer.connect(gui.answer)
        #widget.showed.connect()
        widget.delete.connect(gui.deleteWord)

        server = QWordsServer()
        server.dataReceived.connect(gui.translate)

        sys.exit(app.exec_())
    else:
        sel = os.popen('xsel').read()
        client = QWordsClient()
        client.sendWord(sel)