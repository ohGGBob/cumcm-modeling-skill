# cumcm-modeling 数模 Skill

一个可复用的 AI 数模方法论：从 2026 高教社杯全国大学生数学建模竞赛（CUMCM）A 题《药材的烘干问题》的完整工作区（21+ 条独立求解线、5 轮审理、6 条登记在案的失败模式）复盘提炼而成。

它回答一个问题：**AI 做数模题时，会在哪里翻车、为什么会翻车、下次怎么提前抓住。**

## 仓库结构

```
cumcm-modeling-skill/
├── SKILL.md                          # 数模 skill 主体（可被 DSH 直接加载）
├── QUICKSTART.md                     # 接题 5 分钟速查卡（单屏最小闭环）
├── README.md                         # 本文件
├── scripts/
│   └── analyze.py                    # 数据分析+可视化工具（matrix/field/check 三子命令）
├── templates/                        # 四份填空模板（读题/口径/判据/对账）
│   ├── data_inventory_template.md     #   数据清单
│   ├── caliber_brief_template.md      #   口径简报
│   ├── criteria_generator_template.md #   判据生成器
│   └── provenance_ledger_template.md  #   数字溯源表
├── examples/
│   ├── sample_results.csv            #   多管线结果矩阵示例（含一条离群"读反D"路）
│   └── expected.json                 #   期望量级自检范围
└── docs/
    ├── failure-ledger.md              # 量化失败台账（症状→根因→便宜抓法→后果，30 条）
    ├── failure-frequency.md           # 失败频率×严重度热表（Top10 + 矩阵实证 + 谱系图）
    ├── workspace-inventory.md         # 工作区全部文件盘点（顶层目录 + 关键产物）
    └── lessons-learned.md             # AI 做得不好/困难的复盘（含证据出处）
```

## 如何使用

### 作为 Skill 加载
`SKILL.md` 遵循 skill 的 YAML frontmatter 约定（`name` + `description`）。把它所在目录放入 agent 的 skill 目录即可被识别；当任务涉及数模读题、建模、求解、审计或复盘时，模型会自动或手动加载。

### 直接阅读
- 想快速抓要点 → 读 `QUICKSTART.md`（接题 5 分钟速查卡）或 `SKILL.md` §0–§4。
- 想逐条对照"这样做会失败" → 读 `docs/failure-ledger.md`（30 条量化台账）。
- 想看"哪些坑又常见又致命" → 读 `docs/failure-frequency.md`（频率×严重度热表）。
- 想看完整证据链（哪里难、AI 哪里做砸了）→ 读 `docs/lessons-learned.md`。
- 想看清这个工作区里到底有什么 → 读 `docs/workspace-inventory.md`。
- 想跑数据分析/可视化 → 读 `SKILL.md` §12，用 `scripts/analyze.py`（示例输入在 `examples/`）。
- 想直接套模板动手 → `templates/`（数据清单 / 口径简报 / 判据生成器 / 来源对账，四份填空表）。

### 数据分析 + 可视化工具（`scripts/analyze.py`）
- `python analyze.py matrix results.csv --out-prefix out/comp`　多管线对比：共识区间 + IQR 离群标记 + ECharts 平行坐标 HTML。
- `python analyze.py field result1.xlsx --mode both --t 100,600,1800 --r 0,1.0,2.0 --out T.png`　结果场时间序列 + 剖面图。
- `python analyze.py check results.csv --expected expected.json`　期望量级自检（越界即标）。

`matrix`/`check` 仅用标准库；`field` 需 `pandas openpyxl matplotlib`。

## 方法论速览

- **读题**：先读数据再读公式；公式分数/指数/单位必须视觉核验（`exp(−0.45/C)` 被文本提取误读成 `exp(−0.45·C)` 曾把烘干时长从 57 h 算成 16.4 h）。
- **建模**：题面没给的不许编造；每个数字带来源标签**和可靠度分级**；口径成套、时刻对齐。
- **求解**：先过便宜自检（uniform-field test / 制造解 / 环境≡初值场不动）再跑全程；边界膜阻串联、单位 K。
- **验证**：**三层验证**（解读正确性 / 求解器正确性 / 物理自洽性）缺一不可——收敛、守恒、解析解都是"求解器级"，抓不住公式读反。
- **交叉验证**：多路独立实现 + 解析判据 + 外部约束；离群值逐个定根因，分歧口径显式声明；"假通过"用 G-4 边界—场自洽一票否决。
- **仲裁**：两条路径打架时，先查证据五维（分子/分母/区间/口径/可比性），再用独立求解器逐点复现判决；比值型证据 + 同源恒等式零信息。
- **验收**：新求解器跑下一问前，先用已验交付值当金样本复现（偏差超 0.1K/0.01 即停）；单元测试必须"打到位"（绕过关键项 = 假通过）。
- **合规与收口**：匿名全文扫描（本地路径含用户名）、AI 声明官方逐字句式、工具型号不编造、附录源程序逐个运行核验——"取消资格级"红线进硬清单。
- **尺度/对账/判据复核**：动笔先做量纲尺度标定（α/D、Bi、渗透深度、刚性来源）生成可证伪判据；数字逐条五档对账（一个输入无来源则整链无来源）；门禁判据本身也要过"环境≡初值"自检。
- **代码审计**：最小变异探针 + 数值指纹 + 反事实/三极限/比较原理钉死符号/口径/死参数 bug；对账落地用 P0–P3 严重度 + "谁改谁复核分离" + 勿改清单，警惕"整数倍数"这类数字修辞。
- **跨来源与盲测**：先画谱系图别把同源簇当独立佐证；交付文件逐格 diff；分歧先定性（假设/实质/口径）；公式歧义用"无提示双盲子代理"复现错误阵营来最终裁定。
- **交付**：论文声称 ↔ 代码 ↔ 交付物三者一致；数字可回溯、可复现；结论可追溯作废；AI 声明如实填写。

## 免责

本仓库是**方法论复盘**，不含官方参考答案。题解数值仅为说明失败模式的示例，据此参赛请自行独立完成并遵守竞赛规则（含 AI 使用声明）。