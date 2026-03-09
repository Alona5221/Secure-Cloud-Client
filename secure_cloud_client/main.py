import tkinter as tk

from config import init_directories
from logger_utils import log_info, setup_logger
from ui import SecureCloudApp


def main() -> None:
    """应用入口：初始化环境并启动 GUI。"""
    init_directories()
    setup_logger()
    log_info("INIT", "", "application started")

    root = tk.Tk()
    app = SecureCloudApp(root)
    app.run()


if __name__ == "__main__":
    main()
