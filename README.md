# scicalc-agent

**工具能让大模型"算得对"吗？—— 一个 ReAct 智能体的消融实验**

大模型单独做数值计算经常"自信地算错"：它本质是语言模型，不是计算器。这个项目给大模型装上工具（计算器 + Python 代码执行），让它走 `Thought → Action → Observation` 循环去算题，然后用一个**消融实验**回答两个问题：

1. 加上工具，准确率到底提升多少？（裸 LLM vs 带工具 Agent）
2. 答错之后让它"反思重试"（Reflexion），还能救回多少？

## 三种求解方式（消融对照）

| 方式 | 说明 |
|------|------|
| `baseline` | 裸 LLM，不给任何工具，直接要答案 |
| `tools` | ReAct 智能体，能调用 calculator / python 两个工具 |
| `reflexion` | 在 `tools` 基础上，答错了把失败原因喂回去，反思后重试（Shinn et al. 2023 的思路） |

三者跑在同一份评测集上，差异就纯粹来自"有没有工具、有没有反思"。

## 架构

```
            ┌────────────────────────────┐
   问题 ──▶ │  LLM（DeepSeek / Qwen / …） │
            │  输出 Thought + Action      │
            └─────────────┬──────────────┘
                          │ Action
                          ▼
            ┌────────────────────────────┐
            │  tools.py                  │
            │  calculator / python       │
            └─────────────┬──────────────┘
                          │ Observation
                          ▼
            （喂回 LLM 循环，直到 Final Answer）

   reflexion：答错 → 把"你上一次答案是 X，错了"喂回去 → 重来一遍
```

## 快速开始

```bash
pip install -r requirements.txt

export LLM_API_KEY=sk-你的key          # 默认 DeepSeek，改 base_url 可换 Qwen/Kimi/OpenAI
export LLM_BASE_URL=https://api.deepseek.com/v1
export LLM_MODEL=deepseek-chat

python run_demo.py                     # 同一题看裸 LLM vs 智能体的差别
python eval.py --trials 1              # 跑完整消融实验
```

不设 key 先跑冒烟测试：

```bash
python tests/test_smoke.py
```

## 评测方法

- **评测集**：22 道科学计算题，难度分层——简单题（纯算术、单位换算）到难题（多步推理、单位陷阱、刁钻数字）。故意让"裸 LLM"在难题上出错，消融才有区分度。
- **判对标准**：`|answer - expected| <= tol`（绝对误差）
- **错误归因**：`wrong_answer`（答了但错）、`parse_error`（输出没法解析）、`max_steps`（步数用完）、`tool_error`（工具报错且没答对）

## 结果（DeepSeek-chat 实测）

`python eval.py --trials 1` 的真实输出：

| 求解方式 | 成功率 | 平均步数 | 平均 token/题 | 错误分布 |
|---------|--------|---------|--------------|---------|
| baseline（裸 LLM） | 95.5%（21/22） | 1.00 | 57 | wrong_answer ×1 |
| tools（ReAct 智能体） | 100%（22/22） | 1.09 | 409 | 无 |
| reflexion（+反思重试） | 100%（22/22） | 1.09 | 408 | 无 |

唯一翻车的是 baseline 的一道**多步推理题**（匀加速 5s + 匀速 10s 求总位移）：它把末速度记成 5 而不是 10，位移算成 75（正确 125）。带工具后，Agent 一步步执行代码，22 题全对。

**结论**：这套题上，工具的价值不是"救回一堆错"，而是恰恰体现在**需要多步计算的难题**上——裸 LLM 的短板在"算"，不在"懂"。

> Reflexion 这次和 tools 完全一样（100%），因为 tools 已经全对、没有可反思的失败。要看出 Reflexion 的价值，需要加更难、能让 tools 也出错的题——这是「后面想做」里的一条。

## 工具设计（能力边界）

- `calculator`：只算一个表达式，ast 白名单挡掉 import / 任意函数调用。几乎安全、快。
- `python`：子进程里跑任意代码，能 import math/sympy/numpy，能超时杀掉。强大但要隔离。

两个工具分开，是因为**信任边界**不一样：agent 得自己判断该用哪个，这本身就是它"能力"的一部分。

## 和 LangChain / LangGraph 的对应

手写的东西换成框架就是：

- `Agent.run` 的循环 ≈ `AgentExecutor` / LangGraph 里的 `graph.add_edge("agent", "tools")` 回环
- `TOOLS` ≈ `Tool` + `StructuredTool`
- 工具说明 ≈ `Tool.description`（喂给模型做工具选择）
- `eval.py` 的消融 ≈ 一个最小版 evaluation harness（LangSmith / Ragas 干的事）
- `reflexion` ≈ Reflexion / self-reflection 的简化实现

## 后面想做

- 加 `web_search` 工具，让 agent 查资料而不是全靠记忆
- 用 LangGraph 重写一版做对照，直接对比手写和框架
- 支持并行跑、统计多次试验的方差，输出置信区间
- 换成更难的推理题（如需要符号推导），进一步拉开 baseline 和 tools 的差距
