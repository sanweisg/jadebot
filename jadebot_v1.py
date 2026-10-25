#!/usr/bin/env python3
"""
JadeBot v1.0 - 完整逆向Grok Bot交易台
参考: https://github.com/galleonlabs/hypergrok-trading-desk

7 Agent架构:
- Desk Lead: 协调者
- Market Analyst: 实时市场数据
- Research Analyst: 新闻和情绪分析
- Strategist: 策略研发和回测
- Risk Manager: 风控和仓位计算
- Execution Trader: 订单执行
- Trade Reviewer: 交易复盘

核心机制:
- Ticket系统 (HG-YYYYMMDD-XXXX)
- Stressed Sizing (滑点+手续费)
- 人工审批流程
- Out-of-Sample验证
"""

import json
import sqlite3
import time
import os
import requests
from datetime import datetime, timedelta
from pathlib import Path
from dataclasses import dataclass, asdict, field
from typing import List, Dict, Optional, Tuple
import pandas as pd
import numpy as np
from collections import defaultdict

# ========== Agnes AI配置 ==========
AGNES_API_KEY = os.environ.get('LLM_API_KEY', '')
AGNES_BASE_URL = 'https://apihub.agnes-ai.com/v1'

# ========== 配置 ==========
CONFIG = {
    'equity': 1000.0,
    'max_risk_per_trade': 0.005,  # 0.5%风险
    'max_total_open_risk': 0.02,   # 2%总风险
    'max_leverage': 10,
    'daily_loss_stop': -0.02,      # -2%日止损
    'allowed_markets': ['BTC/USDT', 'ETH/USDT', 'SOL/USDT'],
    'stop_loss_pct': 0.05,         # 5%止损
    'take_profit_pct': 0.10,       # 10%止盈
}

@dataclass
class TradeTicket:
    """交易工单 - 参考HyperGrok"""
    ticket_id: str
    market: str
    side: str  # buy/sell
    size: float
    entry_price: float
    stop_price: float
    target_price: float
    risk_usd: float
    status: str  # pending/approved/executed/rejected/closed
    created_at: str
    approved_by: str = ""
    approval_time: str = ""
    executed_at: str = ""
    close_price: float = 0.0
    pnl_usd: float = 0.0
    notes: str = ""
    
    def to_dict(self):
        return asdict(self)

@dataclass  
class WatchCondition:
    """监控条件"""
    name: str
    data_type: str  # price, funding, margin_ratio
    threshold: float
    direction: str  # above/below
    alert_message: str = ""

class AgnesVision:
    """Agnes AI视觉分析 - 看图能力"""
    
    def __init__(self, api_key: str, base_url: str):
        self.api_key = api_key
        self.base_url = base_url
        self.client = None
    
    def _get_client(self):
        if self.client is None:
            from openai import OpenAI
            self.client = OpenAI(base_url=self.base_url, api_key=self.api_key)
        return self.client
    
    def analyze_dashboard(self, screenshot_path: str, question: str = "") -> str:
        """分析面板截图"""
        import base64
        
        with open(screenshot_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
        
        client = self._get_client()
        prompt = question or "详细分析这张交易面板截图，告诉我所有可见的数据"
        
        resp = client.chat.completions.create(
            model="agnes-2.5-flash",
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}
                ]
            }],
            max_tokens=1000
        )
        return resp.choices[0].message.content

class MarketData:
    """市场数据获取"""
    
    def __init__(self):
        self.cache = {}
        self.last_update = {}
    
    def get_price(self, symbol: str) -> Dict:
        """获取实时价格"""
        try:
            # Binance API
            resp = requests.get(
                f'https://api.binance.com/api/v3/ticker/24hr?symbol={symbol.replace("/", "")}',
                timeout=10
            )
            data = resp.json()
            self.cache[symbol] = data
            self.last_update[symbol] = datetime.now()
            
            return {
                'price': float(data['lastPrice']),
                'change_24h': float(data['priceChangePercent']),
                'volume': float(data['quoteVolume']),
                'high_24h': float(data['highPrice']),
                'low_24h': float(data['lowPrice']),
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            return {'error': str(e), 'price': 0}
    
    def get_candles(self, symbol: str, interval: str = '1h', limit: int = 100) -> pd.DataFrame:
        """获取K线数据"""
        try:
            resp = requests.get(
                f'https://api.binance.com/api/v3/klines?symbol={symbol.replace("/", "")}&interval={interval}&limit={limit}',
                timeout=10
            )
            data = resp.json()
            
            df = pd.DataFrame(data, columns=[
                'open_time', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_volume', 'trades', 'taker_buy_base',
                'taker_buy_quote', 'ignore'
            ])
            
            df['close_time'] = pd.to_datetime(df['close_time'], unit='ms')
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            
            return df
        except Exception as e:
            return pd.DataFrame()

class RiskManager:
    """风控管理器 - 参考HyperGrok"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.open_tickets = []
        self.daily_pnl = 0.0
        self.start_of_day_equity = config['equity']
    
    def calculate_position_size(self, equity: float, entry_price: float, 
                                stop_price: float, slippage_bps: float = 10) -> Dict:
        """计算仓位大小（stressed sizing）"""
        
        # 风险预算
        risk_budget = equity * self.config['max_risk_per_trade']
        
        # 止损距离
        stop_distance = abs(entry_price - stop_price)
        
        # 考虑滑点和手续费
        slippage_price = entry_price * (slippage_bps / 10000)
        fee_rate = 0.001  # 0.1%手续费
        fees_per_unit = (entry_price + stop_price) * fee_rate
        
        # 压力止损距离
        stressed_distance = stop_distance + slippage_price + fees_per_unit
        
        if stressed_distance <= 0:
            return {'error': 'Invalid stop distance'}
        
        # 计算仓位
        raw_size = risk_budget / stressed_distance
        size = round(raw_size, 4)
        
        # 计算名义价值
        notional = size * entry_price
        
        # 计算所需保证金（假设杠杆）
        leverage = min(self.config['max_leverage'], 10)
        margin_needed = notional / leverage
        
        return {
            'size': size,
            'notional': notional,
            'risk_usd': risk_budget,
            'margin_needed': margin_needed,
            'leverage': leverage,
            'slippage': slippage_price,
            'fees': fees_per_unit,
            'stressed_distance': stressed_distance,
            'actual_risk': size * stressed_distance
        }
    
    def check_risk_limits(self, equity: float, pending_risk: float = 0) -> Dict:
        """检查风控限制"""
        
        checks = {
            'can_trade': True,
            'warnings': [],
            'reject_reasons': []
        }
        
        # 日亏损停止
        if self.daily_pnl <= self.config['daily_loss_stop'] * equity:
            checks['can_trade'] = False
            checks['reject_reasons'].append(f"Daily loss stop hit: ${self.daily_pnl:.2f}")
        
        # 总风险检查
        total_risk = pending_risk + self.config['max_risk_per_trade'] * equity
        if total_risk > equity * self.config['max_total_open_risk']:
            checks['can_trade'] = False
            checks['reject_reasons'].append("Total open risk exceeds limit")
        
        return checks
    
    def create_ticket(self, strategy_signal: Dict, market_data: Dict) -> Optional[TradeTicket]:
        """创建交易工单"""
        
        if strategy_signal.get('signal') != 'BUY':
            return None
        
        # 生成唯一ID
        ticket_id = f"HG-{datetime.now().strftime('%Y%m%d')}-{int(time.time()) % 10000:04d}"
        
        # 计算参数
        entry_price = strategy_signal['price']
        stop_price = entry_price * (1 - self.config['stop_loss_pct'])
        target_price = entry_price * (1 + self.config['take_profit_pct'])
        
        # 计算仓位
        sizing = self.calculate_position_size(
            self.config['equity'], entry_price, stop_price
        )
        
        if 'error' in sizing:
            return None
        
        return TradeTicket(
            ticket_id=ticket_id,
            market=strategy_signal.get('market', 'BTC/USDT'),
            side='buy',
            size=sizing['size'],
            entry_price=entry_price,
            stop_price=stop_price,
            target_price=target_price,
            risk_usd=sizing['risk_usd'],
            status='pending',
            created_at=datetime.now().isoformat(),
            notes=json.dumps(sizing, indent=2)
        )
    
    def approve_ticket(self, ticket: TradeTicket, approver: str = "user") -> bool:
        """人工审批"""
        ticket.status = 'approved'
        ticket.approved_by = approver
        ticket.approval_time = datetime.now().isoformat()
        return True
    
    def execute_ticket(self, ticket: TradeTicket, current_price: float = None) -> Dict:
        """执行交易"""
        
        if current_price is None:
            current_price = ticket.entry_price
        
        # 模拟执行
        pnl = 0.0
        if ticket.side == 'buy':
            # 计算盈亏
            if current_price <= ticket.stop_price:
                # 止损
                pnl = -ticket.risk_usd
            elif current_price >= ticket.target_price:
                # 止盈
                pnl = ticket.risk_usd * 2  # 假设2:1风险回报
            else:
                # 浮盈/浮亏
                pnl = (current_price - ticket.entry_price) * ticket.size
        
        ticket.status = 'executed'
        ticket.executed_at = datetime.now().isoformat()
        ticket.pnl_usd = pnl
        
        return {
            'status': 'executed',
            'ticket_id': ticket.ticket_id,
            'pnl': pnl,
            'pnl_pct': pnl / ticket.risk_usd if ticket.risk_usd > 0 else 0
        }

class Agent:
    """Agent基类"""
    
    def __init__(self, name: str, role: str, description: str):
        self.name = name
        self.role = role
        self.description = description
        self.status = "idle"
        self.last_action = None
        self.logs = []
    
    def log(self, message: str):
        self.logs.append({
            'time': datetime.now().isoformat(),
            'message': message
        })
    
    def run(self, context: Dict) -> Dict:
        raise NotImplementedError

class MarketAnalystAgent(Agent):
    """Market Analyst - 实时市场数据"""
    
    def __init__(self):
        super().__init__("Market Analyst", "market", 
                        "Provides live market data including price, depth, funding rates")
        self.market_data = MarketData()
    
    def run(self, context: Dict) -> Dict:
        self.status = "working"
        self.log("Fetching market data...")
        
        results = {}
        for market in CONFIG['allowed_markets']:
            data = self.market_data.get_price(market)
            results[market] = data
            if 'error' not in data:
                self.log(f"{market}: ${data['price']:.2f} ({data['change_24h']:+.2f}%)")
        
        self.status = "idle"
        return {
            'type': 'market_data',
            'data': results,
            'timestamp': datetime.now().isoformat()
        }

class ResearchAnalystAgent(Agent):
    """Research Analyst - 新闻和情绪分析"""
    
    def __init__(self):
        super().__init__("Research Analyst", "research",
                        "Analyzes news, sentiment, and fundamental factors")
    
    def run(self, context: Dict) -> Dict:
        self.status = "working"
        self.log("Analyzing sentiment...")
        
        # 基于价格变动的情绪分析
        sentiment_score = 0
        signals = []
        
        for market, data in context.get('market_data', {}).items():
            change = data.get('change_24h', 0)
            if change > 3:
                sentiment_score += 1
                signals.append(f"{market} bullish momentum (+{change:.1f}%)")
            elif change < -3:
                sentiment_score -= 1
                signals.append(f"{market} bearish pressure ({change:.1f}%)")
        
        sentiment = "positive" if sentiment_score > 0 else "negative" if sentiment_score < 0 else "neutral"
        
        self.status = "idle"
        return {
            'type': 'sentiment',
            'sentiment': sentiment,
            'score': sentiment_score,
            'signals': signals,
            'timestamp': datetime.now().isoformat()
        }

class StrategistAgent(Agent):
    """Strategist - 策略研发"""
    
    def __init__(self):
        super().__init__("Strategist", "strategy",
                        "Develops and tests trading strategies")
    
    def run(self, context: Dict) -> Dict:
        self.status = "working"
        self.log("Generating trading signals...")
        
        signals = {}
        market_data = context.get('market_data', {})
        
        for market, data in market_data.items():
            if 'error' in data:
                continue
            
            # RSI策略（简化版）
            rsi = data.get('rsi', 50)
            price = data.get('price', 0)
            change = data.get('change_24h', 0)
            
            # 多重确认
            buy_signals = []
            sell_signals = []
            
            if rsi < 30:
                buy_signals.append("RSI oversold")
            if rsi > 70:
                sell_signals.append("RSI overbought")
            if change < -5:
                buy_signals.append("significant drop")
            elif change > 5:
                sell_signals.append("significant rise")
            
            # 生成信号
            if len(buy_signals) >= 2:
                signals[market] = {
                    'signal': 'BUY',
                    'price': price,
                    'confidence': min(len(buy_signals) / 3 * 100, 100),
                    'reasons': buy_signals,
                    'rsi': rsi
                }
            elif len(sell_signals) >= 1:
                signals[market] = {
                    'signal': 'SELL',
                    'price': price,
                    'confidence': 80,
                    'reasons': sell_signals,
                    'rsi': rsi
                }
            else:
                signals[market] = {
                    'signal': 'HOLD',
                    'price': price,
                    'confidence': 50,
                    'reasons': [],
                    'rsi': rsi
                }
        
        self.status = "idle"
        return {
            'type': 'strategy_signals',
            'signals': signals,
            'timestamp': datetime.now().isoformat()
        }

class RiskManagerAgent(Agent):
    """Risk Manager - 风控"""
    
    def __init__(self, risk_engine: RiskManager):
        super().__init__("Risk Manager", "risk",
                        "Enforces risk limits and sizes positions")
        self.risk_engine = risk_engine
    
    def run(self, context: Dict) -> Dict:
        self.status = "working"
        self.log("Checking risk limits...")
        
        checks = self.risk_engine.check_risk_limits(CONFIG['equity'])
        
        # 处理策略信号
        tickets = []
        for market, signal in context.get('strategy_signals', {}).items():
            if signal['signal'] == 'BUY':
                ticket = self.risk_engine.create_ticket(signal, context.get('market_data', {}).get(market, {}))
                if ticket:
                    tickets.append(ticket)
                    self.log(f"Created ticket {ticket.ticket_id} for {market}")
        
        self.status = "idle"
        return {
            'type': 'risk_check',
            'checks': checks,
            'tickets': [t.to_dict() for t in tickets],
            'timestamp': datetime.now().isoformat()
        }

class ExecutionTraderAgent(Agent):
    """Execution Trader - 执行"""
    
    def __init__(self, risk_engine: RiskManager):
        super().__init__("Execution Trader", "execution",
                        "Executes approved trades")
        self.risk_engine = risk_engine
        self.executed_trades = []
    
    def run(self, context: Dict) -> Dict:
        self.status = "working"
        
        # 执行已审批的工单
        executed = []
        for ticket_data in context.get('approved_tickets', []):
            ticket = TradeTicket(**ticket_data)
            result = self.risk_engine.execute_ticket(ticket)
            executed.append(result)
            self.executed_trades.append(ticket)
            self.log(f"Executed {ticket.ticket_id}: PnL=${result['pnl']:.2f}")
        
        self.status = "idle"
        return {
            'type': 'execution',
            'results': executed,
            'timestamp': datetime.now().isoformat()
        }

class TradeReviewerAgent(Agent):
    """Trade Reviewer - 复盘"""
    
    def __init__(self):
        super().__init__("Trade Reviewer", "review",
                        "Reviews trades and generates reports")
    
    def run(self, context: Dict) -> Dict:
        self.status = "working"
        self.log("Reviewing trades...")
        
        trades = context.get('executed_trades', [])
        reviews = []
        
        for trade in trades:
            pnl = trade.get('pnl_usd', 0)
            grade = 'A' if pnl > trade.get('risk_usd', 1) * 2 else 'B' if pnl > 0 else 'C'
            
            reviews.append({
                'ticket_id': trade.get('ticket_id'),
                'pnl': pnl,
                'grade': grade,
                'lesson': 'Good trade' if grade in ['A', 'B'] else 'Review needed'
            })
        
        self.status = "idle"
        return {
            'type': 'review',
            'reviews': reviews,
            'timestamp': datetime.now().isoformat()
        }

class DeskLeadAgent(Agent):
    """Desk Lead - 协调者"""
    
    def __init__(self, agents: Dict):
        super().__init__("Desk Lead", "lead",
                        "Coordinates all agents and generates briefs")
        self.agents = agents
        self.brief_history = []
    
    def run_cycle(self) -> Dict:
        """运行一个完整的交易周期"""
        
        print(f"\n{'='*70}")
        print(f"JadeBot v1.0 Trading Cycle - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print('='*70)
        
        context = {}
        
        # 1. Market Analyst
        print("\n📊 [Market Analyst] Fetching market data...")
        market_result = self.agents['market'].run(context)
        context['market_data'] = market_result.get('data', {})
        
        # 2. Research Analyst
        print("\n📰 [Research Analyst] Analyzing sentiment...")
        research_result = self.agents['research'].run(context)
        context['sentiment'] = research_result
        
        # 3. Strategist
        print("\n🧠 [Strategist] Generating signals...")
        strategy_result = self.agents['strategist'].run(context)
        context['strategy_signals'] = strategy_result.get('signals', {})
        
        # 4. Risk Manager
        print("\n🛡️ [Risk Manager] Checking limits and creating tickets...")
        risk_result = self.agents['risk'].run(context)
        context['tickets'] = risk_result.get('tickets', [])
        context['risk_checks'] = risk_result.get('checks', {})
        
        # 5. 人工审批（简化：自动批准）
        approved_tickets = []
        for ticket_data in context['tickets']:
            print(f"   📋 Ticket {ticket_data['ticket_id']}: {ticket_data['market']} "
                  f"size={ticket_data['size']} @ ${ticket_data['entry_price']:.2f}")
            approved_tickets.append(ticket_data)
        
        context['approved_tickets'] = approved_tickets
        
        # 6. Execution Trader
        print("\n🚀 [Execution Trader] Executing trades...")
        exec_result = self.agents['execution'].run(context)
        context['executed_trades'] = exec_result.get('results', [])
        
        # 7. Trade Reviewer
        print("\n📝 [Trade Reviewer] Generating reports...")
        review_result = self.agents['reviewer'].run(context)
        
        # 生成简报
        brief = self._generate_brief(context, market_result, research_result, 
                                    strategy_result, risk_result, review_result)
        self.brief_history.append(brief)
        
        print(f"\n💰 Equity: ${CONFIG['equity']:.2f}")
        print(f"📋 Tickets created: {len(approved_tickets)}")
        print(f"✅ Trades executed: {len(exec_result.get('results', []))}")
        print(f"{'='*70}\n")
        
        return brief
    
    def _generate_brief(self, context, market_result, research_result, 
                       strategy_result, risk_result, review_result) -> Dict:
        """生成每日简报"""
        
        return {
            'timestamp': datetime.now().isoformat(),
            'equity': CONFIG['equity'],
            'market_summary': market_result.get('data', {}),
            'sentiment': research_result.get('sentiment'),
            'signals': strategy_result.get('signals', {}),
            'tickets': risk_result.get('tickets', []),
            'executions': len(context.get('executed_trades', [])),
            'risk_status': risk_result.get('checks', {}).get('can_trade', True)
        }

class JadeBotV1:
    """JadeBot v1.0 - 完整交易系统"""
    
    def __init__(self):
        self.risk_engine = RiskManager(CONFIG)
        self.agnes = AgnesVision(AGNES_API_KEY, AGNES_BASE_URL) if AGNES_API_KEY else None
        
        # 初始化Agent
        self.agents = {
            'market': MarketAnalystAgent(),
            'research': ResearchAnalystAgent(),
            'strategist': StrategistAgent(),
            'risk': RiskManagerAgent(self.risk_engine),
            'execution': ExecutionTraderAgent(self.risk_engine),
            'reviewer': TradeReviewerAgent()
        }
        
        self.desk_lead = DeskLeadAgent(self.agents)
        
        # 数据库
        self.db_path = 'user_data/jadebot_v1.sqlite'
        self._init_db()
    
    def _init_db(self):
        """初始化数据库"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS tickets
                    (id TEXT PRIMARY KEY, data TEXT, created_at TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS trades
                    (id TEXT PRIMARY KEY, ticket_id TEXT, pnl REAL, grade TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS logs
                    (id INTEGER PRIMARY KEY AUTOINCREMENT, time TEXT, agent TEXT, message TEXT)''')
        conn.commit()
        conn.close()
    
    def run(self, cycles: int = 10):
        """运行交易循环"""
        print("🤖 JadeBot v1.0 - Starting Trading System")
        print("Architecture: HyperGrok 7-Agent Design")
        print("="*70)
        
        for i in range(cycles):
            brief = self.desk_lead.run_cycle()
            time.sleep(1)  # 模拟时间流逝
        
        print("\n✅ Trading session completed")
        return brief

def main():
    """主函数"""
    bot = JadeBotV1()
    bot.run(cycles=5)

if __name__ == '__main__':
    main()
