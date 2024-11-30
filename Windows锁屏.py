import tkinter as tk
from tkinter import messagebox
import datetime
import threading
import time 
import ctypes
from ctypes import wintypes
import sys
import winreg
import json
import os
import win32event
import win32api
import winerror


user32 = ctypes.WinDLL('user32', use_last_error=True)
HC_ACTION = 0
WH_KEYBOARD_LL = 13
WM_KEYDOWN = 0x0100
WM_KEYUP = 0x0101
WM_SYSKEYDOWN = 0x0104
WM_SYSKEYUP = 0x0105
WINDOWS_KEYS = (91, 92)  # Windows 键的键码

class KBDLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ('vkCode', wintypes.DWORD),
        ('scanCode', wintypes.DWORD),
        ('flags', wintypes.DWORD),
        ('time', wintypes.DWORD),
        ('dwExtraInfo', ctypes.POINTER(ctypes.c_ulong))
    ]

def low_level_keyboard_handler(nCode, wParam, lParam):
    if nCode == HC_ACTION:
        kb = ctypes.cast(lParam, ctypes.POINTER(KBDLLHOOKSTRUCT)).contents
        if kb.vkCode in WINDOWS_KEYS:
            return 1
    return user32.CallNextHookEx(None, nCode, wParam, lParam)

HOOKPROC = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM)
keyboard_callback = HOOKPROC(low_level_keyboard_handler)
hook_id = None

def set_windows_key_hook():
    global hook_id
    hook_id = user32.SetWindowsHookExW(
        WH_KEYBOARD_LL,
        keyboard_callback,
        None,
        0
    )
    if not hook_id:
        raise ctypes.WinError(ctypes.get_last_error())

def remove_windows_key_hook():
    global hook_id
    if hook_id:
        user32.UnhookWindowsHookEx(hook_id)
        hook_id = None

def add_to_startup():
    """添加程序到开机自启动"""
    try:
        # 获取程序的完整路径
        if getattr(sys, 'frozen', False):
            # 如果是打包后的 exe
            app_path = sys.executable
        else:
            # 如果是 python 脚本
            app_path = os.path.abspath(sys.argv[0])
            # 使用 pythonw.exe 来运行（无控制台窗口）
            python_exe = os.path.join(os.path.dirname(sys.executable), 'pythonw.exe')
            app_path = f'"{python_exe}" "{app_path}"'
        
        key_name = "WindowsScreenLock"
        
        # 添加到 HKEY_CURRENT_USER
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0,
            winreg.KEY_SET_VALUE
        )
        winreg.SetValueEx(key, key_name, 0, winreg.REG_SZ, app_path)
        winreg.CloseKey(key)
        
        # 同时添加到 HKEY_LOCAL_MACHINE 以确保更高权限
        try:
            key = winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0,
                winreg.KEY_SET_VALUE
            )
            winreg.SetValueEx(key, key_name, 0, winreg.REG_SZ, app_path)
            winreg.CloseKey(key)
        except:
            pass  # 如果没有管理员权限，添加到 HKEY_LOCAL_MACHINE 可能会失败
            
    except Exception as e:
        print(f"Error adding to startup: {e}")

def remove_from_startup():
    """从开机自启动中移除程序"""
    try:
        key_name = "WindowsScreenLock"
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0,
            winreg.KEY_ALL_ACCESS
        )
        winreg.DeleteValue(key, key_name)
        winreg.CloseKey(key)
    except Exception as e:
        print(f"Error removing from startup: {e}")

def save_lock_state():
    """保存锁屏状态"""
    state = {
        "target_time": target_time.strftime('%Y-%m-%d %H:%M:%S') if target_time else None,
        "is_locked": bool(target_time and datetime.datetime.now() < target_time)
    }
    try:
        with open(os.path.expanduser('~/.screen_lock_state.json'), 'w') as f:
            json.dump(state, f)
    except Exception as e:
        print(f"Error saving state: {e}")

def load_lock_state():
    """读取锁屏状态"""
    try:
        state_file = os.path.expanduser('~/.screen_lock_state.json')
        if os.path.exists(state_file):
            with open(state_file, 'r') as f:
                state = json.load(f)
                if state["target_time"]:
                    global target_time
                    loaded_time = datetime.datetime.strptime(state["target_time"], '%Y-%m-%d %H:%M:%S')
                    current_time = datetime.datetime.now()
                    
                    # 只在目标时间大于当前时间时才加载
                    if loaded_time > current_time:
                        target_time = loaded_time
                        time_str = target_time.strftime('%H:%M:%S')
                        time_entry.delete(0, tk.END)
                        time_entry.insert(0, time_str)
                        set_target_time()
    except Exception as e:
        print(f"Error loading state: {e}")

def set_target_time():
    global target_time, start_button, time_entry
    time_str = time_entry.get()
    try:
        current_time = datetime.datetime.now()
        input_time = datetime.datetime.strptime(time_str, '%H:%M:%S').time()
        target_time = datetime.datetime.combine(current_time.date(), input_time)
        
        # 验证输入时间是否大于当前时间
        if target_time <= current_time:
            # 如果小于或等于当前时间，直接提示错误
            messagebox.showerror("错误", "目标时间必须大于当前时间")
            return
            
        # 更新输入框显示实际的目标时间
        time_entry.delete(0, tk.END)
        time_entry.insert(0, target_time.strftime('%H:%M:%S'))
            
        root.attributes("-fullscreen", True)
        root.attributes("-topmost", True)
        root.protocol("WM_DELETE_WINDOW", on_closing)
        
        root.bind('<Alt-F4>', lambda e: 'break')
        set_windows_key_hook()
        
        # 添加到开机自启动
        add_to_startup()
        
        # 保存状态
        save_lock_state()
        
        start_button.config(state="disabled")
        time_entry.config(state="disabled")
        
        target_display = target_time.strftime('%H:%M:%S')
        target_time_display.config(text=f"目标时间: {target_display}")
        
        update_current_time()
        threading.Thread(target=check_time, daemon=True).start()
    except ValueError:
        messagebox.showerror("错误", "请输入正确的时间格式（HH:MM:SS）")

def check_time():
    global target_time
    while True:
        current_time = datetime.datetime.now()
        if current_time >= target_time:
            messagebox.showinfo("完成", "恭喜你做到了！")
            root.attributes("-fullscreen", False)
            root.protocol("WM_DELETE_WINDOW", on_closing)
            root.attributes("-topmost", False)
            start_button.config(state="normal")
            time_entry.config(state="normal")
            
            # 移除开机自启动
            remove_from_startup()
            
            # 清除保存的状态
            if os.path.exists(os.path.expanduser('~/.screen_lock_state.json')):
                os.remove(os.path.expanduser('~/.screen_lock_state.json'))
            
            root.unbind('<Alt-F4>')
            remove_windows_key_hook()
            break
        time.sleep(1)

def update_current_time():
    current = datetime.datetime.now().strftime('%H:%M:%S')
    current_time_display.config(text=f"当前时间: {current}")
    root.after(1000, update_current_time)

def on_closing():
    if not target_time or datetime.datetime.now() >= target_time:
        remove_windows_key_hook()
        remove_from_startup()
        if os.path.exists(os.path.expanduser('~/.screen_lock_state.json')):
            os.remove(os.path.expanduser('~/.screen_lock_state.json'))
        root.destroy()
    else:
        messagebox.showwarning("警告", "你不能关闭这个窗口，直到时间到了。")
        return False

def cleanup():
    """清理程序"""
    try:
        remove_windows_key_hook()
        if datetime.datetime.now() >= target_time:
            remove_from_startup()
            if os.path.exists(os.path.expanduser('~/.screen_lock_state.json')):
                os.remove(os.path.expanduser('~/.screen_lock_state.json'))
    except:
        pass

root = tk.Tk()
root.title("定时锁屏")
root.geometry("400x300")


frame = tk.Frame(root, padx=20, pady=20)
frame.pack(expand=True)

tk.Label(frame, text="请输入目标时间 (HH:MM:SS):", font=('Arial', 12)).pack(pady=10)

time_entry = tk.Entry(frame, font=('Arial', 12))
time_entry.pack(pady=10)
time_entry.insert(0, "00:00:00")

start_button = tk.Button(frame, text="开始锁屏", command=set_target_time, font=('Arial', 12))
start_button.pack(pady=10)

target_time_display = tk.Label(frame, text="目标时间: 未设置", font=('Arial', 12))
target_time_display.pack(pady=10)

current_time_display = tk.Label(frame, text="当前时间: --:--:--", font=('Arial', 12))
current_time_display.pack(pady=10)

# 初始化目标时间变量
target_time = None

# 启动时间显示
update_current_time()

# 确保程序退出时移除钩子
root.protocol("WM_DELETE_WINDOW", on_closing)

if __name__ == "__main__":
    try:
        # 检查是否以管理员权限运行
        if not ctypes.windll.shell32.IsUserAnAdmin():
            # 请求管理员权限
            if sys.argv[-1] != 'asadmin':
                script = os.path.abspath(sys.argv[0])
                params = ' '.join([script] + sys.argv[1:] + ['asadmin'])
                shell32 = ctypes.windll.shell32
                ret = shell32.ShellExecuteW(None, "runas", sys.executable, params, None, 1)
                if ret > 32:
                    sys.exit(0)
                else:
                    sys.exit(1)
        
        # 确保只运行一个实例
        mutex = win32event.CreateMutex(None, 1, 'WindowsScreenLock_Mutex')
        if win32api.GetLastError() == winerror.ERROR_ALREADY_EXISTS:
            mutex = None
            sys.exit(0)
        
        # 加载之前的锁屏状态
        load_lock_state()
        
        # 运行主程序
        root.mainloop()
    finally:
        cleanup()