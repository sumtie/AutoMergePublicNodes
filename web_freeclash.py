import requests
from bs4 import BeautifulSoup
import yaml
import re
from urllib.parse import urljoin

# ==================== 配置 ====================
MAIN_URL = "https://www.freeclashnode.com/free-node/"
HEADERS = {
    'user-agent': 'Clash Verge Rev',
}
OUTPUT_FILE = "meta.yaml"


# ==================== 步骤1: 获取最新2篇文章链接 ====================
def get_latest_two_articles():
    resp = requests.get(MAIN_URL, headers=HEADERS, timeout=10)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    articles = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        title = a.get_text(strip=True)
        # 匹配文章链接（以 .htm 结尾且包含日期）
        if "/free-node/" in href and href.endswith(".htm"):
            # 提取日期（格式如 "3月19日"）
            date_match = re.search(r"(\d+月\d+日)", title)
            if date_match:
                date_str = date_match.group(1)
                full_url = urljoin(MAIN_URL, href)
                articles.append({
                    "title": title,
                    "date": date_str,
                    "url": full_url
                })

    # 去重 + 按日期倒序排序（最新在前）
    articles = list({art["url"]: art for art in articles}.values())
    articles.sort(key=lambda x: (int(re.search(r"(\d+)月", x["date"]).group(1)),
                                 int(re.search(r"月(\d+)日", x["date"]).group(1))), reverse=True)

    """
    列表切片小知识：
    列表[:n] → 取前 n 个元素
    列表[2:] → 从第 3 个开始取到最后
    列表[1:4] → 取第 2 个到第 4 个元素（左闭右开）
    """
    latest_two = articles[:2]
    print(f"✅ 找到最新2篇文章：")
    for art in latest_two:
        print(f"   • {art['date']} - {art['title']}")
        print(f"     {art['url']}")
    return [art["url"] for art in latest_two]


# ==================== 提取正确的 Clash YAML 链接（关键修复） ====================
def extract_yaml_urls(article_url):
    resp = requests.get(article_url, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    yaml_urls = []

    # 方法1：查找所有以 .yaml 结尾的纯文本链接
    for text in soup.stripped_strings:
        if re.search(r"https?://node\.freeclashnode\.com/uploads/\d{4}/\d{2}/[^\"'\s]+\.yaml", text):
            match = re.search(r"(https?://node\.freeclashnode\.com/uploads/\d{4}/\d{2}/[^\"'\s]+\.yaml)", text)
            if match:
                yaml_urls.append(match.group(1))

    # 方法2：如果有 <a> 标签也抓（保险）
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if re.search(r"\.yaml$", href) and "node.freeclashnode.com" in href:
            yaml_urls.append(href if href.startswith("http") else urljoin(article_url, href))

    # 去重并保持顺序
    yaml_urls = list(dict.fromkeys(yaml_urls))

    print(f"   📥 从文章提取到 {len(yaml_urls)} 个有效Clash YAML链接")
    for url in yaml_urls:
        print(f"      {url}")
    return yaml_urls


# ==================== 下载 YAML ====================
def fetch_config(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        r.raise_for_status()
        # 1. 获取原始YAML文本
        yaml_text = r.text  # 你的原始YAML文本
        # 2. 预处理：把!<str>替换成普通字符串（或给值加引号）
        # 方式A：直接替换!str标签为普通字符（推荐，不改变值的语义）
        yaml_text = yaml_text.replace('!<str>', '\\!<str>')  # 转义!，让解析器识别为普通字符
        cfg = yaml.safe_load(yaml_text)
        proxies = cfg.get("proxies", []) if isinstance(cfg, dict) else []
        print(f"      ✅ {len(proxies)} 节点 - {url.split('/')[-1]}")
        return proxies
    except Exception as e:
        print(f"      ❌ 下载失败 {url} -> {e}")
        return []


def build_proxy_groups(proxies):
    """最终极简实用版：结构清晰、无多余选项"""
    if not proxies:
        return []

    all_names = [p["name"] for p in proxies]

    groups = [
        {
            "name": "🚀 节点选择",           # 主入口（最推荐设为默认）
            "type": "select",
            "proxies": [
                "自动选择",
                "手动选择",
            ]
        },
        {
            "name": "手动选择",             # 全部节点在这里手动挑选
            "type": "select",
            "proxies": all_names
        },
        {
            "name": "自动选择",
            "type": "url-test",
            "proxies": all_names,
            "url": "http://www.gstatic.com/generate_204",
            "interval": 360
        },
    ]

    return groups


# ==================== 节点去重 + 同名自动加序号 ====================
def deduplicate_proxies(all_proxies):
    """节点去重 + 同名处理
    - 严格去重：相同 server:port:type 的节点只保留一个
    - 同名处理：相同名字的节点自动加 (2)、(3)...
    """
    seen = {}          # 用于严格去重 (server:port:type)
    name_counter = {}  # 用于同名加序号
    unique_proxies = []

    for p in all_proxies:
        if not isinstance(p, dict):
            continue

        # 严格去重 key
        key = f"{p.get('server')}:{p.get('port')}:{p.get('type', '')}"

        if key in seen:
            continue  # 真正重复的节点直接丢弃

        seen[key] = True

        # 同名处理
        base_name = p.get("name", "").strip()
        if not base_name:
            base_name = "Unnamed"

        if base_name not in name_counter:
            name_counter[base_name] = 1
            new_name = base_name
        else:
            name_counter[base_name] += 1
            new_name = f"{base_name} ({name_counter[base_name]})"

        p["name"] = new_name
        unique_proxies.append(p)

    print(f"\n🔄 去重后总节点数: {len(unique_proxies)}（已处理同名节点）")
    return unique_proxies


# ==================== 构建完整 Clash 配置 ====================
def build_full_config(unique_proxies):
    """构建最终的配置文件字典"""
    config = {
        "port": 7890,
        "socks-port": 7891,
        "mode": "rule",
        "log-level": "info",
        "proxies": unique_proxies,
        "proxy-groups": build_proxy_groups(unique_proxies),
        "rules": [  # 基础规则（可后续自行替换）
            "GEOIP,CN,DIRECT",
            "MATCH,🚀 节点选择"     # 所有国外流量默认走主入口
        ]
    }
    return config


# ==================== 保存配置文件 ====================
def save_config(config, filename="meta.yaml"):
    """将配置保存为 YAML 文件"""
    with open(filename, "w", encoding="utf-8") as f:
        yaml.dump(config, f, allow_unicode=True, sort_keys=False, default_flow_style=False)

    print(f"\n🎉 完整配置文件生成成功！→ {filename}")
    print("   建议在客户端把「🚀 节点选择」设为默认策略组")


# ==================== 主流程 ====================
def main():
    print("🚀 开始获取最新 Clash 配置并生成完整文件...\n")

    # 步骤1: 获取最新2篇文章链接
    article_urls = get_latest_two_articles()

    # 步骤2: 下载并收集所有节点
    all_proxies = []
    for url in article_urls:
        yaml_urls = extract_yaml_urls(url)
        for yurl in yaml_urls:
            proxies = fetch_config(yurl)
            all_proxies.extend(proxies)

    # 步骤3: 节点去重 + 同名处理
    unique_proxies = deduplicate_proxies(all_proxies)

    # 步骤4: 构建完整配置
    config = build_full_config(unique_proxies)

    # 步骤5: 保存文件
    save_config(config, OUTPUT_FILE)


if __name__ == "__main__":
    main()
