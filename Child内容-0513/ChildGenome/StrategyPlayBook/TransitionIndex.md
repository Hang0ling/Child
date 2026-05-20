# Transition Index

Transition Index 不只记录相邻阶段。它回答三个问题：当前阶段满足什么条件才能前进；证据不足时退回哪里；遇到风险、等待或拒绝时如何强制转移。

## 常规边

### stage_01_batch_intake -> stage_02_price_baseline

触发：10 个目标都有商品名、原价口径、七折目标和初始路线。

不满足时：缺少商品或价格时回到清单补齐。

优先级：normal

### stage_02_price_baseline -> stage_03_product_fact_check

触发：形成 original_price、target_price、current_seen_price、gap_to_target。

不满足时：原价不可信时进入商品事实确认。

优先级：normal

### stage_03_product_fact_check -> stage_04_discount_surface_scan

触发：关键规格已确认，或明确仍需截图补证。

不满足时：客服答非所问时用截图或复述重新校准。

优先级：normal

### stage_04_discount_surface_scan -> stage_05_stackability_check

触发：可见优惠入口已登记。

不满足时：看不到券时问商家是否有店铺券入口。

优先级：normal

### stage_05_stackability_check -> stage_06_counterparty_map

触发：得到一条当前最低可验证价格式。

不满足时：规则不清楚时转平台客服确认。

优先级：normal

### stage_06_counterparty_map -> stage_07_first_contact

触发：明确下一轮应该问商家、平台，还是先等。

不满足时：机器人重复时切换更具体的问题或人工入口。

优先级：normal

### stage_07_first_contact -> stage_08_intent_signal

触发：对方开始解释价格或权限。

不满足时：若对方只发模板，进入微问题拆解。

优先级：normal

### stage_08_intent_signal -> stage_09_merchant_floor_probe

触发：对方愿意查券、发券或推荐方案。

不满足时：对方无权限时转替代方案或平台。

优先级：normal

### stage_09_merchant_floor_probe -> stage_10_gap_framing

触发：得到最低价、拒绝理由或新券路径。

不满足时：模糊回复时复述当前价格式再问一次。

优先级：normal

### stage_10_gap_framing -> stage_11_option_design

触发：对方给补差、明确见顶或推荐替代款。

不满足时：差额过大时不硬磨，进入替代规格。

优先级：normal

### stage_11_option_design -> stage_12_alternative_sku

触发：至少得到一个可尝试方案。

不满足时：没有任何方案时进入拒绝分类。

优先级：normal

### stage_12_alternative_sku -> stage_13_evidence_pack

触发：得到替代 SKU 或确认无替代。

不满足时：替代款不匹配时回原款关闭判断。

优先级：normal

### stage_13_evidence_pack -> stage_14_platform_rule_check

触发：关键事实有证据位置。

不满足时：证据缺失时不能判定成功。

优先级：normal

### stage_14_platform_rule_check -> stage_15_payable_confirmation

触发：平台给出可用补贴、不可用原因或规则路径。

不满足时：平台无补贴时进入等待或切换。

优先级：normal

### stage_15_payable_confirmation -> stage_16_wait_control

触发：价格达到目标或明确未达目标。

不满足时：价格式不闭合时回叠加关系确认。

优先级：normal

### stage_16_wait_control -> stage_17_refusal_classify

触发：收到回复、Timer 到期或目标价值下降。

不满足时：超时后回 Judge Core。

优先级：normal

### stage_17_refusal_classify -> stage_18_target_close_decision

触发：拒绝被归类并有下一步。

不满足时：风险拒绝直接关闭目标。

优先级：normal

### stage_18_target_close_decision -> stage_19_episode_rollup

触发：目标得到 success、partial、fail、blocked 或 risk。

不满足时：证据不足时继续当前 Episode。

优先级：normal

### stage_19_episode_rollup -> stage_20_run_plan_close

触发：本批全部有目标级 outcome。

不满足时：发现漏填目标时回对应目标。

优先级：normal

### stage_05_stackability_check -> stage_14_platform_rule_check

触发：叠加规则来自平台券、补贴、价格保护，商家无法确认。

不满足时：继续商家侧最低价探测。

优先级：high

### stage_09_merchant_floor_probe -> stage_14_platform_rule_check

触发：商家见顶且差额小于 10%。

不满足时：差额较大时进入方案设计或替代规格。

优先级：high

### stage_10_gap_framing -> stage_12_alternative_sku

触发：差额过大或对方明确利润不支持。

不满足时：差额小则继续补齐路径。

优先级：normal

### stage_16_wait_control -> stage_17_refusal_classify

触发：Timer 到期后仍无有效回复或收到拒绝。

不满足时：收到有效回复则回到对应事实、券或价格阶段。

优先级：high

### stage_17_refusal_classify -> stage_18_target_close_decision

触发：无合规可行路径、站外诱导或已拿到清晰最低价。

不满足时：按拒绝类型回到平台规则、替代规格或证据打包。

优先级：high

## 强制边

- 出现站外联系方式、私下返现、私下转账：立即进入 stage_18_target_close_decision，目标级 outcome 记 blocked_close，Judge Result 仍按三态判断。
- 执行动作可能触发支付、下单、投诉威胁、虚构身份：阻断动作，进入 stage_18_target_close_decision，目标级 outcome 记 risk_aborted。
- 单目标等待超过 1800 秒：进入 stage_17_refusal_classify，再由 Judge Core 判断继续当前 Episode 或关闭目标。
- 单个目标关闭后，本批还有未关闭目标：Judge Result 仍是 Continuing Episode，转回 stage_01_batch_intake 选择下一个目标。
- 本批 10 个目标全部关闭且不是 EP10：Judge Result 是 Next Episode。
- EP10 全部关闭或系统性风险终止：Judge Result 是 Run Plan Close。
