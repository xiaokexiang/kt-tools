import json
import os
import sys
from functools import reduce

from PyQt5.QtCore import QRegExp
from PyQt5.QtGui import QRegExpValidator
from PyQt5.QtWidgets import QApplication, QWidget, QDialog, QLabel, QLineEdit, QPushButton, \
    QGridLayout, QVBoxLayout, QHBoxLayout, QMessageBox, QComboBox

json_path = './servers.json'


class Main(QWidget):
    def __init__(self):
        super(Main, self).__init__()
        self.resize(400, 200)
        self.setWindowTitle('Kt tools')

        self.ip_label = QLabel('地址:', self)
        self.comboBox = QComboBox(self)

        self.username_label = QLabel('账户:', self)
        self.username_line = QLineEdit(self)

        self.password_label = QLabel('密码:', self)
        self.password_line = QLineEdit(self)

        self.image_label = QLabel('镜像:', self)
        self.image_line = QLineEdit(self)

        self.start_button = QPushButton('启动', self)
        self.add_button = QPushButton('新增', self)

        self.grid_layout = QGridLayout()
        self.h_layout = QHBoxLayout()
        self.v_layout = QVBoxLayout()

        self.servers = []
        self.servers_dict = {}
        self.line_edit_init()
        self.button_init()
        self.layout_init()
        self.combo_box_init()
        self.add_page = Add()

    def layout_init(self):
        self.grid_layout.addWidget(self.ip_label, 0, 0, 1, 1)
        self.grid_layout.addWidget(self.comboBox, 0, 1, 1, 1)
        self.grid_layout.addWidget(self.username_label, 1, 0, 1, 1)
        self.grid_layout.addWidget(self.username_line, 1, 1, 1, 1)
        self.grid_layout.addWidget(self.password_label, 2, 0, 1, 1)
        self.grid_layout.addWidget(self.password_line, 2, 1, 1, 1)
        self.grid_layout.addWidget(self.image_label, 3, 0, 1, 1)
        self.grid_layout.addWidget(self.image_line, 3, 1, 1, 1)
        self.h_layout.addWidget(self.start_button)
        self.h_layout.addWidget(self.add_button)
        self.v_layout.addLayout(self.grid_layout)
        self.v_layout.addLayout(self.h_layout)

        self.setLayout(self.v_layout)

    """
    下拉框初始化
    """

    def combo_box_init(self):
        self.comboBox.setEditable(True)
        self.comboBox.lineEdit().setPlaceholderText('请输入ip地址')
        self.comboBox.setValidator(QRegExpValidator(QRegExp(r'^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){'
                                                            r'3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$')))
        if not os.path.exists(json_path) or 0 == os.path.getsize(json_path):
            with open(json_path, 'w') as f:
                pass
        # 此处读取数据库中的数据
        with open(json_path, encoding='utf-8') as f:
            self.servers = reduce(
                lambda y, x: y if (x['ip'] in [i['ip'] for i in y]) else (lambda z, u: (z.append(u), z))(y, x)[1],
                json.loads(f.read()), [])
            data = [item['ip'] for item in self.servers]
            servers_dict = {data[i]: self.servers[i] for i in range(len(self.servers))}
            self.servers_dict = servers_dict
        # 根据ip回显其他数据
        if data.__len__() != 0:
            self.username_line.setText(servers_dict[data[0]]['username'])
            self.password_line.setText(servers_dict[data[0]]['password'])
            self.image_line.setText(servers_dict[data[0]]['image'])
        self.comboBox.addItems(data)
        self.comboBox.currentIndexChanged.connect(lambda: self.on_combobox_func(self.comboBox, servers_dict))
        self.comboBox.currentTextChanged.connect(lambda: self.on_combobox_func(self.comboBox, servers_dict))

    """
    下拉框校验与回显
    """

    def on_combobox_func(self, combo_box, servers_dict):
        if len(combo_box.currentText()) != 0 and combo_box.currentText() != '' and combo_box.currentText() in servers_dict:
            self.username_line.setText(servers_dict[combo_box.currentText()]['username'])
            self.password_line.setText(servers_dict[combo_box.currentText()]['password'])
            self.image_line.setText(servers_dict[combo_box.currentText()]['image'])
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
        self.start_button.clicked.connect(self.check_sign_in_func)
        self.add_button.clicked.connect(self.show_add_page)

    """
    编辑框校验
    """

    def check_input_func(self):
        if self.comboBox.currentText() and self.username_line.text() and self.password_line.text() and self.image_line.text():
            self.start_button.setEnabled(True)
        else:
            self.start_button.setEnabled(False)

    """
    启动逻辑
    """

    def check_sign_in_func(self):
        self.start_button.setEnabled(False)
        # 校验数据是否存在
        if not self.comboBox.currentText() in self.servers_dict:
            new_item = {
                "ip": self.comboBox.currentText(),
                "username": self.username_line.text(),
                "password": self.password_line.text(),
                "image": self.image_line.text()
            }
            self.servers_dict[self.comboBox.currentText()] = new_item
            self.servers.append(new_item)
            with open(json_path, 'w') as file:
                json.dump(self.servers, file)

            QMessageBox.information(self, 'Information', 'Register Successfully')
            # self.close()
        # self.start_button.setEnabled(True)
        # self.comboBox.clear()
        # self.username_line.clear()
        # self.comboBox.lineEdit().setEnabled(False)
        # self.username_line.setEnabled(False)
        # self.password_line.setEnabled(False)
        # self.image_line.setEnabled(False)

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
    demo = Main()
    demo.show()
    sys.exit(app.exec_())
