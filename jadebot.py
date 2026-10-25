#!/usr/bin/env python3
"""
JadeBot 启动脚本
一键启动完整系统
"""
import subprocess
import sys
import os
import time
from pathlib import Path

BOT_DIR = Path('/home/jace/jadebot')
VENV_DIR = BOT_DIR / 'venv'
CONFIG_PATH = BOT_DIR / 'user_data' / 'configs' / 'config_dryrun.json'

def check_prerequisites():
    """检查前置条件"""
    print("\n" + "="*60)
    print("  🤖 JadeBot 前置检查")
    print("="*60 + "\n")
    
    # 检查Python
    try:
        result = subprocess.run([sys.executable, '--version'], 
                              capture_output=True, text=True)
        print(f"✅ Python: {result.stdout.strip()}")
    except Exception as e:
        print(f"❌ Python错误: {e}")
        return False
    
    # 检查虚拟环境
    if not VENV_DIR.exists():
        print("⚠️  虚拟环境不存在，正在创建...")
        subprocess.run([sys.executable, '-m', 'venv', str(VENV_DIR)])
        print("✅ 虚拟环境已创建")
    
    # 激活虚拟环境
    venv_python = VENV_DIR / 'bin' / 'python'
    if not venv_python.exists():
        print("❌ 虚拟环境Python不存在")
        return False
    print(f"✅ 虚拟环境: {venv_python}")
    
    # 检查必要包
    packages = ['freqtrade', 'ccxt', 'python-telegram-bot']
    for pkg in packages:
        result = subprocess.run(
            [str(venv_python), '-c', f'import {pkg.replace("-", "_")}'],
            capture_output=True
        )
        if result.returncode == 0:
            print(f"✅ {pkg}")
        else:
            print(f"⚠️  {pkg} 未安装，正在安装...")
            subprocess.run(
                [str(venv_python), '-m', 'pip', 'install', pkg],
                capture_output=True
            )
    
    # 检查配置文件
    if not CONFIG_PATH.exists():
        print(f"❌ 配置文件不存在: {CONFIG_PATH}")
        return False
    print(f"✅ 配置文件: {CONFIG_PATH}")
    
    return True


def download_data():
    """下载交易数据"""
    print("\n📥 正在下载交易数据...")
    venv_python = str(VENV_DIR / 'bin' / 'python')
    cmd = [
        venv_python, '-m', 'freqtrade', 'download-data',
        '-c', str(CONFIG_PATH),
        '--days', '30',
        '--timeframes', '5m'
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        print("✅ 数据下载完成")
        return True
    else:
        print(f"⚠️  数据下载遇到问题: {result.stderr}")
        return False


def run_backtest():
    """运行回测"""
    print("\n📊 正在运行回测...")
    venv_python = str(VENV_DIR / 'python')
    cmd = [
        venv_python, '-m', 'freqtrade', 'backtesting',
        '-c', str(CONFIG_PATH),
        '--strategy', 'JadeMAStrategy',
        '--timerange', '20250901-20251025'
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    print(result.stdout)
    if result.returncode == 0:
        print("✅ 回测完成")
        return True
    else:
        print(f"⚠️  回测失败: {result.stderr}")
        return False


def start_telegram_bot():
    """启动Telegram Bot"""
    print("\n💬 正在启动Telegram Bot...")
    venv_python = str(VENV_DIR / 'bin' / 'python')
    cmd = [venv_python, str(BOT_DIR / 'bot.py')]
    
    # 检查环境变量
    token = os.environ.get('TELEGRAM_BOT_TOKEN', '')
    if not token:
        print("⚠️  未设置 TELEGRAM_BOT_TOKEN 环境变量")
        print("请先获取Bot Token：")
        print("1. 在Telegram搜索 @BotFather")
        print("2. 发送 /newbot 创建新Bot")
        print("3. 复制Bot Token并设置环境变量")
        print("export TELEGRAM_BOT_TOKEN='你的token'")
        return False
    
    try:
        proc = subprocess.Popen([venv_python, str(BOT_DIR / 'bot.py')])
        print(f"✅ Telegram Bot已启动 (PID: {proc.pid})")
        return proc
    except Exception as e:
        print(f"❌ 启动失败: {e}")
        return False


def main():
    """主函数"""
    print("\n" + "="*60)
    print("  🤖 JadeBot v0.1 - 自动化交易助手")
    print("="*60)
    
    # 检查前置条件
    if not check_prerequisites():
        print("\n❌ 前置检查失败，请修复后重试")
        sys.exit(1)
    
    print("\n" + "="*60)
    print("  📋 请选择操作:")
    print("="*60)
    print("  1. 下载交易数据")
    print("  2. 运行回测")
    print("  3. 启动Telegram Bot")
    print("  4. 全部运行（下载+回测+启动Bot）")
    print("  5. 退出")
    print("="*60)
    
    choice = input("\n请输入选项 (1-5): ").strip()
    
    if choice == '1':
        download_data()
    elif choice == '2':
        run_backtest()
    elif choice == '3':
        start_telegram_bot()
    elif choice == '4':
        download_data()
        run_backtest()
        start_telegram_bot()
    elif choice == '5':
        print("👋 再见！")
    else:
        print("❌ 无效选项")
    
    print("\n" + "="*60)


if __name__ == '__main__':
    main()
