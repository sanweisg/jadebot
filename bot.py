#!/usr/bin/env python3
"""
JadeBot - Telegram Bot for Crypto Trading Control
手机控制你的交易机器人
"""
import os
import sys
import asyncio
import logging
import subprocess
import json
from pathlib import Path
from datetime import datetime

import aiohttp
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    ContextTypes, MessageHandler, filters
)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/home/jace/jadebot/user_data/logs/bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 路径配置
BOT_DIR = Path('/home/jace/jadebot')
CONFIG_PATH = BOT_DIR / 'user_data' / 'configs' / 'config_dryrun.json'
LOG_DIR = BOT_DIR / 'user_data' / 'logs'
TRADE_DB = BOT_DIR / 'tradesv3.dryrun.sqlite'

# 全局状态
bot_process = None
is_running = False


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """开始命令"""
    welcome_msg = """
🤖 **JadeBot v0.1** - 你的私人交易助手

*功能列表：*
/start - 显示此菜单
/status - 查看运行状态
/start_bot - 启动交易机器人
/stop_bot - 停止交易机器人
/backtest - 运行回测
/balance - 查看余额
/trades - 查看最近交易
/help - 显示帮助

*注意：当前为模拟模式(dry-run)，不操作真实资金。*
    """
    await update.message.reply_text(welcome_msg, parse_mode='HTML')


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """查看状态"""
    global is_running
    
    if is_running:
        msg = "✅ **交易机器人正在运行中**\n\n当前为模拟模式(dry-run)。"
    else:
        msg = "⏸️ **交易机器人未运行**\n\n使用 /start_bot 启动。"
    
    await update.message.reply_text(msg, parse_mode='HTML')


async def start_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """启动交易机器人"""
    global bot_process, is_running
    
    if is_running:
        await update.message.reply_text("⚠️ 机器人已经在运行中。")
        return
    
    # 检查配置
    if not CONFIG_PATH.exists():
        await update.message.reply_text("❌ 配置文件不存在！")
        return
    
    # 启动 freqtrade
    try:
        cmd = [
            sys.executable, '-m', 'freqtrade', 'trade',
            '-c', str(CONFIG_PATH)
        ]
        
        bot_process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            cwd=str(BOT_DIR)
        )
        
        is_running = True
        logger.info(f"Trading bot started with PID {bot_process.pid}")
        
        await update.message.reply_text(
            f"✅ 交易机器人已启动！(PID: {bot_process.pid})\n\n"
            "正在监控市场并执行交易策略...\n"
            "使用 /status 查看状态。",
            parse_mode='HTML'
        )
        
    except Exception as e:
        logger.error(f"Failed to start bot: {e}")
        await update.message.reply_text(f"❌ 启动失败：{e}")


async def stop_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """停止交易机器人"""
    global bot_process, is_running
    
    if not is_running:
        await update.message.reply_text("⚠️ 机器人未运行。")
        return
    
    try:
        if bot_process:
            bot_process.terminate()
            bot_process.wait(timeout=10)
            logger.info("Trading bot stopped")
        
        is_running = False
        await update.message.reply_text(
            "⏹️ 交易机器人已停止。",
            parse_mode='HTML'
        )
    except Exception as e:
        logger.error(f"Failed to stop bot: {e}")
        await update.message.reply_text(f"❌ 停止失败：{e}")


async def backtest(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """运行回测"""
    await update.message.reply_text(
        "🔄 正在运行回测...\n\n"
        "这可能需要几分钟，请耐心等待。"
    )
    
    try:
        cmd = [
            sys.executable, '-m', 'freqtrade', 'backtesting',
            '-c', str(CONFIG_PATH),
            '--strategy', 'SimpleRSI',
            '--timerange', '20250101-20251025',
            '--export', 'trades'
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(BOT_DIR))
        
        if result.returncode == 0:
            await update.message.reply_text(
                "✅ 回测完成！\n\n"
                "查看完整结果：`/home/jace/jadebot/user_data/backtest-results/`",
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                f"❌ 回测失败：\n{result.stderr}"
            )
    except Exception as e:
        await update.message.reply_text(f"❌ 错误：{e}")


async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """查看余额"""
    try:
        cmd = [
            sys.executable, '-m', 'freqtrade', 'show-config',
            '-c', str(CONFIG_PATH)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            config = json.loads(result.stdout)
            dry_run_wallet = config.get('dry_run_wallet', 1000)
            
            msg = f"""
💰 **当前钱包余额**

• 初始资金: ${dry_run_wallet} USDT
• 当前模式: 模拟交易(dry-run)
• 注意: 实际交易需接入交易所API
            """
            await update.message.reply_text(msg, parse_mode='HTML')
        else:
            await update.message.reply_text(f"❌ 获取余额失败：{result.stderr}")
    except Exception as e:
        await update.message.reply_text(f"❌ 错误：{e}")


async def trades(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """查看交易记录"""
    try:
        cmd = [
            sys.executable, '-m', 'freqtrade', 'trades',
            '-c', str(CONFIG_PATH)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            # 截断长输出
            if len(result.stdout) > 1500:
                output = result.stdout[:1500] + "\n...(输出过长，请查看日志文件)"
            else:
                output = result.stdout
            
            await update.message.reply_text(
                f"📊 **最近交易记录**\n\n```{output}```",
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                "📭 暂无交易记录。\n\n"
                "当机器人开始交易后，这里会显示交易历史。"
            )
    except Exception as e:
        await update.message.reply_text(f"❌ 错误：{e}")


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """帮助"""
    help_msg = """
📖 **JadeBot 帮助文档**

*基本命令：*
• /start - 显示主菜单
• /help - 显示此帮助
• /status - 查看机器人状态

*交易控制：*
• /start_bot - 启动交易机器人
• /stop_bot - 停止交易机器人

*数据分析：*
• /backtest - 运行策略回测
• /balance - 查看钱包余额
• /trades - 查看交易历史

*重要提示：*
1. 当前为模拟模式，不操作真实资金
2. 需配置OKX/Binance API才能实盘交易
3. 建议先在模拟账户上测试策略

*下一步：*
1. 注册OKX账号并创建API Key
2. 配置 config_dryrun.json
3. 运行回测验证策略
4. 切换到实盘模式

需要更多帮助？联系开发者。
    """
    await update.message.reply_text(help_msg, parse_mode='HTML')


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理普通消息"""
    text = update.message.text.lower().strip()
    
    # 简单的自然语言响应
    responses = {
        "你好": "你好！我是JadeBot，你的交易助手。",
        "hello": "Hello! I'm JadeBot, your trading assistant.",
        "价格": "查看最新价格，使用命令 /price BTC",
        "btc": "BTC当前约 $67,000（模拟数据）",
        "eth": "ETH当前约 $3,500（模拟数据）",
        "赚钱": "自动化交易需要谨慎。先用模拟模式测试策略！",
        "亏损": "记住：设置止损，控制仓位，不要贪婪。",
    }
    
    for key, response in responses.items():
        if key in text:
            await update.message.reply_text(response)
            return
    
    await update.message.reply_text(
        "我不太明白。输入 /help 查看可用命令。"
    )


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理按钮点击"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "start_bot":
        await start_bot(update, context)
    elif query.data == "stop_bot":
        await stop_bot(update, context)
    elif query.data == "backtest":
        await backtest(update, context)
    elif query.data == "balance":
        await balance(update, context)
    elif query.data == "trades":
        await trades(update, context)
    elif query.data == "help":
        await help_cmd(update, context)
    elif query.data == "settings":
        await query.edit_message_text(
            "⚙️ 设置功能开发中...\n\n"
            "将支持：\n"
            "• 切换交易所\n"
            "• 修改策略参数\n"
            "• 设置止损止盈"
        )


def main():
    """主函数"""
    # 读取Telegram token
    token = os.environ.get('TELEGRAM_BOT_TOKEN', '')
    
    if not token:
        logger.error("请设置 TELEGRAM_BOT_TOKEN 环境变量")
        print("\n请执行：")
        print("export TELEGRAM_BOT_TOKEN='你的bot_token'")
        print("\n或编辑配置文件：user_data/configs/bot_config.env")
        sys.exit(1)
    
    # 创建应用
    application = Application.builder().token(token).build()
    
    # 注册命令
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('status', status))
    application.add_handler(CommandHandler('start_bot', start_bot))
    application.add_handler(CommandHandler('stop_bot', stop_bot))
    application.add_handler(CommandHandler('backtest', backtest))
    application.add_handler(CommandHandler('balance', balance))
    application.add_handler(CommandHandler('trades', trades))
    application.add_handler(CommandHandler('help', help_cmd))
    
    # 注册按钮回调
    application.add_handler(CallbackQueryHandler(button_handler))
    
    # 处理普通消息
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    logger.info("JadeBot Telegram Bot 启动中...")
    print("\n" + "="*50)
    print("  🤖 JadeBot v0.1 - 交易控制机器人")
    print("="*50)
    print("\n在 Telegram 中搜索 @your_bot_username 开始使用")
    print("查看实时日志：tail -f user_data/logs/bot.log")
    print("\n按 Ctrl+C 停止\n")
    
    # 启动
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
