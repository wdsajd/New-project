#!/usr/bin/env python3
"""
AI科技资讯智能分析系统
抓取过去24小时AI/科技资讯，进行智能分析，生成深度报告并推送
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

class AITechNewsAnalyzer:
    def __init__(self):
        self.server_chan_key = os.getenv('SERVER_CHAN_KEY')
        self.zhipu_api_key = os.getenv('ZHIPU_API_KEY')
        self.twenty_four_hours_ago = datetime.now() - timedelta(hours=24)
        
        # 配置多个AI/科技新闻源
        self.news_sources = [
            # 国际AI研究
            {
                'name': 'Arxiv AI Papers',
                'url': 'http://arxiv.org/list/cs.AI/recent',
                'type': 'arxiv',
                'category': 'research'
            },
            {
                'name': 'MIT Tech Review AI',
                'url': 'https://www.technologyreview.com/topic/artificial-intelligence/feed/',
                'type': 'rss',
                'category': 'research'
            },
            # 国际科技媒体
            {
                'name': 'TechCrunch AI',
                'url': 'https://techcrunch.com/category/artificial-intelligence/feed/',
                'type': 'rss',
                'category': 'tech'
            },
            {
                'name': 'VentureBeat AI',
                'url': 'https://venturebeat.com/category/ai/feed/',
                'type': 'rss',
                'category': 'tech'
            },
            {
                'name': 'The Verge AI',
                'url': 'https://www.theverge.com/ai-artificial-intelligence/rss',
                'type': 'rss',
                'category': 'tech'
            },
            # 开发者社区
            {
                'name': 'Hacker News AI',
                'url': 'https://hn.algolia.com/api/v1/search_by_date?tags=story&numericFilters=created_at_i>{}&query=AI',
                'type': 'hn_api',
                'category': 'community'
            },
            # 中文AI媒体
            {
                'name': '机器之心',
                'url': 'https://www.jiqizhixin.com/feed',
                'type': 'rss',
                'category': 'cn_ai'
            },
            {
                'name': '量子位',
                'url': 'https://www.qbitai.com/feed',
                'type': 'rss',
                'category': 'cn_ai'
            },
            {
                'name': 'AI科技评论',
                'url': 'https://www.leiphone.com/feed',
                'type': 'rss',
                'category': 'cn_ai'
            }
        ]
        
        self.all_articles = []
        self.ai_articles = []
        self.deep_analyses = []
        self.featured_article = None
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
    
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
                            'full_text': f"标题: {title}\n作者: {authors}\n摘要: {abstract}"
                        }
                        self.all_articles.append(article)
                        self.ai_articles.append(article)
        except Exception as e:
            print(f"⚠️ Arxiv论文抓取失败: {e}")
    
    def fetch_rss(self, source):
        """抓取RSS源"""
        try:
            feed = feedparser.parse(source['url'])
            for entry in feed.entries[:10]:
                # 检查发布时间
                pub_time = None
                if hasattr(entry, 'published_parsed'):
                    pub_time = datetime(*entry.published_parsed[:6])
                elif hasattr(entry, 'updated_parsed'):
                    pub_time = datetime(*entry.updated_parsed[:6])
                
                if pub_time and pub_time < self.twenty_four_hours_ago:
                    continue
                
                # 检查是否AI相关
                title = entry.get('title', '')
                summary = entry.get('summary', '')
                content = f"{title} {summary}".lower()
                
                ai_keywords = ['ai', 'artificial intelligence', 'machine learning', 
                              'deep learning', 'neural network', 'llm', 'gpt', 'transformer',
                              '人工智能', '机器学习', '深度学习', '大模型','生成式AI','计算机视觉','图像生成','训练'，
                              'AIGC','Diffusion模型','MoE模型','RLHF']
                
                is_ai_related = any(keyword in content for keyword in ai_keywords)
                
                article = {
                    'id': hashlib.md5(entry.get('link', '').encode()).hexdigest()[:8],
                    'title': title[:150],
                    'link': entry.get('link', ''),
                    'source': source['name'],
                    'summary': summary[:250] + '...' if len(summary) > 250 else summary,
                    'category': source['category'],
                    'importance': 8 if is_ai_related else 6,
                    'time': pub_time.strftime('%Y-%m-%d %H:%M') if pub_time else '未知',
                    'full_text': f"标题: {title}\n摘要: {summary}"
                }
                
                self.all_articles.append(article)
                if is_ai_related:
                    self.ai_articles.append(article)
                    
        except Exception as e:
            print(f"⚠️ RSS网站抓取失败 {source['name']}: {e}")
    
    def fetch_hackernews(self, source):
        """抓取Hacker News AI内容"""
        try:
            timestamp = int(self.twenty_four_hours_ago.timestamp())
            url = source['url'].format(timestamp)
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                hits = response.json().get('hits', [])
                for hit in hits[:15]:
                    title = hit.get('title', '').lower()
                    if not any(keyword in title for keyword in ['ai', 'llm', 'gpt', 'openai', 'anthropic']):
                        continue
                    
                    article = {
                        'id': f"hn_{hit.get('objectID', '')}",
                        'title': hit.get('title', ''),
                        'link': hit.get('url', f"https://news.ycombinator.com/item?id={hit.get('objectID')}"),
                        'source': source['name'],
                        'points': hit.get('points', 0),
                        'comments': hit.get('num_comments', 0),
                        'category': 'community',
                        'importance': min(9, 7 + (hit.get('points', 0) // 20)),
                        'time': datetime.fromtimestamp(hit.get('created_at_i', 0)).strftime('%Y-%m-%d %H:%M'),
                        'full_text': f"标题: {hit.get('title', '')}\n得分: {hit.get('points', 0)} | 评论: {hit.get('num_comments', 0)}"
                    }
                    self.all_articles.append(article)
                    self.ai_articles.append(article)
                    
        except Exception as e:
            print(f"⚠️ Hacker News抓取失败: {e}")
    
    def fetch_all_news(self):
        """抓取所有新闻源"""
        print("📡 开始抓取新闻源...")
        for source in self.news_sources:
            print(f"  → {source['name']}")
            try:
                if source['type'] == 'arxiv':
                    self.fetch_arxiv(source)
                elif source['type'] == 'rss':
                    self.fetch_rss(source)
                elif source['type'] == 'hn_api':
                    self.fetch_hackernews(source)
                time.sleep(1)  # 礼貌延迟
            except Exception as e:
                print(f"    ❌ 抓取失败: {e}")
        
        print(f"\n✅ 抓取完成！共获得 {len(self.all_articles)} 篇文章")
        print(f"✨ 其中AI相关: {len(self.ai_articles)} 篇")
    
    def analyze_with_zhipu(self, article):
        """使用智谱AI分析文章"""
        try:
            from zhipuai import ZhipuAI
            
            client = ZhipuAI(api_key=self.zhipu_api_key)
            
            prompt = f"""作为AI科技分析师，请分析以下文章：

标题：{article['title']}
来源：{article['source']}
摘要：{article.get('summary', '暂无详细摘要')}

请提供以下分析：
1. 核心技术点（识别文中提到的关键技术并进行简要说明）
2. 创新程度（高/中/低）
3. 行业影响（技术迭代方向、拓展潜力、科研突破、商业应用、技术普及等）
4. 推荐理由（为什么这篇文章值得关注）
5.性能表现（推理速度、准确率、多模态兼容性、上下文承载能力等）
6. 技术标签（3-5个关键词）

请用JSON格式回复，包含以下字段：
- technique_points: 列表，核心技术点
- innovation_level: 字符串，高/中/低
- industry_impact: 字符串
- recommendation_reason: 字符串
- efficiency_performance: 字符串
- tech_tags: 列表，技术标签
"""
            
            response = client.chat.completions.create(
                model="glm-4",
                messages=[
                    {"role": "system", "content": "你是一个专业的AI科技分析师，擅长分析技术文章。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=800
            )
            
            result_text = response.choices[0].message.content
            json_match = re.search(r'\{.*\}', result_text, re.DOTALL)
            
            if json_match:
                analysis_result = json.loads(json_match.group())
            else:
                analysis_result = {
                    "technique_points": ["AI技术"],
                    "innovation_level": "中",
                    "industry_impact": "推动AI技术发展",
                    "recommendation_reason": "文章涉及当前AI热点话题",
                    "tech_tags": ["人工智能"]
                }
            
            return {
                'technique_tags': analysis_result.get('tech_tags', ['AI技术']),
                'innovation_level': analysis_result.get('innovation_level', '中'),
                'industry_impact': analysis_result.get('industry_impact', '技术进展'),
                'recommendation': analysis_result.get('recommendation_reason', '值得关注'),
                'technique_points': analysis_result.get('technique_points', []),
                'source': 'zhipu_ai'
            }
            
        except Exception as e:
            print(f"⚠️ 智谱AI分析失败: {e}")
            return self._fallback_analysis(article)
    
    def _fallback_analysis(self, article):
        """备用关键词分析"""
        text = f"{article['title']} {article.get('summary', '')}".lower()
        
        tech_tags = []
        if any(word in text for word in ['llm', 'gpt', '大语言模型']):
            tech_tags.append('大语言模型')
        if any(word in text for word in ['transformer', '注意力机制']):
            tech_tags.append('Transformer')
        if any(word in text for word in ['multimodal', '多模态']):
            tech_tags.append('多模态AI')
        if any(word in text for word in ['computer vision', '计算机视觉']):
            tech_tags.append('计算机视觉')
        if not tech_tags:
            tech_tags = ['AI技术']
        
        return {
            'technique_tags': tech_tags,
            'innovation_level': '中',
            'industry_impact': '推动AI技术发展',
            'recommendation': 'AI领域相关进展',
            'technique_points': tech_tags,
            'source': 'keyword_analysis'
        }
    
    def generate_deep_analyses(self, limit=5):
        """生成深度分析"""
        if not self.ai_articles:
            return []
        
        # 选择最重要的文章进行分析
        important_articles = sorted(
            self.ai_articles,
            key=lambda x: x.get('importance', 5),
            reverse=True
        )[:limit]
        
        print(f"\n🔍 开始深度分析 {len(important_articles)} 篇文章...")
        
        analyses = []
        for i, article in enumerate(important_articles, 1):
            print(f"  {i}. 分析: {article['title'][:60]}...")
            analysis = self.analyze_with_zhipu(article)
            
            analysis_text = f"""## 📊 {article['title']}

**来源**: {article['source']} | **时间**: {article.get('time', 'N/A')}
**AI分析模型**: 🤖 智谱GLM-4

**🔗 原文链接**: {article['link']}

**📝 内容摘要**:
{article.get('summary', '暂无详细摘要')}

**🏷️ 技术标签**: {', '.join(analysis['technique_tags'])}

**✨ 创新程度**: {analysis['innovation_level'].upper()}

**📈 行业影响**: {analysis['industry_impact']}

**💡 推荐理由**: {analysis['recommendation']}

**🔬 核心技术点**:
{chr(10).join(f'- {point}' for point in analysis['technique_points'][:3])}

---
"""
            analyses.append({
                'article': article,
                'analysis': analysis,
                'text': analysis_text
            })
            time.sleep(1)  # API调用间隔
        
        self.deep_analyses = analyses
        return analyses
    
    def select_featured_article(self):
        """选择深度精选文章"""
        if not self.all_articles:
            return None
        
        # 根据重要性、来源权威性、内容长度选择
        scored_articles = []
        for article in self.all_articles:
            score = article.get('importance', 5)
            
            # 来源权重
            source_weights = {
                'Arxiv AI Papers': 3,
                'MIT Tech Review AI': 3,
                '机器之心': 2,
                '量子位': 2,
                'TechCrunch AI': 2
            }
            score += source_weights.get(article['source'], 0)
            
            # 内容长度加分
            if len(article.get('summary', '')) > 150:
                score += 1
            
            scored_articles.append((score, article))
        
        scored_articles.sort(reverse=True, key=lambda x: x[0])
        self.featured_article = scored_articles[0][1]
        
        return self.featured_article
    
    def generate_report(self):
        """生成完整报告"""
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M')
        
        report = f"""# 🤖 AI科技日报 ({current_time})

## 📊 数据概览
- 总共抓取: **{len(self.all_articles)}** 篇文章
- AI相关: **{len(self.ai_articles)}** 篇
- 深度分析: **{len(self.deep_analyses)}** 篇
- 新闻来源: **{len(self.news_sources)}** 个

"""
        
        # 1. AI快讯摘要
        if self.ai_articles:
            report += "\n## 🚀 AI快讯摘要\n"
            
            # 按类别分组
            articles_by_category = {}
            for article in self.ai_articles[:20]:  # 最多20条快讯
                cat = article.get('category', 'other')
                if cat not in articles_by_category:
                    articles_by_category[cat] = []
                articles_by_category[cat].append(article)
            
            category_names = {
                'research': '🧪 研究论文',
                'tech': '📰 科技新闻',
                'community': '👥 社区讨论',
                'cn_ai': '🇨🇳 中文资讯'
            }
            
            for cat, articles in articles_by_category.items():
                name = category_names.get(cat, '📌 其他')
                report += f"\n### {name}\n"
                for i, article in enumerate(articles[:4], 1):
                    report += f"{i}. **{article['title']}**\n"
                    report += f"   📍 {article['source']} | 🔗 [阅读原文]({article['link']})\n"
        
        # 2. 深度分析部分
        if self.deep_analyses:
            report += "\n## 🔍 深度分析\n"
            report += "_以下文章已进行详细技术分析：_\n\n"
            for analysis in self.deep_analyses:
                report += analysis['text']
        
        # 3. 每日精选
        if self.featured_article:
            report += "\n## 🏆 今日深度精选\n"
            report += f"### {self.featured_article['title']}\n\n"
            report += f"**来源**: {self.featured_article['source']}\n"
            report += f"**时间**: {self.featured_article.get('time', '未知')}\n"
            report += f"**摘要**: {self.featured_article.get('summary', '暂无摘要')}\n\n"
            report += f"**🔗 深度阅读**: {self.featured_article['link']}\n"
        
        # 4. 趋势总结
        report += "\n## 📈 今日AI趋势总结\n"
        
        # 统计技术关键词
        all_tags = []
        for analysis in self.deep_analyses:
            all_tags.extend(analysis['analysis']['technique_tags'])
        
        if all_tags:
            tag_counts = Counter(all_tags)
            top_tags = tag_counts.most_common(5)
            
            report += "**热门技术焦点**:\n"
            for tag, count in top_tags:
                report += f"- {tag} ({count}次提及)\n"
        
        report += f"\n---\n"
        report += f"⏰ 下次更新: 明日 08:00 (北京时间)\n"
        report += f"📚 数据源: {len(self.news_sources)}个专业AI/科技媒体\n"
        report += f"🤖 分析方式: 智谱GLM-4 AI分析\n"
        report += f"📅 生成时间: {current_time}"
        
        return report
    
    def save_report(self, report):
        """保存报告到文件"""
        # 保存为JSON数据
        output_data = {
            'fetch_time': datetime.now().isoformat(),
            'total_articles': len(self.all_articles),
            'ai_articles': len(self.ai_articles),
            'deep_analyses': len(self.deep_analyses),
            'featured_article': self.featured_article,
            'all_articles': self.all_articles[:50]
        }
        
        with open('ai_news_analysis.json', 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
        
        # 保存为Markdown报告
        with open('news_report.md', 'w', encoding='utf-8') as f:
            f.write(report)
        
        print("💾 报告已保存至: ai_news_analysis.json, news_report.md")
    
    def send_to_wechat(self, report):
        """通过Server酱发送到微信"""
        if not self.server_chan_key:
            print("⚠️ 未配置Server酱密钥，跳过推送")
            return False
        
        # Server酱Turbo版API
        url = f"https://sctapi.ftqq.com/{self.server_chan_key}.send"
        
        # 如果报告过长，进行截断
        if len(report) > 6000:
            report = report[:6000] + "\n\n...（报告过长，已截断，完整内容请查看保存的文件）"
        
        data = {
            'title': f"AI科技日报 {datetime.now().strftime('%m-%d')} | {len(self.ai_articles)}篇AI资讯",
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
        print("🤖 AI科技资讯智能分析系统启动")
        print(f"📅 执行时间: {datetime.now()}")
        print("=" * 70)
        
        # 1. 抓取新闻
        self.fetch_all_news()
        
        if not self.all_articles:
            print("❌ 未抓取到任何文章，程序退出")
            return None, "无内容"
        
        # 2. 生成深度分析
        self.generate_deep_analyses(limit=5)
        
        # 3. 选择每日精选
        self.select_featured_article()
        
        # 4. 生成报告
        report = self.generate_report()
        
        # 5. 保存报告
        self.save_report(report)
        
        # 6. 发送推送
        title = f"AI科技日报 {datetime.now().strftime('%m-%d')} | {len(self.ai_articles)}篇AI资讯"
        
        return report, title

def main():
    """主函数"""
    analyzer = AITechNewsAnalyzer()
    report, title = analyzer.run()
    
    if report:
        # 发送到微信
        if analyzer.server_chan_key:
            print("\n📤 正在发送到微信...")
            analyzer.send_to_wechat(report)
        else:
            print("\n⚠️ 未配置SERVER_CHAN_KEY，跳过推送")
            print("请在GitHub Secrets中设置该密钥")
        
        # 打印部分内容预览
        print("\n" + "=" * 70)
        print("📋 生成内容预览:")
        print("=" * 70)
        print(report[:1500] + "..." if len(report) > 1500 else report)
    else:
        print("❌ 未生成报告，请检查配置")

if __name__ == "__main__":
    main()
