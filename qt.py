import hashlib
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import threading
from base64 import b64decode

import paramiko
import yaml
from PyQt5.QtCore import QRegExp, Qt, QThread, pyqtSignal
from PyQt5.QtGui import QRegExpValidator, QIcon
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QLineEdit, QPushButton, \
    QGridLayout, QVBoxLayout, QHBoxLayout, QMessageBox, QComboBox, QTextEdit

favicon_ico = "AAABAAEAEBAAAAEAIABoBAAAFgAAACgAAAAQAAAAIAAAAAEAIAAAAAAAAAQAAAAAAAAAAAAAAAAAAAAAAAD//////////////////////////////////////////////////////////////////////////////////////////////////////////9bW1v+8vLz/vLy8/7y8vP+8vLz/vLy8/7y8vP/W1tb//////////////////////////////////////+Xl5f8bGxv/ERER/xEREf8RERH/ERER/xEREf8RERH/Gxsb/+Xl5f////////////////////////////////9mZmb/ERER/xEREf8RERH/ERER/xEREf8RERH/ERER/xEREf9mZmb////////////////////////////IyMj/EhIS/xEREf8RERH/ERER/xEREf8RERH/ERER/xEREf8RERH/EhIS/8jIyP/////////////////9/f3/QkJC/xEREf8RERH/ERER/xEREf8RERH/GBgY/6mpqf+Wlpb/ERER/xEREf9CQkL//f39////////////pKSk/xEREf8RERH/ERER/xISEv9AQED/PDw8/7q6uv//////qamp/xEREf8RERH/ERER/6SkpP//////9PT0/ycnJ/8RERH/ERER/xUVFf+9vb3/////////////////urq6/xgYGP8RERH/ERER/xEREf8nJyf/9PT0//X19f8pKSn/ERER/xEREf9aWlr/9/f3/9fX1////////////zw8PP8RERH/ERER/xEREf8RERH/KSkp//X19f//////pqam/xEREf8RERH/WVlZ/1ZWVv8gICD/19fX//////9AQED/ERER/xEREf8RERH/ERER/6ampv////////////39/f9DQ0P/ERER/xEREf8RERH/VlZW//f39/+9vb3/EhIS/xEREf8RERH/ERER/0NDQ//9/f3/////////////////ycnJ/xISEv8RERH/ERER/1lZWf9aWlr/FRUV/xEREf8RERH/ERER/xISEv/Jycn///////////////////////////9nZ2f/ERER/xEREf8RERH/ERER/xEREf8RERH/ERER/xEREf9nZ2f/////////////////////////////////5eXl/xsbG/8RERH/ERER/xEREf8RERH/ERER/xEREf8bGxv/5eXl///////////////////////////////////////W1tb/vLy8/7y8vP+8vLz/vLy8/7y8vP+8vLz/1tbW////////////////////////////////////////////////////////////////////////////////////////////////////////////AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=="
config_json = {
    'apiVersion': 'v1',
    'clusters': [{
        'name': 'cluster-ssl',
        'cluster': {
            'certificate-authority': './{local_path}/ca.pem',
            'server': 'https://{ip}:6443'
        }
    }],
    "contexts": [{
        "context": {
            'cluster': 'cluster-ssl',
            'user': 'admin_ssl'
        },
        'name': 'admin@cluster-ssl'
    }],
    'current-context': 'admin@cluster-ssl',
    'kind': 'Config',
    'users': [{
        'name': 'admin_ssl',
        'user': {
            'client-certificate': './{local_path}/admin.pem',
            'client-key': './{local_path}/admin-key.pem'
        }
    }]
}
default_image = 'abcsys.cn:5000/public/kt-connect-shadow:stable'
default_username = 'root'
base_dir = os.path.expanduser('~') + '/.kube/'
icon_name = 'favicon.ico'


class Main(QWidget):
    def __init__(self):
        super(Main, self).__init__()
        self.resize(600, 300)
        self.setWindowTitle('Kt tools from xiaokexiang')
        self.icon_init(favicon_ico, 'favicon.ico')
        self.setWindowIcon(QIcon(icon_name))
        os.remove(icon_name)
        self.ip_label = QLabel('地址:', self)
        self.ip_line = QComboBox(self)
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

        self.prepare_button = QPushButton('1. 校验', self)
        self.start_button = QPushButton('2. 启动', self)
        self.stop_button = QPushButton('3. 停止', self)
        self.delete_button = QPushButton('4. 删除', self)

        self.grid_layout = QGridLayout()
        self.h_layout = QHBoxLayout()
        self.v_layout = QVBoxLayout()

        self.db = sqlite3.connect(base_dir + '/.db')
        self.alive = True
        self.prepare = False
        self.servers = []
        self.servers_dict = {}

        self.line_edit_init()
        self.layout_init()
        self.db_init()
        self.combo_box_init()
        self.button_init()

    def icon_init(self, source, target):
        image = open(target, 'wb')
        image.write(b64decode(source))
        image.close()

    def db_init(self):
        self.db.cursor().execute(
            "CREATE TABLE IF NOT EXISTS HOST("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "ip varchar(15), "
            "username varchar(15), "
            "password varchar(20), "
            "image varchar(50), "
            "connected int default 0, "
            "is_deleted int)"
        )

    def list(self, sql="SELECT DISTINCT * FROM HOST WHERE is_deleted = 0 ORDER BY id DESC", value=None):
        c = self.db.cursor()
        if value is None:
            c.execute(sql)
        else:
            c.execute(sql, value)
        r = c.fetchall()
        self.servers = r
        self.servers_dict = {self.servers[i][1]: self.servers[i] for i in range(len(self.servers))}
        return r

    def exist(self, sql):
        c = self.db.cursor()
        c.execute(sql)
        r = c.fetchall()
        return r.__len__() != 0

    def modified(self, sql, value=None):
        c = self.db.cursor()
        if value is None:
            c.execute(sql)
        else:
            c.execute(sql, value)
        self.db.commit()

    def closeEvent(self, QCloseEvent):
        self.db.close()

    def layout_init(self):
        self.grid_layout.addWidget(self.ip_label, 0, 0, 1, 1)
        self.grid_layout.addWidget(self.ip_line, 0, 1, 1, 1)
        self.grid_layout.addWidget(self.username_label, 1, 0, 1, 1)
        self.grid_layout.addWidget(self.username_line, 1, 1, 1, 1)
        self.grid_layout.addWidget(self.password_label, 2, 0, 1, 1)
        self.grid_layout.addWidget(self.password_line, 2, 1, 1, 1)
        self.grid_layout.addWidget(self.image_label, 3, 0, 1, 1)
        self.grid_layout.addWidget(self.image_line, 3, 1, 1, 1)
        self.grid_layout.addWidget(self.text_label, 4, 0, 1, 1)
        self.grid_layout.addWidget(self.text_line, 4, 1, 1, 1)
        self.h_layout.addWidget(self.prepare_button)
        self.h_layout.addWidget(self.start_button)
        self.h_layout.addWidget(self.stop_button)
        self.h_layout.addWidget(self.delete_button)
        self.v_layout.addLayout(self.grid_layout)
        self.v_layout.addLayout(self.h_layout)

        self.setLayout(self.v_layout)

    """
    下拉框初始化
    """

    def combo_box_init(self):
        self.ip_line.setEditable(True)
        self.ip_line.lineEdit().setPlaceholderText('请输入ip地址')
        self.ip_line.setValidator(QRegExpValidator(QRegExp(r'^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){'r'3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$')))

        self.list()
        data = [item[1] for item in self.servers]
        if self.servers.__len__() != 0:
            self.username_line.setText(self.servers_dict[data[0]][2])
            self.password_line.setText(self.servers_dict[data[0]][3])
            self.image_line.setText(self.servers_dict[data[0]][4])
        self.ip_line.addItems(data)
        self.ip_line.currentIndexChanged.connect(lambda: self.on_combobox_func(self.ip_line, self.servers_dict))
        self.ip_line.currentTextChanged.connect(lambda: self.on_combobox_func(self.ip_line, self.servers_dict))

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
        self.ip_line.currentTextChanged.connect(self.check_input_func)
        self.username_line.textChanged.connect(self.check_input_func)
        self.password_line.textChanged.connect(self.check_input_func)
        self.image_line.textChanged.connect(self.check_input_func)

    """
    按钮初始化
    """

    def button_init(self):
        if self.ip_line.currentText() is None or not self.ip_line.currentText() in self.servers_dict:
            self.prepare_button.setEnabled(False)
            self.start_button.setEnabled(False)
            self.stop_button.setEnabled(False)
            self.delete_button.setEnabled(False)
        else:
            on = self.ip_line.currentText() in self.servers_dict and self.servers_dict[self.ip_line.currentText()][5] == 1
            self.prepare_button.setEnabled(on)
            self.start_button.setEnabled(on)
            self.stop_button.setEnabled(False)
            self.delete_button.setEnabled(self.ip_line.currentText() in self.servers_dict)
        self.prepare_button.clicked.connect(self.prepare_func)
        self.start_button.clicked.connect(self.start_func)
        self.stop_button.clicked.connect(self.stop_func)
        self.delete_button.clicked.connect(self.delete_func)

    """
    编辑框校验
    """

    def check_input_func(self):
        if self.ip_line.currentText() and self.password_line.text():
            self.prepare_button.setEnabled(True)
            self.start_button.setEnabled(self.ip_line.currentText() in self.servers_dict and self.servers_dict[self.ip_line.currentText()][5] == 1)
            self.delete_button.setEnabled(True)
        else:
            self.start_button.setEnabled(False)
            self.prepare_button.setEnabled(False)
            self.delete_button.setEnabled(False)
            self.stop_button.setEnabled(False)

    def text_append_text(self, text):
        self.text_line.append(text)
        self.text_line.moveCursor(self.text_line.textCursor().End)
        self.text_line.ensureCursorVisible()

    def show_error(self, message):
        self.text_append_text(message)
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Critical)
        msg.setText("错误")
        msg.setInformativeText(message)
        msg.setWindowTitle("错误")
        msg.exec_()

    def show_info(self, message):
        self.text_append_text(message)

    """
    校验
    """

    def prepare_func(self):
        self.worker = PrepareThread(self.ip_line.currentText(),
                                    default_username if self.username_line.text() == '' else self.username_line.text(),
                                    self.password_line.text(),
                                    default_image if self.image_line.text() == '' else self.image_line.text())
        self.worker.error.connect(self.show_error)
        self.worker.info.connect(self.show_info)
        self.worker.res.connect(self.post_prepare)
        self.worker.start()

    """
    校验回调
    """

    def post_prepare(self, info):
        self.start_button.setEnabled(True)
        info_dict = dict(json.loads(info))
        ip = info_dict['ip']
        username = info_dict['username']
        password = info_dict['password']
        image = info_dict['image']
        if self.exist(sql="SELECT * FROM HOST WHERE ip = '{0}' AND is_deleted = 0".format(ip)):
            self.modified("UPDATE HOST SET username = ?, password = ?, image = ?, connected = 1 WHERE ip = ?", (username, password, image, ip))
        else:
            self.modified("INSERT INTO HOST(ip, username, password, image, connected) VALUES (?,?,?,?,?)", (ip, username, password, image, 1))
            self.ip_line.insertItem(0, ip)
            self.username_line.setText(username)
            self.password_line.setText(password)
            self.image_line.setText(image)
        self.list()
        self.start_button.setEnabled(True)

    """
    启动
    """

    def start_func(self):
        self.start_button.setEnabled(False)
        self.alive = True
        self.username_line = default_username if self.username_line is None else self.username_line
        self.image_line = default_image if self.image_line is None else self.image_line
        # 校验数据是否存在
        if not self.ip_line.currentText() in self.servers_dict:
            self.modified("INSERT INTO HOST(ip, username, password, image, is_deleted) VALUES (?,?,?,?,?) ", (self.ip_line.currentText(),
                                                                                                              self.username_line.text(),
                                                                                                              self.password_line.text(),
                                                                                                              self.image_line.text(),
                                                                                                              0))
            self.list()
            self.ip_line.insertItem(0, self.ip_line.currentText())
        if not self.start_button.isEnabled():
            if os.path.exists(os.path.expanduser('~') + '/.ktctl/pid'):
                os.remove(os.path.expanduser('~') + '/.ktctl/pid')
            threading.Thread(target=self.execute_command,
                             args=('ktctl -i {image_name} --namespace=kube-system connect --method=socks5 --dump2hosts'.format(image_name=self.image_line.text()),)) \
                .start()
        self.ip_line.setEnabled(False)
        self.username_line.setEnabled(False)
        self.password_line.setEnabled(False)
        self.image_line.setEnabled(False)
        self.stop_button.setEnabled(True)

    """
    停止
    """

    def stop_func(self):
        self.alive = False
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.text_line.clear()
        self.ip_line.setEnabled(True)
        self.username_line.setEnabled(True)
        self.password_line.setEnabled(True)
        self.image_line.setEnabled(True)

    """
    删除
    """

    def delete_func(self):
        reply = QMessageBox.question(self, '提示', '是否删除？', QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.modified("UPDATE HOST SET is_deleted = 1 WHERE ip = '{0}'".format(self.ip_line.currentText()))
            self.list()
            self.ip_line.removeItem(0)
            self.text_line.clear()
            QMessageBox.information(QWidget(), "提示", "删除成功！", QMessageBox.Ok)

    def read_output(self, process):
        while self.alive:
            output = process.stdout.readline()
            if output == '' and process.poll() is not None:
                break
            if output:
                self.text_append_text(re.sub(r'\x1B\[[0-?]*[ -/]*[@-~]', '', output.strip().decode('GBK')))  # kt有ANSI转义符

    def execute_command(self, command):
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)
        thread = threading.Thread(target=self.read_output, args=(process,))
        thread.start()


class PrepareThread(QThread):
    error = pyqtSignal(str)
    info = pyqtSignal(str)
    res = pyqtSignal(str)

    def __init__(self, ip, username, password, image):
        super().__init__()
        self.ip = ip
        self.username = username
        self.password = password
        self.image = image

    def run(self):
        self.prepare_validate()

    def prepare_validate(self):
        username = self.username
        password = self.password
        ip = self.ip
        if self.check_ssh(ip, username, password):
            if self.sftp_transfer(ip, 22, username, password):
                self.generate_config()

    """
    ssh 校验
    """

    def check_ssh(self, ip, username, password):
        self.info.emit('正在校验用户名密码，请稍等...')
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            ssh.connect(ip, username=username, password=password, timeout=10)
            self.info.emit('用户名密码正确，服务器: {0}登录成功！'.format(self.ip))
            return True
        except Exception as e:
            self.error.emit("用户名密码正确，服务器: {0}登录失败，错误原因: {1}".format(self.ip, e.args[0]))
            return False

    def sftp_transfer(self, ip, port, username, password):
        local_path = base_dir + ip + '/'
        server_path = '/etc/kubernetes/pki/'
        if os.path.exists(local_path) and os.listdir(local_path):
            self.info.emit('kubernetes pki文件夹已存在！对文件夹内的文件依次进行比对！')
            t = paramiko.Transport(ip, port)
            t.connect(username=username, password=password)
            sftp = paramiko.SFTPClient.from_transport(t)
            remote_files = sftp.listdir(server_path)
            for file in os.listdir(local_path):
                local_file = os.path.join(local_path, file)
                remote_file = os.path.join(server_path, file)
                if file in remote_files:
                    local_md5 = self.md5(local_file)
                    remote_file_obj = sftp.file(remote_file)
                    remote_md5 = hashlib.md5(remote_file_obj.read()).hexdigest()
                    remote_file_obj.close()
                    if local_md5 != remote_md5:
                        self.info.emit('服务器与本地的文件{0}不同，重新同步！'.format(file))
                        sftp.get(remote_file, local_file)
            t.close()
            self.info.emit('kubernetes pki文件夹已存在！文件认证对比结束！')
            return True
        else:
            try:
                if os.path.exists(local_path):
                    shutil.rmtree(local_path)
                self.info.emit('正在传输kubernetes pki文件，请稍等！\r')
                os.makedirs(local_path)
                t = paramiko.Transport(ip, port)
                t.connect(username=username, password=password)
                sftp = paramiko.SFTPClient.from_transport(t)
                remote_files = sftp.listdir(server_path)
                for file in remote_files:
                    local_file = local_path + file
                    remote_file = server_path + file
                    if not os.path.exists(local_file):
                        sftp.get(remote_file, local_file)
                self.info.emit("文件传输完成，正在启动kt-connect！\r")
                t.close()
                return True
            except Exception as e:
                self.info.emit('传输kubernetes pki文件失败，错误原因: {0}'.format(e.args[0]))
                shutil.rmtree(local_path)
                return False

    def generate_config(self):
        file = open(base_dir + 'config', 'w', encoding='utf-8')
        yaml.dump(json.loads(json.dumps(config_json).replace('{local_path}', self.ip).replace('{ip}', self.ip)), file)
        file.close()
        self.res.emit(json.dumps({"ip": self.ip, "username": self.username, "password": self.password, "image": self.image}))

    def md5(self, file_path):
        md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                md5.update(chunk)
        return md5.hexdigest()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    main = Main()
    main.show()
    sys.exit(app.exec_())
