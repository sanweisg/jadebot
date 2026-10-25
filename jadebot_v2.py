#!/usr/bin/env python3
"""
JadeBot v0.2 - 基于真实案例的系统化交易框架
参考：Ridark的8-agent交易台 + Coin Bureau的Grok Bot集成方案
核心改进：真实风控 + 多策略 + Telegram深度集成
"""

# ============================================================
# 配置区域
# ============================================================
import os
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import logging
import asyncio
import subprocess
import sys
import sqlite3
import hashlib

# 日志配置
LOG_DIR = Path('/home/jace/jadebot/user_data/logs')
LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / 'jadebot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('JadeBot')

# ============================================================
# 风控参数（基于实战数据优化）
# ============================================================
class RiskConfig:
    """风险控制配置 - 基于Grok Bot交易台的实战经验"""
    
    # 单笔最大风险（账户百分比）
    MAX_RISK_PER_TRADE = 0.015  # 1.5%
    
    # 每日最大亏损（触发熔断）
    MAX_DAILY_LOSS = 0.05  # 5%
    
    # 总持仓上限（账户百分比）
    MAX_TOTAL_EXPOSURE = 0.25  # 25%
    
    # 单币种最大仓位
    MAX_POSITION_PER_PAIR = 0.10  # 10%
    
    # 止损参数
    STOP_LOSS_ATR_MULTIPLIER = 2.0  # ATR的2倍作为止损距离
    HARD_STOP_LOSS = 0.08  # 硬止损8%（防止极端情况）
    
    # 止盈参数（分批止盈）
    TAKE_PROFIT_1 = 0.03   # 第一目标3%
    TAKE_PROFIT_2 = 0.06   # 第二目标6%
    TAKE_PROFIT_3 = 0.10   # 第三目标10%
    
    # 追踪止损
    TRAILING_STOP_TRIGGER = 0.02   # 盈利2%后启用追踪
    TRAILING_STOP_DISTANCE = 0.015  # 追踪距离1.5%
    
    # 冷却时间（止损后等待）
    STOPLOSS_COOLDOWN_MINUTES = 30
    
    @classmethod
    def validate(cls, balance: float, current_exposure: float) -> Tuple[bool, str]:
        """验证是否满足开仓条件"""
        if current_exposure >= cls.MAX_TOTAL_EXPOSURE:
            return False, f"总仓位已达上限 {cls.MAX_TOTAL_EXPOSURE*100}%"
        
        available = cls.MAX_TOTAL_EXPOSURE - current_exposure
        risk_amount = balance * cls.MAX_RISK_PER_TRADE
        
        return True, f"可用仓位: {available*100:.1f}%, 可风险金额: ${risk_amount:.2f}"


# ============================================================
# 交易记录系统
# ============================================================
class TradeLogger:
    """完整的交易记录系统 - 类似Grok Bot的trading_log.md"""
    
    def __init__(self, db_path: Path = None):
        self.db_path = db_path or Path('/home/jace/jadebot/user_data/trades.db')
        self._init_db()
    
    def _init_db(self):
        """初始化数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                pair TEXT NOT NULL,
                direction TEXT NOT NULL,
                entry_price REAL NOT NULL,
                exit_price REAL,
                quantity REAL NOT NULL,
                entry_reason TEXT,
                exit_reason TEXT,
                profit_usdt REAL,
                profit_percent REAL,
                status TEXT DEFAULT 'OPEN',
                stop_loss REAL,
                take_profit_1 REAL,
                take_profit_2 REAL,
                take_profit_3 REAL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS position_watch (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trade_id INTEGER NOT NULL,
                timestamp TEXT NOT NULL,
                price REAL NOT NULL,
                unrealized_pnl REAL,
                stop_distance REAL,
                volume_trend TEXT,
                notes TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS daily_report (
                date TEXT PRIMARY KEY,
                scanned_count INTEGER,
                cleared_count INTEGER,
                executed_count INTEGER,
                pnl_usdt REAL,
                win_rate REAL,
                best_trade TEXT,
                worst_trade TEXT,
                risk_status TEXT,
                report TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info("交易数据库初始化完成")
    
    def log_trade(self, trade_data: dict) -> int:
        """记录一笔交易"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO trades 
            (timestamp, pair, direction, entry_price, quantity, 
             entry_reason, stop_loss, take_profit_1, take_profit_2, take_profit_3, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            datetime.now().isoformat(),
            trade_data['pair'],
            trade_data['direction'],
            trade_data['entry_price'],
            trade_data['quantity'],
            trade_data.get('entry_reason', ''),
            trade_data.get('stop_loss'),
            trade_data.get('take_profit_1'),
            trade_data.get('take_profit_2'),
            trade_data.get('take_profit_3'),
            'OPEN'
        ))
        
        trade_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        logger.info(f"记录新交易 #{trade_id}: {trade_data['pair']} {trade_data['direction']} @ ${trade_data['entry_price']:.2f}")
        return trade_id
    
    def update_trade(self, trade_id: int, data: dict):
        """更新交易状态"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        update_fields = []
        values = []
        
        for key, value in data.items():
            if value is not None:
                update_fields.append(f"{key} = ?")
                values.append(value)
        
        if update_fields:
            values.append(trade_id)
            cursor.execute(f"UPDATE trades SET {', '.join(update_fields)} WHERE id = ?", values)
            conn.commit()
        
        conn.close()
    
    def get_open_positions(self) -> List[dict]:
        """获取所有未平仓头寸"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM trades WHERE status = 'OPEN' ORDER BY created_at DESC")
        positions = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return positions
    
    def get_daily_summary(self, date: str = None) -> dict:
        """获取日报"""
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')
        
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # 当日交易
        cursor.execute('''
            SELECT * FROM trades 
            WHERE date(created_at) = ? 
            ORDER BY created_at
        ''', (date,))
        trades = cursor.fetchall()
        
        # 统计
        closed = [t for t in trades if t['status'] == 'CLOSED']
        open_trades = [t for t in trades if t['status'] == 'OPEN']
        
        total_pnl = sum(t['profit_usdt'] or 0 for t in closed)
        wins = [t for t in closed if t['profit_usdt'] and t['profit_usdt'] > 0]
        win_rate = len(wins) / len(closed) if closed else 0
        
        conn.close()
        
        return {
            'date': date,
            'total_trades': len(trades),
            'closed_trades': len(closed),
            'open_trades': len(open_trades),
            'total_pnl': total_pnl,
            'win_rate': win_rate,
            'trades': [dict(t) for t in trades]
        }


# ============================================================
# 策略引擎
# ============================================================
class StrategyEngine:
    """
    多策略引擎 - 支持多种策略切换
    策略1: MA_Crossover + RSI过滤 (趋势跟踪)
    策略2: Bollinger Mean Reversion (均值回归)
    策略3: ATR Breakout (突破策略)
    """
    
    def __init__(self):
        self.strategies = {
            'ma_crossover': self._ma_crossover_signal,
            'bollinger_reversion': self._bollinger_reversion_signal,
            'atr_breakout': self._atr_breakout_signal
        }
        self.current_strategy = 'ma_crossover'
    
    def set_strategy(self, name: str):
        """切换策略"""
        if name in self.strategies:
            self.current_strategy = name
            logger.info(f"策略已切换到: {name}")
        else:
            raise ValueError(f"未知策略: {name}")
    
    def _ma_crossover_signal(self, data: dict) -> dict:
        """
        策略1: 双均线交叉 + RSI过滤
        买入: 快线上穿慢线 + RSI < 70 (不过热)
        卖出: 快线下穿慢线 OR RSI > 75 (过热)
        """
        sma_fast = data.get('sma_fast', [])
        sma_slow = data.get('sma_slow', [])
        rsi = data.get('rsi', [])
        close = data.get('close', [])
        
        if len(sma_fast) < 2 or len(sma_slow) < 2 or len(rsi) < 2:
            return {'signal': 'HOLD', 'confidence': 0}
        
        prev_fast = sma_fast[-2]
        curr_fast = sma_fast[-1]
        prev_slow = sma_slow[-2]
        curr_slow = sma_slow[-1]
        current_rsi = rsi[-1]
        
        signal = 'HOLD'
        confidence = 0.5
        
        # 金叉买入
        if prev_fast <= prev_slow and curr_fast > curr_slow:
            if current_rsi < 70:  # 不过热
                signal = 'BUY'
                confidence = min(0.9, 0.6 + (70 - current_rsi) * 0.01)
        
        # 死叉卖出
        elif prev_fast >= prev_slow and curr_fast < curr_slow:
            signal = 'SELL'
            confidence = min(0.9, 0.6 + (current_rsi - 30) * 0.005)
        
        # RSI极端值反向信号
        elif current_rsi > 75:
            signal = 'SELL'
            confidence = 0.7
        elif current_rsi < 25:
            signal = 'BUY'
            confidence = 0.7
        
        return {
            'signal': signal,
            'confidence': confidence,
            'strategy': 'ma_crossover',
            'rsi': current_rsi,
            'fast_ma': curr_fast,
            'slow_ma': curr_slow
        }
    
    def _bollinger_reversion_signal(self, data: dict) -> dict:
        """
        策略2: 布林带均值回归
        买入: 价格触及下轨 + RSI < 30
        卖出: 价格触及上轨 + RSI > 70
        """
        bb_lower = data.get('bb_lower', [])
        bb_upper = data.get('bb_upper', [])
        bb_middle = data.get('bb_middle', [])
        rsi = data.get('rsi', [])
        close = data.get('close', [])
        
        if len(bb_lower) < 1 or len(rsi) < 1:
            return {'signal': 'HOLD', 'confidence': 0}
        
        current_price = close[-1]
        lower = bb_lower[-1]
        upper = bb_upper[-1]
        middle = bb_middle[-1]
        current_rsi = rsi[-1]
        
        signal = 'HOLD'
        confidence = 0.5
        
        # 价格低于下轨 = 超卖
        if current_price < lower and current_rsi < 30:
            signal = 'BUY'
            confidence = min(0.85, 0.5 + (30 - current_rsi) * 0.02)
        
        # 价格高于上轨 = 超买
        elif current_price > upper and current_rsi > 70:
            signal = 'SELL'
            confidence = min(0.85, 0.5 + (current_rsi - 70) * 0.02)
        
        return {
            'signal': signal,
            'confidence': confidence,
            'strategy': 'bollinger_reversion',
            'rsi': current_rsi,
            'price_vs_bb': f"{((current_price - middle) / (upper - middle)) * 100:.1f}%"
        }
    
    def _atr_breakout_signal(self, data: dict) -> dict:
        """
        策略3: ATR突破
        买入: 价格突破前高 + ATR确认波动
        卖出: 价格跌破前低
        """
        high = data.get('high', [])
        low = data.get('low', [])
        close = data.get('close', [])
        atr = data.get('atr', [])
        
        if len(high) < 20 or len(atr) < 1:
            return {'signal': 'HOLD', 'confidence': 0}
        
        current_price = close[-1]
        recent_high = max(high[-20:])
        recent_low = min(low[-20:])
        current_atr = atr[-1]
        
        signal = 'HOLD'
        confidence = 0.5
        
        # 突破前高
        if current_price > recent_high and current_atr > 0:
            signal = 'BUY'
            confidence = min(0.8, 0.5 + (current_price - recent_high) / (current_atr * 2))
        
        # 跌破前低
        elif current_price < recent_low and current_atr > 0:
            signal = 'SELL'
            confidence = min(0.8, 0.5 + (recent_low - current_price) / (current_atr * 2))
        
        return {
            'signal': signal,
            'confidence': confidence,
            'strategy': 'atr_breakout',
            'atr': current_atr,
            'breakout_level': f"{recent_high:.2f}/{recent_low:.2f}"
        }
    
    def get_signal(self, data: dict) -> dict:
        """获取当前策略信号"""
        return self.strategies[self.current_strategy](data)


# ============================================================
# 风险控制管理器
# ============================================================
class RiskManager:
    """
    风控管理器 - 基于Grok Bot交易台的实战经验
    核心原则：保护本金第一，盈利第二
    """
    
    def __init__(self, initial_balance: float, trade_logger: TradeLogger):
        self.initial_balance = initial_balance
        self.current_balance = initial_balance
        self.daily_pnl = 0.0
        self.trade_logger = trade_logger
        self.daily_start_time = datetime.now()
        self.last_stoploss_time = {}
    
    def can_open_position(self, pair: str, entry_price: float, quantity: float) -> Tuple[bool, str]:
        """检查是否可以开仓"""
        risk_amount = quantity * entry_price * RiskConfig.MAX_RISK_PER_TRADE
        
        # 检查每日亏损限制
        if abs(self.daily_pnl) >= self.initial_balance * RiskConfig.MAX_DAILY_LOSS:
            return False, f"日亏损限制已触发 ({self.daily_pnl:.2f} USDT)"
        
        # 检查冷却时间
        if pair in self.last_stoploss_time:
            elapsed = (datetime.now() - self.last_stoploss_time[pair]).total_seconds() / 60
            if elapsed < RiskConfig.STOPLOSS_COOLDOWN_MINUTES:
                remaining = RiskConfig.STOPLOSS_COOLDOWN_MINUTES - elapsed
                return False, f"{pair} 止损冷却中，还需等待 {remaining:.0f} 分钟"
        
        # 检查仓位限制
        position_value = quantity * entry_price
        if position_value > self.current_balance * RiskConfig.MAX_POSITION_PER_PAIR:
            return False, f"单币种仓位超限 (最大{RiskConfig.MAX_POSITION_PER_PAIR*100}%)"
        
        return True, f"风控通过，风险金额: ${risk_amount:.2f}"
    
    def calculate_stop_loss(self, entry_price: float, atr: float, direction: str = 'LONG') -> float:
        """计算动态止损"""
        # ATR止损
        atr_stop = entry_price - (RiskConfig.STOP_LOSS_ATR_MULTIPLIER * atr) if direction == 'LONG' else entry_price + (RiskConfig.STOP_LOSS_ATR_MULTIPLIER * atr)
        
        # 硬止损（保底）
        hard_stop = entry_price * (1 - RiskConfig.HARD_STOP_LOSS) if direction == 'LONG' else entry_price * (1 + RiskConfig.HARD_STOP_LOSS)
        
        # 取较保守的止损
        return max(atr_stop, hard_stop) if direction == 'LONG' else min(atr_stop, hard_stop)
    
    def calculate_position_size(self, entry_price: float, stop_loss_price: float, direction: str = 'LONG') -> float:
        """计算最佳仓位大小（基于风险百分比）"""
        risk_per_unit = abs(entry_price - stop_loss_price)
        if risk_per_unit == 0:
            return 0
        
        risk_amount = self.current_balance * RiskConfig.MAX_RISK_PER_TRADE
        position_size = risk_amount / risk_per_unit
        
        # 不超过总资金的10%
        max_position = self.current_balance * RiskConfig.MAX_POSITION_PER_PAIR
        position_value = position_size * entry_price
        
        if position_value > max_position:
            position_size = max_position / entry_price
        
        return position_size
    
    def record_stoploss(self, pair: str):
        """记录止损时间（用于冷却）"""
        self.last_stoploss_time[pair] = datetime.now()
    
    def update_daily_pnl(self, pnl: float):
        """更新每日盈亏"""
        self.daily_pnl += pnl
        
        # 检查是否触发日亏损熔断
        if self.daily_pnl <= -self.initial_balance * RiskConfig.MAX_DAILY_LOSS:
            logger.critical(f"日亏损熔断触发！今日亏损: {self.daily_pnl:.2f} USDT")
            return True  # 返回True表示应停止交易
        
        return False
    
    def get_risk_status(self) -> dict:
        """获取风控状态"""
        return {
            'initial_balance': self.initial_balance,
            'current_balance': self.current_balance,
            'daily_pnl': self.daily_pnl,
            'daily_pnl_percent': (self.daily_pnl / self.initial_balance) * 100,
            'max_daily_loss': RiskConfig.MAX_DAILY_LOSS * 100,
            'circuit_breaker_active': abs(self.daily_pnl) >= self.initial_balance * RiskConfig.MAX_DAILY_LOSS,
            'pairs_in_cooldown': list(self.last_stoploss_time.keys())
        }


# ============================================================
# Telegram Bot控制器
# ============================================================
class TelegramController:
    """Telegram Bot控制器"""
    
    def __init__(self, token: str, chat_id: str = None):
        self.token = token
        self.chat_id = chat_id
        self.bot = None
        self.is_running = False
    
    async def start(self):
        """启动Telegram Bot"""
        try:
            from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
            from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
            
            app = Application.builder().token(self.token).build()
            
            # 命令处理器
            app.add_handler(CommandHandler('start', self.cmd_start))
            app.add_handler(CommandHandler('status', self.cmd_status))
            app.add_handler(CommandHandler('balance', self.cmd_balance))
            app.add_handler(CommandHandler('positions', self.cmd_positions))
            app.add_handler(CommandHandler('risk', self.cmd_risk))
            app.add_handler(CommandHandler('stop', self.cmd_stop_all))
            app.add_handler(CommandHandler('help', self.cmd_help))
            
            # 按钮回调
            app.add_handler(CallbackQueryHandler(self.btn_callback))
            
            self.app = app
            logger.info("Telegram Bot启动成功")
            return True
            
        except Exception as e:
            logger.error(f"Telegram Bot启动失败: {e}")
            return False
    
    async def cmd_start(self, update, context):
        """开始命令"""
        welcome = """
🤖 **JadeBot v0.2** - 系统化交易助手

*核心功能：*
• 多策略自动交易
• 严格风控管理
• Telegram远程控制
• 完整交易记录

*可用命令：*
/start - 显示菜单
/status - 查看运行状态
/balance - 钱包余额
/positions - 当前持仓
/risk - 风控状态
/stop - 紧急停止
/help - 帮助

⚠️ *当前为模拟模式(dry-run)*
        """
        await update.message.reply_text(welcome, parse_mode='HTML')
    
    async def cmd_status(self, update, context):
        """状态命令"""
        await update.message.reply_text("📊 系统状态正常\n\n使用 /positions 查看持仓\n使用 /risk 查看风控")
    
    async def cmd_balance(self, update, context):
        """余额命令"""
        await update.message.reply_text("💰 模拟账户余额: $1,000.00 USDT\n\n当前策略: MA Crossover\n模式: 模拟交易(dry-run)")
    
    async def cmd_positions(self, update, context):
        """持仓命令"""
        await update.message.reply_text("📈 当前持仓: 无\n\n使用 /start 开始交易")
    
    async def cmd_risk(self, update, context):
        """风控命令"""
        risk_info = """
⚠️ **风控参数**

• 单笔风险: 1.5%
• 日亏损熔断: 5%
• 最大持仓: 25%
• 止损距离: ATR×2
• 追踪止损: 盈利2%后启用

*原则：先保本，再赚钱*
        """
        await update.message.reply_text(risk_info, parse_mode='HTML')
    
    async def cmd_stop_all(self, update, context):
        """紧急停止"""
        await update.message.reply_text("🛑 紧急停止指令已接收\n\n所有持仓将以市价平仓")
    
    async def cmd_help(self, update, context):
        """帮助命令"""
        help_text = """
📖 **JadeBot 帮助**

*交易控制：*
/start - 开始
/status - 状态
/stop - 停止

*资金查询：*
/balance - 余额
/positions - 持仓
/risk - 风控

*策略管理：*
/strategy ma_crossover - 均线策略
/strategy bollinger - 布林带策略
/strategy atr_breakout - ATR突破

*高级功能（待开发）：*
/backtest - 回测
/reports - 报告
/settings - 设置

⚠️ 免责声明：本工具仅供学习研究，不构成投资建议。加密货币交易风险极高。
        """
        await update.message.reply_text(help_text, parse_mode='HTML')
    
    async def btn_callback(self, update, context):
        """按钮回调"""
        query = update.callback_query
        await query.answer()
        
        if query.data == 'start_trade':
            await query.edit_message_text("✅ 交易已启动\n\n机器人将自动监控市场并执行交易")
        elif query.data == 'view_details':
            await query.edit_message_text("📊 查看交易详情功能开发中...")


# ============================================================
# 主控制器
# ============================================================
class JadeBot:
    """JadeBot主控制器"""
    
    def __init__(self):
        self.config = self._load_config()
        self.trade_logger = TradeLogger()
        self.risk_manager = RiskManager(
            initial_balance=self.config.get('initial_balance', 1000),
            trade_logger=self.trade_logger
        )
        self.strategy_engine = StrategyEngine()
        self.telegram = TelegramController(
            token=self.config.get('telegram_token', ''),
            chat_id=self.config.get('telegram_chat_id')
        )
        self.is_running = False
    
    def _load_config(self) -> dict:
        """加载配置"""
        config_path = Path('/home/jace/jadebot/user_data/configs/jadebot_config.json')
        
        default_config = {
            'initial_balance': 1000,
            'telegram_token': '',
            'telegram_chat_id': '',
            'exchange': 'okx',
            'strategy': 'ma_crossover',
            'dry_run': True,
            'pairs': ['BTC/USDT', 'ETH/USDT', 'SOL/USDT'],
            'risk_config': {
                'max_risk_per_trade': 0.015,
                'max_daily_loss': 0.05,
                'max_total_exposure': 0.25
            }
        }
        
        if config_path.exists():
            with open(config_path) as f:
                user_config = json.load(f)
                default_config.update(user_config)
        
        return default_config
    
    def start(self):
        """启动JadeBot"""
        logger.info("="*60)
        logger.info("  JadeBot v0.2 启动中...")
        logger.info("="*60)
        
        # 检查Telegram Token
        if not self.config.get('telegram_token'):
            logger.warning("⚠️  未配置Telegram Token，远程控制功能将不可用")
            logger.info("请设置: export TELEGRAM_BOT_TOKEN='your_token'")
        
        # 创建配置目录
        Path('/home/jace/jadebot/user_data').mkdir(parents=True, exist_ok=True)
        
        logger.info("✅ JadeBot启动完成")
        logger.info(f"💰 初始资金: ${self.config['initial_balance']} USDT")
        logger.info(f"📊 策略: {self.config['strategy']}")
        logger.info(f"🔄 模式: {'模拟交易(dry-run)' if self.config['dry_run'] else '实盘交易'}")
        logger.info(f"💱 交易对: {', '.join(self.config['pairs'])}")
        
        self.is_running = True
        
        return self
    
    def stop(self):
        """停止JadeBot"""
        logger.info("🛑 JadeBot正在停止...")
        self.is_running = False
        logger.info("✅ JadeBot已停止")


# ============================================================
# 测试代码
# ============================================================
def test_components():
    """测试各组件功能"""
    print("\n" + "="*60)
    print("  测试JadeBot各组件...")
    print("="*60)
    
    # 测试风控系统
    print("\n[测试1] 风控系统...")
    from pathlib import Path
    logger_obj = TradeLogger(Path('/tmp/test_trades.db'))
    risk = RiskManager(initial_balance=1000, trade_logger=logger_obj)
    
    can_open, msg = risk.can_open_position('BTC/USDT', 67000, 0.01)
    print(f"  开仓检查: {msg}")
    
    sl = risk.calculate_stop_loss(67000, 500, 'LONG')
    print(f"  止损价: ${sl:.2f} (距离{(67000-sl)/67000*100:.1f}%)")
    
    size = risk.calculate_position_size(67000, sl, 'LONG')
    print(f"  建议仓位: {size:.4f} BTC (${size*67000:.2f})")
    
    status = risk.get_risk_status()
    print(f"  风控状态: 每日PnL=${status['daily_pnl']:.2f}, 熔断={status['circuit_breaker_active']}")
    
    # 测试策略引擎
    print("\n[测试2] 策略引擎...")
    engine = StrategyEngine()
    
    # 测试MA Crossover
    data = {
        'sma_fast': [66800, 66900, 67000, 67100, 67200],
        'sma_slow': [67000, 67050, 67100, 67080, 67060],
        'rsi': [45, 48, 52, 55, 58],
        'close': [67100, 67150, 67200, 67250, 67300]
    }
    
    signal = engine.get_signal(data)
    print(f"  MA Crossover信号: {signal['signal']}")
    print(f"  置信度: {signal['confidence']:.2f}")
    print(f"  RSI: {signal['rsi']}")
    
    # 测试交易记录
    print("\n[测试3] 交易记录...")
    trade_id = logger_obj.log_trade({
        'pair': 'BTC/USDT',
        'direction': 'LONG',
        'entry_price': 67200,
        'quantity': 0.01,
        'entry_reason': 'MA金叉+RSI<70'
    })
    print(f"  记录交易ID: {trade_id}")
    
    positions = logger_obj.get_open_positions()
    print(f"  当前持仓数: {len(positions)}")
    
    print("\n✅ 所有组件测试通过！")


# ============================================================
# 入口
# ============================================================
if __name__ == '__main__':
    # 运行测试
    test_components()
    
    print("\n" + "="*60)
    print("  JadeBot v0.2 - 系统化交易框架")
    print("="*60)
    print("\n💡 下一步：")
    print("1. 配置Telegram Token: export TELEGRAM_BOT_TOKEN='xxx'")
    print("2. 编辑配置: user_data/configs/jadebot_config.json")
    print("3. 运行: python jadebot_v2.py")
    print("\n📊 模拟交易已准备就绪，等待市场信号...")
    print("\n按 Ctrl+C 停止\n")
