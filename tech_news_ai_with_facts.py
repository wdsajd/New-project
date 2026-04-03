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
from urllib.parse import urljoin
from collections import Counter
import random  # 用于生成 salt
import google.generativeai as genai

# 导入新闻抓取模块
from news_fetcher import NewsFetcher, AsyncNewsFetcher

# 尝试导入 fake_useragent（可选）
try:
    from fake_useragent import UserAgent
    UA_AVAILABLE = True
    ua = UserAgent()
except ImportError:
    print("⚠️  警告: 未安装 fake_useragent，将使用默认 User-Agent")
    print("   安装命令: pip install fake-useragent")
    UA_AVAILABLE = False
    ua = None

# 条件导入异步库（提供友好的错误提示）
try:
    import asyncio
    import aiohttp
    ASYNC_AVAILABLE = True
except ImportError as e:
    print("⚠️  警告: 未安装异步库，异步功能将不可用")
    print(f"   缺失模块: {e.name}")
    print("   安装命令: pip install aiohttp")
    ASYNC_AVAILABLE = False
    # 创建占位符避免后续代码报错
    asyncio = None
    aiohttp = None

class EnhancedNewsAnalyzer:
    def __init__(self):
        self.server_chan_key = os.getenv('SERVER_CHAN_KEY')
        self.gemini_api_key = os.getenv('GEMINI_API_KEY')
        self.forty_eight_hours_ago = datetime.now() - timedelta(hours=48)
        
        # 初始化新闻抓取器（传入百度翻译函数）
        self.news_fetcher = NewsFetcher(baidu_translate_func=self.baidu_translate)
        
        # 防御性检查：API密钥配置提醒
        if not self.gemini_api_key:
            print("⚠️  警告: 未配置 GEMINI_API_KEY 环境变量")
            print("   → 深度分析将使用备用关键词分析（功能受限）")
            print("   → 建议配置 Gemini API 以获得完整分析能力\n")
        
        if not self.server_chan_key:
            print("⚠️  警告: 未配置 SERVER_CHAN_KEY 环境变量")
            print("   → 微信推送功能将被禁用\n")
        
        baidu_appid = os.getenv('BAIDU_APPID')
        baidu_secret_key = os.getenv('BAIDU_SECRET_KEY')
        if not baidu_appid or not baidu_secret_key:
            print("⚠️  警告: 未配置百度翻译 API（BAIDU_APPID/BAIDU_SECRET_KEY）")
            print("   → 英文内容将不会被翻译为中文\n")
        
        # AI科技新闻源
        self.ai_news_sources = [
            {'name': 'Arxiv AI Papers', 'url': 'https://arxiv.org/list/cs.AI/recent', 'type': 'arxiv', 'category': 'ai_research'},
            # TechCrunch 和 VentureBeat 改为 HTML 解析（RSS 源不稳定）
            {'name': 'TechCrunch AI', 'url': 'https://techcrunch.com/category/artificial-intelligence/', 'type': 'html', 'category': 'tech'},
            {'name': 'Hacker News AI', 'url': 'https://hn.algolia.com/api/v1/search_by_date?tags=story&numericFilters=created_at_i>{}&query=AI', 'type': 'hn_api', 'category': 'community'},
            {'name': 'VentureBeat AI', 'url': 'https://venturebeat.com/ai/', 'type': 'html', 'category': 'tech'},
            {'name': 'The Verge AI', 'url': 'https://www.theverge.com/rss/ai-artificial-intelligence/index.xml', 'type': 'rss', 'category': 'tech'},
        ]
        
        # 多方面事实新闻源
        # 已替换所有失效 RSS 源
        self.fact_news_sources = [
            # 国内新闻（已验证可用的 RSS）
            {'name': '人民网', 'url': 'http://www.people.com.cn/rss/politics.xml', 'type': 'rss', 'category': 'china', 'lang': 'zh'},
            {'name': '中国新闻网', 'url': 'https://www.chinanews.com.cn/rss/scroll-news.xml', 'type': 'rss', 'category': 'china', 'lang': 'zh'},
            # 凤凰网改为 HTML 解析（RSS 源不稳定）
            {'name': '凤凰网资讯', 'url': 'https://news.ifeng.com/', 'type': 'html', 'category': 'china', 'lang': 'zh'},
            # 国际新闻（稳定 RSS）
            {'name': 'BBC中文', 'url': 'https://feeds.bbci.co.uk/zhongwen/simp/rss.xml', 'type': 'rss', 'category': 'world', 'lang': 'zh'},
            # FT中文网改为备用源
            {'name': 'FT中文网', 'url': 'https://www.ftchinese.com/', 'type': 'html', 'category': 'world', 'lang': 'zh'},
            {'name': '纽约时报中文', 'url': 'https://cn.nytimes.com/rss/', 'type': 'rss', 'category': 'world', 'lang': 'zh'},
            # 联合早报已移除（404错误）
            # TechCrunch AI - HTML解析（RSS 源不稳定）
            {'name': 'TechCrunch HTML', 'url': 'https://techcrunch.com/category/artificial-intelligence/', 'type': 'html', 'category': 'tech', 'lang': 'en'},
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
    
    def _get_headers(self, url=None):
        """生成随机请求头"""
        if UA_AVAILABLE and ua:
            user_agent = ua.random
        else:
            # 备用 User-Agent 列表
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
        
        # 特定网站添加 Referer
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
        from urllib.parse import urlparse
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            # 移除www前缀
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
        
        # 更新该域名的最后请求时间
        self.domain_delays[domain] = time.time()
    
    # ==================== 新增：百度翻译函数 ====================
    def baidu_translate(self, title, summary):
        """使用百度API翻译英文到中文，提供贴合实际的翻译，失败时返回标记"""
        appid = os.getenv('BAIDU_APPID')
        secret_key = os.getenv('BAIDU_SECRET_KEY')
        if not appid or not secret_key:
            print("⚠️ 未配置百度翻译密钥，跳过翻译")
            # 返回特殊标记表示未翻译
            return {
                'title': f"{title} (未翻译)",
                'summary': f"{summary} (未翻译)" if summary else "(未翻译)"
            }
        
        try:
            query = title + '\n' + summary if summary else title
            from_lang = 'en'
            to_lang = 'zh'
            salt = str(random.randint(32768, 65536))
            sign = hashlib.md5((appid + query + salt + secret_key).encode('utf-8')).hexdigest()
            
            url = 'http://api.fanyi.baidu.com/api/trans/vip/translate'
            params = {
                'q': query,
                'from': from_lang,
                'to': to_lang,
                'appid': appid,
                'salt': salt,
                'sign': sign
            }
            
            response = requests.get(url, params=params, timeout=10)
            result = response.json()
            
            if 'trans_result' in result:
                trans_result = result['trans_result'][0]['dst']
                parts = trans_result.split('\n')
                translated_title = parts[0].strip()
                translated_summary = parts[1].strip() if len(parts) > 1 else ''
                return {
                    'title': translated_title,
                    'summary': translated_summary
                }
            else:
                print(f"⚠️ 百度翻译失败: {result.get('error_msg', '未知错误')}")
                # 翻译失败也返回标记
                return {
                    'title': f"{title} (未翻译)",
                    'summary': f"{summary} (未翻译)" if summary else "(未翻译)"
                }
        except Exception as e:
            print(f"⚠️ 百度翻译请求失败: {e}")
            # 异常情况下也返回标记
            return {
                'title': f"{title} (未翻译)",
                'summary': f"{summary} (未翻译)" if summary else "(未翻译)"
            }
    
    # ==================== 新闻抓取方法（已迁移到 news_fetcher.py）====================
    def fetch_arxiv(self, source):
        """抓取Arxiv AI论文（委托给 news_fetcher 模块）"""
        articles = self.news_fetcher.fetch_arxiv(source)
        self.all_articles.extend(articles)
        self.ai_articles.extend(articles)
        return len(articles)
    
    async def fetch_rss_async(self, session, source, article_type='ai'):
        """异步RSS抓取方法（委托给 news_fetcher 模块）"""
        if not ASYNC_AVAILABLE:
            raise RuntimeError("异步功能不可用：请先安装 aiohttp (pip install aiohttp)")
        
        async_fetcher = AsyncNewsFetcher(baidu_translate_func=self.baidu_translate)
        articles = await async_fetcher.fetch_rss_async(session, source, article_type)
        
        self.all_articles.extend(articles)
        if article_type == 'ai':
            self.ai_articles.extend(articles)
        else:
            self.fact_articles.extend(articles)
        
        return len(articles)
    
    async def fetch_hackernews_async(self, session, source, article_type='ai'):
        """异步Hacker News抓取方法（委托给 news_fetcher 模块）"""
        # 异步 HN 抓取暂未实现，使用同步版本
        return self.fetch_hackernews(source, article_type)

    # ==================== 新增：抓取事实新闻 ====================
    def fetch_fact_news(self):
        """抓取多方面事实新闻"""
        print("\n📰 开始抓取多方面事实新闻（过去48小时）...")
        
        for source in self.fact_news_sources:
            print(f"  → {source['name']}")
            try:
                # 使用新闻抓取模块
                articles = self.news_fetcher.fetch_from_source(source, article_type='fact')
                self.all_articles.extend(articles)
                self.fact_articles.extend(articles)
                time.sleep(1)  # 礼貌延迟
            except Exception as e:
                print(f"    ❌ 抓取失败: {e}")
                continue
        
        print(f"✅ 事实新闻抓取完成！共获得 {len(self.fact_articles)} 篇")
        
        # 去重和筛选最重要的10篇
        unique_facts = []
        seen_ids = set()
        for article in self.fact_articles:
            if article['id'] not in seen_ids:
                unique_facts.append(article)
                seen_ids.add(article['id'])
        self.fact_articles = sorted(
            unique_facts, 
            key=lambda x: (x.get('importance', 5), datetime.strptime(x['time'], '%Y-%m-%d %H:%M') if x.get('time') else datetime.now()), 
            reverse=True
        )[:10]
    
    # ==================== 新闻抓取方法（已迁移到 news_fetcher.py）====================
    def fetch_rss(self, source, article_type='ai'):
        """通用RSS抓取方法（委托给 news_fetcher 模块）"""
        articles = self.news_fetcher.fetch_rss(source, article_type)
        self.all_articles.extend(articles)
        if article_type == 'ai':
            self.ai_articles.extend(articles)
        else:
            self.fact_articles.extend(articles)
        return len(articles)
    
    def fetch_hackernews(self, source, article_type='ai'):
        """通用Hacker News抓取方法（委托给 news_fetcher 模块）"""
        articles = self.news_fetcher.fetch_hackernews(source, article_type)
        self.all_articles.extend(articles)
        if article_type == 'ai':
            self.ai_articles.extend(articles)
        else:
            self.fact_articles.extend(articles)
        return len(articles)
    
    def fetch_html(self, source, article_type='fact'):
        """HTML页面解析方法（委托给 news_fetcher 模块）"""
        articles = self.news_fetcher.fetch_html(source, article_type)
        self.all_articles.extend(articles)
        if article_type == 'ai':
            self.ai_articles.extend(articles)
        else:
            self.fact_articles.extend(articles)
        return len(articles)
    
    def fetch_all_news(self):
        """抓取所有新闻"""
        print("📡 开始抓取AI科技新闻（过去48小时）...")
        for source in self.ai_news_sources:
            print(f"  → {source['name']}")
            try:
                # 使用新闻抓取模块
                articles = self.news_fetcher.fetch_from_source(source, article_type='ai')
                self.all_articles.extend(articles)
                self.ai_articles.extend(articles)
                time.sleep(1)
            except Exception as e:
                print(f"    ❌ 抓取失败: {e}")
        
        print(f"✅ AI新闻抓取完成！共获得 {len(self.ai_articles)} 篇")
    


    def fetch_arxiv_abstract(self, url):
        """从 arXiv 论文详情页提取完整摘要（使用 news_fetcher 模块）"""
        return self.news_fetcher.fetch_arxiv_abstract(url)

    def analyze_with_gemini(self, article):
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            print("  ⚠️  未配置 GEMINI_API_KEY，使用备用分析")
            return self._fallback_analysis(article)
    
        try:
            genai.configure(api_key=api_key)
            # 使用多模型降级策略
            models_to_try = [
                'gemini-2.0-flash',
                'gemini-1.5-flash',
                'gemini-1.5-pro',
                'gemini-2.0-flash-lite',
            ]
            
            model = None
            last_error = None
            for model_name in models_to_try:
                try:
                    test_model = genai.GenerativeModel(model_name)
                    # 测试模型是否可用
                    test_response = test_model.generate_content("test")
                    if test_response and test_response.text:
                        print(f"  ✓ 使用模型: {model_name}")
                        model = test_model
                        break
                except Exception as e:
                    last_error = e
                    continue
            
            if model is None:
                print(f"  ⚠️  所有 Gemini 模型均不可用，使用备用分析")
                if last_error:
                    print(f"     最后错误: {last_error}")
                return self._fallback_analysis(article)
    
            # 如果是ArXiv，优先获取真实摘要（已带缓存）
            full_abstract = ""
            if 'arxiv.org' in article['link']:
                full_abstract = self.fetch_arxiv_abstract(article['link'])
    
            prompt = f"""作为专业AI论文分析师，请分析以下论文：
    
    标题：{article['title']}
    来源：{article['source']}
    摘要：{full_abstract or article.get('summary', '暂无摘要')}
    
    请严格输出JSON：
    {{
      "content_summary": "150-250字中文摘要，提炼核心贡献、方法、结果",
      "content_tags": ["标签1", "标签2", ...],
      "importance_level": "高/中/低",
      "impact_scope": "多方面影响描述",
      "attention_reason": "结合创新、结果、局限的多角度理由",
      "key_points": ["要点1", "要点2", "要点3"]
    }}
    
    直接返回JSON，无多余文字。
    """
    
            response = model.generate_content(prompt)
            
            # 检查响应是否为空
            if not response or not response.text:
                print(f"  ⚠️  Gemini 返回空响应，使用备用分析")
                return self._fallback_analysis(article)
            
            text = response.text.strip()
            
            # 检查文本内容是否为空或太短
            if not text or len(text) < 10:
                print(f"  ⚠️  Gemini 返回内容过短 ({len(text)} 字符)，使用备用分析")
                return self._fallback_analysis(article)
            
            # 改进的 JSON 提取（使用更精确的正则）
            json_match = re.search(r'\{[^{}]*\}', text, re.DOTALL)
            if not json_match:
                # 尝试查找代码块中的 JSON
                code_block_match = re.search(r'```(?:json)?\s*\n(.*?)\n```', text, re.DOTALL)
                if code_block_match:
                    json_text = code_block_match.group(1).strip()
                    try:
                        analysis_result = json.loads(json_text)
                        if 'key_points' not in analysis_result:
                            analysis_result['key_points'] = analysis_result.get('content_tags', [])[:3]
                        return analysis_result
                    except json.JSONDecodeError:
                        pass
            
            if json_match:
                try:
                    analysis_result = json.loads(json_match.group(0))
                    # 确保 key_points 存在
                    if 'key_points' not in analysis_result:
                        analysis_result['key_points'] = analysis_result.get('content_tags', [])[:3]
                    return analysis_result
                except json.JSONDecodeError as e:
                    print(f"  ⚠️  Gemini JSON 解析失败: {e}")
                    return self._fallback_analysis(article)
            else:
                print(f"  ⚠️  Gemini返回格式异常，无法解析JSON，使用备用分析")
                return self._fallback_analysis(article)
        except json.JSONDecodeError as e:
            print(f"  ❌ Gemini分析JSON解析失败:")
            print(f"     错误类型: {type(e).__name__}")
            print(f"     错误信息: {str(e)}")
            print(f"     文章标题: {article.get('title', 'N/A')[:80]}")
            return self._fallback_analysis(article)
        except requests.exceptions.RequestException as e:
            print(f"  ❌ Gemini API网络请求失败:")
            print(f"     错误类型: {type(e).__name__}")
            print(f"     错误信息: {str(e)}")
            print(f"     文章标题: {article.get('title', 'N/A')[:80]}")
            return self._fallback_analysis(article)
        except Exception as e:
            error_msg = str(e)
            if "not found for API version" in error_msg or "404" in error_msg:
                print(f"  ❌ Gemini模型不可用错误:")
                print(f"     错误信息: {error_msg}")
                print(f"     可能的解决方案:")
                print(f"     1. 尝试使用 'gemini-1.5-flash' 或 'gemini-1.5-pro'")
                print(f"     2. 检查Google AI Studio中的可用模型列表")
                print(f"     3. 更新google-generativeai库: pip install --upgrade google-generativeai")
                print(f"     4. 查看API版本是否为最新 (建议使用v1而非v1beta)")
            else:
                print(f"  ❌ Gemini分析发生未预期错误:")
                print(f"     错误类型: {type(e).__name__}")
                print(f"     错误信息: {str(e)}")
                print(f"     文章链接: {article.get('link', 'N/A')}")
                print(f"     文章标题: {article.get('title', 'N/A')[:80]}")
                import traceback
                print(f"     堆栈跟踪:\n{traceback.format_exc()}")
            return self._fallback_analysis(article)
        
    def _fallback_analysis(self, article):
        """备用关键词分析，当 Gemini 失败时使用"""
        text = f"{article['title']} {article.get('summary', '')}".lower()
        
        tags = []
        
        # 政治相关
        if any(word in text for word in ['politics', 'government', 'policy', '政治', '政府', '政策']):
            tags.append('政治')
        
        # 经济相关
        if any(word in text for word in ['economy', 'financial', 'market', '经济', '金融', '市场']):
            tags.append('经济')
        
        # 科技相关
        if any(word in text for word in ['technology', 'tech', 'digital', '科技', '技术', '数字化']):
            tags.append('科技')
        
        # 健康医疗
        if any(word in text for word in ['health', 'medical', '疫情', '疫苗', '健康', '医疗']):
            tags.append('健康')
        
        # 环境生态
        if any(word in text for word in ['environment', 'climate', '环保', '气候', '环境', '生态']):
            tags.append('环境')
        
        # AI 特定关键词（扩展）
        ai_keywords = [
            'ai', 'llm', 'gpt', 'transformer', '人工智能', '大模型', '生成式ai',
            'reasoning', '推理', 'chain of thought', '思维链', 'cot',
            'routing', '路由', 'router', '分发',
            'agent', '智能体', '自主代理',
            'rlhf', '人类反馈强化学习', 'reinforcement learning',
            'fine-tuning', '微调', 'adapter', '适配器',
            'multimodal', '多模态', 'vision', '图像', 'audio', '音频',
            'embedding', '嵌入', 'vector', '向量',
            'attention', '注意力', 'self-attention', '自注意力',
            'few-shot', '少样本', 'zero-shot', '零样本',
            'prompt', '提示词', 'instruction', '指令',
            'benchmark', '基准测试', 'evaluation', '评估',
            'moe', '混合专家', 'sparse', '稀疏',
            'diffusion', '扩散模型', 'stable diffusion',
            'rl', '强化学习', 'q-learning',
            'nlp', '自然语言处理', 'computer vision', '计算机视觉',
            'robotics', '机器人', 'autonomous', '自动驾驶',
            'ethics', '伦理', 'bias', '偏见', 'fairness', '公平性'
        ]
        
        if any(word in text for word in ai_keywords):
            tags.append('AI相关')
        
        # 默认标签
        if not tags:
            tags = ['综合新闻']
        
        return {
            'content_summary': "暂无详细摘要",
            'content_tags': tags,
            'importance_level': '中',
            'impact_scope': '广泛关注',
            'attention_reason': '值得关注的新闻报道',
            'key_points': tags
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
            analysis = self.analyze_with_gemini(article)
            
            # 如果有翻译，使用翻译
            title_display = article.get('title_translated', article['title'])
            
            analysis_text = f"""## 📊 {title_display}

**来源**: {article['source']} | **时间**: {article.get('time', 'N/A')}
**AI分析模型**: 🤖 Gemini

**🔗 原文链接**: {article['link']}

**📝 内容摘要**:
{article.get('summary_translated', article.get('summary', '暂无详细摘要'))}

**🏷️ 内容标签**: {', '.join(analysis['content_tags'])}

**✨ 重要性**: {analysis['importance_level'].upper()}

**📈 影响范围**: {analysis['impact_scope']}

**💡 关注理由**: {analysis['attention_reason']}

**🔬 核心要点**:
{chr(10).join(f'- {point}' for point in analysis['key_points'][:3])}

---
"""
            analyses.append({
                'article': article,
                'analysis': analysis,
                'text': analysis_text
            })
            
            if self.gemini_api_key:
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
    
    def format_fact_news_section(self):
        """格式化事实新闻部分，按中文/国际分组展示"""
        if not self.fact_articles:
            return ""

        section = f"""
## 🌍 48小时事实资讯速览 ({len(self.fact_articles)}篇)

**新闻来源**: {', '.join(set([a['source'] for a in self.fact_articles[:10]]))}

"""

        # 按语言/地区分组：中文 vs 英文
        cn_articles = []
        intl_articles = []
        
        for article in self.fact_articles[:10]:  # 最多10篇
            lang = article.get('lang', 'en')
            if lang == 'zh':
                cn_articles.append(article)
            else:
                intl_articles.append(article)
        
        # 1. 中文新闻区
        if cn_articles:
            section += f"\n### 🇨🇳 中文新闻\n\n"
            for i, article in enumerate(cn_articles, 1):
                emoji = "⭐️" if article.get('importance', 0) > 7 else "📍"
                title = article['title']  # 中文新闻直接显示原标题
                source = article['source']
                
                section += f"{i}. {emoji} **{title}**\n"
                section += f"   📍 {source}"
                
                # 添加互动数据（如果有）
                if article.get('points', 0) > 0:
                    section += f" | 👍 {article['points']}"
                if article.get('comments', 0) > 0:
                    section += f" | 💬 {article['comments']}"
                
                section += f"\n   🔗 [阅读原文]({article['link']})\n\n"
        
        # 2. 国际新闻区（英文，显示翻译+原文）
        if intl_articles:
            section += f"\n### 🌐 国际新闻\n\n"
            for i, article in enumerate(intl_articles, 1):
                emoji = "⭐️" if article.get('importance', 0) > 7 else "📍"
                
                # 优先显示翻译后的标题
                title_cn = article.get('title_translated', article['title'])
                title_en = article['title']
                source = article['source']
                
                # 格式：翻译标题 (Original: 英文原文)
                section += f"{i}. {emoji} **{title_cn}**"
                if 'title_translated' in article and title_cn != title_en:
                    section += f" (Original: {title_en})"
                section += "\n"
                
                section += f"   📍 {source}"
                
                # 添加互动数据（如果有）
                if article.get('points', 0) > 0:
                    section += f" | 👍 {article['points']}"
                if article.get('comments', 0) > 0:
                    section += f" | 💬 {article['comments']}"
                
                section += f"\n   🔗 [阅读原文]({article['link']})\n\n"
        
        # 添加精选事实新闻
        if self.featured_fact:
            featured_title = self.featured_fact.get('title_translated', self.featured_fact['title'])
            featured_summary = self.featured_fact.get('summary_translated', self.featured_fact.get('summary', '点击链接查看详情'))
            orig_title = self.featured_fact['title'] if 'title_translated' in self.featured_fact else ''
            orig_summary = self.featured_fact.get('summary', '') if 'summary_translated' in self.featured_fact else ''
            
            orig_title_part = "(Original: " + orig_title + ")" if orig_title else ""
            orig_summary_part = "\n\nOriginal Summary: " + orig_summary if orig_summary else ""
            
            section += f"""
## 📰 今日事实精选

**{featured_title}** {orig_title_part}

**来源**: {self.featured_fact['source']} | **时间**: {self.featured_fact.get('time', '今日')}

**摘要**: {featured_summary}{orig_summary_part}

**🔗 深度阅读**: {self.featured_fact['link']}
"""
        
        section += f"""
---
*事实新闻来自 {len(set([a['source'] for a in self.fact_articles]))} 个国内外权威媒体*
*每日筛选过去48小时最重要新闻，保持信息广度与深度*
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
            # 按类别分组展示AI新闻
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
- **分析支持**: Gemini
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
        
        if len(report) > 20000:
            report = report[:20000] + "\n\n...（报告过长，已截断）"
        
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
    
    async def run_async(self):
        """异步主执行函数（带异常处理）"""
        if not ASYNC_AVAILABLE:
            raise RuntimeError("异步功能不可用：请先安装 aiohttp (pip install aiohttp)")
        
        print("=" * 70)
        print("📊 增强版资讯分析系统启动 (异步模式)")
        print(f"📅 执行时间: {datetime.now()}")
        print("=" * 70)
        
        try:
            # 1. 异步抓取AI新闻
            await self.fetch_all_news_async()
            
            # 2. 异步抓取事实新闻
            await self.fetch_fact_news_async()
            
            if not self.all_articles:
                print("❌ 未抓取到任何文章，程序退出")
                return self._generate_error_report("未抓取到任何新闻文章"), "抓取失败"
            
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
            
        except KeyboardInterrupt:
            print("\n⚠️ 用户中断执行")
            return self._generate_error_report("用户手动中断执行"), "执行中断"
            
        except Exception as e:
            print(f"\n❌ 执行过程中发生错误: {e}")
            import traceback
            print(f"详细错误信息:\n{traceback.format_exc()}")
            return self._generate_error_report(f"执行异常: {str(e)}"), "执行失败"
    
    def run(self):
        """主执行函数（带异常处理）"""
        print("=" * 70)
        print("📊 增强版资讯分析系统启动")
        print(f"📅 执行时间: {datetime.now()}")
        print("=" * 70)
        
        try:
            # 1. 抓取AI新闻
            self.fetch_all_news()
            
            # 2. 抓取事实新闻
            self.fetch_fact_news()
            
            if not self.all_articles:
                print("❌ 未抓取到任何文章，程序退出")
                return self._generate_error_report("未抓取到任何新闻文章"), "抓取失败"
            
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
            
        except KeyboardInterrupt:
            print("\n⚠️ 用户中断执行")
            return self._generate_error_report("用户手动中断执行"), "执行中断"
            
        except Exception as e:
            print(f"\n❌ 执行过程中发生错误: {e}")
            import traceback
            print(f"详细错误信息:\n{traceback.format_exc()}")
            return self._generate_error_report(f"执行异常: {str(e)}"), "执行失败"
    
    def _generate_error_report(self, error_message):
        """生成错误情况下的简化报告"""
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M')
        
        error_report = f"""# 📊 资讯分析报告 (执行失败)

## ⚠️ 执行状态
- **状态**: 执行失败
- **错误信息**: {error_message}
- **执行时间**: {current_time}

## 📈 当前数据统计
- **AI科技资讯**: {len(self.ai_articles)} 篇
- **事实资讯**: {len(self.fact_articles)} 篇
- **深度分析**: {len(self.deep_analyses)} 篇

## 📋 已获取内容预览
"""
        
        # 添加已成功抓取的文章预览
        if self.ai_articles:
            error_report += f"\n### 🤖 已获取的AI资讯 ({len(self.ai_articles)}篇)\n"
            for i, article in enumerate(self.ai_articles[:5], 1):  # 最多显示5篇
                title_display = article.get('title_translated', article['title'])
                error_report += f"{i}. {title_display}\n"
                error_report += f"   📍 {article['source']} | 🔗 [原文链接]({article['link']})\n\n"
        
        if self.fact_articles:
            error_report += f"\n### 🌍 已获取的事实资讯 ({len(self.fact_articles)}篇)\n"
            for i, article in enumerate(self.fact_articles[:5], 1):  # 最多显示5篇
                title_display = article.get('title_translated', article['title'])
                error_report += f"{i}. {title_display}\n"
                error_report += f"   📍 {article['source']} | 🔗 [原文链接]({article['link']})\n\n"
        
        error_report += f"""
---

## 🛠️ 建议解决方案
1. 检查网络连接是否正常
2. 确认各新闻源是否可访问
3. 验证API密钥配置是否正确
4. 查看详细错误日志定位问题

*报告生成时间: {current_time}*
"""
        
        return error_report

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='AI科技资讯分析系统')
    parser.add_argument('--use-async', action='store_true', help='使用异步模式加速抓取')
    args = parser.parse_args()
    
    analyzer = EnhancedNewsAnalyzer()
    
    if args.use_async:
        # 异步模式
        if not ASYNC_AVAILABLE:
            print("❌ 异步模式不可用：请先安装 aiohttp")
            print("   安装命令: pip install aiohttp")
            print("   或使用同步模式: python tech_news_ai_with_facts.py")
            return
        
        print("🚀 启动异步模式...")
        report, title = asyncio.run(analyzer.run_async())
    else:
        # 同步模式（默认）
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
