from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox

from crypto_utils import decrypt_file, encrypt_file
from file_manager import download_encrypted_file, list_server_files, upload_encrypted_file
from logger_utils import log_info


class SecureCloudApp:
    """基于口令的加密网盘客户端主界面。"""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("基于口令的加密网盘客户端")
        self.root.geometry("900x500")

        self.selected_file_path = ""
        self.server_files: list[dict] = []

        self._build_ui()
        self.refresh_server_files_event()

    def _build_ui(self) -> None:
        title_label = tk.Label(self.root, text="基于口令的加密网盘客户端", font=("Arial", 16, "bold"))
        title_label.pack(pady=10)

        password_frame = tk.Frame(self.root)
        password_frame.pack(fill="x", padx=15, pady=5)
        tk.Label(password_frame, text="口令：", width=10, anchor="w").pack(side="left")
        self.password_entry = tk.Entry(password_frame, show="*", width=50)
        self.password_entry.pack(side="left", padx=5)

        main_frame = tk.Frame(self.root)
        main_frame.pack(fill="both", expand=True, padx=15, pady=10)

        left_frame = tk.LabelFrame(main_frame, text="本地操作", padx=10, pady=10)
        left_frame.pack(side="left", fill="both", expand=True, padx=(0, 8))

        tk.Label(left_frame, text="本地文件路径：", anchor="w").pack(fill="x")
        self.file_path_var = tk.StringVar(value="未选择文件")
        file_path_entry = tk.Entry(left_frame, textvariable=self.file_path_var, state="readonly")
        file_path_entry.pack(fill="x", pady=5)

        tk.Button(left_frame, text="选择文件", command=self.select_file_event, width=16).pack(pady=8)
        tk.Button(left_frame, text="加密上传", command=self.upload_event, width=16).pack(pady=8)

        right_frame = tk.LabelFrame(main_frame, text="服务器密文文件", padx=10, pady=10)
        right_frame.pack(side="right", fill="both", expand=True, padx=(8, 0))

        self.server_listbox = tk.Listbox(right_frame, height=14)
        self.server_listbox.pack(fill="both", expand=True, pady=5)

        button_frame = tk.Frame(right_frame)
        button_frame.pack(fill="x", pady=5)
        tk.Button(button_frame, text="刷新文件列表", command=self.refresh_server_files_event, width=16).pack(side="left", padx=5)
        tk.Button(button_frame, text="下载并解密", command=self.download_event, width=16).pack(side="left", padx=5)

        self.status_var = tk.StringVar(value="就绪")
        status_label = tk.Label(self.root, textvariable=self.status_var, anchor="w", relief="sunken")
        status_label.pack(fill="x", side="bottom")

    def update_status(self, message: str) -> None:
        """更新状态栏文本。"""
        self.status_var.set(message)

    def select_file_event(self) -> None:
        """选择本地文件。"""
        file_path = filedialog.askopenfilename(title="选择要加密的本地文件")
        if not file_path:
            self.update_status("未选择文件")
            return

        self.selected_file_path = file_path
        self.file_path_var.set(file_path)
        log_info("SELECT_FILE", Path(file_path).name, "success")
        self.update_status("已选择本地文件")

    def upload_event(self) -> None:
        """加密并上传文件。"""
        password = self.password_entry.get()
        if not password.strip():
            messagebox.showwarning("提示", "请输入口令后再执行加密上传")
            self.update_status("操作失败：口令为空")
            return

        if not self.selected_file_path:
            messagebox.showwarning("提示", "请先选择本地文件")
            self.update_status("操作失败：未选择本地文件")
            return

        ok, msg, enc_path = encrypt_file(self.selected_file_path, password)
        if not ok:
            messagebox.showerror("加密失败", msg)
            self.update_status(f"操作失败：{msg}")
            return

        ok, upload_msg, server_name = upload_encrypted_file(enc_path)
        if not ok:
            messagebox.showerror("上传失败", upload_msg)
            self.update_status(f"操作失败：{upload_msg}")
            return

        self.refresh_server_files_event()
        self.update_status(f"加密上传成功：{server_name}")
        messagebox.showinfo("成功", f"文件已加密并上传成功\n服务器文件名：{server_name}")

    def refresh_server_files_event(self) -> None:
        """刷新服务器文件列表。"""
        self.server_files = list_server_files()
        self.server_listbox.delete(0, tk.END)

        for item in self.server_files:
            self.server_listbox.insert(tk.END, item["name"])

        self.update_status(f"服务器文件列表已刷新，共 {len(self.server_files)} 个文件")

    def download_event(self) -> None:
        """下载并解密服务器选中的密文文件。"""
        password = self.password_entry.get()
        if not password.strip():
            messagebox.showwarning("提示", "请输入口令后再执行下载解密")
            self.update_status("操作失败：口令为空")
            return

        selected_indices = self.server_listbox.curselection()
        if not selected_indices:
            messagebox.showwarning("提示", "请先从服务器文件列表中选择密文文件")
            self.update_status("操作失败：未选中服务器文件")
            return

        selected_name = self.server_listbox.get(selected_indices[0])
        ok, msg, local_cache_path = download_encrypted_file(selected_name)
        if not ok:
            messagebox.showerror("下载失败", msg)
            self.update_status(f"操作失败：{msg}")
            return

        ok, decrypt_msg, output_path = decrypt_file(local_cache_path, password)
        if not ok:
            messagebox.showerror("解密失败", "口令错误或文件已损坏，解密失败")
            self.update_status(f"操作失败：{decrypt_msg}")
            return

        self.update_status(f"下载并解密成功：{Path(output_path).name}")
        messagebox.showinfo("成功", f"文件已下载并解密成功\n输出路径：{output_path}")

        log_info("DECRYPT", selected_name, "success")

    def run(self) -> None:
        self.root.mainloop()
