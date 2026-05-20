#!/usr/bin/env python3

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


CATEGORIES = [
    ("EP01", "厨房小件", ["304 不锈钢保温杯", "小麦秸秆饭盒", "硅胶锅铲套装", "可视油壶", "双层沥水篮", "手动切菜器", "密封保鲜袋 100 只", "竹纤维洗碗布 10 条", "鸡蛋收纳盒", "厨房纸巾架"]),
    ("EP02", "收纳整理", ["透明鞋盒 6 只", "抽屉分隔板", "衣柜收纳箱", "桌面理线盒", "真空压缩袋", "可折叠脏衣篮", "内衣收纳盒", "冰箱收纳盒", "药品收纳盒", "浴室置物架"]),
    ("EP03", "家清耗材", ["厨房湿巾 10 包", "洗衣凝珠 60 颗", "马桶清洁泡腾片", "一次性抹布卷", "地板清洁片", "除霉啫喱", "油污清洁剂", "垃圾袋 120 只", "洗碗块 40 颗", "静电除尘纸"]),
    ("EP04", "宠物用品", ["猫砂 10kg", "猫抓板", "宠物湿巾", "狗狗拾便袋", "宠物饮水机滤芯", "猫碗双碗架", "宠物梳毛器", "猫玩具逗猫棒套装", "狗狗牵引绳", "宠物除臭喷雾"]),
    ("EP05", "母婴小件", ["婴儿湿巾 80 抽 5 包", "儿童防撞角", "宝宝硅胶围兜", "奶瓶刷套装", "儿童衣架 20 支", "婴儿口水巾", "儿童餐盘", "宝宝洗衣皂", "婴儿指甲剪套装", "推车挂钩"]),
    ("EP06", "服饰与袜裤", ["男士棉袜 10 双", "女士无痕内裤 4 条", "防晒冰袖", "儿童打底裤", "纯棉短袖 T 恤", "运动束脚裤", "薄款家居服", "遮阳帽", "保暖袜 5 双", "帆布腰带"]),
    ("EP07", "数码配件", ["Type-C 数据线 3 条", "20W 充电头", "手机支架", "钢化膜 3 片", "蓝牙耳机保护套", "鼠标垫", "USB 分线器", "平板收纳包", "自拍杆三脚架", "理线魔术贴"]),
    ("EP08", "美妆个护", ["氨基酸洗面奶", "压缩面膜 100 粒", "一次性洗脸巾", "眉笔 2 支", "粉扑 6 个", "护手霜 3 支", "牙线棒 100 支", "便携漱口水", "身体乳", "修眉刀 6 支"]),
    ("EP09", "零食饮品", ["每日坚果 750g", "无糖苏打水 12 瓶", "低脂鸡胸肉", "冻干水果脆", "黑咖啡粉", "牛肉干", "儿童鳕鱼肠", "即食燕麦片", "酸梅汤粉", "玉米脆片"]),
    ("EP10", "小家居用品", ["香薰蜡烛", "小夜灯", "门后挂钩", "抱枕套 2 个", "防滑地垫", "桌面垃圾桶", "衣物除毛器", "晒被夹 12 个", "窗帘绑带", "鞋刷套装"]),
]

PRICE_SEEDS = [59, 32, 45, 28, 41, 36, 24, 18, 27, 33]
ROUTES = ["券叠加", "直降", "替代规格", "活动价", "平台补贴"]


def write(path: str, content: str) -> None:
    target = ROOT / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content.rstrip() + "\n", encoding="utf-8")


def dump(path: str, data: object) -> None:
    write(path, json.dumps(data, ensure_ascii=False, indent=2))


def build_targets() -> list[dict[str, object]]:
    targets: list[dict[str, object]] = []
    for ep_idx, (episode_id, category, products) in enumerate(CATEGORIES, start=1):
        for item_idx, product in enumerate(products, start=1):
            merchant_no = (ep_idx - 1) * 10 + item_idx
            original = PRICE_SEEDS[item_idx - 1] + (ep_idx - 1) * 4 + (item_idx % 3) * 3
            targets.append({
                "episode_id": episode_id,
                "merchant_id": f"M{merchant_no:03d}",
                "category": category,
                "product": product,
                "original_price": original,
                "target_price_70pct": round(original * 0.7, 1),
                "suggested_initial_route": ROUTES[(item_idx + ep_idx) % len(ROUTES)],
                "result_fields": "blank_until_real_run",
            })
    return targets


TARGETS = build_targets()


def simple_spec(meta_id: str, title: str, subtitle: str, kind: str, summary: list[str], sections: list[dict[str, object]], runtime_spec: dict[str, object]) -> dict[str, object]:
    return {
        "meta": {"id": meta_id, "title": title, "subtitle": subtitle, "version": 5, "kind": kind},
        "summary": summary,
        "sections": sections,
        "runtime_spec": runtime_spec,
    }


def render_doc(spec: dict[str, object]) -> str:
    meta = spec["meta"]
    lines = [f"# {meta['title']}", "", str(meta.get("subtitle", "")), ""]
    for paragraph in spec.get("summary", []):
        lines.extend([paragraph, ""])
    for section in spec.get("sections", []):
        lines.extend([f"## {section['title']}", ""])
        for paragraph in section.get("paragraphs", []):
            lines.extend([paragraph, ""])
        for bullet in section.get("bullets", []):
            lines.append(f"- {bullet}")
        if section.get("bullets"):
            lines.append("")
        for item in section.get("items", []):
            lines.extend([f"### {item['title']}", ""])
            for paragraph in item.get("paragraphs", []):
                lines.extend([paragraph, ""])
            for bullet in item.get("bullets", []):
                lines.append(f"- {bullet}")
            if item.get("bullets"):
                lines.append("")
    return "\n".join(lines)


DETAILED_STAGES = [
    {"id": "stage_01_batch_intake", "name": "批次接入", "core": "把 10 个目标从清单变成可处理对象。", "read": "读取商品、价格种子、品类、商家编号和本批范围。", "do": "为每个目标建立空白状态卡，先标记未知字段，不急着沟通。", "say": "这一阶段通常不发消息，只准备后续问题。", "exit": "10 个目标都有商品名、原价口径、七折目标和初始路线。", "fallback": "缺少商品或价格时回到清单补齐。"},
    {"id": "stage_02_price_baseline", "name": "价格基线", "core": "先知道七折到底是多少，避免只靠感觉砍价。", "read": "原价、页面价、券前价、券后价、同页活动说明。", "do": "计算七折目标、当前差额、可接受最高价和明显不值得继续的价格带。", "say": "后续可说：我这边预算大概在某个到手价区间，想先确认页面价怎么算。", "exit": "形成 original_price、target_price、current_seen_price、gap_to_target。", "fallback": "原价不可信时进入商品事实确认。"},
    {"id": "stage_03_product_fact_check", "name": "商品事实确认", "core": "确认谈的是同一个东西，不让价格谈判建立在误读上。", "read": "规格、数量、材质、保质期、适配型号、发货地、库存。", "do": "把会影响价格的事实单独列出，比如几包装、是否含赠品、是否为补充装。", "say": "这款是页面这个规格和数量吗？我主要想确认到手价前先把规格对齐。", "exit": "关键规格已确认，或明确仍需截图补证。", "fallback": "客服答非所问时用截图或复述重新校准。"},
    {"id": "stage_04_discount_surface_scan", "name": "优惠入口扫描", "core": "先找所有可能降价入口，再决定问谁。", "read": "商品页领券、店铺首页券、购物车券、关注券、满减、红包、秒杀入口。", "do": "记录每个入口的金额、门槛、是否可领、是否已过期。", "say": "我看到页面有券和活动，想确认哪些能一起用。", "exit": "可见优惠入口已登记。", "fallback": "看不到券时问商家是否有店铺券入口。"},
    {"id": "stage_05_stackability_check", "name": "叠加关系确认", "core": "七折通常不是单一让利，而是多层优惠组合。", "read": "券与券、券与活动、红包与平台补贴的叠加限制。", "do": "把价格拆成页面价减哪些项，避免把不能叠加的优惠算进去。", "say": "店铺券和平台券能一起用吗？如果不能，哪个方案到手价更低？", "exit": "得到一条当前最低可验证价格式。", "fallback": "规则不清楚时转平台客服确认。"},
    {"id": "stage_06_counterparty_map", "name": "对手画像", "core": "先判断对方能决定什么，再决定怎么问。", "read": "商家客服、机器人、平台客服、售后入口、活动客服的身份信号。", "do": "标注权限、态度、回复速度、是否愿意解释、是否出现风险词。", "say": "请问这个优惠是店铺这边能处理，还是要平台客服确认？", "exit": "明确下一轮应该问商家、平台，还是先等。", "fallback": "机器人重复时切换更具体的问题或人工入口。"},
    {"id": "stage_07_first_contact", "name": "第一句接触", "core": "第一句话不压迫，先让对方愿意解释。", "read": "商品事实、当前差额、可见优惠入口。", "do": "用具体事实开场，只问一个问题。", "say": "你好，我想买这款，页面上看到几种优惠，能麻烦你帮我看一下最终到手价怎么叠吗？", "exit": "对方开始解释价格或权限。", "fallback": "若对方只发模板，进入微问题拆解。"},
    {"id": "stage_08_intent_signal", "name": "购买意向信号", "core": "用真实动作降低对方怀疑，但不虚构订单。", "read": "是否收藏、加购、浏览同店相近款、是否确实愿意今天成交。", "do": "完成真实动作后如实说明，争取对方把问题当成临门成交。", "say": "我已经收藏并放进购物车了，主要差在最后到手价，想请你帮我看还有没有能叠的券。", "exit": "对方愿意查券、发券或推荐方案。", "fallback": "对方无权限时转替代方案或平台。"},
    {"id": "stage_09_merchant_floor_probe", "name": "商家底价探测", "core": "问平台内最低可支付价，不问私下补差。", "read": "当前到手价、七折目标、差额、商家已给优惠。", "do": "把差额说小，把成交条件说清楚，给对方选择空间。", "say": "如果都在平台内完成，您这边能帮我看一下最低到手价大概能到多少吗？", "exit": "得到最低价、拒绝理由或新券路径。", "fallback": "模糊回复时复述当前价格式再问一次。"},
    {"id": "stage_10_gap_framing", "name": "差额框架", "core": "把冲突从“让不让利”改成“差多少能成交”。", "read": "差额绝对值、差额比例、商家态度。", "do": "当差额小于 10% 时强调补齐最后差额，大差额则转替代款。", "say": "现在离我的预算还差大概几元，如果能补到这个区间，我今天就在平台内定。", "exit": "对方给补差、明确见顶或推荐替代款。", "fallback": "差额过大时不硬磨，进入替代规格。"},
    {"id": "stage_11_option_design", "name": "方案设计", "core": "把一个降价请求拆成多个可行方案。", "read": "直降、店铺券、组合装、低配款、无赠品版、等待活动。", "do": "一次给两到三个选项，让对方选最容易执行的。", "say": "如果这款不方便直接降，店铺券、组合装或同用途低配款，哪种更接近预算？", "exit": "至少得到一个可尝试方案。", "fallback": "没有任何方案时进入拒绝分类。"},
    {"id": "stage_12_alternative_sku", "name": "替代规格", "core": "原款压不动时，不把时间耗死在原款。", "read": "同用途、少赠品、不同包装、组合装、活动款。", "do": "只接受需求仍匹配的替代，不为了低价牺牲核心需求。", "say": "如果这款到不了预算，有没有同用途、少赠品或组合里更划算的一款？", "exit": "得到替代 SKU 或确认无替代。", "fallback": "替代款不匹配时回原款关闭判断。"},
    {"id": "stage_13_evidence_pack", "name": "证据打包", "core": "每个数字都要知道从哪里来。", "read": "当前商品页、领券页、购物车价、客服回复、活动说明。", "do": "只记录必要证据，不发无关截图，不暴露个人信息。", "say": "我这边页面显示是这个到手价，想确认是不是还有券没有叠上。", "exit": "关键事实有证据位置。", "fallback": "证据缺失时不能判定成功。"},
    {"id": "stage_14_platform_rule_check", "name": "平台规则确认", "core": "商家解释不了的平台券、补贴和价格保护交给平台客服。", "read": "平台券入口、补贴提示、价格保护规则、客服解释。", "do": "问规则和可用条件，不要求客服绕规则处理。", "say": "平台这边是否还有可叠加补贴、活动补贴或价格保护？如果有，条件是什么？", "exit": "平台给出可用补贴、不可用原因或规则路径。", "fallback": "平台无补贴时进入等待或切换。"},
    {"id": "stage_15_payable_confirmation", "name": "到手价确认", "core": "只认最终可支付价格，不认口头好像可以。", "read": "购物车到手价、券使用状态、活动顺序、支付前页面。", "do": "复核价格式是否达到七折，未确认前不写成功。", "say": "我理解现在最终到手价是这个数字，对应这些优惠，对吗？", "exit": "价格达到目标或明确未达目标。", "fallback": "价格式不闭合时回叠加关系确认。"},
    {"id": "stage_16_wait_control", "name": "等待控制", "core": "等待是策略，不是空转。", "read": "最后发送时间、等待窗口、回复状态、目标价值。", "do": "初次等 300 秒，最长 1800 秒；等待期间不刷屏。", "say": "通常不再发送；若需补充，只补一个关键证据。", "exit": "收到回复、Timer 到期或目标价值下降。", "fallback": "超时后回 Judge Core。"},
    {"id": "stage_17_refusal_classify", "name": "拒绝分类", "core": "拒绝不是结尾，先判断拒绝类型。", "read": "没权限、没利润、没活动、规则限制、机器人模板、站外诱导。", "do": "权限问题转平台，利润问题转替代款，规则问题补证，风险问题关闭。", "say": "理解，如果这款确实做不到，能否帮我确认最接近预算的合规方案？", "exit": "拒绝被归类并有下一步。", "fallback": "风险拒绝直接关闭目标。"},
    {"id": "stage_18_target_close_decision", "name": "目标关闭判断", "core": "关闭单个目标，不等于关闭整个 Episode。", "read": "最终价、证据、拒绝类型、是否还有可行路径。", "do": "给目标级 outcome，但 Judge Result 仍只用三态。", "say": "通常不再发消息，只整理证据和结论。", "exit": "目标得到 success、partial、fail、blocked 或 risk。", "fallback": "证据不足时继续当前 Episode。"},
    {"id": "stage_19_episode_rollup", "name": "批次汇总", "core": "10 个目标都处理完，才考虑切到下个 Episode。", "read": "本批每个目标的状态、证据完整度、风险事件。", "do": "检查是否还有未关闭目标；有则继续，无则输出 Next Episode 或最终关闭。", "say": "不面向客服，只面向 Judge Core。", "exit": "本批全部有目标级 outcome。", "fallback": "发现漏填目标时回对应目标。"},
    {"id": "stage_20_run_plan_close", "name": "全局关闭", "core": "只有 EP10 完成或系统性风险出现，才关闭整个 Run Plan。", "read": "100 个目标登记表、风险日志、复盘字段。", "do": "只输出 Run Plan Close，并整理轨迹包格式。", "say": "不再发议价消息。", "exit": "Run Plan Close。", "fallback": "若只是单目标完成，回 Episode 汇总。"},
]


def build_tactics() -> list[dict[str, str]]:
    raw = """
st001_warm_specific_open|暖而具体的开场|刚进入客服窗口，对方还不知道你要什么。|轻、短、明确|先给出商品和目的，不把砍价放在第一句。|你好，我想买这款，主要想先确认最终到手价怎么计算，能麻烦你帮我看一下吗？|对方解释价格后，进入优惠结构确认。|不直接要求七折，不使用命令语气。|不虚构订单。
st002_permission_to_ask|先请求允许|担心对方把问题当成压价或纠缠。|礼貌、低压|先征求对方是否方便看一个小问题，降低抵触。|我想确认一个小问题，如果方便的话麻烦你帮我看下这个券能不能叠加。|对方愿意看，就只问一个具体点。|不要连续追问多个问题。|同义问题最多两次。
st003_single_point_focus|单点问题|对方回复模板化，或问题太大没人答。|窄、清楚|把问题缩小到一个可判断的事实。|我先只确认一个点：这张店铺券能不能和页面活动一起用？|得到单点答案后再问下一点。|不把规格、库存、价格一起塞进去。|每轮只推进一个缺口。
st004_rule_curiosity|规则好奇|需要问优惠规则但不想显得质疑。|请教式|把自己放在不懂规则的位置，让对方解释。|我可能没看懂规则，想请你帮我确认一下，这个优惠是下单页自动叠加吗？|对方解释后复述确认。|不说平台写错或客服不专业。|只问平台内规则。
st005_face_saving_limit|给权限台阶|对方可能没权限直接降价。|理解、给台阶|先承认权限边界，再问可行路径。|如果这个不是你这边能直接改的，也没关系，能不能帮我看下还有哪个平台内入口能确认？|无权限则转平台或替代方案。|不逼客服承诺权限外事项。|不得要求越权。
st006_product_respect|先认可商品|商家可能对直接砍价敏感。|尊重、自然|先说明商品符合需求，再谈价格差额。|这款规格是合适的，我主要卡在最后到手价，想看看有没有合规优惠能补一点。|商家愿意沟通后进入差额框架。|不夸大、不奉承。|认可必须真实。
st007_budget_plain|预算坦白|需要说目标价但不想强压。|诚实、平静|把预算说成自己的限制，不说成对方义务。|我这边预算大概在 49 元左右，所以想确认有没有办法把到手价靠近这个区间。|对方给方案则验证价格。|不说你必须做到这个价。|预算不得伪装成平台规则。
st008_gap_as_problem|把差额变成共同问题|当前价接近目标价，只差一点。|合作、具体|把冲突改成一起解决小差额。|现在大概差 3 元左右，我想看有没有券或活动能把这点补上。|差额小则问补贴；无补贴则收口。|不威胁去别家。|差额必须计算真实。
st009_no_pressure_frame|不施压框架|对方防御或说利润低。|温和、降压|明确表示理解，不把对方逼进对抗。|如果确实没有空间我理解，我只是想确认有没有平台内能用的券或活动。|对方放松后问规则或替代。|不能把理解变成继续纠缠。|拒绝后要能收口。
st010_today_but_true|真实今日意向|确实愿意当天成交。|真诚、克制|表达今天可成交，但不虚构已下单。|如果到手价能接近这个区间，我今天可以直接在平台内定。|对方若给优惠，进入到手价确认。|没准备成交时不要使用。|不得说已下单。
st011_cart_signal_clean|购物车信号|已加购但未下单。|事实、无夸张|用加购说明认真购买，不暗示已经付款。|我已经放到购物车了，页面现在显示这个价，想确认还有没有券没叠上。|对方看价格后补截图或问券。|不能说已经拍下或已付款。|不得触发支付。
st012_favorite_signal_clean|收藏信号|已收藏商品或店铺。|轻、真实|把收藏作为购买意向，不作为交换。|我已经收藏了，主要想等你帮我确认下最终到手价。|对方愿意查后进入优惠确认。|不能暗示收藏就该给私下优惠。|不得索要站外补偿。
st013_same_store_browse|同店浏览|原款价格压不动，仍愿意在店内买。|开放、合作|说明看过同店商品，给商家推荐空间。|我也看了店里相近款，如果这款不好做到预算，有没有同用途更划算的规格？|对方推荐后进入替代 SKU 验证。|不能用浏览同店商品威胁。|替代必须同用途。
st014_screenshot_clarity|截图澄清|双方看到价格不同。|客观、澄清|截图只用于说明自己看到的页面。|我这边页面显示的是这个到手价，我发当前页截图给你，想确认是不是有券没叠上。|截图后等对方解释。|不发含个人信息截图。|截图必须来自当前页面。
st015_cart_screenshot_check|购物车截图核价|需要确认最终价。|事实、可验证|用购物车价代替口头猜测。|我这边购物车显示约 52 元，想确认最终是不是只能到这个价。|确认后进入差额或关闭。|不把购物车价伪装成支付成功。|不自动下单。
st016_coupon_page_check|领券页核对|券入口复杂。|请教、细节|让对方看具体券，不泛泛问便宜。|领券页这里有几张券，我不确定哪张能用，能帮我看下优先领哪张吗？|得到券路径后重新计算。|不要求对方发站外券。|只接受平台内券。
st017_repeat_back|复述确认|对方说了复杂规则。|认真、准确|先复述再推进，避免误读。|我理解是店铺券能用，但平台券不能和活动叠，对吗？|确认后进入下一步。|不选择性复述对自己有利部分。|复述必须完整。
st018_summary_before_ask|先总结再请求|多轮信息已经混乱。|有条理|把已知信息压缩成一句，再问一个缺口。|我现在理解是原价 70，商家侧约 52，还差 3 元；想确认平台这边有没有补贴。|对方能快速定位问题。|总结必须真实。|不得加入未确认数字。
st019_soft_correction|温和纠偏|客服误解了商品或价格。|不指责|用“可能我没说清”修复误解。|可能我刚才没说清，我问的是这个 10 包规格，不是单包价格。|对方回到正确规格后继续。|不说你理解错了。|纠偏不带情绪。
st020_robot_reframe|机器人重问|机器人模板循环。|短句、关键词|用平台更容易识别的关键词重发。|我想咨询：优惠券是否可叠加，当前商品到手价如何计算。|仍循环则找人工或等待。|不刷屏。|重发不得超过限制。
st021_no_oriented_question|让对方说不是|对方不愿直接承诺。|低压|用“是否不方便”让对方更容易回答。|这款如果不方便再优惠，是因为店铺这边没有权限吗？|得到原因后分类。|不把回答当成承诺。|不能诱导虚假权限。
st022_calibrated_how|怎么做问题|需要对方参与方案设计。|开放、合作|问“怎么更接近”，不只问“能不能降”。|如果我要把到手价靠近 49 元，平台内一般怎么操作最合适？|对方给路径后验证。|不要求绕规则。|路径必须可验证。
st023_what_would_work|什么可行|直接要求失败后。|探索式|让对方说可行范围。|那这款在平台内什么方案最接近这个预算？|进入可行方案。|不追问同一个不可行要求。|失败后要换问法。
st024_two_option_choice|二选一减负|对方不知道怎么回答。|清楚、低负担|只给两个选项。|你看是店铺券更可能补一点，还是换组合装更合适？|对方选一条后深入。|选项不要超过三个。|选项必须合规。
st025_small_yes_inventory|先问库存|尚未确认是否值得谈。|基础、自然|用库存问题开启，不急着砍价。|这款现在是有现货的吗？如果有，我再确认一下到手价。|有货再谈价格；无货转替代。|无货不继续硬谈原款。|库存影响目标状态。
st026_size_before_price|规格先于价格|价格取决于规格。|谨慎|先确认规格，避免低价是不同版本。|这个价格对应的是 10 包这一款吗？规格一样我再算到手价。|规格一致再谈优惠。|不拿不同规格比较。|规格不一致需重算。
st027_quantity_check|数量确认|套装商品容易误读。|细致|确认数量和单位。|页面写的是 10 包，我想确认是一单发 10 包对吗？|数量确认后核价。|不把赠品数量算成主商品。|数量必须证据化。
st028_material_check|材质确认|材质影响价格和替代。|稳妥|先问材质，再谈替代。|这个材质和页面描述一致吗？如果一致我再看优惠怎么叠。|材质确认后继续。|不为低价牺牲核心材质。|材质不明不判成功。
st029_expiry_check|保质期确认|食品、母婴、清洁耗材。|谨慎、负责|把保质期作为购买前提。|这批大概是什么日期的？日期合适我再确认到手价。|日期合适再谈优惠。|临期不能默认接受。|安全优先于低价。
st030_shipping_check|运费核对|运费影响到手价。|实用|把运费纳入最终价。|这个价格下还需要运费吗？我想按最终实际支付来算。|确认后重算。|不忽略运费判成功。|总价才是到手价。
st031_threshold_check|满减门槛|满减需要凑单。|计算式|问门槛，不盲目加购。|这个满减需要满多少才能用？单买这款能触发吗？|不能触发则问组合。|不为了满减买无用商品。|凑单必须真实需要。
st032_bundle_probe|组合装探测|单件价不达标。|建设性|问组合是否降低单价。|如果买组合装，单件到手价会不会更低一点？|组合划算则核总价。|只买真实需要的组合。|组合价要折算单件。
st033_no_gift_version|无赠品版|赠品拉高价格。|务实|把赠品换成价格空间。|如果不要赠品，有没有基础版或简装版更接近预算？|有则验证规格。|不要求私下扣赠品补钱。|只能换平台内 SKU。
st034_old_package|旧包装询问|新旧包装价差。|自然|问旧包装或普通包装。|有没有旧包装或普通包装版本？功能一样的话我可以接受。|有则确认差异。|不能接受影响使用的差异。|版本差异要记录。
st035_color_size_discount|颜色尺码差异|服饰家居常见。|灵活|问不影响需求的颜色尺码。|如果颜色不同价格更合适，也可以帮我推荐一下。|转替代款。|不接受不合适尺码。|替代不牺牲需求。
st036_activity_time|活动时间|当前无优惠但可能有活动。|耐心|询问活动周期。|如果今天没有合适优惠，下一次平台内活动大概是什么时候？|记录等待或切换。|不让对方承诺虚假活动。|未来活动不算当前成功。
st037_price_protection|价保确认|担心买后降价。|规则导向|问价格保护而非私下补差。|这款如果之后活动价更低，平台内有价格保护规则吗？|有价保则降低犹豫。|不要求店外补差。|只按规则处理。
st038_platform_coupon_gap|平台券补差|商家见顶，差额小。|规则归位|把最后差额交给平台规则。|商家这边已经确认到这个价，平台侧还有可叠加补贴吗？|平台回复后核价。|不要求平台违规处理。|平台结果要记录。
st039_merchant_authority|商家权限确认|不知道商家能做什么。|尊重权限|问权限边界。|这个优惠是店铺这边能处理的吗，还是只能看平台活动？|按权限转移。|不逼客服越权。|权限不清先不压价。
st040_human_handoff|人工入口|机器人解决不了。|平静|请求人工但不发火。|这个问题涉及券叠加，机器人可能不太好判断，能转人工帮我确认吗？|转人工后缩小问题。|不辱骂机器人或客服。|人工入口也要等待。
st041_acknowledge_margin|承认利润|商家说利润低。|理解|承认成本，再问替代。|理解利润有限，那有没有同用途但成本更合适的规格？|转替代款。|不说你肯定还有利润。|不争利润真实性。
st042_acknowledge_policy|承认规则|平台说规则限制。|接受、求路径|不争规则，问可行路径。|明白规则限制，那当前商品还有哪种平台内优惠是能用的？|进入可用路径。|不要求绕开规则。|规则优先。
st043_acknowledge_busy|承认忙碌|客服回复慢。|体谅|降低催促感。|不着急，你方便的时候帮我确认一下券能不能叠加就行。|等待 Timer。|不在短时间内重复催。|等待按 Timer 执行。
st044_thank_before_next|先谢再问|对方已经帮忙一次。|感激、顺接|感谢后只补一个问题。|谢谢你刚才帮我看了，我再确认最后一点：购物车价就是最终价吗？|确认后收口。|不把感谢变成继续压迫。|补问只能一个。
st045_micro_commitment|小承诺推进|需要对方继续查。|轻承诺|请求对方只帮忙看一步。|能不能先帮我看一下有没有可领券？如果没有我就不继续问这个方向。|有券继续，无券转移。|说到做到，别无券后继续纠缠。|承诺要兑现。
st046_if_then_close|条件式收口|希望表达成交条件。|清楚、克制|把条件说清，不施压。|如果最终能到 49 元左右，我就按这个页面价在平台内定；如果不行我也理解。|对方给最终价后判断。|不能伪装成交承诺。|条件必须真实。
st047_boundary_statement|边界声明|容易被引导站外。|坚定、礼貌|提前表明只接受平台内方案。|我这边只走平台内优惠和下单页价格，想确认有哪些合规方式。|对方站外则关闭。|不继续站外话题。|站外立即阻断。
st048_no_fake_bulk|不装大单|商家问买几件。|诚实|只说真实数量。|我目前就是按这一单看价格，不想乱说采购量，主要确认这单到手价。|商家按真实数量报价。|不虚构批量采购。|身份和数量真实。
st049_no_complaint_threat|不用投诉|对方服务差或拒绝。|克制|把情绪和价格分开。|没关系，我只是确认价格规则，不涉及投诉或评价。|缓和后继续或关闭。|不暗示差评换价。|威胁动作阻断。
st050_private_cashback_stop|私下返现阻断|对方提出私下补差。|礼貌但明确|立即拉回平台内。|这个我不走站外哈，如果平台内没有办法，我就按当前价格判断。|进入关闭或平台规则。|不交换联系方式。|私下返现关闭目标。
st051_personal_info_mask|隐私遮挡|需要发截图。|谨慎|先遮挡再发送。|我可以发当前价格截图，但会把账号和地址遮掉，只看价格部分。|发图后等解释。|不发个人信息。|截图先脱敏。
st052_evidence_label|证据标注|多张截图或多轮价格。|有序|告诉对方每个数字来自哪里。|这个 70 是页面原价，52 是购物车显示，我想确认差额还能不能通过券补。|对方更易判断。|数字来处不清就不要报。|数字必须可追溯。
st053_price_formula|价格算式|到手价复杂。|结构化|用算式减少误会。|我现在理解是页面价减店铺券再减活动，最后约 52，对吗？|确认后问缺口。|不把未验证券写进算式。|价格式必须闭合。
st054_low_gap_frame|小差额框架|只差几元。|轻推|强调小缺口而不是大砍价。|现在不是差很多，主要差最后几元，想看有没有券能补齐。|有券则核价，无券则收口。|不说这点钱你们肯定能让。|不要道德绑架。
st055_high_gap_switch|大差额转向|离七折很远。|理性|不硬磨原款。|这个差距有点大，原款如果做不到，有没有更接近预算的同用途款？|转替代 SKU。|不浪费多轮硬压。|保护整体任务时间。
st056_anchor_without_attack|锚定不攻击|需要说目标价。|平稳|报预算，不评价商家贵。|我预算在 49 元左右，不是说这款不好，只是想看有没有合适优惠。|对方更少防御。|不说你家太贵。|不贬低商品。
st057_contrast_options|对比方案|有多个方案。|比较、清楚|让对方帮选低价方案。|这两个方案里，哪个最终到手价更低、限制更少？|选择低风险方案。|不只看金额忽略条件。|条件也要记录。
st058_decoy_remove|去掉无效选项|赠品或凑单干扰。|清爽|删除不需要的价值项。|赠品对我不是必须，如果去掉赠品有更低方案，我更愿意看那个。|转无赠品版。|不要求私下退赠品钱。|只能换平台内版本。
st059_confirm_no_hidden_cost|隐藏成本|运费、门槛、凑单。|谨慎|确认没有额外成本。|这个到手价还需要凑单或运费吗？我想看实际支付总价。|确认后判定。|不只看商品页低价。|总支付价为准。
st060_time_value|时间成本|单目标耗时过长。|自控|主动收口避免任务拖住。|如果现在没有明确优惠，我先不占用你时间，后面有活动我再看。|关闭或等待。|不因不甘心继续磨。|整体完成率优先。
st061_polite_pause|礼貌暂停|对方沉默。|克制|暂停而非催促。|我先等你确认，辛苦了。|进入 Timer。|不连续发送问号。|等待不刷屏。
st062_delayed_followup|延迟补问|Timer 后需要补一句。|简短|只补充一次。|我补充一下，我只想确认平台券能不能叠加，方便时回复就行。|再等待或关闭。|同义补问最多一次。|遵守等待时间。
st063_reply_speed_label|回复速度标注|对方慢但未拒绝。|观察|内部标记，不对客服施压。|不发送；记录为回复慢，等待到 Timer。|到期后 Judge。|不把慢回复当拒绝。|内部动作不发消息。
st064_defense_label|防御识别|对方语气变硬。|降温|承认不强求。|我不是要为难你，如果规则不支持，麻烦你告诉我就行。|降低防御后问替代。|不反驳情绪。|情绪高时不加压。
st065_confusion_label|困惑识别|对方没看懂。|澄清|先承认自己表达复杂。|可能我说复杂了，我只想问最终付款页还能不能再少一点。|回到单点问题。|不怪对方没懂。|先修复表达。
st066_goodwill_label|善意接住|对方愿意帮忙。|感谢、推进|接住对方善意，让其继续。|谢谢你愿意帮我看，那我就按你说的先确认这张券。|继续核券。|不趁机加压太多。|保持请求小。
st067_refusal_permission|拒绝后请求许可|被拒后还想问替代。|尊重|先问能否再问一个替代问题。|明白，那我还能再问一个替代规格的问题吗？|同意后问替代。|不同意就收口。|尊重拒绝。
st068_refusal_reason|拒绝原因|不知道下一步。|诊断|让拒绝可分类。|方便说下主要是没券、没权限，还是这个规格利润确实不支持吗？|按原因转移。|不争辩原因。|原因只是路由信号。
st069_authority_redirect|权限转接|对方说处理不了。|顺势|请对方指出正确入口。|那这个应该找平台客服确认，还是店铺这边有其它入口？|转正确对象。|不要求当前客服硬处理。|对象要匹配权限。
st070_alternative_close|替代收口|原款失败但有替代。|建设性|把失败变成选择。|原款我就不硬问了，你推荐一个最接近预算的同用途款就行。|进入替代验证。|替代必须同用途。|不降低核心需求。
st071_success_confirm|成功确认|价格达标。|稳、复核|确认最终价和条件。|我确认一下，按这个券后最终到手价能到 49 元以内，对吗？|达标则目标 success。|未验证不写成功。|成功要有证据。
st072_partial_confirm|部分成功确认|没到七折但有最低价。|务实|确认最低边界。|那我理解目前平台内最低就是这个价，对吗？|记录 partial。|不把 partial 写成 success。|状态要分清。
st073_fail_confirm|失败确认|明确无方案。|平静|最后确认无替代。|明白，这款目前没有更低方案，也没有同用途替代，对吗？|确认后 fail。|不要继续重复问价。|失败也要有证据。
st074_block_confirm|风险关闭|出现站外诱导。|礼貌坚定|不参与站外，直接收束。|站外方式我就不参与了，谢谢，我按平台内价格记录。|blocked close。|不讨论站外细节。|站外即关闭。
st075_reopen_if_new_coupon|新券重开|关闭前出现新信息。|灵活|允许因新证据回到核价。|如果后面页面弹出新券，我再按新券重新确认到手价。|新券出现则重开计算。|不能凭可能有券拖延。|必须有新证据。
st076_platform_language|平台客服语言|面对平台客服。|规则、客观|不谈商家态度，只谈规则。|我想确认这个商品当前有没有可叠加的平台补贴或价格保护。|平台答复后核价。|不要求平台替商家降价。|平台只确认规则。
st077_merchant_language|商家客服语言|面对商家客服。|生意、成交|强调平台内成交可能。|如果到手价能接近预算，我今天就在平台内买这款。|商家给方案后验证。|不虚构大单。|成交意向要真实。
st078_after_template|模板回复后|客服复制模板。|具体化|从模板中抓一个点追问。|我看到你说以页面为准，那我想确认购物车这张券是否已经包含在页面价里。|得到具体答案。|不抱怨模板。|模板后只问一处。
st079_after_price_drop|对方已让一步|商家已经降价。|感谢、收尾|感谢让步，只问最后差额。|谢谢你已经帮我看低了，我再确认最后这几元有没有券能补。|有则成功，无则 partial。|不贪多。|让步后更克制。
st080_after_no_coupon|无券后|确认没有券。|转向|不重复问券，改问替代或活动。|如果没有券，那有没有同用途更接近预算的规格或活动时间？|转替代或等待。|不反复问同一张券。|换路径不换压力。
st081_after_wrong_sku|发错商品|商品不一致。|校准|温和指出 SKU。|我看你发的好像是另一款，我问的是这个 10 包链接里的规格。|回正确 SKU。|不指责。|SKU 对齐后再谈价。
st082_after_stockout|无货|没库存。|转移|不谈无货商品价格。|如果这款没货，有没有同用途现货款更接近这个价格？|转现货替代。|无货不判成功。|库存是硬条件。
st083_after_minimum_order|起购限制|多件起购。|算总价|确认起购是否影响预算。|这款需要几件起购？如果按起购数量算，单件到手价是多少？|重算价格。|不忽略起购。|按真实购买量计算。
st084_after_shipping_fee|运费出现|运费拉高总价。|总价意识|确认包邮门槛。|加上运费后总价会变，我想确认有没有包邮券或满包邮门槛。|核总价。|不只算商品价。|运费计入到手价。
st085_after_coupon_threshold|券门槛过高|券看得到用不了。|门槛分析|问低门槛券或组合。|这张券门槛有点高，单买用不了的话，有没有低门槛券？|转低门槛方案。|不为用券乱凑单。|门槛必须可达。
st086_after_platform_denial|平台否认补贴|平台说没有。|接受、关闭|不争平台规则。|明白，没有平台补贴的话，我就按当前最低价记录。|partial 或 switch。|不继续要求补偿。|平台结论记证据。
st087_after_merchant_denial|商家否认空间|商家说到底。|理解、分类|问是否有替代。|理解，那这款如果已经到底，有没有同用途基础款能更接近预算？|替代或关闭。|不说别人都能降。|不引入虚假竞品。
st088_after_conflicting_answers|答案冲突|商家和平台说法不同。|核对|把冲突变成规则确认。|商家那边说店铺券能用，平台这里显示不确定，能帮我确认以下单页为准吗？|以下单页结果为证据。|不让双方互相背锅。|以下单页为准。
st089_after_new_activity|活动出现|页面出现活动。|及时验证|确认活动是否当前可用。|我看到页面新出现活动价，想确认现在下单页是否已经生效。|生效则核价。|不把未开始活动算入价格。|活动需生效。
st090_after_price_change|价格变化|页面价变动。|记录|重新计算，不沿用旧价。|页面价刚变了，我按新页面价重新算一下，麻烦你确认券还能不能用。|更新证据。|不拿旧价判定。|价格变更要刷新。
st091_self_check_before_send|发送前自检|准备发消息前。|冷静|内部检查风险和重复度。|不发送；先检查这句话是否真实、是否站内、是否只问一个问题。|通过再发送。|发现风险就改写。|内部动作不发客服。
st092_emotion_cooldown|情绪降温|自己急躁。|暂停|先等，不写冲动话。|不发送；等 30 秒后只保留一个核心问题。|降温后重写。|不把急躁传给客服。|急躁时先等待。
st093_three_number_rule|三数字规则|价格表达混乱。|简洁|只报三个数字。|原价 70，当前约 52，预算 49，我想确认最后差额有没有平台内优惠。|对方理解差额。|数字超过三个会变乱。|数字要可验证。
st094_one_screen_rule|一屏原则|消息太长。|压缩|让客服一屏读完。|不发送长段；改成商品、当前价、问题三句。|提高回复率。|不堆背景。|消息要短。
st095_evidence_before_claim|先证据后判断|想判成功。|严谨|先找证据再下结论。|不发送；确认购物车或支付前页面是否真的达到目标。|证据齐后关闭。|无证据不成功。|证据优先。
st096_low_value_exit|低价值退出|单目标消耗过多。|整体观|保护 100 目标效率。|如果还没有明确路径，我先记录当前最低价，继续看其它商品。|关闭或切换。|不为单目标过耗。|整体完成率优先。
st097_learning_note|经验沉淀|关闭后复盘。|简短|记录可复用经验。|不发送；记录“差额小转平台有效/无效”等经验。|进入下个目标。|不把偶然成功当规律。|经验要可复用。
st098_kind_last_message|最后礼貌|目标关闭前。|体面|留好关系。|谢谢你帮我确认，我这边清楚了。|关闭目标。|不带讽刺。|结束也要克制。
st099_reentry_with_new_fact|带新事实重入|等待后有新截图或新券。|说明变化|先说新增事实，不重复旧话。|我这边刚看到新券入口，所以重新确认一下它能不能和店铺券叠加。|按新证据继续。|没有新事实不重入。|重入必须有增量。
st100_final_judge_handoff|交给判断核心|沟通动作结束。|清晰交接|整理事实给下一步判断。|不发送；把当前价、证据、对方回复、风险状态交回判断。|Judge 输出三态。|不把目标 outcome 当 Judge Result。|三态严格执行。
"""
    tactics: list[dict[str, str]] = []
    for line in raw.strip().splitlines():
        parts = line.split("|")
        if len(parts) != 9:
            raise ValueError(f"Bad tactic row: {line}")
        tactic_id, name, situation, tone, purpose, say, transition, boundary, guardrail = parts
        tactics.append({
            "id": tactic_id,
            "name": name,
            "situation": situation,
            "tone": tone,
            "purpose": purpose,
            "say": say,
            "transition": transition,
            "boundary": boundary,
            "guardrail": guardrail,
        })
    return tactics


TACTIC_BANK = build_tactics()


def render_long_term() -> str:
    lines = [
        "# Long Term Strategy Graph",
        "",
        "长期策略图把 100 个商品的议价过程拆成 20 个阶段。它不是让执行者机械走完 20 步，而是提供一个能回退、等待、切换、关闭的导航图；每个阶段都说明应该看什么、做什么、怎么说、什么时候离开。",
        "",
    ]
    for stage in DETAILED_STAGES:
        lines.extend([
            f"## {stage['id']} {stage['name']}",
            "",
            stage["core"],
            "",
            f"先看：{stage['read']}",
            "",
            f"要做：{stage['do']}",
            "",
            f"可说：{stage['say']}",
            "",
            f"离开条件：{stage['exit']}",
            "",
            f"回退方式：{stage['fallback']}",
            "",
        ])
    return "\n".join(lines)


def render_short_term() -> str:
    lines = [
        "# Short Term Strategy Graph",
        "",
        "短期策略图不是长期阶段的下级目录。它处理的是当下沟通里的感受、语气、关系、节奏和一句话怎么落地：对方防御时怎么降温，对方模糊时怎么缩小问题，对方愿意帮忙时怎么接住，对方拒绝时怎么体面转移。",
        "",
    ]
    for tactic in TACTIC_BANK:
        lines.extend([
            f"## {tactic['id']} {tactic['name']}",
            "",
            f"适用场景：{tactic['situation']}",
            "",
            f"用途：{tactic['purpose']}",
            "",
            f"语气：{tactic['tone']}",
            "",
            f"可说：{tactic['say']}",
            "",
            f"转移：{tactic['transition']}",
            "",
            f"边界：{tactic['boundary']}",
            "",
            f"守则：{tactic['guardrail']}",
            "",
        ])
    return "\n".join(lines)


def build_edges() -> list[dict[str, object]]:
    edges: list[dict[str, object]] = []
    for index in range(len(DETAILED_STAGES) - 1):
        current = DETAILED_STAGES[index]
        nxt = DETAILED_STAGES[index + 1]
        edges.append({
            "from": current["id"],
            "to": nxt["id"],
            "when": current["exit"],
            "otherwise": current["fallback"],
            "priority": "normal",
        })
    edges.extend([
        {"from": "stage_05_stackability_check", "to": "stage_14_platform_rule_check", "when": "叠加规则来自平台券、补贴、价格保护，商家无法确认。", "otherwise": "继续商家侧最低价探测。", "priority": "high"},
        {"from": "stage_09_merchant_floor_probe", "to": "stage_14_platform_rule_check", "when": "商家见顶且差额小于 10%。", "otherwise": "差额较大时进入方案设计或替代规格。", "priority": "high"},
        {"from": "stage_10_gap_framing", "to": "stage_12_alternative_sku", "when": "差额过大或对方明确利润不支持。", "otherwise": "差额小则继续补齐路径。", "priority": "normal"},
        {"from": "stage_16_wait_control", "to": "stage_17_refusal_classify", "when": "Timer 到期后仍无有效回复或收到拒绝。", "otherwise": "收到有效回复则回到对应事实、券或价格阶段。", "priority": "high"},
        {"from": "stage_17_refusal_classify", "to": "stage_18_target_close_decision", "when": "无合规可行路径、站外诱导或已拿到清晰最低价。", "otherwise": "按拒绝类型回到平台规则、替代规格或证据打包。", "priority": "high"},
    ])
    return edges


def render_transition_index(edges: list[dict[str, object]]) -> str:
    lines = [
        "# Transition Index",
        "",
        "Transition Index 不只记录相邻阶段。它回答三个问题：当前阶段满足什么条件才能前进；证据不足时退回哪里；遇到风险、等待或拒绝时如何强制转移。",
        "",
        "## 常规边",
        "",
    ]
    for edge in edges:
        lines.extend([
            f"### {edge['from']} -> {edge['to']}",
            "",
            f"触发：{edge['when']}",
            "",
            f"不满足时：{edge['otherwise']}",
            "",
            f"优先级：{edge['priority']}",
            "",
        ])
    lines.extend([
        "## 强制边",
        "",
        "- 出现站外联系方式、私下返现、私下转账：立即进入 stage_18_target_close_decision，目标级 outcome 记 blocked_close，Judge Result 仍按三态判断。",
        "- 执行动作可能触发支付、下单、投诉威胁、虚构身份：阻断动作，进入 stage_18_target_close_decision，目标级 outcome 记 risk_aborted。",
        "- 单目标等待超过 1800 秒：进入 stage_17_refusal_classify，再由 Judge Core 判断继续当前 Episode 或关闭目标。",
        "- 单个目标关闭后，本批还有未关闭目标：Judge Result 仍是 Continuing Episode，转回 stage_01_batch_intake 选择下一个目标。",
        "- 本批 10 个目标全部关闭且不是 EP10：Judge Result 是 Next Episode。",
        "- EP10 全部关闭或系统性风险终止：Judge Result 是 Run Plan Close。",
    ])
    return "\n".join(lines)


def episode_doc(episode_id: str, category: str, rows: list[dict[str, object]]) -> str:
    lines = [
        f"# {episode_id} Trajectory Template",
        "",
        f"品类焦点：{category}",
        "",
        "本文件只给真实运行后的填写格式，不写未发生的结果。",
        "",
        "## 目标登记",
        "",
        "| 商家 | 商品 | 原价 | 七折目标 | 当前状态 | 证据位置 | 目标级 outcome | Judge Result |",
        "|---|---|---:|---:|---|---|---|---|",
    ]
    for row in rows:
        lines.append(f"| {row['merchant_id']} | {row['product']} | {row['original_price']} | {row['target_price_70pct']} | not_started | 待填 | 待填 | 待填三态之一 |")
    lines.extend([
        "",
        "## 单目标格式",
        "",
        "| 字段 | 填写内容 |",
        "|---|---|",
        "| 商品事实 | 规格、数量、库存、原价口径 |",
        "| 优惠结构 | 页面券、店铺券、平台券、活动价、叠加关系 |",
        "| 沟通轨迹 | 每轮动作、具体说法、对方回应、新证据 |",
        "| 操作轨迹 | 收藏、加购、店内浏览、截图、平台客服确认 |",
        "| 价格计算 | 原价、目标价、当前价、差额、最终可验证路径 |",
        "| 关闭信息 | 目标级 outcome、Judge Result、关闭理由 |",
    ])
    return "\n".join(lines)


def make_trajectory() -> None:
    for ep, cat, _ in CATEGORIES:
        rows = [row for row in TARGETS if row["episode_id"] == ep]
        write(f"TrajectoryPackage/{ep}.md", episode_doc(ep, cat, rows))

    package = {
        "schema_version": 5,
        "package_type": "trajectory_template",
        "judge_result_enum": ["Continuing Episode", "Next Episode", "Run Plan Close"],
        "target_level_outcome_enum": ["success_close", "partial_success_close", "fail_close", "blocked_close", "risk_aborted"],
        "episode_files": [f"TrajectoryPackage/{ep}.md" for ep, _, _ in CATEGORIES],
        "required_columns": ["target_id", "product", "original_price", "target_price", "evidence", "target_outcome", "judge_result"],
    }
    dump("TrajectoryPackage/TrajectoryPackage.json", package)
    write("TrajectoryPackage/TrajectoryPackage.md", """# Trajectory Package Template

这里不放实际结果，只规定关闭整个 Run Plan 时必须交付什么格式。

## 总格式

| 模块 | 必填内容 |
|---|---|
| Run Plan | 任务编号、开始时间、关闭时间、最终 Judge Result |
| Episode | EP01 到 EP10 的文件路径和批次状态 |
| Target | 100 个目标的商品、原价、七折目标、最终可验证价格 |
| Dialogue | 每轮具体说法、对方回应、截图或页面证据位置 |
| Operation | 收藏、加购、浏览同店商品、发截图、转平台客服等动作 |
| Closure | 目标级 outcome、三态 Judge Result、关闭理由 |

## Episode 文件

""" + "\n".join(f"- `TrajectoryPackage/{ep}.md`：{cat}" for ep, cat, _ in CATEGORIES))


def make_core_docs() -> None:
    write("README.md", """# Agentic RL Project Structure

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
- `TrajectoryPackage/`：真实运行结束后的轨迹包格式。""")

    overview = simple_spec(
        "SCENARIO-OVERVIEW-PDD-100",
        "Scenario Overview",
        "拼多多 100 商品 / 100 商家议价任务总览",
        "overview",
        ["系统在平台内处理 100 个商品目标。成功只认可验证到手价，不认口头承诺、站外补差或未发生结果。"],
        [
            {"title": "任务结构", "bullets": ["10 个 Episode，每批 10 个目标", "每次只深度处理一个 active_target", "单目标关闭后仍回到本批继续，直到本批 10 个目标都有 outcome"]},
            {"title": "成功定义", "bullets": ["confirmed_payable_price <= original_price * 0.7", "优惠路径能在平台内复核", "风险违规执行次数为 0"]},
        ],
        {"scenario_id": "PDD-100SKU-100MERCHANT-70PCT", "total_targets": 100, "episode_count": 10, "targets_per_episode": 10},
    )
    write("ScenarioOverview.md", render_doc(overview))
    dump("ScenarioOverview.json", overview)


def make_genome_docs() -> None:
    dna = simple_spec(
        "CG-PDD-BARGAIN-V5",
        "Child DNA",
        "拼多多站内议价型核心基因",
        "child_genome",
        ["DNA 不是话术库，而是这个 Child 的人格底层：它像一个克制、会算账、懂边界、又愿意给对方台阶的买家。"],
        [
            {"title": "人物小传", "paragraphs": ["这个 Child 的默认身份不是强势采购，也不是随便薅羊毛的人，而是一个认真比较、预算清楚、愿意今天在平台内成交的普通买家。它会把对方当成有权限边界的人来沟通：客服能解释规则，商家能给店铺方案，平台能确认平台补贴。它不幻想一句话砍到七折，而是把七折拆成事实、券、差额、替代规格和等待。"]},
            {"title": "文化背景", "paragraphs": ["它继承的是平台电商里的轻协商文化：礼貌、快、证据清楚、不给对方难堪。它知道低客单商品利润薄，硬压常常不如问券、问组合、问替代款、问活动时间。它也知道客服常被模板约束，所以每轮只问一个可回答的问题。"]},
            {"title": "稳定原则", "bullets": ["先确认事实，再谈价格", "先问优惠结构，再问目标价", "给对方选择，不给对方命令", "只使用真实购买意向信号", "所有成功都必须能在平台内复核", "目标级 outcome 不能冒充 Judge Result"]},
            {"title": "行为气质", "bullets": ["温和但不软", "数字清楚但不咄咄逼人", "等待时能克制", "失败时体面退出", "风险出现时立刻收口"]},
        ],
        {"persona": "warm_firm_budget_buyer", "judge_result_enum": ["Continuing Episode", "Next Episode", "Run Plan Close"]},
    )
    memory = simple_spec(
        "EM-PDD-BARGAIN-V5",
        "Experience Memory",
        "可继承的议价经验",
        "child_genome",
        ["Experience Memory 保存能复用的经验，不保存偶然成功的幻觉。它让 Child 下次更快识别对手、差额和转移路径。"],
        [
            {"title": "价格经验", "bullets": ["差额小于 10% 时，平台补贴、店铺券和轻组合最值得尝试", "差额大于 20% 时，原款硬磨通常低效，应更早问替代规格", "低客单标品更依赖券和活动，高客单非标品更依赖方案设计", "到手价必须以购物车或支付前页面为准"]},
            {"title": "沟通经验", "bullets": ["第一句越具体，对方越容易脱离模板", "收藏、加购、浏览同店商品是购买意向，不是交换筹码", "截图只用于解释自己看到的价格，不用于压迫", "对方拒绝后先分类，不立刻重复请求", "客服说没权限时，下一步通常不是再求一次，而是问谁能确认规则"]},
            {"title": "转移经验", "bullets": ["商家见顶且差额小，转平台客服", "规则不清，转平台客服", "利润不支持，转替代款", "机器人循环，缩小问题或换入口", "站外诱导，关闭目标"]},
        ],
        {"experience_cards": ["gap_size_routing", "one_question_per_round", "real_intent_signal", "refusal_classification", "platform_rule_escalation"]},
    )
    for path, spec in [("ChildGenome/DNA", dna), ("ChildGenome/ExperienceMemory", memory)]:
        write(f"{path}.md", render_doc(spec))
        dump(f"{path}.json", spec)

    edges = build_edges()
    long_spec = {"meta": {"title": "Long Term Strategy Graph", "kind": "strategy_playbook", "version": 5}, "nodes": DETAILED_STAGES}
    short_spec = {
        "meta": {"title": "Short Term Strategy Graph", "kind": "short_term_emotional_strategy", "version": 6},
        "design": {
            "independent_from_long_term": True,
            "primary_axis": "conversation_situation_and_emotional_tone",
            "stable_fields": ["id", "name", "situation", "tone", "purpose", "say", "transition", "boundary", "guardrail"],
        },
        "tactics": TACTIC_BANK,
    }
    transition_spec = {"meta": {"title": "Transition Index", "kind": "strategy_playbook", "version": 5}, "edges": edges, "forced_edges": ["off_platform", "risk_action", "timer_expired", "episode_done", "run_done"]}
    write("ChildGenome/StrategyPlayBook/LongTermStrategyGraph.md", render_long_term())
    write("ChildGenome/StrategyPlayBook/ShortTermStrategyGraph.md", render_short_term())
    write("ChildGenome/StrategyPlayBook/TransitionIndex.md", render_transition_index(edges))
    dump("ChildGenome/StrategyPlayBook/LongTermStrategyGraph.json", long_spec)
    dump("ChildGenome/StrategyPlayBook/ShortTermStrategyGraph.json", short_spec)
    dump("ChildGenome/StrategyPlayBook/TransitionIndex.json", transition_spec)


def make_signals() -> None:
    message = "你好，这款厨房湿巾我已经确认了页面券和商家优惠：原价 70 元，目前商家侧大概能到 52 元，离 49 元左右的预算还差一点。想请你帮我看一下，平台这边是否还有可叠加的客服补偿券、活动补贴或价格保护规则？如果有，请帮我确认金额、使用条件和是否能在当前商品页面直接使用。"
    execution_brief = {
        "schema_version": 5,
        "signal_type": "Execution Brief",
        "brief_id": "EB-EP03-M021-R4",
        "episode_id": "EP03",
        "active_target_id": "M021",
        "round": 4,
        "execution_command": {"command_id": "EC-EP03-M021-R4", "channel": "拼多多平台客服会话", "action": "send_message", "message": message},
        "execution_timer": {"timer_id": "ET-EP03-M021-R4", "wait_seconds": "300", "max_wait_seconds": "1800", "early_resume_conditions": "平台客服回复；商家同步回复新的优惠信息"},
        "soft_strategy": {"tone": "温和、具体、请对方帮忙核规则", "relationship_goal": "让平台客服愿意查补贴，而不是觉得用户在施压"},
        "hard_execution": {"must_send_once": True, "must_wait_seconds": 300, "must_not_repeat": True, "must_collect": ["补贴金额", "使用条件", "叠加关系", "回复摘要"]},
        "judge_result_enum": ["Continuing Episode", "Next Episode", "Run Plan Close"],
    }
    signals = {
        "ExecutionBrief": execution_brief,
        "ExecutionCommand": {"schema_version": 5, "signal_type": "Execution Command", **execution_brief["execution_command"]},
        "ExecutionTimer": {"schema_version": 5, "signal_type": "Execution Timer", **execution_brief["execution_timer"]},
        "ExecutionResult": {"schema_version": 5, "signal_type": "Execution Result", "execution_status": "completed", "wait_status": "waiting_for_reply", "risk_status": "safe"},
        "OpponentState": {"schema_version": 5, "signal_type": "Opponent State", "episode_id": "EP03", "active_target_id": "M021", "primary_opponent": "平台客服", "secondary_opponent": "商家客服", "risk_signals": []},
        "JudgeResult": {"schema_version": 5, "signal_type": "Judge Result", "allowed_decisions": ["Continuing Episode", "Next Episode", "Run Plan Close"], "decision": "Continuing Episode", "reason": "消息已发出且仍在等待窗口内。"},
        "HistoryContext": {"schema_version": 5, "signal_type": "History Context", "episode_id": "EP03", "active_target_id": "M021"},
    }
    for name, data in signals.items():
        dump(f"Signals/{name}.json", data)
    write("Signals/ExecutionBrief.md", f"""# Execution Brief

本轮编号 EB-EP03-M021-R4，目标是 EP03/M021，第 4 轮。商品是厨房湿巾 10 包，原价 70 元，七折目标是 49 元；商家侧上一轮已经把当前最好到手价压到约 52 元，只差 3 元。继续压商家容易让对话僵住，所以这一轮进入平台规则确认：把购物车当前价格说清楚，请平台核对是否有可叠加补贴、活动补贴或价格保护；如果客服看不懂差额，再补当前商品页或领券页截图；发出后等待，不重复追问。

软的一面：这句话要像“请你帮我核一下规则”，不要像“你必须给我补贴”。语气要温和、数字要具体、目标要单一，只让平台客服查三件事：有没有补贴、能不能叠加、条件是什么。主对手是平台客服，次对手是商家客服。商家客服目前配合但利润空间已接近尽头，平台客服更适合确认可叠加券、活动规则和价格保护。

硬的一面：只能发送一次，不能说已经下单，不能请求站外返现，不能重复催促，不能触发支付。发送后必须登记 Timer，回来时必须带回补贴金额、使用条件、叠加关系和回复摘要。

消息编号 EC-EP03-M021-R4，发送到 拼多多平台客服会话，动作是 send_message。正文是：「{message}」

这条消息发出后等待 300 秒，最长等待 1800 秒。只要平台客服回复或商家同步回复新的优惠信息，就提前恢复。超时后回到 Judge Core，decision 仍只能是三态之一。

回来时必须带回：是否存在补贴、补贴金额、使用条件、能否与当前店铺券叠加、客服回复摘要。平台确认补贴就进入到手价确认；明确没有补贴就进入等待、替代款或目标关闭判断；出现站外要求或其它风险就进入目标关闭判断。

Judge Result 只允许给出 Continuing Episode、Next Episode、Run Plan Close。目标级 success_close、partial_success_close、blocked_close 等只能作为证据字段，不能写成 Judge Result。""")
    write("Signals/HistoryContext.md", """# History Context

## 当前卡片

| 项目 | 状态 |
|---|---|
| Episode | EP03 |
| Active Target | M021 |
| 商品 | 厨房湿巾 10 包 |
| 原价 / 七折目标 | 70 元 / 49 元 |
| 当前最好到手价 | 约 52 元 |
| 当前差额 | 约 3 元 |
| 当前阶段 | 平台规则确认 |
| Judge Result | Continuing Episode |

## 已发生

| 轮次 | 结果 |
|---:|---|
| 1 | 确认规格和库存 |
| 2 | 找到店铺券，无低配款 |
| 3 | 商家侧最低约 52 元 |
| 4 | 已向平台客服询问补贴，等待回复 |

## 下一步只看三件事

- 平台是否有可叠加补贴。
- 补贴后是否能到 49 元左右。
- 若没有补贴，是否切替代款或关闭 M021。""")
    write("Signals/ThinkLog.md", """# Think Log

EP03/M021 当前差额约 3 元。继续压商家收益低，平台规则仍未确认，所以本轮问平台补贴并等待。

Judge Result 只能是 Continuing Episode、Next Episode、Run Plan Close。""")
    write("Signals/ActLog.md", """# Act Log

| 动作 | 状态 |
|---|---|
| 打开平台客服会话 | done |
| 发送补贴确认消息 | done |
| 注册 300 秒等待 | done |
| 风险事件 | none |""")


def make_environment_docs() -> None:
    mission = simple_spec(
        "MS-PDD-70PCT-V5",
        "Mission Spec",
        "本次任务的目标、成功标准与边界",
        "environment_setting",
        ["任务不是“强行砍到七折”，而是在平台内为 100 个商品寻找可验证的七折成交路径。每个目标都要留下价格、证据、沟通和关闭状态。"],
        [
            {"title": "目标", "bullets": ["处理 100 个商品，每个商品对应一个商家目标", "每个目标争取 confirmed_payable_price <= original_price * 0.7", "每个目标都必须形成目标级 outcome", "整个任务只在平台内沟通和验证"]},
            {"title": "成功路径", "bullets": ["商家直降", "店铺券和平台券叠加", "平台活动或补贴", "价格保护规则", "同用途替代规格", "组合装或无赠品版"]},
            {"title": "不做", "bullets": ["不自动下单", "不请求站外返现", "不虚构身份、订单或采购量", "不使用威胁、投诉、刷屏换价"]},
        ],
        {"objective": "100 targets at or below 70 percent payable price", "success_rule": "confirmed_payable_price <= original_price * 0.7"},
    )
    risk = simple_spec(
        "RPOL-PDD-COMPLIANCE-V5",
        "Risk Policy",
        "运行时必须阻断、等待或关闭的风险边界",
        "environment_setting",
        ["Risk Policy 不是惩罚清单，而是执行刹车。它告诉系统：哪些话不能发，哪些动作要先停，哪些情况必须关闭目标。读它时先看“场景”，再看“系统动作”。"],
        [
            {"title": "必须立刻阻断并关闭目标", "bullets": ["对方要求加微信、电话、其它站外联系方式", "对方要求私下返现、私下转账、收货后补差价", "为了拿优惠而需要绕开平台规则", "继续沟通会要求暴露身份证、手机号、住址以外的敏感信息"]},
            {"title": "必须阻断但不一定关闭目标", "bullets": ["消息里声称已经付款、已经下单、采购很多件，但这些并未发生", "消息里暗示差评、投诉、举报、曝光来换价格", "动作会触发支付、下单、提交订单或确认收货", "截图里包含账号、地址、手机号、订单号等不该发送的信息"]},
            {"title": "必须等待或降频", "bullets": ["同一窗口同义消息已经发过 2 次", "对方没有回复但还没到 300 秒", "情绪开始急躁，下一句话只是在重复催促", "机器人循环时，先把问题缩成一个可回答的小点"]},
            {"title": "允许继续的情况", "bullets": ["询问平台内券、活动、补贴、价格保护", "询问同用途替代规格、组合装、无赠品版", "发送当前商品页、领券页、购物车价截图来澄清价格", "如实说明已收藏、已加购、已浏览同店商品"]},
            {"title": "程序可读动作", "bullets": ["off_platform_contact -> block_and_close", "private_cashback -> block_and_close", "fabricated_order_or_identity -> block", "threat_or_harassment -> block", "unauthorized_payment -> block", "repeat_spam -> wait", "sensitive_info_exposure -> block"]},
        ],
        {"risk_rules": [
            {"id": "RP-01", "trigger": "off_platform_contact", "action": "block_and_close"},
            {"id": "RP-02", "trigger": "private_cashback", "action": "block_and_close"},
            {"id": "RP-03", "trigger": "fabricated_order_or_identity", "action": "block"},
            {"id": "RP-04", "trigger": "threat_or_harassment", "action": "block"},
            {"id": "RP-05", "trigger": "unauthorized_payment", "action": "block"},
            {"id": "RP-06", "trigger": "repeat_spam", "action": "wait"},
            {"id": "RP-07", "trigger": "sensitive_info_exposure", "action": "block"},
        ], "limits": {"same_window_repeat_limit": 2, "initial_wait_seconds": 300, "max_wait_seconds_per_target": 1800}},
    )
    run_plan = simple_spec(
        "RP-PDD-100SKU-10EP-V5",
        "Run Plan",
        "100 商品任务的 Episode 组织计划",
        "environment_setting",
        ["Run Plan 把 100 个目标切成 10 个 Episode。Episode 是批次容器，不改变单目标逐个判断的原则。"],
        [{"title": "批次", "bullets": [f"{ep}：{cat}，处理 {((i - 1) * 10 + 1):03d}-{i * 10:03d} 号商家" for i, (ep, cat, _) in enumerate(CATEGORIES, start=1)]}],
        {"episode_count": 10, "targets_per_episode": 10, "total_targets": 100},
    )
    category_playbooks = [
        ("厨房小件", ["问材质、容量、尺寸、是否食品接触、是否有套装", "替代方向：少赠品版、单件装、组合装、旧包装", "重点避坑：图片同款但容量不同、赠品拉高原价、颜色或尺寸影响价格"]),
        ("收纳整理", ["问尺寸、承重、材质厚度、是否可叠放", "替代方向：少件数、不同尺寸、无盖款、同店组合券", "重点避坑：大图显大但尺寸小、套装数量不一致、运费改变到手价"]),
        ("家清耗材", ["问包装数量、单片规格、是否补充装、保质期", "替代方向：补充装、大包装、无香型、组合装、活动周期", "重点避坑：抽数不同、纸张克重不同、赠品不算核心价值"]),
        ("宠物用品", ["问适配体重、材质安全、味道、消耗周期", "替代方向：大包装、补充装、替换芯、同用途基础款", "重点避坑：猫狗规格不同、滤芯型号不匹配、低价款数量缩水"]),
        ("母婴小件", ["先问安全材质、适用年龄、尺寸、是否有检测说明", "替代方向：简装版、少件装、同材质基础款", "重点避坑：不能为了低价牺牲安全和适配"]),
        ("服饰与袜裤", ["问尺码、面料、厚薄、颜色、是否断码", "替代方向：断码色、基础色、多双装、旧包装", "重点避坑：尺码偏差、面料克重、季节厚薄影响价格"]),
        ("数码配件", ["问功率、接口、长度、协议、兼容型号", "替代方向：短线、低功率、单件装、无包装版", "重点避坑：快充协议不一致、线长不同、套装数量不同"]),
        ("美妆个护", ["问规格、保质期、肤质适配、是否正装或小样", "替代方向：小规格、组合券、同功效基础款", "重点避坑：临期、规格缩水、赠品混入总价"]),
        ("零食饮品", ["问净含量、保质期、口味组合、发货时效", "替代方向：临近活动、组合口味、大包装、少件装", "重点避坑：克重不同、口味不同、临期不可接受"]),
        ("小家居用品", ["问尺寸、材质、安装方式、是否含配件", "替代方向：无赠品版、基础款、同店组合", "重点避坑：尺寸不适配、配件另购、图片氛围误导实际规格"]),
        ("纸品湿巾", ["问抽数、张数、单张尺寸、是否加厚", "替代方向：补充装、箱装、无盖款", "重点避坑：包数多但单包抽数少"]),
        ("清洁剂", ["问容量、适用材质、是否浓缩、是否有替换装", "替代方向：替换装、多瓶装、无喷头版", "重点避坑：适用场景不对导致无效购买"]),
        ("充电线材", ["问接口、长度、电流、是否支持数据传输", "替代方向：短线、多条装、普通充电版", "重点避坑：只充电不传输、快充不兼容"]),
        ("袜子内衣", ["问面料、尺码范围、厚薄、腰口弹性", "替代方向：基础色、多件装、断码优惠", "重点避坑：均码不合适、面料比例模糊"]),
        ("食品囤货", ["问生产日期、保质期、单件克重、发货仓", "替代方向：大包装、组合口味、活动预告", "重点避坑：临期、克重不同、运费门槛"]),
        ("替换耗材", ["问型号、兼容范围、几只装、安装方式", "替代方向：多只装、基础包装、同型号不同品牌", "重点避坑：型号差一个字母就不兼容"]),
    ]
    prior = simple_spec(
        "PK-PDD-BARGAIN-V5",
        "Prior Knowledge",
        "运行前可用的先验经验",
        "environment_setting",
        ["先验知识用于让系统少走弯路：知道平台价格由哪些部分组成，知道商家和平台各自能解决什么，也知道哪些动作只是购买意向，不能被包装成筹码。"],
        [
            {"title": "价格结构", "bullets": ["到手价通常由页面价、店铺券、平台券、红包、活动价、满减、支付前优惠共同构成", "商家往往能解释店铺券和推荐替代款，但不能决定平台补贴", "平台客服更适合确认平台券、活动规则、价格保护和补贴条件"]},
            {"title": "品类经验", "items": [{"title": name, "bullets": bullets} for name, bullets in category_playbooks]},
        ],
        {"platform_boundary": "in_platform_only", "category_playbooks": [{"category": name, "rules": bullets} for name, bullets in category_playbooks]},
    )
    for path, spec in [("MissionSpec", mission), ("RiskPolicy", risk), ("RunPlan", run_plan), ("PriorKnowledge", prior)]:
        write(f"EnvironmentSettings/{path}.md", render_doc(spec))
        dump(f"EnvironmentSettings/{path}.json", spec)
    dump("EnvironmentSettings/MissionSpec.json", {
        "meta": {"id": "MS-PDD-70PCT-V5", "title": "Mission Spec", "version": 6},
        "objective": "100 个商品分别争取七折及以下平台内可验证到手价",
        "success_rule": "confirmed_payable_price <= original_price * 0.7",
        "required_target_outcome": True,
        "allowed_success_paths": ["merchant_discount", "store_coupon", "platform_coupon", "platform_activity", "price_protection", "alternative_sku", "bundle_or_no_gift_version"],
        "forbidden_paths": ["auto_order", "off_platform_cashback", "fabricated_identity_or_order", "threat_or_spam"],
    })
    dump("EnvironmentSettings/RiskPolicy.json", {
        "meta": {"id": "RPOL-PDD-COMPLIANCE-V5", "title": "Risk Policy", "version": 6},
        "risk_rules": risk["runtime_spec"]["risk_rules"],
        "limits": risk["runtime_spec"]["limits"],
        "action_meaning": {
            "block_and_close": "阻断当前动作，并把目标送入关闭判断",
            "block": "阻断当前动作，要求重新生成合规动作",
            "wait": "不继续发送，进入等待或降频",
        },
    })
    dump("EnvironmentSettings/PriorKnowledge.json", {
        "meta": {"id": "PK-PDD-BARGAIN-V5", "title": "Prior Knowledge", "version": 6},
        "platform_boundary": "in_platform_only",
        "price_components": ["page_price", "store_coupon", "platform_coupon", "red_packet", "activity_price", "full_reduction", "pre_payment_discount"],
        "category_playbooks": [{"category": name, "rules": bullets} for name, bullets in category_playbooks],
    })
    closure_rules = [
        ("消息已发出且仍在 300 秒初次等待窗内", "Continuing Episode"),
        ("客服已回复但补贴金额、使用条件或叠加关系仍缺一项", "Continuing Episode"),
        ("当前目标价格未达七折，但仍存在未验证的平台券、店铺券、替代规格或活动时间", "Continuing Episode"),
        ("当前目标已达七折但缺少购物车价、支付前页面或客服确认等证据", "Continuing Episode"),
        ("当前目标已关闭但本批还有未关闭目标", "Continuing Episode"),
        ("当前目标无回复超过 1800 秒，但本批仍有其它目标可处理", "Continuing Episode"),
        ("当前目标出现拒绝，需要先分类为无权限、无利润、无活动、无替代或风险", "Continuing Episode"),
        ("当前批 10 个目标全部都有目标级 outcome，且后续 Episode 仍存在", "Next Episode"),
        ("当前批 10 个目标全部关闭，但还有至少一个目标证据字段缺失", "Continuing Episode"),
        ("当前批 10 个目标全部关闭且证据字段完整，且当前批不是 EP10", "Next Episode"),
        ("EP10 的 10 个目标全部都有目标级 outcome 且证据字段完整", "Run Plan Close"),
        ("出现站外返现、私下转账、虚构身份、威胁投诉等系统性风险并需要终止整个任务", "Run Plan Close"),
        ("执行工具持续异常导致无法继续获取页面、客服或价格证据，且重试后仍不可恢复", "Run Plan Close"),
    ]
    closure_outcomes = [
        ("success_close", "平台内可验证到手价达到七折或以下，且证据字段完整"),
        ("partial_success_close", "没到七折，但得到清晰最低价、活动时间或可复用路径"),
        ("fail_close", "明确拒绝，且无平台券、店铺券、替代规格、活动等待等后续路径"),
        ("blocked_close", "对方要求站外、私下补差、私下返现，或工具无法继续处理单目标"),
        ("risk_aborted", "继续执行会触碰虚构、威胁、骚扰、自动下单、敏感信息等风险红线"),
    ]
    write("EnvironmentSettings/ClosurePolicy.md", """# Closure Policy

Closure Policy 用来判断每轮回来后该继续当前 Episode、进入下一个 Episode，还是关闭整个 Run Plan。目标级 outcome 只记录单个目标状态，不能替代 Judge Result。

Judge Result 只允许给出 Continuing Episode、Next Episode、Run Plan Close。success_close、partial_success_close、fail_close、blocked_close、risk_aborted 都只是目标级 outcome。

## 判定表

| 条件 | Judge Result |
|---|---|
""" + "\n".join(f"| {condition} | {result} |" for condition, result in closure_rules) + """

## 目标级 outcome

| outcome | 含义 |
|---|---|
""" + "\n".join(f"| {outcome} | {meaning} |" for outcome, meaning in closure_outcomes))
    dump("EnvironmentSettings/ClosurePolicy.json", {
        "schema_version": 6,
        "judge_result_enum": ["Continuing Episode", "Next Episode", "Run Plan Close"],
        "target_outcome_enum": ["success_close", "partial_success_close", "fail_close", "blocked_close", "risk_aborted"],
        "judge_result_rules": [{"condition": condition, "judge_result": result} for condition, result in closure_rules],
        "target_outcome_rules": [{"outcome": outcome, "condition": meaning} for outcome, meaning in closure_outcomes],
    })


def main() -> None:
    make_core_docs()
    make_environment_docs()
    make_genome_docs()
    make_signals()
    make_trajectory()


if __name__ == "__main__":
    main()
