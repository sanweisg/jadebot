#!/bin/bash
# JadeBot 自进化系统安装脚本
# 用法: ./install_self_learning.sh

echo "=== 开始安装自学习系统 ==="
echo ""

# 1. 安装Cognee（记忆系统）
echo "[1/4] 安装Cognee..."
cd ~/jadebot/cognee || {
    echo "Cognee未安装，正在下载..."
    cd ~/jadebot
    git -c http.proxy="" -c https.proxy="" clone --depth 1 https://github.com/kaylee-ai/cognee.git
}
pip install -e cognee -q
echo "✅ Cognee安装完成"

# 2. 安装Reflexio（学习循环）
echo ""
echo "[2/4] 安装Reflexio..."
cd ~/jadebot/reflexio || {
    echo "Reflexio未安装，正在下载..."
    cd ~/jadebot
    git -c http.proxy="" -c https.proxy="" clone --depth 1 https://github.com/ReflexioAI/reflexio.git
}
pip install -e reflexio -q
echo "✅ Reflexio安装完成"

# 3. 初始化记忆系统
echo ""
echo "[3/4] 初始化记忆系统..."
mkdir -p ~/.cognee/jadebot
cognee init --data-dir ~/.cognee/jadebot
echo "✅ 记忆系统初始化完成"

# 4. 导入现有记忆
echo ""
echo "[4/4] 导入现有记忆..."
if [ -f ~/Desktop/终极记忆_赚钱项目.txt ]; then
    cognee ingest --source ~/Desktop/终极记忆_赚钱项目.txt --data-type text
    echo "✅ 记忆导入完成"
else
    echo "⚠️  记忆文件不存在，跳过导入"
fi

echo ""
echo "=== 安装完成 ==="
echo ""
echo "下一步："
echo "1. 启动Cognee服务: cognee serve"
echo "2. 启动Reflexio学习循环: reflexio run --loop"
echo "3. 每次任务完成后自动学习改进"
echo ""
echo "文档位置:"
echo "- ~/jadebot/SELF_IMPROVING_SYSTEM.md"
echo "- ~/jadebot/cognee/README.md"
echo "- ~/jadebot/reflexio/README.md"
