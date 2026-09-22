"""冒烟测试：不调真实 API，验证工具、解析、baseline、ReAct 循环、评测统计。

跑法：python -m pytest tests/ 或者直接 python tests/test_smoke.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agent import Agent, BaselineSolver, parse_action, parse_final, parse_number
from tools import calculator, python_executor


class ScriptedLLM:
    """按顺序吐预设回复的假 LLM。"""
    def __init__(self, replies):
        self.replies = list(replies)
        self.calls = 0

    def chat(self, messages, **kwargs):
        idx = min(self.calls, len(self.replies) - 1)
        self.calls += 1
        return self.replies[idx], None


class GoldenLLM:
    """永远直接给标准答案。"""
    def __init__(self, answers):
        self.answers = answers
        self.i = 0

    def chat(self, messages, **kwargs):
        a = self.answers[self.i % len(self.answers)]
        self.i += 1
        return f"Final Answer: {a}", None


def test_calculator_basic():
    assert float(calculator("2 * 9.8")) == 19.6
    assert float(calculator("math.sqrt(4)")) == 2.0


def test_calculator_blocks_injection():
    try:
        calculator("__import__('os').system('echo hi')")
    except (ValueError, NameError):
        return
    assert False, "注入应该被挡下来"


def test_python_executor():
    assert python_executor("print(1 + 1)") == "2"
    assert python_executor("print(1/0)").startswith("出错")


def test_parse():
    assert parse_final("Final Answer: 16.666") == 16.666
    assert parse_action("Action: calculator[2*3]") == ("calculator", "2*3")
    assert parse_number("答案是 16.67 m/s") == 16.67


def test_baseline():
    llm = ScriptedLLM(["答案是 16.67"])
    r = BaselineSolver(llm).run("60 km/h 是多少 m/s")
    assert r["final_answer"] == 16.67
    assert r["error"] is None


def test_react_loop():
    llm = ScriptedLLM([
        "Thought: 算一下\nAction: calculator[3+4]",
        "Thought: 得到结果\nFinal Answer: 7",
    ])
    r = Agent(llm).run("3+4 等于几")
    assert r["final_answer"] == 7.0
    assert r["steps"] == 2
    assert r["error"] is None


def test_feedback_goes_into_prompt():
    # feedback 应该出现在首条 user 消息里（Reflexion 依赖这个）
    seen = []

    class Spy:
        def chat(self, messages, **kwargs):
            seen.append(messages[1]["content"])
            return "Final Answer: 7", None

    Agent(Spy()).run("1+1", feedback="上次错了")
    assert "上次错了" in seen[0]


def test_eval_accuracy():
    from tasks import TASKS
    llm = GoldenLLM([t["answer"] for t in TASKS])
    agent = Agent(llm)
    ok = 0
    for t in TASKS:
        r = agent.run(t["question"])
        if r["final_answer"] is not None and abs(r["final_answer"] - t["answer"]) <= t["tol"]:
            ok += 1
    assert ok == len(TASKS)


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print(f"PASS {t.__name__}")
    print("全部通过")
