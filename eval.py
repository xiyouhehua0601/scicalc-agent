"""评测 harness。

对每个任务跑 agent，算成功率、平均步数、token 消耗，并把失败拆成几类：
- wrong_answer：给了答案但不对
- parse_error：模型输出没法解析成 Action 或 Final Answer
- max_steps：步数用完还没给答案
- tool_error：工具执行出错（且最终没答对）

跑完会打印一个汇总表，并把完整结果存到 results/ 下。
"""
import argparse
import json
import os
import sys
from collections import defaultdict

from agent import Agent
from llm import LLMClient
from tasks import TASKS


def is_correct(final, task):
    if final is None:
        return False
    return abs(final - task["answer"]) <= task["tol"]


def categorize(result, correct):
    if correct:
        return "ok"
    if result["error"] == "parse_error":
        return "parse_error"
    if result["error"] == "max_steps":
        return "max_steps"
    if any("工具出错" in (t.get("observation") or "") for t in result["trajectory"]):
        return "tool_error"
    return "wrong_answer"


def run(trials=1):
    agent = Agent(LLMClient())
    results = []
    for task in TASKS:
        for t in range(trials):
            r = agent.run(task["question"])
            correct = is_correct(r["final_answer"], task)
            results.append({
                "task_id": task["id"],
                "category": task["category"],
                "question": task["question"],
                "expected": task["answer"],
                "got": r["final_answer"],
                "correct": correct,
                "error": categorize(r, correct),
                "steps": r["steps"],
                "tokens": (r["usage"] or {}).get("total_tokens", 0),
                "trajectory": r["trajectory"],
            })
    return results


def summarize(results):
    n = len(results)
    ok = [r for r in results if r["correct"]]
    acc = len(ok) / n if n else 0.0
    by_cat = defaultdict(lambda: [0, 0])
    for r in results:
        by_cat[r["category"]][1] += 1
        by_cat[r["category"]][0] += 1 if r["correct"] else 0
    err = defaultdict(int)
    for r in results:
        if not r["correct"]:
            err[r["error"]] += 1
    avg_steps = sum(r["steps"] for r in ok) / len(ok) if ok else 0.0
    avg_tokens = sum(r["tokens"] for r in results) / n if n else 0.0

    print(f"成功率: {acc*100:.1f}%  ({len(ok)}/{n})")
    print(f"答对题平均步数: {avg_steps:.2f}    平均 token/题: {avg_tokens:.0f}")
    print()
    print("按题型:")
    for cat, (c, tot) in sorted(by_cat.items()):
        print(f"  {cat:<8} {c}/{tot}")
    print()
    print("错误分布:")
    for e, c in sorted(err.items(), key=lambda x: -x[1]):
        print(f"  {e:<14} {c}")
    return acc


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--trials", type=int, default=1, help="每题跑几次")
    args = p.parse_args()

    results = run(args.trials)
    acc = summarize(results)

    os.makedirs("results", exist_ok=True)
    out = {"accuracy": acc, "results": results}
    with open("results/eval.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"\n完整结果已存到 results/eval.json")


if __name__ == "__main__":
    main()
