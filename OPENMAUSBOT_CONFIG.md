# OpenMausBot + Agnes AI 配置指南

## 已完成
✅ REA逆向Grok Bot（详见 GROK_BOT_REA_REPORT.md）
✅ 创建OpenMausBot配置文件
✅ 配置Agnes AI作为自定义Provider

## 下一步：安装OpenMausBot

### 方法1：使用预编译包（推荐）
```bash
# 下载Windows版
wget https://github.com/milind-soni/OpenMausBot/releases/latest/download/openmausbot-windows-x64.exe
# 运行安装程序

# 或下载Linux版
wget https://github.com/milind-soni/OpenMausBot/releases/latest/download/openmausbot-linux-x86_64.AppImage
chmod +x openmausbot-linux-x86_64.AppImage
./openmausbot-linux-x86_64.AppImage
```

### 方法2：从源码构建
```bash
cd ~/jadebot/OpenMausBot
npm install -g pnpm
pnpm install
pnpm build
pnpm start
```

## 配置Agnes API

### 编辑配置文件
```bash
nano ~/.openmausbot/config.json
```

### 添加Agnes配置
```json
{
  "instances": {
    "agnes": {
      "driver": "openai-compat",
      "displayName": "Agnes AI",
      "environment": {
        "AGNES_API_KEY": "sk-0dQ..."
      },
      "config": {
        "url": "https://apihub.agnes-ai.com/v1",
        "apiKeyEnv": "AGNES_API_KEY",
        "model": "agnes-2.5-flash"
      }
    }
  }
}
```

### 或者使用CLI配置
```bash
openmausbot setup
# 选择 "Custom Provider"
# 输入URL: https://apihub.agnes-ai.com/v1
# 输入API Key: sk-0dQ...
# 输入Model: agnes-2.5-flash
```

## 创建交易Agent

### 创建第一个Agent
1. 打开OpenMausBot应用
2. 点击 "New Bot"
3. 选择模型: Agnes AI / agnes-2.5-flash
4. 设置角色: "Market Scanner"
5. 添加工具: Binance API, WebSocket

### 批量创建350个Agent
创建脚本:
```bash
#!/bin/bash
# create_agents.sh

for i in {1..350}; do
    agent_type=$(get_agent_type $i)
    echo "Creating Agent #$i: $agent_type"
    openmausbot create --name "agent-$i" --type $agent_type --model agnes-2.5-flash
done
```

## 集成Freqtrade

### 1. 修改JadeBot配置
```bash
# 在 config_final.json 中添加
{
  "openmausbot_integration": true,
  "agent_count": 350,
  "api_key": "your-openmausbot-api-key"
}
```

### 2. 创建通信接口
```python
# jadebot_openmausbot_bridge.py
import requests
import json

class OpenMausBotBridge:
    def __init__(self, api_url, api_key):
        self.api_url = api_url
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        })
    
    def send_signal(self, signal_data):
        """发送交易信号到OpenMausBot"""
        response = self.session.post(
            f'{self.api_url}/agents/trading/signal',
            json=signal_data
        )
        return response.json()
    
    def get_agent_status(self, agent_id):
        """获取Agent状态"""
        response = self.session.get(f'{self.api_url}/agents/{agent_id}')
        return response.json()
```

## 运行测试

### 启动OpenMausBot
```bash
openmausbot serve --port 3000
```

### 启动JadeBot
```bash
cd ~/jadebot
source venv/bin/activate
python jadebot_v2.py
```

### 验证连接
```bash
# 测试Agnes API
curl https://apihub.agnes-ai.com/v1/chat/completions \
  -H "Authorization: Bearer [REDACTED_BEARER]" \
  -H "Content-Type: application/json" \
  -d '{"model": "agnes-2.5-flash", "messages": [{"role": "user", "content": "Hello"}]}'
```

## 注意事项

### 1. API密钥安全
- 不要在Git中提交API密钥
- 使用环境变量存储密钥
- 定期轮换密钥

### 2. 性能优化
- 350个Agent需要足够的服务器资源
- 建议：16核CPU + 32GB RAM + SSD
- 使用Docker容器化部署

### 3. 成本控制
- Agnes API有免费额度（20 RPM）
- 超出后按量计费
- 建议使用缓存减少API调用

## 参考资料

- [OpenMausBot GitHub](https://github.com/milind-soni/OpenMausBot)
- [Rakazo GitHub](https://github.com/elie222/rakazo)
- [Agnes AI Docs](https://wiki.agnes-ai.com/en/docs/overview)
- [Grok Bot架构分析](GROK_BOT_REA_REPORT.md)

完成时间: 2026-10-26
作者: JadeBot Team
版本: v3.0
