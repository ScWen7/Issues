# AgentPlatform

本目录维护 Team Agent Collaboration Platform 的产品架构设计，当前不包含平台实现。

- 用户维护的方向输入为 `Team Agent Collaboration Platform.md`；不得把其中初始概念当作已确定的数据模型。
- 设计入口为 `README.md`，统一术语见 `CONTEXT.md`，跨专题关系见 `docs/architecture/overview.md`。
- 当前主线见[架构总览的阶段交付与评审](docs/architecture/overview.md#本阶段交付与评审)。围绕团队实际承接、完成和复用一项研发工作的过程，先核对团队资料、项目现状、Issue 决定如何成为各角色的工作依据，再判断自主分工、SOP、本地执行、业务验收及后续改进怎样衔接。
- 专题一至四的设计、源码研究、宿主实验和专题五的场景原型按其实际覆盖提供证据。选择下一项研究时说明它影响哪位成员的哪项决定。已明确的适配与集成缺口回到相应专题验收。
- 先确定工作机制、产品边界和核心模型，不提前编写数据库、接口或技术实现方案。
- 以订单批量导出为贯穿案例，明确案例假设与真实产品决策的区别。
- 研究引用固定源码版本与文件位置，区分代码事实、设计推导和未验证能力。参考源码只读，研究副本与临时笔记放 `.tmp/`。
- 任何专题均复用统一工作对象、Work Context、Execution Contract 和 Evidence & Feedback；不得另建一套工作状态或证据权威。
