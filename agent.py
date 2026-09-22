"""两种求解器 + ReAct 智能体。

- BaselineSolver：裸 LLM，不给工具，直接要答案。用来当消融实验的对照。
- Agent：ReAct 智能体，Thought -> Action -> Observation 循环，能调用工具。

Reflexion 的重试逻辑放在 eval.py 里，因为只有评测时才知道标准答案。
"""
import re

from tools import TOOLS

SYSTEM_PROMPT = """你是一个会使用工具的计算智能体，负责求解科学计算题。

你能用的工具：
- calculator[表达式]：算一个算术表达式，返回数值
- python[代码]：执行一段 Python 代码（可 import math/sympy/numpy），返回 print 出来的内容

你必须严格按下面格式回复，每次只给一步：
Thought: 你的思考
Action: 工具名[参数]

系统会回给你 Observation，然后你继续。得出最终结果时：
Final Answer: 一个数字

规则：
1. 数值计算一律交给工具，不要自己心算
2. 最终答案只写数字，不要带单位、不要解释
"""

FEW_SHOT = """问：把 60 km/h 换算成 m/s
Thought: 60 km/h 换算成 m/s 就是除以 3.6。
Action: calculator[60 / 3.6]
Observation: 16.666666666666668
Thought: 得到结果了。
Final Answer: 16.666666666666668

问：一个球从 20 m 高处自由落下，g=9.8，落地要几秒？
Thought: 自由落体 t = sqrt(2h/g)，用 python 算。
Action: python[import math; print(math.sqrt(2*20/9.8))]
Observation: 2.0203050891044216
Thought: 得到落地时间。
Final Answer: 2.0203050891044216
"""

BASELINE_SYSTEM = """你是计算助手。直接给出数值答案，只输出数字本身，不要解释、不要单位、不要步骤。"""

_ACTION_RE = re.compile(r"Action:\s*(\w+)\[([^\]]*)\]")
_FINAL_RE = re.compile(r"Final Answer:\s*([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)")
_NUM_RE = re.compile(r"[-+]?\d+\.?\d+(?:[eE][-+]?\d+)?")


def parse_action(text):
    m = _ACTION_RE.search(text)
    if m:
        return m.group(1), m.group(2).strip()
    return None, None


def parse_final(text):
    m = _FINAL_RE.search(text)
    if m:
        return float(m.group(1))
    return None


def parse_number(text):
    """从一段文字里抠出第一个数字，给 baseline 用。"""
    m = _NUM_RE.search(text)
    if m:
        return float(m.group(0))
    return None


class BaselineSolver:
    """不给工具，直接让裸 LLM 报答案。"""

    def __init__(self, llm):
        self.llm = llm

    def run(self, question):
        text, usage = self.llm.chat([
            {"role": "system", "content": BASELINE_SYSTEM},
            {"role": "user", "content": question},
        ])
        ans = parse_number(text)
        return {
            "final_answer": ans,
            "steps": 1,
            "usage": usage,
            "trajectory": [{"step": 0, "text": text}],
            "error": None if ans is not None else "parse_error",
        }


class Agent:
    def __init__(self, llm):
        self.llm = llm

    def run(self, question, max_steps=6, feedback=None):
        """feedback：Reflexion 用，把上一次的失败原因带进去。"""
        user = FEW_SHOT + f"问：{question}"
        if feedback:
            user = f"上一次你没能做对这道题。{feedback}\n\n" + user
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user},
        ]
        trajectory = []
        total_usage = None

        for step in range(max_steps):
            text, usage = self.llm.chat(messages)
            if usage is not None:
                total_usage = usage
            trajectory.append({"step": step, "text": text})

            final = parse_final(text)
            if final is not None:
                return {
                    "final_answer": final,
                    "steps": step + 1,
                    "trajectory": trajectory,
                    "usage": total_usage,
                    "error": None,
                }

            tool, arg = parse_action(text)
            if tool is None:
                return {
                    "final_answer": None,
                    "steps": step + 1,
                    "trajectory": trajectory,
                    "usage": total_usage,
                    "error": "parse_error",
                }

            if tool not in TOOLS:
                obs = f"未知工具 {tool}"
            else:
                try:
                    obs = TOOLS[tool]["run"](arg)
                except Exception as e:
                    obs = f"工具出错: {e}"

            trajectory[-1]["observation"] = obs
            messages.append({"role": "assistant", "content": text})
            messages.append({"role": "user", "content": f"Observation: {obs}"})

        return {
            "final_answer": None,
            "steps": max_steps,
            "trajectory": trajectory,
            "usage": total_usage,
            "error": "max_steps",
        }
