#!/usr/bin/env python3
"""
JadeBot 自动学习模块
每次任务完成后自动分析并改进
"""

import json
import os
import sqlite3
from datetime import datetime
from pathlib import Path

class JadeBotLearner:
    def __init__(self):
        self.db_path = Path.home() / ".jadebot" / "learn.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.init_db()
    
    def init_db(self):
        """初始化学习数据库"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        # 成功模式表
        c.execute('''CREATE TABLE IF NOT EXISTS success_patterns
                    (id INTEGER PRIMARY KEY,
                     pattern TEXT,
                     context TEXT,
                     result REAL,
                     timestamp TIMESTAMP)''')
        
        # 失败模式表
        c.execute('''CREATE TABLE IF NOT EXISTS failure_patterns
                    (id INTEGER PRIMARY KEY,
                     error TEXT,
                     context TEXT,
                     solution TEXT,
                     timestamp TIMESTAMP)''')
        
        # 技能进化表
        c.execute('''CREATE TABLE IF NOT EXISTS skills
                    (name TEXT PRIMARY KEY,
                     version INTEGER,
                     effectiveness REAL,
                     last_used TIMESTAMP)''')
        
        conn.commit()
        conn.close()
    
    def record_success(self, pattern, context, result):
        """记录成功模式"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("INSERT INTO success_patterns VALUES (NULL, ?, ?, ?, ?)",
                 (pattern, context, result, datetime.now()))
        conn.commit()
        conn.close()
    
    def record_failure(self, error, context, solution):
        """记录失败模式"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("INSERT INTO failure_patterns VALUES (NULL, ?, ?, ?, ?)",
                 (error, context, solution, datetime.now()))
        conn.commit()
        conn.close()
    
    def analyze_and_improve(self):
        """分析历史数据，生成改进方案"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        # 分析成功模式
        c.execute("""SELECT pattern, COUNT(*) as count 
                    FROM success_patterns 
                    GROUP BY pattern 
                    ORDER BY count DESC 
                    LIMIT 10""")
        top_successes = c.fetchall()
        
        # 分析失败模式
        c.execute("""SELECT error, COUNT(*) as count 
                    FROM failure_patterns 
                    GROUP BY error 
                    ORDER BY count DESC 
                    LIMIT 10""")
        top_failures = c.fetchall()
        
        conn.close()
        
        # 生成改进建议
        improvements = []
        
        # 基于成功模式优化
        for pattern, count in top_successes:
            if count >= 3:  # 成功的模式重复使用
                improvements.append(f"保持模式: {pattern[:50]}...")
        
        # 基于失败模式改进
        for error, count in top_failures:
            if count >= 2:  # 失败的错误要避免
                improvements.append(f"避免错误: {error[:50]}...")
        
        return improvements
    
    def save_improvement(self, improvement_text):
        """保存改进到技能库"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        # 检查技能是否已存在
        c.execute("SELECT version, effectiveness FROM skills WHERE name=?",
                 (improvement_text[:30],))
        row = c.fetchone()
        
        if row:
            # 更新现有技能
            new_version = row[0] + 1
            new_effectiveness = min(1.0, row[1] + 0.01)
            c.execute("UPDATE skills SET version=?, effectiveness=?, last_used=? WHERE name=?",
                     (new_version, new_effectiveness, datetime.now(), improvement_text[:30]))
        else:
            # 创建新技能
            c.execute("INSERT INTO skills VALUES (?, 1, 0.1, ?)",
                     (improvement_text[:30], datetime.now()))
        
        conn.commit()
        conn.close()
        
        return f"✅ 技能已更新: {improvement_text[:30]}... (v{new_version if row else 1})"


if __name__ == "__main__":
    learner = JadeBotLearner()
    
    print("=== JadeBot 自动学习分析 ===")
    print(f"时间: {datetime.now()}")
    print("")
    
    improvements = learner.analyze_and_improve()
    
    if improvements:
        print("发现改进机会:")
        for i, imp in enumerate(improvements, 1):
            print(f"  {i}. {imp}")
            learner.save_improvement(imp)
    else:
        print("暂无新的学习数据")
    
    print("")
    print("✅ 学习完成，下次任务会更聪明")
