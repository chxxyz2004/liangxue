#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
知识库初始化脚本
为现有Markdown文章添加frontmatter元数据
"""
import os
import re
from datetime import datetime

BLOG_DIR = '/workspace/现代量学讲义'

# 文件分类映射
FILE_CATEGORIES = {
    '复盘日报': '日报',
    '复盘日报_': '日报',
    '盘前预案': '预案',
    '盘前预案_': '预案',
    '盘中盯盘': '日报',
    '收盘复盘': '日报',
    '联网复盘': '日报',
    '案例_': '案例',
    '讲义_': '讲义',
    '学习路线图_': '路线',
    '历史回溯': '报告',
    '案例报告': '报告',
}

# 默认标签
DEFAULT_TAGS = {
    '日报': ['复盘', '每日总结'],
    '预案': ['操作计划', '盘前'],
    '案例': ['个股分析', '实战'],
    '讲义': ['理论学习', '量学'],
    '路线': ['学习路径', '系统学习'],
    '报告': ['分析报告', '研究'],
}

def parse_filename(filename):
    """解析文件名，提取标题和日期"""
    name = filename.replace('.md', '')
    
    # 提取日期
    date_match = re.search(r'(\d{4}-\d{2}-\d{2}|\d{8})', name)
    date = ''
    if date_match:
        d = date_match.group(1)
        if len(d) == 8:
            d = f"{d[:4]}-{d[4:6]}-{d[6:8]}"
        date = d
    
    # 提取标题
    title = name
    for prefix in FILE_CATEGORIES.keys():
        if name.startswith(prefix):
            title = name[len(prefix):]
            break
    
    # 清理标题
    title = re.sub(r'[_-]', ' ', title)
    title = re.sub(r'\s+', ' ', title).strip()
    
    return title, date

def detect_category(filename):
    """检测文章分类"""
    for prefix, cat in FILE_CATEGORIES.items():
        if filename.startswith(prefix):
            return cat
    return '其他'

def add_frontmatter(filepath, title, date, category, tags):
    """为文件添加frontmatter"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
    except:
        return False
    
    # 检查是否已有frontmatter
    if content.startswith('---'):
        return True
    
    # 构建frontmatter
    fm = f"""---
title: "{title}"
date: {date}
category: {category}
tags: [{', '.join(f'"{t}"' for t in tags)}]
---

"""
    
    # 写入新内容
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(fm + content)
    
    return True

def main():
    """主函数"""
    count = 0
    for filename in os.listdir(BLOG_DIR):
        if not filename.endswith('.md') or filename.startswith('.'):
            continue
        
        filepath = os.path.join(BLOG_DIR, filename)
        
        # 跳过特殊文件
        if filename in ['signal_library.md', 'failure_cases.md', 'github开源项目调研报告.md', '案例导航.md']:
            continue
        
        title, date = parse_filename(filename)
        category = detect_category(filename)
        tags = DEFAULT_TAGS.get(category, [category])
        
        if add_frontmatter(filepath, title, date, category, tags):
            print(f"✓ {filename} -> [{category}] {title}")
            count += 1
    
    print(f"\n共处理 {count} 个文件")

if __name__ == '__main__':
    main()
