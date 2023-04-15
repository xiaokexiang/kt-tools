### 简介
基于kt-connect，用于提高在多个环境之间进行调试的小工具，需要提前在本地配置好ktctl和kubectl

### 终端打包命令

```python
pyinstaller -F -c -i favicon.ico kt-tools.py
```

### 图形化界面打包命令
```python
pyinstaller -wF -i favicon.ico qt.py -n kt-tools
```