# Freqtrade 2026.9 配置陷阱

## 问题: StaticPairList requires pair_whitelist to be set

### 原因
freqtrade 2026.9 要求 `pair_whitelist` 在 `exchange` 对象内部，不是顶层。

### 错误配置 ❌
```json
{
    "pair_whitelist": ["BTC/USDT"],
    "pairlists": [{"method": "StaticPairList"}]
}
```

### 正确配置 ✅
```json
{
    "exchange": {
        "name": "binance",
        "pair_whitelist": ["BTC/USDT", "ETH/USDT"]
    },
    "pairlists": [{"method": "StaticPairList"}]
}
```

### 验证命令
```bash
freqtrade show-config --config config_final.json
freqtrade test-pairlist --config config_final.json
```

### 来源
代码位置: `~/venv/lib/python3.12/site-packages/freqtrade/configuration/config_validation.py:189`
```python
if (
    isinstance(pl, dict)
    and pl.get("method") == "StaticPairList"
    and not conf.get("exchange", {}).get("pair_whitelist")
):
    raise ConfigurationError("StaticPairList requires pair_whitelist to be set.")
```