"""
发布打包脚本

生成带 logo.ico 的单文件可执行程序，命名规则：
frp-desktop-{版本号}.exe
"""
import os
import shutil
import subprocess
import sys

from app.version import (
    RELEASE_INFO_FILE,
    __version__,
    get_release_exe_basename,
    get_release_exe_name,
    write_release_info,
)


ROOT = os.path.dirname(os.path.abspath(__file__))
ICON_FILE = "logo.ico"
ENTRY_SCRIPT = "main.py"


def main():
    os.chdir(ROOT)
    icon_path = os.path.join(ROOT, ICON_FILE)
    if not os.path.exists(icon_path):
        print(f"错误：未找到图标文件 {ICON_FILE}")
        return 1
    if not os.path.exists(os.path.join(ROOT, ENTRY_SCRIPT)):
        print(f"错误：未找到入口文件 {ENTRY_SCRIPT}")
        return 1

    release_info_path = write_release_info(ROOT)
    print(f"已写入发布信息：{release_info_path}")

    basename = get_release_exe_basename()
    exe_name = get_release_exe_name()
    data_sep = ";" if os.name == "nt" else ":"

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onefile",
        "--windowed",
        f"--icon={ICON_FILE}",
        f"--name={basename}",
        f"--add-data={ICON_FILE}{data_sep}.",
        f"--add-data={RELEASE_INFO_FILE}{data_sep}.",
        "--collect-all",
        "requests",
        ENTRY_SCRIPT,
    ]

    print(f"开始打包：版本 {__version__}")
    print(f"输出文件：dist/{exe_name}")
    print("命令：", " ".join(cmd))
    result = subprocess.run(cmd, cwd=ROOT)
    if result.returncode != 0:
        print("打包失败")
        return result.returncode

    dist_exe = os.path.join(ROOT, "dist", exe_name)
    if not os.path.exists(dist_exe):
        print(f"打包完成，但未找到预期文件：{dist_exe}")
        return 1

    # 清理临时生成的同名 spec，避免仓库里堆积中间文件
    generated_spec = os.path.join(ROOT, f"{basename}.spec")
    if os.path.exists(generated_spec):
        os.remove(generated_spec)

    build_dir = os.path.join(ROOT, "build", basename)
    if os.path.isdir(build_dir):
        shutil.rmtree(build_dir, ignore_errors=True)

    print(f"打包成功：{dist_exe}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
