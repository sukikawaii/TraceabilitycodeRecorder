import os
import json
from webdav3.client import Client
import tkinter as tk
from tkinter import messagebox, simpledialog
from barcode import Code128
from barcode.writer import ImageWriter
from io import BytesIO
from PIL import ImageTk, Image
import datetime
import logging

# 日志配置
log_directory = os.path.join(os.environ['USERPROFILE'], 'Documents', 'Traceability code records', 'log')
os.makedirs(log_directory, exist_ok=True)
log_filename = os.path.join(log_directory, 'tracker.log')
logging.basicConfig(filename=log_filename, level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

# medicine_data.txt 文件路径
data_directory = os.path.join(os.environ['USERPROFILE'], 'Documents', 'Traceability code records', 'userdata')
os.makedirs(data_directory, exist_ok=True)
data_filename = os.path.join(data_directory, 'medicine_data.txt')


def load_webdav_config():
    with open('webdav_config.json', 'r') as file:
        config = json.load(file)
        print("Loaded WebDAV configuration:", config)
        # logging.info("Loaded WebDAV configuration: %s", config)
        return config


def read_data_from_webdav(filename):
    config = load_webdav_config()
    client = Client(config)
    print("Connecting to WebDAV...")
    logging.info("Connecting to WebDAV...")
    try:
        client.download_sync(remote_path=f'{config["webdav_root"]}{filename}', local_path=filename)
        print(f"Downloaded '{filename}' from WebDAV.")
        logging.info(f"Downloaded '{filename}' from WebDAV.")
        data = read_data(filename)
        client.clean(local_path=filename)
        print(f"Cleared temporary file '{filename}'.")
        logging.info(f"Cleared temporary file '{filename}'.")
        return data
    except Exception as e:
        print(f"Error reading data from WebDAV: {e}")
        logging.error(f"Error reading data from WebDAV: {e}")
        return {}


def write_data_to_webdav(filename, data):
    config = load_webdav_config()
    client = Client(config)
    print("Connecting to WebDAV...")
    logging.info("Connecting to WebDAV...")
    try:
        write_data(filename, data)
        client.upload_sync(remote_path=f'{config["webdav_root"]}{filename}', local_path=filename)
        print(f"Uploaded '{filename}' to WebDAV.")
        logging.info(f"Uploaded '{filename}' to WebDAV.")
        client.clean(local_path=filename)
        print(f"Cleared temporary file '{filename}'.")
        logging.info(f"Cleared temporary file '{filename}'.")
    except Exception as e:
        print(f"Error writing data to WebDAV: {e}")
        logging.error(f"Error writing data to WebDAV: {e}")


def read_data(filename):
    data = {}
    try:
        with open(filename, 'r') as file:
            for line in file:
                parts = line.strip().split(',')
                barcode = parts[0]
                data[barcode] = parts[1:]
        return data
    except FileNotFoundError:
        return {}


def write_data(filename, data):
    with open(filename, 'w') as file:
        for barcode, values in data.items():
            line = f"{barcode},{','.join(values)}\n"
            file.write(line)


def generate_barcode_image(code):
    # 生成不含数字的Code128条形码图像
    code128 = Code128(code, writer=ImageWriter())
    buffer = BytesIO()
    code128.write(buffer, options={"write_text": False, "module_width": 0.3, "module_height": 10})
    buffer.seek(0)
    img = Image.open(buffer)
    img = img.resize((img.width // 2, img.height // 2), Image.LANCZOS)
    return ImageTk.PhotoImage(img), img.size


def check_webdav_connection(filename):
    """检查WebDAV连接并读取数据文件"""
    config = load_webdav_config()
    client = Client(config)
    try:
        # 尝试下载文件
        client.download_sync(remote_path=f'{config["webdav_root"]}{filename}', local_path=filename)
        data = read_data(filename)
        client.clean(local_path=filename)
        print(f"WebDAV connection successful.")
        logging.info(f"WebDAV connection successful.")
        return True, data
    except Exception as e:
        print(f"Error checking WebDAV connection: {e}")
        # logging.error(f"Error checking WebDAV connection: {e}")
        return False, {}


class MedicineTrackerApp:
    def __init__(self, root, filename):
        self.root = root
        self.filename = filename
        self.data = None
        self.last_searched_barcode = None

        # print("Starting MedicineTrackerApp...")
        # logging.info("Starting MedicineTrackerApp...")

        # 检查WebDAV连接
        self.webdav_connected, self.data = check_webdav_connection(self.filename)
        if not self.webdav_connected:
            # 如果WebDAV连接失败，尝试从本地读取数据
            self.data = read_data(self.filename)

        # 设置窗口图标
        root.iconbitmap('app_icon.ico')

        # 设置窗口标题
        version_number = "v0.1.0"  # 设置版本号
        self.root.title(f"追溯码记录器 {version_number}")
        self.center_window(self.root)

        # 在窗口底部添加版本号标签
        self.version_label = tk.Label(root, text=f"版本: {version_number}", font=("Arial", 8))
        self.version_label.pack(side=tk.BOTTOM, pady=5)

        # 输入框
        self.barcode_entry = tk.Entry(root, width=50)
        self.barcode_entry.pack(pady=10)
        self.barcode_entry.focus_set()  # 默认焦点
        self.barcode_entry.bind('<Return>', self.on_search_or_add_traceability)

        # 添加追溯码按钮
        self.add_traceability_button = tk.Button(root, text="添加追溯码", command=self.on_add_traceability)
        self.add_traceability_button.pack(pady=5)

        # 显示药品信息
        self.medication_label = tk.Label(root, text="", wraplength=300)
        self.medication_label.pack(pady=10)

        # 显示追溯码列表
        self.traceability_listbox = tk.Listbox(root, width=50)
        self.traceability_listbox.pack(pady=10)
        self.traceability_listbox.bind('<Double-Button-1>', self.on_copy_and_delete)

        # 设置主窗口的背景颜色
        self.root.configure(bg='white')

        # 添加开发者信息
        self.developer_label = tk.Label(root, text="by 张强", font=("Arial", 8))
        self.developer_label.pack(side=tk.BOTTOM, pady=5)

        # 显示连接状态
        self.connection_status_label = tk.Label(root, text="", font=("Arial", 10))
        self.connection_status_label.pack(pady=5)
        if self.webdav_connected:
            self.connection_status_label.config(text="已成功连接WebDAV服务器", fg="green")
        else:
            self.connection_status_label.config(text="未连接WebDAV服务器", fg="red")

        # 启用或禁用主要功能
        if self.data is not None:
            self.enable_ui()
        else:
            self.disable_ui()

        # print("Finished initializing MedicineTrackerApp.")
        # logging.info("Finished initializing MedicineTrackerApp.")

    def center_window(self, window):
        # 获取屏幕尺寸
        screen_width = window.winfo_screenwidth()
        screen_height = window.winfo_screenheight()

        # 计算窗口位置使其居中
        x = (screen_width - 400) // 2
        y = (screen_height - 420) // 2  # 调整窗口高度
        window.geometry(f"400x420+{x}+{y}")  # 调整窗口高度

    def enable_ui(self):
        self.barcode_entry.config(state=tk.NORMAL)
        self.add_traceability_button.config(state=tk.NORMAL)

    def disable_ui(self):
        self.barcode_entry.config(state=tk.DISABLED)
        self.add_traceability_button.config(state=tk.DISABLED)

    def on_search_or_add_traceability(self, event):
        if not self.barcode_entry.get() and self.last_searched_barcode is not None:
            self.barcode_entry.delete(0, tk.END)  # 清除输入框内容
            self.on_add_traceability()
        else:
            self.on_search(event)

    def on_search(self, event):
        search_term = self.barcode_entry.get().strip()
        if not search_term:
            return

        self.barcode_entry.delete(0, tk.END)  # 清除输入框内容

        # 搜索药品名称
        matches = []
        for barcode, (medication, *traceabilities) in self.data.items():
            if search_term.lower() in medication.lower():
                matches.append((medication, barcode, traceabilities))

        if matches:
            self.show_multiple_matches(matches)
        elif search_term.isdigit():  # 如果没有匹配药品名称，检查是否为条形码
            if search_term in self.data:
                self.display_info(search_term)
                self.last_searched_barcode = search_term
            else:
                if messagebox.askyesno("提示", "未找到条形码信息，是否创建新记录？"):
                    self.create_new_record(search_term)
        else:
            messagebox.showinfo("提示", "未找到相关药品，请检查输入或创建新记录。")

    def show_multiple_matches(self, matches):
        # 创建一个顶级窗口来显示多个匹配项
        match_window = tk.Toplevel(self.root)
        match_window.title("匹配结果")

        # 计算弹窗大小
        item_height = 20  # 每个项目的高度
        padding = 10  # 内边距
        border_width = 2  # 边框宽度
        window_width = 400  # 固定宽度
        window_height = (len(matches) * item_height) + (padding * 2) + border_width * 2

        # 居中显示弹窗
        screen_width = match_window.winfo_screenwidth()
        screen_height = match_window.winfo_screenheight()
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        match_window.geometry(f"{window_width}x{window_height}+{x}+{y}")

        listbox = tk.Listbox(match_window, selectmode=tk.SINGLE, width=50, height=len(matches))
        listbox.pack(padx=padding, pady=padding, fill=tk.BOTH, expand=True)

        for medication, barcode, traceabilities in matches:
            info_text = f"药品名称: {medication}\n  条形码: {barcode}\n  追溯码数量: {len(traceabilities)}"
            listbox.insert(tk.END, info_text)

        # 默认选择第一个项目
        listbox.select_set(0)  # 选择第一个项目
        listbox.event_generate("<<ListboxSelect>>")  # 触发选择事件

        def on_select(event):
            selected_index = listbox.curselection()
            if selected_index:
                index = selected_index[0]
                _, barcode, _ = matches[index]
                self.display_info(barcode)
                self.last_searched_barcode = barcode
                match_window.destroy()

        listbox.bind('<<ListboxSelect>>', lambda event: None)  # 避免默认选择行为
        listbox.bind('<Double-Button-1>', lambda event: on_select(event))  # 双击选择
        listbox.bind('<Return>', lambda event: on_select(event))  # 回车键选择
        listbox.bind('<Up>', lambda event: self.handle_up_down_key(listbox, event))  # 上键
        listbox.bind('<Down>', lambda event: self.handle_up_down_key(listbox, event))  # 下键
        listbox.focus_set()

    def handle_up_down_key(self, listbox, event):
        current_selection = listbox.curselection()
        if current_selection:
            index = current_selection[0]
            if event.keysym == 'Up':
                new_index = max(0, index - 1)
            else:
                new_index = min(len(listbox.get(0, tk.END)) - 1, index + 1)
            listbox.select_clear(current_selection)
            listbox.select_set(new_index)
            listbox.event_generate("<<ListboxSelect>>")
        else:
            listbox.select_set(0)  # 如果没有选择任何项，选择第一个
            listbox.event_generate("<<ListboxSelect>>")

    def display_info(self, barcode):
        medication, traceabilities = self.data[barcode][0], self.data[barcode][1:]
        num_traceabilities = len(traceabilities)
        info_text = f"药品名称: {medication}\n条形码: {barcode}\n追溯码数量: {num_traceabilities}"
        self.medication_label.config(text=info_text)
        self.traceability_listbox.delete(0, tk.END)
        for trace in traceabilities:
            self.traceability_listbox.insert(tk.END, trace)

    def create_new_record(self, barcode):
        medication = simpledialog.askstring("输入", "请输入药品名称:")
        if medication:
            traceability = simpledialog.askstring("输入", "请输入追溯码:")
            if traceability:
                if traceability in self.data.get(barcode, []):
                    messagebox.showerror("错误", "该追溯码已存在，不能添加重复的追溯码。")
                elif self.check_traceability_in_logs(traceability):
                    response = messagebox.askyesno("提示",
                                                   f"该追溯码已于 {self.find_traceability_date(traceability)} 添加过，是否继续添加？")
                    if response:
                        self.data[barcode] = [medication, traceability]
                        if self.webdav_connected:
                            write_data_to_webdav(self.filename, self.data)
                        else:
                            write_data(self.filename, self.data)
                        self.display_info(barcode)
                        self.last_searched_barcode = barcode
                        self.log_event('CREATE', barcode, medication, traceability)
                else:
                    self.data[barcode] = [medication, traceability]
                    if self.webdav_connected:
                        write_data_to_webdav(self.filename, self.data)
                    else:
                        write_data(self.filename, self.data)
                    self.display_info(barcode)
                    self.last_searched_barcode = barcode
                    self.log_event('CREATE', barcode, medication, traceability)

    def check_traceability_in_logs(self, traceability):
        # 检查日志文件是否存在该追溯码
        with open(log_filename, 'r') as log_file:
            for line in log_file:
                if traceability in line:
                    return True
        return False

    def find_traceability_date(self, traceability):
        # 查找追溯码的日期
        with open(log_filename, 'r') as log_file:
            for line in reversed(list(log_file)):
                if traceability in line:
                    return line.split(' - ')[0]
        return "未知"

    def on_add_traceability(self):
        if self.last_searched_barcode is None:
            messagebox.showwarning("警告", "请先查询条形码")
            return
        traceability = simpledialog.askstring("输入", "请输入新的追溯码:")
        if traceability:
            if traceability in self.data.get(self.last_searched_barcode, []):
                messagebox.showerror("错误", "该追溯码已存在，不能添加重复的追溯码。")
            elif self.check_traceability_in_logs(traceability):
                response = messagebox.askyesno("提示", f"该追溯码已于 {self.find_traceability_date(traceability)} 添加过，是否继续添加？")
                if response:
                    self.data[self.last_searched_barcode].append(traceability)
                    if self.webdav_connected:
                        write_data_to_webdav(self.filename, self.data)
                    else:
                        write_data(self.filename, self.data)
                    self.display_info(self.last_searched_barcode)
                    self.log_event('ADD', self.last_searched_barcode, self.data[self.last_searched_barcode][0],
                                   traceability)
                    # 将焦点设置回输入框
                    self.barcode_entry.focus_set()
            else:
                self.data[self.last_searched_barcode].append(traceability)
                if self.webdav_connected:
                    write_data_to_webdav(self.filename, self.data)
                else:
                    write_data(self.filename, self.data)
                self.display_info(self.last_searched_barcode)
                self.log_event('ADD', self.last_searched_barcode, self.data[self.last_searched_barcode][0],
                               traceability)
                # 将焦点设置回输入框
                self.barcode_entry.focus_set()

    def on_copy_and_delete(self, event):
        selected_index = self.traceability_listbox.curselection()
        if selected_index:
            traceability = self.traceability_listbox.get(selected_index)
            self.root.clipboard_clear()
            self.root.clipboard_append(traceability)
            # 显示删除确认对话框
            self.show_delete_confirmation(traceability)

    def show_delete_confirmation(self, traceability):
        # 创建一个顶级窗口来显示条形码图像
        window = tk.Toplevel(self.root)
        window.title("删除确认")

        # 生成条形码图像
        barcode_image, size = generate_barcode_image(traceability)

        # 根据条形码图像大小调整弹窗大小
        window_width = size[0] + 20  # 增加20像素的边距
        window_height = size[1] + 60  # 增加60像素的边距用于按钮和标题栏
        x = (self.root.winfo_screenwidth() - window_width) // 2
        y = (self.root.winfo_screenheight() - window_height) // 2
        window.geometry(f"{window_width}x{window_height}+{x}+{y}")

        # 设置窗口的背景颜色
        window.configure(bg='white')

        # 显示条形码图像
        label = tk.Label(window, image=barcode_image, bg='white')
        label.image = barcode_image
        label.pack(pady=10)

        # 删除按钮
        delete_button = tk.Button(window, text="删除", command=lambda: self.delete_traceability(traceability, window),
                                  bg='white')
        delete_button.pack(side=tk.LEFT, padx=5, pady=5)

        # 取消按钮
        cancel_button = tk.Button(window, text="取消", command=window.destroy, bg='white')
        cancel_button.pack(side=tk.LEFT, padx=5, pady=5)

    def delete_traceability(self, traceability, window):
        barcode = self.last_searched_barcode
        self.data[barcode].remove(traceability)
        if self.webdav_connected:
            write_data_to_webdav(self.filename, self.data)
        else:
            write_data(self.filename, self.data)
        self.display_info(barcode)
        window.destroy()
        self.log_event('DELETE', barcode, self.data[barcode][0], traceability)

    def log_event(self, action, barcode, medication, traceability=None):
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        message = f"{timestamp} - {action} - Barcode: {barcode}, Medication: {medication}"
        if traceability:
            message += f", Traceability: {traceability}"
        logging.info(message)
        print(message)  # 输出到控制台


if __name__ == "__main__":
    root = tk.Tk()
    print("Creating MedicineTrackerApp instance...")
    # logging.info("Creating MedicineTrackerApp instance...")
    app = MedicineTrackerApp(root, data_filename)
    print("Starting main loop...")
    # logging.info("Starting main loop...")
    root.mainloop()
