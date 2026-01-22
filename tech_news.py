#!/usr/bin/env python3
"""
每日科技资讯抓取与推送脚本
抓取过去24小时主流科技媒体新闻，通过Server酱发送到微信
"""

import os
import requests
import json
from datetime import datetime, timedelta
import time
from bs4 import BeautifulSoup

class TechNewsCollector:
    def __init__(self):
        self.server_chan_key = os.getenv('SERVER_CHAN_KEY')
        self.twenty_four_hours_ago = datetime.now() - timedelta(hours=24)
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        self.all_news = []
    
    def fetch_techcrunch(self):
        """抓取TechCrunch新闻（通过API）[citation:2]"""
        try:
            api_url = "https://techcrunch.com/wp-json/tc/v1/magazine?page=1&_embed=true"
            response = requests.get(api_url, headers=self.headers, timeout=10)
            
            if response.status_code == 200:
                articles = response.json()
                for article in articles[:5]:  # 取前5条
                    # 解析发布日期（根据实际API响应调整）
                    title = article.get('title', {}).get('rendered', '')
                    link = article.get('link', '')
                    
                    self.all_news.append({
                        'title': title[:100] + '...' if len(title) > 100 else title,
                        'link': link,
                        'source': 'TechCrunch',
                        'time': datetime.now().strftime('%Y-%m-%d')
                    })
        except Exception as e:
            print(f"TechCrunch抓取失败: {e}")
    
    def fetch_sina_tech(self):
        """抓取新浪科技新闻（示例）[citation:6]"""
        try:
            url = "https://finance.sina.com.cn/tech/"
            response = requests.get(url, headers=self.headers, timeout=10)
            
            if response.status_code == 200:
                response.encoding = 'utf-8'
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # 查找新闻列表（根据实际页面结构调整）
                news_items = soup.find_all('li', class_=False)[:10]
                
                for item in news_items:
                    link_tag = item.find('a')
                    if link_tag:
                        title = link_tag.get_text().strip()
                        link = link_tag.get('href')
                        if link and not link.startswith('http'):
                            link = 'https:' + link
                        
                        self.all_news.append({
                            'title': title[:80] + '...' if len(title) > 80 else title,
                            'link': link,
                            'source': '新浪科技',
                            'time': datetime.now().strftime('%H:%M')
                        })
        except Exception as e:
            print(f"新浪科技抓取失败: {e}")
    
    def fetch_hackernews(self):
        """抓取Hacker News热门新闻"""
        try:
            # 获取热门故事ID
            top_url = "https://hacker-news.firebaseio.com/v0/topstories.json"
            response = requests.get(top_url, timeout=10)
            
            if response.status_code == 200:
                story_ids = response.json()[:8]
                
                for story_id in story_ids[:5]:  # 只获取前5条详情
                    story_url = f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json"
                    story_resp = requests.get(story_url, timeout=5)
                    
                    if story_resp.status_code == 200:
                        story = story_resp.json()
                        # 检查时间戳是否在24小时内
                        if 'time' in story:
                            story_time = datetime.fromtimestamp(story['time'])
                            if story_time > self.twenty_four_hours_ago:
                                self.all_news.append({
                                    'title': story.get('title', ''),
                                    'link': story.get('url', f'https://news.ycombinator.com/item?id={story_id}'),
                                    'source': 'Hacker News',
                                    'score': story.get('score', 0),
                                    'time': story_time.strftime('%Y-%m-%d %H:%M')
                                })
                    time.sleep(0.2)  # 礼貌延迟
                    
        except Exception as e:
            print(f"Hacker News抓取失败: {e}")
    
    def format_message(self):
        """格式化推送消息"""
        if not self.all_news:
            return "今日暂无科技资讯", "科技资讯日报（空）"
        
        # 按来源分组
        news_by_source = {}
        for item in self.all_news:
            source = item.get('source', '其他')
            if source not in news_by_source:
                news_by_source[source] = []
            news_by_source[source].append(item)
        
        # 构建Markdown消息
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M')
        message = f"## 🚀 科技资讯日报 ({current_time})\n\n"
        message += f"过去24小时共抓取 **{len(self.all_news)}** 条资讯\n\n"
        
        for source, items in news_by_source.items():
            message += f"### 📰 {source}\n"
            for i, item in enumerate(items[:3], 1):  # 每个来源最多3条
                title = item['title']
                url = item['link']
                
                # 添加额外信息
                extra = ""
                if 'score' in item and item['score'] > 0:
                    extra = f" | 👍 {item['score']}"
                
                message += f"{i}. **{title}**{extra}\n"
                message += f"   🔗 {url}\n\n"
        
        message += "\n---\n"
        message += "📊 数据来源: TechCrunch、新浪科技、Hacker News等\n"
        message += "⏰ 下次更新: 明日 08:00 (北京时间)"
        
        title = f"科技资讯日报 ({datetime.now().strftime('%m-%d')})"
        return message, title
    
    def send_to_wechat(self, message, title):
        """通过Server酱发送到微信[citation:5]"""
        if not self.server_chan_key:
            print("未设置Server酱密钥，跳过推送")
            return False
        
        # Server酱Turbo版API (推荐)
        url = f"https://sctapi.ftqq.com/{self.server_chan_key}.send"
        
        data = {
            'title': title,
            'desp': message
        }
        
        try:
            response = requests.post(url, data=data, timeout=10)
            result = response.json()
            
            if result.get('code') == 0:
                print(f"✅ 微信推送成功！消息ID: {result.get('data', {}).get('pushid')}")
                return True
            else:
                print(f"❌ 推送失败: {result.get('message')}")
                return False
        except Exception as e:
            print(f"❌ 推送请求失败: {e}")
            return False
    
    def run(self):
        """主执行函数"""
        print("=" * 60)
        print(f"开始执行科技资讯抓取 - {datetime.now()}")
        print("=" * 60)
        
        # 顺序抓取各来源
        print("\n1. 抓取TechCrunch...")
        self.fetch_techcrunch()
        time.sleep(1)
        
        print("2. 抓取新浪科技...")
        self.fetch_sina_tech()
        time.sleep(1)
        
        print("3. 抓取Hacker News...")
        self.fetch_hackernews()
        
        print(f"\n✅ 抓取完成！共获得 {len(self.all_news)} 条资讯")
        
        # 格式化并发送
        message, title = self.format_message()
        
        print("\n" + "=" * 60)
        print("生成的消息摘要：")
        print("=" * 60)
        print(message[:500] + "..." if len(message) > 500 else message)
        
        if self.server_chan_key:
            print("\n正在发送到微信...")
            self.send_to_wechat(message, title)
        else:
            print("\n⚠️ 未配置SERVER_CHAN_KEY，跳过推送步骤")
            print("如需推送，请在GitHub仓库Settings → Secrets中设置")
        
        # 保存结果到文件（可选）
        with open('news_result.json', 'w', encoding='utf-8') as f:
            json.dump(self.all_news, f, ensure_ascii=False, indent=2)
        
        return len(self.all_news)

if __name__ == "__main__":
    collector = TechNewsCollector()
    news_count = collector.run()
    exit(0 if news_count > 0 else 1)
