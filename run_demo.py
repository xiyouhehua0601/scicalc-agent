"""单题演示：跑一道题，把 Thought/Action/Observation 全程打印出来。"""
import sys

from agent import Agent
from llm import LLMClient


def main():
    question = " ".join(sys.argv[1:]) or "悬臂梁长 2 m，EI=50000 N·m^2，自由端受 1000 N 集中力，挠度是多少？（δ=P*L^3/(3EI)）"
    agent = Agent(LLMClient())
    r = agent.run(question)
    print(f"问：{question}\n")
    for t in r["trajectory"]:
        print(t["text"])
        if "observation" in t:
            print(f"Observation: {t['observation']}")
        print("-" * 50)
    print(f"\n最终答案: {r['final_answer']}  (步数 {r['steps']}, error={r['error']})")


if __name__ == "__main__":
    main()
