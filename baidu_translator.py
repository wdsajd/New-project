#!/usr/bin/env python3
"""
百度翻译API模块
支持中英文互译，专门用于新闻资讯翻译
"""

import os
import json
import hashlib
import random
import requests
import logging
from typing import Optional, Dict, Union
from urllib.parse import quote

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BaiduTranslator:
    def __init__(self, app_id: str = None, secret_key: str = None):
        """
        初始化百度翻译API
        
        参数:
            app_id: 百度翻译API的APP ID
            secret_key: 百度翻译API的密钥
        """
        # 优先使用传入的参数，其次从环境变量获取
        self.app_id = app_id or os.getenv('BAIDU_TRANSLATE_APPID')
        self.secret_key = secret_key or os.getenv('BAIDU_TRANSLATE_SECRET')
        
        # API端点
        self.api_url = "https://fanyi-api.baidu.com/api/trans/vip/translate"
        
        # 语言代码映射
        self.lang_codes = {
            'auto': 'auto',    # 自动检测
            'zh': 'zh',        # 中文
            'en': 'en',        # 英语
            'jp': 'jp',        # 日语
            'kor': 'kor',      # 韩语
            'fra': 'fra',      # 法语
            'de': 'de',        # 德语
            'ru': 'ru',        # 俄语
        }
        
        # 验证配置
        self._validate_config()
    
    def _validate_config(self):
        """验证必要的配置"""
        if not self.app_id or not self.secret_key:
            logger.warning("⚠️ 百度翻译API配置不完整，翻译功能将不可用")
            logger.info("请设置以下环境变量：")
            logger.info("1. BAIDU_TRANSLATE_APPID: 百度翻译APP ID")
            logger.info("2. BAIDU_TRANSLATE_SECRET: 百度翻译密钥")
            return False
        return True
    
    def _generate_sign(self, text: str, salt: str) -> str:
        """
        生成百度翻译API所需的签名
        
        签名公式：sign = md5(appid + q + salt + secret_key)
        """
        sign_str = self.app_id + text + salt + self.secret_key
        return hashlib.md5(sign_str.encode('utf-8')).hexdigest()
    
    def detect_language(self, text: str) -> str:
        """
        检测文本语言（简化版）
        百度翻译API自带自动检测功能，这里做简单判断
        """
        if not text.strip():
            return 'auto'
        
        # 简单中英文检测
        zh_count = sum(1 for char in text if '\u4e00' <= char <= '\u9fff')
        en_ratio = sum(1 for char in text if 'a' <= char.lower() <= 'z') / max(len(text), 1)
        
        if zh_count / len(text) > 0.3:
            return 'zh'
        elif en_ratio > 0.5:
            return 'en'
        else:
            return 'auto'
    
    def translate_text(
        self, 
        text: str, 
        from_lang: str = 'auto', 
        to_lang: str = 'zh'
    ) -> Optional[str]:
        """
        翻译单条文本
        
        参数:
            text: 待翻译文本
            from_lang: 源语言代码
            to_lang: 目标语言代码
            
        返回:
            翻译后的文本，失败返回None
        """
        if not text or not text.strip():
            return text
        
        # 检查配置
        if not self.app_id or not self.secret_key:
            logger.error("❌ 百度翻译API未配置，无法翻译")
            return None
        
        # 自动检测语言
        if from_lang == 'auto':
            from_lang = self.detect_language(text)
        
        # 如果是中文且目标语言也是中文，直接返回
        if from_lang == 'zh' and to_lang == 'zh':
            return text
        
        try:
            # 准备参数
            salt = str(random.randint(32768, 65536))
            sign = self._generate_sign(text, salt)
            
            # 构建请求参数
            params = {
                'q': text,
                'from': from_lang,
                'to': to_lang,
                'appid': self.app_id,
                'salt': salt,
                'sign': sign
            }
            
            logger.debug(f"翻译请求: {text[:50]}... ({from_lang}->{to_lang})")
            
            # 发送请求
            response = requests.get(
                self.api_url, 
                params=params,
                timeout=10,
                headers={'Content-Type': 'application/x-www-form-urlencoded'}
            )
            
            response.raise_for_status()
            result = response.json()
            
            # 检查错误
            if 'error_code' in result:
                error_msg = result.get('error_msg', '未知错误')
                logger.error(f"❌ 翻译API错误 {result['error_code']}: {error_msg}")
                return None
            
            # 提取翻译结果
            if 'trans_result' in result:
                translated = result['trans_result'][0]['dst']
                logger.debug(f"翻译结果: {translated[:50]}...")
                return translated
            else:
                logger.error(f"❌ 翻译响应格式异常: {result}")
                return None
                
        except requests.exceptions.Timeout:
            logger.error("❌ 翻译请求超时")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ 翻译网络错误: {e}")
            return None
        except Exception as e:
            logger.error(f"❌ 翻译处理异常: {e}")
            return None
    
    def translate_news_item(
        self, 
        title: str, 
        summary: str = "",
        force_translate: bool = False
    ) -> Dict[str, Union[str, Dict]]:
        """
        翻译新闻条目（标题和摘要）
        
        参数:
            title: 新闻标题
            summary: 新闻摘要（可选）
            force_translate: 是否强制翻译（即使检测为中文）
            
        返回:
            包含原始内容和翻译内容的字典
        """
        result = {
            'original': {'title': title, 'summary': summary},
            'translated': {'title': '', 'summary': ''},
            'language': self.detect_language(title + summary)
        }
        
        # 检查是否需要翻译
        if not force_translate and result['language'] == 'zh':
            result['translated']['title'] = title
            result['translated']['summary'] = summary
            result['note'] = '原文为中文，未翻译'
            return result
        
        # 翻译标题
        if title:
            translated_title = self.translate_text(title, 'auto', 'zh')
            if translated_title:
                result['translated']['title'] = translated_title
                logger.info(f"✅ 标题翻译完成: {title[:30]}... → {translated_title[:30]}...")
        
        # 翻译摘要
        if summary:
            # 如果摘要太长，分批翻译
            if len(summary) > 2000:
                logger.warning(f"⚠️ 摘要过长 ({len(summary)}字符)，将分批次翻译")
                translated_summary = self._translate_long_text(summary)
            else:
                translated_summary = self.translate_text(summary, 'auto', 'zh')
            
            if translated_summary:
                result['translated']['summary'] = translated_summary
                logger.info(f"✅ 摘要翻译完成: {summary[:50]}...")
        
        return result
    
    def _translate_long_text(self, text: str, chunk_size: int = 1500) -> str:
        """
        翻译长文本（分批处理）
        
        参数:
            text: 长文本
            chunk_size: 每批字符数
            
        返回:
            合并后的翻译结果
        """
        # 按句子分割（简单实现）
        sentences = []
        current = ""
        
        for char in text:
            current += char
            if char in '.!?。！？' and len(current) > 50:
                sentences.append(current.strip())
                current = ""
        
        if current:
            sentences.append(current.strip())
        
        # 分批翻译
        translated_parts = []
        current_batch = ""
        
        for sentence in sentences:
            if len(current_batch) + len(sentence) > chunk_size:
                # 翻译当前批次
                translated = self.translate_text(current_batch, 'auto', 'zh')
                if translated:
                    translated_parts.append(translated)
                current_batch = sentence
            else:
                if current_batch:
                    current_batch += " " + sentence
                else:
                    current_batch = sentence
        
        # 翻译最后一批
        if current_batch:
            translated = self.translate_text(current_batch, 'auto', 'zh')
            if translated:
                translated_parts.append(translated)
        
        return " ".join(translated_parts)
    
    def format_bilingual_display(
        self, 
        original_title: str, 
        translated_title: str,
        original_summary: str = "",
        translated_summary: str = ""
    ) -> str:
        """
        格式化双语显示（用于报告）
        
        返回:
            格式化后的HTML/文本内容
        """
        if not translated_title or original_title == translated_title:
            return original_title
        
        # HTML格式（用于邮件报告）
        html_format = f"""
        <div class="bilingual-item">
            <div class="original">
                <span class="lang-tag">EN</span> {original_title}
            </div>
            <div class="translated">
                <span class="lang-tag">中</span> {translated_title}
            </div>
        """
        
        if original_summary and translated_summary and original_summary != translated_summary:
            html_format += f"""
            <div class="summary-section">
                <div class="original-summary">
                    <small>{original_summary[:150]}...</small>
                </div>
                <div class="translated-summary">
                    <small>{translated_summary[:150]}...</small>
                </div>
            </div>
            """
        
        html_format += "</div>"
        
        # 纯文本格式（备用）
        text_format = f"""
        【原文】{original_title}
        【翻译】{translated_title}
        """
        
        if original_summary and translated_summary and original_summary != translated_summary:
            text_format += f"""
        【原文摘要】{original_summary[:100]}...
        【翻译摘要】{translated_summary[:100]}...
            """
        
        return {
            'html': html_format,
            'text': text_format,
            'has_translation': translated_title != original_title
        }

# 全局翻译器实例（单例模式）
_translator_instance = None

def get_translator() -> BaiduTranslator:
    """获取翻译器实例"""
    global _translator_instance
    if _translator_instance is None:
        _translator_instance = BaiduTranslator()
    return _translator_instance

def translate_news(title: str, summary: str = "") -> Dict:
    """
    便捷函数：翻译新闻
    
    参数:
        title: 新闻标题
        summary: 新闻摘要
        
    返回:
        翻译结果字典
    """
    translator = get_translator()
    return translator.translate_news_item(title, summary)

# 测试函数
if __name__ == "__main__":
    # 测试配置
    test_config = {
        'BAIDU_TRANSLATE_APPID': '你的APP_ID',
        'BAIDU_TRANSLATE_SECRET': '你的密钥'
    }
    
    # 设置环境变量
    for key, value in test_config.items():
        os.environ[key] = value
    
    # 创建翻译器
    translator = BaiduTranslator()
    
    # 测试翻译
    test_cases = [
        ("Artificial Intelligence is changing the world", "AI technology is advancing rapidly."),
        ("Global climate summit reaches new agreement", "World leaders agree on climate targets."),
        ("这是一条中文新闻标题", "这是中文摘要内容。"),
    ]
    
    for title, summary in test_cases:
        print(f"\n{'='*50}")
        print(f"测试翻译: {title}")
        print(f"{'='*50}")
        
        result = translator.translate_news_item(title, summary)
        
        print(f"检测语言: {result['language']}")
        print(f"原始标题: {result['original']['title']}")
        print(f"翻译标题: {result['translated']['title']}")
        
        if result['original']['summary']:
            print(f"原始摘要: {result['original']['summary'][:100]}...")
            print(f"翻译摘要: {result['translated']['summary'][:100]}...")
        
        formatted = translator.format_bilingual_display(
            result['original']['title'],
            result['translated']['title'],
            result['original']['summary'],
            result['translated']['summary']
        )
        
        print(f"\n格式化显示（文本）:")
        print(formatted['text'])
