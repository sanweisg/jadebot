#!/usr/bin/env python3
"""
JadeBot Multi-Agent System - 修正版
模仿Grok Bot的Agent架构 + 风控规则 + 连续亏损停手
"""

import json
import sqlite3
import time
from datetime import datetime
from pathlib import Path
import pandas as pd
import talib.abstract as ta
from typing import List, Dict, Optional

class JadeAgent:
    """单个Agent基类"""
    def __init__(self, name: str):
        self.name = name
        self.status = "idle"
        self.last_action = None
    
    def analyze(self, data: Dict) -> Dict:
        raise NotImplementedError

class MarketAgent(JadeAgent):
    """市场监控Agent - 分析趋势和信号"""
    def __init__(self):
        super().__init__("Market Agent")
    
    def analyze(self, df: pd.DataFrame) -> Dict:
        """分析市场数据，返回信号"""
        if len(df) == 0:
            return {"action": "HOLD", "price": 0, "rsi": 50}
        
        latest = df.iloc[-1]
        
        # RSI分析
        rsi = latest['rsi']
        rsi_signal = "neutral"
        if rsi < 30:
            rsi_signal = "oversold"
        elif rsi > 70:
            rsi_signal = "overbought"
        
        # EMA趋势分析
        trend = "bearish" if latest['close'] < latest['ema_200'] else "bullish"
        
        # MACD分析
        macd_signal = "neutral"
        if latest['macd'] > latest['macd_signal'] and latest['macd_hist'] > 0:
            macd_signal = "bullish_crossover"
        elif latest['macd'] < latest['macd_signal'] and latest['macd_hist'] < 0:
            macd_signal = "bearish_crossover"
        
        # 综合评分
        score = 0
        if trend == "bullish": score += 2
        if rsi_signal == "oversold": score += 3
        elif rsi_signal == "overbought": score -= 3
        if macd_signal == "bullish_crossover": score += 2
        elif macd_signal == "bearish_crossover": score -= 2
        
        return {
            "timestamp": str(datetime.now()),
            "pair": "BTC/USDT",
            "price": latest['close'],
            "rsi": round(rsi, 2),
            "trend": trend,
            "macd_signal": macd_signal,
            "composite_score": score,
            "action": "BUY" if score >= 4 else ("SELL" if score <= -4 else "HOLD"),
            "confidence": min(abs(score) / 10 * 100, 100)
        }

class RiskAgent(JadeAgent):
    """风险管理Agent - 控制仓位和止损"""
    def __init__(self):
        super().__init__("Risk Agent")
        self.max_drawdown = 0.05  # 5%日止损
        self.max_position_size = 0.10  # 单笔10%
        self.consecutive_losses = 0
        self.total_trades = 0
    
    def check_risk(self, portfolio: Dict) -> Dict:
        """检查风控规则"""
        risk_report = {
            "timestamp": str(datetime.now()),
            "portfolio_value": portfolio.get("balance", 1000),
            "daily_pnl": portfolio.get("daily_pnl", 0),
            "consecutive_losses": self.consecutive_losses,
            "can_trade": True,
            "stop_trading": False,
            "warnings": []
        }
        
        # 检查日亏损熔断
        if risk_report["daily_pnl"] <= -self.max_drawdown * 1000:
            risk_report["stop_trading"] = True
            risk_report["warnings"].append("⚠️ 日亏损达到熔断线(-5%)，停止交易")
        
        # 检查连续亏损（2次停手）
        if self.consecutive_losses >= 2:
            risk_report["stop_trading"] = True
            risk_report["warnings"].append("⚠️ 连续亏损2次，暂停交易")
        
        return risk_report

class EntryAgent(JadeAgent):
    """入场Agent - 决定何时买入"""
    def __init__(self):
        super().__init__("Entry Agent")
    
    def evaluate_entry(self, market_signal: Dict, risk_report: Dict) -> Dict:
        """评估入场信号"""
        if risk_report.get("stop_trading"):
            return {"action": "NO_TRADE", "reason": "风控阻止"}
        
        # 多重确认才入场
        entries = []
        if market_signal["action"] == "BUY":
            entries.append("BUY")
        if market_signal["rsi"] < 35:
            entries.append("RSI_OVERSOLD")
        if market_signal["macd_signal"] == "bullish_crossover":
            entries.append("MACD_CROSS")
        
        # 至少2个条件确认
        if len(entries) >= 2:
            return {
                "action": "BUY",
                "entry_price": market_signal["price"],
                "confidence": market_signal["confidence"],
                "confluence": entries,
                "reason": f"多因子确认: {', '.join(entries)}"
            }
        
        return {"action": "WAIT", "reason": "信号不充分"}

class ExitAgent(JadeAgent):
    """出场Agent - 决定何时卖出"""
    def __init__(self):
        super().__init__("Exit Agent")
    
    def evaluate_exit(self, position: Dict, market_signal: Dict) -> Dict:
        """评估出场条件"""
        entry_price = position["entry_price"]
        current_price = market_signal["price"]
        pnl_pct = (current_price - entry_price) / entry_price
        
        # 止盈条件
        if pnl_pct >= 0.10:  # 10%止盈
            return {"action": "SELL", "reason": "达到止盈目标(10%)", "pnl": pnl_pct}
        elif pnl_pct >= 0.05 and market_signal["rsi"] > 65:  # 5%利润+RSI超买
            return {"action": "SELL", "reason": "部分止盈+RSI超买", "pnl": pnl_pct}
        
        # 止损条件
        if pnl_pct <= -0.05:  # 5%止损
            return {"action": "SELL", "reason": "触发止损(-5%)", "pnl": pnl_pct}
        
        # 趋势反转
        if market_signal["action"] == "SELL" and market_signal["confidence"] > 70:
            return {"action": "SELL", "reason": "趋势反转信号", "pnl": pnl_pct}
        
        return {"action": "HOLD", "pnl": pnl_pct}

class JadeBot:
    """JadeBot主控制器 - 协调所有Agent"""
    def __init__(self):
        self.agents = {
            "market": MarketAgent(),
            "risk": RiskAgent(),
            "entry": EntryAgent(),
            "exit": ExitAgent()
        }
        self.portfolio = {
            "balance": 1000,
            "daily_pnl": 0,
            "positions": [],
            "trades": []
        }
        self.is_running = False
        self.loop_count = 0
    
    def run_cycle(self, df: pd.DataFrame) -> Dict:
        """执行一个交易周期"""
        self.loop_count += 1
        
        # 1. 市场Agent分析
        market_signal = self.agents["market"].analyze(df)
        
        # 2. 风控Agent检查
        risk_report = self.agents["risk"].check_risk(self.portfolio)
        
        # 3. 如果没有持仓，评估入场
        if not self.portfolio["positions"]:
            entry_decision = self.agents["entry"].evaluate_entry(market_signal, risk_report)
            if entry_decision["action"] == "BUY" and not risk_report["stop_trading"]:
                position = {
                    "pair": "BTC/USDT",
                    "entry_price": market_signal["price"],
                    "size": 100,
                    "entry_time": market_signal["timestamp"],
                    "status": "open"
                }
                self.portfolio["positions"].append(position)
                self.portfolio["trades"].append({
                    "type": "ENTRY",
                    "price": market_signal["price"],
                    "time": market_signal["timestamp"],
                    "reason": entry_decision["reason"]
                })
        
        # 4. 如果有持仓，评估出场
        else:
            for pos in self.portfolio["positions"]:
                if pos["status"] == "open":
                    exit_decision = self.agents["exit"].evaluate_exit(pos, market_signal)
                    if exit_decision["action"] == "SELL":
                        pos["status"] = "closed"
                        pos["exit_price"] = market_signal["price"]
                        pos["exit_time"] = market_signal["timestamp"]
                        pos["pnl"] = exit_decision["pnl"]
                        
                        self.portfolio["daily_pnl"] += pos["pnl"] * pos["size"]
                        self.portfolio["trades"].append({
                            "type": "EXIT",
                            "price": market_signal["price"],
                            "pnl_pct": pos["pnl"],
                            "time": market_signal["timestamp"],
                            "reason": exit_decision["reason"]
                        })
                        
                        # 更新连续亏损计数
                        if pos["pnl"] < 0:
                            self.agents["risk"].consecutive_losses += 1
                        else:
                            self.agents["risk"].consecutive_losses = 0
        
        return {
            "cycle": self.loop_count,
            "market": market_signal,
            "risk": risk_report,
            "portfolio": self.portfolio
        }

# 主程序
if __name__ == "__main__":
    bot = JadeBot()
    
    # 加载数据
    data_dir = Path("/home/jace/jadebot/user_data/data/binance")
    btc_file = data_dir / "BTC_USDT-1h.feather"
    
    if btc_file.exists():
        df = pd.read_feather(btc_file)
        df['ema_200'] = ta.EMA(df, timeperiod=200)
        df['rsi'] = ta.RSI(df, timeperiod=14)
        df['ema_20'] = ta.EMA(df, timeperiod=20)
        
        # 计算MACD
        ema12 = df['close'].ewm(span=12, adjust=False).mean()
        ema26 = df['close'].ewm(span=26, adjust=False).mean()
        df['macd'] = ema12 - ema26
        df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
        df['macd_hist'] = df['macd'] - df['macd_signal']
        
        print("=" * 70)
        print("🤖 JadeBot Multi-Agent System 启动")
        print("=" * 70)
        print(f"数据范围: {df['close'].index[0]} 到 {df['close'].index[-1]}")
        print(f"K线数量: {len(df)}")
        print()
        
        # 模拟运行最后一个完整周期
        print("📊 运行模拟交易...\n")
        cycle_data = bot.run_cycle(df)
        
        market = cycle_data["market"]
        risk = cycle_data["risk"]
        
        print(f"✅ 周期 {cycle_data['cycle']}:")
        print(f"   价格: ${market['price']:.2f}")
        print(f"   RSI: {market['rsi']:.2f}")
        print(f"   趋势: {market['trend']}")
        print(f"   建议: {market['action']}")
        print(f"   置信度: {market['confidence']:.1f}%")
        print()
        print(f"🛡️  风控状态:")
        print(f"   日盈亏: ${risk['daily_pnl']:.2f}")
        print(f"   连续亏损: {risk['consecutive_losses']}次")
        print(f"   可交易: {'✅ 是' if not risk['stop_trading'] else '🛑 否'}")
        if risk['warnings']:
            for w in risk['warnings']:
                print(f"   ⚠️  {w}")
        print()
        print(f"💼 持仓状态:")
        open_positions = [p for p in bot.portfolio['positions'] if p['status'] == 'open']
        print(f"   持仓数: {len(open_positions)}")
        print(f"   可用资金: ${1000 - sum(p['size'] for p in open_positions):.2f} USDT")
        print()
        
        # 显示交易历史
        if bot.portfolio['trades']:
            print("📜 最近交易:")
            for trade in bot.portfolio['trades'][-5:]:
                print(f"   [{trade['type']}] ${trade['price']:.2f} - {trade.get('reason', '')}")
        
        print("\n" + "=" * 70)
        print("✅ 多Agent系统运行完成")
        print("=" * 70)
        print("\n💡 如何运行实时模拟:")
        print("   cd ~/jadebot")
        print("   source venv/bin/activate")
        print("   python multi_agent.py")
        print("\n📊 要启动Freqtrade真实模拟:")
        print("   freqtrade trade --strategy SimpleStableRSI --config config_final.json")
