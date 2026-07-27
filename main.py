#!/usr/bin/env python3
from controller import Controller

def main():
    controller = Controller()
    try:
        controller.run()
    finally:
        controller.shutdown()  # 保存 storage 数据

if __name__ == "__main__":
    main()
