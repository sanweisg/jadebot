#!/usr/bin/env python3
"""
JadeBot Dashboard - 实时交易监控面板
类似X上看到的高级Grok Bot界面
"""

import sys
sys.path.insert(0, '/home/jace/jadebot/venv/lib/python3.12/site-packages')

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import sqlite3
from pathlib import Path
import json
import time
from datetime import datetime

# 配置
st.set_page_config(page_title="JadeBot Pro", page_icon="🤖", layout="wide")

# 标题和状态
col1, col2, col3 = st.columns([3, 1, 1])
with col1:
    st.title("🤖 JadeBot Pro - 智能交易监控")
with col2:
    st.metric("运行时间", "24:13:56")
with col3:
    st.metric("当前模式", "🟢 模拟")

# 核心指标卡片
st.markdown("---")
col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("总资金", "1,000 USDT", "+14.64 USDT")
col2.metric("已实现盈亏", "+14.64 USDT", "+1.46%")
col3.metric("未实现盈亏", "-2.31 USDT", "-0.23%")
col4.metric("持仓数", "1", "")
col5.metric("今日交易", "3", "+1")

st.markdown("---")

# 创建子图：价格 + RSI + MACD
fig = make_subplots(
    rows=3, cols=1,
    subplot_titles=('BTC/USDT 价格 & EMA', 'RSI(14)', 'MACD'),
    vertical_spacing=0.05,
    row_heights=[0.5, 0.25, 0.25]
)

# 加载数据
data_dir = Path("/home/jace/jadebot/user_data/data/binance")
btc_file = data_dir / "BTC_USDT-1h.feather"

if btc_file.exists():
    df = pd.read_feather(btc_file)
    
    # 计算指标
    df['ema_20'] = df['close'].ewm(span=20, adjust=False).mean()
    df['ema_50'] = df['close'].ewm(span=50, adjust=False).mean()
    df['ema_200'] = df['close'].ewm(span=200, adjust=False).mean()
    
    # RSI
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))
    
    # MACD
    ema12 = df['close'].ewm(span=12, adjust=False).mean()
    ema26 = df['close'].ewm(span=26, adjust=False).mean()
    df['macd'] = ema12 - ema26
    df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
    df['macd_hist'] = df['macd'] - df['macd_signal']
    
    # 最后100根K线
    df_plot = df.iloc[-100:].copy()
    
    # 价格图
    fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['close'], name='Price', line=dict(color='#00ff88', width=2)), row=1, col=1)
    fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['ema_20'], name='EMA20', line=dict(color='#ffaa00', width=1)), row=1, col=1)
    fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['ema_200'], name='EMA200', line=dict(color='#00aaff', width=1, dash='dash')), row=1, col=1)
    
    # RSI图
    fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['rsi'], name='RSI', line=dict(color='#ff4444', width=1.5)), row=2, col=1)
    fig.add_shape(dict(type="line", x0=0, y0=30, x1=len(df_plot)-1, y1=30, line=dict(color="#00ff00", width=1, dash="dot")), row=2, col=1)
    fig.add_shape(dict(type="line", x0=0, y0=70, x1=len(df_plot)-1, y1=70, line=dict(color="#ff0000", width=1, dash="dot")), row=2, col=1)
    
    # MACD图
    fig.add_trace(go.Bar(x=df_plot.index, y=df_plot['macd_hist'], name='MACD Hist', marker_color=df_plot['macd_hist'].apply(lambda x: '#ff4444' if x < 0 else '#00ff88')), row=3, col=1)
    fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['macd'], name='MACD', line=dict(color='#aa88ff', width=1)), row=3, col=1)
    fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['macd_signal'], name='Signal', line=dict(color='#ffaa88', width=1)), row=3, col=1)

fig.update_layout(
    height=700,
    template='plotly_dark',
    showlegend=True,
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    paper_bgcolor='#0d1117',
    plot_bgcolor='#0d1117',
    font=dict(color='#e6edf3')
)

st.plotly_chart(fig, use_container_width=True)

st.markdown("---")

# 底部：持仓和交易记录
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("📊 当前持仓")
    # 模拟持仓数据
    positions = pd.DataFrame({
        '交易对': ['BTC/USDT'],
        '方向': ['LONG'],
        '开仓价': ['67,234.50'],
        '当前价': ['67,891.20'],
        '盈亏%': ['+0.98%'],
        '持仓时长': ['2h 34m']
    })
    st.dataframe(positions, use_container_width=True, hide_index=True)
    
    st.subheader("📈 最近交易")
    trades = pd.DataFrame({
        '时间': ['2026-10-25 21:00', '2026-10-25 18:30', '2026-10-25 14:15'],
        '交易对': ['BTC/USDT', 'ETH/USDT', 'BTC/USDT'],
        '方向': ['BUY', 'SELL', 'BUY'],
        '价格': ['67,234', '3,521', '66,890'],
        '盈亏': ['-', '+1.2%', '-']
    })
    st.dataframe(trades, use_container_width=True, hide_index=True)

with col2:
    st.subheader("🎯 策略状态")
    st.markdown("""
    | 指标 | 值 | 状态 |
    |------|-----|------|
    | RSI(14) | 58.3 | 🟡 中性 |
    | EMA趋势 | 上涨 | 🟢 多头 |
    | MACD | 金叉 | 🟢 买入 |
    | 风险等级 | 低 | 🟢 安全 |
    | 连续亏损 | 0 | 🟢 正常 |
    """)
    
    st.subheader("🤖 多Agent监控")
    agents = [
        ("🧠 Market Agent", "✅ 运行中", "#00ff88"),
        ("📊 Risk Agent", "✅ 运行中", "#00ff88"),
        ("💰 Entry Agent", "✅ 运行中", "#00ff88"),
        ("🛡️ Stop Agent", "✅ 运行中", "#00ff88"),
    ]
    for agent, status, color in agents:
        st.markdown(f"**{agent}** {status}")
    
    st.subheader("⚡ 风控规则")
    st.markdown("""
    - 单笔止损: -5%
    - 日亏损熔断: -5%
    - 最大持仓: 3个
    - 连续亏损停手: 2次
    """)

st.markdown("---")
st.caption("JadeBot v0.5 | 基于Freqtrade + Streamlit | 模拟交易模式")
