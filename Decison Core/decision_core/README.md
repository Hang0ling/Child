# Decision Core MVP

这个目录实现了一个可运行的 Decision Core MVP：

1. `ControlFlowDecider`：规则判断 `continue_current_episode` / `next_episode`
2. `ContextBuilder`：生成统一 `NormalizedContext`
3. `StrategyMemoryComposer`：匹配 Strategy Playbook，召回并挂载 Experience Memory
4. `BriefPlanBuilder`：生成结构化 `BriefPlan`
5. `BriefValidator`：校验模式、字段、步骤、约束和续跑/新 Episode 特定规则
6. `BriefRepairer`：最多修复 2 次，不合格则不渲染坏 Brief
7. `BriefRenderer`：用固定模板渲染最终 `Execution Brief`

## 运行示例

从当前项目根目录执行：

```bash
python -m decision_core.cli \
  --input decision_core/examples/next_episode_input.json \
  --print-brief

python -m decision_core.cli \
  --input decision_core/examples/continue_input.json \
  --print-brief
```

写出完整结构化结果：

```bash
python -m decision_core.cli \
  --input decision_core/examples/next_episode_input.json \
  --output decision_core/examples/next_episode_output.json \
  --brief-output decision_core/examples/next_episode_brief.txt
```

## 输入字段

顶层 payload 支持：

- `judge_result`
- `execution_result`
- `act_log`
- `history_context`
- `run_plan`
- `environment_settings`
- `strategy_playbook`
- `experience_memory`

`Opponent State` 指目标用户状态，不指手机页面状态。可以在输入中提供：

- `history_context.target_user_state`
- `history_context.opponent_state`
- `execution_result.target_user_state`
- `run_plan.target_user_state`
- `run_plan.next_episode.target_user_state`

如果没有提供，系统会按当前 step 推断目标用户状态，例如“尚未锁定目标用户”“候选用户待验证”“已具备触达理由”“待确认优惠券送达”。

## 输出字段

`DecisionCoreOrchestrator.run(payload)` 返回：

- `ok`
- `control_decision`
- `normalized_context`
- `strategy_result`
- `brief_plan`
- `validation`
- `repair_history`
- `execution_brief`

如果最终校验失败，`ok=false`，`execution_brief=null`，不会输出坏 Brief。

## 测试

```bash
python -m unittest discover -s decision_core/tests
```
