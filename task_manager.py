import os
import sys
import time
import psutil

# 核心修复 1：动态解决中文路径导致 PyQt5 插件找不到的问题
try:
    import PyQt5
    qt_plugin_path = os.path.join(os.path.dirname(PyQt5.__file__), 'Qt5', 'plugins')
    os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = qt_plugin_path
except ImportError:
    pass

from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QProgressBar, QGroupBox)
from PyQt5.QtCore import QTimer


class TaskManagerApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("系统资源监控 (类任务管理器)")
        self.setGeometry(300, 300, 600, 500) # 稍微加高一点以容纳更多信息
        
        # 设置全局深色主题
        self.setStyleSheet("""
            QMainWindow { background-color: #202020; }
            QLabel { color: #ffffff; font-family: 'Microsoft YaHei'; font-size: 14px; }
            QGroupBox { color: #ffffff; font-family: 'Microsoft YaHei'; border: 1px solid #444; margin-top: 10px; padding-top: 15px; }
            QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top left; padding: 0 5px; }
            QProgressBar { border: 1px solid #444; border-radius: 5px; text-align: center; color: white; background-color: #333; height: 20px; }
            QProgressBar::chunk { background-color: #0078D7; border-radius: 5px; } 
        """)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # 1. CPU
        self.cpu_group = QGroupBox("CPU")
        cpu_layout = QHBoxLayout()
        self.cpu_label = QLabel("0%")
        self.cpu_label.setFixedWidth(50)
        self.cpu_bar = QProgressBar()
        self.cpu_bar.setTextVisible(False)
        cpu_layout.addWidget(self.cpu_label)
        cpu_layout.addWidget(self.cpu_bar)
        self.cpu_group.setLayout(cpu_layout)
        main_layout.addWidget(self.cpu_group)

        # 2. 内存
        self.mem_group = QGroupBox("内存")
        mem_layout = QHBoxLayout()
        self.mem_label = QLabel("0%")
        self.mem_label.setFixedWidth(50)
        self.mem_bar = QProgressBar()
        self.mem_bar.setTextVisible(False)
        self.mem_bar.setStyleSheet("QProgressBar::chunk { background-color: #107C10; border-radius: 5px; }")
        mem_layout.addWidget(self.mem_label)
        mem_layout.addWidget(self.mem_bar)
        self.mem_group.setLayout(mem_layout)
        main_layout.addWidget(self.mem_group)

        # 3. 磁盘使用率 (C盘)
        self.disk_group = QGroupBox("磁盘使用率 (C盘)")
        disk_layout = QHBoxLayout()
        self.disk_label = QLabel("0%")
        self.disk_label.setFixedWidth(50)
        self.disk_bar = QProgressBar()
        self.disk_bar.setTextVisible(False)
        disk_layout.addWidget(self.disk_label)
        disk_layout.addWidget(self.disk_bar)
        self.disk_group.setLayout(disk_layout)
        main_layout.addWidget(self.disk_group)

        # 4. 网络速率
        self.net_group = QGroupBox("网络收发速率")
        net_layout = QVBoxLayout()
        self.net_upload = QLabel("上传: 0.00 KB/s")
        self.net_download = QLabel("下载: 0.00 KB/s")
        net_layout.addWidget(self.net_upload)
        net_layout.addWidget(self.net_download)
        self.net_group.setLayout(net_layout)
        main_layout.addWidget(self.net_group)

        # 5. 磁盘IO读写速率 (老师截图里要求加的)
        self.disk_io_group = QGroupBox("磁盘IO读写速率")
        disk_io_layout = QVBoxLayout()
        self.disk_read = QLabel("读取: 0.00 KB/s")
        self.disk_write = QLabel("写入: 0.00 KB/s")
        disk_io_layout.addWidget(self.disk_read)
        disk_io_layout.addWidget(self.disk_write)
        self.disk_io_group.setLayout(disk_io_layout)
        main_layout.addWidget(self.disk_io_group)

        # 初始化历史数据
        self.last_net_io = psutil.net_io_counters()
        self.last_disk_io = psutil.disk_io_counters()
        self.last_time = time.time()

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_stats)
        self.timer.start(1000)

    def update_stats(self):
        # 更新 CPU, 内存, 磁盘使用率
        self.cpu_bar.setValue(int(psutil.cpu_percent()))
        self.cpu_label.setText(f"{psutil.cpu_percent()}%")

        mem = psutil.virtual_memory()
        self.mem_bar.setValue(int(mem.percent)) 
        self.mem_label.setText(f"{mem.percent}%")

        disk = psutil.disk_usage('C:\\')
        self.disk_bar.setValue(int(disk.percent))
        self.disk_label.setText(f"{disk.percent}%")

        # 计算网络与磁盘IO速率
        current_time = time.time()
        current_net_io = psutil.net_io_counters()
        current_disk_io = psutil.disk_io_counters()
        time_diff = current_time - self.last_time

        if time_diff > 0:
            # 网络速率
            up_speed = (current_net_io.bytes_sent - self.last_net_io.bytes_sent) / time_diff / 1024
            down_speed = (current_net_io.bytes_recv - self.last_net_io.bytes_recv) / time_diff / 1024
            self.net_upload.setText(f"上传: {up_speed:.2f} KB/s")
            self.net_download.setText(f"下载: {down_speed:.2f} KB/s")

            # 磁盘IO速率
            read_speed = (current_disk_io.read_bytes - self.last_disk_io.read_bytes) / time_diff / 1024
            write_speed = (current_disk_io.write_bytes - self.last_disk_io.write_bytes) / time_diff / 1024
            self.disk_read.setText(f"读取: {read_speed:.2f} KB/s")
            self.disk_write.setText(f"写入: {write_speed:.2f} KB/s")

        self.last_net_io = current_net_io
        self.last_disk_io = current_disk_io
        self.last_time = current_time


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = TaskManagerApp()
    window.show()
    sys.exit(app.exec_())