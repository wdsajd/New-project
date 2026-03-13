#!/usr/bin/env python3
"""
测试memory-merger技能的模拟脚本
"""

import os
import re

def read_file(filepath):
    """读取文件内容"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return None

def analyze_memory_file(content):
    """分析记忆文件内容"""
    print("📋 分析记忆文件内容...")
    
    # 提取记忆部分
    memories = []
    current_memory = None
    
    lines = content.split('\n')
    for line in lines:
        # 查找记忆标题
        if line.startswith('## Memory '):
            if current_memory:
                memories.append(current_memory)
            current_memory = {'title': line, 'content': []}
        elif current_memory and line.strip():
            current_memory['content'].append(line)
    
    if current_memory:
        memories.append(current_memory)
    
    print(f"找到 {len(memories)} 个记忆片段")
    for i, memory in enumerate(memories, 1):
        title = memory['title'].replace('## ', '')
        print(f"  {i}. {title}")
    
    return memories

def merge_memories(memory_content, instruction_content):
    """模拟合并记忆"""
    print("\n🔄 模拟合并过程...")
    
    # 简单的合并逻辑
    merged = instruction_content
    
    # 在指令文件末尾添加记忆内容
    if "## Merged Memories" not in merged:
        merged += "\n\n## Merged Memories\n"
    
    # 提取记忆的核心内容（去掉标题）
    memory_lines = memory_content.split('\n')
    for line in memory_lines:
        if line.startswith('## Memory '):
            # 将记忆标题转换为普通标题
            line = line.replace('Memory ', '')
            merged += f"\n{line}\n"
        elif line.strip() and not line.startswith('---'):
            merged += f"{line}\n"
    
    return merged

def test_memory_merger():
    """主测试函数"""
    print("🧪 开始测试memory-merger技能")
    print("=" * 50)
    
    # 读取文件
    memory_file = "test-memory-domain/test-memory.instructions.md"
    instruction_file = "test-memory-domain/test.instructions.md"
    
    memory_content = read_file(memory_file)
    instruction_content = read_file(instruction_file)
    
    if not memory_content:
        print("❌ 找不到记忆文件")
        return
    
    print("✅ 找到记忆文件")
    
    if not instruction_content:
        print("⚠️  找不到指令文件，将创建新文件")
        instruction_content = "---\nname: test\ndescription: Merged instructions\n---\n\n# Test Domain Instructions\n"
    
    # 分析记忆文件
    memories = analyze_memory_file(memory_content)
    
    # 模拟合并
    print("\n📝 模拟用户输入 'go' 批准所有记忆...")
    
    merged_content = merge_memories(memory_content, instruction_content)
    
    # 保存结果
    output_file = "test-memory-domain/test-merged.instructions.md"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(merged_content)
    
    print(f"\n✅ 合并完成！结果已保存到: {output_file}")
    
    # 显示部分结果
    print("\n📄 合并结果预览（前20行）:")
    print("-" * 50)
    lines = merged_content.split('\n')[:20]
    for line in lines:
        print(line)
    print("...")

if __name__ == "__main__":
    test_memory_merger()