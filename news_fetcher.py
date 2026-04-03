#!/usr/bin/env python3
"""
新闻抓取模块
负责从各种来源抓取新闻文章（RSS、ArXiv、HTML、HackerNews）
"""

import os
import re
import json
import requests
import hashlib
from datetime import datetime, timedelta
import time
from bs4 import BeautifulSoup
import feedparser
from urllib.parse import urljoin, urlparse
from collections import Counter
import random

# 尝试导入 fake_useragent（可选）
try:
    from fake_useragent import UserAgent
    UA_AVAILABLE = True
    ua = UserAgent()
except ImportError:
    UA_AVAILABLE = False
    ua = None

# 条件导入异步库
try:
    import asyncio
    import aiohttp
    ASYNC_AVAILABLE = True
except ImportError:
    ASYNC_AVAILABLE = False
    asyncio = None
    aiohttp = None


class NewsFetcher:
    """新闻抓取器 - 负责从各种来源抓取新闻"""
    
    def __init__(self, baidu_translate_func=None):
        """
        初始化新闻抓取器
        
        Args:
            baidu_translate_func: 可选的百度翻译函数，用于翻译英文内容
        """
        self.forty_eight_hours_ago = datetime.now() - timedelta(hours=48)
        self.baidu_translate = baidu_translate_func or self._default_translate
        
        # 请求频率控制
        self.domain_delays = {}
        self.min_delay_between_requests = 2
        self.max_concurrent_requests = 3
        
        # 摘要缓存
        self.abstract_cache = {}
    
    def _default_translate(self, title, summary):
        """默认翻译函数（不翻译）"""
        return {'title': title, 'summary': summary}
    
    def _get_headers(self, url=None):
        """生成随机请求头"""
        if UA_AVAILABLE and ua:
            user_agent = ua.random
        else:
            user_agents = [
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            ]
            user_agent = random.choice(user_agents)
        
        headers = {
            'User-Agent': user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0',
        }
        
        if url:
            if 'thepaper' in url:
                headers['Referer'] = 'https://www.thepaper.cn/'
            elif 'hupu' in url:
                headers['Referer'] = 'https://www.hupu.com/'
            elif 'techcrunch' in url:
                headers['Referer'] = 'https://techcrunch.com/'
        
        return headers
    
    def _extract_domain(self, url):
        """从URL提取域名用于频率控制"""
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            if domain.startswith('www.'):
                domain = domain[4:]
            return domain
        except:
            return 'unknown'
    
    def _wait_if_needed(self, url):
        """根据频率控制策略等待适当时间"""
        domain = self._extract_domain(url)
        current_time = time.time()
        
        if domain in self.domain_delays:
            elapsed = current_time - self.domain_delays[domain]
            if elapsed < self.min_delay_between_requests:
                wait_time = self.min_delay_between_requests - elapsed
                print(f"  ⏳ 频率控制: 等待 {wait_time:.1f} 秒后再请求 {domain}")
                time.sleep(wait_time)
        
        self.domain_delays[domain] = time.time()
    
    def _is_ai_related(self, title, summary=''):
        """检查内容是否与AI相关"""
        content = f"{title} {summary}".lower()
        ai_keywords = [
            'ai', 'artificial intelligence', 'machine learning', 
            'deep learning', 'neural network', 'llm', 'gpt', 'transformer',
            '人工智能', '机器学习', '深度学习', '大模型', '生成式AI', 
            '计算机视觉', '图像生成', '训练', 'AIGC', 'Diffusion模型', 
            'MoE模型', 'RLHF'
        ]
        return any(keyword in content for keyword in ai_keywords)
    
    def fetch_arxiv(self, source):
        """抓取Arxiv AI论文（带重试机制）"""
        max_retries = 3
        base_delay = 3
        articles = []
        
        for attempt in range(max_retries):
            try:
                response = requests.get(
                    source['url'], 
                    headers=self._get_headers(source['url']), 
                    timeout=20
                )
                
                if response.status_code != 200:
                    print(f"  ⚠️  {source['name']} HTTP {response.status_code}")
                    if attempt < max_retries - 1:
                        delay = base_delay * (attempt + 1)
                        print(f"     等待 {delay} 秒后重试第 {attempt + 2} 次...")
                        time.sleep(delay)
                        continue
                    return articles
                
                response.encoding = 'utf-8'
                
                try:
                    soup = BeautifulSoup(response.text, 'lxml')
                except:
                    soup = BeautifulSoup(response.text, 'html.parser')
                
                dt_list = soup.find_all('dt')
                dd_list = soup.find_all('dd')
                
                if not dt_list:
                    print(f"  ⚠️  {source['name']} 未找到 <dt> 元素")
                    return articles
                
                for dt, dd in zip(dt_list[:10], dd_list[:10]):
                    paper_id = None
                    link_elem = dt.find('a')
                    if link_elem and 'href' in link_elem:
                        href = link_elem['href']
                        if '/abs/' in href:
                            paper_id = href.split('/abs/')[-1].strip('/')
                        elif '/html/' in href:
                            paper_id = href.split('/html/')[-1].split('/')[0]
                    
                    if not paper_id:
                        continue
                    
                    title_elem = dd.find('div', class_='list-title')
                    authors_elem = dd.find('div', class_='list-authors')
                    abstract_elem = dd.find('p', class_='abstract') or dd.find('p')
                    
                    if title_elem:
                        title = title_elem.get_text().replace('Title:', '').strip()
                        authors = authors_elem.get_text().replace('Authors:', '').strip() if authors_elem else ''
                        abstract = abstract_elem.get_text().strip() if abstract_elem else ''
                        
                        article = {
                            'id': f"arxiv_{paper_id}",
                            'title': f"[论文] {title[:120]}",
                            'link': f'https://arxiv.org/abs/{paper_id}',
                            'source': source['name'],
                            'summary': abstract[:250] + '...' if len(abstract) > 250 else abstract,
                            'authors': authors,
                            'category': 'research',
                            'importance': 9,
                            'time': datetime.now().strftime('%Y-%m-%d %H:%M'),
                            'type': 'ai',
                            'lang': 'en'
                        }
                        translated = self.baidu_translate(article['title'], article['summary'])
                        article['title_translated'] = translated['title']
                        article['summary_translated'] = translated['summary']
                        articles.append(article)
                
                print(f"  ✓ {source['name']} 抓取完成 ({len(articles)}篇)")
                return articles
                
            except requests.exceptions.Timeout:
                print(f"  ⚠️  {source['name']} 请求超时")
                if attempt < max_retries - 1:
                    delay = base_delay * (attempt + 1)
                    time.sleep(delay)
            except requests.exceptions.ConnectionError as e:
                print(f"  ⚠️  {source['name']} 连接错误: {e}")
                if attempt < max_retries - 1:
                    delay = base_delay * (attempt + 1)
                    time.sleep(delay)
            except Exception as e:
                print(f"  ⚠️  {source['name']} 抓取失败: {e}")
                return articles
        
        return articles
    
    def fetch_rss(self, source, article_type='ai'):
        """通用RSS抓取方法（同步版本）"""
        max_retries = 3
        base_delay = 2
        articles = []
        
        self._wait_if_needed(source['url'])
        
        for attempt in range(max_retries):
            try:
                session = requests.Session()
                response = session.get(
                    source['url'], 
                    headers=self._get_headers(source['url']), 
                    timeout=25
                )
                
                if response.status_code == 404:
                    print(f"  ⚠️  {source['name']} 页面不存在 (404)")
                    return articles
                elif response.status_code == 403:
                    print(f"  ⚠️  {source['name']} 访问被拒绝 (403)")
                    if attempt < max_retries - 1:
                        delay = base_delay * (2 ** attempt) + random.uniform(0, 3)
                        time.sleep(delay)
                        continue
                    return articles
                elif response.status_code != 200:
                    print(f"  ⚠️  {source['name']} HTTP {response.status_code}")
                    if attempt < max_retries - 1:
                        delay = base_delay * (attempt + 1) + random.uniform(0, 1)
                        time.sleep(delay)
                        continue
                    return articles
                
                # 设置正确的编码
                if response.apparent_encoding:
                    apparent = response.apparent_encoding.lower()
                    if 'gb' in apparent or 'gbk' in apparent or 'gb2312' in apparent:
                        response.encoding = 'gbk'
                    else:
                        response.encoding = 'utf-8'
                elif 'zh' in source.get('lang', ''):
                    response.encoding = 'utf-8'
                
                feed = feedparser.parse(response.text)
                
                if not feed.entries:
                    print(f"  ⚠️  {source['name']} 返回空内容")
                    return articles
                
                seen_links = set()
                
                for entry in feed.entries[:20]:
                    if len(articles) >= 5:
                        break
                    
                    pub_time = None
                    if hasattr(entry, 'published_parsed'):
                        pub_time = datetime(*entry.published_parsed[:6])
                    elif hasattr(entry, 'updated_parsed'):
                        pub_time = datetime(*entry.updated_parsed[:6])
                    
                    if not pub_time:
                        pub_time = datetime.now()
                    
                    if pub_time < self.forty_eight_hours_ago:
                        continue
                    
                    title = entry.get('title', '').strip()
                    summary = entry.get('summary', '').strip()
                    link = entry.get('link', '').strip()
                    
                    if not title or not link:
                        continue
                    
                    link_hash = hashlib.md5(link.encode()).hexdigest()
                    if link_hash in seen_links:
                        continue
                    seen_links.add(link_hash)
                    
                    if summary:
                        soup = BeautifulSoup(summary, 'html.parser')
                        summary = soup.get_text()[:250]
                    
                    article = {
                        'id': link_hash[:8],
                        'title': title[:150],
                        'link': link,
                        'source': source['name'],
                        'summary': summary[:250] + '...' if len(summary) > 250 else summary,
                        'category': source.get('category', 'general'),
                        'lang': source.get('lang', 'en'),
                        'importance': 6,
                        'time': pub_time.strftime('%Y-%m-%d %H:%M'),
                        'type': article_type
                    }
                    
                    if article['lang'] == 'en':
                        translated = self.baidu_translate(title, summary)
                        article['title_translated'] = translated['title']
                        article['summary_translated'] = translated['summary']
                    
                    if article_type == 'ai':
                        if self._is_ai_related(title, summary):
                            article['importance'] = 8
                            articles.append(article)
                    else:
                        articles.append(article)
                
                print(f"  ✓ {source['name']} 抓取完成 ({len(articles)}篇)")
                return articles
                
            except requests.exceptions.Timeout:
                print(f"  ⚠️  {source['name']} 请求超时")
                if attempt < max_retries - 1:
                    time.sleep(base_delay * (attempt + 1))
            except Exception as e:
                print(f"  ⚠️  {source['name']} 抓取失败: {e}")
                if attempt < max_retries - 1:
                    time.sleep(base_delay)
        
        return articles
    
    def fetch_html(self, source, article_type='fact'):
        """HTML页面解析方法"""
        max_retries = 2
        articles = []
        
        for attempt in range(max_retries):
            try:
                self._wait_if_needed(source['url'])
                
                headers = self._get_headers(source['url'])
                headers.update({
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Accept-Encoding': 'gzip, deflate',
                    'Referer': 'https://www.google.com/'
                })
                
                response = requests.get(source['url'], headers=headers, timeout=25)
                
                if response.status_code != 200:
                    print(f"  ⚠️  {source['name']} HTTP {response.status_code}")
                    if attempt < max_retries - 1:
                        time.sleep(3)
                        continue
                    return articles
                
                response.encoding = response.apparent_encoding or 'utf-8'
                
                try:
                    soup = BeautifulSoup(response.text, 'lxml')
                except:
                    soup = BeautifulSoup(response.text, 'html.parser')
                
                seen_links = set()
                
                selectors_to_try = [
                    'article', 'div.post-block', 'div.post-card',
                    'div.tease-card', 'div.article-card', 'div.entry-content',
                    'div.content-card', 'section.article',
                ]
                
                article_items = []
                for selector in selectors_to_try:
                    article_items = soup.select(selector)
                    if article_items:
                        break
                
                if not article_items:
                    article_items = soup.find_all(['h2', 'h3'])
                
                for item in article_items[:15]:
                    if len(articles) >= 5:
                        break
                    
                    title_elem = None
                    link_elem = None
                    
                    if item.name == 'article':
                        title_elem = item.find('h2') or item.find('h3') or item.find('h1')
                        link_elem = item.find('a')
                    elif item.name in ['h2', 'h3']:
                        title_elem = item
                        link_elem = item.find('a')
                    else:
                        title_elem = item.find('h2') or item.find('h3') or item.find('h1')
                        link_elem = item.find('a')
                    
                    if not title_elem or not link_elem:
                        continue
                    
                    title = title_elem.get_text().strip()
                    link = link_elem.get('href', '')
                    
                    if link and not link.startswith('http'):
                        link = urljoin(source['url'], link)
                    
                    if not title or not link:
                        continue
                    
                    link_hash = hashlib.md5(link.encode()).hexdigest()
                    if link_hash in seen_links:
                        continue
                    seen_links.add(link_hash)
                    
                    if article_type == 'ai' and not self._is_ai_related(title):
                        continue
                    
                    summary = ''
                    excerpt_elem = item.find(class_=re.compile(r'excerpt|summary|description'))
                    if excerpt_elem:
                        summary = excerpt_elem.get_text().strip()
                    elif item.name == 'article':
                        p_elem = item.find('p')
                        if p_elem:
                            summary = p_elem.get_text().strip()
                    
                    article = {
                        'id': link_hash[:8],
                        'title': title[:150],
                        'link': link,
                        'source': source['name'],
                        'summary': summary[:250] + '...' if len(summary) > 250 else summary,
                        'category': source.get('category', 'general'),
                        'lang': source.get('lang', 'en'),
                        'importance': 6,
                        'time': datetime.now().strftime('%Y-%m-%d %H:%M'),
                        'type': article_type
                    }
                    
                    if article['lang'] == 'en':
                        translated = self.baidu_translate(title, summary)
                        article['title_translated'] = translated['title']
                        article['summary_translated'] = translated['summary']
                    
                    articles.append(article)
                
                print(f"  ✓ {source['name']} HTML解析完成 ({len(articles)}篇)")
                return articles
                
            except requests.exceptions.Timeout:
                print(f"  ⚠️  {source['name']} 请求超时")
                if attempt < max_retries - 1:
                    time.sleep(3)
            except Exception as e:
                print(f"  ❌ {source['name']} HTML解析出错: {e}")
                return articles
        
        return articles
    
    def fetch_hackernews(self, source, article_type='ai'):
        """Hacker News抓取方法"""
        max_retries = 3
        retry_delay = 2
        articles = []
        
        for attempt in range(max_retries):
            try:
                timestamp = int(self.forty_eight_hours_ago.timestamp())
                url = source['url'].format(timestamp)
                
                if article_type == 'fact' and 'query=AI' in url:
                    url = url.replace('&query=AI', '')
                
                headers = self._get_headers(url)
                headers.update({
                    'Accept': 'application/json, text/plain, */*',
                    'Accept-Language': 'en-US,en;q=0.9',
                })
                
                response = requests.get(url, headers=headers, timeout=20)
                
                if response.status_code != 200:
                    print(f"  ⚠️  {source['name']} HTTP {response.status_code}")
                    if attempt < max_retries - 1:
                        time.sleep(retry_delay)
                        continue
                    return articles
                
                hits = response.json().get('hits', [])
                seen_links = set()
                
                for hit in hits[:10]:
                    link = hit.get('url', f"https://news.ycombinator.com/item?id={hit.get('objectID')}")
                    link_hash = hashlib.md5(link.encode()).hexdigest()
                    if link_hash in seen_links:
                        continue
                    seen_links.add(link_hash)
                    
                    title = hit.get('title', '')
                    
                    if article_type == 'ai' and not any(kw in title.lower() for kw in ['ai', 'llm', 'gpt', 'openai', 'anthropic']):
                        continue
                    
                    article = {
                        'id': f"hn_{hit.get('objectID', '')}",
                        'title': title,
                        'link': link,
                        'source': source['name'],
                        'points': hit.get('points', 0),
                        'comments': hit.get('num_comments', 0),
                        'category': source.get('category', 'tech'),
                        'importance': min(9, 6 + (hit.get('points', 0) // 20)),
                        'time': datetime.fromtimestamp(hit.get('created_at_i', 0)).strftime('%Y-%m-%d %H:%M'),
                        'type': article_type,
                        'lang': source.get('lang', 'en')
                    }
                    
                    if article['lang'] == 'en':
                        translated = self.baidu_translate(title, '')
                        article['title_translated'] = translated['title']
                    
                    articles.append(article)
                
                print(f"  ✓ {source['name']} 抓取完成 ({len(articles)}篇)")
                return articles
                
            except requests.exceptions.Timeout:
                print(f"  ⚠️  {source['name']} 请求超时")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
            except Exception as e:
                print(f"  ⚠️  {source['name']} 抓取出错: {e}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
        
        return articles
    
    def fetch_arxiv_abstract(self, url):
        """从 arXiv 论文详情页提取完整摘要"""
        if url in self.abstract_cache:
            return self.abstract_cache[url]
        
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            abstract_tag = soup.find('blockquote', class_='abstract')
            if abstract_tag:
                abstract_text = abstract_tag.text.strip()
                self.abstract_cache[url] = abstract_text
                return abstract_text
            else:
                self.abstract_cache[url] = ""
                return ""
        except Exception as e:
            print(f"  ❌ 抓取 arXiv 摘要失败 {url}: {e}")
            self.abstract_cache[url] = ""
            return ""
    
    def fetch_from_source(self, source, article_type='ai'):
        """
        根据源类型自动选择合适的抓取方法
        
        Args:
            source: 新闻源配置字典
            article_type: 'ai' 或 'fact'
        
        Returns:
            list: 抓取到的文章列表
        """
        source_type = source.get('type', 'rss')
        
        if source_type == 'arxiv':
            return self.fetch_arxiv(source)
        elif source_type == 'rss':
            return self.fetch_rss(source, article_type)
        elif source_type == 'html':
            return self.fetch_html(source, article_type)
        elif source_type == 'hn_api':
            return self.fetch_hackernews(source, article_type)
        else:
            print(f"  ⚠️  未知的源类型: {source_type}")
            return []


# 异步抓取方法（可选）
class AsyncNewsFetcher(NewsFetcher):
    """异步新闻抓取器"""
    
    async def fetch_rss_async(self, session, source, article_type='ai'):
        """异步RSS抓取"""
        if not ASYNC_AVAILABLE:
            raise RuntimeError("异步功能不可用：请先安装 aiohttp")
        
        articles = []
        try:
            async with session.get(source['url'], timeout=aiohttp.ClientTimeout(total=15)) as response:
                if response.status == 200:
                    text = await response.text()
                    feed = feedparser.parse(text)
                    seen_links = set()
                    
                    for entry in feed.entries[:20]:
                        if len(articles) >= 5:
                            break
                        
                        pub_time = None
                        if hasattr(entry, 'published_parsed'):
                            pub_time = datetime(*entry.published_parsed[:6])
                        elif hasattr(entry, 'updated_parsed'):
                            pub_time = datetime(*entry.updated_parsed[:6])
                        
                        if not pub_time:
                            pub_time = datetime.now()
                        
                        if pub_time < self.forty_eight_hours_ago:
                            continue
                        
                        title = entry.get('title', '').strip()
                        summary = entry.get('summary', '').strip()
                        link = entry.get('link', '').strip()
                        
                        link_hash = hashlib.md5(link.encode()).hexdigest()
                        if link_hash in seen_links:
                            continue
                        seen_links.add(link_hash)
                        
                        if summary:
                            soup = BeautifulSoup(summary, 'html.parser')
                            summary = soup.get_text()[:250]
                        
                        article = {
                            'id': link_hash[:8],
                            'title': title[:150],
                            'link': link,
                            'source': source['name'],
                            'summary': summary[:250] + '...' if len(summary) > 250 else summary,
                            'category': source.get('category', 'general'),
                            'lang': source.get('lang', 'en'),
                            'importance': 6,
                            'time': pub_time.strftime('%Y-%m-%d %H:%M'),
                            'type': article_type
                        }
                        
                        if article['lang'] == 'en':
                            translated = self.baidu_translate(title, summary)
                            article['title_translated'] = translated['title']
                            article['summary_translated'] = translated['summary']
                        
                        if article_type == 'ai':
                            if self._is_ai_related(title, summary):
                                article['importance'] = 8
                                articles.append(article)
                        else:
                            articles.append(article)
                    
                    print(f"  ✓ {source['name']} 抓取完成 ({len(articles)}篇)")
        except Exception as e:
            print(f"  ❌ {source['name']} 抓取出错: {e}")
        
        return articles


if __name__ == "__main__":
    # 测试代码
    print("测试新闻抓取模块...")
    fetcher = NewsFetcher()
    
    # 测试 ArXiv 抓取
    test_source = {
        'name': 'Arxiv AI Papers',
        'url': 'https://arxiv.org/list/cs.AI/recent',
        'type': 'arxiv',
        'category': 'ai_research'
    }
    
    articles = fetcher.fetch_arxiv(test_source)
    print(f"\n抓取到 {len(articles)} 篇文章")
    for article in articles[:3]:
        print(f"- {article['title'][:60]}...")
