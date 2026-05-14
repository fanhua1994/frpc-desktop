import os
import json
import requests
from typing import Optional, Dict, Any, List, Tuple


def get_web_auth() -> Optional[Tuple[str, str]]:
    """从 frpc_config.json 中获取 Web 服务认证信息"""
    config_file = 'frpc_config.json'
    if os.path.exists(config_file):
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                username = config.get('web_username', '')
                password = config.get('web_password', '')
                if username and password:
                    return (username, password)
        except:
            pass
    
    return None


def get_base_url() -> Optional[str]:
    """从 frpc_config.json 中读取 webServer 配置，构建 baseUrl"""
    config_file = 'frpc_config.json'
    if not os.path.exists(config_file):
        return None
    
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        web_addr = config.get('web_addr')
        web_port = config.get('web_port')
        
        if not web_addr or not web_port:
            return None
        
        # 构建 baseUrl
        base_url = f"http://{web_addr}:{web_port}"
        return base_url
    except Exception as e:
        print(f"读取配置文件失败: {e}")
        return None


def read_config_file() -> Optional[Dict[str, Any]]:
    """
    读取配置文件
    接口：GET http://baseUrl/api/config
    从 frpc.toml 中读取文件内容
    """
    base_url = get_base_url()
    if not base_url:
        return {"error": "无法获取 baseUrl，请检查 frpc.toml 配置"}
    
    try:
        url = f"{base_url}/api/config"
        # 如果存在认证信息，使用 auth 参数
        auth = get_web_auth()
        response = requests.get(url, auth=auth, timeout=5)
        
        print('读取配置文件：', response.status_code)
        print('用户名 密码：', auth)
        
        if response.status_code == 200:
            return response.json()
        else:
            return {
                "error": f"请求失败，状态码: {response.status_code}",
                "status_code": response.status_code,
                "response": response.text
            }
    except requests.exceptions.ConnectionError:
        return {"error": "连接失败，请确保 frpc 服务正在运行"}
    except requests.exceptions.Timeout:
        return {"error": "请求超时"}
    except Exception as e:
        return {"error": f"请求异常: {str(e)}"}


def reload_config() -> Optional[Dict[str, Any]]:
    """
    重载配置文件
    接口：POST http://baseUrl/api/reload
    使配置生效
    """
    base_url = get_base_url()
    if not base_url:
        return {"error": "无法获取 baseUrl，请检查 frpc.toml 配置"}
    
    try:
        url = f"{base_url}/api/reload"
        # 如果存在认证信息，使用 auth 参数
        auth = get_web_auth()
        response = requests.get(url, auth=auth, timeout=5)
        
        print('重载配置文件：', response.status_code)

        if response.status_code in [200, 201, 204]:
            # 尝试解析 JSON 响应，如果没有响应体则返回成功
            try:
                return response.json()
            except:
                return {"success": True, "status_code": response.status_code, "message": "配置重载成功"}
        else:
            # 尝试解析错误响应（可能是 JSON 格式）
            error_message = f"重载失败，状态码: {response.status_code}"
            try:
                error_json = response.json()
                # 如果响应是 JSON，尝试提取错误信息
                if isinstance(error_json, dict):
                    if "error" in error_json:
                        error_message = error_json["error"]
                    elif "message" in error_json:
                        error_message = error_json["message"]
                    elif "msg" in error_json:
                        error_message = error_json["msg"]
                    else:
                        # 如果 JSON 中有其他字段，也包含进去
                        error_message = f"重载失败: {str(error_json)}"
            except:
                # 如果不是 JSON，使用响应文本
                if response.text:
                    error_message = f"重载失败: {response.text}"
            
            return {
                "error": error_message,
                "status_code": response.status_code,
                "response": response.text
            }
    except requests.exceptions.ConnectionError:
        return {"error": "连接失败，请确保 frpc 服务正在运行"}
    except requests.exceptions.Timeout:
        return {"error": "请求超时"}
    except Exception as e:
        return {"error": f"请求异常: {str(e)}"}


def write_config_file(config_data: str, auto_reload: bool = True) -> Optional[Dict[str, Any]]:
    """
    写入配置文件
    接口：PUT http://baseUrl/api/config
    
    参数:
        config_data: TOML 格式的配置字符串
        示例格式:
        serverAddr = "162.14.77.110"
        serverPort = 7000
        auth.method = "token"
        auth.token = "d4c2dc7262c3d97bcaf3c2d1201282e3"
        webServer.addr = "127.0.0.1"
        webServer.port = 7400
        [[proxies]]
        name = "test-tcp"
        type = "tcp"
        localIP = "192.168.0.107"
        localPort = 6969
        remotePort = 7503
        auto_reload: 是否在写入后自动重载配置（默认 True）
    """
    base_url = get_base_url()
    if not base_url:
        return {"error": "无法获取 baseUrl，请检查 frpc.toml 配置"}
    
    try:
        url = f"{base_url}/api/config"
        # 发送 TOML 格式的字符串，Content-Type 为 text/plain
        headers = {'Content-Type': 'text/plain; charset=utf-8'}
        # 如果存在认证信息，使用 auth 参数
        auth = get_web_auth()
        response = requests.put(url, data=config_data.encode('utf-8'), headers=headers, auth=auth, timeout=5)

        print('写入配置文件：', response.status_code)
        
        if response.status_code in [200, 201, 204]:
            result = {
                "success": True,
                "status_code": response.status_code,
                "message": "配置写入成功"
            }
            
            # 尝试解析 JSON 响应
            try:
                json_response = response.json()
                result.update(json_response)
            except:
                pass
            
            # 如果启用自动重载，则调用重载接口
            if auto_reload:
                reload_result = reload_config()
                if "error" in reload_result:
                    result["reload_error"] = reload_result["error"]
                    result["reload_status_code"] = reload_result.get("status_code")
                    result["reload_response"] = reload_result.get("response", "")
                    # 如果重载失败，将错误信息也包含在主消息中
                    result["message"] = f"配置写入成功，但重载失败: {reload_result['error']}"
                else:
                    result["reload_success"] = True
                    result["message"] = "配置写入并重载成功"
            
            return result
        else:
            return {
                "error": f"请求失败，状态码: {response.status_code}",
                "status_code": response.status_code,
                "response": response.text
            }
    except requests.exceptions.ConnectionError:
        return {"error": "连接失败，请确保 frpc 服务正在运行"}
    except requests.exceptions.Timeout:
        return {"error": "请求超时"}
    except Exception as e:
        return {"error": f"请求异常: {str(e)}"}


def query_config(key: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    查询配置文件
    如果提供 key，则查询特定配置项；否则返回全部配置
    接口：GET http://baseUrl/api/config?key=xxx
    """
    base_url = get_base_url()
    if not base_url:
        return {"error": "无法获取 baseUrl，请检查 frpc.toml 配置"}
    
    try:
        url = f"{base_url}/api/config"
        params = {}
        if key:
            params['key'] = key
        
        # 如果存在认证信息，使用 auth 参数
        auth = get_web_auth()
        response = requests.get(url, params=params, auth=auth, timeout=5)
        print('查询配置文件：', response.status_code)
        if response.status_code == 200:
            return response.json()
        else:
            return {
                "error": f"请求失败，状态码: {response.status_code}",
                "status_code": response.status_code,
                "response": response.text
            }
    except requests.exceptions.ConnectionError:
        return {"error": "连接失败，请确保 frpc 服务正在运行"}
    except requests.exceptions.Timeout:
        return {"error": "请求超时"}
    except Exception as e:
        return {"error": f"请求异常: {str(e)}"}


def get_proxy_status() -> Optional[Dict[str, Any]]:
    """
    查询代理列表和状态
    接口：GET http://baseUrl/api/status
    
    返回格式示例:
    {
        "tcp": [
            {
                "name": "test-tcp",
                "type": "tcp",
                "status": "start error",
                "err": "proxy [test-tcp] already exists",
                "local_addr": "192.168.0.107:6969",
                "plugin": "",
                "remote_addr": ""
            }
        ]
    }
    """
    base_url = get_base_url()
    if not base_url:
        return {"error": "无法获取 baseUrl，请检查 frpc.toml 配置"}
    
    try:
        url = f"{base_url}/api/status"
        # 如果存在认证信息，使用 auth 参数
        auth = get_web_auth()
        response = requests.get(url, auth=auth, timeout=5)

        print('查询代理列表：', response.status_code)
        
        if response.status_code == 200:
            return response.json()
        else:
            return {
                "error": f"请求失败，状态码: {response.status_code}",
                "status_code": response.status_code,
                "response": response.text
            }
    except requests.exceptions.ConnectionError:
        return {"error": "连接失败，请确保 frpc 服务正在运行"}
    except requests.exceptions.Timeout:
        return {"error": "请求超时"}
    except Exception as e:
        return {"error": f"请求异常: {str(e)}"}


def read_frpc_toml_content() -> Optional[str]:
    """
    直接读取本地 frpc.toml 文件内容
    """
    if not os.path.exists('frpc.toml'):
        return None
    
    try:
        with open('frpc.toml', 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        print(f"读取 frpc.toml 文件失败: {e}")
        return None


def check_frpc_service_status() -> Optional[int]:
    """
    通过 API 检测 frpc 服务是否在运行
    
    返回:
        status_code: HTTP 状态码，如果连接成功返回 200，连接失败返回 None
    """
    try:
        base_url = get_base_url()
        if not base_url:
            return None
        
        # 尝试连接 status API，使用较短的超时时间避免阻塞
        url = f"{base_url}/api/status"
        # 如果存在认证信息，使用 auth 参数
        auth = get_web_auth()
        response = requests.get(url, auth=auth, timeout=0.5)
        return response.status_code
    except:
        return None


def generate_toml_config(
    server_addr: str,
    server_port: int,
    auth_token: Optional[str] = None,
    web_addr: str = "127.0.0.1",
    web_port: int = 7400,
    log_level: str = "info",
    proxies: Optional[list] = None
) -> str:
    """
    生成 TOML 格式的配置字符串
    
    参数:
        server_addr: 服务器地址
        server_port: 服务器端口
        auth_token: 认证 token（可选）
        web_addr: Web 服务地址
        web_port: Web 服务端口
        log_level: 日志级别，可选值为 trace, debug, info, warn, error，默认 info
        proxies: 代理配置列表，每个代理为字典格式
            示例: [{"name": "test-tcp", "type": "tcp", "localIP": "192.168.0.107", 
                   "localPort": 6969, "remotePort": 7503}]
    
    返回:
        TOML 格式的配置字符串
    """
    config_lines = [
        f'serverAddr = "{server_addr}"',
        f'serverPort = {server_port}',
        '',
        '# 认证配置',
        'auth.method = "token"'
    ]
    
    if auth_token:
        config_lines.append(f'auth.token = "{auth_token}"')
    else:
        config_lines.append('# auth.token = ""')
    
    config_lines.extend([
        '',
        '# 监控',
        f'webServer.addr = "{web_addr}"',
        f'webServer.port = {web_port}',
        '',
        '# 日志配置',
        'log.to = "frpc.log"',
        f'log.level = "{log_level}"'
    ])
    
    # 添加代理配置
    if proxies:
        for proxy in proxies:
            config_lines.append('')
            config_lines.append('[[proxies]]')
            config_lines.append(f'name = "{proxy.get("name", "")}"')
            config_lines.append(f'type = "{proxy.get("type", "")}"')
            if 'localIP' in proxy:
                config_lines.append(f'localIP = "{proxy["localIP"]}"')
            if 'localPort' in proxy:
                config_lines.append(f'localPort = {proxy["localPort"]}')
            if 'remotePort' in proxy:
                config_lines.append(f'remotePort = {proxy["remotePort"]}')
    
    return '\n'.join(config_lines)
