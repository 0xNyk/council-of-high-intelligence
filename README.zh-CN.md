# 高智商议会（Council of High Intelligence）

<p align="center">
  <a href="README.md">English</a> | <strong>简体中文</strong>
</p>

<p align="center">
  <img src="assets/header.jpeg" alt="Council of High Intelligence" width="800">
</p>

<p align="center">
  18 位 AI 人格跨多个大语言模型提供商，共同审议你最棘手的决策。只需一条命令。
</p>

<p align="center">
  <a href="https://github.com/0xNyk/council-of-high-intelligence/releases"><img src="https://img.shields.io/github/v/release/0xNyk/council-of-high-intelligence" alt="Release"></a>
  <a href="https://github.com/0xNyk/council-of-high-intelligence/stargazers"><img src="https://img.shields.io/github/stars/0xNyk/council-of-high-intelligence" alt="Stars"></a>
  <a href="https://creativecommons.org/publicdomain/zero/1.0/"><img src="https://img.shields.io/badge/license-CC0-blue" alt="License"></a>
  <img src="https://img.shields.io/badge/Claude_Code-skill-blueviolet" alt="Claude Code Skill">
  <img src="https://img.shields.io/badge/Codex-skill-black" alt="Codex Skill">
  <img src="https://img.shields.io/badge/members-18-orange" alt="18 Members">
</p>

<details>
<summary><strong>目录</strong></summary>

- [快速开始](#快速开始)
- [为什么有效](#为什么有效)
- [18 位议会成员](#18-位议会成员)
- [三种审议模式](#三种审议模式)
- [多提供商自动路由](#多提供商自动路由)
- [审议协议](#审议协议)
- [安装](#安装)
- [环境要求](#环境要求)
- [参与贡献](#参与贡献)
- [支持项目](#支持项目)

</details>

## 快速开始

### Claude Code

```bash
git clone https://github.com/0xNyk/council-of-high-intelligence.git
cd council-of-high-intelligence
./install.sh
```

然后在 Claude Code 中运行：

```
/council Should we open-source our agent framework?
/council --quick Should we add caching here?
/council --duo Should we use microservices or monolith?
```

你也可以直接使用中文提问：

```
/council 我们应该把智能体框架开源吗？
```

### Codex

```bash
git clone https://github.com/0xNyk/council-of-high-intelligence.git
cd council-of-high-intelligence
./install.sh --codex
```

然后在 Codex 中运行：

```
/council Should we open-source our agent framework?
/council --quick Should we add caching here?
/council --duo Should we use microservices or monolith?
```

## 为什么有效

单个大语言模型只会给你一条披着自信外衣的推理路径。向它提出一个困难问题，你可能得到一个流畅、结构清晰，却完全错误的答案。议会带来的则是结构化分歧：

- **获得真正不同的视角**——极性配对会制造真实张力（苏格拉底拆解假设；费曼从第一性原理重新构建）。多提供商路由把成员分配到 Claude、OpenAI、Gemini 和 Ollama，让你得到真正不同的推理，而不是同一个模型换上不同人设
- **尽早发现错误的问题**——“问题重述关卡”要求每位成员在分析前重新表述问题。如果 3 位成员给出了不同的重述，那么问题本身可能才是问题
- **知道议会无法回答什么**——裁决首先列出“未解决问题”和“建议的下一步”，而不是听起来很自信的共识。议会不知道什么，往往比它赞同什么更重要
- **防止群体思维**——异议配额、新颖性关卡和反事实提示会强制产生真实分歧。如果超过 70% 的成员过早达成一致，将有两位成员被要求为相反观点提出最有力的论证

> **为什么不直接问 Claude？** 单个提示只能得到一个模型自信的最佳猜测。议会会从不同思想传统中生成 3–18 份独立分析，迫使它们相互质疑，并综合出一个不会掩盖分歧的裁决。这就像请教一位顾问与召集整个董事会之间的区别。

## 18 位议会成员

| Agent | 人物 | 领域 | 默认模型 | 思维极性 |
|-------|------|------|----------|----------|
| `council-aristotle` | 亚里士多德 | 分类与结构 | opus | 对一切进行分类 |
| `council-socrates` | 苏格拉底 | 拆解假设 | opus | 质疑一切 |
| `council-sun-tzu` | 孙子 | 对抗性战略 | sonnet | 研判局势与竞争 |
| `council-ada` | 阿达·洛芙莱斯 | 形式系统与抽象 | sonnet | 判断什么能够或不能被机械化 |
| `council-aurelius` | 马可·奥勒留 | 韧性与道德清醒 | opus | 区分掌控与接受 |
| `council-machiavelli` | 马基雅维利 | 权力动态与现实政治 | sonnet | 分析参与者实际会如何行动 |
| `council-lao-tzu` | 老子 | 无为与涌现 | opus | 判断何时少即是多 |
| `council-feynman` | 费曼 | 第一性原理调试 | sonnet | 拒绝未经解释的复杂性 |
| `council-torvalds` | 林纳斯·托瓦兹 | 务实工程 | sonnet | 要么交付，要么闭嘴 |
| `council-musashi` | 宫本武藏 | 战略时机 | sonnet | 寻找决定性一击 |
| `council-watts` | 艾伦·瓦茨 | 视角与问题重构 | opus | 消解虚假问题 |
| `council-karpathy` | 安德烈·卡帕西 | 神经网络直觉 | sonnet | 分析模型实际如何学习与失败 |
| `council-sutskever` | 伊利亚·苏茨克维 | 规模化前沿与 AI 安全 | opus | 判断能力何时转化为风险 |
| `council-kahneman` | 丹尼尔·卡尼曼 | 认知偏差与决策科学 | opus | 你自己的思考是第一个误差源 |
| `council-meadows` | 多内拉·梅多斯 | 系统思维与反馈回路 | sonnet | 重新设计系统，而非只处理症状 |
| `council-munger` | 查理·芒格 | 多元思维模型与经济学 | sonnet | 反过来想——什么必然导致失败？ |
| `council-taleb` | 纳西姆·塔勒布 | 反脆弱与尾部风险 | opus | 为极端情况设计，而不是平均情况 |
| `council-rams` | 迪特·拉姆斯 | 以用户为中心的设计 | sonnet | 少，却更好——由用户决定 |

<details>
<summary><strong>极性配对</strong>——成员会被选为彼此刻意设置的制衡力量</summary>

- **苏格拉底 vs 费曼**——自上而下地拆解 vs 自下而上地重建
- **亚里士多德 vs 老子**——对一切分类 vs 结构本身就是问题
- **孙子 vs 奥勒留**——赢得外部博弈 vs 治理内在世界
- **阿达 vs 马基雅维利**——形式纯粹性 vs 混乱的人类激励
- **托瓦兹 vs 瓦茨**——交付具体方案 vs 质疑问题是否存在
- **武藏 vs 托瓦兹**——等待完美时机 vs 立即交付
- **卡帕西 vs 苏茨克维**——构建、观察、迭代 vs 暂停、研究、先确保安全
- **卡帕西 vs 阿达**——经验主义的机器学习直觉 vs 形式系统理论
- **卡尼曼 vs 费曼**——你的认知是第一个误差源 vs 相信第一性原理推理
- **梅多斯 vs 托瓦兹**——重新设计反馈回路 vs 修复症状并交付
- **芒格 vs 亚里士多德**——多元模型格栅 vs 单一分类体系
- **塔勒布 vs 卡帕西**——隐藏的灾难性尾部风险 vs 平滑的经验规模曲线
- **拉姆斯 vs 阿达**——用户需要什么 vs 计算能够做什么

</details>

## 三种审议模式

### 完整模式（默认）

三轮结构化审议：独立分析 → 交叉质询 → 最终立场。

```
/council Should we open-source our agent framework?
/council --triad strategy What's our competitive moat?
/council --full What is the right pricing model?
```

### 快速模式（`--quick`）

面向简单决策的两轮快速分析，不进行交叉质询。

```
/council --quick Should we add caching here?
/council --quick --triad shipping Should we release today?
```

### 双人模式（`--duo`）

使用极性配对进行两人辩证讨论，非常适合探索观点之间的张力。

```
/council --duo Should we use microservices or monolith?
/council --duo --members torvalds,ada Is this abstraction worth it?
```

<details>
<summary><strong>预定义 Triad</strong>——20 个针对特定领域的三人组合</summary>

| 领域 | Triad | 组合逻辑 |
|------|-------|----------|
| `architecture` | Aristotle + Ada + Feynman | 分类 + 形式化 + 简洁性检验 |
| `strategy` | Sun Tzu + Machiavelli + Aurelius | 局势 + 激励 + 道德根基 |
| `ethics` | Aurelius + Socrates + Lao Tzu | 责任 + 质疑 + 自然秩序 |
| `debugging` | Feynman + Socrates + Ada | 自下而上 + 假设检验 + 形式验证 |
| `innovation` | Ada + Lao Tzu + Aristotle | 抽象 + 涌现 + 分类 |
| `conflict` | Socrates + Machiavelli + Aurelius | 揭示 + 预测 + 奠基 |
| `complexity` | Lao Tzu + Aristotle + Ada | 涌现 + 范畴 + 形式化 |
| `risk` | Sun Tzu + Aurelius + Feynman | 威胁 + 韧性 + 经验验证 |
| `shipping` | Torvalds + Musashi + Feynman | 务实 + 时机 + 第一性原理 |
| `product` | Torvalds + Machiavelli + Watts | 交付 + 激励 + 重构问题 |
| `founder` | Musashi + Sun Tzu + Torvalds | 时机 + 局势 + 工程现实 |
| `ai` | Karpathy + Sutskever + Ada | 经验机器学习 + 规模化前沿 + 形式边界 |
| `ai-product` | Karpathy + Torvalds + Machiavelli | 机器学习能力 + 务实交付 + 激励 |
| `ai-safety` | Sutskever + Aurelius + Socrates | 安全前沿 + 道德清醒 + 拆解假设 |
| `decision` | Kahneman + Munger + Aurelius | 偏差识别 + 逆向思考 + 道德清醒 |
| `systems` | Meadows + Lao Tzu + Aristotle | 反馈回路 + 涌现 + 分类 |
| `uncertainty` | Taleb + Sun Tzu + Sutskever | 尾部风险 + 局势 + 规模化前沿 |
| `design` | Rams + Torvalds + Watts | 用户清晰度 + 可维护性 + 重构问题 |
| `economics` | Munger + Machiavelli + Sun Tzu | 思维模型 + 激励 + 竞争 |
| `bias` | Kahneman + Socrates + Watts | 认知偏差 + 拆解假设 + 审视框架 |

</details>

<details>
<summary><strong>议会配置（Profiles）</strong>——针对不同需求预先构建的成员面板</summary>

### `classic`（默认）

包含全部 18 位成员以及上述领域 Triad，最适合广泛审议。

### `exploration-orthogonal`

面向探索和减少“未知的未知”的 12 人面板：

- Socrates、Feynman、Sun Tzu、Machiavelli、Ada、Lao Tzu、Aurelius、Torvalds、Karpathy、Sutskever、Kahneman、Meadows
- 配置专属 Triad：`unknowns`、`market-entry`、`system-design`、`reframing`、`ai-frontier`、`blind-spots`

### `execution-lean`

面向快速从决策走向行动的 5 人面板：

- Torvalds、Feynman、Sun Tzu、Aurelius、Ada
- 配置专属 Triad：`ship-now`、`launch-strategy`、`stability`

</details>

## 多提供商自动路由

议会会自动检测已安装的大语言模型提供商，并把成员分配给不同提供商，以获得真正的模型多样性——无需配置。

```
/council --triad decision Should we accept this acquisition offer?
```

**支持的提供商**（自动检测）：

| 提供商 | CLI | 执行方式 |
|--------|-----|----------|
| Anthropic（Claude） | native | subagent（始终可用） |
| OpenAI | `codex` | `codex exec` |
| Google | `gemini` | `gemini -p` |
| Ollama（本地） | `ollama` | `ollama run` |
| NVIDIA NIM | `NVIDIA_API_KEY` 环境变量 | `openai_compatible_api` |
| Cursor | `cursor-agent` | `cursor-agent -p` |

NVIDIA NIM（[build.nvidia.com](https://build.nvidia.com)）通过兼容 OpenAI 的端点提供 130 多个开放权重模型（DeepSeek、Kimi、MiniMax、GLM、Qwen、Nemotron）。免费层包含 1,000 个积分、40 RPM。检测时只需执行 `export NVIDIA_API_KEY=nvapi-...`，不需要安装 CLI。席位分配示例见 `configs/provider-model-slots.nim.example.yaml`。

Cursor CLI（[cursor.com/cli](https://cursor.com/cli)）是一个模型**聚合器**——一个二进制文件（`cursor-agent`）即可调用 GPT-5.x、Claude、Gemini 和 Grok 系列模型，认证方式为 `CURSOR_API_KEY`（或 `cursor-agent login`）。成员通过无界面的只读模式执行：`cursor-agent -p --mode ask --model <id>`。使用 `curl https://cursor.com/install -fsS | bash` 安装。由于 Cursor 也能提供 `claude-*` 模型，当某个席位需要增加多样性而不是复制 Anthropic 偏差时，应选择**跨模型家族**的 Cursor 模型（例如 `gpt-5.4-high`、`gemini-2.5-pro`、`grok-4`）。运行 `cursor-agent --list-models` 查看当前可用 ID。席位分配示例见 `configs/provider-model-slots.cursor.example.yaml`。

**路由方式：**

1. 极性配对会被分配到不同提供商（硬性约束）
2. 成员尽可能均匀地分散到可用提供商
3. 使用 frontmatter 中每位成员的 `provider_affinity` 处理平局
4. 任意提供商失败时，自动回退到 Claude

**参数：**

- `--no-auto-route`——关闭自动路由，使用仅 Claude 的默认配置
- `--dry-route`——只打印路由表，不实际运行议会
- `--models [path]`——通过 YAML 配置手动覆盖（参见 `configs/provider-model-slots.example.yaml`）

## 审议协议

完整模式执行 7 个步骤：提供商路由 → 问题重述关卡 → 独立分析 → 交叉质询 → 约束扫描 → 最终立场 → 综合裁决。裁决首先说明议会不知道什么。

<details>
<summary><strong>完整协议详情</strong></summary>

### 完整模式（7 个步骤）

1. **提供商检测与路由**——自动检测提供商并分配成员
2. **问题重述关卡**——每位成员在分析前重新表述问题，并提供另一种问题框架
3. **第一轮：独立分析（先盲评）**——所有成员并行分析（最多 400 词）
4. **第二轮：交叉质询**——成员相互质疑（300 词，必须回应至少 2 位其他成员）
5. **轮后约束**——异议配额、新颖性关卡、一致性检查、反递归（只执行一次）
6. **第三轮：最终凝练**——100 词的立场陈述
7. **综合裁决**——首先给出“未解决问题”和“建议的下一步”

### 快速模式

1. **问题重述 + 快速分析**——并行重构问题并分析（最多 200 词）
2. **最终立场**——凝练为 75 词

### 双人模式

1. **问题重述 + 开场立场**——重新表述问题并陈述立场（300 词）
2. **直接回应**——回应对手的论点（200 词）
3. **最终陈述**——50 词的立场

### 约束机制

- **有界协议是核心强制机制**——审议采用固定轮数预算（完整模式 3 轮／快速模式 2 轮／双人模式 3 轮），因此不会无限循环。反递归护栏会在轮次内强制执行边界（“毒芹规则”限制苏格拉底的连续追问；任意配对往返超过 2 条消息即被截断）。
- 异议配额 + 新颖性关卡 + 反事实检验可以防止过早收敛
- **平局裁定依赖计数后的加权票数，而不是文字印象**——每位成员在最终轮输出结构化的 `STANCE:` 行；形成共识需要达到**按领域加权后的三分之二多数**（领域内席位权重为 1.5 倍，并且必须在立场形成之前指定）。如果确实存在分裂，系统会把完整票数交给用户，而不是强行制造虚假共识
- 所有裁决都包含“投票统计”和用于跟踪结果的“后续行动”部分

</details>

## 安装

安装 18 位议会成员，以及适用于 Claude 和／或 Codex 的技能文件。

```bash
./install.sh                                   # 安装到 Claude（默认）
./install.sh --codex                           # 安装 Claude + Codex 技能
./install.sh --codex-only                      # 仅安装 Codex
./install.sh --claude-dir /path/to/.claude     # 使用非默认 Claude 配置目录
./install.sh --codex-dir /path/to/.codex       # 使用非默认 Codex 配置目录
./install.sh --dry-run                          # 只预览，不写入文件
./install.sh --copy-configs                     # 同时安装模型路由模板
```

安装完成后请重启目标客户端。运行 `./scripts/council-simulation-checklist.sh` 进行验证。你还可以通过[演示会话包](demos/session-pack.md)测试所有模式。

## 环境要求

- [Claude Code](https://claude.ai/claude-code) CLI（使用 Claude 时需要）
- [Codex](https://github.com/openai/codex)（使用 Codex 技能时需要）
- 客户端支持 Agent／Subagent（默认已启用）

**可选提供商**（自动检测，用于多提供商路由）：

- [Codex CLI](https://github.com/openai/codex)（OpenAI）——`npm i -g @openai/codex`
- [Gemini CLI](https://github.com/google-gemini/gemini-cli)（Google）——参见 [gemini-cli 仓库](https://github.com/google-gemini/gemini-cli)
- [Ollama](https://ollama.com)（本地模型）——从 ollama.com 安装
- [Cursor CLI](https://cursor.com/cli)（GPT／Claude／Gemini／Grok 聚合器）——`curl https://cursor.com/install -fsS | bash`

## 参与贡献

欢迎贡献。请先阅读[贡献指南](CONTRIBUTING.md)。

## 支持项目

如果你觉得这个项目有用，可以考虑支持我的开源工作。

[![Buy Me A Coffee](https://img.shields.io/badge/Buy%20Me%20a%20Coffee-support-orange?logo=buymeacoffee)](https://buymeacoffee.com/nyk_builderz)

**Solana 捐赠地址**

`BYLu8XD8hGDUtdRBWpGWu5HKoiPrWqCxYFSh4oxXuvPg`

## 许可证

[![CC0](https://licensebuttons.net/p/zero/1.0/88x31.png)](https://creativecommons.org/publicdomain/zero/1.0/)

在法律允许的最大范围内，作者已放弃对本作品享有的全部版权及相关或邻接权利。

---

<p align="center">
  <a href="https://star-history.com/#0xNyk/council-of-high-intelligence&Date">
    <img src="https://api.star-history.com/svg?repos=0xNyk/council-of-high-intelligence&type=Date" alt="Star History" width="400">
  </a>
</p>
