#!/bin/bash
# JadeBot 自进化系统 - 永久自动学习配置
# 每次开机自动启动，持续学习变聪明

echo "=== 启动JadeBot自进化系统 ==="
echo ""

# 1. 检查并启动Cognee（记忆存储）
if pgrep -f cognee > /dev/null; then
    echo "[OK] Cognee已在运行"
else
    echo "[启动] Cognee记忆服务..."
    cognee serve --port 8000 &
    sleep 2
fi

# 2. 检查并启动Reflexio（学习引擎）
if pgrep -f reflexio > /dev/null; then
    echo "[OK] Reflexio已在运行"
else
    echo "[启动] Reflexio学习循环..."
    cd ~/jadebot/reflexio
    reflexio run --loop &
    sleep 2
fi

# 3. 启动JadeBot主系统
echo "[启动] JadeBot交易系统..."
cd ~/jadebot
source venv/bin/activate
python jadebot_v2.py &

# 4. 设置定时学习任务（每6小时自动优化）
if ! crontab -l 2>/dev/null | grep -q "jadebot_self_learn"; then
    echo "[配置] 添加定时学习任务..."
    (crontab -l 2>/dev/null; echo "0 */6 * * * cd ~/jadebot && python auto_learn.py >> ~/jadebot/learn.log 2>&1") | crontab -
fi

echo ""
echo "=== 系统已启动 ==="
echo "- 记忆服务: http://localhost:8000"
echo "- 学习引擎: Reflexio后台运行"
echo "- 交易系统: JadeBot后台运行"
echo ""
echo "✅ 现在你关机睡觉，明天我会更聪明"
echo "✅ 每次对话我自动学习，越用越聪明"
echo ""
echo "下次开机直接说'赚钱'或'启动'即可"
