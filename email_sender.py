#!/usr/bin/env python3
"""
安全的邮件发送模块
使用环境变量存储敏感信息，避免密钥泄露
"""

import os
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SecureEmailSender:
    def __init__(self):
        """从环境变量初始化邮件配置"""
        # 从环境变量获取配置，有默认值但关键信息必须通过环境变量传入
        self.smtp_server = os.getenv('SMTP_SERVER', 'smtp.qq.com')
        self.smtp_port = int(os.getenv('SMTP_PORT', '465'))
        self.sender_email = os.getenv('SENDER_EMAIL')
        self.sender_pass = os.getenv('SENDER_PASSWORD')  # 重要：使用通用名称而非特定服务名
        self.receiver_email = os.getenv('RECEIVER_EMAIL')
        
        # 验证必要配置
        self._validate_config()
        
        # 常见邮箱服务商的端口映射（供参考）
        self.email_service_ports = {
            'qq.com': (465, 587),
            '163.com': (465, 994),
            'gmail.com': (465, 587),
            'outlook.com': (587, 25),
            'yahoo.com': (465, 587)
        }
    
    def _validate_config(self):
        """验证必要的配置是否存在"""
        missing_configs = []
        
        if not self.sender_email:
            missing_configs.append('SENDER_EMAIL')
        if not self.sender_pass:
            missing_configs.append('SENDER_PASSWORD')
        if not self.receiver_email:
            missing_configs.append('RECEIVER_EMAIL')
        
        if missing_configs:
            error_msg = f"缺少必要的邮件配置: {', '.join(missing_configs)}"
            logger.error(error_msg)
            logger.info("请在GitHub Secrets中设置以下环境变量:")
            logger.info("1. SENDER_EMAIL: 发件人邮箱")
            logger.info("2. SENDER_PASSWORD: 邮箱授权码/应用密码")
            logger.info("3. RECEIVER_EMAIL: 收件人邮箱")
            logger.info("可选: SMTP_SERVER, SMTP_PORT")
            raise ValueError(error_msg)
    
    def _get_email_service_hint(self):
        """根据邮箱域名提供配置提示"""
        if not self.sender_email:
            return ""
        
        domain = self.sender_email.split('@')[-1].lower()
        
        hints = {
            'qq.com': {
                'server': 'smtp.qq.com',
                'port': 465,
                'tip': '需在QQ邮箱设置中开启SMTP服务并获取授权码'
            },
            '163.com': {
                'server': 'smtp.163.com',
                'port': 465,
                'tip': '需在163邮箱设置中开启SMTP服务并获取授权码'
            },
            'gmail.com': {
                'server': 'smtp.gmail.com',
                'port': 587,
                'tip': '需开启两步验证并生成应用专用密码'
            }
        }
        
        return hints.get(domain, {})
    
    def format_html_email(self, subject, content, style='tech'):
        """格式化HTML邮件内容"""
        
        # 不同的样式模板
        styles = {
            'tech': """
                <style>
                    body { font-family: 'Segoe UI', Arial, sans-serif; line-height: 1.6; color: #333; max-width: 800px; margin: 0 auto; padding: 20px; }
                    .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 10px 10px 0 0; }
                    .content { background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; border: 1px solid #e0e0e0; }
                    h1 { margin: 0; font-size: 24px; }
                    h2 { color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px; }
                    h3 { color: #34495e; }
                    .news-item { background: white; margin: 15px 0; padding: 15px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
                    .meta { color: #7f8c8d; font-size: 12px; margin-top: 10px; }
                    .footer { text-align: center; margin-top: 30px; padding-top: 20px; border-top: 1px solid #eee; color: #95a5a6; font-size: 12px; }
                    .tag { display: inline-block; background: #e74c3c; color: white; padding: 2px 8px; border-radius: 12px; font-size: 12px; margin-right: 5px; }
                    .link { color: #3498db; text-decoration: none; }
                    .link:hover { text-decoration: underline; }
                    pre { background: #2c3e50; color: #ecf0f1; padding: 15px; border-radius: 5px; overflow-x: auto; }
                    code { background: #f8f8f8; padding: 2px 4px; border-radius: 3px; font-family: 'Courier New', monospace; }
                </style>
            """,
            'simple': """
                <style>
                    body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
                    h1 { color: #2c3e50; }
                    h2 { color: #34495e; }
                    .news-item { margin: 20px 0; padding: 15px; background: #f8f9fa; border-left: 4px solid #3498db; }
                    .footer { margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd; color: #7f8c8d; font-size: 12px; }
                </style>
            """
        }
        
        html_template = f"""
        <!DOCTYPE html>
        <html lang="zh-CN">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{subject}</title>
            {styles.get(style, styles['simple'])}
        </head>
        <body>
            <div class="header">
                <h1>📰 {subject}</h1>
                <div class="meta">生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div>
            </div>
            
            <div class="content">
                {content}
            </div>
            
            <div class="footer">
                <p>本邮件由 GitHub Actions 自动生成并发送</p>
                <p>🤖 自动资讯系统 | 每日更新</p>
            </div>
        </body>
        </html>
        """
        
        return html_template
    
    def send_email(self, subject, content, content_type='html', style='tech'):
        """
        发送邮件
        
        参数:
            subject: 邮件主题
            content: 邮件内容
            content_type: 'html' 或 'plain'
            style: 邮件样式 ('tech' 或 'simple')
        """
        try:
            # 创建邮件
            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = self.sender_email
            message["To"] = self.receiver_email
            message["Date"] = datetime.now().strftime('%a, %d %b %Y %H:%M:%S %z')
            
            # 添加纯文本版本（备用）
            text_part = MIMEText(content if content_type == 'plain' else 
                                "请使用支持HTML的邮件客户端查看此邮件。", "plain", "utf-8")
            message.attach(text_part)
            
            # 添加HTML版本
            if content_type == 'html':
                html_content = self.format_html_email(subject, content, style)
                html_part = MIMEText(html_content, "html", "utf-8")
                message.attach(html_part)
            else:
                html_part = MIMEText(content, "plain", "utf-8")
                message.attach(html_part)
            
            # 创建SSL安全连接
            context = ssl.create_default_context()
            
            logger.info(f"正在连接邮件服务器: {self.smtp_server}:{self.smtp_port}")
            
            # 根据端口选择连接方式
            if self.smtp_port == 465:
                with smtplib.SMTP_SSL(self.smtp_server, self.smtp_port, context=context) as server:
                    server.login(self.sender_email, self.sender_pass)
                    server.send_message(message)
            else:
                with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                    server.starttls(context=context)
                    server.login(self.sender_email, self.sender_pass)
                    server.send_message(message)
            
            logger.info(f"✅ 邮件发送成功！主题: {subject}")
            logger.info(f"   发件人: {self.sender_email}")
            logger.info(f"   收件人: {self.receiver_email}")
            return True
            
        except smtplib.SMTPAuthenticationError:
            logger.error("❌ 邮件认证失败，请检查邮箱和授权码")
            logger.info("💡 提示:")
            service_hint = self._get_email_service_hint()
            if service_hint:
                logger.info(f"   - 确保已开启SMTP服务")
                logger.info(f"   - 使用正确的授权码（不是邮箱密码）")
                logger.info(f"   - {service_hint.get('tip', '')}")
            return False
            
        except Exception as e:
            logger.error(f"❌ 邮件发送失败: {str(e)}")
            return False

def send_daily_report_via_email(report_content, subject_prefix="每日资讯报告"):
    """
    发送每日报告的便捷函数
    """
    try:
        # 初始化邮件发送器
        mailer = SecureEmailSender()
        
        # 生成邮件主题
        current_date = datetime.now().strftime('%Y年%m月%d日')
        subject = f"{subject_prefix} - {current_date}"
        
        # 发送邮件
        success = mailer.send_email(
            subject=subject,
            content=report_content,
            content_type='html',
            style='tech'
        )
        
        return success
        
    except Exception as e:
        logger.error(f"发送报告失败: {e}")
        return False

# 测试函数（仅在直接运行时执行）
if __name__ == "__main__":
    # 测试配置（本地测试时使用，GitHub Actions中不执行）
    test_config = {
        'SMTP_SERVER': 'smtp.qq.com',
        'SMTP_PORT': '465',
        'SENDER_EMAIL': 'test@example.com',
        'SENDER_PASSWORD': 'your_password',
        'RECEIVER_EMAIL': 'receiver@example.com'
    }
    
    # 设置环境变量用于测试
    for key, value in test_config.items():
        os.environ[key] = value
    
    # 测试发送
    try:
        mailer = SecureEmailSender()
        test_content = """
        <h2>📋 测试邮件</h2>
        <p>这是一封测试邮件，用于验证邮件发送功能是否正常。</p>
        <div class="news-item">
            <h3>测试新闻标题</h3>
            <p>测试新闻内容摘要...</p>
            <div class="meta">来源: 测试源 | 时间: 2024-01-15</div>
        </div>
        """
        
        success = mailer.send_email(
            subject="📧 邮件功能测试",
            content=test_content,
            content_type='html'
        )
        
        if success:
            print("✅ 测试邮件发送成功！")
        else:
            print("❌ 测试邮件发送失败")
            
    except Exception as e:
        print(f"❌ 测试过程中出错: {e}")
