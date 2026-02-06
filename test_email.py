#!/usr/bin/env python3
import os
import sys

# 设置环境变量（仅用于本地测试）
os.environ['SMTP_SERVER'] = 'smtp.qq.com'
os.environ['SMTP_PORT'] = '465'
os.environ['SENDER_EMAIL'] = '你的邮箱@qq.com'
os.environ['SENDER_PASSWORD'] = '你的授权码'
os.environ['RECEIVER_EMAIL'] = '接收邮箱@qq.com'

# 导入并测试
from email_sender import send_daily_report_via_email

# 测试内容
test_report = """
<h2>本地测试邮件</h2>
<p>如果收到此邮件，说明邮件配置正确！</p>
<ul>
    <li>✅ SMTP服务器连接正常</li>
    <li>✅ 邮箱认证成功</li>
    <li>✅ 邮件发送功能正常</li>
</ul>
"""

if __name__ == "__main__":
    print("开始发送测试邮件...")
    success = send_daily_report_via_email(test_report, "测试邮件")
    
    if success:
        print("✅ 测试成功！请检查收件箱。")
        sys.exit(0)
    else:
        print("❌ 测试失败，请检查配置。")
        sys.exit(1)
