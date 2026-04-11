import base64
import time
import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime
from typing import Dict, Optional

# ==================== 配置 ====================
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                  '(KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9',
}

CLASH_HEADERS = {
    'User-Agent': 'clash-verge/v2.4.0'
}

V2RAY_HEADERS = {
    'User-Agent': 'v2ray'
}

# 重试配置
MAX_RETRIES = 3
RETRY_BACKOFF = 2  # 指数退避基数（秒）


def fetch_page(url: str, headers: Dict = None, timeout: int = 15) -> Optional[str]:
    """带重试机制的页面获取函数"""
    if headers is None:
        headers = HEADERS

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.get(url, headers=headers, timeout=timeout)
            resp.raise_for_status()
            return resp.text
        except requests.RequestException as e:
            print(f"[{datetime.now()}] 请求失败 ({attempt}/{MAX_RETRIES}): {url} | 错误: {e}")
            if attempt == MAX_RETRIES:
                print(f"[{datetime.now()}] 已达到最大重试次数，放弃请求: {url}")
                return None
            sleep_time = RETRY_BACKOFF ** attempt
            time.sleep(sleep_time)
    return None


def find_latest_article_url() -> Optional[str]:
    """从 cfmem.com 首页提取最新「免费节点更新」文章链接"""
    html = fetch_page("https://www.cfmem.com/")
    if not html:
        return None

    soup = BeautifulSoup(html, 'html.parser')

    for a in soup.find_all('a', href=True):
        title = a.get_text().strip()
        if ("免费节点更新" in title and
                ("V2Ray" in title or "Clash" in title or "SingBox" in title)):
            latest_url = a['href']
            if not latest_url.startswith('http'):
                latest_url = "https://www.cfmem.com" + latest_url
            print(f"[{datetime.now()}] 找到最新文章: {title}")
            print(f"文章链接: {latest_url}")
            return latest_url

    print(f"[{datetime.now()}] 未在首页找到免费节点更新文章")
    return None


def extract_subscription_links(article_url: str) -> Dict[str, Optional[str]]:
    """从文章页面提取订阅链接"""
    html = fetch_page(article_url, timeout=30)
    if not html:
        return {"v2ray": None, "clash": None, "mihomo": None, "singbox": None}

    soup = BeautifulSoup(html, 'html.parser')
    text = soup.get_text()

    links: Dict[str, Optional[str]] = {
        "v2ray": None,
        "clash": None,
        "mihomo": None,
        "singbox": None
    }

    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue

        # V2Ray (.txt)
        if match := re.search(r'https?://[^\s]+?\.txt', line):
            if "v2ray" in line.lower() or not links["v2ray"]:
                links["v2ray"] = match.group(0)

        # Clash / Mihomo (.yaml)
        if match := re.search(r'https?://[^\s]+?\.yaml', line):
            url = match.group(0)
            if "mihomo" in line.lower():
                links["mihomo"] = url
            else:
                links["clash"] = url

        # SingBox (.json)
        if match := re.search(r'https?://[^\s]+?\.json', line):
            if "singbox" in line.lower() or not links["singbox"]:
                links["singbox"] = match.group(0)

    return links


def download_subscription(url: str, headers: Dict = None) -> Optional[str]:
    """通用下载订阅内容函数"""
    if not url:
        return None

    print(f"[{datetime.now()}] 正在下载: {url}")
    content = fetch_page(url, headers=headers, timeout=30)
    if content:
        print(f"[{datetime.now()}] 下载成功，长度: {len(content)} 字符")
    return content


def decode_base64(encoded_string):
    """对Base64编码的字符串进行解码"""
    # 将字符串转换为字节
    encoded_bytes = encoded_string.encode('utf-8')
    # 解码Base64字节
    decoded_bytes = base64.b64decode(encoded_bytes)
    # 将解码后的字节转换为字符串
    decoded_string = decoded_bytes.decode('utf-8')
    return decoded_string


def main():
    print(f"[{datetime.now()}] 开始获取 cfmem.com 最新节点订阅...")

    # 1. 找到最新文章
    article_url = find_latest_article_url()
    if not article_url:
        print("获取文章链接失败，程序退出")
        return

    time.sleep(1.5)

    # 2. 提取订阅链接
    links = extract_subscription_links(article_url)

    print(f"\n[{datetime.now()}] 最新订阅链接：")
    for key, url in links.items():
        status = "✅ 获取成功" if url else "❌ 未找到"
        print(f"{key.upper():<8}: {url if url else 'None'}  ({status})")

    # ==================== 保存 V2Ray 订阅 ====================
    if links.get("v2ray"):
        v2_content = download_subscription(links["v2ray"], headers=V2RAY_HEADERS)
        if v2_content:
            v2_content = decode_base64(v2_content)
            with open("v2.txt", "w", encoding="utf-8") as f:
                f.write(v2_content)
            print(f"✅ v2.txt 已保存到当前目录")
        else:
            print("❌ 下载 V2Ray 订阅内容失败")
    else:
        print("❌ 未找到 V2Ray 订阅链接")

    # ==================== 保存 Clash 订阅 ====================
    if links.get("clash"):
        yaml_content = download_subscription(links["clash"], headers=CLASH_HEADERS)
        if yaml_content:
            with open("meta.yaml", "w", encoding="utf-8") as f:
                f.write(yaml_content)
            print(f"✅ meta.yaml 已保存到当前目录")
        else:
            print("❌ 下载 Clash 订阅内容失败")
    else:
        print("❌ 未找到 Clash 订阅链接")

    print(f"\n[{datetime.now()}] 本次任务完成\n")


if __name__ == "__main__":
    main()
