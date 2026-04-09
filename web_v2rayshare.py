import time
import requests
from bs4 import BeautifulSoup
import urllib3
import re

# 初始化配置
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE_URL = "https://v2rayshare.net/"
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36'
}


def get_soup(url):
    """职责：获取网页内容并返回 BeautifulSoup 对象"""
    try:
        response = requests.get(url, headers=HEADERS, timeout=10, verify=False)
        response.raise_for_status()
        return BeautifulSoup(response.text, 'html.parser')
    except Exception as e:
        print(f"[错误] 请求 {url} 失败: {e}")
        return None


def fetch_latest_article_info(home_url):
    """职责：从主页解析出最新一篇文章的链接和标题"""
    soup = get_soup(home_url)
    if not soup:
        return None

    blog_post_div = soup.find('div', class_='blog-post col-lg-8 fadein-bottom')
    if blog_post_div:
        article = blog_post_div.find('article')
        if article:
            a_tag = article.find('a')
            if a_tag:
                return {
                    'url': a_tag.get('href'),
                    'title': a_tag.get('title')
                }
    return None


def extract_raw_content_list(article_url):
    """职责：在文章详情页中，提取指定范围内的原始文本信息"""
    soup = get_soup(article_url)
    if not soup:
        return []

    content_list = []
    # 找到起始点：包含“订阅链接”的标题
    start_node = soup.find(['h2', 'p'], string=re.compile("订阅链接"))

    if start_node:
        for sibling in start_node.find_next_siblings():
            # 停止点：遇到“温馨提示”
            if sibling.name == 'p' and "温馨提示" in sibling.get_text():
                break

            text = sibling.get_text(strip=True)
            if text:
                content_list.append(text)

    return content_list


def process_subscription_data(raw_list):
    """职责：清洗原始文本，从中过滤出纯净的 URL 链接"""
    urls = []
    for item in raw_list:
        # 使用正则提取出 https 开头的链接
        found = re.findall(r'https?://[^\s,]+', item)
        urls.extend(found)
    return list(set(urls))  # 去重


def main():
    """职责：流程调度（Orchestrator）"""
    print(f"[*] 正在检查主页: {BASE_URL}")
    article_info = fetch_latest_article_info(BASE_URL)

    if not article_info:
        print("[!] 未能获取文章信息，程序退出。")
        return

    print(f"[*] 发现最新文章: {article_info['title']}")
    print(f"[*] 正在跳转详情页...")

    # 稍微延迟保护服务器
    time.sleep(1)

    raw_content = extract_raw_content_list(article_info['url'])
    if not raw_content:
        print("[!] 详情页内容提取为空。")
        return

    # 获取清洗后的 URL 列表
    final_urls = process_subscription_data(raw_content)

    print("\n--- 提取结果 ---")
    for url in final_urls:
        print(url)

    # 这里以后可以衔接你之前写的 SubConverter 转换逻辑
    # converter.convert(final_urls) ...


if __name__ == "__main__":
    main()
