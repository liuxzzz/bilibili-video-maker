import uiautomator2 as u2


def main():
    d = u2.connect()  # 连接多台设备需要指定设备序列号

    print(d.info)


if __name__ == "__main__":
    main()
