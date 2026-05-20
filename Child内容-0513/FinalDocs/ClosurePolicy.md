# Closure Policy

Closure Policy 用来判断每轮回来后该继续当前 Episode、进入下一个 Episode，还是关闭整个 Run Plan。目标级 outcome 只记录单个目标状态，不能替代 Judge Result。

Judge Result 只允许给出 Continuing Episode、Next Episode、Run Plan Close。success_close、partial_success_close、fail_close、blocked_close、risk_aborted 都只是目标级 outcome。

## 判定表

| 条件 | Judge Result |
|---|---|
| 消息已发出且仍在 300 秒初次等待窗内 | Continuing Episode |
| 客服已回复但补贴金额、使用条件或叠加关系仍缺一项 | Continuing Episode |
| 当前目标价格未达七折，但仍存在未验证的平台券、店铺券、替代规格或活动时间 | Continuing Episode |
| 当前目标已达七折但缺少购物车价、支付前页面或客服确认等证据 | Continuing Episode |
| 当前目标已关闭但本批还有未关闭目标 | Continuing Episode |
| 当前目标无回复超过 1800 秒，但本批仍有其它目标可处理 | Continuing Episode |
| 当前目标出现拒绝，需要先分类为无权限、无利润、无活动、无替代或风险 | Continuing Episode |
| 当前批 10 个目标全部都有目标级 outcome，且后续 Episode 仍存在 | Next Episode |
| 当前批 10 个目标全部关闭，但还有至少一个目标证据字段缺失 | Continuing Episode |
| 当前批 10 个目标全部关闭且证据字段完整，且当前批不是 EP10 | Next Episode |
| EP10 的 10 个目标全部都有目标级 outcome 且证据字段完整 | Run Plan Close |
| 出现站外返现、私下转账、虚构身份、威胁投诉等系统性风险并需要终止整个任务 | Run Plan Close |
| 执行工具持续异常导致无法继续获取页面、客服或价格证据，且重试后仍不可恢复 | Run Plan Close |

## 目标级 outcome

| outcome | 含义 |
|---|---|
| success_close | 平台内可验证到手价达到七折或以下，且证据字段完整 |
| partial_success_close | 没到七折，但得到清晰最低价、活动时间或可复用路径 |
| fail_close | 明确拒绝，且无平台券、店铺券、替代规格、活动等待等后续路径 |
| blocked_close | 对方要求站外、私下补差、私下返现，或工具无法继续处理单目标 |
| risk_aborted | 继续执行会触碰虚构、威胁、骚扰、自动下单、敏感信息等风险红线 |
