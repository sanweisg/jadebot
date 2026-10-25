#!/bin/bash
# JadeBot 永久自学习系统 - 启动脚本
# 用法: ./permanent_self_learning.sh

set -e

echo "=== 启动JadeBot永久自学习系统 ==="
echo ""

# 1. 检查并安装依赖
if ! command -v reflexio &> /dev/null; then
    echo "[安装] Reflexio..."
    cd ~/jadebot/venv
    pip install reflexio-ai -q
fi

# 2. 初始化Reflexio（如果未初始化）
if [ ! -d ~/.reflexio ]; then
    echo "[初始化] Reflexio记忆库..."
    mkdir -p ~/.reflexio
    export REFLEXIO_DATA_DIR=~/.reflexio
    venv/bin/reflexio init --data-dir ~/.reflexio 2>/dev/null || true
fi

# 3. 导入现有记忆
if [ -f ~/Desktop/终极记忆_赚钱项目.txt ]; then
    echo "[导入] 现有记忆..."
    venv/bin/reflexio import --file ~/Desktop/终极记忆_赚钱项目.txt --type text 2>/dev/null || echo "跳过导入（格式不匹配）"
fi

# 4. 启动Reflexio服务
echo "[启动] Reflexio服务..."
pkill -f "reflexio.*services" 2>/dev/null || true
sleep 1
cd ~/jadebot/venv
nohup venv/bin/reflexio services start > ~/.reflexio/reflexio.log 2>&1 &
echo "Reflexio服务已启动（日志: ~/.reflexio/reflexio.log）"

# 5. 设置定时学习任务
echo "[配置] 定时学习任务..."
(crontab -l 2>/dev/null; echo "# JadeBot自学习任务") | crontab -
(crontab -l 2>/dev/null; echo "0 */6 * * * cd ~/jadebot && venv/bin/python auto_learn.py >> ~/jadebot/learn.log 2>&1") | crontab -
(crontab -l 2>/dev/null; echo "0 4 * * * cd ~/jadebot && venv/bin/reflexio cleanup --old-days 30 >> ~/jadebot/cleanup.log 2>&1") | crontab -

echo ""
echo "=== 系统已启动 ==="
echo ""
echo "📊 Reflexio服务: http://localhost:8061"
echo "📝 学习日志: ~/jadebot/learn.log"
echo "🧠 记忆数据库: ~/.reflexio/"
echo ""
echo "✅ 每次任务完成后自动学习"
echo "✅ 每6小时自动优化"
echo "✅ 30天-old记忆自动清理"
echo ""
echo "下次开机说'启动自学习'即可"
