# 导入 tkinter，用于创建根窗口。
import tkinter as tk

# 导入目录初始化函数。
from config import init_directories
# 导入日志初始化与记录函数。
from logger_utils import log_info, setup_logger
# 导入界面应用类。
from ui import SecureCloudApp


def main() -> None:
    """应用入口：初始化环境并启动 GUI。"""
    # 初始化项目目录结构。
    init_directories()
    # 初始化日志系统。
    setup_logger()
    # 记录程序启动日志。
    log_info("INIT", "", "application started")

    # 创建 Tk 根窗口。
    root = tk.Tk()
    # 初始化主应用。
    app = SecureCloudApp(root)
    # 启动 GUI 主循环。
    app.run()


# 当本文件作为脚本直接执行时，进入程序入口。
if __name__ == "__main__":
    # 调用主函数。
    main()
