"""工具定义与执行。

这里只有两个工具：
- calculator：算一个算术表达式，用 ast 白名单挡住注入
- python：在子进程里跑一段 Python，能超时杀掉

每个工具就是一个 {run, desc, example} 三元组，agent 靠 desc 决定该用哪个。
"""
import ast
import math
import subprocess
import sys

# 允许的节点类型，其它一律拒绝，防止 eval 被拿来干坏事
_ALLOWED_NODES = (
    ast.Expression, ast.BinOp, ast.UnaryOp, ast.Constant,
    ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow, ast.Mod,
    ast.USub, ast.UAdd, ast.Call, ast.Attribute, ast.Name, ast.Load,
)


def calculator(expression: str) -> str:
    tree = ast.parse(expression, mode="eval")
    for node in ast.walk(tree):
        if not isinstance(node, _ALLOWED_NODES):
            raise ValueError(f"表达式里有不允许的成分: {type(node).__name__}")
        if isinstance(node, ast.Name) and node.id != "math":
            raise ValueError(f"未知变量 {node.id!r}")
        if isinstance(node, ast.Call):
            # 只允许 math.xxx 这种函数调用
            if not (
                isinstance(node.func, ast.Attribute)
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id == "math"
            ):
                raise ValueError("只允许调用 math 模块的函数")
    ns = {"__builtins__": {}, "math": math}
    value = eval(compile(tree, "<calc>", "eval"), ns)
    return str(value)


def python_executor(code: str, timeout: float = 10.0) -> str:
    try:
        r = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True, text=True, timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return "超时（超过 10 秒）"
    if r.returncode != 0:
        return f"出错: {r.stderr.strip()[-400:]}"
    return r.stdout.strip()


TOOLS = {
    "calculator": {
        "run": calculator,
        "desc": "算一个算术表达式，返回数值。适合一步到位的纯计算。",
        "example": "calculator[2 * 9.8]",
    },
    "python": {
        "run": python_executor,
        "desc": "执行一段 Python 代码，返回 print 的内容。适合需要 import math/sympy/numpy 的多步推导。",
        "example": "python[import math; print(math.sqrt(2*20/9.8))]",
    },
}
