#!/root/.python-env/bin/python

import os
import sys
import time
import shutil
import pathlib
import tarfile
import tempfile
import subprocess
import urllib.request
from datetime import datetime
import logging

def run(cmd: str, cwd: str = None, capture: bool = False) -> subprocess.CompletedProcess:
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            executable="/bin/bash",
            cwd=cwd,
            capture_output=capture,
            text=True,
            check=True
        )
        return result
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"命令执行失败: {cmd}\n{e.stderr}")
class Config:
    RCLONE_REMOTE = "FEADXUS-Google-Drive"
    RCLONE_REMOTE_PATH = f"{RCLONE_REMOTE}:/desktop/"
    MOUNT_POINT = "/tmp/Command"
CONFIG = Config()
PASSWORD_FOUR = "083AA5F2FD75585D1DE42D6D9977723DBA26F4653653F722"
DISK_VOLUME = "/tmp/Command/R-T"
DISK_POINT = "/tmp/disk_1"
pip_packages = [
    "google-auth-oauthlib",
    "google-api-python-client"
]
subprocess.check_call(["pip3", "install", *pip_packages])
veracrypt_url = "https://github.com/veracrypt/VeraCrypt/releases/download/VeraCrypt_1.26.29/veracrypt-console-1.26.29-Debian-13-amd64.deb"
veracrypt_deb = "/tmp/veracrypt-console-1.26.29-amd64.deb"
urllib.request.urlretrieve(veracrypt_url, veracrypt_deb)
subprocess.check_call(["sudo", "apt-get", "install", "-y", veracrypt_deb])
subprocess.check_call(["sudo", "apt-get", "install", "-y", "secure-delete"])
os.remove(veracrypt_deb)
subprocess.run(
    "curl -fsSL https://rclone.org/install.sh | sudo bash",
    shell=True,
    executable="/bin/bash",
    check=True,
)
def setup_rclone_config() -> None:
    rclone_secret = os.getenv("RCLONE_SECRET_DATA")
    if not rclone_secret:
        raise RuntimeError("❌ RCLONE_SECRET_DATA 环境变量未设置")
    conf_dir = os.path.expanduser("~/.config/rclone")
    os.makedirs(conf_dir, exist_ok=True)
    conf_path = os.path.join(conf_dir, "rclone.conf")
    with open(conf_path, "w", encoding="utf-8") as f:
        f.write(rclone_secret)
    print(f"✅ rclone 配置已写入: {conf_path}")
def mount_remote_command() -> None:
    mount_point = pathlib.Path(Config.MOUNT_POINT)
    mount_point.mkdir(parents=True, exist_ok=True)
    log_file = pathlib.Path("/tmp/rclone-command.log")
    cmd = [
        "rclone",
        "mount",
        Config.RCLONE_REMOTE_PATH,
        str(mount_point),
        "--config",
        os.path.expanduser("~/.config/rclone/rclone.conf"),
        "--vfs-cache-mode",
        "writes",
        "--log-level",
        "INFO",
        "--log-file",
        str(log_file),
    ]
    print("启动 rclone 后台挂载...")
    print(f"日志文件: {log_file}")
    with open(log_file, "w", encoding="utf-8") as log:
        process = subprocess.Popen(
            cmd,
            stdin=subprocess.DEVNULL,
            stdout=log,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
    for _ in range(30):
        time.sleep(1)
        return_code = process.poll()
        if return_code is not None:
            log_content = ""
            if log_file.exists():
                log_content = log_file.read_text(
                    encoding="utf-8",
                    errors="replace",
                )
            raise RuntimeError(
                f"❌ rclone 启动失败,返回码: {return_code}\n"
                f"日志内容:\n{log_content}"
            )
        result = subprocess.run(
            ["mountpoint", "-q", str(mount_point)],
            check=False,
        )
        if result.returncode == 0:
            print(
                f"✅ 已后台挂载"
                f"{Config.RCLONE_REMOTE_PATH} → {mount_point}"
            )
            return
    process.terminate()
    log_content = ""
    if log_file.exists():
        log_content = log_file.read_text(
            encoding="utf-8",
            errors="replace",
        )
    raise RuntimeError(
        f"❌ 挂载超时: {mount_point}\n"
        f"rclone 日志:\n{log_content}"
    )
def check_and_create_mount_point(mount_point):
    if not os.path.exists(mount_point):
        try:
            os.makedirs(mount_point)
            logging.info(f"2 ✅ 创建目录: {mount_point}")
            return True
        except OSError as e:
            logging.error(f"2 ❌ 创建目录失败: {e}")
            sys.exit(1)
    else:
        logging.info(f"2 ✅ 目录已存在: {mount_point}")
        return True
def run_veracrypt():
    command = [
        '/usr/bin/veracrypt',
        '--slot', '9',
        '--pim', '0',
        '--mount-options', 'nokernelcrypto',
        DISK_VOLUME,
        '--password', f'{PASSWORD_FOUR}',
        '--protect-hidden', 'no',
        '--keyfiles', '',
        DISK_POINT
    ]
    try:
        result = subprocess.run(
            command,
            capture_output=True, text=True, check=False
        )
        if result.returncode != 0:
            logging.error(f"❌ Veracrypt 执行失败: {result.stderr}")
            return False
        try:
            df_result = subprocess.run(
                ['df', DISK_POINT],
                check=True,
                capture_output=True, text=True
            )
            logging.info("4 ✅ Veracrypt 挂载成功")
            return True
        except Exception as e:
            logging.error(f"4 ❌ 无法通过 df 查询挂载状态: {e}")
            return False
    except FileNotFoundError:
        logging.error("4 ❌ Veracrypt 未找到!请检查路径或安装.")
        return False
    except Exception as e:
        logging.error(f"4 ❌ 解密分区执行异常: {e}")
        return False
def execute_script(script_path, *args):
    try:
        if not os.path.isfile(script_path):
            logging.error(f"脚本路径不存在: {script_path}")
            return None
        command = ['bash', script_path] + list(args)
        subprocess.Popen(
            command,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True
        )
    except Exception as e:
        print(f"❌ 执行失败: {e}")
        return None
def main() -> None:
    extract_dir = None
    try:
        print("[设置 rclone 配置]")
        setup_rclone_config()
        print("[挂载网盘目录]")
        mount_remote_command()
        print("[创建挂载点目录]")
        check_and_create_mount_point(DISK_POINT)
        print("[执行 Veracrypt 解密]")
        run_veracrypt()
        print("[执行脚本]")
        script_path = "/tmp/disk_1/deploy_open_retry.sh"
        execute_script(script_path)
    except Exception as e:
        print(f"发生错误: {e}")
if __name__ == "__main__":
    main()
