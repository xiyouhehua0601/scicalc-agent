"""单题演示：同一道题分别用裸 LLM 和 ReAct 智能体解，看差别。"""
import sys

from agent import Agent, BaselineSolver
from llm import LLMClient

DEFAULT = "汽车先以 90 km/h 行驶 45 分钟，再以 60 km/h 行驶 30 分钟，全程平均速度是多少 km/h？"


def main():
    question = " ".join(sys.argv[1:]) or DEFAULT
    llm = LLMClient()

    print(f"问：{question}\n")

    print("===== 裸 LLM（不给工具）=====")
    b = BaselineSolver(llm).run(question)
    print(b["trajectory"][0]["text"])
    print(f"答案: {b['final_answer']}\n")

    print("===== ReAct 智能体（带工具）=====")
    r = Agent(llm).run(question)
    for t in r["trajectory"]:
        print(t["text"])
        if "observation" in t:
            print(f"Observation: {t['observation']}")
    print(f"答案: {r['final_answer']}  (步数 {r['steps']}, error={r['error']})")


if __name__ == "__main__":
    main()
