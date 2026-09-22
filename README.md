# scicalc-agent

一个用 **ReAct 智能体**求解科学计算题、并**系统评测它能力边界**的小项目。

LLM 单独做数值计算经常"自信地算错"——它其实是语言模型，不是计算器。这个项目给它装上工具（计算器 + Python 代码执行），让它走 `Thought → Action → Observation` 的循环去算题，然后回答一个更重要的问题：**有了工具之后，它还在哪些地方出错？**

## 有什么

- `agent.py` —— 手写的 ReAct 循环，不用框架，搞清楚每一步在干嘛
- `tools.py` —— 两个工具：`calculator`（ast 白名单防注入）、`python`（子进程 + 超时）
- `tasks.py` —— 10 道力学/物理计算题，带标准答案和容差
- `eval.py` —— 评测 harness：成功率、平均步数、token 消耗、按题型和错误类型归因
- `run_demo.py` —— 单题演示，打印完整推理轨迹

## 为什么做这个

1. 它能直接回答「Agent 的能力边界在哪」——不是跑通一个 Hello World，而是用数据说清楚它在哪一类题上容易挂、挂在哪一步（规划错 / 工具用错 / 算错 / 超时）。
2. 力学/科学计算是我的本行，选题和 CS 背景的千篇一律「聊天机器人 RAG」区分开。
3. 手写 ReAct 循环而不是调 LangChain 的现成接口，是为了真正理解 Agent 的编排逻辑。

## 架构

```
           ┌──────────────────────────────┐
  问题 ──▶ │  LLM（DeepSeek / Qwen / …）   │
           │  输出 Thought + Action        │
           └──────────────┬───────────────┘
                          │ Action
                          ▼
           ┌──────────────────────────────┐
           │  tools.py                     │
           │  calculator / python          │
           └──────────────┬───────────────┘
                          │ Observation
                          ▼
              （喂回 LLM，循环，直到 Final Answer）
```

## 快速开始

```bash
# 1. 装依赖（就一个 requests）
pip install -r requirements.txt

# 2. 设 API key（默认 DeepSeek，最便宜；改 base_url 可换 Qwen/Kimi/OpenAI）
export LLM_API_KEY=sk-你的key
export LLM_BASE_URL=https://api.deepseek.com/v1
export LLM_MODEL=deepseek-chat

# 3. 跑一道题看完整轨迹
python run_demo.py "悬臂梁长 2 m，EI=50000 N·m^2，自由端受 1000 N 集中力，挠度是多少？"

# 4. 跑整套评测（每题可 --trials 3 跑多次取平均）
python eval.py --trials 1
```

不设 key 也能先跑冒烟测试（用假 LLM 验证核心逻辑）：

```bash
python tests/test_smoke.py
```

## 工具设计（能力边界）

- `calculator`：只算一个表达式，白名单挡住 import / 任意函数调用。适合一步到位的计算。
- `python`：子进程里跑任意代码，能 import math/sympy/numpy，也能超时杀掉。适合多步推导。

两个工具分开，是因为它们的**信任边界**不一样：calculator 几乎安全所以快，python 强大但要隔离。agent 得自己判断该用哪个，这本身就是它"能力"的一部分。

## 评测方法

- 答对标准：`|answer - expected| <= tol`（绝对误差，材料力学那题答案小所以容差更紧）
- 失败分四类：`wrong_answer`（答了但错）、`parse_error`（输出没法解析）、`max_steps`（步数用完）、`tool_error`（工具报错且没答对）
- 指标：成功率、答对题的平均步数、平均 token/题，另外按题型单独看

## 结果（DeepSeek-chat 实测）

`python eval.py --trials 1` 的真实输出：

| 指标 | 数值 |
|------|------|
| 成功率 | 100%（10/10） |
| 答对题平均步数 | 1.2 |
| 平均 token / 题 | 409 |

这 10 道题全对，说明这几道计算题对带工具的 Agent 来说不算难——`calculator` 一步就能兜住大部分。这其实印证了「瓶颈不在工具本身、而在模型会不会用工具」：DeepSeek-chat 的工具调用很稳，所以没出错。

想让错误分析那块真正亮出来，加几道更难的题（多步推导、单位要自己换算、或故意带陷阱）就能看到 `wrong_answer` / `parse_error` 是怎么被归因的。这也是「后面想做」里的一条。

## 和 LangChain / LangGraph 的对应

这里手写的东西，换成框架就是：

- `Agent.run` 的循环 ≈ `AgentExecutor` / LangGraph 里的一个 `graph.add_edge("agent", "tools")` 回环
- `TOOLS` ≈ `Tool` + `StructuredTool`
- 提示词里的工具说明 ≈ `Tool` 的 description（喂给模型做工具选择）
- `eval.py` ≈ 一个最小版的 evaluation harness（LangSmith / Ragas 干的事）

## 后面想做

- 加一个 `web_search` 工具，让 agent 查资料而不是全靠记忆
- 把 ReAct 升级成 Reflexion（失败后自我反思再试一次），看成功率能涨多少
- 用 LangGraph 重写一版做对照，直接对比手写和框架
- 支持并行跑、统计多次试验的方差
