#!/usr/bin/env python3
"""
AI科技资讯智能分析系统
抓取过去24小时AI/科技资讯，进行智能分析，生成深度报告并推送
"""

import os
import re
import json
import requests
import random
from datetime import datetime, timedelta
import time
from bs4 import BeautifulSoup
from urllib.parse import quote
import hashlib

class AITechNewsAnalyzer:
    def __init__(self):
        self.server_chan_key = os.getenv('SERVER_CHAN_KEY')
        self.ai_api_key = os.getenv('AI_API_KEY')  # 用于内容分析的AI API密钥
        self.twenty_four_hours_ago = datetime.now() - timedelta(hours=24)
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        # 扩展的新闻源 - 专注AI和技术领域
        self.news_sources = [
            # AI专业新闻
            {
                'name': 'Arxiv AI最新论文',
                'url': 'http://arxiv.org/list/cs.AI/recent',
                'type': 'arxiv',
                'category': 'ai_research'
            },
            {
                'name': 'MIT Technology Review AI',
                'url': 'https://www.technologyreview.com/topic/artificial-intelligence/feed/',
                'type': 'rss',
                'category': 'ai_news'
            },
            {
                'name': 'VentureBeat AI',
                'url': 'https://venturebeat.com/category/ai/feed/',
                'type': 'rss',
                'category': 'ai_business'
            },
            # 综合科技新闻
            {
                'name': 'TechCrunch AI',
                'url': 'https://techcrunch.com/category/artificial-intelligence/feed/',
                'type': 'rss',
                'category': 'tech_news'
            },
            {
                'name': 'The Verge AI',
                'url': 'https://www.theverge.com/ai-artificial-intelligence/rss',
                'type': 'rss',
                'category': 'tech_news'
            },
            {
                'name': 'Hacker News AI',
                'url': 'https://hn.algolia.com/api/v1/search_by_date?tags=story&numericFilters=created_at_i>{}&query=AI',
                'type': 'api',
                'category': 'community'
            },
            # 中文AI新闻
            {
                'name': '机器之心',
                'url': 'https://www.jiqizhixin.com/feed',
                'type': 'rss',
                'category': 'ai_news_cn'
            },
            {
                'name': '量子位AI',
                'url': 'https://www.qbitai.com/feed',
                'type': 'rss',
                'category': 'ai_news_cn'
            }
        ]
        
        self.all_articles = []
        self.ai_articles = []
        self.deep_analysis = []
        self.featured_article = None
    
    def fetch_arxiv_papers(self, source):
        """抓取Arxiv AI最新论文"""
        try:
            response = requests.get(source['url'], headers=self.headers, timeout=15)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # 解析Arxiv页面结构
                dt_list = soup.find_all('dt')
                dd_list = soup.find_all('dd')
                
                for i, (dt, dd) in enumerate(zip(dt_list[:10], dd_list[:10])):
                    # 提取论文ID和标题
                    paper_id = dt.find('a', title='Abstract').text.strip()
                    title_tag = dd.find('div', class_='list-title')
                    if title_tag:
                        title = title_tag.text.replace('Title:', '').strip()
                        
                        # 提取作者和摘要
                        authors_tag = dd.find('div', class_='list-authors')
                        authors = authors_tag.text.replace('Authors:', '').strip() if authors_tag else ''
                        
                        abstract_tag = dd.find('p')
                        abstract = abstract_tag.text.strip() if abstract_tag else ''
                        
                        # 生成Arxiv链接
                        paper_url = f'https://arxiv.org/abs/{paper_id}'
                        
                        article = {
                            'title': f"[论文] {title[:80]}",
                            'link': paper_url,
                            'source': source['name'],
                            'summary': abstract[:150] + '...' if len(abstract) > 150 else abstract,
                            'authors': authors,
                            'category': 'ai_research',
                            'importance': 8,  # 重要性评分(1-10)
                            'time': datetime.now().strftime('%Y-%m-%d')
                        }
                        
                        self.all_articles.append(article)
                        self.ai_articles.append(article)
                        
        except Exception as e:
            print(f"Arxiv抓取失败: {e}")
    
    def fetch_rss_feed(self, source):
        """抓取RSS新闻源"""
        try:
            import feedparser
            feed = feedparser.parse(source['url'])
            
            for entry in feed.entries[:8]:  # 每个源取前8条
                # 检查是否包含AI关键词
                title = entry.get('title', '')
                summary = entry.get('summary', '')
                content = f"{title} {summary}".lower()
                
                ai_keywords = ['ai', 'artificial intelligence', 'machine learning', 
                              '深度学习', '神经网络', 'llm', 'gpt', '人工智能']
                
                is_ai_related = any(keyword in content for keyword in ai_keywords)
                
                article = {
                    'title': title[:100],
                    'link': entry.get('link', ''),
                    'source': source['name'],
                    'summary': summary[:200] + '...' if len(summary) > 200 else summary,
                    'category': source['category'],
                    'importance': 7 if is_ai_related else 5,
                    'time': entry.get('published', datetime.now().strftime('%Y-%m-%d'))
                }
                
                self.all_articles.append(article)
                if is_ai_related:
                    self.ai_articles.append(article)
                    
        except Exception as e:
            print(f"RSS抓取失败 {source['name']}: {e}")
    
    def fetch_hackernews_ai(self, source):
        """抓取Hacker News AI相关内容"""
        try:
            # 计算时间戳
            timestamp = int((datetime.now() - timedelta(hours=24)).timestamp())
            url = source['url'].format(timestamp)
            
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                hits = response.json().get('hits', [])
                
                for hit in hits[:15]:
                    title = hit.get('title', '').lower()
                    
                    # 筛选AI相关内容
                    if any(keyword in title for keyword in ['ai', 'llm', 'gpt', 'openai', 'anthropic']):
                        article = {
                            'title': hit.get('title', ''),
                            'link': hit.get('url', f"https://news.ycombinator.com/item?id={hit.get('objectID')}"),
                            'source': source['name'],
                            'points': hit.get('points', 0),
                            'comments': hit.get('num_comments', 0),
                            'category': 'community',
                            'importance': min(9, 6 + (hit.get('points', 0) // 10)),  # 根据点赞数评分
                            'time': datetime.fromtimestamp(hit.get('created_at_i', 0)).strftime('%Y-%m-%d %H:%M')
                        }
                        
                        self.all_articles.append(article)
                        self.ai_articles.append(article)
                        
        except Exception as e:
            print(f"Hacker News抓取失败: {e}")
    
    def analyze_with_ai(self, article):
        """使用AI分析单篇文章（使用免费API）"""
        try:
            # 方法1: 使用OpenRouter的免费模型（需要注册获取API key）
            if self.ai_api_key:
                return self._analyze_with_openai(article)
            # 方法2: 使用智谱AI（有免费额度）
            elif os.getenv('ZHIPU_API_KEY'):
                return self._analyze_with_zhipu(article)
            # 方法3: 使用本地关键词分析（无需API）
            else:
                return self._analyze_with_keywords(article)
                
        except Exception as e:
            print(f"AI分析失败: {e}")
            return self._analyze_with_keywords(article)
    
    def _analyze_with_keywords(self, article):
        """基于关键词的简单分析"""
        title = article['title'].lower()
        summary = article.get('summary', '').lower()
        text = f"{title} {summary}"
        
        analysis = {
            'technique_tags': [],
            'trend_insight': '',
            'business_impact': '',
            'difficulty': 'medium'
        }
        
        # 技术关键词检测
        tech_keywords = {
            'llm': '大语言模型',
            'gpt': 'GPT系列',
            'diffusion': '扩散模型',
            'transformer': 'Transformer架构',
            'multimodal': '多模态AI',
            'reinforcement': '强化学习',
            'computer vision': '计算机视觉',
            'nlp': '自然语言处理'
        }
        
        for eng, chi in tech_keywords.items():
            if eng in text:
                analysis['technique_tags'].append(chi)
        
        # 趋势洞察
        if not analysis['technique_tags']:
            analysis['technique_tags'] = ['AI技术']
        
        if any(word in text for word in ['breakthrough', 'new method', '创新']):
            analysis['trend_insight'] = '技术突破性进展'
            analysis['importance'] = 9
        elif any(word in text for word in ['application', 'deploy', '应用']):
            analysis['trend_insight'] = '实际应用部署'
            analysis['importance'] = 8
        else:
            analysis['trend_insight'] = '技术研究进展'
            analysis['importance'] = 7
        
        return analysis
    
    def _analyze_with_openai(self, article):
        """使用OpenAI兼容API进行分析（需要API密钥）"""
        try:
            import openai
            
            # 使用OpenRouter作为示例（支持多个模型）
            client = openai.OpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=self.ai_api_key
            )
            
            prompt = f"""
            请分析以下AI/科技文章，提供：
            1. 核心技术点（3-5个关键词）
            2. 行业影响分析
            3. 技术难度评级（low/medium/high）
            4. 一句话总结
            
            文章标题：{article['title']}
            文章摘要：{article.get('summary', '无摘要')}
            来源：{article['source']}
            
            请用JSON格式回复，包含：technique_tags, industry_impact, difficulty_level, summary。
            """
            
            response = client.chat.completions.create(
                model="google/gemma-7b-it:free",  # 免费模型
                messages=[{"role": "user", "content": prompt}],
                max_tokens=500,
                temperature=0.3
            )
            
            # 解析返回的JSON
            import json
            result = json.loads(response.choices[0].message.content)
            return result
            
        except Exception as e:
            print(f"OpenAI分析失败，退回关键词分析: {e}")
            return self._analyze_with_keywords(article)
    
    def select_featured_article(self):
        """选择一篇深度精选文章"""
        if not self.all_articles:
            return None
        
        # 根据重要性、来源权威性、内容长度等评分
        scored_articles = []
        for article in self.all_articles:
            score = article.get('importance', 5)
            
            # 来源权威性加分
            source_weights = {
                'Arxiv AI最新论文': 2,
                'MIT Technology Review AI': 3,
                '机器之心': 2,
                '量子位AI': 2,
                'VentureBeat AI': 2
            }
            score += source_weights.get(article['source'], 0)
            
            # 内容长度加分
            if len(article.get('summary', '')) > 200:
                score += 1
            
            scored_articles.append((score, article))
        
        # 选择分数最高的
        scored_articles.sort(reverse=True, key=lambda x: x[0])
        self.featured_article = scored_articles[0][1]
        
        return self.featured_article
    
    def generate_detailed_analysis(self, limit=5):
        """生成详细分析文稿"""
        if not self.ai_articles:
            return []
        
        # 选择最重要的几篇进行分析
        important_articles = sorted(
            self.ai_articles, 
            key=lambda x: x.get('importance', 5), 
            reverse=True
        )[:limit]
        
        analyses = []
        for article in important_articles:
            analysis = self.analyze_with_ai(article)
            
            analysis_text = f"""
## 📊 {article['title']}

**来源**: {article['source']} | **时间**: {article.get('time', 'N/A')}

**🔗 原文链接**: {article['link']}

**📝 内容摘要**:
{article.get('summary', '暂无详细摘要')}

**🏷️ 技术标签**: {', '.join(analysis.get('technique_tags', ['AI技术']))}

**📈 趋势洞察**: {analysis.get('trend_insight', 'AI领域进展')}

**💼 行业影响**: {analysis.get('business_impact', '推动AI技术发展与应用')}

**⚙️ 技术难度**: {analysis.get('difficulty', 'medium').upper()}

---
"""
            analyses.append({
                'article': article,
                'analysis': analysis,
                'text': analysis_text
            })
        
        self.deep_analysis = analyses
        return analyses
    
    def format_push_message(self):
        """格式化推送消息"""
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M')
        
        message = f"""# 🤖 AI科技日报 ({current_time})

## 📊 数据概览
• 总共抓取: **{len(self.all_articles)}** 篇文章
• AI相关: **{len(self.ai_articles)}** 篇
• 分析深度: **{len(self.deep_analysis)}** 篇详细分析
"""

        # 1. AI快讯摘要
        if self.ai_articles:
            message += "\n## 🚀 AI快讯摘要\n"
            ai_by_category = {}
            for article in self.ai_articles[:15]:  # 最多15条快讯
                cat = article.get('category', 'other')
                if cat not in ai_by_category:
                    ai_by_category[cat] = []
                ai_by_category[cat].append(article)
            
            for category, articles in ai_by_category.items():
                category_name = {
                    'ai_research': '🧪 研究论文',
                    'ai_news': '📰 AI新闻',
                    'ai_business': '💼 商业应用',
                    'tech_news': '🔧 技术动态',
                    'ai_news_cn': '🇨🇳 中文资讯'
                }.get(category, '📌 其他')
                
                message += f"\n### {category_name}\n"
                for i, article in enumerate(articles[:4], 1):
                    message += f"{i}. **{article['title']}**\n"
                    message += f"   📍 {article['source']} | 🔗 [阅读原文]({article['link']})\n"
        
        # 2. 深度分析部分
        if self.deep_analysis:
            message += "\n## 🔍 深度分析\n"
            message += "_以下文章已进行详细技术分析：_\n\n"
            
            for analysis in self.deep_analysis:
                article = analysis['article']
                message += f"### {article['title']}\n"
                message += analysis['text']
        
        # 3. 每日精选
        if self.featured_article:
            message += "\n## 🏆 今日深度精选\n"
            message += f"### {self.featured_article['title']}\n\n"
            message += f"**推荐理由**: 本文来自{self.featured_article['source']}，"
            message += f"在今日资讯中具有较高的技术深度和行业影响力。\n\n"
            message += f"**核心要点**:\n"
            
            # 从摘要中提取要点
            summary = self.featured_article.get('summary', '')
            sentences = summary.split('. ')
            for i, sentence in enumerate(sentences[:3], 1):
                if sentence.strip():
                    message += f"{i}. {sentence.strip()}.\n"
            
            message += f"\n**🔗 深度阅读**: {self.featured_article['link']}\n"
        
        # 4. 趋势总结
        message += "\n## 📈 今日AI趋势总结\n"
        
        # 统计技术关键词
        all_tags = []
        for analysis in self.deep_analysis:
            all_tags.extend(analysis['analysis'].get('technique_tags', []))
        
        if all_tags:
            from collections import Counter
            tag_counts = Counter(all_tags)
            top_tags = tag_counts.most_common(5)
            
            message += "**热门技术焦点**:\n"
            for tag, count in top_tags:
                message += f"• {tag} ({count}次提及)\n"
        
        message += f"\n---\n"
        message += f"⏰ 下次更新: 明日 08:00 (北京时间)\n"
        message += f"📚 数据源: {len(self.news_sources)}个专业AI/科技媒体\n"
        message += f"🤖 分析方式: 关键词分析"
        if self.ai_api_key:
            message += "+AI模型分析"
        
        title = f"AI科技日报 {current_time.split()[0]} | {len(self.ai_articles)}篇AI资讯"
        
        return message, title
    
    def run(self):
        """主执行函数"""
        print("=" * 70)
        print("🤖 AI科技资讯智能分析系统启动")
        print(f"📅 执行时间: {datetime.now()}")
        print("=" * 70)
        
        # 顺序抓取各新闻源
        print("\n📡 开始抓取新闻源...")
        for source in self.news_sources:
            print(f"  → 正在抓取: {source['name']}")
            
            if source['type'] == 'arxiv':
                self.fetch_arxiv_papers(source)
            elif source['type'] == 'rss':
                self.fetch_rss_feed(source)
            elif source['type'] == 'api':
                self.fetch_hackernews_ai(source)
            
            time.sleep(1.5)  # 礼貌延迟
        
        print(f"\n✅ 抓取完成！共获得 {len(self.all_articles)} 篇文章")
        print(f"✨ 其中AI相关: {len(self.ai_articles)} 篇")
        
        # 生成深度分析
        print("\n🔍 开始深度分析重要文章...")
        self.generate_detailed_analysis(limit=5)
        
        # 选择每日精选
        print("\n🏆 选择今日深度精选...")
        self.select_featured_article()
        
        # 生成推送消息
        print("\n📝 生成推送内容...")
        message, title = self.format_push_message()
        
        # 保存分析结果
        output = {
            'fetch_time': datetime.now().isoformat(),
            'total_articles': len(self.all_articles),
            'ai_articles': len(self.ai_articles),
            'deep_analysis': len(self.deep_analysis),
            'featured_article': self.featured_article,
            'articles': self.all_articles[:20]
        }
        
        with open('ai_news_analysis.json', 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        
        print(f"\n💾 分析结果已保存至: ai_news_analysis.json")
        print(f"📨 消息标题: {title}")
        print(f"📏 消息长度: {len(message)} 字符")
        
        return message, title

def send_to_serverchan(title, message, api_key):
    """发送到Server酱"""
    if not api_key:
        print("❌ 未配置Server酱密钥，跳过推送")
        return False
    
    # 如果消息过长，进行分割（Server酱有限制）
    if len(message) > 6000:
        parts = [message[i:i+4000] for i in range(0, len(message), 4000)]
        message = parts[0] + f"\n\n...（消息过长，已截断，完整内容请查看日志）"
    
    url = f"https://sctapi.ftqq.com/{api_key}.send"
    
    data = {
        'title': title[:100],  # 标题限制长度
        'desp': message,
        'channel': 9  # 企业微信通道，更稳定
    }
    
    try:
        response = requests.post(url, data=data, timeout=15)
        result = response.json()
        
        if result.get('code') == 0:
            print(f"✅ 微信推送成功！推送ID: {result.get('data', {}).get('pushid')}")
            return True
        else:
            print(f"❌ 推送失败: {result}")
            return False
    except Exception as e:
        print(f"❌ 推送请求失败: {e}")
        return False

if __name__ == "__main__":
    analyzer = AITechNewsAnalyzer()
    message, title = analyzer.run()
    
    # 发送推送
    api_key = os.getenv('SERVER_CHAN_KEY')
    if api_key:
        print("\n📤 正在发送到微信...")
        success = send_to_serverchan(title, message, api_key)
        if not success:
            print("\n⚠️ 推送失败，但分析已完成。")
    else:
        print("\n⚠️ 未配置SERVER_CHAN_KEY，跳过推送")
        print("请在GitHub Secrets中添加该密钥")
    
    # 在控制台显示部分内容
    print("\n" + "=" * 70)
    print("📋 生成内容预览:")
    print("=" * 70)
    print(message[:1500] + "..." if len(message) > 1500 else message)
