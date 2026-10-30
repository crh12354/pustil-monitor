import os
import sys
import time
import psutil

# 核心修复：解决中文路径导致 PyQt5 插件找不到的问题
try:
    import PyQt5
    qt_plugin_path = os.path.join(os.path.dirname(PyQt5.__file__), 'Qt5', 'plugins')
    os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = qt_plugin_path
except ImportError:
    pass

from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QLineEdit, QTableWidget, 
                             QTableWidgetItem, QHeaderView, QGroupBox)
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QColor, QFont

class TaskManagerApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("系统资源监控 - 类似任务管理器")
        self.resize(800, 600)
        
        # 设置全局样式（白底黑字，类似经典任务管理器）
        self.setStyleSheet("""
            QMainWindow { background-color: #f0f0f0; }
            QLabel { font-family: 'Microsoft YaHei'; font-size: 14px; font-weight: bold; }
            QLineEdit { font-family: 'Microsoft YaHei'; font-size: 14px; padding: 5px; border: 1px solid #ccc; border-radius: 3px; }
            QTableWidget { font-family: 'Microsoft YaHei'; font-size: 13px; background-color: white; alternate-background-color: #f9f9f9; }
            QHeaderView::section { background-color: #e0e0e0; font-weight: bold; padding: 4px; border: 1px solid #ccc; }
            QGroupBox { font-family: 'Microsoft YaHei'; font-weight: bold; border: 1px solid #ccc; margin-top: 10px; padding-top: 15px; }
            QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top left; padding: 0 5px; }
        """)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # --- 顶部：实时概览面板 ---
        top_group = QGroupBox("系统实时概览")
        top_layout = QHBoxLayout()
        self.lbl_cpu = QLabel("CPU: 0%")
        self.lbl_mem = QLabel("内存: 0%")
        self.lbl_net = QLabel("网络总速率: 0 KB/s")
        self.lbl_disk_io = QLabel("磁盘IO总速率: 0 KB/s")
        
        top_layout.addWidget(self.lbl_cpu)
        top_layout.addWidget(self.lbl_mem)
        top_layout.addWidget(self.lbl_net)
        top_layout.addWidget(self.lbl_disk_io)
        top_group.setLayout(top_layout)
        main_layout.addWidget(top_group)

        # --- 中间：搜索框 ---
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("搜索过滤 (输入名称，如 C盘 / WLAN / CPU):"))
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("输入关键字进行筛选...")
        # 监听输入框内容变化，触发过滤函数
        self.search_box.textChanged.connect(self.filter_table)
        search_layout.addWidget(self.search_box)
        main_layout.addLayout(search_layout)

        # --- 底部：详细数据表格 ---
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["设备名称", "类型", "使用率/占用", "读写/收发速率", "状态/详情"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch) # 列宽自适应
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers) # 禁止编辑表格
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        main_layout.addWidget(self.table)

        # 记录上一次的数据，用于算速率
        self.last_time = time.time()
        self.last_net_io = psutil.net_io_counters(pernic=True)
        self.last_disk_io = psutil.disk_io_counters(perdisk=True)
        self.last_cpu_times = psutil.cpu_times()

        # 定时器
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_data)
        self.timer.start(1000) # 每秒刷新

    def update_data(self):
        current_time = time.time()
        time_diff = current_time - self.last_time
        
        # 1. 获取 CPU 数据
        cpu_percent = psutil.cpu_percent()
        self.lbl_cpu.setText(f"CPU: {cpu_percent}%")
        cpu_cores = psutil.cpu_percent(percpu=True)

        # 2. 获取内存数据
        mem = psutil.virtual_memory()
        self.lbl_mem.setText(f"内存: {mem.percent}%")

        # 3. 获取网络数据 (计算每个网卡的速率)
        current_net_io = psutil.net_io_counters(pernic=True)
        net_data = []
        total_up, total_down = 0, 0
        if time_diff > 0:
            for nic, io in current_net_io.items():
                up = (io.bytes_sent - self.last_net_io.get(nic, io).bytes_sent) / time_diff / 1024
                down = (io.bytes_recv - self.last_net_io.get(nic, io).bytes_recv) / time_diff / 1024
                total_up += up
                total_down += down
                net_data.append((nic, up, down))
        self.lbl_net.setText(f"网络总速率: ↑{total_up:.1f} KB/s | ↓{total_down:.1f} KB/s")

        # 4. 获取磁盘使用率与IO数据
        current_disk_io = psutil.disk_io_counters(perdisk=True)
        disk_usage = []
        disk_io_data = []
        total_read, total_write = 0, 0
        if time_diff > 0:
            for disk, io in current_disk_io.items():
                read = (io.read_bytes - self.last_disk_io.get(disk, io).read_bytes) / time_diff / 1024
                write = (io.write_bytes - self.last_disk_io.get(disk, io).write_bytes) / time_diff / 1024
                total_read += read
                total_write += write
                disk_io_data.append((disk, read, write))
        self.lbl_disk_io.setText(f"磁盘IO总速率: 读{total_read:.1f} | 写{total_write:.1f} KB/s")

        for part in psutil.disk_partitions():
            try:
                usage = psutil.disk_usage(part.mountpoint)
                disk_usage.append((part.device, part.mountpoint, usage.percent, usage.total))
            except PermissionError:
                pass

        # --- 构建表格数据 ---
        table_data = []

        # 添加 CPU 核心
        for i, p in enumerate(cpu_cores):
            table_data.append([f"CPU 核心 {i}", "处理器", f"{p}%", "-", "正常"])
            
        # 添加内存
        table_data.append(["物理内存", "内存", f"{mem.percent}%", "-", f"已用 {mem.used / (1024**3):.2f} GB / 共 {mem.total / (1024**3):.2f} GB"])

        # 添加网络接口
        for nic, up, down in net_data:
            status = "已连接" if nic in psutil.net_if_stats() and psutil.net_if_stats()[nic].isup else "未连接"
            table_data.append([nic, "网络适配器", "-", f"↑{up:.2f} KB/s | ↓{down:.2f} KB/s", status])

        # 添加磁盘分区
        for device, mountpoint, percent, total in disk_usage:
            table_data.append([f"{device} ({mountpoint})", "磁盘分区", f"{percent}%", "-", f"总容量 {total / (1024**3):.2f} GB"])

        # 添加磁盘IO设备
        for disk, read, write in disk_io_data:
            table_data.append([f"物理磁盘 {disk}", "磁盘设备 IO", "-", f"读{read:.2f} | 写{write:.2f} KB/s", "正常"])

        # 将数据填入表格
        self.table.setRowCount(len(table_data))
        for row, data in enumerate(table_data):
            for col, value in enumerate(data):
                item = QTableWidgetItem(value)
                item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row, col, item)

        # 重新应用一次过滤（防止刷新后搜索框失效）
        self.filter_table()

        # 更新历史记录
        self.last_time = current_time
        self.last_net_io = current_net_io
        self.last_disk_io = current_disk_io

    def filter_table(self):
        """根据搜索框的内容过滤表格行"""
        text = self.search_box.text().strip().lower()
        for row in range(self.table.rowCount()):
            # 获取该行的第一列（设备名称）和第二列（类型）
            item_name = self.table.item(row, 0).text().lower()
            item_type = self.table.item(row, 1).text().lower()
            
            # 如果搜索词在名称或类型中，则显示，否则隐藏
            if text in item_name or text in item_type:
                self.table.setRowHidden(row, False)
            else:
                self.table.setRowHidden(row, True)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = TaskManagerApp()
    window.show()
    sys.exit(app.exec_())