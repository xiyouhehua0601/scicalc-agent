"""消融实验 harness。

对比三种求解方式在同一评测集上的表现：
- baseline：裸 LLM，不给工具
- tools：ReAct 智能体（calculator + python 两个工具）
- reflexion：tools 基础上，答错了把原因喂回去让它反思重试

跑完打印对比表，并把每个 solver 的完整结果分别存到 results/ 下。
"""
import argparse
import json
import os
from collections import defaultdict

from agent import Agent, BaselineSolver
from llm import LLMClient
from tasks import TASKS

SOLVER_NAMES = ["baseline", "tools", "reflexion"]
REFLEXION_RETRIES = 2


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


def run_solver(llm, name, task):
    """跑一个 solver 解一题，返回带判定信息的结果 dict。"""
    if name == "baseline":
        r = BaselineSolver(llm).run(task["question"])
    else:
        agent = Agent(llm)
        r = agent.run(task["question"])
        if name == "reflexion":
            for _ in range(REFLEXION_RETRIES):
                if is_correct(r["final_answer"], task):
                    break
                prev = r["final_answer"] if r["final_answer"] is not None else "（没给出答案）"
                r = agent.run(task["question"], feedback=f"你的答案是 {prev}，不正确，反思哪里错了再试。")

    correct = is_correct(r["final_answer"], task)
    r["correct"] = correct
    r["error"] = categorize(r, correct)
    return r


def run(trials=1):
    llm = LLMClient()
    results = {name: [] for name in SOLVER_NAMES}
    for task in TASKS:
        for t in range(trials):
            for name in SOLVER_NAMES:
                r = run_solver(llm, name, task)
                r.update({"task_id": task["id"], "category": task["category"],
                          "question": task["question"], "expected": task["answer"]})
                results[name].append(r)
    return results


def _summary_for(name, rs):
    n = len(rs)
    ok = [r for r in rs if r["correct"]]
    acc = len(ok) / n if n else 0.0
    avg_steps = sum(r["steps"] for r in ok) / len(ok) if ok else 0.0
    avg_tokens = sum((r.get("usage") or {}).get("total_tokens", 0) for r in rs) / n if n else 0.0
    err = defaultdict(int)
    for r in rs:
        if not r["correct"]:
            err[r["error"]] += 1
    return {"name": name, "acc": acc, "n_ok": len(ok), "n": n,
            "avg_steps": avg_steps, "avg_tokens": avg_tokens, "err": dict(err)}


def summarize(results):
    rows = [_summary_for(name, results[name]) for name in SOLVER_NAMES]
    print("=" * 70)
    print(f"{'求解方式':<12}{'成功率':<12}{'平均步数':<10}{'平均token/题':<14}{'错误分布'}")
    print("-" * 70)
    for r in rows:
        err = " ".join(f"{k}:{v}" for k, v in sorted(r["err"].items(), key=lambda x: -x[1])) or "无"
        print(f"{r['name']:<12}{r['acc']*100:>6.1f}%   {r['avg_steps']:>6.2f}   {r['avg_tokens']:>10.0f}   {err}")
    print("=" * 70)
    # 按题型看 tools 的表现
    by_cat = defaultdict(lambda: [0, 0])
    for r in results["tools"]:
        by_cat[r["category"]][1] += 1
        by_cat[r["category"]][0] += 1 if r["correct"] else 0
    print("\ntools 模式按题型：")
    for cat, (c, tot) in sorted(by_cat.items()):
        print(f"  {cat:<8} {c}/{tot}")
    return {r["name"]: r for r in rows}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--trials", type=int, default=1, help="每题每个 solver 跑几次")
    args = p.parse_args()

    results = run(args.trials)
    summary = summarize(results)

    os.makedirs("results", exist_ok=True)
    for name in SOLVER_NAMES:
        with open(f"results/{name}.json", "w", encoding="utf-8") as f:
            json.dump(results[name], f, ensure_ascii=False, indent=2)
    with open("results/summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print("\n完整结果：results/{baseline,tools,reflexion}.json，汇总：results/summary.json")


if __name__ == "__main__":
    main()
