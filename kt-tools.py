import time
from functools import reduce

import IPy
import paramiko
import os
import json
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
    base_dir = os.path.expanduser('~') + '/.kube/'
    servers_file = base_dir + 'servers.json'
    config_path = base_dir + 'config'
    select, server = check_file(servers_file)
    if select and bool(server):
        server = dict(server)
        ip = server.get('ip')
        username = server.get('username')
        password = server.get('password')
    else:
        ip = None
        while ip is None:
            ip = input('请输入IP地址: ')
        time.sleep(0.5)
        username = input('请输入用户名称: ')
        time.sleep(0.5)
        password = input('请输入密码: ')
        username = 'root' if username is None or username == '' else username
    if not ssh_connect(ip, username, password):
        input('按任意键退出！')
        exit(0)
    else:
        store_servers(ip, username, password, servers_file)
        sftp_transfer(ip, 22, username, password, base_dir, '/etc/kubernetes/pki/')
        generate_config(ip, config_path)
        exec_command(base_dir)


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
                console_txt = console_txt + ' {0}. 地址: {1}, 用户名: {2}, 密码: {3}, 镜像: {4}, 更新时间: {5} \r\n'.format(
                    index + 1,
                    server.get('ip'),
                    server.get('username'),
                    server.get('password'),
                    server.get('image'),
                    server.get('date'))
                result[index + 1] = server
            console_txt = console_txt + '请输入序号选择（如果新增直接回车）: \r\n'
            select = input(console_txt)
            if select == '' or result.get(int(select)) is None:
                return True, {}
            else:
                return True, result.get(int(select))
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
        print("服务器: {0}登录失败，错误原因: {1}".format(ip, e.args))
        return False


def sftp_transfer(ip, port, username, password, local_path, server_path):
    local_path = local_path + ip + '/'
    if os.path.exists(local_path):
        print('kubernetes pki文件夹已存在，跳过sftp传输！')
        return True
    else:
        try:
            print('kubernetes pki文件夹不存在，正在传输kubernetes pki文件，请稍等！')
            os.makedirs(local_path)
            t = paramiko.Transport(ip, port)
            t.connect(username=username, password=password)
            sftp = paramiko.SFTPClient.from_transport(t)
            remote_files = sftp.listdir(server_path)
            for file in remote_files:
                print('正在同步文件: {0}'.format(file))
                local_file = local_path + file
                remote_file = server_path + file
                if not os.path.exists(local_file):
                    sftp.get(remote_file, local_file)
            t.close()
            return True
        except Exception as e:
            print('传输kubernetes pki文件失败，错误原因: {0}'.format(e.args))
            return False


def generate_config(ip, config_path):
    file = open(config_path, 'w', encoding='utf-8')
    yaml.dump(json.loads(json.dumps(config_json).replace('{local_path}', ip).replace('{ip}', ip)), file)
    file.close()


def exec_command(base_dir):
    if os.path.exists(os.path.expanduser('~') + '/.ktctl/pid'): os.remove(os.path.expanduser('~') + '/.ktctl/pid')
    command = 'ktctl -d -i abcsys.cn:5000/public/kt-connect-shadow:stable  --namespace=kube-system connect ' \
              '--method=socks5 --dump2hosts'

    os.system(command)


def store_servers(ip, username, password, servers_file):
    r = {
        "ip": ip,
        "username": username,
        "password": password,
        "image": "abcsys.cn:5000/public/kt-connect-shadow:stable",
        "date": generate_time()
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
