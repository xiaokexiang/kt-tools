import os
import os
import re
import sqlite3
import subprocess
import sys
import threading

from PyQt5.QtCore import QRegExp, Qt
from PyQt5.QtGui import QRegExpValidator
from PyQt5.QtWidgets import QApplication, QWidget, QDialog, QLabel, QLineEdit, QPushButton, \
    QGridLayout, QVBoxLayout, QHBoxLayout, QMessageBox, QComboBox, QTextEdit

json_path = './servers.json'
log_path = './.log'


class Main(QWidget):
    def __init__(self):
        super(Main, self).__init__()
        self.resize(500, 300)
        self.setWindowTitle('Kt tools')

        self.ip_label = QLabel('地址:', self)
        self.comboBox = QComboBox(self)
        self.username_label = QLabel('账户:', self)
        self.username_line = QLineEdit(self)
        self.password_label = QLabel('密码:', self)
        self.password_line = QLineEdit(self)
        self.image_label = QLabel('镜像:', self)
        self.image_line = QLineEdit(self)
        self.text_label = QLabel('日志:', self)
        self.text_line = QTextEdit(self)
        self.text_line.setReadOnly(True)
        self.text_line.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.text_line.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.start_button = QPushButton('启动', self)
        self.stop_button = QPushButton('停止', self)
        self.add_button = QPushButton('新增', self)

        self.grid_layout = QGridLayout()
        self.h_layout = QHBoxLayout()
        self.v_layout = QVBoxLayout()

        self.db = sqlite3.connect('./.db')
        self.alive = True
        self.servers = []
        self.servers_dict = {}

        self.line_edit_init()
        self.button_init()
        self.layout_init()
        self.db_init()
        self.combo_box_init()
        self.add_page = Add()

    def db_init(self):
        self.db.cursor().execute("CREATE TABLE IF NOT EXISTS HOST(id INTEGER PRIMARY KEY AUTOINCREMENT, ip varchar(15), username varchar(15), password varchar(20), image varchar(50), is_deleted int)")

    def closeEvent(self, QCloseEvent):
        self.db.close()

    def layout_init(self):
        self.grid_layout.addWidget(self.ip_label, 0, 0, 1, 1)
        self.grid_layout.addWidget(self.comboBox, 0, 1, 1, 1)
        self.grid_layout.addWidget(self.username_label, 1, 0, 1, 1)
        self.grid_layout.addWidget(self.username_line, 1, 1, 1, 1)
        self.grid_layout.addWidget(self.password_label, 2, 0, 1, 1)
        self.grid_layout.addWidget(self.password_line, 2, 1, 1, 1)
        self.grid_layout.addWidget(self.image_label, 3, 0, 1, 1)
        self.grid_layout.addWidget(self.image_line, 3, 1, 1, 1)
        self.grid_layout.addWidget(self.text_label, 4, 0, 1, 1)
        self.grid_layout.addWidget(self.text_line, 4, 1, 1, 1)
        self.h_layout.addWidget(self.start_button)
        self.h_layout.addWidget(self.stop_button)
        self.h_layout.addWidget(self.add_button)
        self.v_layout.addLayout(self.grid_layout)
        self.v_layout.addLayout(self.h_layout)

        self.setLayout(self.v_layout)

    def query(self, sql=None):
        c = self.db.cursor()
        c.execute("SELECT DISTINCT * FROM HOST WHERE is_deleted = 0 ORDER BY id DESC" if sql is None else sql)
        self.servers = c.fetchall()
        self.servers_dict = {self.servers[i][1]: self.servers[i] for i in range(len(self.servers))}

    def insert(self, sql, value):
        c = self.db.cursor()
        c.execute(sql, value)
        self.db.commit()

    """
    下拉框初始化
    """

    def combo_box_init(self):
        self.comboBox.setEditable(True)
        self.comboBox.lineEdit().setPlaceholderText('请输入ip地址')
        self.comboBox.setValidator(QRegExpValidator(QRegExp(r'^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){'r'3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$')))

        self.query()
        data = [item[1] for item in self.servers]
        if self.servers.__len__() != 0:
            self.username_line.setText(self.servers_dict[data[0]][2])
            self.password_line.setText(self.servers_dict[data[0]][3])
            self.image_line.setText(self.servers_dict[data[0]][4])
        self.comboBox.addItems(data)
        self.comboBox.currentIndexChanged.connect(lambda: self.on_combobox_func(self.comboBox, self.servers_dict))
        self.comboBox.currentTextChanged.connect(lambda: self.on_combobox_func(self.comboBox, self.servers_dict))

    """
    下拉框校验与回显
    """

    def on_combobox_func(self, combo_box, servers_dict):
        if len(combo_box.currentText()) != 0 and combo_box.currentText() != '' and combo_box.currentText() in servers_dict:
            self.username_line.setText(servers_dict[combo_box.currentText()][2])
            self.password_line.setText(servers_dict[combo_box.currentText()][3])
            self.image_line.setText(servers_dict[combo_box.currentText()][4])
        else:
            self.username_line.clear()
            self.password_line.clear()
            self.image_line.clear()

    """
    编辑框初始化
    """

    def line_edit_init(self):
        self.username_line.setPlaceholderText('请输入账户(不填默认root)')
        self.username_line.setMaxLength(10)
        self.password_line.setPlaceholderText('请输入密码')
        self.username_line.setMaxLength(15)
        self.image_line.setPlaceholderText('请输入镜像(默认abcsys.cn:5000/public/kt-connect-shadow:stable)')
        self.comboBox.currentTextChanged.connect(self.check_input_func)
        self.username_line.textChanged.connect(self.check_input_func)
        self.password_line.textChanged.connect(self.check_input_func)
        self.image_line.textChanged.connect(self.check_input_func)

    """
    按钮初始化
    """

    def button_init(self):
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(False)
        self.start_button.clicked.connect(self.start_func)
        self.stop_button.clicked.connect(self.stop_func)
        self.add_button.clicked.connect(self.show_add_page)

    """
    编辑框校验
    """

    def check_input_func(self):
        if self.comboBox.currentText() and self.username_line.text() and self.password_line.text() and self.image_line.text():
            self.start_button.setEnabled(True)
        else:
            self.start_button.setEnabled(False)

    def text_append_text(self, text):
        self.text_line.append(text)
        self.text_line.moveCursor(self.text_line.textCursor().End)
        self.text_line.ensureCursorVisible()

    """
    启动逻辑
    """

    def start_func(self):
        self.start_button.setEnabled(False)
        self.alive = True
        # 校验数据是否存在
        if not self.comboBox.currentText() in self.servers_dict:
            self.insert("INSERT INTO HOST(ip, username, password, image, is_deleted) VALUES (?,?,?,?,?) ", (self.comboBox.currentText(),
                                                                                                            self.username_line.text(),
                                                                                                            self.password_line.text(),
                                                                                                            self.image_line.text(),
                                                                                                            0))
            self.query()
            self.comboBox.insertItem(0, self.comboBox.currentText())
        if not self.start_button.isEnabled():
            if os.path.exists(os.path.expanduser('~') + '/.ktctl/pid'):
                os.remove(os.path.expanduser('~') + '/.ktctl/pid')
            threading.Thread(target=self.execute_command,
                             args=('ktctl -d -i abcsys.cn:5000/public/kt-connect-shadow:stable  --namespace=kube-system connect --method=socks5 --dump2hosts',)) \
                .start()
        QMessageBox.information(self, 'Info', '启动成功！')
        self.comboBox.setEnabled(False)
        self.username_line.setEnabled(False)
        self.password_line.setEnabled(False)
        self.image_line.setEnabled(False)
        self.stop_button.setEnabled(True)

    """
    停止逻辑
    """

    def stop_func(self):
        self.alive = False
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.text_line.clear()
        self.comboBox.setEnabled(True)
        self.username_line.setEnabled(True)
        self.password_line.setEnabled(True)
        self.image_line.setEnabled(True)

    def read_output(self, process):
        while True:
            if not self.alive:
                break
            output = process.stdout.readline()
            if output == '' and process.poll() is not None:
                break
            if output:
                self.text_append_text(re.sub(r'\x1B\[[0-?]*[ -/]*[@-~]', '', output.strip().decode('GBK')))  # kt有ANSI转义符

    def execute_command(self, command):
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)
        thread = threading.Thread(target=self.read_output, args=(process,))
        thread.start()
        thread.join()

    def show_add_page(self):
        self.add_page.exec_()


class Add(QDialog):
    def __init__(self):
        super(QDialog, self).__init__()
        self.resize(400, 200)
        self.ip_address_label = QLabel('Ip地址:', self)
        self.username_label = QLabel('用户名:', self)
        self.password_label = QLabel('密码:', self)
        self.ip_address_line = QLineEdit(self)
        self.username_line = QLineEdit(self)
        self.password_line = QLineEdit(self)
        self.do_add_button = QPushButton('确认', self)
        self.do_cancel_button = QPushButton('取消', self)

        self.ip_h_layout = QHBoxLayout()
        self.username_h_layout = QHBoxLayout()
        self.password_h_layout = QHBoxLayout()
        self.h_layout = QHBoxLayout()
        self.all_v_layout = QVBoxLayout()
        self.button_init()
        self.line_edit_init()
        self.layout_init()

    def layout_init(self):
        self.ip_h_layout.addWidget(self.ip_address_label)
        self.ip_h_layout.addWidget(self.ip_address_line)
        self.username_h_layout.addWidget(self.username_label)
        self.username_h_layout.addWidget(self.username_line)
        self.password_h_layout.addWidget(self.password_label)
        self.password_h_layout.addWidget(self.password_line)

        self.all_v_layout.addLayout(self.ip_h_layout)
        self.all_v_layout.addLayout(self.username_h_layout)
        self.all_v_layout.addLayout(self.password_h_layout)
        self.h_layout.addWidget(self.do_add_button)
        self.h_layout.addWidget(self.do_cancel_button)
        self.all_v_layout.addLayout(self.h_layout)
        self.setLayout(self.all_v_layout)

    def line_edit_init(self):
        self.ip_address_line.setPlaceholderText('请输入ip地址')
        self.username_line.setPlaceholderText('请输入用户名')
        self.password_line.setPlaceholderText('请输入密码')
        self.ip_address_line.textChanged.connect(self.check_input_func)
        self.username_line.textChanged.connect(self.check_input_func)
        self.password_line.textChanged.connect(self.check_input_func)

    def check_input_func(self):
        if self.ip_address_line.text() and self.username_line.text() and self.password_line.text():
            self.do_add_button.setEnabled(True)
        else:
            self.do_add_button.setEnabled(False)

    def button_init(self):
        self.do_add_button.setEnabled(False)
        self.do_add_button.clicked.connect(self.check_do_add_func)
        self.do_cancel_button.clicked.connect(self.check_do_cancel_func)

    def check_do_add_func(self):
        QMessageBox.information(self, 'Information', '新增成功！')

    def check_do_cancel_func(self):
        self.close()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    main = Main()
    main.show()
    sys.exit(app.exec_())
