"""从 GitHub Releases 下载官方 frpc 客户端"""
import os
import platform
import re
import shutil
import tempfile
import zipfile
import xml.etree.ElementTree as ET

import requests

GITHUB_RELEASES_API = "https://api.github.com/repos/fatedier/frp/releases"
GITHUB_RELEASES_ATOM = "https://github.com/fatedier/frp/releases.atom"
GITHUB_HEADERS = {
    "Accept": "application/vnd.github+json",
    "User-Agent": "frpc-desktop",
}
FALLBACK_TAGS = (
    "v0.71.0",
    "v0.70.1",
    "v0.70.0",
    "v0.69.1",
    "v0.69.0",
    "v0.68.1",
    "v0.68.0",
    "v0.67.0",
    "v0.66.0",
    "v0.65.0",
)
MAX_DOWNLOAD_BYTES = 80 * 1024 * 1024
MIN_ZIP_BYTES = 1024 * 1024
TAG_PATTERN = re.compile(r"^v?\d+\.\d+(\.\d+)?(?:-[\w.]+)?$")
ZIP_MAGIC = b"PK\x03\x04"


def detect_windows_arch():
    """检测当前 Windows 架构对应的 frp 资源后缀"""
    machine = platform.machine().lower()
    if machine in ("arm64", "aarch64"):
        return "windows_arm64"
    if machine in ("x86", "i386", "i686"):
        return "windows_386"
    return "windows_amd64"


def _tag_to_version(tag):
    return tag[1:] if tag.startswith("v") else tag


def fetch_releases(limit=20):
    """
    获取 frp 发行版列表

    返回:
        (releases, warning)
        releases: [{tag, name, prerelease, published_at}, ...]
    """
    try:
        response = requests.get(
            GITHUB_RELEASES_API,
            headers=GITHUB_HEADERS,
            params={"per_page": limit},
            timeout=20,
        )
        if response.status_code == 200:
            releases = []
            for item in response.json():
                tag = _normalize_tag(item.get("tag_name") or "")
                if not tag:
                    continue
                releases.append(
                    {
                        "tag": tag,
                        "name": item.get("name") or tag,
                        "prerelease": bool(item.get("prerelease")),
                        "published_at": item.get("published_at") or "",
                    }
                )
            if releases:
                return releases[:limit], None
    except Exception:
        pass

    atom_releases, atom_error = _fetch_releases_from_atom(limit)
    if atom_releases:
        return atom_releases, None
    if atom_error:
        return _fallback_releases(f"{atom_error}，已提供常用版本作为备选")
    return _fallback_releases("未获取到可用版本，已提供常用版本作为备选")


def _fetch_releases_from_atom(limit=20):
    try:
        response = requests.get(
            GITHUB_RELEASES_ATOM,
            headers={"User-Agent": "frpc-desktop"},
            timeout=20,
        )
        if response.status_code != 200:
            return [], f"获取版本列表失败（HTTP {response.status_code}）"

        root = ET.fromstring(response.content)
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        releases = []
        for entry in root.findall("atom:entry", ns):
            title = (entry.findtext("atom:title", default="", namespaces=ns) or "").strip()
            link = ""
            link_el = entry.find("atom:link", ns)
            if link_el is not None:
                link = link_el.get("href") or ""
            tag = ""
            match = re.search(r"/releases/tag/([^/]+)$", link)
            if match:
                tag = match.group(1)
            elif re.match(r"^v?\d+\.\d+", title):
                tag = title.split()[0]
            if tag and TAG_PATTERN.match(tag):
                releases.append(
                    {
                        "tag": tag,
                        "name": title or tag,
                        "prerelease": False,
                        "published_at": entry.findtext("atom:updated", default="", namespaces=ns) or "",
                    }
                )
            if len(releases) >= limit:
                break
        return releases, None
    except requests.exceptions.RequestException as exc:
        return [], f"无法连接 GitHub：{exc}"
    except Exception as exc:
        return [], f"解析版本列表失败：{exc}"


def _fallback_releases(message):
    releases = [{"tag": tag, "name": tag, "prerelease": False, "published_at": ""} for tag in FALLBACK_TAGS]
    return releases, message


def _normalize_tag(tag):
    tag = (tag or "").strip()
    if not TAG_PATTERN.match(tag):
        return None
    return tag


def _asset_url(tag, arch):
    version = _tag_to_version(tag)
    filename = f"frp_{version}_{arch}.zip"
    return f"https://github.com/fatedier/frp/releases/download/{tag}/{filename}", filename


def _iter_download_urls(direct_url):
    yield direct_url
    yield f"https://ghproxy.net/{direct_url}"
    yield f"https://mirror.ghproxy.com/{direct_url}"


def download_frpc(tag, dest_dir="frp", progress_callback=None, arch=None):
    """
    下载指定版本的 Windows frpc.exe

    参数:
        tag: 发行版标签，例如 v0.71.0
        dest_dir: 解压后的存放目录
        progress_callback: fn(downloaded, total)
        arch: 资源架构，默认自动检测

    返回:
        (exe_path, error)
    """
    tag = _normalize_tag(tag)
    if not tag:
        return None, "版本号无效"

    arch = arch or detect_windows_arch()
    direct_url, filename = _asset_url(tag, arch)
    os.makedirs(dest_dir, exist_ok=True)

    tmp_dir = tempfile.mkdtemp(prefix="frpc-dl-")
    zip_path = os.path.join(tmp_dir, filename)
    last_error = None

    try:
        downloaded_ok = False
        for url in _iter_download_urls(direct_url):
            try:
                _download_file(url, zip_path, progress_callback)
                downloaded_ok = True
                break
            except Exception as exc:
                last_error = exc
                continue

        if not downloaded_ok:
            return None, f"下载失败：{last_error}"

        exe_path = _extract_frpc_exe(zip_path, dest_dir)
        if not exe_path:
            return None, "压缩包中未找到 frpc.exe"
        return os.path.abspath(exe_path), None
    except Exception as exc:
        return None, f"下载或解压失败：{exc}"
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def _download_file(url, dest_path, progress_callback=None):
    with requests.get(
        url,
        headers={"User-Agent": "frpc-desktop"},
        stream=True,
        timeout=60,
        allow_redirects=True,
    ) as response:
        if response.status_code != 200:
            raise RuntimeError(f"HTTP {response.status_code} ({url})")

        total = int(response.headers.get("content-length") or 0)
        if total > MAX_DOWNLOAD_BYTES:
            raise RuntimeError("安装包超过大小限制")

        downloaded = 0
        with open(dest_path, "wb") as handle:
            for chunk in response.iter_content(chunk_size=1024 * 64):
                if not chunk:
                    continue
                downloaded += len(chunk)
                if downloaded > MAX_DOWNLOAD_BYTES:
                    raise RuntimeError("安装包超过大小限制")
                handle.write(chunk)
                if progress_callback:
                    progress_callback(downloaded, total)

        size = os.path.getsize(dest_path)
        if size < MIN_ZIP_BYTES:
            raise RuntimeError("下载文件过小，可能不是有效安装包")
        with open(dest_path, "rb") as handle:
            magic = handle.read(4)
        if magic != ZIP_MAGIC:
            raise RuntimeError("下载内容不是有效的 zip 安装包")


def _extract_frpc_exe(zip_path, dest_dir):
    with zipfile.ZipFile(zip_path) as archive:
        if archive.testzip() is not None:
            raise RuntimeError("压缩包损坏")
        member = None
        for name in archive.namelist():
            if ".." in name.replace("\\", "/").split("/"):
                continue
            basename = os.path.basename(name).lower()
            if basename == "frpc.exe" and not name.endswith("/"):
                member = name
                break
        if not member:
            return None

        info = archive.getinfo(member)
        if info.file_size > MAX_DOWNLOAD_BYTES:
            raise RuntimeError("可执行文件超过大小限制")

        target = os.path.join(dest_dir, "frpc.exe")
        temp_target = target + ".tmp"
        with archive.open(member) as source, open(temp_target, "wb") as output:
            shutil.copyfileobj(source, output)
        if os.path.getsize(temp_target) < 1024 * 100:
            os.remove(temp_target)
            raise RuntimeError("解压出的 frpc.exe 无效")
        os.replace(temp_target, target)
        return target
