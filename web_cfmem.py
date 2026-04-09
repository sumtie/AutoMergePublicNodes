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

# 重试配置
MAX_RETRIES = 3
RETRY_BACKOFF = 2  # 指数退避基数（秒）


def fetch_page(url: str, headers: Dict = None, timeout: int = 15) -> Optional[str]:
    """带重试机制的页面获取函数（单一职责：只负责请求）"""
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

    # 更宽松的正则，适配 fs.v2rayse.com / oss.v2rayse.com 等
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


def download_clash_subscription(url: str) -> Optional[str]:
    """单独下载 订阅内容（可选使用）"""
    if not url:
        return None

    print(f"[{datetime.now()}] 正在下载 Clash 订阅: {url}")
    content = fetch_page(url, headers=CLASH_HEADERS, timeout=30)
    if content:
        print(f"[{datetime.now()}] Clash 订阅下载成功，长度: {len(content)} 字符")
    return content


def main():
    print(f"[{datetime.now()}] 开始获取最新节点订阅...")

    # 1. 找到最新文章
    article_url = find_latest_article_url()
    if not article_url:
        print("获取文章链接失败，程序退出")
        return

    time.sleep(1.5)  # 礼貌间隔

    # 2. 提取订阅链接
    links = extract_subscription_links(article_url)

    print(f"\n[{datetime.now()}] 最新订阅链接：")
    for key, url in links.items():
        status = "✅ 获取成功" if url else "❌ 未找到"
        print(f"{key.upper():<8}: {url if url else 'None'}  ({status})")

    # 示例：如果需要下载 Clash 订阅内容，可取消注释
    if links.get("clash"):
        yaml_content = download_clash_subscription(links["clash"])
        if yaml_content:
            with open("clash.yaml", "w", encoding="utf-8") as f:
                f.write(yaml_content)
            print("Clash 订阅已保存为 clash.yaml")

    print(f"[{datetime.now()}] 本次任务完成\n")


if __name__ == "__main__":
    main()
