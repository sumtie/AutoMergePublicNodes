import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import re
import time
import os

# --- 配置区 ---
BASE_URL = "https://freefq.com"
LIST_URL = "https://freefq.com/free-xray/"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Referer": BASE_URL
}


def get_article_url():
    """步骤 1: 从列表页获取最新文章的链接"""
    print(f"[*] 步骤 1: 正在访问列表页 {LIST_URL}")
    try:
        res = requests.get(LIST_URL, headers=HEADERS, timeout=10)
        res.encoding = 'gb2312'
        if res.status_code != 200:
            print(f"[!] 错误: 列表页状态码 {res.status_code}")
            return None

        soup = BeautifulSoup(res.text, 'html.parser')
        tag = soup.find('a', string=lambda t: t and "免费xray账号分享" in t)

        if tag and tag.get('href'):
            full_url = urljoin(BASE_URL, tag['href'])
            print(f"[OK] 找到文章链接: {full_url}")
            return full_url
        print("[!] 错误: 未能在列表页找到关键词链接")
    except Exception as e:
        print(f"[X] 步骤 1 异常: {e}")
    return None


def get_real_node_page(article_url):
    """步骤 2: 从文章详情页提取存放节点的二级 .htm 链接"""
    print(f"[*] 步骤 2: 正在解析详情页 {article_url}")
    try:
        res = requests.get(article_url, headers=HEADERS, timeout=10)
        res.encoding = 'utf-8'

        soup = BeautifulSoup(res.text, 'html.parser')
        text_area = soup.find('td', id='text')
        if not text_area:
            print("[!] 错误: 未找到 <td id='text'> 区域")
            return None

        link_tag = text_area.find('a', href=lambda h: h and h.endswith('.htm'))
        if link_tag:
            node_page_url = urljoin(BASE_URL, link_tag['href'])
            print(f"[OK] 找到真实节点页面: {node_page_url}")
            return node_page_url
        print("[!] 错误: 未在详情页找到二级 .htm 链接")
    except Exception as e:
        print(f"[X] 步骤 2 异常: {e}")
    return None


def extract_nodes_from_source(final_url):
    """步骤 3: 访问最终页面并使用正则抓取所有协议节点"""
    print(f"[*] 步骤 3: 正在从源码提取节点 {final_url}")
    try:
        res = requests.get(final_url, headers=HEADERS, timeout=10)
        res.encoding = 'gb2312'

        pattern = r'(?:vmess|vless|ss|trojan)://[^\s"\'<>]+'
        matches = re.findall(pattern, res.text)

        clean_nodes = []
        for m in matches:
            node = m.split('<')[0].replace('&amp;', '&').strip()
            if node and node not in clean_nodes:
                clean_nodes.append(node)

        if clean_nodes:
            print(f"[OK] 成功提取到 {len(clean_nodes)} 个节点")
            return clean_nodes
        print("[!] 错误: 最终页面未匹配到任何节点")
    except Exception as e:
        print(f"[X] 步骤 3 异常: {e}")
    return []


def main():
    """控制中心：按步骤执行"""
    print("=" * 50)
    print("开始从 freefq.com 获取免费 Xray 节点")
    print("=" * 50)

    # 1. 找文章链接
    article_link = get_article_url()
    if not article_link:
        print("[!] 任务终止：未找到文章链接")
        return

    time.sleep(1)

    # 2. 找真实节点页面
    real_data_page = get_real_node_page(article_link)
    if not real_data_page:
        print("[!] 任务终止：未找到节点页面")
        return

    time.sleep(2)

    # 3. 提取节点
    final_nodes = extract_nodes_from_source(real_data_page)

    # 4. 保存到 v2.txt（当前目录）
    if final_nodes:
        print("\n" + "=" * 20 + " 保存节点到 v2.txt " + "=" * 20)

        with open("v2.txt", "w", encoding="utf-8") as f:
            for node in final_nodes:
                f.write(node + "\n")

        print(f"✅ 成功保存 {len(final_nodes)} 个节点到 v2.txt")
        print(f"   文件路径：{os.path.abspath('v2.txt')}")
    else:
        print("\n[!] 未获取到任何节点，v2.txt 未生成")

    print("\n" + "=" * 50)
    print("任务完成")
    print("=" * 50)


if __name__ == "__main__":
    main()
