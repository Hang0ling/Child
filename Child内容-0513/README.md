# Agentic RL Project Structure

这个项目描述一个拼多多站内议价任务文件集：选择 100 个商品，分别与对应商家或平台客服沟通，争取把最终可支付价格压到原价 70% 或以下。

## 文件分工

- `.md` 给人读：策略、判断、上下文、轨迹模板。
- `.json` 给程序读：枚举、节点、边、命令、计时、判定结果。
- 可执行信息不单独伪装成硬字段，而是融入清晰句子，再由脚本抽取。

## 入口

- `ChildGenome/StrategyPlayBook/LongTermStrategyGraph.md`：20 阶段长期策略图。
- `ChildGenome/StrategyPlayBook/ShortTermStrategyGraph.md`：100 条短期战术。
- `ChildGenome/StrategyPlayBook/TransitionIndex.md`：阶段转移和强制边。
- `EnvironmentSettings/`：任务目标、风险、先验知识、关闭规则。
- `Signals/`：当前轮执行与判断信号。
- `TrajectoryPackage/`：真实运行结束后的轨迹包格式。
