# JadeBot - 一键启动脚本
# 保存为 ~/jadebot/start.sh，双击运行

cd ~/jadebot
source venv/bin/activate

echo "============================================"
echo "🤖 JadeBot 控制面板"
echo "============================================"
echo ""
echo "请选择操作："
echo "1. 启动多Agent模拟"
echo "2. 启动FreqUI面板（浏览器查看）"
echo "3. 启动模拟交易（后台运行）"
echo "4. 查看实时日志"
echo "5. 停止所有进程"
echo "0. 退出"
echo ""
read -p "输入选项: " choice

case $choice in
  1) python multi_agent.py ;;
  2) freqtrade webserver --config config_final.json ;;
  3) freqtrade trade --strategy SimpleStableRSI --config config_final.json > user_data/logs/trade.log 2>&1 & echo "已启动，PID: $!" ;;
  4) tail -f user_data/logs/trade.log ;;
  5) pkill -f "freqtrade" && pkill -f "multi_agent" && echo "已停止" ;;
  0) exit 0 ;;
  *) echo "无效选项" ;;
esac
