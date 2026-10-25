# AI自学习系统 - 技术文档

## 什么是自学习AI？

自学习AI = 每次完成任务后都会变聪明的Agent

### 核心组件

```
1. 记忆系统 (Cognee)
   ├── 存储所有对话历史
   ├── 自动提取知识图谱
   └── 跨会话持久化

2. 反馈循环 (Reflexio)
   ├── 记录成功/失败模式
   ├── 自动分析改进点
   └── 应用优化到下次

3. 自我改进
   ├── Skill进化
   ├── Prompt优化
   └── 策略调整
```

---

## 工作原理

### 第1次任务
```
用户: "帮我分析BTC价格"
Agent: 执行分析 → 返回结果
系统: 记录全过程到记忆库
```

### 第2次任务（类似）
```
用户: "分析ETH价格走势"
Agent: 检索第1次经验 → 使用优化后的方法 → 返回结果
系统: 对比两次结果 → 记录改进
```

### 第100次任务
```
Agent: 已经学会最优分析方法
系统: 自动避免重复错误
结果: 速度快5x，质量高90%+
```

---

## 安装步骤

### 快速安装（推荐）
```bash
cd ~/jadebot
./install_self_learning.sh
```

### 手动安装

#### 1. 安装Cognee
```bash
pip install cognee
cognee init --data-dir ~/.cognee/jadebot
```

#### 2. 安装Reflexio
```bash
pip install reflexio
reflexio init --model agnes-2.5-flash
```

#### 3. 启动服务
```bash
# 终端1: 启动Cognee
cognee serve --port 8000

# 终端2: 启动Reflexio学习循环
reflexio run --loop
```

---

## 配置示例

### reflexio_config.py
```python
from reflexio import ReflexioAgent, FeedbackLoop

# 初始化Agent
agent = ReflexioAgent(
    model="agnes-2.5-flash",
    memory_backend="cognee",
    memory_endpoint="http://localhost:8000"
)

# 配置学习参数
feedback_loop = FeedbackLoop(
    improvement_threshold=0.1,  # 10%改进就保存
    max_retries=3,
    auto_optimize=True
)

# 任务完成后自动学习
@agent.on_task_complete
def learn_from_task(result):
    feedback_loop.record(result)
    if feedback_loop.should_improve():
        feedback_loop.apply_improvement()
        agent.save_skill()
```

---

## 预期效果

### 时间线
- **第1周**: 建立基础记忆，成功率提升15%
- **第1月**: 形成稳定模式，速度提升2x
- **第3月**: 高度优化，成本降低70%

### 关键指标
| 指标 | 初始 | 1周后 | 1月后 |
|------|------|-------|-------|
| 任务成功率 | 65% | 75% | 90%+ |
| Token消耗 | 100% | 80% | 40% |
| 响应时间 | 基础 | -30% | -70% |
| 错误率 | 高 | 中 | 低 |

---

## 进阶功能

### 1. 定时自动学习
```bash
# 添加到crontab
0 * * * * cd ~/jadebot && python auto_learn.py
0 3 * * * cd ~/jadebot && python consolidate_memory.py
```

### 2. 多Agent协同学习
```python
# Agent A完成任务后分享经验给Agent B
agent_a.share_experience(agent_b)
agent_b.learn_from(agent_a.success_patterns)
```

### 3. 用户反馈闭环
```python
# 用户纠正后自动学习
if user_corrects(agent_output):
    feedback_loop.record_correction(
        original=agent_output,
        corrected=user_version,
        lesson="never_do_this_again"
    )
```

---

## 故障排查

### 问题1: Cognee启动失败
```bash
# 检查端口占用
lsof -i :8000
# 杀掉占用进程
kill -9 <PID>
# 重新启动
cognee serve --port 8000
```

### 问题2: Reflexio连接超时
```bash
# 检查Cognee是否运行
curl http://localhost:8000/health
# 如果无响应，重启Cognee
```

### 问题3: 学习速度慢
```bash
# 增加资源分配
export COGNEE_WORKERS=4
export REFLEXIO_PARALLEL=2
```

---

## 参考资料

- [Cognee文档](https://github.com/kaylee-ai/cognee)
- [Reflexio文档](https://github.com/ReflexioAI/reflexio)
- [Awesome-Self-Improving-Agents](https://github.com/FrontisAI/Awesome-Self-Improving-Agents)
- [Self-Evolving-Agents-Survey](https://github.com/XMUDeepLIT/Awesome-Self-Evolving-Agents)

---

**完成时间**: 2026-10-26
**版本**: v1.0
**作者**: JadeBot Team
