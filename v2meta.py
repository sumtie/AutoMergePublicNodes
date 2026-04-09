import requests
import base64
import json
import urllib.parse
import yaml
from typing import Dict, List, Optional

# ==================== 常见公开 V2Ray 订阅链接 ====================
SUB_URLS = [
    # "https://raw.githubusercontent.com/Pawdroid/Free-servers/main/sub",  # base64 格式
    # "https://raw.githubusercontent.com/barry-far/V2ray-Config/main/All_Configs_Sub.txt",  # 明文链接
    "https://raw.githubusercontent.com/WLget/V2Ray_configs_64/master/ConfigSub_list.txt",
    # 你可以继续添加更多...
]


# 如果被墙，推荐用镜像（把上面链接改成下面格式）
# 示例：https://hk.gh-proxy.org/https://raw.githubusercontent.com/...

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
}


def decode_sub(content: str) -> List[str]:
    """处理 base64 或明文订阅"""
    content = content.strip()
    try:
        # 尝试 base64 解码
        decoded = base64.b64decode(content + '=' * (-len(content) % 4)).decode('utf-8')
        links = [line.strip() for line in decoded.splitlines() if line.strip() and '://' in line]
        return links
    except:
        # 明文直接按行分割
        return [line.strip() for line in content.splitlines() if line.strip() and '://' in line]


def clean_name(name: str) -> str:
    """清理节点名称"""
    name = urllib.parse.unquote(name)
    name = name.replace(' ', '_').replace('|', '').strip()[:60]
    return name or "Unnamed_Node"


def parse_vmess(link: str) -> Optional[Dict]:
    try:
        b64 = link[8:].split('#')[0]
        b64 += '=' * (-len(b64) % 4)
        data = json.loads(base64.urlsafe_b64decode(b64).decode('utf-8'))
        name = clean_name(data.get('ps', data.get('add', 'VMess')))

        proxy = {
            'name': name,
            'type': 'vmess',
            'server': data['add'],
            'port': int(data['port']),
            'uuid': data['id'],
            'alterId': int(data.get('aid', 0)),
            'cipher': data.get('scy', 'auto'),
            'tls': data.get('tls', '') in ['tls', '1'],
            'skip-cert-verify': True,
            'servername': data.get('sni', data.get('host', data.get('add', ''))),
            'network': data.get('net', 'tcp'),
        }
        if proxy['network'] == 'ws':
            proxy['ws-opts'] = {
                'path': data.get('path', '/'),
                'headers': {'Host': data.get('host', '')} if data.get('host') else {}
            }
        return proxy
    except:
        return None


def parse_ss(link: str) -> Optional[Dict]:
    try:
        if '#' in link:
            link, raw_name = link.split('#', 1)
            name = clean_name(raw_name)
        else:
            name = "SS"

        if '@' in link[5:]:
            # ss://method:pass@server:port
            part = link[5:]
            method_pass, server_port = part.split('@')
            method, password = method_pass.split(':', 1)
            server, port = server_port.split(':', 1)
        else:
            # base64 格式
            b64 = link[5:].split('#')[0]
            b64 += '=' * (-len(b64) % 4)
            decoded = base64.urlsafe_b64decode(b64).decode()
            method, password, server_port = decoded.rsplit(':', 2)
            server, port = server_port.split('@') if '@' in server_port else (server_port, '443')

        return {
            'name': name,
            'type': 'ss',
            'server': server,
            'port': int(port),
            'cipher': method,
            'password': password,
            'skip-cert-verify': True,
        }
    except:
        return None


def parse_trojan(link: str) -> Optional[Dict]:
    try:
        if '#' in link:
            link, raw_name = link.split('#', 1)
            name = clean_name(raw_name)
        else:
            name = "Trojan"

        parsed = urllib.parse.urlparse(link)
        password = parsed.username or parsed.password
        server = parsed.hostname
        port = parsed.port or 443
        query = urllib.parse.parse_qs(parsed.query)

        return {
            'name': name,
            'type': 'trojan',
            'server': server,
            'port': int(port),
            'password': password,
            'skip-cert-verify': True,
            'sni': query.get('sni', [server])[0],
            'network': query.get('type', ['tcp'])[0],
        }
    except:
        return None


# ==================== 新增：hysteria2 解析 ====================
def parse_hysteria2(link: str) -> Optional[Dict]:
    try:
        if '#' in link:
            link, raw_name = link.split('#', 1)
            name = clean_name(raw_name)
        else:
            name = "Hysteria2"

        parsed = urllib.parse.urlparse(link)
        if parsed.scheme not in ('hysteria2', 'hy2'):
            return None

        password = parsed.username or ''
        server = parsed.hostname
        port = parsed.port or 443
        query = urllib.parse.parse_qs(parsed.query)

        proxy = {
            'name': name,
            'type': 'hysteria2',
            'server': server,
            'port': int(port),
            'password': password,
            'sni': query.get('sni', [server])[0],
            'skip-cert-verify': 'true' in query.get('insecure', ['false'])[0].lower(),
            'up': query.get('up', [''])[0] or query.get('upload', [''])[0],
            'down': query.get('down', [''])[0] or query.get('download', [''])[0],
            'obfs': query.get('obfs', [''])[0],
            'obfs-password': query.get('obfs-password', [''])[0],
            'alpn': query.get('alpn', []),
            # 'fingerprint': query.get('fp', [''])[0] or query.get('fingerprint', [''])[0],
            'client-fingerprint': query.get('fp', [''])[0] or query.get('fingerprint', [''])[0],
        }

        # ports / hop-interval 如果有（较少见）
        if 'ports' in query:
            proxy['ports'] = query['ports'][0]
        if 'hop-interval' in query:
            proxy['hop-interval'] = int(query['hop-interval'][0])

        # 清理空值
        for k in list(proxy):
            if proxy[k] in ('', None, []):
                del proxy[k]

        return proxy
    except:
        return None


# ==================== 新增：tuic 解析 ====================
def parse_tuic(link: str) -> Optional[Dict]:
    try:
        if '#' in link:
            link, raw_name = link.split('#', 1)
            name = clean_name(raw_name)
        else:
            name = "TUIC"

        parsed = urllib.parse.urlparse(link)
        if parsed.scheme != 'tuic':
            return None

        query = urllib.parse.parse_qs(parsed.query)

        # TUIC v5: uuid:password@host:port
        # TUIC v4: token@host:port
        auth = parsed.username or ''
        if ':' in auth:
            uuid, password = auth.split(':', 1)
            token = None
        else:
            token = auth
            uuid = None
            password = None

        server = parsed.hostname
        port = parsed.port or 443

        proxy = {
            'name': name,
            'type': 'tuic',
            'server': server,
            'port': int(port),
            'udp-relay-mode': query.get('udp_relay_mode', ['native'])[0],
            'congestion-controller': query.get('congestion_control', ['cubic'])[0],
            'disable-sni': 'true' in query.get('disable_sni', ['false'])[0].lower(),
            'reduce-rtt': 'true' in query.get('reduce_rtt', ['false'])[0].lower(),
            'skip-cert-verify': 'true' in query.get('allow_insecure', ['false'])[0].lower(),
            'sni': query.get('sni', [server])[0],
            'alpn': query.get('alpn', []),
        }

        if token:
            proxy['token'] = token
        if uuid:
            proxy['uuid'] = uuid
        if password:
            proxy['password'] = password

        # 其他可选
        if 'heartbeat' in query:
            proxy['heartbeat-interval'] = int(query['heartbeat'][0])
        if 'max_udp' in query:
            proxy['max-udp-relay-packet-size'] = int(query['max_udp'][0])

        for k in list(proxy):
            if proxy[k] in ('', None, []):
                del proxy[k]

        return proxy
    except:
        return None


# ==================== 增强原有 parse_vless，支持 reality ====================
def parse_vless(link: str) -> Optional[Dict]:
    try:
        if '#' in link:
            link, raw_name = link.split('#', 1)
            name = clean_name(raw_name)
        else:
            name = "VLESS"

        parsed = urllib.parse.urlparse(link)
        uuid = parsed.username
        server = parsed.hostname
        port = parsed.port or 443
        query = urllib.parse.parse_qs(parsed.query)

        proxy = {
            'name': name,
            'type': 'vless',
            'server': server,
            'port': int(port),
            'uuid': uuid,
            'tls': query.get('security', ['none'])[0] in ['tls', 'reality'],
            'servername': query.get('sni', [server])[0] or query.get('peer', [server])[0],
            'flow': query.get('flow', [''])[0],
            'network': query.get('type', ['tcp'])[0],
            'udp': True,
            'packet-encoding': query.get('packet-encoding', [''])[0] or 'xudp',
            'skip-cert-verify': 'true' in query.get('allowInsecure', ['false'])[0].lower() or 'true' in
                                query.get('insecure', ['false'])[0].lower(),
            # 'fingerprint': ...   ← 删除或注释掉这行（不再需要）
            'alpn': query.get('alpn', []),
        }

        # Reality 支持
        if query.get('security', [''])[0] == 'reality':
            proxy['reality-opts'] = {
                'public-key': query.get('pbk', [''])[0],
                'short-id': query.get('sid', [''])[0],
            }
            # fp 参数优先作为 client-fingerprint（最重要修改）
            fp = query.get('fp', [''])[0] or query.get('fingerprint', [''])[0]
            if fp:
                proxy['client-fingerprint'] = fp

        # ws / grpc 传输层
        if proxy['network'] == 'ws':
            proxy['ws-opts'] = {
                'path': query.get('path', ['/'])[0],
                'headers': {'Host': query.get('host', [proxy['servername']])[0]}
            }
        elif proxy['network'] == 'grpc':
            proxy['grpc-opts'] = {
                'grpc-service-name': query.get('serviceName', [''])[0]
            }
        # ==================== 新增：过滤不支持的 xtls flow ====================
        flow = proxy.get('flow', '')
        if flow and flow not in ['xtls-rprx-vision', '']:
            print(f"⚠️ 跳过不支持的 flow: {flow} → {name}")
            return None  # 直接丢弃这个节点

        # 清理空值（可选，但推荐保留）
        for k in list(proxy.keys()):
            if proxy[k] in ('', None, [], {}):
                del proxy[k]

        return proxy
    except:
        return None


def fetch_subscription_links(sub_urls: List[str]) -> List[str]:
    """从订阅链接抓取所有原始节点链接"""
    all_links: List[str] = []
    for url in sub_urls:
        try:
            print(f"正在抓取: {url}")
            resp = requests.get(url, headers=HEADERS, timeout=15)
            resp.raise_for_status()
            links = decode_sub(resp.text)
            all_links.extend(links)
            print(f"✓ 获取到 {len(links)} 条链接")
        except Exception as e:
            print(f"抓取失败 {url}: {e}")
    return all_links


def parse_single_link(link: str) -> Optional[Dict]:
    """根据协议类型解析单个链接为 proxy 配置"""
    if link.startswith('vmess://'):
        return parse_vmess(link)
    elif link.startswith('ss://'):
        return parse_ss(link)
    elif link.startswith('trojan://'):
        return parse_trojan(link)
    elif link.startswith(('vless://', 'vless+')):
        return parse_vless(link)
    elif link.startswith(('hysteria2://', 'hy2://')):
        return parse_hysteria2(link)
    elif link.startswith('tuic://'):
        return parse_tuic(link)
    return None


def filter_and_deduplicate_proxies(proxies: List[Dict]) -> List[Dict]:
    """按名称去重：名称相同则添加 _1、_2、_3 ... 后缀"""
    from collections import defaultdict

    name_counter = defaultdict(int)      # 统计每个名称出现的次数
    final_proxies: List[Dict] = []

    for proxy in proxies:
        if not proxy or not proxy.get('server') or not proxy.get('port'):
            continue

        original_name = proxy['name']
        name_counter[original_name] += 1
        count = name_counter[original_name]

        # 如果是第一次出现，直接使用原名；否则添加 _数字
        if count > 1:
            proxy['name'] = f"{original_name}_{count}"

        final_proxies.append(proxy)

    return final_proxies


def build_clash_config(proxies: List[Dict]) -> Dict:
    """生成 配置（简洁版）"""
    proxy_names = [p["name"] for p in proxies]

    return {
        "port": 7890,
        "socks-port": 7891,
        "mode": "rule",
        "log-level": "info",
        "proxies": proxies,
        "proxy-groups": [
            {
                "name": "节点选择",
                "type": "select",
                "proxies": [
                    "自动选择",
                    "手动选择"
                ]
            },
            {
                "name": "自动选择",
                "type": "url-test",
                "url": "http://www.gstatic.com/generate_204",
                "interval": 360,
                "tolerance": 60,
                "proxies": proxy_names
            },
            {
                "name": "手动选择",
                "type": "select",
                "proxies": proxy_names
            }
        ],
        "rules": [
            "GEOIP,CN,DIRECT",
            "MATCH,节点选择"
        ]
    }


def parse_raw_links(raw_links):
    if not raw_links:
        print("未获取到任何节点链接，程序退出。")
        return

    # 解析所有链接
    print(f"\n开始解析 {len(raw_links)} 条节点链接...")
    parsed_proxies: List[Dict] = []
    for link in raw_links:
        proxy = parse_single_link(link)
        if proxy:
            parsed_proxies.append(proxy)

    # 处理名称重复（相同名称加 _数字）
    final_proxies = filter_and_deduplicate_proxies(parsed_proxies)
    print(f"处理完成，共得到 {len(final_proxies)} 个节点（已处理重名）\n")

    if not final_proxies:
        print("没有有效节点可生成配置！")
        return

    # 生成配置
    config = build_clash_config(final_proxies)
    return config


def main():
    """主流程控制"""
    print("=== 配置生成工具启动 ===\n")
    # 抓取订阅
    raw_links = fetch_subscription_links(SUB_URLS)
    config = parse_raw_links(raw_links)
    with open("meta2.yaml", "w", encoding="utf-8") as f:
        yaml.dump(config, f, allow_unicode=True, sort_keys=False, default_flow_style=False)
    print("✅ meta2.yaml 生成成功！")


if __name__ == "__main__":
    main()
