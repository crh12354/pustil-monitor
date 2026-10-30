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
                             QTableWidgetItem, QHeaderView, QGroupBox, QTabWidget)
from PyQt5.QtCore import QTimer, Qt

class TaskManagerApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("系统资源监控与进程管理")
        self.resize(900, 650)
        
        # 设置全局样式
        self.setStyleSheet("""
            QMainWindow { background-color: #f0f0f0; }
            QLabel { font-family: 'Microsoft YaHei'; font-size: 14px; font-weight: bold; }
            QLineEdit { font-family: 'Microsoft YaHei'; font-size: 14px; padding: 5px; border: 1px solid #ccc; border-radius: 3px; }
            QTableWidget { font-family: 'Microsoft YaHei'; font-size: 13px; background-color: white; alternate-background-color: #f9f9f9; }
            QHeaderView::section { background-color: #e0e0e0; font-weight: bold; padding: 4px; border: 1px solid #ccc; }
            QGroupBox { font-family: 'Microsoft YaHei'; font-weight: bold; border: 1px solid #ccc; margin-top: 10px; padding-top: 15px; }
            QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top left; padding: 0 5px; }
            QTabWidget::pane { border: 1px solid #ccc; background: white; }
            QTabBar::tab { background: #e0e0e0; padding: 8px 20px; font-family: 'Microsoft YaHei'; font-size: 14px; }
            QTabBar::tab:selected { background: white; font-weight: bold; border-bottom: 2px solid #0078D7; }
        """)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # --- 顶部：实时概览面板 ---
        top_group = QGroupBox("系统实时概览")
        top_layout = QHBoxLayout()
        self.lbl_cpu = QLabel("CPU: 0%")
        self.lbl_mem = QLabel("内存: 0%")
        self.lbl_net = QLabel("网络: 0 KB/s")
        self.lbl_disk_io = QLabel("磁盘IO: 0 KB/s")
        
        top_layout.addWidget(self.lbl_cpu)
        top_layout.addWidget(self.lbl_mem)
        top_layout.addWidget(self.lbl_net)
        top_layout.addWidget(self.lbl_disk_io)
        top_group.setLayout(top_layout)
        main_layout.addWidget(top_group)

        # --- 中间：搜索框 ---
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("搜索过滤 (输入名称/PID):"))
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("输入关键字进行筛选...")
        self.search_box.textChanged.connect(self.filter_tables)
        search_layout.addWidget(self.search_box)
        main_layout.addLayout(search_layout)

        # --- 底部：选项卡 (Tab) ---
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)

        # Tab 1: 系统资源表
        self.tab_res = QWidget()
        res_layout = QVBoxLayout(self.tab_res)
        self.table_res = QTableWidget()
        self.table_res.setColumnCount(5)
        self.table_res.setHorizontalHeaderLabels(["设备名称", "类型", "使用率/占用", "读写/收发速率", "状态/详情"])
        self.setup_table(self.table_res)
        res_layout.addWidget(self.table_res)
        self.tabs.addTab(self.tab_res, "系统资源")

        # Tab 2: 进程管理表
        self.tab_proc = QWidget()
        proc_layout = QVBoxLayout(self.tab_proc)
        self.table_proc = QTableWidget()
        self.table_proc.setColumnCount(5)
        self.table_proc.setHorizontalHeaderLabels(["进程名", "PID", "CPU 占用", "内存占用", "状态"])
        self.setup_table(self.table_proc)
        proc_layout.addWidget(self.table_proc)
        self.tabs.addTab(self.tab_proc, "进程管理")

        # 初始化数据
        self.last_time = time.time()
        self.last_net_io = psutil.net_io_counters(pernic=True)
        self.last_disk_io = psutil.disk_io_counters(perdisk=True)
        
        # 初始化进程 CPU 统计
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                proc.cpu_percent(None)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

        # 定时器
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_data)
        self.timer.start(1000) # 每秒刷新

    def setup_table(self, table):
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        table.setAlternatingRowColors(True)
        table.setEditTriggers(QTableWidget.NoEditTriggers) # 禁止编辑
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.setSortingEnabled(True) # 允许点击表头排序

    def update_data(self):
        current_time = time.time()
        time_diff = current_time - self.last_time
        
        # 1. 更新顶部概览
        cpu_percent = psutil.cpu_percent()
        mem = psutil.virtual_memory()
        self.lbl_cpu.setText(f"CPU: {cpu_percent}%")
        self.lbl_mem.setText(f"内存: {mem.percent}%")

        # --- 更新 Tab 1: 系统资源表 ---
        self.update_system_resources(mem, current_time, time_diff)

        # --- 更新 Tab 2: 进程管理表 ---
        self.update_processes()

        # 重新应用一次过滤
        self.filter_tables()

        # 更新记录
        self.last_time = current_time
        self.last_net_io = psutil.net_io_counters(pernic=True)
        self.last_disk_io = psutil.disk_io_counters(perdisk=True)

    def update_system_resources(self, mem, current_time, time_diff):
        cpu_cores = psutil.cpu_percent(percpu=True)
        
        # 计算总网络速率
        net_data = []
        total_up, total_down = 0, 0
        current_net_io = psutil.net_io_counters(pernic=True)
        if time_diff > 0:
            for nic, io in current_net_io.items():
                up = (io.bytes_sent - self.last_net_io.get(nic, io).bytes_sent) / time_diff / 1024
                down = (io.bytes_recv - self.last_net_io.get(nic, io).bytes_recv) / time_diff / 1024
                total_up += up
                total_down += down
                net_data.append((nic, up, down))
        self.lbl_net.setText(f"网络: ↑{total_up:.0f} | ↓{total_down:.0f} KB/s")

        # 计算总磁盘IO速率
        disk_io_data = []
        total_read, total_write = 0, 0
        current_disk_io = psutil.disk_io_counters(perdisk=True)
        if time_diff > 0:
            for disk, io in current_disk_io.items():
                read = (io.read_bytes - self.last_disk_io.get(disk, io).read_bytes) / time_diff / 1024
                write = (io.write_bytes - self.last_disk_io.get(disk, io).write_bytes) / time_diff / 1024
                total_read += read
                total_write += write
                disk_io_data.append((disk, read, write))
        self.lbl_disk_io.setText(f"磁盘IO: 读{total_read:.0f} | 写{total_write:.0f} KB/s")

        # 构建表格数据
        res_data = []
        for i, p in enumerate(cpu_cores):
            res_data.append([f"CPU 核心 {i}", "处理器", f"{p}%", "-", "正常"])
        res_data.append(["物理内存", "内存", f"{mem.percent}%", "-", f"已用 {mem.used / (1024**3):.2f}G / 共 {mem.total / (1024**3):.2f}G"])
        
        for nic, up, down in net_data:
            status = "已连接" if nic in psutil.net_if_stats() and psutil.net_if_stats()[nic].isup else "未连接"
            res_data.append([nic, "网络适配器", "-", f"↑{up:.1f} | ↓{down:.1f} KB/s", status])
            
        for part in psutil.disk_partitions():
            try:
                usage = psutil.disk_usage(part.mountpoint)
                res_data.append([f"{part.device} ({part.mountpoint})", "磁盘分区", f"{usage.percent}%", "-", f"总容量 {usage.total / (1024**3):.2f}G"])
            except PermissionError:
                pass
                
        for disk, read, write in disk_io_data:
            res_data.append([f"物理磁盘 {disk}", "磁盘设备 IO", "-", f"读{read:.1f} | 写{write:.1f} KB/s", "正常"])

        # 填充表格 (暂时关闭排序以避免闪烁)
        self.table_res.setSortingEnabled(False)
        self.table_res.setRowCount(len(res_data))
        for row, data in enumerate(res_data):
            for col, value in enumerate(data):
                item = QTableWidgetItem(value)
                item.setTextAlignment(Qt.AlignCenter)
                self.table_res.setItem(row, col, item)
        self.table_res.setSortingEnabled(True)

    def update_processes(self):
        proc_data = []
        # 获取所有进程信息
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_info', 'status']):
            try:
                info = proc.info
                # 过滤掉没有名字的系统空进程
                if not info['name']:
                    continue
                    
                # 格式化 CPU 和内存
                cpu_usage = f"{info['cpu_percent']}%"
                mem_mb = info['memory_info'].rss / (1024 * 1024)
                mem_usage = f"{mem_mb:.1f} MB"
                
                # 翻译状态
                status_map = {
                    psutil.STATUS_RUNNING: "运行中",
                    psutil.STATUS_SLEEPING: "睡眠",
                    psutil.STATUS_DISK_SLEEP: "磁盘休眠",
                    psutil.STATUS_STOPPED: "已停止",
                    psutil.STATUS_ZOMBIE: "僵尸",
                    psutil.STATUS_DEAD: "死亡",
                    psutil.STATUS_WAKING: "唤醒中",
                    psutil.STATUS_IDLE: "空闲"
                }
                status_str = status_map.get(info['status'], info['status'])
                
                proc_data.append([info['name'], str(info['pid']), cpu_usage, mem_usage, status_str])
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass

        # 填充进程表格 (暂时关闭排序)
        self.table_proc.setSortingEnabled(False)
        self.table_proc.setRowCount(len(proc_data))
        for row, data in enumerate(proc_data):
            for col, value in enumerate(data):
                item = QTableWidgetItem(value)
                # 让 PID 和数值列可以按数字大小正确排序
                if col == 1: 
                    item.setData(Qt.UserRole, int(value)) 
                elif col == 2:
                    item.setData(Qt.UserRole, float(value.replace('%','')))
                elif col == 3:
                    item.setData(Qt.UserRole, float(value.replace(' MB','')))
                
                item.setTextAlignment(Qt.AlignCenter)
                self.table_proc.setItem(row, col, item)
        self.table_proc.setSortingEnabled(True)

    def filter_tables(self):
        """根据搜索框内容过滤当前显示的表格"""
        text = self.search_box.text().strip().lower()
        current_tab = self.tabs.currentIndex()
        
        # 过滤系统资源表
        if current_tab == 0:
            for row in range(self.table_res.rowCount()):
                item_name = self.table_res.item(row, 0).text().lower()
                item_type = self.table_res.item(row, 1).text().lower()
                if text in item_name or text in item_type:
                    self.table_res.setRowHidden(row, False)
                else:
                    self.table_res.setRowHidden(row, True)
        # 过滤进程管理表
        else:
            for row in range(self.table_proc.rowCount()):
                # 匹配进程名或者PID
                item_name = self.table_proc.item(row, 0).text().lower()
                item_pid = self.table_proc.item(row, 1).text().lower()
                if text in item_name or text in item_pid:
                    self.table_proc.setRowHidden(row, False)
                else:
                    self.table_proc.setRowHidden(row, True)

    # 切换 Tab 时重新过滤一次
    def on_tab_changed(self, index):
        self.filter_tables()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = TaskManagerApp()
    # 绑定 tab 切换事件
    window.tabs.currentChanged.connect(window.on_tab_changed)
    window.show()
    sys.exit(app.exec_())