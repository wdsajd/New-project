#!/usr/bin/env python3
"""
AI科技资讯与事实资讯智能分析系统
抓取过去48小时AI/科技资讯和多方事实新闻，智能分析后推送
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
from urllib.parse import urljoin
from collections import Counter

class EnhancedNewsAnalyzer:
    def __init__(self):
        self.server_chan_key = os.getenv('SERVER_CHAN_KEY')
        self.zhipu_api_key = os.getenv('ZHIPU_API_KEY')
        self.forty_eight_hours_ago = datetime.now() - timedelta(hours=48)
        
        # AI科技新闻源（保持不变）
        self.ai_news_sources = [
            {'name': 'Arxiv AI Papers', 'url': 'http://arxiv.org/list/cs.AI/recent', 'type': 'arxiv', 'category': 'ai_research'},
            {'name': 'TechCrunch AI', 'url': 'https://techcrunch.com/category/artificial-intelligence/feed/', 'type': 'rss', 'category': 'tech'},
            {'name': 'Hacker News AI', 'url': 'https://hn.algolia.com/api/v1/search_by_date?tags=story&numericFilters=created_at_i>{}&query=AI', 'type': 'hn_api', 'category': 'community'},
            {'name': '机器之心', 'url': 'https://www.jiqizhixin.com/feed', 'type': 'rss', 'category': 'cn_ai'},
            {'name': '量子位', 'url': 'https://www.qbitai.com/feed', 'type': 'rss', 'category': 'cn_ai'},
        ]
        
        # 更新：多方面事实新闻源，优先中国国内可访问来源，减少重复和过时
        self.fact_news_sources = [
            # 国内新闻（优先可访问来源）
            {'name': '央视网', 'url': 'http://news.cctv.com/rss/index.xml', 'type': 'rss', 'category': 'china', 'lang': 'zh'},
            {'name': '新华网', 'url': 'http://www.news.cn/rss/rsstw.xml', 'type': 'rss', 'category': 'china', 'lang': 'zh'},  # 更新为更稳定的新华网RSS
            {'name': '人民日报', 'url': 'http://www.people.com.cn/rss/politics.xml', 'type': 'rss', 'category': 'china', 'lang': 'zh'},
            {'name': '澎湃新闻', 'url': 'https://rsshub.app/thepaper/featured', 'type': 'rss', 'category': 'china', 'lang': 'zh'},
            {'name': '虎扑社区', 'url': 'https://rsshub.app/hupu/bbs/all', 'type': 'rss', 'category': 'community', 'lang': 'zh'},  # 添加虎扑 via RSSHub
            {'name': '腾讯新闻', 'url': 'https://rsshub.app/tencent/news/author/1', 'type': 'rss', 'category': 'china', 'lang': 'zh'},  # 添加腾讯新闻
            # 国际/亚太新闻（选择在中国可访问或中立来源）
            {'name': '联合早报', 'url': 'https://www.zaobao.com/realtime/china/rss', 'type': 'rss', 'category': 'asia', 'lang': 'zh'},  # 更新为中国实时
            {'name': 'BBC中文', 'url': 'https://feeds.bbci.co.uk/zhongwen/simp/rss.xml', 'type': 'rss', 'category': 'world', 'lang': 'zh'},  # BBC中文版，可访问
            {'name': 'Reuters China', 'url': 'https://www.reuters.com/arc/outboundfeeds/rss/world/china/', 'type': 'rss', 'category': 'world', 'lang': 'en'},  # Reuters中国相关
            # 社区/综合
            {'name': 'Reddit World News', 'url': 'https://www.reddit.com/r/worldnews/.rss', 'type': 'rss', 'category': 'world', 'lang': 'en'},
            {'name': 'Hacker News Top', 'url': 'https://hn.algolia.com/api/v1/search_by_date?tags=story&numericFilters=created_at_i>{}', 'type': 'hn_api', 'category': 'tech', 'lang': 'en'},
        ]
        
        self.all_articles = []
        self.ai_articles = []
        self.fact_articles = []
        self.deep_analyses = []
        self.featured_article = None
        self.featured_fact = None
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
    
    # ==================== 原有AI新闻抓取方法（保持不变） ====================
    def fetch_arxiv(self, source):
        """抓取Arxiv AI论文"""
        try:
            response = requests.get(source['url'], headers=self.headers, timeout=15)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                dt_list = soup.find_all('dt')
                dd_list = soup.find_all('dd')
                
                for i, (dt, dd) in enumerate(zip(dt_list[:8], dd_list[:8])):
                    paper_id_elem = dt.find('a', title='Abstract')
                    if not paper_id_elem:
                        continue
                    
                    paper_id = paper_id_elem.text.strip()
                    title_elem = dd.find('div', class_='list-title')
                    authors_elem = dd.find('div', class_='list-authors')
                    abstract_elem = dd.find('p')
                    
                    if title_elem:
                        title = title_elem.text.replace('Title:', '').strip()
                        authors = authors_elem.text.replace('Authors:', '').strip() if authors_elem else ''
                        abstract = abstract_elem.text.strip() if abstract_elem else ''
                        
                        article = {
                            'id': f"arxiv_{paper_id}",
                            'title': f"[论文] {title[:120]}",
                            'link': f'https://arxiv.org/abs/{paper_id}',
                            'source': source['name'],
                            'summary': abstract[:200] + '...' if len(abstract) > 200 else abstract,
                            'authors': authors,
                            'category': 'research',
                            'importance': 9,
                            'time': datetime.now().strftime('%Y-%m-%d'),
                            'type': 'ai'
                        }
                        self.all_articles.append(article)
                        self.ai_articles.append(article)
        except Exception as e:
            print(f"⚠️ Arxiv抓取失败: {e}")
    
    def fetch_rss(self, source, article_type='ai'):
        """通用RSS抓取方法，增强去重和时效性"""
        try:
            feed = feedparser.parse(source['url'])
            articles_added = 0
            seen_links = set()  # 增强去重
            
            for entry in feed.entries[:20]:  # 增加检查范围以获取更多新鲜内容
                if articles_added >= 5:  # 每个源最多取5条
                    break
                    
                # 检查发布时间
                pub_time = None
                if hasattr(entry, 'published_parsed'):
                    pub_time = datetime(*entry.published_parsed[:6])
                elif hasattr(entry, 'updated_parsed'):
                    pub_time = datetime(*entry.updated_parsed[:6])
                
                # 如果无法获取时间，使用当前时间但降低优先级
                if not pub_time:
                    pub_time = datetime.now()
                    article_importance = 4  # 降低未知时间的重要性
                
                # 检查是否在过去48小时内
                if pub_time < self.forty_eight_hours_ago:
                    continue
                
                title = entry.get('title', '').strip()
                summary = entry.get('summary', '').strip()
                link = entry.get('link', '').strip()
                
                # 去重检查
                link_hash = hashlib.md5(link.encode()).hexdigest()
                if link_hash in seen_links:
                    continue
                seen_links.add(link_hash)
                
                # 清理HTML标签
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
                
                # 如果是英文，进行翻译以提供中英文对照
                if article['lang'] == 'en' and self.zhipu_api_key:
                    translated = self.translate_with_zhipu(title, summary)
                    if translated:
                        article['title_translated'] = translated['title']
                        article['summary_translated'] = translated['summary']
                
                # 如果是AI新闻源，检查是否AI相关
                if article_type == 'ai':
                    content = f"{title} {summary}".lower()
                    ai_keywords = ['ai', 'artificial intelligence', 'machine learning', 
                              'deep learning', 'neural network', 'llm', 'gpt', 'transformer',
                              '人工智能', '机器学习', '深度学习', '大模型', '生成式AI', '计算机视觉', '图像生成','训练',
                              'AIGC', 'Diffusion模型', 'MoE模型', 'RLHF']
                    
                    is_ai_related = any(keyword in content for keyword in ai_keywords)
                    if is_ai_related:
                        article['importance'] = 8
                        self.all_articles.append(article)
                        self.ai_articles.append(article)
                        articles_added += 1
                else:
                    # 事实新闻直接添加，检查重复
                    if link_hash not in [a['id'] for a in self.fact_articles]:
                        self.all_articles.append(article)
                        self.fact_articles.append(article)
                        articles_added += 1
                    
        except Exception as e:
            print(f"⚠️ RSS抓取失败 {source['name']}: {e}")
    
    def fetch_hackernews(self, source, article_type='ai'):
        """通用Hacker News抓取方法"""
        try:
            timestamp = int(self.forty_eight_hours_ago.timestamp())
            query_param = source['url'].format(timestamp)
            url = query_param
            
            # 如果不是AI专用搜索，移除AI查询参数
            if article_type == 'fact' and 'query=AI' in url:
                url = url.replace('&query=AI', '')
            
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                hits = response.json().get('hits', [])
                seen_links = set()
                for hit in hits[:10]:
                    link = hit.get('url', f"https://news.ycombinator.com/item?id={hit.get('objectID')}")
                    link_hash = hashlib.md5(link.encode()).hexdigest()
                    if link_hash in seen_links:
                        continue
                    seen_links.add(link_hash)
                    
                    title = hit.get('title', '')
                    
                    # 对于事实新闻，不筛选AI内容
                    if article_type == 'ai' and not any(keyword in title.lower() for keyword in ['ai', 'llm', 'gpt', 'openai', 'anthropic']):
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
                        'type': article_type
                    }
                    
                    # 翻译如果英文
                    if source.get('lang') == 'en' and self.zhipu_api_key:
                        translated = self.translate_with_zhipu(title, '')
                        if translated:
                            article['title_translated'] = translated['title']
                    
                    self.all_articles.append(article)
                    if article_type == 'ai':
                        self.ai_articles.append(article)
                    else:
                        self.fact_articles.append(article)
                        
        except Exception as e:
            print(f"⚠️ Hacker News抓取失败: {e}")
    
    # ==================== 新增：翻译功能 ====================
    def translate_with_zhipu(self, title, summary):
        """使用智谱AI翻译英文到中文，提供贴合实际的翻译"""
        try:
            from zhipuai import ZhipuAI
            
            client = ZhipuAI(api_key=self.zhipu_api_key)
            
            prompt = f"""作为专业翻译，请将以下英文内容翻译成贴合实际、自然流畅的中文：
标题：{title}
摘要：{summary}

请提供中英文对照：
- 原标题：[original title]
- 翻译标题：[translated title]
- 原摘要：[original summary]
- 翻译摘要：[translated summary]

输出JSON格式：
{{
  "title": "translated title",
  "summary": "translated summary"
}}
但在报告中可显示完整对照。
"""
            
            response = client.chat.completions.create(
                model="glm-3-turbo",
                messages=[
                    {"role": "system", "content": "你是一个专业的英中翻译专家，翻译要准确、自然。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                max_tokens=400
            )
            
            result_text = response.choices[0].message.content
            json_match = re.search(r'\{.*\}', result_text, re.DOTALL)
            
            if json_match:
                return json.loads(json_match.group())
            else:
                return None
            
        except Exception as e:
            print(f"⚠️ 翻译失败: {e}")
            return None
    
    # ==================== 新增：抓取事实新闻 ====================
    def fetch_fact_news(self):
        """抓取多方面事实新闻"""
        print("\n📰 开始抓取多方面事实新闻（过去48小时）...")
        
        for source in self.fact_news_sources:
            print(f"  → {source['name']}")
            try:
                if source['type'] == 'rss':
                    self.fetch_rss(source, article_type='fact')
                elif source['type'] == 'hn_api':
                    self.fetch_hackernews(source, article_type='fact')
                time.sleep(1)  # 礼貌延迟
            except Exception as e:
                print(f"    ❌ 抓取失败: {e}")
                continue
        
        print(f"✅ 事实新闻抓取完成！共获得 {len(self.fact_articles)} 篇")
        
        # 去重
        unique_facts = []
        seen_ids = set()
        for article in self.fact_articles:
            if article['id'] not in seen_ids:
                unique_facts.append(article)
                seen_ids.add(article['id'])
        
        # 排序：优先级高 → 重要性高 → 时间新
        self.fact_articles = sorted(
            unique_facts,
            key=lambda x: (
                -x.get('priority', 5),                     # 注意负号：越高优先级越靠前
                x.get('importance', 5),
                datetime.strptime(x['time'], '%Y-%m-%d %H:%M') if x.get('time') else datetime.now()
            ),
            reverse=True
        )[:12]  # 最多保留12条
    
    # ==================== 原有AI分析功能（保持不变） ====================
    def fetch_all_news(self):
        """抓取所有新闻"""
        print("📡 开始抓取AI科技新闻（过去48小时）...")
        for source in self.ai_news_sources:
            print(f"  → {source['name']}")
            try:
                if source['type'] == 'arxiv':
                    self.fetch_arxiv(source)
                elif source['type'] == 'rss':
                    self.fetch_rss(source, article_type='ai')
                elif source['type'] == 'hn_api':
                    self.fetch_hackernews(source, article_type='ai')
                time.sleep(1)
            except Exception as e:
                print(f"    ❌ 抓取失败: {e}")
        
        print(f"✅ AI新闻抓取完成！共获得 {len(self.ai_articles)} 篇")
    
    def analyze_with_zhipu(self, article):
        """使用智谱AI分析文章"""
        try:
            from zhipuai import ZhipuAI
            
            client = ZhipuAI(api_key=self.zhipu_api_key)
            
            prompt = f"""作为新闻分析师，请分析以下文章：

标题：{article['title']}
来源：{article['source']}
摘要：{article.get('summary', '暂无详细摘要')}

请提供以下分析：
1. 核心内容要点
2. 新闻重要性（高/中/低）
3. 影响范围（国际/国内/区域/行业）
4. 值得关注的理由
5. 内容标签（3-5个关键词）

请用JSON格式回复，包含以下字段：
- key_points: 列表，核心内容要点
- importance_level: 字符串，高/中/低
- impact_scope: 字符串
- attention_reason: 字符串
- content_tags: 列表，内容标签
"""
            
            response = client.chat.completions.create(
                model="glm-3-turbo",  # 使用性价比更高的模型
                messages=[
                    {"role": "system", "content": "你是一个专业的新闻分析师。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=600
            )
            
            result_text = response.choices[0].message.content
            json_match = re.search(r'\{.*\}', result_text, re.DOTALL)
            
            if json_match:
                analysis_result = json.loads(json_match.group())
            else:
                analysis_result = {
                    "key_points": ["重要新闻"],
                    "importance_level": "中",
                    "impact_scope": "广泛关注",
                    "attention_reason": "值得关注的新闻报道",
                    "content_tags": ["新闻"]
                }
            
            return {
                'content_tags': analysis_result.get('content_tags', ['新闻']),
                'importance_level': analysis_result.get('importance_level', '中'),
                'impact_scope': analysis_result.get('impact_scope', '广泛'),
                'attention_reason': analysis_result.get('attention_reason', '值得关注'),
                'key_points': analysis_result.get('key_points', []),
                'source': 'zhipu_ai'
            }
            
        except Exception as e:
            print(f"⚠️ 智谱AI分析失败: {e}")
            return self._fallback_analysis(article)
    
    def _fallback_analysis(self, article):
        """备用关键词分析"""
        text = f"{article['title']} {article.get('summary', '')}".lower()
        
        # 根据内容判断类别
        tags = []
        if any(word in text for word in ['politics', 'government', 'policy', '政治', '政府']):
            tags.append('政治')
        if any(word in text for word in ['economy', 'financial', 'market', '经济', '金融']):
            tags.append('经济')
        if any(word in text for word in ['technology', 'tech', 'digital', '科技', '技术']):
            tags.append('科技')
        if any(word in text for word in ['health', 'medical', '疫情', '疫苗', '健康']):
            tags.append('健康')
        if any(word in text for word in ['environment', 'climate', '环保', '气候']):
            tags.append('环境')
        if not tags:
            tags = ['综合新闻']
        
        return {
            'content_tags': tags,
            'importance_level': '中',
            'impact_scope': '广泛关注',
            'attention_reason': '值得关注的新闻报道',
            'key_points': tags,
            'source': 'keyword_analysis'
        }
    
    def generate_deep_analyses(self, limit=3):
        """生成深度分析（AI新闻）"""
        if not self.ai_articles:
            return []
        
        important_articles = sorted(
            self.ai_articles,
            key=lambda x: x.get('importance', 5),
            reverse=True
        )[:limit]
        
        print(f"\n🔍 开始深度分析 {len(important_articles)} 篇AI文章...")
        
        analyses = []
        for i, article in enumerate(important_articles, 1):
            print(f"  {i}. 分析: {article['title'][:60]}...")
            analysis = self.analyze_with_zhipu(article)
            
            # 如果有翻译，使用翻译
            title_display = article.get('title_translated', article['title'])
            
            analysis_text = f"""### 📑 论文 {title_display}

**来源**: {article['source']} | **时间**: {article.get('time', 'N/A')} | **AI分析模型**: 🤖 智谱GLM

**原文链接**: {article['link']}

**内容摘要**:
{analysis.get('content_summary', '暂无摘要')}

**内容标签**: {', '.join(analysis.get('content_tags', []))}

**重要性**: {analysis.get('importance_level', '中')}

**影响范围**: {analysis.get('impact_scope', '广泛关注')}

**关注理由**: {analysis.get('attention_reason', '值得关注的报道')}

**核心要点**（标签形式）:
{chr(10).join(f'- {point}' for point in analysis.get('key_points', []))}

---
"""
            analyses.append({
                'article': article,
                'analysis': analysis,
                'text': analysis_text
            })
            
            if self.zhipu_api_key:
                time.sleep(1)  # API调用间隔
        
        self.deep_analyses = analyses
        return analyses
    
    def select_featured_articles(self):
        """选择精选文章"""
        if self.ai_articles:
            scored_ai = sorted(
                [(a.get('importance', 5), a) for a in self.ai_articles],
                reverse=True, key=lambda x: x[0]
            )
            if scored_ai:
                self.featured_article = scored_ai[0][1]
        
        if self.fact_articles:
            # 事实新闻按重要性和时效性评分
            for article in self.fact_articles:
                # 加分项：高重要性、多评论/分数、近期发布
                score = article.get('importance', 5)
                if article.get('points', 0) > 50:
                    score += 1
                if article.get('comments', 0) > 20:
                    score += 1
                article['_score'] = score
            
            scored_facts = sorted(
                self.fact_articles,
                key=lambda x: x.get('_score', 5),
                reverse=True
            )
            if scored_facts:
                self.featured_fact = scored_facts[0]
                self.featured_fact['generated_summary'] = self.generate_fact_summary(self.featured_fact)
    
    def generate_fact_summary(self, article):
        """为事实精选生成简短摘要"""
        if not self.zhipu_api_key:
            return article.get('summary_translated', article.get('summary', '暂无摘要'))[:100] + '...'
        
        try:
            from zhipuai import ZhipuAI
            client = ZhipuAI(api_key=self.zhipu_api_key)
            
            prompt = f"""基于以下新闻标题和链接，生成80-120字中文摘要：
标题：{article['title']}
链接：{article['link']}

摘要要求：提炼核心事件/内容/数据/意义，语言客观专业。"""
            
            response = client.chat.completions.create(
                model="glm-3-turbo",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=150
            )
            
            summary = response.choices[0].message.content.strip()
            if len(summary) > 120:
                summary = summary[:117] + "..."
            return summary
        except Exception as e:
            print(f"⚠️ 生成摘要失败: {e}")
            return article.get('summary_translated', article.get('summary', '暂无摘要'))[:100] + '...'
    
    def format_fact_news_section(self):
        """整理事实新闻部分，分组显示国内+国际"""
        if not self.fact_articles:
            return ""

        section = f"""
## 🌍 48小时事实资讯速览 ({len(self.fact_articles)}篇)

*事实新闻来自 {len(set([a['source'] for a in self.fact_articles]))} 个国内外权威媒体*
*筛选过去48小时最重要新闻，保持信息广度与深度*
"""

        # ── 国内新闻 ────────────────────────────────
        domestic = [
            a for a in self.fact_articles 
            if a.get('lang') == 'zh' or a.get('category') in ['china', 'cn']
        ]
        domestic = sorted(domestic, key=lambda x: x.get('importance', 5), reverse=True)[:7]

        if domestic:
            section += f"""
### 🇨🇳 国内新闻
"""
            for i, article in enumerate(domestic, 1):
                title_orig = article['title']
                title_cn = article.get('title_translated', title_orig)
                source = article['source']
                link = article['link']

                section += f"{i}. **{title_orig}**\n"
                if title_cn != title_orig:
                    section += f"   {title_cn}\n"
                section += f"   📍 {source} | 🔗 [阅读原文]({link})\n\n"

        # ── 国际新闻 ────────────────────────────────
        international = [
            a for a in self.fact_articles 
            if a.get('lang') != 'zh' or a.get('category') in ['world', 'asia', 'international']
        ]
        international = sorted(international, key=lambda x: x.get('importance', 5), reverse=True)[:7]

        if international:
            section += f"""
### 🌐 国际新闻
"""
            for i, article in enumerate(international, 1):
                title_orig = article['title']
                title_cn = article.get('title_translated', title_orig)
                source = article['source']
                link = article['link']

                section += f"{i}. **{title_orig}**\n"
                if title_cn != title_orig:
                    section += f"   {title_cn}\n"
                section += f"   📍 {source} | 🔗 [阅读原文]({link})\n\n"

        # ── 今日事实精选 ─────────────────────────────
        if self.featured_fact:
            featured = self.featured_fact
            title_orig = featured['title']
            title_cn = featured.get('title_translated', title_orig)

            summary_text = featured.get('generated_summary',
                                       featured.get('summary_translated',
                                                   featured.get('summary', '暂无可用摘要')))

            if len(summary_text) > 120:
                summary_text = summary_text[:117] + "…"

            section += f"""
## 📰 今日事实精选

**{title_orig}**  
{title_cn if title_cn != title_orig else ''}

**来源**：{featured['source']} | **时间**：{featured.get('time', '今日')}

**摘要**：{summary_text}

**深度阅读**：{featured['link']}
"""

        return section
    
    def generate_report(self):
        """生成完整报告"""
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M')
        
        report = f"""# 📊 每日资讯双报告 ({current_time})

## 📈 数据总览
- **AI科技资讯**: {len(self.ai_articles)} 篇
- **事实资讯**: {len(self.fact_articles)} 篇
- **深度分析**: {len(self.deep_analyses)} 篇
- **覆盖媒体**: {len(self.ai_news_sources) + len(self.fact_news_sources)} 个

"""
        
        # 1. AI科技新闻部分
        if self.ai_articles:
            report += f"""
## 🤖 AI科技日报

### 🚀 AI快讯摘要
"""
            ai_by_category = {}
            for article in self.ai_articles[:15]:
                cat = article.get('category', 'other')
                if cat not in ai_by_category:
                    ai_by_category[cat] = []
                ai_by_category[cat].append(article)
            
            category_names = {
                'research': '🧪 研究前沿',
                'tech': '🔧 技术动态',
                'community': '👥 社区热点',
                'cn_ai': '🇨🇳 国内AI'
            }
            
            for cat, articles in ai_by_category.items():
                name = category_names.get(cat, '📌 其他')
                report += f"\n**{name}**\n"
                for i, article in enumerate(articles[:3], 1):
                    title_display = article.get('title_translated', article['title'])
                    report += f"{i}. {title_display}\n"
                    report += f"   📍 {article['source']} | 🔗 [阅读原文]({article['link']})\n"
            
            # AI深度分析
            if self.deep_analyses:
                report += "\n## 🔍 AI深度分析\n"
                report += "_以下AI文章已进行详细技术分析：_\n\n"
                for analysis in self.deep_analyses:
                    report += analysis['text']
            
            # AI精选
            if self.featured_article:
                featured_title = self.featured_article.get('title_translated', self.featured_article['title'])
                featured_summary = self.featured_article.get('summary_translated', self.featured_article.get('summary', '暂无摘要'))
                
                report += f"""
## 🏆 今日AI精选

**{featured_title}**

**来源**: {self.featured_article['source']}
**摘要**: {featured_summary}

**🔗 深度阅读**: {self.featured_article['link']}
"""
        
        # 2. 事实新闻部分
        report += self.format_fact_news_section()
        
        # 3. 总结
        report += f"""

---

## 📋 报告信息
- **生成时间**: {current_time}
- **下次更新**: 明日 08:00 (北京时间)
- **分析支持**: 智谱AI GLM模型
- **推送方式**: Server酱微信推送

*保持信息敏感度，拥抱科技变革，关注世界动态*
"""
        
        title = f"资讯双报告 {datetime.now().strftime('%m-%d')} | AI:{len(self.ai_articles)} 事实:{len(self.fact_articles)}"
        
        return report, title
    
    def save_reports(self, report):
        """保存报告"""
        output_data = {
            'fetch_time': datetime.now().isoformat(),
            'ai_articles_count': len(self.ai_articles),
            'fact_articles_count': len(self.fact_articles),
            'deep_analyses_count': len(self.deep_analyses),
            'featured_article': self.featured_article,
            'featured_fact': self.featured_fact,
            'ai_articles': self.ai_articles[:20],
            'fact_articles': self.fact_articles[:10]
        }
        
        with open('enhanced_news_analysis.json', 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
        
        with open('enhanced_news_report.md', 'w', encoding='utf-8') as f:
            f.write(report)
        
        print("💾 报告已保存至: enhanced_news_analysis.json, enhanced_news_report.md")
    
    def send_to_wechat(self, report):
        """通过Server酱发送到微信"""
        if not self.server_chan_key:
            print("⚠️ 未配置Server酱密钥，跳过推送")
            return False
        
        url = f"https://sctapi.ftqq.com/{self.server_chan_key}.send"
        
        if len(report) > 6000:
            report = report[:6000] + "\n\n...（报告过长，已截断，完整内容请查看保存的文件）"
        
        data = {
            'title': f"资讯双报告 {datetime.now().strftime('%m-%d')} | AI:{len(self.ai_articles)} 事实:{len(self.fact_articles)}",
            'desp': report
        }
        
        try:
            response = requests.post(url, data=data, timeout=15)
            result = response.json()
            
            if result.get('code') == 0:
                print(f"✅ 微信推送成功！消息ID: {result.get('data', {}).get('pushid')}")
                return True
            else:
                print(f"❌ 推送失败: {result}")
                return False
        except Exception as e:
            print(f"❌ 推送请求失败: {e}")
            return False
    
        def run(self):
        """主执行函数"""
        print("=" * 70)
        print("📊 增强版资讯分析系统启动")
        print(f"📅 执行时间: {datetime.now()}")
        print("=" * 70)
        
        # 1. 抓取AI新闻
        self.fetch_all_news()
        
        # 2. 抓取事实新闻（排序已移到 fetch_fact_news 內）
        self.fetch_fact_news()
        
        if not self.all_articles:
            print("❌ 未抓取到任何文章，程序退出")
            return None, "无内容"
        
        # 3. 生成AI深度分析
        self.generate_deep_analyses(limit=3)
        
        # 4. 选择精选文章
        self.select_featured_articles()
        
        # 5. 生成报告
        report, title = self.generate_report()
        
        # 6. 保存报告
        self.save_reports(report)
        
        print(f"\n📊 报告生成完成:")
        print(f"   AI资讯: {len(self.ai_articles)} 篇")
        print(f"   事实资讯: {len(self.fact_articles)} 篇")
        print(f"   报告标题: {title}")
        
        return report, title
        
        # 3. 生成AI深度分析
        self.generate_deep_analyses(limit=3)
        
        # 4. 选择精选文章
        self.select_featured_articles()
        
        # 5. 生成报告
        report, title = self.generate_report()
        
        # 6. 保存报告
        self.save_reports(report)
        
        print(f"\n📊 报告生成完成:")
        print(f"   AI资讯: {len(self.ai_articles)} 篇")
        print(f"   事实资讯: {len(self.fact_articles)} 篇")
        print(f"   报告标题: {title}")
        
        return report, title

def main():
    analyzer = EnhancedNewsAnalyzer()
    report, title = analyzer.run()
    
    if report:
        if analyzer.server_chan_key:
            print("\n📤 正在发送到微信...")
            analyzer.send_to_wechat(report)
        else:
            print("\n⚠️ 未配置SERVER_CHAN_KEY，跳过推送")
        
        # 打印预览
        print("\n" + "=" * 70)
        print("📋 内容预览:")
        print("=" * 70)
        preview_length = min(2000, len(report))
        print(report[:preview_length] + "..." if len(report) > preview_length else report)
    else:
        print("❌ 未生成报告，请检查配置")

if __name__ == "__main__":
    main()
