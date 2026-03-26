import requests
import yaml
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import re
import time
from v2c import parse_raw_links

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
        # 定位包含特定关键词的第一个链接
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
        # 定位 id="text" 的单元格
        text_area = soup.find('td', id='text')
        if not text_area:
            print("[!] 错误: 未找到 <td id='text'> 区域")
            return None

        # 寻找该区域内以 .htm 结尾的链接
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
        # 根据你提供的源码，这里可能是 gb2312 编码
        res.encoding = 'gb2312'

        # 使用正则表达式匹配 vmess, vless, ss, trojan
        pattern = r'(?:vmess|vless|ss|trojan)://[^\s"\'<>]+'
        matches = re.findall(pattern, res.text)

        # 清洗数据：去掉残留标签、转换 HTML 实体字符、去重
        clean_nodes = []
        for m in matches:
            node = m.split('<')[0].replace('&amp;', '&').strip()
            if node not in clean_nodes:
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
    # 1. 找文章
    article_link = get_article_url()
    if not article_link: return

    time.sleep(1)  # 礼貌间隔

    # 2. 找真实数据页
    real_data_page = get_real_node_page(article_link)
    if not real_data_page: return

    time.sleep(2)

    # 3. 提取节点
    final_nodes = extract_nodes_from_source(real_data_page)

    # 4. 汇总输出
    if final_nodes:
        print("\n" + "=" * 20 + " 抓取结果汇总 " + "=" * 20)
        config = parse_raw_links(final_nodes)
        with open("meta.yaml", "w", encoding="utf-8") as f:
            yaml.dump(config, f, allow_unicode=True, sort_keys=False, default_flow_style=False)
        print("✅ meta.yaml 生成成功！")
        with open("v2.txt", "w", encoding="utf-8") as f:
            for node in final_nodes:
                f.write(node + "\n")
        print(f"[*] 所有节点已保存至当前目录下的 v2.txt")
        print(f"[*] 预览前2个节点:")
        for n in final_nodes[:2]:
            print(f"    {n[:80]}...")
    else:
        print("\n[!] 任务结束，未获取到任何数据。")


if __name__ == "__main__":
    main()
