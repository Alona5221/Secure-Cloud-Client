# 开启未来注解支持。
from __future__ import annotations

# 导入 tkinter 基础组件。
import tkinter as tk
# 导入 Path 用于提取文件名展示。
from pathlib import Path
# 导入文件选择与消息框组件。
from tkinter import filedialog, messagebox

# 导入加密与解密业务函数。
from crypto_utils import decrypt_file, encrypt_file
# 导入文件管理函数。
from file_manager import download_encrypted_file, list_server_files, upload_encrypted_file
# 导入日志记录函数。
from logger_utils import log_info


# 定义主界面应用类。
class SecureCloudApp:
    """基于口令的加密网盘客户端主界面。"""

    def __init__(self, root: tk.Tk) -> None:
        """初始化窗口与状态。"""
        # 保存根窗口实例。
        self.root = root
        # 设置窗口标题。
        self.root.title("基于口令的加密网盘客户端")
        # 设置窗口尺寸。
        self.root.geometry("900x500")

        # 当前用户选择的本地文件路径。
        self.selected_file_path = ""
        # 服务器文件列表缓存。
        self.server_files: list[dict] = []

        # 构建 UI 组件。
        self._build_ui()
        # 首次启动时刷新服务器列表。
        self.refresh_server_files_event()

    def _build_ui(self) -> None:
        """构建图形界面布局。"""
        # 顶部标题。
        title_label = tk.Label(self.root, text="基于口令的加密网盘客户端", font=("Arial", 16, "bold"))
        # 标题放置。
        title_label.pack(pady=10)

        # 口令输入区域容器。
        password_frame = tk.Frame(self.root)
        # 放置容器。
        password_frame.pack(fill="x", padx=15, pady=5)
        # 口令标签。
        tk.Label(password_frame, text="口令：", width=10, anchor="w").pack(side="left")
        # 口令输入框，启用掩码显示。
        self.password_entry = tk.Entry(password_frame, show="*", width=50)
        # 放置口令输入框。
        self.password_entry.pack(side="left", padx=5)

        # 主体左右分栏容器。
        main_frame = tk.Frame(self.root)
        # 放置主体区域。
        main_frame.pack(fill="both", expand=True, padx=15, pady=10)

        # 左侧：本地操作区域。
        left_frame = tk.LabelFrame(main_frame, text="本地操作", padx=10, pady=10)
        # 放置左侧区域。
        left_frame.pack(side="left", fill="both", expand=True, padx=(0, 8))

        # 本地文件路径标签。
        tk.Label(left_frame, text="本地文件路径：", anchor="w").pack(fill="x")
        # 路径文本变量。
        self.file_path_var = tk.StringVar(value="未选择文件")
        # 只读路径显示框。
        file_path_entry = tk.Entry(left_frame, textvariable=self.file_path_var, state="readonly")
        # 放置路径显示框。
        file_path_entry.pack(fill="x", pady=5)

        # 选择文件按钮。
        tk.Button(left_frame, text="选择文件", command=self.select_file_event, width=16).pack(pady=8)
        # 加密上传按钮。
        tk.Button(left_frame, text="加密上传", command=self.upload_event, width=16).pack(pady=8)

        # 右侧：服务器文件区域。
        right_frame = tk.LabelFrame(main_frame, text="服务器密文文件", padx=10, pady=10)
        # 放置右侧区域。
        right_frame.pack(side="right", fill="both", expand=True, padx=(8, 0))

        # 服务器文件列表控件。
        self.server_listbox = tk.Listbox(right_frame, height=14)
        # 放置列表控件。
        self.server_listbox.pack(fill="both", expand=True, pady=5)

        # 右侧按钮容器。
        button_frame = tk.Frame(right_frame)
        # 放置按钮容器。
        button_frame.pack(fill="x", pady=5)
        # 刷新列表按钮。
        tk.Button(button_frame, text="刷新文件列表", command=self.refresh_server_files_event, width=16).pack(side="left", padx=5)
        # 下载并解密按钮。
        tk.Button(button_frame, text="下载并解密", command=self.download_event, width=16).pack(side="left", padx=5)

        # 底部状态栏变量。
        self.status_var = tk.StringVar(value="就绪")
        # 底部状态栏控件。
        status_label = tk.Label(self.root, textvariable=self.status_var, anchor="w", relief="sunken")
        # 放置底部状态栏。
        status_label.pack(fill="x", side="bottom")

    def update_status(self, message: str) -> None:
        """更新状态栏文本。"""
        # 更新状态变量，自动刷新标签显示。
        self.status_var.set(message)

    def select_file_event(self) -> None:
        """处理“选择文件”按钮事件。"""
        # 打开文件选择对话框。
        file_path = filedialog.askopenfilename(title="选择要加密的本地文件")
        # 若用户取消选择。
        if not file_path:
            # 更新状态提示。
            self.update_status("未选择文件")
            # 结束处理。
            return

        # 保存用户选择路径。
        self.selected_file_path = file_path
        # 在界面中显示路径。
        self.file_path_var.set(file_path)
        # 写入选择文件日志。
        log_info("SELECT_FILE", Path(file_path).name, "success")
        # 更新状态栏。
        self.update_status("已选择本地文件")

    def upload_event(self) -> None:
        """处理“加密上传”按钮事件。"""
        # 获取口令输入。
        password = self.password_entry.get()
        # 若口令为空（或仅空白）。
        if not password.strip():
            # 弹窗提示。
            messagebox.showwarning("提示", "请输入口令后再执行加密上传")
            # 更新状态栏。
            self.update_status("操作失败：口令为空")
            # 结束流程。
            return

        # 若未选择文件。
        if not self.selected_file_path:
            # 弹窗提示。
            messagebox.showwarning("提示", "请先选择本地文件")
            # 更新状态栏。
            self.update_status("操作失败：未选择本地文件")
            # 结束流程。
            return

        # 调用加密逻辑。
        ok, msg, enc_path = encrypt_file(self.selected_file_path, password)
        # 若加密失败。
        if not ok:
            # 弹窗提示错误。
            messagebox.showerror("加密失败", msg)
            # 更新状态栏。
            self.update_status(f"操作失败：{msg}")
            # 停止后续上传。
            return

        # 加密成功后执行上传。
        ok, upload_msg, server_name = upload_encrypted_file(enc_path)
        # 若上传失败。
        if not ok:
            # 弹窗提示。
            messagebox.showerror("上传失败", upload_msg)
            # 更新状态。
            self.update_status(f"操作失败：{upload_msg}")
            # 结束流程。
            return

        # 上传成功后刷新右侧列表。
        self.refresh_server_files_event()
        # 更新状态栏成功提示。
        self.update_status(f"加密上传成功：{server_name}")
        # 弹窗提示成功。
        messagebox.showinfo("成功", f"文件已加密并上传成功\n服务器文件名：{server_name}")

    def refresh_server_files_event(self) -> None:
        """处理“刷新文件列表”按钮事件。"""
        # 拉取服务器密文列表。
        self.server_files = list_server_files()
        # 清空列表框。
        self.server_listbox.delete(0, tk.END)

        # 逐项插入服务器文件名。
        for item in self.server_files:
            self.server_listbox.insert(tk.END, item["name"])

        # 更新状态栏。
        self.update_status(f"服务器文件列表已刷新，共 {len(self.server_files)} 个文件")

    def download_event(self) -> None:
        """处理“下载并解密”按钮事件。"""
        # 获取当前输入口令。
        password = self.password_entry.get()
        # 校验口令非空。
        if not password.strip():
            # 弹窗提示。
            messagebox.showwarning("提示", "请输入口令后再执行下载解密")
            # 更新状态栏。
            self.update_status("操作失败：口令为空")
            # 结束处理。
            return

        # 获取当前列表选中项索引。
        selected_indices = self.server_listbox.curselection()
        # 若未选中。
        if not selected_indices:
            # 弹窗提示。
            messagebox.showwarning("提示", "请先从服务器文件列表中选择密文文件")
            # 更新状态。
            self.update_status("操作失败：未选中服务器文件")
            # 结束处理。
            return

        # 取选中文件名。
        selected_name = self.server_listbox.get(selected_indices[0])
        # 执行下载到 client_cache。
        ok, msg, local_cache_path = download_encrypted_file(selected_name)
        # 若下载失败。
        if not ok:
            # 弹窗提示。
            messagebox.showerror("下载失败", msg)
            # 更新状态。
            self.update_status(f"操作失败：{msg}")
            # 结束处理。
            return

        # 下载成功后执行解密。
        ok, decrypt_msg, output_path = decrypt_file(local_cache_path, password)
        # 若解密失败。
        if not ok:
            # 统一错误文案。
            messagebox.showerror("解密失败", "口令错误或文件已损坏，解密失败")
            # 更新状态。
            self.update_status(f"操作失败：{decrypt_msg}")
            # 结束处理。
            return

        # 更新状态栏成功提示。
        self.update_status(f"下载并解密成功：{Path(output_path).name}")
        # 弹窗显示输出路径。
        messagebox.showinfo("成功", f"文件已下载并解密成功\n输出路径：{output_path}")

        # 记录成功日志。
        log_info("DECRYPT", selected_name, "success")

    def run(self) -> None:
        """启动 Tk 事件循环。"""
        # 进入界面主循环。
        self.root.mainloop()
