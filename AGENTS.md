# AgentPlatform

本目录维护 Team Agent Collaboration Platform 的产品架构设计，当前不包含平台实现。

- 用户维护的方向输入为 `Team Agent Collaboration Platform.md`；不得把其中初始概念当作已确定的数据模型。
- 设计入口为 `README.md`，统一术语见 `CONTEXT.md`，跨专题关系见 `docs/architecture/overview.md`。
- 当前阶段按[整体产品范围](docs/architecture/overview.md#当前设计重点)推进。以成员从平台或本机开工、团队接手交付以及经验在下次工作中被采用的路径组织五个专题。设计进度与待完善处统一见[总览](docs/architecture/overview.md#4-跨专题职责)。
- 提出下一项设计时，先核对总览、对应专题及 Multica 现有入口、配置和源码，说明尚缺哪项成员决定。产品设计、案例推演和后续工程接入各按实际范围记录。[治理基线](docs/architecture/governance-baseline.md#3-扩展原则先复用再补缺口)
- 先确定工作机制、产品边界和核心模型，不提前编写数据库、接口或技术实现方案。
- 用轻量文案和跨成员订单说明同一设计如何应对不同规模的工作。团队 Wiki 与项目资料、项目代码 Wiki 可分别按需接入。
- 研究引用固定源码版本与文件位置，区分代码事实、设计推导和未验证能力。参考源码只读，研究副本与临时笔记放 `.tmp/`。
- 任何专题均复用统一工作对象、Work Context、Execution Contract 和 Evidence & Feedback；不得另建一套工作状态或证据权威。
