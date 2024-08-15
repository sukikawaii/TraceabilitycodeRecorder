import os
import json
from webdav3.client import Client
import tkinter as tk
from tkinter import ttk
from ttkbootstrap import Style
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
        # print("Loaded WebDAV configuration:", config)
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
        # print(f"Error checking WebDAV connection: {e}")
        # logging.error(f"Error checking WebDAV connection: {e}")
        return False, {}


class MedicineTrackerApp:
    def __init__(self, root, filename):
        self.root = root
        self.filename = filename
        self.data = None
        self.last_searched_barcode = None
        root.resizable(False, False)
        root.iconbitmap('app_icon.ico')


        # 检查WebDAV连接
        self.webdav_connected, self.data = check_webdav_connection(self.filename)
        if not self.webdav_connected:
            # 如果WebDAV连接失败，尝试从本地读取数据
            self.data = read_data(self.filename)



        # 设置窗口标题
        self.root.title(f"追溯码记录器")
        self.center_window(self.root)


        # 输入框
        self.barcode_entry = tk.Entry(root, width=40)
        self.barcode_entry.grid(row=0, column=0, pady=10, padx=20, sticky='ew')  # 使用grid布局
        self.barcode_entry.focus_set()  # 默认焦点
        self.barcode_entry.bind('<Return>', self.on_search_or_add_traceability)

        # 添加追溯码按钮
        self.add_traceability_button = tk.Button(root, text="添加追溯码", command=self.on_add_traceability)
        self.add_traceability_button.grid(row=0, column=1, pady=5, padx=0)  # 使用grid布局

        # 添加显示所有药品信息的按钮
        self.show_all_button = tk.Button(root, text="显示所有药品信息", command=self.show_all_medications)
        self.show_all_button.grid(row=1, column=0, columnspan=2, pady=5)  # 使用grid布局

        # 添加药名
        # self.add_medication_button = tk.Button(root, text="添加药名")
        # self.add_medication_button.grid(row=1, column=1, sticky='ew', padx=5)


        # 显示药品信息
        self.medication_label = tk.Label(root, text="", wraplength=300)
        self.medication_label.grid(row=2, column=0, columnspan=2, pady=10)  # 使用grid布局

        # 显示追溯码列表
        self.traceability_listbox = tk.Listbox(root, width=50)
        self.traceability_listbox.grid(row=3, column=0, columnspan=2, pady=10)  # 使用grid布局
        self.traceability_listbox.bind('<Double-Button-1>', self.on_copy_and_delete)

        # 设置主窗口的背景颜色
        self.root.configure(bg='white')


        # 添加设置按钮
        self.settings_button = tk.Button(root, text="设置", command=self.open_settings_window)
        self.settings_button.grid(row=7, column=0, columnspan=2, pady=5)  # 使用grid布局

    def open_settings_window(self):
        settings_window = tk.Toplevel(self.root)
        settings_window.title("设置")
        window_width = 400
        window_height = 300
        screen_width = settings_window.winfo_screenwidth()
        screen_height = settings_window.winfo_screenheight()
        settings_window.resizable(False, False)  # 禁止调整窗口大小
        settings_window.iconbitmap('app_icon.ico')  # 设置窗口图标

        # 计算窗口居中的位置
        x_cordinate = int((screen_width / 2) - (window_width / 2))
        y_cordinate = int((screen_height / 2) - (window_height / 2))

        # 设置窗口的几何尺寸，包括位置
        settings_window.geometry(f"{window_width}x{window_height}+{x_cordinate+40}+{y_cordinate+80}")

        notebook = ttk.Notebook(settings_window)
        notebook.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # 实验室标签页
        lab_tab = ttk.Frame(notebook)
        notebook.add(lab_tab, text="实验室")
        self.create_lab_interface(lab_tab)

        # 登录标签页
        login_tab = ttk.Frame(notebook)
        notebook.add(login_tab, text="登录")
        self.create_login_interface(login_tab)

        # WebDAV标签页
        webdav_tab = ttk.Frame(notebook)
        notebook.add(webdav_tab, text="WebDAV")
        self.create_webdav_interface(webdav_tab)

        # 导入导出标签页
        io_tab = ttk.Frame(notebook)
        notebook.add(io_tab, text="导入导出")
        self.create_io_interface(io_tab)

        # 关于标签页
        about_tab = ttk.Frame(notebook)
        notebook.add(about_tab, text="关于")
        self.create_about_interface(about_tab)

    def create_lab_interface(self, parent):
        # 监听扫码枪
        checkbox_var = tk.BooleanVar()
        ttk.Checkbutton(parent, text="监听扫码枪", variable=checkbox_var).pack(pady=5)

        # 监听销售平台
        checkbox_var = tk.BooleanVar()
        ttk.Checkbutton(parent, text="监听销售平台", variable=checkbox_var).pack(pady=5)

        # 连接状态
        self.connection_status_label = ttk.Label(parent, text="", font=("Arial", 10))
        self.connection_status_label.pack(padx=10, pady=5)
        self.update_connection_status()

    def update_connection_status(self):
        if self.webdav_connected:
            self.connection_status_label.config(text="已成功连接WebDAV服务器", foreground="green")
        else:
            self.connection_status_label.config(text="未连接WebDAV服务器", foreground="red")

    def create_login_interface(self, parent):
        style = ttk.Style()
        style.configure('Passport.TLabel', font=('Arial', 24))
        ttk.Label(parent, text="通行证", style='Passport.TLabel').pack(pady=10)

        ttk.Label(parent, text="用户名:").pack()
        username_entry = ttk.Entry(parent)
        username_entry.pack(pady=5)

        ttk.Label(parent, text="密码:").pack()
        password_entry = ttk.Entry(parent, show="*")
        password_entry.pack(pady=5)

        login_button = ttk.Button(parent, text="登录", command=lambda: self.login(username_entry, password_entry))
        login_button.pack(pady=10)

    def login(self, username_entry, password_entry):
        # 登录逻辑
        pass

    def create_webdav_interface(self, parent):
        webdav_config = load_webdav_config()

        # 设置居中布局
        for i in range(4):
            parent.columnconfigure(i, weight=1)

        # 读取配置文件中的值
        hostname = webdav_config.get('webdav_hostname', '')
        username = webdav_config.get('webdav_login', '')
        password = webdav_config.get('webdav_password', '')
        root = webdav_config.get('webdav_root', '')

        # 创建输入框和标签
        ttk.Label(parent, text="主机名:").grid(row=0, column=0, sticky='e')
        hostname_entry = ttk.Entry(parent, width=40)
        hostname_entry.insert(0, hostname)
        hostname_entry.grid(row=0, column=1, columnspan=3, padx=5, pady=5)

        ttk.Label(parent, text="用户名:").grid(row=1, column=0, sticky='e')
        username_entry = ttk.Entry(parent, width=40)
        username_entry.insert(0, username)
        username_entry.grid(row=1, column=1, columnspan=3, padx=5, pady=5)

        ttk.Label(parent, text="密码:").grid(row=2, column=0, sticky='e')
        password_entry = ttk.Entry(parent, show="*", width=40)
        password_entry.insert(0, password)
        password_entry.grid(row=2, column=1, columnspan=3, padx=5, pady=5)

        ttk.Label(parent, text="根路径:").grid(row=3, column=0, sticky='e')
        root_entry = ttk.Entry(parent, width=40)
        root_entry.insert(0, root)
        root_entry.grid(row=3, column=1, columnspan=3, padx=5, pady=5)

        # 保存按钮
        save_button = ttk.Button(parent, text="保存", command=lambda: self.save_webdav_config(webdav_config, hostname_entry, username_entry, password_entry, root_entry))
        save_button.grid(row=4, column=2, pady=10)

    def save_webdav_config(self, config, hostname_entry, username_entry, password_entry, root_entry):
        # 更新配置
        config['webdav_hostname'] = hostname_entry.get()
        config['webdav_login'] = username_entry.get()
        config['webdav_password'] = password_entry.get()
        config['webdav_root'] = root_entry.get()

        # 保存配置
        with open('webdav_config.json', 'w') as file:
            json.dump(config, file, indent=4)

        # 更新连接状态
        self.webdav_connected = check_webdav_connection(config)
        self.update_connection_status()

    def create_io_interface(self, parent):
        # 设置居中布局
        parent.columnconfigure(0, weight=1)

        import_button = ttk.Button(parent, text="导入")
        import_button.pack(pady=5)

        export_button = ttk.Button(parent, text="导出")
        export_button.pack(pady=5)


    def create_about_interface(self, parent):
        # 设置居中布局
        parent.columnconfigure(0, weight=1)

        ttk.Label(parent, text="这是关于页面。").pack(padx=10, pady=10)
        developer_label = ttk.Label(parent, text="by 张强")
        developer_label.pack(pady=5)
        version_number = "0.1.1"
        version_label = ttk.Label(parent, text=f"版本: {version_number}")
        version_label.pack(pady=5)

    def show_all_medications(self):
        # 创建一个顶级窗口来显示所有药品信息
        all_medications_window = tk.Toplevel(self.root)
        all_medications_window.title("所有药品信息")

        # 计算弹窗大小
        item_height = 20  # 每个项目的高度
        padding = 10  # 内边距
        border_width = 2  # 边框宽度
        window_width = 400  # 固定宽度
        window_height = (len(self.data) * item_height) + (padding * 2) + border_width * 2

        # 居中显示弹窗
        screen_width = all_medications_window.winfo_screenwidth()
        screen_height = all_medications_window.winfo_screenheight()
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        all_medications_window.geometry(f"{window_width}x{window_height}+{x+30}+{y-20}")

        all_medications_listbox = tk.Listbox(all_medications_window, selectmode=tk.SINGLE, width=50,
                                             height=len(self.data))
        all_medications_listbox.pack(padx=padding, pady=padding, fill=tk.BOTH, expand=True)

        for barcode, (medication, *traceabilities) in self.data.items():
            info_text = f"条形码: {barcode}  \n追溯码数量: {len(traceabilities)}  \n药品名称: {medication}"
            all_medications_listbox.insert(tk.END, info_text)

        # 默认选择第一个项目
        all_medications_listbox.select_set(0)  # 选择第一个项目
        all_medications_listbox.event_generate("<<ListboxSelect>>")  # 触发选择事件

        def on_select(event):
            selected_index = all_medications_listbox.curselection()
            if selected_index:
                index = selected_index[0]
                barcode, (medication, *traceabilities) = list(self.data.items())[index]
                self.display_info(barcode)
                self.last_searched_barcode = barcode
                all_medications_window.destroy()

        all_medications_listbox.bind('<<ListboxSelect>>', lambda event: None)  # 避免默认选择行为
        all_medications_listbox.bind('<Double-Button-1>', lambda event: on_select(event))  # 双击选择
        all_medications_listbox.bind('<Return>', lambda event: on_select(event))  # 回车键选择
        all_medications_listbox.bind('<Up>',
                                     lambda event: self.handle_up_down_key(all_medications_listbox, event))  # 上键
        all_medications_listbox.bind('<Down>',
                                     lambda event: self.handle_up_down_key(all_medications_listbox, event))  # 下键
        all_medications_listbox.focus_set()  # 设置焦点
        all_medications_window.bind('<Escape>', lambda event: all_medications_window.destroy())

    def center_window(self, window):
        # 获取屏幕尺寸
        screen_width = window.winfo_screenwidth()
        screen_height = window.winfo_screenheight()

        # 计算窗口位置使其居中
        x = (screen_width - 400) // 2
        y = (screen_height - 420) // 2  # 调整窗口高度
        window.geometry(f"400x420+{x}+{y}")  # 调整窗口高度

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

        # 新增的检查：验证条形码是否为13位数字或为"0"
        if (search_term.isdigit() and len(search_term) == 13) or search_term == "0":
            self.barcode_entry.delete(0, tk.END)  # 清除输入框内容

            # 如果是13位数字或"0"，则按条形码搜索
            if search_term in self.data:
                self.display_info(search_term)
                self.last_searched_barcode = search_term
            else:
                if messagebox.askyesno("提示", "未找到条形码信息，是否创建新记录？"):
                    self.create_new_record(search_term)
                else:
                    messagebox.showinfo("提示", "未找到相关药品，请检查输入或创建新记录。")
        elif search_term.isdigit():  # 如果是数字但不是13位
            messagebox.showerror("错误", "条形码必须是13位数字。")
        else:  # 如果不是数字，按药品名称搜索
            matches = []
            for barcode, (medication, *traceabilities) in self.data.items():
                if search_term.lower() in medication.lower():
                    matches.append((medication, barcode, traceabilities))
            if matches:
                self.show_multiple_matches(matches)
            else:
                messagebox.showinfo("提示", "未找到相关药品，请检查输入。")

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
        match_window.geometry(f"{window_width}x{window_height}+{x+30}+{y-20}")

        listbox = tk.Listbox(match_window, selectmode=tk.SINGLE, width=50, height=len(matches))
        listbox.pack(padx=padding, pady=padding, fill=tk.BOTH, expand=True)

        for medication, barcode, traceabilities in matches:
            info_text = f"条形码: {barcode}\n  追溯码数量: {len(traceabilities)}\n  药品名称: {medication}"
            listbox.insert(tk.END, info_text)

        # 默认选择第一个项目
        listbox.select_set(0)  # 选择第一个项目
        listbox.event_generate("<<ListboxSelect>>")  # 触发选择事件
        match_window.bind('<Escape>', lambda event: match_window.destroy())

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
            # 新增的检查：验证追溯码是否为20位数字
            while True:
                traceability = simpledialog.askstring("输入", "请输入追溯码:")
                if traceability and (traceability.isdigit() and len(traceability) == 20):
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
                            break
                    else:
                        self.data[barcode] = [medication, traceability]
                        if self.webdav_connected:
                            write_data_to_webdav(self.filename, self.data)
                        else:
                            write_data(self.filename, self.data)
                        self.display_info(barcode)
                        self.last_searched_barcode = barcode
                        self.log_event('CREATE', barcode, medication, traceability)
                        break
                elif traceability:
                    messagebox.showerror("错误", "追溯码必须是20位数字。")
                else:
                    break
        self.barcode_entry.focus_set()


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

        # 新增的检查：验证追溯码是否为20位数字
        while True:
            traceability = simpledialog.askstring("输入", "请输入新的追溯码:")
            if traceability and (traceability.isdigit() and len(traceability) == 20):
                if traceability in self.data.get(self.last_searched_barcode, []):
                    messagebox.showerror("错误", "该追溯码已存在，不能添加重复的追溯码。")
                elif self.check_traceability_in_logs(traceability):
                    response = messagebox.askyesno("提示",
                                                   f"该追溯码已于 {self.find_traceability_date(traceability)} 添加过，是否继续添加？")
                    if response:
                        self.data[self.last_searched_barcode].append(traceability)
                        if self.webdav_connected:
                            write_data_to_webdav(self.filename, self.data)
                        else:
                            write_data(self.filename, self.data)
                        self.display_info(self.last_searched_barcode)
                        self.log_event('ADD', self.last_searched_barcode, self.data[self.last_searched_barcode][0],
                                       traceability)
                        break
                else:
                    self.data[self.last_searched_barcode].append(traceability)
                    if self.webdav_connected:
                        write_data_to_webdav(self.filename, self.data)
                    else:
                        write_data(self.filename, self.data)
                    self.display_info(self.last_searched_barcode)
                    self.log_event('ADD', self.last_searched_barcode, self.data[self.last_searched_barcode][0],
                                   traceability)
                    break
            elif traceability:
                messagebox.showerror("错误", "追溯码必须是20位数字。")
            else:
                break

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
    style = Style(theme='litera')
    app = MedicineTrackerApp(root, data_filename)
    root.mainloop()
