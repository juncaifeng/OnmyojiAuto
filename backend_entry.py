"""PyInstaller 的绝对导入入口；不要以包内相对导入脚本作为 frozen entry。"""
from OAT.server.__main__ import main


if __name__ == "__main__":
    main()
