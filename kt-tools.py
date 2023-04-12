import json
import os
import re
import shutil
import sys
import time
from functools import reduce

"""
1. 支持删除
2. 支持ssh
3. 支持md5文件比对kubernetes pki
"""
import IPy
import paramiko
import yaml

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


def kt():
    try:
        print('------------------> kt-tools version: 0.1.0 <------------------')
        base_dir = os.path.expanduser('~') + '/.kube/'
        servers_file = base_dir + 'servers.json'
        config_path = base_dir + 'config'
        select, server = check_file(servers_file)
        if select and bool(server):
            server = dict(server)
            ip = server.get('ip')
            username = server.get('username')
            password = server.get('password')
            image = server.get('image')
        else:
            ip = None
            while ip is None or ip == '':
                ip = input('请输入IP地址: ')
            time.sleep(0.5)
            username = input('请输入用户名称（回车跳过）: ')
            time.sleep(0.5)
            username = 'root' if username is None or username == '' else username
            password = input('请输入密码: ')
            while password is None or password == '':
                password = input('请输入密码: ')
            time.sleep(0.5)
            image = input('请输入镜像名（回车跳过）: ')
            image = 'abcsys.cn:5000/public/kt-connect-shadow:stable' if image is None or image == '' else image
        # if not ssh_connect(ip, username, password):
        #     input('按任意键退出！')
        #     exit(0)
        # else:
        if not sftp_transfer(ip, 22, username, password, base_dir, '/etc/kubernetes/pki/'):
            raise NameError
        else:
            store_servers(ip, username, password, image, servers_file)
            generate_config(ip, config_path)
            exec_command()
    except NameError as e:
        input('按任意键推出...')
        exit(100)
    except Exception as e:
        print('未知异常: {0}'.format(e.args[0]))
        input('按任意键推出...')
        exit(101)


def check_file(servers_file):
    if not os.path.exists(servers_file) or 0 == os.path.getsize(servers_file):
        return False, {}
    try:
        with open(servers_file, encoding='utf-8') as f:
            servers = dict(json.loads(f.read())).get('servers')
            console_txt = '当前环境下已有的服务列表: \r\n'
            result = {}
            for index, s in enumerate(servers):
                server = dict(s)
                console_txt = console_txt + ' {0}. 地址: {1}, 用户名: {2}, 密码: {3}, 镜像: {4}\r\n'.format(
                    index + 1,
                    server.get('ip'),
                    server.get('username'),
                    server.get('password'),
                    server.get('image'))
                result[index + 1] = server
            loop = 1
            while True:
                if loop == 1:
                    console_txt = console_txt if '请输入序号选择节点: （回车新增节点，0删除节点）\r\n' in console_txt else console_txt + '请输入序号选择节点: （回车新增节点，0删除节点）\r\n'
                    select = input(console_txt)
                    if select.isdigit():
                        loop = 2
                    elif select == '':
                        return True, {}
                    elif result.get(int(select)) is not None:
                        return True, result.get(int(select))
                elif loop == 2:
                    if select == '0':
                        ip_ids = input('请输入需要删除的节点id（多个节点请用逗号分割，输入0返回上一级）\r\n')
                        if ip_ids == '0':
                            loop = 1
                        elif re.findall(r'(?!0)\b\d+(,\d+)*\b', ip_ids).__len__() == 1:
                            print(123)
                            return True, {}
                        else:
                            continue

                    if ip_ids is None or ip_ids == '' or re.fullmatch(r'\d+(,\d+)*', s) is not None:
                        continue
    except Exception as e:
        return False, {}


def check_ip(ip):
    try:
        IPy.IP(ip)
        return True
    except Exception as e:
        return False


def generate_time():
    return time.strftime("%Y/%m/%d %H:%M:%S", time.localtime())


def ssh_connect(ip, username, password):
    print('正在尝试ssh登录到服务器: {0}，请稍等！'.format(ip))
    ssh = paramiko.SSHClient()
    key = paramiko.AutoAddPolicy()
    ssh.set_missing_host_key_policy(key)
    try:
        ssh.connect(ip, 22, username, password, timeout=15)
        print('服务器: {0}登录成功！'.format(ip))
        return True
    except Exception as e:
        print("服务器: {0}登录失败，错误原因: {1}".format(ip, e.args[0]))
        return False


def sftp_transfer(ip, port, username, password, local_path, server_path):
    local_path = local_path + ip + '/'
    if os.path.exists(local_path) and not not os.listdir(local_path):
        print('kubernetes pki文件夹已存在，跳过ssh验证与sftp传输！')
        return True
    else:
        try:
            if os.path.exists(local_path):
                shutil.rmtree(local_path)
            print('正在传输kubernetes pki文件，请稍等！\r')
            os.makedirs(local_path)
            t = paramiko.Transport(ip, port)
            t.connect(username=username, password=password)
            sftp = paramiko.SFTPClient.from_transport(t)
            remote_files = sftp.listdir(server_path)
            total = len(remote_files)
            scale = total * 10
            for i in range(0, scale, 10):
                file = remote_files[int(i / 10)]
                print("\r", end="")
                print("传输进度: {}: ".format('{:.1%}'.format((i + 10) / scale)), "▋" * (i // 2), end="")
                local_file = local_path + file
                remote_file = server_path + file
                if not os.path.exists(local_file):
                    sftp.get(remote_file, local_file)
                sys.stdout.flush()
            print('\r')
            print("文件传输完成，正在启动kt-connect！\r")
            t.close()
            return True
        except Exception as e:
            print('传输kubernetes pki文件失败，错误原因: {0}'.format(e.args[0]))
            shutil.rmtree(local_path)
            return False


def generate_config(ip, config_path):
    file = open(config_path, 'w', encoding='utf-8')
    yaml.dump(json.loads(json.dumps(config_json).replace('{local_path}', ip).replace('{ip}', ip)), file)
    file.close()


def exec_command():
    if os.path.exists(os.path.expanduser('~') + '/.ktctl/pid'): os.remove(os.path.expanduser('~') + '/.ktctl/pid')
    command = 'ktctl -d -i abcsys.cn:5000/public/kt-connect-shadow:stable  --namespace=kube-system connect ' \
              '--method=socks5 --dump2hosts'

    os.system(command)


def store_servers(ip, username, password, image, servers_file):
    r = {
        "ip": ip,
        "username": username,
        "password": password,
        "image": image
    }
    if not os.path.exists(servers_file) or 0 == os.path.getsize(servers_file):
        with open(servers_file, 'w', encoding='utf-8') as f:
            servers_list = [r]
            f.write(json.dumps({"servers": servers_list}))
            f.close()
    else:
        with open(servers_file, 'r+', encoding='utf-8') as f:
            file = dict(json.loads(f.read())).get('servers')
            f.seek(0)
            f.truncate()
            file.append(r)
            # 根据ip去重
            file = reduce(
                lambda y, x: y if (x['ip'] in [i['ip'] for i in y]) else (lambda z, u: (z.append(u), z))(y, x)[1],
                file, [])
            f.write(json.dumps({'servers': file}))
            f.close()


kt()
