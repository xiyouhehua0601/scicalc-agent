"""评测集：10 道科学计算题，每题带标准答案和容差。

都是答案唯一的数值题，覆盖单位换算 / 运动学 / 材料力学 / 功与能 / 几何 / 算术。
容差用的绝对误差，材料力学那题答案比较小所以给得紧一点。
"""
TASKS = [
    {"id": 1, "category": "单位换算", "answer": 16.6667, "tol": 0.01,
     "question": "把 60 km/h 换算成 m/s"},
    {"id": 2, "category": "运动学", "answer": 2.0203, "tol": 0.01,
     "question": "一个球从 20 m 高处自由落下，g=9.8，落地需要多少秒？"},
    {"id": 3, "category": "运动学", "answer": 40.8163, "tol": 0.01,
     "question": "小球以 20 m/s、45 度角抛出，g=9.8，水平射程是多少米？（R=v^2*sin(2θ)/g）"},
    {"id": 4, "category": "材料力学", "answer": 0.05333, "tol": 0.0005,
     "question": "悬臂梁长 L=2 m，抗弯刚度 EI=50000 N·m^2，自由端受集中力 P=1000 N，自由端挠度是多少米？（δ=P*L^3/(3*E*I)）"},
    {"id": 5, "category": "静力学", "answer": 10.0, "tol": 1e-6,
     "question": "弹簧刚度 k=200 N/m，拉伸量 x=0.05 m，弹力 F=k*x 是多少牛顿？"},
    {"id": 6, "category": "功与能", "answer": 9.0, "tol": 1e-6,
     "question": "质量 2 kg 的物体以 3 m/s 运动，动能 0.5*m*v^2 是多少焦耳？"},
    {"id": 7, "category": "功与能", "answer": 200.0, "tol": 1e-6,
     "question": "恒力 50 N 沿力的方向推动 4 m，做的功是多少焦耳？"},
    {"id": 8, "category": "几何", "answer": 78.5398, "tol": 0.01,
     "question": "半径 5 cm 的圆，面积 π*r^2 是多少平方厘米？π 取 3.14159"},
    {"id": 9, "category": "算术", "answer": 105.0, "tol": 1e-6,
     "question": "计算 12.5 乘以 8.4"},
    {"id": 10, "category": "材料力学", "answer": 7.85, "tol": 1e-6,
     "question": "边长 0.1 m 的钢立方体，密度 7850 kg/m^3，质量是多少千克？"},
]
