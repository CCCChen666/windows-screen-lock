# Windows Screen Lock

一个基于 Python 的 Windows 定时锁屏工具。

## 功能特点

- 设置目标时间进行锁屏
- 支持系统重启后继续锁定
- 禁用 Windows 键和 Alt+F4
- 全屏显示倒计时
- 自动添加到开机启动项

## 使用方法

1. 安装依赖：
pip install pywin32
2. 运行程序：
python Windows锁屏.py
3. 输入目标时间（格式：HH:MM:SS）
4. 点击"开始锁屏"

## 注意事项

- 需要管理员权限运行
- 建议先用短时间测试
- 重启后程序会自动运行并继续锁定
- 达到目标时间后自动解除锁定

## 环境要求

- Windows 操作系统
- Python 3.6+
- pywin32