# AgentPlatform

本目录维护 Team Agent Collaboration Platform 的产品架构设计，当前不包含平台实现。

- 用户维护的方向输入为 `Team Agent Collaboration Platform.md`；不得把其中初始概念当作已确定的数据模型。
- 设计入口为 `README.md`，统一术语见 `CONTEXT.md`，跨专题关系见 `docs/architecture/overview.md`。
- 按专题完成源码研究、完整方案、贯穿案例与交叉审查后，再进入下一专题；当前开展专题三 A「执行平面与宿主适配」探索，沿用专题一、二的工作对象、执行契约与案例。
- 先确定工作机制、产品边界和核心模型，不提前编写数据库、接口或技术实现方案。
- 以订单批量导出为贯穿案例，明确案例假设与真实产品决策的区别。
- 研究引用固定源码版本与文件位置，区分代码事实、设计推导和未验证能力。参考源码只读，研究副本与临时笔记放 `.tmp/`。
- 任何专题均复用统一工作对象、Work Context、Execution Contract 和 Evidence & Feedback；不得另建一套工作状态或证据权威。
