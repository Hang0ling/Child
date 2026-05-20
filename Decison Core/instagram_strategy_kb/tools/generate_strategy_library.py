from __future__ import annotations

import argparse
import csv
import json
import re
from collections import defaultdict
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GENERATED_ON = "2026-05-20"

STAGES = {
    "S1": "陌生人画像与边界策略",
    "S2": "主页可信与安全感策略",
    "S3": "内容吸引与共同兴趣策略",
    "S4": "公共互动与破冰策略",
    "S5": "私信熟悉与倾听策略",
    "S6": "小资源互助策略",
    "S7": "长期朋友关系维护策略",
    "S8": "关系复盘与迭代策略",
    "S9": "学习提升策略",
}

GOALS = [
    "发现合适陌生人",
    "提升主页可信感",
    "降低陌生防备",
    "开启自然互动",
    "增加 Story 回复",
    "开启私信对话",
    "提供小帮助",
    "提高后续对话率",
    "建立长期朋友关系",
    "形成可信专业感",
]

FORMATS = [
    "Reels 策略",
    "Carousel 策略",
    "Story 策略",
    "Live 策略",
    "Highlights 策略",
    "Bio 策略",
    "评论策略",
    "私信策略",
    "资源互助策略",
    "社群/圈层策略",
]

PSYCHOLOGY = [
    "降低陌生感",
    "降低怀疑感",
    "提升真实感",
    "提升专业感",
    "提升被理解感",
    "提升参与感",
    "提升互惠感",
    "提升安全感",
    "提升持续关注理由",
]

RELATIONSHIP_MISSION = "用于在社交平台上认识合适的陌生人，通过公开互动、真诚倾听和小范围互助，逐步成为朋友并赢得长期信任。"

SAFETY_BOUNDARY = "必须真实透明、尊重对方选择；不伪装身份、不套取隐私、不制造虚假亲密或焦虑，对方冷淡、拒绝或沉默时停止推进。"

GOAL_REFRAME = {
    "增加被看见": "发现合适陌生人",
    "提升主页信任感": "提升主页可信感",
    "提升关注转化率": "降低陌生防备",
    "增加评论互动": "开启自然互动",
    "增加 Story 回复": "增加 Story 回复",
    "开启私信对话": "开启私信对话",
    "提高福利领取率": "提供小帮助",
    "提高后续对话率": "提高后续对话率",
    "建立长期关系": "建立长期朋友关系",
    "形成专家感": "形成可信专业感",
}

FORMAT_REFRAME = {
    "Reels 策略": "Reels 策略",
    "Carousel 策略": "Carousel 策略",
    "Story 策略": "Story 策略",
    "Live 策略": "Live 策略",
    "Highlights 策略": "Highlights 策略",
    "Bio 策略": "Bio 策略",
    "评论策略": "评论策略",
    "私信策略": "私信策略",
    "福利策略": "资源互助策略",
    "社群策略": "社群/圈层策略",
}

TEXT_REPLACEMENTS = [
    ("小众服务对象", "小众共同兴趣人群"),
    ("用户名", "账号名称"),
    ("用户路径", "关系路径"),
    ("用户旅程", "关系旅程"),
    ("产品/服务", "内容或服务"),
    ("我服务谁", "我想认识谁、能帮谁"),
    ("服务谁", "想认识谁、能帮谁"),
    ("帮他们解决什么", "能给他们什么具体帮助"),
    ("正确的人留下", "合适的人愿意继续互动"),
    ("提升关注转化率", "降低陌生防备"),
    ("提高福利领取率", "提供小帮助"),
    ("建立长期关系", "建立长期朋友关系"),
    ("形成专家感", "形成可信专业感"),
    ("主页信任感", "主页可信感"),
    ("用户生成内容", "对方自愿分享内容"),
    ("用户原话", "对方原话"),
    ("用户画像", "想认识的人画像"),
    ("目标用户", "想认识的人"),
    ("新粉", "新认识的人"),
    ("老粉", "长期互动对象"),
    ("粉丝", "互动对象"),
    ("客户服务", "关系回应"),
    ("客服", "关系回应"),
    ("购买或行动", "继续互动"),
    ("购买", "继续互动"),
    ("成交", "关系推进"),
    ("转化", "关系推进"),
    ("销售", "推销式表达"),
    ("福利", "小资源"),
    ("lead magnet", "小资源"),
    ("资料", "小资源"),
    ("报价", "进一步交流"),
    ("价格", "投入边界"),
    ("报名", "进一步交流"),
    ("预约", "进一步交流"),
    ("咨询", "进一步交流"),
    ("付费", "深入交流"),
    ("业务结果", "关系结果"),
    ("业务", "关系"),
    ("产品", "内容或服务"),
    ("服务对象", "想认识和能帮助的人"),
    ("客户", "对方"),
    ("用户", "对方"),
    ("品牌", "账号"),
]

STAGE_RELATIONSHIP_INTRO = {
    "S1": "这条策略先帮你判断哪些陌生人值得认识、从什么共同语境开始互动。",
    "S2": "陌生人点进主页时，会先判断你是否真实、安全、值得回应。",
    "S3": "内容不是单向表演，而是让有共同兴趣的人看见你、愿意回应你的入口。",
    "S4": "公共互动的重点是在已有语境里贡献价值，让对方先觉得你具体、礼貌、可信。",
    "S5": "私信是更高亲密度空间，必须先让对方有选择权和安全感。",
    "S6": "小资源和小帮助用于降低对方行动负担，不用于制造亏欠感。",
    "S7": "朋友关系需要节奏、记忆和持续关心，不能只在需要回应时出现。",
    "S8": "关系复盘要看互动质量、信任信号和边界是否被尊重，而不只看数量。",
    "S9": "学习提升要服务更真诚、更稳定的关系能力，而不是堆技巧。",
}

SOURCES = {
    "META_BLUEPRINT": {
        "name": "Meta Small Business Academy: Instagram Marketing",
        "group": "官方平台资料",
        "url": "https://www.facebookblueprint.com/student/collection/507784-instagram-marketing",
        "use_for": "Instagram 官方营销基础、账号建设、广告入门",
        "distilled": "先建立线上存在感，再用内容、直播和广告工具触达新客户。",
    },
    "INSTAGRAM_BEST_PRACTICES": {
        "name": "Instagram Best Practices",
        "group": "官方平台资料",
        "url": "https://about.fb.com/news/2024/10/best-practices-education-hub-creators-instagram/",
        "use_for": "Instagram 创作者官方建议、内容、触达、互动、变现",
        "distilled": "内容创作、互动、触达、变现和规则都需要看专业面板里的个性化反馈。",
    },
    "META_SOCIAL_CERT": {
        "name": "Meta Social Media Marketing Professional Certificate",
        "group": "官方平台资料",
        "url": "https://www.coursera.org/professional-certificates/facebook-social-media-marketing",
        "use_for": "系统学习社媒营销、内容、广告、数据",
        "distilled": "用课程化路径补齐社媒策略、广告、数据和职业化运营能力。",
    },
    "HUBSPOT_INSTAGRAM": {
        "name": "HubSpot Instagram Marketing Guide",
        "group": "Instagram 实战资料",
        "url": "https://www.hubspot.com/instagram-marketing",
        "use_for": "Instagram 策略、内容类型、增长、分析",
        "distilled": "品牌账号要用真实、优质、多样化内容呈现视觉身份，少做生硬广告。",
    },
    "BUFFER_INSTAGRAM": {
        "name": "Buffer Instagram Marketing Guide",
        "group": "Instagram 实战资料",
        "url": "https://buffer.com/resources/instagram-marketing/",
        "use_for": "账号策略、内容规划、增长技巧",
        "distilled": "先选对账号类型和基础设置，再用日历和排程提高持续发布能力。",
    },
    "HOOTSUITE_INSTAGRAM_RESOURCES": {
        "name": "Hootsuite Instagram Resources",
        "group": "Instagram 实战资料",
        "url": "https://blog.hootsuite.com/network/instagram/",
        "use_for": "Instagram 算法、Reels、Stories、数据、工具",
        "distilled": "围绕目标、受众、日历、算法、格式实验、互动和分析建立完整运营闭环。",
    },
    "SPROUT_INSTAGRAM_STRATEGY": {
        "name": "Sprout Social Instagram Marketing Strategy",
        "group": "Instagram 实战资料",
        "url": "https://sproutsocial.com/insights/instagram-marketing-strategy/",
        "use_for": "品牌 Instagram 策略、社群、营销结果",
        "distilled": "用清晰内容计划、受众理解、互动和数据来驱动品牌结果。",
    },
    "LATER_INSTAGRAM_GUIDES": {
        "name": "Later Instagram Guides",
        "group": "Instagram 实战资料",
        "url": "https://later.com/resources/guide/",
        "use_for": "Instagram 内容规划、Stories、Influencer Marketing",
        "distilled": "用启动清单、Stories Campaign、签名系列和影响者资料规划持续增长。",
    },
    "GOOGLE_SKILLSHOP_DIGITAL_MARKETING": {
        "name": "Google Skillshop: Fundamentals of Digital Marketing",
        "group": "数字营销资料",
        "url": "https://skillshop.exceedlms.com/student/collection/1830706-fundamentals-of-digital-marketing",
        "use_for": "数字营销基础、渠道、用户、数据",
        "distilled": "从数字客户、内容、社媒、视频、渠道和业务数据建立可迁移的营销基础。",
    },
    "CXL_INSTITUTE": {
        "name": "CXL Institute",
        "group": "数字营销资料",
        "url": "https://cxl.com/institute/",
        "use_for": "增长营销、转化优化、数据分析、高阶营销",
        "distilled": "用受众研究、转化优化、实验和数据分析提高营销决策质量。",
    },
    "SPROUT_SOCIAL_GUIDES": {
        "name": "Sprout Social Guides",
        "group": "数字营销资料",
        "url": "https://sproutsocial.com/insights/guides/",
        "use_for": "社媒管理、品牌、数据、社群运营",
        "distilled": "把社媒管理拆成发布、互动、倾听、品牌和报告流程。",
    },
    "CANVA_SOCIAL_MEDIA_MASTERY": {
        "name": "Canva Design School: Social Media Mastery",
        "group": "设计资料",
        "url": "https://www.canva.com/design-school/courses/social-media-mastery",
        "use_for": "社媒视觉、内容日历、品牌一致性",
        "distilled": "用模板、品牌组件和内容日历减少视觉生产摩擦，保持一致性。",
    },
    "COURSERA_DIGITAL_MARKETING_CANVA": {
        "name": "Coursera: Digital Marketing with Canva",
        "group": "设计资料",
        "url": "https://www.coursera.org/specializations/digital-marketing-with-canva",
        "use_for": "Canva 视觉设计、视频、品牌内容",
        "distilled": "用 Canva 做专业社媒视觉，并用数据驱动内容优化。",
    },
    "CARNEGIE": {
        "name": "How to Win Friends and Influence People",
        "group": "书籍资料",
        "author": "Dale Carnegie",
        "use_for": "人际关系、让别人感到被重视",
        "distilled": "真诚关注对方、记住对方、先让对方感到被看见，再谈影响。",
    },
    "CIALDINI_INFLUENCE": {
        "name": "Influence",
        "group": "书籍资料",
        "author": "Robert Cialdini",
        "use_for": "说服力、互惠、社会认同、权威",
        "distilled": "互惠、社会认同、权威和一致性可以提高行动意愿，但必须透明使用。",
    },
    "CIALDINI_PRESUASION": {
        "name": "Pre-Suasion",
        "group": "书籍资料",
        "author": "Robert Cialdini",
        "use_for": "说服前的氛围设计",
        "distilled": "行动前的注意力焦点会影响后续判断，先设计理解场景，再提出请求。",
    },
    "NONVIOLENT_COMMUNICATION": {
        "name": "Nonviolent Communication",
        "group": "书籍资料",
        "author": "Marshall Rosenberg",
        "use_for": "共情沟通、表达需求、减少压迫感",
        "distilled": "先观察事实和感受，再表达需要和请求，降低对话压迫感。",
    },
    "NEVER_SPLIT_DIFFERENCE": {
        "name": "Never Split the Difference",
        "group": "书籍资料",
        "author": "Chris Voss",
        "use_for": "提问、倾听、谈判、异议处理",
        "distilled": "用镜像、标注和校准问题让对方说出真实顾虑。",
    },
    "MADE_TO_STICK": {
        "name": "Made to Stick",
        "group": "书籍资料",
        "author": "Chip Heath & Dan Heath",
        "use_for": "让内容更容易被记住",
        "distilled": "简单、意外、具体、可信、情绪和故事能提升内容记忆度。",
    },
    "STORYBRAND": {
        "name": "Building a StoryBrand",
        "group": "书籍资料",
        "author": "Donald Miller",
        "use_for": "品牌叙事、用户导向表达",
        "distilled": "用户是主角，品牌是帮助者；表达应围绕用户问题和清晰行动。",
    },
    "EVERYBODY_WRITES": {
        "name": "Everybody Writes",
        "group": "书籍资料",
        "author": "Ann Handley",
        "use_for": "内容写作、品牌表达",
        "distilled": "好内容来自清晰受众、清晰语气、具体表达和反复编辑。",
    },
    "CONTAGIOUS": {
        "name": "Contagious",
        "group": "书籍资料",
        "author": "Jonah Berger",
        "use_for": "传播机制、内容扩散",
        "distilled": "社交货币、触发物、情绪、公共可见、实用价值和故事会增加传播概率。",
    },
    "SHOW_YOUR_WORK": {
        "name": "Show Your Work!",
        "group": "书籍资料",
        "author": "Austin Kleon",
        "use_for": "公开记录过程、建立真实感",
        "distilled": "持续公开过程、材料和学习轨迹，会让陌生人更容易相信你。",
    },
    "THIS_IS_MARKETING": {
        "name": "This Is Marketing",
        "group": "书籍资料",
        "author": "Seth Godin",
        "use_for": "小众市场、服务特定人群、建立信任",
        "distilled": "先服务一个足够具体的小群体，用信任和改变而不是打扰来做营销。",
    },
}


SOURCES.update(
    {
        "HBR_BETTER_LISTENER": {
            "name": "Harvard Business Review: How to Become a Better Listener",
            "group": "沟通与情商资料",
            "url": "https://www.hbs.edu/faculty/Pages/item.aspx?num=61726",
            "use_for": "主动倾听、减少误解、提高对话质量",
            "distilled": "倾听是一项可训练能力，尤其适合把评论、Story 回复和私信转成真实理解。",
        },
        "MINDTOOLS_ACTIVE_LISTENING": {
            "name": "MindTools: Active Listening",
            "group": "沟通与情商资料",
            "url": "https://www.mindtools.com/az4wxv7/active-listening/",
            "use_for": "倾听步骤、复述、澄清、延迟判断、尊重回应",
            "distilled": "有效倾听包括专注、反馈、澄清、暂缓评判和合适回应。",
        },
        "CNVC_FEELINGS_NEEDS": {
            "name": "Nonviolent Communication: Feelings and Needs",
            "group": "沟通与情商资料",
            "url": "https://nonviolentcommunication.com/learn-nonviolent-communication/feelings/",
            "use_for": "情绪/需求识别、共情表达、降低压迫感",
            "distilled": "具体表达情绪和需求，比笼统好坏判断更容易让对方感到被理解。",
        },
        "CRUCIAL_CONVERSATIONS": {
            "name": "Crucial Conversations for Mastering Dialogue",
            "group": "沟通与情商资料",
            "url": "https://cruciallearning.com/courses/crucial-conversations-for-dialogue/",
            "use_for": "高风险对话、表达观点、创造安全、共同目的",
            "distilled": "高情绪、高风险、意见不同的对话要先建立安全和共同目的，再表达观点。",
        },
        "CRUCIAL_MAKE_IT_SAFE": {
            "name": "Crucial Conversations: Make It Safe",
            "group": "沟通与情商资料",
            "url": "https://cruciallearning.com/blog/crucial-conversations-skill-summary-make-it-safe/",
            "use_for": "防御性回应、误解修复、对比声明",
            "distilled": "当对方开始防御时，先澄清自己不是要做什么、真正想做什么，再回到主题。",
        },
        "GREATER_GOOD_LISTENING": {
            "name": "Greater Good Science Center: Listening with Empathy",
            "group": "沟通与情商资料",
            "url": "https://greatergood.berkeley.edu/article/item/what_youre_listening_for_and_what_you_might_be_missing",
            "use_for": "同理倾听、降低防御、根据对话需要调整回应",
            "distilled": "先觉察自己的默认倾听滤镜，再用存在、肯定、好奇和澄清降低对方防御。",
        },
        "GOLEMAN_EQ": {
            "name": "Emotional Intelligence",
            "group": "沟通与情商资料",
            "author": "Daniel Goleman",
            "use_for": "自我觉察、自我调节、同理心、社交技能",
            "distilled": "高情商运营先管理自己的急迫感，再识别对方情绪、需求和关系信号。",
        },
        "META_REELS_ADS": {
            "name": "Meta for Business: Instagram and Facebook Reels Ads",
            "group": "Instagram 案例与广告资料",
            "url": "https://www.facebook.com/business/ads/facebook-instagram-reels-ads",
            "use_for": "Reels 广告、9:16 创意、安全区、A/B 测试、创作者合作",
            "distilled": "Reels 创意要原生竖屏、有声音、关键信息在安全区，并通过测试学习。",
        },
        "INSTAGRAM_REELS_ADS_HELP": {
            "name": "Instagram Help Center: Create Instagram Reels Ads",
            "group": "Instagram 案例与广告资料",
            "url": "https://www.facebook.com/help/instagram/546362593027755",
            "use_for": "Reels 广告目标、规格、声音、授权和投放设置",
            "distilled": "Reels 广告要与业务目标、全屏竖屏规格、音乐授权和投放位置一致。",
        },
        "LATER_CASE_STUDIES": {
            "name": "Later: Social Media and Influencer Marketing Case Studies",
            "group": "Instagram 案例与广告资料",
            "url": "https://later.com/resources/case-studies/",
            "use_for": "Instagram 影响者案例、真实品牌 campaign、创作者筛选",
            "distilled": "案例反复显示：真实创作者、清楚主题和可复用内容资产能放大品牌信任。",
        },
        "SPROUT_CASE_STUDIES": {
            "name": "Sprout Social Case Studies",
            "group": "Instagram 案例与广告资料",
            "url": "https://sproutsocial.com/insights/case-studies/",
            "use_for": "社媒客户服务、社区管理、品牌忠诚、社交数据应用",
            "distilled": "案例要看关系和流程：社媒不仅发布内容，也承担客户关怀和社群管理。",
        },
        "SPROUT_INSTAGRAM_ENGAGEMENT_CASE": {
            "name": "Sprout Social: Using Sprout to Increase Engagement on Instagram",
            "group": "Instagram 案例与广告资料",
            "url": "https://media.sproutsocial.com/uploads/2019/03/instagram-engagement.pdf",
            "use_for": "Instagram 社群互动、UGC 发现、品牌关键词",
            "distilled": "持续监测品牌关键词和粉丝内容，可以把 UGC、评论和社群故事接回品牌叙事。",
        },
        "HOOTSUITE_ALGORITHM_2026": {
            "name": "Hootsuite: Instagram Algorithm Tips for 2026",
            "group": "Instagram 实战资料",
            "url": "https://blog.hootsuite.com/instagram-algorithm/",
            "use_for": "Feed、Reels、Stories、Explore 排名信号",
            "distilled": "不同入口的排名信号不同，内容要分别优化观看、保存、分享、回复和关系信号。",
        },
        "HOOTSUITE_REELS_2026": {
            "name": "Hootsuite: Instagram Reels for Business in 2026",
            "group": "Instagram 实战资料",
            "url": "https://blog.hootsuite.com/instagram-reels/",
            "use_for": "Reels 规格、案例、教程、UGC、CTA、指标",
            "distilled": "Reels 适合教程、幕后、UGC、采访和可分享内容，必须用指标持续迭代。",
        },
        "HOOTSUITE_CAROUSEL_2025": {
            "name": "Hootsuite: Instagram Carousels Guide",
            "group": "Instagram 实战资料",
            "url": "https://blog.hootsuite.com/instagram-carousel/",
            "use_for": "Carousel 首图、滑动、保存、互动",
            "distilled": "Carousel 的第一张负责钩子，后续每页负责一个清楚、可收藏的价值点。",
        },
        "HOOTSUITE_STATS_2026": {
            "name": "Hootsuite: Instagram Statistics 2026",
            "group": "Instagram 实战资料",
            "url": "https://blog.hootsuite.com/instagram-statistics/",
            "use_for": "Instagram 用户、Stories、Reels、广告和商业趋势",
            "distilled": "统计数据用于决定内容优先级，但必须回到自己账号的受众行为验证。",
        },
        "LATER_STORIES_CAMPAIGN": {
            "name": "Later: How to Plan an Instagram Stories Campaign",
            "group": "Instagram 实战资料",
            "url": "https://mktg-cdn.later.com/ebooks/Later_How-to-Plan-an-Instagram-Stories-Campaign.pdf",
            "use_for": "Stories campaign、节奏设计、互动贴纸、活动承接",
            "distilled": "Stories campaign 要有铺垫、互动、转化和后续复用，而不是零散临时发布。",
        },
    }
)


def strategy(
    sid: str,
    title: str,
    stage: str,
    goals: list[str],
    formats: list[str],
    psychology: list[str],
    sources: list[str],
    principle: str,
    actions: list[str],
    metrics: list[str],
    keywords: list[str],
    template: str = "",
) -> dict:
    return {
        "id": sid,
        "title": title,
        "stage": stage,
        "stage_name": STAGES[stage],
        "goals": goals,
        "formats": formats,
        "psychology": psychology,
        "sources": sources,
        "principle": principle,
        "actions": actions,
        "metrics": metrics,
        "keywords": keywords,
        "template": template,
    }


STRATEGIES = [
    strategy(
        "IGS-S1-01",
        "用“小众服务对象”定义账号边界",
        "S1",
        ["提升关注转化率", "形成专家感", "建立长期关系"],
        ["Bio 策略", "社群策略"],
        ["提升被理解感", "降低陌生感", "提升持续关注理由"],
        ["THIS_IS_MARKETING", "GOOGLE_SKILLSHOP_DIGITAL_MARKETING", "HOOTSUITE_INSTAGRAM_RESOURCES"],
        "账号越早说清楚“我服务谁、帮他们解决什么、用什么方式解决”，越容易让正确的人留下。",
        [
            "写出一个不超过 18 个字的核心人群，例如“想用英语表达育儿理念的妈妈”。",
            "列出这个人群最常出现的 5 个场景、5 个焦虑、5 个期待结果。",
            "把主页 Bio、置顶内容、福利和评论互动都围绕这个人群重写。",
        ],
        ["主页访问到关注率", "非目标咨询占比", "新粉留言中是否复述你的定位"],
        ["用户定位", "小众人群", "niche", "目标用户", "账号定位"],
        "我帮助【具体人群】在【具体场景】解决【具体问题】，不用【常见阻碍】也能【期待结果】。",
    ),
    strategy(
        "IGS-S1-02",
        "建立用户需求四层卡",
        "S1",
        ["提升主页信任感", "增加评论互动", "开启私信对话"],
        ["Carousel 策略", "Story 策略", "私信策略"],
        ["提升被理解感", "提升安全感", "降低怀疑感"],
        ["GOOGLE_SKILLSHOP_DIGITAL_MARKETING", "CXL_INSTITUTE", "NONVIOLENT_COMMUNICATION"],
        "用户不是只为内容形式停留，而是为“被准确理解”停留；需求要拆到事实、感受、需要和顾虑。",
        [
            "每个目标用户画像写 4 层：正在经历什么、心里怎么想、真正想要什么、为什么还没行动。",
            "把四层分别转成选题：事实型 Reels、感受型 Story、需要型 Carousel、顾虑型 DM。",
            "每周从评论和私信里补充原话，替换掉团队自己想象的描述。",
        ],
        ["评论中“这就是我”的比例", "Story 投票参与率", "私信开启率"],
        ["需求洞察", "用户心理", "痛点", "NVC", "受众研究"],
    ),
    strategy(
        "IGS-S1-03",
        "做目标受众内容雷达",
        "S1",
        ["增加被看见", "形成专家感", "建立长期关系"],
        ["Reels 策略", "Carousel 策略", "Story 策略"],
        ["提升专业感", "提升持续关注理由", "提升参与感"],
        ["SPROUT_INSTAGRAM_STRATEGY", "HOOTSUITE_INSTAGRAM_RESOURCES", "BUFFER_INSTAGRAM"],
        "内容计划不要只按灵感排，而要覆盖用户会反复搜索、收藏、分享和追问的问题。",
        [
            "把内容雷达分成 6 格：误区、教程、案例、工具、观点、幕后。",
            "每格至少准备 10 个问题句标题，优先选用户会主动搜索的词。",
            "每周发布时确保至少覆盖 4 格，避免账号只剩一种表达。",
        ],
        ["覆盖的内容支柱数量", "收藏率", "分享率", "搜索关键词命中"],
        ["内容支柱", "内容雷达", "选题库", "内容规划"],
    ),
    strategy(
        "IGS-S1-04",
        "画出竞品与相邻账号互动地图",
        "S1",
        ["增加被看见", "增加评论互动", "形成专家感"],
        ["评论策略", "社群策略"],
        ["降低陌生感", "提升参与感", "提升专业感"],
        ["HOOTSUITE_INSTAGRAM_RESOURCES", "BUFFER_INSTAGRAM", "CARNEGIE"],
        "Instagram 会参考相关账号互动来理解你是谁；真正的关系也来自高质量参与，而不是孤立发布。",
        [
            "列出 30 个同领域、相邻领域和潜在合作账号，按受众重合度分层。",
            "每天选择 5 个账号留下有信息量的评论，避免只写表情或泛泛夸奖。",
            "记录哪些评论带来主页访问、回复或互关，保留高质量互动入口。",
        ],
        ["评论回复率", "由评论带来的主页访问", "相关账号互动力"],
        ["竞品分析", "相邻账号", "主动互动", "评论增长"],
    ),
    strategy(
        "IGS-S1-05",
        "搭建目标用户语言库",
        "S1",
        ["增加 Story 回复", "开启私信对话", "提升关注转化率"],
        ["Story 策略", "私信策略", "Bio 策略"],
        ["提升被理解感", "降低陌生感", "提升真实感"],
        ["EVERYBODY_WRITES", "CXL_INSTITUTE", "NONVIOLENT_COMMUNICATION"],
        "用户会回应“像自己说出来”的内容；语言库能让文案从自我表达变成用户表达。",
        [
            "收集评论、私信、客户反馈、竞品评论区中的原话，按痛点、欲望、反对意见分类。",
            "每条文案至少嵌入 1 句用户原话，不把它改成过度营销腔。",
            "每月清理过时表达，保留高回复、高收藏、高私信触发的说法。",
        ],
        ["Story 回复率", "私信开场质量", "文案保存率"],
        ["语言库", "用户原话", "文案", "Story 回复"],
        "你是不是也有过这种感觉：【用户原话】？",
    ),
    strategy(
        "IGS-S1-06",
        "建立购买或行动阻力清单",
        "S1",
        ["开启私信对话", "提高后续对话率", "提高福利领取率"],
        ["私信策略", "福利策略", "Story 策略"],
        ["提升安全感", "降低怀疑感", "提升被理解感"],
        ["NEVER_SPLIT_DIFFERENCE", "NONVIOLENT_COMMUNICATION", "CXL_INSTITUTE"],
        "阻力不是用户不懂，而是用户还没有被允许说出真实顾虑；策略要先承认顾虑。",
        [
            "把阻力分成价格、时间、信任、能力、隐私、结果不确定 6 类。",
            "为每类准备一个共情句、一个澄清问题、一个低风险下一步。",
            "在福利页、Story 和私信里主动回答最常见的 3 个阻力。",
        ],
        ["福利领取后回复率", "异议被提出后的继续对话率", "跳出率"],
        ["异议处理", "用户阻力", "私信转化", "信任"],
    ),
    strategy(
        "IGS-S1-07",
        "固定 3 个核心内容支柱",
        "S1",
        ["形成专家感", "增加被看见", "提升主页信任感"],
        ["Reels 策略", "Carousel 策略", "Story 策略"],
        ["提升专业感", "提升持续关注理由", "提升真实感"],
        ["BUFFER_INSTAGRAM", "SPROUT_INSTAGRAM_STRATEGY", "MADE_TO_STICK"],
        "内容支柱让用户知道为什么持续关注你，也让算法和新访客更快理解账号主题。",
        [
            "选择 3 个支柱：一个解决即时问题，一个展示专业判断，一个展示真实过程。",
            "每个支柱绑定 2 种格式，例如教程用 Carousel，过程用 Story，观点用 Reels。",
            "连续 30 天保持支柱不变，只测试标题、开头和 CTA。",
        ],
        ["各支柱平均互动率", "新粉来源内容分布", "连续关注后的回访率"],
        ["内容支柱", "账号主题", "专家感", "内容一致性"],
    ),
    strategy(
        "IGS-S1-08",
        "画用户旅程触点图",
        "S1",
        ["提升关注转化率", "提高后续对话率", "建立长期关系"],
        ["Bio 策略", "Highlights 策略", "私信策略"],
        ["提升安全感", "降低怀疑感", "提升持续关注理由"],
        ["GOOGLE_SKILLSHOP_DIGITAL_MARKETING", "STORYBRAND", "SPROUT_SOCIAL_GUIDES"],
        "用户从看见你到信任你，中间需要多个低压力触点，而不是一次性被要求购买或报名。",
        [
            "把旅程拆成看见、理解、相信、互动、领取、对话、复访 7 步。",
            "每一步指定一个内容入口：Reel、置顶帖、Highlight、Story、福利、私信、社群。",
            "检查每一步是否有明确下一步，避免用户看完不知道做什么。",
        ],
        ["主页访问后下一步点击率", "Highlight 完播率", "私信后续回复率"],
        ["用户旅程", "触点设计", "转化路径", "长期关系"],
    ),
    strategy(
        "IGS-S1-09",
        "设置新粉第一问机制",
        "S1",
        ["增加评论互动", "增加 Story 回复", "开启私信对话"],
        ["Story 策略", "评论策略", "私信策略"],
        ["提升参与感", "提升被理解感", "降低陌生感"],
        ["CARNEGIE", "NONVIOLENT_COMMUNICATION", "LATER_INSTAGRAM_GUIDES"],
        "关系建立的第一步不是介绍自己，而是给新粉一个轻松说出自己的入口。",
        [
            "置顶帖和欢迎 Story 都放一个低门槛问题，例如“你现在卡在哪一步？”",
            "用投票、滑杆、问答框降低表达成本，再把高意向回复延伸到私信。",
            "回复时先复述对方处境，再给一个小建议，最后再邀请下一步。",
        ],
        ["新粉 7 日内互动率", "Story 问答提交数", "第一轮私信回复率"],
        ["新粉互动", "第一问", "Story 问答", "评论引导"],
    ),
    strategy(
        "IGS-S2-01",
        "把 Bio 写成一句价值承诺",
        "S2",
        ["提升主页信任感", "提升关注转化率", "形成专家感"],
        ["Bio 策略"],
        ["降低陌生感", "提升专业感", "提升被理解感"],
        ["STORYBRAND", "HOOTSUITE_INSTAGRAM_RESOURCES", "HUBSPOT_INSTAGRAM"],
        "Bio 是主页的第一判断点，要让用户 3 秒内知道你能帮他获得什么改变。",
        [
            "第一行写服务对象，第二行写结果，第三行写证明或方法，最后放行动入口。",
            "删除抽象形容词，把“高质量、专业、成长”改成可感知结果。",
            "每月用主页访问到关注率检验 Bio 是否足够清楚。",
        ],
        ["主页访问到关注率", "Bio 链接点击率", "新粉私信中提到的关键词"],
        ["Bio", "主页优化", "价值主张", "关注转化"],
        "帮【人群】用【方法】在【场景】做到【结果】。从这里开始：【入口】",
    ),
    strategy(
        "IGS-S2-02",
        "在 Bio 和用户名中放搜索关键词",
        "S2",
        ["增加被看见", "提升关注转化率", "形成专家感"],
        ["Bio 策略"],
        ["提升专业感", "提升持续关注理由"],
        ["HOOTSUITE_INSTAGRAM_RESOURCES", "BUFFER_INSTAGRAM", "GOOGLE_SKILLSHOP_DIGITAL_MARKETING"],
        "社交搜索会读取账号名称、Bio、字幕和标题；关键词能帮对的人更快找到你。",
        [
            "把用户会搜索的 3 个词放进名称或 Bio，例如“亲子英语 / 儿童内容 / IG 增长”。",
            "避免只写品牌名而没有品类词，新账号尤其需要描述性关键词。",
            "在置顶帖标题、Reels 字幕和 Highlights 名称中重复核心关键词。",
        ],
        ["搜索曝光", "主页访问来源", "关键词相关私信"],
        ["Instagram SEO", "关键词", "Bio 搜索", "主页被发现"],
    ),
    strategy(
        "IGS-S2-03",
        "统一头像、封面和视觉识别",
        "S2",
        ["提升主页信任感", "提升关注转化率", "形成专家感"],
        ["Bio 策略", "Highlights 策略", "Carousel 策略"],
        ["降低怀疑感", "提升专业感", "提升真实感"],
        ["CANVA_SOCIAL_MEDIA_MASTERY", "COURSERA_DIGITAL_MARKETING_CANVA", "HUBSPOT_INSTAGRAM"],
        "视觉一致性会降低陌生账号的不确定感，尤其当用户从 Reels 点进主页时。",
        [
            "固定头像风格、3 个主色、2 种字体、封面布局和按钮样式。",
            "用 Canva 建一个账号模板库：Reels 封面、Carousel 封面、Story 背景、福利封面。",
            "每次发内容前检查缩略图在主页九宫格中是否能被快速理解。",
        ],
        ["主页停留时长", "置顶内容点击率", "视觉模板复用率"],
        ["视觉一致性", "Canva", "主页信任", "品牌识别"],
    ),
    strategy(
        "IGS-S2-04",
        "把 Highlights 设计成信任货架",
        "S2",
        ["提升主页信任感", "提升关注转化率", "提高福利领取率"],
        ["Highlights 策略", "Story 策略", "福利策略"],
        ["降低怀疑感", "提升安全感", "提升真实感"],
        ["HUBSPOT_INSTAGRAM", "HOOTSUITE_INSTAGRAM_RESOURCES", "STORYBRAND"],
        "Highlights 能把临时 Story 变成长期主页资产，承担“了解你、相信你、开始行动”的功能。",
        [
            "设置 5 个固定栏目：Start、案例、幕后、FAQ、福利。",
            "每个 Highlight 第一张用封面说明用户能得到什么，而不是只写内部分类名。",
            "每月删除过时 Story，把高回复 Story 加入对应栏目。",
        ],
        ["Highlight 打开率", "FAQ 后私信率", "福利 Highlight 点击率"],
        ["Highlights", "主页信任", "FAQ", "福利入口"],
    ),
    strategy(
        "IGS-S2-05",
        "用 3 条置顶帖完成主页导览",
        "S2",
        ["提升主页信任感", "提升关注转化率", "形成专家感"],
        ["Carousel 策略", "Reels 策略", "Bio 策略"],
        ["降低陌生感", "提升专业感", "提升持续关注理由"],
        ["SPROUT_INSTAGRAM_STRATEGY", "BUFFER_INSTAGRAM", "STORYBRAND"],
        "置顶帖要像店门口的导览牌，帮助新访客快速判断是否值得关注。",
        [
            "置顶 1：你是谁和服务谁；置顶 2：最强实用教程；置顶 3：案例或成果证明。",
            "每条置顶帖结尾都指向下一步：关注、看 Highlight、评论关键词或私信。",
            "如果置顶帖 60 天内不再代表当前账号定位，就更新。",
        ],
        ["置顶帖互动率", "置顶帖到关注转化", "置顶帖带来的私信"],
        ["置顶帖", "主页导览", "关注转化", "Start here"],
    ),
    strategy(
        "IGS-S2-06",
        "把社会认同放在主页可见处",
        "S2",
        ["提升主页信任感", "提升关注转化率", "形成专家感"],
        ["Highlights 策略", "Bio 策略", "Carousel 策略"],
        ["降低怀疑感", "提升专业感", "提升安全感"],
        ["CIALDINI_INFLUENCE", "HUBSPOT_INSTAGRAM", "SPROUT_INSTAGRAM_STRATEGY"],
        "陌生人会用他人的反馈判断风险；社会认同要具体、真实、可核验。",
        [
            "收集用户结果、评论截图、合作记录、媒体或证书，但避免夸大承诺。",
            "做成“结果/反馈/案例”Highlight，并在置顶帖解释背景和过程。",
            "用具体前后变化替代空泛好评，例如“从不敢评论到连续 7 天发 Story”。",
        ],
        ["案例 Highlight 查看率", "主页关注转化率", "咨询时信任问题减少"],
        ["社会认同", "案例", "用户反馈", "主页信任"],
    ),
    strategy(
        "IGS-S2-07",
        "降低联系和链接摩擦",
        "S2",
        ["开启私信对话", "提高福利领取率", "提升关注转化率"],
        ["Bio 策略", "私信策略", "福利策略"],
        ["提升安全感", "降低陌生感", "提升互惠感"],
        ["META_BLUEPRINT", "HOOTSUITE_INSTAGRAM_RESOURCES", "GOOGLE_SKILLSHOP_DIGITAL_MARKETING"],
        "用户愿意行动时，不应被复杂入口、失效链接或模糊 CTA 卡住。",
        [
            "检查联系方式、Bio 链接、福利领取路径、表单字段和自动回复是否可用。",
            "每个入口只承诺一个动作，例如“评论 PLAN 领取模板”。",
            "手机端亲自走一遍从主页到领取的流程，删掉不必要步骤。",
        ],
        ["Bio 链接点击率", "福利领取完成率", "入口报错次数"],
        ["链接优化", "CTA", "领取路径", "主页转化"],
    ),
    strategy(
        "IGS-S2-08",
        "制作 Start Here 新手导览",
        "S2",
        ["提升主页信任感", "提升关注转化率", "建立长期关系"],
        ["Highlights 策略", "Carousel 策略", "Story 策略"],
        ["降低陌生感", "提升安全感", "提升持续关注理由"],
        ["LATER_INSTAGRAM_GUIDES", "HOOTSUITE_INSTAGRAM_RESOURCES", "STORYBRAND"],
        "新访客需要被带路；一个清楚的 Start Here 能把碎片内容串成路径。",
        [
            "做一条 6-8 页 Carousel：你适合谁、先看什么、常见问题、下一步。",
            "把它置顶，并拆成 Story 加入 Start Highlight。",
            "每次账号定位调整后同步更新导览，避免旧内容误导新粉。",
        ],
        ["Start Here 完读率", "导览后关注率", "导览后私信率"],
        ["Start Here", "新手导览", "主页路径", "新粉"],
    ),
    strategy(
        "IGS-S2-09",
        "做主页风险感审计",
        "S2",
        ["提升主页信任感", "提升关注转化率", "开启私信对话"],
        ["Bio 策略", "Highlights 策略", "私信策略"],
        ["降低怀疑感", "提升安全感", "提升真实感"],
        ["NONVIOLENT_COMMUNICATION", "CXL_INSTITUTE", "META_BLUEPRINT"],
        "主页上的夸张承诺、信息缺口和不一致视觉都会放大用户风险感。",
        [
            "从陌生访客视角检查 5 件事：我知道你是谁吗、信任你吗、知道下一步吗、担心被推销吗、能退出吗。",
            "把高压话术改成选择式 CTA，例如“想要模板可以评论关键词”。",
            "删掉无法证明的绝对化承诺，把证据和边界讲清楚。",
        ],
        ["主页跳出率", "私信拒绝率", "用户提出的信任顾虑数量"],
        ["风险感", "主页审计", "低压力 CTA", "安全感"],
    ),
    strategy(
        "IGS-S3-01",
        "Reels 前 3 秒放强钩子",
        "S3",
        ["增加被看见", "提升关注转化率", "形成专家感"],
        ["Reels 策略"],
        ["提升参与感", "提升专业感", "提升持续关注理由"],
        ["INSTAGRAM_BEST_PRACTICES", "HOOTSUITE_INSTAGRAM_RESOURCES", "MADE_TO_STICK"],
        "Reels 的观看时长和完播会影响触达；开头必须立即说明为什么值得继续看。",
        [
            "用结果、反常识、错误纠正、清单或场景冲突开头。",
            "第一屏同时出现口播、字幕和画面动作，降低静音观看损失。",
            "每周复盘前 3 秒流失点，把低 retention 的开头改写再测。",
        ],
        ["3 秒留存率", "平均观看时长", "分享率", "主页访问率"],
        ["Reels", "钩子", "前3秒", "留存", "触达"],
        "别再【常见错误】了，真正影响【结果】的是这 3 件事。",
    ),
    strategy(
        "IGS-S3-02",
        "坚持原创、字幕、音频和清晰封面",
        "S3",
        ["增加被看见", "提升主页信任感", "形成专家感"],
        ["Reels 策略"],
        ["提升专业感", "提升真实感", "提升安全感"],
        ["INSTAGRAM_BEST_PRACTICES", "HOOTSUITE_INSTAGRAM_RESOURCES", "COURSERA_DIGITAL_MARKETING_CANVA"],
        "平台建议创作者使用原创、无水印、可理解的短视频；字幕和封面会影响理解与点击。",
        [
            "避免搬运带其他平台水印的视频，优先录制或重新剪辑为 Instagram 原生感内容。",
            "给每条 Reel 加字幕、标题封面、关键词 caption 和相关地点或协作者标签。",
            "封面只表达一个信息：这条视频解决什么问题。",
        ],
        ["推荐触达", "封面点击率", "字幕开启后的完播率"],
        ["原创内容", "Reels 字幕", "封面", "无水印"],
    ),
    strategy(
        "IGS-S3-03",
        "把 Carousel 做成可收藏资产",
        "S3",
        ["增加评论互动", "提升关注转化率", "形成专家感"],
        ["Carousel 策略"],
        ["提升专业感", "提升持续关注理由", "提升互惠感"],
        ["HOOTSUITE_INSTAGRAM_RESOURCES", "HUBSPOT_INSTAGRAM", "MADE_TO_STICK"],
        "Carousel 更适合承载步骤、清单和框架；收藏代表用户认为以后还会用。",
        [
            "第一页只负责让人继续滑：痛点、承诺或反常识。",
            "中间每页只讲一个动作或判断，保持字体清楚、留白足够。",
            "最后一页给评论问题或收藏提醒，而不是只写“关注我”。",
        ],
        ["收藏率", "滑动完成率", "评论率", "主页访问率"],
        ["Carousel", "收藏", "清单", "教程", "信息图"],
    ),
    strategy(
        "IGS-S3-04",
        "公开幕后过程而不只展示结果",
        "S3",
        ["提升主页信任感", "增加 Story 回复", "建立长期关系"],
        ["Story 策略", "Reels 策略", "Highlights 策略"],
        ["提升真实感", "降低陌生感", "提升安全感"],
        ["SHOW_YOUR_WORK", "HUBSPOT_INSTAGRAM", "CANVA_SOCIAL_MEDIA_MASTERY"],
        "幕后内容能让品牌从抽象账号变成真实的人和过程，减少“你是不是只会包装”的怀疑。",
        [
            "每周至少发布 3 条过程型 Story：准备、失败、修改、用户反馈、复盘。",
            "把高价值过程整理进“幕后”Highlight，形成长期信任证据。",
            "过程内容也要有结构：背景、困难、选择、结果、下一步。",
        ],
        ["幕后 Story 回复率", "Highlight 查看率", "信任类私信数量"],
        ["幕后", "过程记录", "真实感", "Show Your Work"],
    ),
    strategy(
        "IGS-S3-05",
        "用用户生成内容和客户故事降低怀疑",
        "S3",
        ["提升主页信任感", "提升关注转化率", "建立长期关系"],
        ["Reels 策略", "Carousel 策略", "Story 策略"],
        ["降低怀疑感", "提升真实感", "提升安全感"],
        ["HOOTSUITE_INSTAGRAM_RESOURCES", "CIALDINI_INFLUENCE", "SPROUT_INSTAGRAM_STRATEGY"],
        "用户故事比品牌自夸更有说服力，但必须给出背景和边界，避免制造虚假期待。",
        [
            "邀请用户分享使用过程、前后变化或一句真实反馈，并取得发布许可。",
            "把故事拆成问题、尝试、变化、仍在努力的部分，保留可信度。",
            "用 Story 贴纸请观众选择想看哪类案例，减少单向展示。",
        ],
        ["案例内容保存率", "案例后私信率", "UGC 投稿数"],
        ["UGC", "客户故事", "社会认同", "案例"],
    ),
    strategy(
        "IGS-S3-06",
        "用内容日历保证稳定输出",
        "S3",
        ["增加被看见", "建立长期关系", "形成专家感"],
        ["Reels 策略", "Carousel 策略", "Story 策略"],
        ["提升持续关注理由", "提升专业感", "提升安全感"],
        ["BUFFER_INSTAGRAM", "HOOTSUITE_INSTAGRAM_RESOURCES", "CANVA_SOCIAL_MEDIA_MASTERY"],
        "稳定不是每天硬发，而是提前把目标、格式、选题和发布时间放进可执行日历。",
        [
            "按周排 3 条 Reels、2 条 Carousel、每日 Story，不足时先保证质量最高的格式。",
            "把每条内容标注目标：触达、互动、信任、私信或福利。",
            "批量制作封面和模板，发布后把结果回填到日历。",
        ],
        ["发布完成率", "各格式互动率", "最佳发布时间命中率"],
        ["内容日历", "排程", "稳定输出", "Canva"],
    ),
    strategy(
        "IGS-S3-07",
        "每天用 Story 做低门槛互动",
        "S3",
        ["增加 Story 回复", "开启私信对话", "建立长期关系"],
        ["Story 策略", "私信策略"],
        ["提升参与感", "降低陌生感", "提升被理解感"],
        ["HOOTSUITE_INSTAGRAM_RESOURCES", "LATER_INSTAGRAM_GUIDES", "CARNEGIE"],
        "Story 更适合关系维护和即时反馈，贴纸能让用户用很低成本表达态度。",
        [
            "每日 Story 至少包含一个互动组件：投票、滑杆、问答框或测验。",
            "问题要具体到场景，例如“你现在最难的是选题、拍摄还是坚持？”",
            "把高意向回复转入私信，但第一句先感谢和复述，不急着推福利。",
        ],
        ["Story 回复率", "贴纸互动率", "Story 到 DM 转化率"],
        ["Story", "投票", "问答框", "关系维护"],
    ),
    strategy(
        "IGS-S3-08",
        "用 Live 做高信任微课堂",
        "S3",
        ["提升主页信任感", "开启私信对话", "形成专家感"],
        ["Live 策略", "Story 策略", "福利策略"],
        ["提升真实感", "提升专业感", "提升参与感"],
        ["META_BLUEPRINT", "HOOTSUITE_INSTAGRAM_RESOURCES", "SPROUT_INSTAGRAM_STRATEGY"],
        "Live 的实时感适合展示专业判断和回应真实问题，可作为私信和福利的高信任入口。",
        [
            "每场 Live 只解决一个主题，提前用 Story 收集问题。",
            "直播中设置 3 个互动节点：开场投票、中段提问、结尾领取资料。",
            "直播后剪成 Reels、整理成 Carousel，并把回放放进 Highlight。",
        ],
        ["Live 观看人数", "评论问题数", "Live 后私信数", "回放观看率"],
        ["Live", "微课堂", "直播互动", "专家感"],
    ),
    strategy(
        "IGS-S3-09",
        "用“简单且具体”的信息提高记忆度",
        "S3",
        ["增加被看见", "形成专家感", "提升关注转化率"],
        ["Reels 策略", "Carousel 策略", "Bio 策略"],
        ["提升专业感", "提升持续关注理由", "提升被理解感"],
        ["MADE_TO_STICK", "EVERYBODY_WRITES", "CONTAGIOUS"],
        "内容越容易复述，越容易被保存、分享和记住；每条内容只传递一个核心判断。",
        [
            "发前问自己：用户能不能用一句话告诉朋友这条讲了什么？",
            "用具体数字、例子和对比替代抽象概念。",
            "标题、开头和结尾重复同一个主张，减少信息分散。",
        ],
        ["分享率", "评论中复述观点的比例", "收藏率"],
        ["记忆点", "传播", "文案", "简单具体"],
    ),
    strategy(
        "IGS-S4-01",
        "做垂直领域评论冲刺",
        "S4",
        ["增加被看见", "增加评论互动", "开启私信对话"],
        ["评论策略", "社群策略"],
        ["降低陌生感", "提升参与感", "提升专业感"],
        ["HOOTSUITE_INSTAGRAM_RESOURCES", "CARNEGIE", "SPROUT_SOCIAL_GUIDES"],
        "高质量评论能让同领域用户先在熟悉场景里看到你，降低直接陌生触达的不适。",
        [
            "每天在 10 个相关账号下留下“补充信息型”或“具体共鸣型”评论。",
            "评论里不引流、不硬推，只提供一句有用观察或真诚提问。",
            "把收到回复的账号加入互动清单，后续持续建立关系。",
        ],
        ["外部评论带来的主页访问", "评论回复率", "互关率"],
        ["主动互动", "评论冲刺", "垂直社群", "被看见"],
    ),
    strategy(
        "IGS-S4-02",
        "首小时优先回复有效评论",
        "S4",
        ["增加评论互动", "增加被看见", "建立长期关系"],
        ["评论策略"],
        ["提升参与感", "提升被理解感", "提升安全感"],
        ["HOOTSUITE_INSTAGRAM_RESOURCES", "SPROUT_INSTAGRAM_STRATEGY", "CARNEGIE"],
        "早期互动会影响内容热度，及时且具体的回复也会训练用户下次继续留言。",
        [
            "发布后 60 分钟预留回复时间，优先回复有观点、有问题、有经历的评论。",
            "每次回复都加一个自然追问，推动评论串变长。",
            "把重复问题记录为下一条内容，不让评论只停留在当下。",
        ],
        ["首小时评论数", "评论串平均长度", "由评论转私信数"],
        ["首小时互动", "评论回复", "算法信号", "社群"],
    ),
    strategy(
        "IGS-S4-03",
        "把评论 CTA 从命令改成选择题",
        "S4",
        ["增加评论互动", "开启私信对话", "提升关注转化率"],
        ["评论策略", "Carousel 策略", "Reels 策略"],
        ["提升参与感", "提升安全感", "降低陌生感"],
        ["HUBSPOT_INSTAGRAM", "EVERYBODY_WRITES", "NONVIOLENT_COMMUNICATION"],
        "命令式 CTA 容易造成压力，选择题能让用户轻松参与并暴露真实需求。",
        [
            "把“评论你的想法”改成“A/B/C 你卡在哪个？”",
            "对不同选项准备不同回复，必要时邀请私信领取对应资料。",
            "用投票结果反向生成下一条内容，形成闭环。",
        ],
        ["评论率", "选项型评论占比", "评论后私信率"],
        ["评论 CTA", "选择题", "低压力互动", "文案"],
    ),
    strategy(
        "IGS-S4-04",
        "用协作内容借力相关受众",
        "S4",
        ["增加被看见", "提升主页信任感", "形成专家感"],
        ["Reels 策略", "Live 策略", "社群策略"],
        ["提升专业感", "降低陌生感", "提升真实感"],
        ["HOOTSUITE_INSTAGRAM_RESOURCES", "LATER_INSTAGRAM_GUIDES", "SPROUT_INSTAGRAM_STRATEGY"],
        "合作内容让你出现在相邻信任网络中，比冷启动触达更自然。",
        [
            "选择受众重合但产品不冲突的账号，设计互补主题。",
            "优先做 Collab Reel、联合 Live 或互相问答 Story。",
            "合作后复盘新增关注、保存、私信和未来合作机会。",
        ],
        ["合作内容触达", "合作新增关注", "合作后私信数"],
        ["合作", "Collab", "联合直播", "影响者"],
    ),
    strategy(
        "IGS-S4-05",
        "用社交聆听发现高共鸣话题",
        "S4",
        ["增加被看见", "增加评论互动", "形成专家感"],
        ["评论策略", "Story 策略", "Carousel 策略"],
        ["提升被理解感", "提升专业感", "提升参与感"],
        ["HOOTSUITE_INSTAGRAM_RESOURCES", "SPROUT_SOCIAL_GUIDES", "CXL_INSTITUTE"],
        "用户正在讨论的话题，比团队会议里的猜想更接近真实需求。",
        [
            "每周追踪行业关键词、竞品评论、热门问题和用户抱怨。",
            "把高频话题分成“立即回应”“深度解释”“需要验证”三类。",
            "用 Story 先小范围测试话题热度，再决定是否做成主内容。",
        ],
        ["话题测试回复率", "由聆听生成内容的表现", "关键词互动量"],
        ["社交聆听", "话题发现", "评论分析", "趋势"],
    ),
    strategy(
        "IGS-S4-06",
        "把 Story 回复当成关系入口",
        "S4",
        ["增加 Story 回复", "开启私信对话", "建立长期关系"],
        ["Story 策略", "私信策略"],
        ["提升被理解感", "降低陌生感", "提升安全感"],
        ["NONVIOLENT_COMMUNICATION", "CARNEGIE", "HOOTSUITE_INSTAGRAM_RESOURCES"],
        "Story 回复天然带上下文，比冷私信更适合开启轻松对话。",
        [
            "对每条 Story 回复先承接上下文，避免直接复制模板。",
            "用一句复述加一个开放问题，让对方愿意多说一点。",
            "只有当对方表达明确需求时，再给福利或进一步建议。",
        ],
        ["Story 回复到二次回复率", "Story 回复转私信深聊率", "取消关注率"],
        ["Story 回复", "关系入口", "私信承接", "共情"],
    ),
    strategy(
        "IGS-S4-07",
        "设置固定 Ask Me Anything 栏目",
        "S4",
        ["增加 Story 回复", "形成专家感", "提高后续对话率"],
        ["Story 策略", "Live 策略", "Highlights 策略"],
        ["提升参与感", "提升专业感", "提升安全感"],
        ["META_BLUEPRINT", "HUBSPOT_INSTAGRAM", "LATER_INSTAGRAM_GUIDES"],
        "固定问答栏目能让用户形成提问习惯，也让专业能力被持续看见。",
        [
            "每周固定一天开放问答，主题要窄，例如“主页诊断 10 分钟”。",
            "选 5-8 个典型问题公开回答，隐私问题转为匿名处理。",
            "把高质量回答沉淀到 FAQ Highlight 和后续 Carousel。",
        ],
        ["问答提交数", "回答 Story 完播率", "FAQ Highlight 查看率"],
        ["AMA", "问答", "专家感", "Story 栏目"],
    ),
    strategy(
        "IGS-S4-08",
        "用评论关键词开启福利领取",
        "S4",
        ["增加评论互动", "开启私信对话", "提高福利领取率"],
        ["评论策略", "私信策略", "福利策略"],
        ["提升互惠感", "提升参与感", "降低陌生感"],
        ["CIALDINI_INFLUENCE", "HOOTSUITE_INSTAGRAM_RESOURCES", "BUFFER_INSTAGRAM"],
        "评论关键词既能提升内容互动，也能把有兴趣的人自然带到私信。",
        [
            "关键词要和内容主题一致，例如“评论 BIO 领取主页检查表”。",
            "自动或手动回复都要先确认需求，再发送资料链接。",
            "领取后追问一个使用场景，避免福利发完关系就断。",
        ],
        ["关键词评论数", "福利发送成功率", "领取后回复率"],
        ["评论关键词", "福利领取", "私信自动化", "互惠"],
    ),
    strategy(
        "IGS-S4-09",
        "积极参与竞品和同行的公共讨论",
        "S4",
        ["增加被看见", "形成专家感", "建立长期关系"],
        ["评论策略", "社群策略"],
        ["降低陌生感", "提升专业感", "提升安全感"],
        ["THIS_IS_MARKETING", "CARNEGIE", "SPROUT_SOCIAL_GUIDES"],
        "同行不是只用来比较，也可以成为共同教育市场的公共空间。",
        [
            "只在自己能补充价值的帖子下评论，避免抢话题或攻击。",
            "多用“我补充一个角度”而不是“你说错了”。",
            "把互相尊重的互动沉淀为未来合作、转介绍或联合内容机会。",
        ],
        ["同行互动回复率", "同行转介绍数", "合作机会数"],
        ["同行互动", "公共讨论", "社群关系", "专家感"],
    ),
    strategy(
        "IGS-S5-01",
        "用许可式私信开场",
        "S5",
        ["开启私信对话", "提高后续对话率", "提升主页信任感"],
        ["私信策略"],
        ["提升安全感", "降低陌生感", "提升被理解感"],
        ["NONVIOLENT_COMMUNICATION", "NEVER_SPLIT_DIFFERENCE", "CARNEGIE"],
        "私信是高亲密度空间，开场要让用户感觉自己可以选择，而不是被追着成交。",
        [
            "先说明你为什么来私信：承接评论、Story 回复或福利领取。",
            "用许可问题开启，例如“我可以根据你的情况给一个小建议吗？”",
            "如果对方没有回复，最多一次轻提醒，不连续施压。",
        ],
        ["第一轮回复率", "已读不回率", "负面反馈数"],
        ["私信开场", "许可式沟通", "DM", "安全感"],
        "看到你刚才提到【用户场景】。我可以问你 1 个问题，再给你一个更贴合的建议吗？",
    ),
    strategy(
        "IGS-S5-02",
        "镜像用户原话而不是急着解释",
        "S5",
        ["提高后续对话率", "开启私信对话", "建立长期关系"],
        ["私信策略"],
        ["提升被理解感", "提升安全感", "降低怀疑感"],
        ["NEVER_SPLIT_DIFFERENCE", "NONVIOLENT_COMMUNICATION", "EVERYBODY_WRITES"],
        "用户在私信里最先需要被听见；镜像原话能让对方继续展开真实问题。",
        [
            "复制对方关键短语并轻轻追问，例如“你说‘不知道怎么开始’？”",
            "避免马上给长篇方案，先确认问题、目标和限制。",
            "把用户原话沉淀到语言库，后续用于内容和 FAQ。",
        ],
        ["二次回复率", "用户补充信息长度", "对话中断点"],
        ["镜像", "倾听", "私信", "用户原话"],
    ),
    strategy(
        "IGS-S5-03",
        "用 3 个诊断问题判断需求",
        "S5",
        ["开启私信对话", "提高后续对话率", "形成专家感"],
        ["私信策略", "福利策略"],
        ["提升专业感", "提升安全感", "提升被理解感"],
        ["CXL_INSTITUTE", "NEVER_SPLIT_DIFFERENCE", "GOOGLE_SKILLSHOP_DIGITAL_MARKETING"],
        "有效私信不是把所有知识倒出来，而是快速定位用户所在阶段和下一步。",
        [
            "固定 3 问：现在目标是什么、目前卡在哪里、试过什么还没用。",
            "根据答案把用户分成新手、执行中、需要转化优化三类。",
            "每类只给一个下一步，避免信息过载。",
        ],
        ["诊断完成率", "建议采纳率", "后续预约或领取率"],
        ["需求诊断", "私信问题", "转化", "用户阶段"],
    ),
    strategy(
        "IGS-S5-04",
        "先给小价值再提出下一步",
        "S5",
        ["提高后续对话率", "提高福利领取率", "提升主页信任感"],
        ["私信策略", "福利策略"],
        ["提升互惠感", "提升安全感", "降低怀疑感"],
        ["CIALDINI_INFLUENCE", "CARNEGIE", "THIS_IS_MARKETING"],
        "互惠不是诱导，而是在请求之前先提供真正能减轻用户负担的小帮助。",
        [
            "在私信里给一个具体改进点、一个模板或一个判断标准。",
            "确认对方觉得有用后，再问是否需要更完整的资料或下一步。",
            "避免把免费价值设计成必须付费才能理解的半截内容。",
        ],
        ["小建议后回复率", "福利领取率", "后续咨询率"],
        ["互惠", "私信价值", "福利", "下一步"],
    ),
    strategy(
        "IGS-S5-05",
        "用标注法处理异议",
        "S5",
        ["提高后续对话率", "提升主页信任感", "开启私信对话"],
        ["私信策略"],
        ["降低怀疑感", "提升安全感", "提升被理解感"],
        ["NEVER_SPLIT_DIFFERENCE", "NONVIOLENT_COMMUNICATION", "CXL_INSTITUTE"],
        "异议不是反对你，而是用户在保护自己；先标注顾虑，再提供证据和选择。",
        [
            "用“听起来你担心的是……”标注，而不是立刻反驳。",
            "把异议拆成事实问题和感受问题，分别回应。",
            "提供低风险选项，例如先看案例、先用免费清单、以后再决定。",
        ],
        ["异议后继续对话率", "用户主动补充顾虑数", "最终行动率"],
        ["异议处理", "标注", "私信谈判", "安全感"],
    ),
    strategy(
        "IGS-S5-06",
        "把 Story 回复自然桥接到私信",
        "S5",
        ["增加 Story 回复", "开启私信对话", "提高后续对话率"],
        ["Story 策略", "私信策略"],
        ["降低陌生感", "提升被理解感", "提升安全感"],
        ["HOOTSUITE_INSTAGRAM_RESOURCES", "INSTAGRAM_BEST_PRACTICES", "NONVIOLENT_COMMUNICATION"],
        "Story 已经提供了上下文，私信桥接只需要延续对方刚表达的兴趣。",
        [
            "对投票、问答、滑杆结果分组回复，不同选择给不同私信开场。",
            "开场引用对方在 Story 的行为，例如“你刚选了‘选题卡住’”。",
            "不要立刻发长链接，先问是否要一个简短建议。",
        ],
        ["Story 互动到 DM 比例", "私信第一轮回复率", "后续对话率"],
        ["Story 到私信", "DM 桥接", "私信开场", "互动"],
    ),
    strategy(
        "IGS-S5-07",
        "用无压力结尾提高下次回复",
        "S5",
        ["提高后续对话率", "建立长期关系", "提升主页信任感"],
        ["私信策略"],
        ["提升安全感", "降低怀疑感", "提升持续关注理由"],
        ["THIS_IS_MARKETING", "NONVIOLENT_COMMUNICATION", "CARNEGIE"],
        "一次私信不必完成所有转化，好的结尾会保护关系并留下回来继续聊的理由。",
        [
            "结尾给用户选择权，例如“你可以先试这个，之后有结果再发我”。",
            "约定一个轻量回访点，但不制造紧迫压力。",
            "把未成熟线索放入长期互动列表，而不是反复催促。",
        ],
        ["下次主动回复率", "私信取消或拉黑率", "长期线索复活率"],
        ["无压力成交", "私信结尾", "长期关系", "回访"],
    ),
    strategy(
        "IGS-S5-08",
        "给高意向用户做记忆笔记",
        "S5",
        ["提高后续对话率", "建立长期关系", "形成专家感"],
        ["私信策略", "社群策略"],
        ["提升被理解感", "提升安全感", "提升专业感"],
        ["CARNEGIE", "SPROUT_SOCIAL_GUIDES", "CXL_INSTITUTE"],
        "记住用户的具体情况，会让后续对话更像关系，而不是群发。",
        [
            "为高意向用户记录来源内容、需求、顾虑、已发资料和约定回访点。",
            "下次互动时提到前文，而不是重新问一遍基础问题。",
            "定期清理无效记录，只维护真实互动过的人。",
        ],
        ["回访回复率", "重复问题减少", "高意向用户转化率"],
        ["用户记录", "CRM", "私信维护", "长期关系"],
    ),
    strategy(
        "IGS-S5-09",
        "私信中明确隐私和边界",
        "S5",
        ["提升主页信任感", "提高后续对话率", "建立长期关系"],
        ["私信策略", "社群策略"],
        ["提升安全感", "降低怀疑感", "提升真实感"],
        ["INSTAGRAM_BEST_PRACTICES", "HUBSPOT_INSTAGRAM", "NONVIOLENT_COMMUNICATION"],
        "用户越愿意说真实问题，越需要知道内容不会被随意公开或误用。",
        [
            "涉及个人经历、截图、案例时先请求许可，再决定是否匿名发布。",
            "清楚说明你能帮什么、不能承诺什么，避免过度期待。",
            "遇到敏感问题时建议转向专业服务或更安全渠道。",
        ],
        ["用户许可率", "敏感对话投诉数", "信任类正反馈"],
        ["隐私", "边界", "私信安全", "案例授权"],
    ),
    strategy(
        "IGS-S6-01",
        "把福利设计成一个小胜利",
        "S6",
        ["提高福利领取率", "提升主页信任感", "提高后续对话率"],
        ["福利策略", "私信策略", "Carousel 策略"],
        ["提升互惠感", "提升安全感", "提升专业感"],
        ["CIALDINI_INFLUENCE", "GOOGLE_SKILLSHOP_DIGITAL_MARKETING", "CXL_INSTITUTE"],
        "好的福利不是资料堆，而是让用户在 10 分钟内完成一个可感知的小进步。",
        [
            "把福利目标写成动词结果，例如“检查 Bio 的 7 个问题”。",
            "删除背景知识，只保留能立即使用的清单、模板或示例。",
            "领取后安排一个反馈问题，知道用户是否真的完成。",
        ],
        ["福利领取率", "福利使用反馈率", "领取后私信率"],
        ["福利", "lead magnet", "小胜利", "互惠"],
    ),
    strategy(
        "IGS-S6-02",
        "用高收藏内容反推福利主题",
        "S6",
        ["提高福利领取率", "增加评论互动", "形成专家感"],
        ["福利策略", "Carousel 策略", "Reels 策略"],
        ["提升专业感", "提升互惠感", "提升持续关注理由"],
        ["HOOTSUITE_INSTAGRAM_RESOURCES", "CXL_INSTITUTE", "SPROUT_INSTAGRAM_STRATEGY"],
        "用户已经用收藏和保存告诉你什么值得深入，福利主题应从真实行为中来。",
        [
            "每月挑选保存率最高的 5 条内容，找出共同问题。",
            "把其中最具体的问题做成模板、检查表或案例拆解。",
            "福利发布前用 Story 问一句“你想要完整版吗？”验证需求。",
        ],
        ["福利预热回复率", "高收藏内容到领取转化", "福利后续使用率"],
        ["福利选题", "保存率", "数据驱动", "模板"],
    ),
    strategy(
        "IGS-S6-03",
        "用 DM 关键词搭建低摩擦领取路径",
        "S6",
        ["提高福利领取率", "开启私信对话", "增加评论互动"],
        ["福利策略", "评论策略", "私信策略"],
        ["提升参与感", "提升互惠感", "降低陌生感"],
        ["HOOTSUITE_INSTAGRAM_RESOURCES", "BUFFER_INSTAGRAM", "CIALDINI_INFLUENCE"],
        "关键词路径让用户不用离开 Instagram 就能表达兴趣，适合轻量福利和内容延伸。",
        [
            "每个福利只设置一个关键词，避免用户不知道该评论什么。",
            "自动回复或人工回复要包含资料、使用方法和一个反馈问题。",
            "把领取用户按主题打标签，为后续内容和私信跟进做准备。",
        ],
        ["关键词评论数", "DM 打开率", "资料点击率", "反馈回复率"],
        ["DM 关键词", "福利路径", "自动回复", "领取率"],
    ),
    strategy(
        "IGS-S6-04",
        "把 Carousel 延伸成检查表福利",
        "S6",
        ["提高福利领取率", "提升关注转化率", "形成专家感"],
        ["Carousel 策略", "福利策略", "私信策略"],
        ["提升专业感", "提升互惠感", "提升持续关注理由"],
        ["HOOTSUITE_INSTAGRAM_RESOURCES", "CANVA_SOCIAL_MEDIA_MASTERY", "EVERYBODY_WRITES"],
        "Carousel 负责公开教育，福利负责让用户带走可执行工具，两者天然相连。",
        [
            "把 Carousel 的每页要点转成可勾选检查项。",
            "在最后一页提供关键词领取，不强迫用户跳外链。",
            "福利模板视觉与原帖一致，增强专业感和记忆。",
        ],
        ["Carousel 完读率", "最后一页评论率", "检查表领取率"],
        ["Carousel 福利", "检查表", "Canva 模板", "领取"],
    ),
    strategy(
        "IGS-S6-05",
        "做 Story 专属限时福利",
        "S6",
        ["增加 Story 回复", "提高福利领取率", "开启私信对话"],
        ["Story 策略", "福利策略", "私信策略"],
        ["提升参与感", "提升互惠感", "提升持续关注理由"],
        ["CIALDINI_PRESUASION", "LATER_INSTAGRAM_GUIDES", "HOOTSUITE_INSTAGRAM_RESOURCES"],
        "Story 的临时性适合做轻量限时福利，但重点应是上下文匹配，而不是制造焦虑。",
        [
            "先用 2-3 张 Story 铺垫问题，再开放福利领取。",
            "福利只限与当天主题相关的人领取，避免泛流量。",
            "结束后把用户反馈或常见问题沉淀为下次公开内容。",
        ],
        ["Story 福利回复率", "领取后使用反馈", "次日回访率"],
        ["Story 福利", "限时", "预先说服", "私信"],
    ),
    strategy(
        "IGS-S6-06",
        "Live 结束发送加餐资料",
        "S6",
        ["提高福利领取率", "提高后续对话率", "形成专家感"],
        ["Live 策略", "福利策略", "私信策略"],
        ["提升互惠感", "提升专业感", "提升参与感"],
        ["META_BLUEPRINT", "CIALDINI_INFLUENCE", "SPROUT_INSTAGRAM_STRATEGY"],
        "直播后的福利承接能把实时注意力转成可持续关系。",
        [
            "直播前说明会后有资料，但资料必须服务直播主题。",
            "直播中用关键词收集领取者，直播后分批私信发送。",
            "资料里附一个行动任务和回报问题，例如“做完发我，我帮你看一眼”。",
        ],
        ["Live 后领取率", "资料后反馈率", "回放观看率"],
        ["Live 福利", "直播资料", "加餐", "后续对话"],
    ),
    strategy(
        "IGS-S6-07",
        "在主页放福利货架而不是单一链接",
        "S6",
        ["提高福利领取率", "提升主页信任感", "提升关注转化率"],
        ["Highlights 策略", "Bio 策略", "福利策略"],
        ["提升安全感", "提升互惠感", "提升持续关注理由"],
        ["HUBSPOT_INSTAGRAM", "STORYBRAND", "BUFFER_INSTAGRAM"],
        "不同阶段用户需要不同福利，主页应让他们按自己的问题选择，而不是只给一个入口。",
        [
            "设置“免费资源”Highlight，按新手、进阶、案例、工具分类。",
            "Bio 链接页只放 3 个最常用资源，避免选择过载。",
            "每个资源说明适合谁、不适合谁、需要花多久完成。",
        ],
        ["福利 Highlight 点击率", "资源选择完成率", "领取到关注转化"],
        ["福利货架", "免费资源", "Highlight", "Bio 链接"],
    ),
    strategy(
        "IGS-S6-08",
        "福利发送后立刻问使用场景",
        "S6",
        ["提高后续对话率", "开启私信对话", "建立长期关系"],
        ["私信策略", "福利策略"],
        ["提升被理解感", "提升安全感", "提升参与感"],
        ["NONVIOLENT_COMMUNICATION", "NEVER_SPLIT_DIFFERENCE", "CXL_INSTITUTE"],
        "资料发送不是结束，而是理解用户真实场景的开始。",
        [
            "发送资料后问一个具体问题：你准备用它改哪一部分？",
            "根据回答给一个微建议，避免只说“有问题问我”。",
            "48 小时后基于对方场景轻回访一次，询问是否卡住。",
        ],
        ["福利后第一问回复率", "48 小时回访回复率", "资料完成率"],
        ["福利跟进", "使用场景", "私信回访", "后续对话"],
    ),
    strategy(
        "IGS-S6-09",
        "展示福利使用后的真实反馈",
        "S6",
        ["提升主页信任感", "提高福利领取率", "提升关注转化率"],
        ["福利策略", "Story 策略", "Highlights 策略"],
        ["降低怀疑感", "提升真实感", "提升安全感"],
        ["CIALDINI_INFLUENCE", "SPROUT_INSTAGRAM_STRATEGY", "HUBSPOT_INSTAGRAM"],
        "福利结果反馈能证明资料不是噱头，也能让潜在用户知道自己能获得什么。",
        [
            "征得许可后展示用户完成截图、改前改后或一句反馈。",
            "同时展示适用边界，不把个别结果包装成普遍保证。",
            "把反馈放入福利 Highlight，作为下一批领取者的信任入口。",
        ],
        ["福利反馈查看率", "反馈后领取率", "信任类私信"],
        ["福利反馈", "社会认同", "案例", "真实感"],
    ),
    strategy(
        "IGS-S7-01",
        "打造固定签名内容系列",
        "S7",
        ["建立长期关系", "形成专家感", "增加被看见"],
        ["Reels 策略", "Carousel 策略", "Story 策略"],
        ["提升持续关注理由", "提升专业感", "提升参与感"],
        ["LATER_INSTAGRAM_GUIDES", "SHOW_YOUR_WORK", "SPROUT_INSTAGRAM_STRATEGY"],
        "固定系列能让用户知道什么时候回来、为什么回来，也降低团队选题成本。",
        [
            "选择一个能连续做 12 周的栏目，例如“每周主页诊断”。",
            "固定视觉、标题结构和发布时间，让用户形成记忆。",
            "每 4 周复盘一次栏目表现，只优化钩子和 CTA，不频繁换主题。",
        ],
        ["系列回访率", "系列平均保存率", "系列新增关注"],
        ["签名系列", "固定栏目", "长期关注", "内容系列"],
    ),
    strategy(
        "IGS-S7-02",
        "建立每周社群仪式",
        "S7",
        ["建立长期关系", "增加 Story 回复", "增加评论互动"],
        ["Story 策略", "评论策略", "社群策略"],
        ["提升参与感", "提升持续关注理由", "降低陌生感"],
        ["CARNEGIE", "THIS_IS_MARKETING", "SPROUT_SOCIAL_GUIDES"],
        "长期关系需要节奏感；用户参与越固定，账号越不像一次性内容频道。",
        [
            "每周固定一个参与动作：周一目标、周三提问、周五复盘。",
            "公开回应部分用户投稿，让参与者感到被看见。",
            "把仪式名称固定下来，逐渐形成社群语言。",
        ],
        ["每周参与人数", "重复参与率", "用户投稿数"],
        ["社群仪式", "长期关系", "用户参与", "固定互动"],
    ),
    strategy(
        "IGS-S7-03",
        "设计新粉 7 天欢迎路径",
        "S7",
        ["提升关注转化率", "建立长期关系", "提高后续对话率"],
        ["Highlights 策略", "Story 策略", "私信策略"],
        ["降低陌生感", "提升安全感", "提升持续关注理由"],
        ["STORYBRAND", "NONVIOLENT_COMMUNICATION", "BUFFER_INSTAGRAM"],
        "新粉关注后的前 7 天决定他会不会形成记忆和互动习惯。",
        [
            "第 1 天引导看 Start Here，第 2-3 天推核心教程，第 4-5 天展示案例和幕后。",
            "第 6 天用 Story 问问题，第 7 天提供低门槛福利。",
            "用手动或自动方式记录哪些新粉在 7 天内互动过。",
        ],
        ["新粉 7 日留存互动率", "Start Here 查看率", "7 日内私信率"],
        ["新粉欢迎", "7天路径", "留存", "关系建立"],
    ),
    strategy(
        "IGS-S7-04",
        "固定用户 spotlight 栏目",
        "S7",
        ["建立长期关系", "提升主页信任感", "增加评论互动"],
        ["Story 策略", "Carousel 策略", "社群策略"],
        ["提升真实感", "提升参与感", "提升互惠感"],
        ["CIALDINI_INFLUENCE", "HUBSPOT_INSTAGRAM", "SPROUT_INSTAGRAM_STRATEGY"],
        "让用户成为内容的一部分，会提高社群归属感和真实可信度。",
        [
            "每周展示一个用户问题、尝试或成果，必须先获得许可。",
            "强调过程和可复制动作，而不是只展示漂亮结果。",
            "邀请其他用户评论支持或提出类似问题。",
        ],
        ["用户投稿数", "spotlight 评论率", "被展示用户后续互动"],
        ["用户 spotlight", "UGC", "社群", "长期关系"],
    ),
    strategy(
        "IGS-S7-05",
        "把旧内容重新打包成新路径",
        "S7",
        ["增加被看见", "建立长期关系", "形成专家感"],
        ["Carousel 策略", "Highlights 策略", "Reels 策略"],
        ["提升持续关注理由", "提升专业感", "提升安全感"],
        ["LATER_INSTAGRAM_GUIDES", "HOOTSUITE_INSTAGRAM_RESOURCES", "BUFFER_INSTAGRAM"],
        "长期运营不能只追新内容；把旧内容按用户路径重新组织，会提高资产复用率。",
        [
            "每月选择 10 条旧内容，按“新手入门、常见错误、案例、工具”重新归类。",
            "把旧 Carousel 改成 Reel 脚本，把旧 Live 改成 FAQ Carousel。",
            "用 Highlight 或置顶帖把内容路径重新呈现给新粉。",
        ],
        ["旧内容二次触达", "重制内容保存率", "内容资产复用率"],
        ["内容复用", "旧内容", "内容路径", "长期维护"],
    ),
    strategy(
        "IGS-S7-06",
        "用长期叙事记录成长线",
        "S7",
        ["建立长期关系", "提升主页信任感", "增加 Story 回复"],
        ["Story 策略", "Reels 策略", "Highlights 策略"],
        ["提升真实感", "提升持续关注理由", "降低陌生感"],
        ["SHOW_YOUR_WORK", "STORYBRAND", "EVERYBODY_WRITES"],
        "长期叙事让用户不只是看单条内容，而是在跟随一个正在变化的过程。",
        [
            "选择一个长期项目或主题，每周公开进展、选择和复盘。",
            "把失败和调整也纳入叙事，避免只展示完美结果。",
            "每个阶段设置一个问题让用户参与判断或投票。",
        ],
        ["长期项目 Story 查看率", "重复回复用户数", "系列完结互动"],
        ["长期叙事", "过程公开", "真实感", "故事"],
    ),
    strategy(
        "IGS-S7-07",
        "把 Instagram 关系桥接到其他渠道",
        "S7",
        ["建立长期关系", "提高后续对话率", "提高福利领取率"],
        ["福利策略", "私信策略", "社群策略"],
        ["提升安全感", "提升持续关注理由", "提升互惠感"],
        ["GOOGLE_SKILLSHOP_DIGITAL_MARKETING", "SPROUT_SOCIAL_GUIDES", "CXL_INSTITUTE"],
        "Instagram 适合发现和互动，但长期关系可以通过邮件、社群或预约系统沉淀。",
        [
            "只在用户领取福利或表达明确兴趣后邀请加入更长期渠道。",
            "说明加入后会获得什么频率、什么内容、如何退出。",
            "用标签记录来源内容，后续评估哪个入口带来高质量关系。",
        ],
        ["跨渠道加入率", "跨渠道留存", "来源内容贡献"],
        ["跨渠道", "邮件", "社群", "长期沉淀"],
    ),
    strategy(
        "IGS-S7-08",
        "建立负面评论和误解处理 SOP",
        "S7",
        ["提升主页信任感", "建立长期关系", "提升关注转化率"],
        ["评论策略", "私信策略", "社群策略"],
        ["提升安全感", "降低怀疑感", "提升专业感"],
        ["NONVIOLENT_COMMUNICATION", "HUBSPOT_INSTAGRAM", "INSTAGRAM_BEST_PRACTICES"],
        "公开评论区的处理方式会被旁观者用来判断品牌安全感和专业度。",
        [
            "把评论分成误解、抱怨、攻击、垃圾信息四类，分别准备回应方式。",
            "对误解先澄清事实，对抱怨先承认感受，对攻击和垃圾信息按平台工具处理。",
            "必要时转入私信处理，但在公开区留下简短、平和、可理解的回应。",
        ],
        ["负面评论升级率", "公开回应后的二次评论", "隐藏或删除比例"],
        ["负面评论", "SOP", "安全感", "社群管理"],
    ),
    strategy(
        "IGS-S7-09",
        "用关系节奏表维护高价值互动",
        "S7",
        ["建立长期关系", "提高后续对话率", "形成专家感"],
        ["私信策略", "评论策略", "社群策略"],
        ["提升被理解感", "提升安全感", "提升持续关注理由"],
        ["SPROUT_SOCIAL_GUIDES", "HOOTSUITE_INSTAGRAM_RESOURCES", "CARNEGIE"],
        "长期关系不是靠记忆硬撑，需要有节奏地回应、回访和提供价值。",
        [
            "把高价值互动分成新粉、活跃用户、潜在合作、潜在客户四类。",
            "为每类设置自然触达节奏，例如每 2 周回应一次内容或私信回访。",
            "触达必须基于对方最近行为，避免无上下文群发。",
        ],
        ["高价值用户重复互动率", "回访回复率", "合作或转化机会数"],
        ["关系节奏", "高价值互动", "CRM", "长期维护"],
    ),
    strategy(
        "IGS-S8-01",
        "按目标建立 KPI 树",
        "S8",
        ["增加被看见", "提升关注转化率", "提高福利领取率"],
        ["Reels 策略", "Carousel 策略", "福利策略"],
        ["提升专业感", "提升安全感"],
        ["GOOGLE_SKILLSHOP_DIGITAL_MARKETING", "SPROUT_INSTAGRAM_STRATEGY", "CXL_INSTITUTE"],
        "不同目标不能只看同一个点赞数；每个目标要对应上游、中游和下游指标。",
        [
            "触达看曝光、观看时长、分享；信任看主页访问、Highlight、案例查看。",
            "互动看评论、Story 回复、私信；福利看领取、使用反馈、后续对话。",
            "每周只选择 3 个核心指标复盘，避免指标过载。",
        ],
        ["核心指标完成率", "指标与业务结果相关性", "复盘执行率"],
        ["KPI", "数据复盘", "指标树", "Instagram Insights"],
    ),
    strategy(
        "IGS-S8-02",
        "用 Reels 留存曲线优化开头和节奏",
        "S8",
        ["增加被看见", "形成专家感", "提升关注转化率"],
        ["Reels 策略"],
        ["提升专业感", "提升持续关注理由"],
        ["INSTAGRAM_BEST_PRACTICES", "HOOTSUITE_INSTAGRAM_RESOURCES", "CXL_INSTITUTE"],
        "Reels 不是只看播放量，留存曲线能告诉你用户在哪一秒失去兴趣。",
        [
            "记录每条 Reel 的 3 秒留存、平均观看、完播和重看。",
            "把前 3 秒掉点高的视频拆解原因：开头太慢、利益不清、画面不动、字幕不明。",
            "保留高留存结构，连续做 3 条同主题变体测试。",
        ],
        ["3 秒留存", "平均观看时长", "完播率", "重看率"],
        ["Reels 数据", "留存曲线", "完播", "复盘"],
    ),
    strategy(
        "IGS-S8-03",
        "用 Carousel 保存和滑动数据判断实用性",
        "S8",
        ["形成专家感", "提升关注转化率", "增加评论互动"],
        ["Carousel 策略"],
        ["提升专业感", "提升互惠感", "提升持续关注理由"],
        ["HOOTSUITE_INSTAGRAM_RESOURCES", "SPROUT_INSTAGRAM_STRATEGY", "MADE_TO_STICK"],
        "Carousel 的价值常体现在用户愿不愿意滑完、保存、评论和转发给朋友。",
        [
            "记录第一页点击、滑动完成、保存、分享和评论问题。",
            "如果保存高但评论低，补一个更具体的讨论问题。",
            "如果第一页打开低，优先改封面标题和视觉层级。",
        ],
        ["保存率", "滑动完成率", "分享率", "评论率"],
        ["Carousel 数据", "保存率", "滑动", "实用内容"],
    ),
    strategy(
        "IGS-S8-04",
        "把 Stories 分成关系指标复盘",
        "S8",
        ["增加 Story 回复", "开启私信对话", "建立长期关系"],
        ["Story 策略", "私信策略"],
        ["提升参与感", "提升被理解感", "提升持续关注理由"],
        ["HOOTSUITE_INSTAGRAM_RESOURCES", "LATER_INSTAGRAM_GUIDES", "SPROUT_SOCIAL_GUIDES"],
        "Story 的价值不只在观看，更在回复、贴纸互动和转入私信的关系信号。",
        [
            "分别记录观看、下一张、退出、投票、问答、回复和私信承接。",
            "复盘哪类问题最容易让用户说出真实场景。",
            "把高回复 Story 模板化，形成每周栏目。",
        ],
        ["Story 回复率", "贴纸互动率", "退出率", "DM 承接率"],
        ["Story 数据", "关系指标", "回复率", "贴纸互动"],
    ),
    strategy(
        "IGS-S8-05",
        "复盘主页访问到关注转化",
        "S8",
        ["提升主页信任感", "提升关注转化率", "形成专家感"],
        ["Bio 策略", "Highlights 策略", "Carousel 策略"],
        ["降低怀疑感", "提升专业感", "提升安全感"],
        ["HOOTSUITE_INSTAGRAM_RESOURCES", "BUFFER_INSTAGRAM", "HUBSPOT_INSTAGRAM"],
        "触达增加后，如果主页转化低，问题可能在 Bio、置顶、视觉、证据或 CTA。",
        [
            "每周计算主页访问到关注率，并标注来源内容。",
            "当触达高但关注低时，检查来源内容是否与主页承诺一致。",
            "一次只调整一个主页元素，观察 7-14 天后再判断。",
        ],
        ["主页访问到关注率", "来源内容匹配度", "Bio 链接点击率"],
        ["主页转化", "关注率", "Bio 复盘", "来源匹配"],
    ),
    strategy(
        "IGS-S8-06",
        "建立私信转化阶段表",
        "S8",
        ["开启私信对话", "提高后续对话率", "提高福利领取率"],
        ["私信策略", "福利策略"],
        ["提升专业感", "提升安全感", "降低怀疑感"],
        ["CXL_INSTITUTE", "NEVER_SPLIT_DIFFERENCE", "NONVIOLENT_COMMUNICATION"],
        "私信复盘要看用户停在哪个阶段，而不是只看最后有没有成交或报名。",
        [
            "把私信分为开启、诊断、发送价值、处理顾虑、下一步、回访 6 阶段。",
            "记录每阶段转化率和常见流失原因。",
            "针对最大流失阶段优化话术或内容入口。",
        ],
        ["各阶段转化率", "流失原因分布", "回访回复率"],
        ["私信漏斗", "DM 转化", "阶段表", "复盘"],
    ),
    strategy(
        "IGS-S8-07",
        "用福利漏斗评估资源质量",
        "S8",
        ["提高福利领取率", "提高后续对话率", "建立长期关系"],
        ["福利策略", "私信策略"],
        ["提升互惠感", "提升安全感", "提升持续关注理由"],
        ["GOOGLE_SKILLSHOP_DIGITAL_MARKETING", "CXL_INSTITUTE", "CIALDINI_INFLUENCE"],
        "福利不应只追领取数，真正要看用户是否使用、反馈和继续对话。",
        [
            "漏斗记录曝光、评论关键词、发送成功、打开、使用反馈、后续对话。",
            "如果领取高但反馈低，说明福利可能太大、太难或说明不清。",
            "把高反馈福利升级成系列内容或付费入口。",
        ],
        ["福利领取率", "资料打开率", "使用反馈率", "后续对话率"],
        ["福利漏斗", "资料质量", "领取率", "后续对话"],
    ),
    strategy(
        "IGS-S8-08",
        "做钩子 A/B 测试",
        "S8",
        ["增加被看见", "增加评论互动", "形成专家感"],
        ["Reels 策略", "Carousel 策略"],
        ["提升专业感", "提升参与感", "提升持续关注理由"],
        ["CXL_INSTITUTE", "MADE_TO_STICK", "HOOTSUITE_INSTAGRAM_RESOURCES"],
        "内容测试要控制变量；同一个主题换钩子，才能知道是主题弱还是开头弱。",
        [
            "同一主题写 3 种钩子：痛点型、结果型、反常识型。",
            "保持主体内容和发布时间接近，只换开头或封面标题。",
            "用 48 小时数据判断哪个钩子值得做成系列。",
        ],
        ["前 3 秒留存", "封面点击率", "分享率", "评论率"],
        ["A/B 测试", "钩子", "实验", "内容优化"],
    ),
    strategy(
        "IGS-S8-09",
        "每月做来源组合审计",
        "S8",
        ["增加被看见", "建立长期关系", "形成专家感"],
        ["Reels 策略", "Story 策略", "社群策略"],
        ["提升专业感", "提升安全感", "提升持续关注理由"],
        ["SPROUT_INSTAGRAM_STRATEGY", "HOOTSUITE_INSTAGRAM_RESOURCES", "SPROUT_SOCIAL_GUIDES"],
        "增长来自多种来源组合：推荐、搜索、评论、合作、Story 和老粉互动都要被看见。",
        [
            "每月把新增关注按来源内容、搜索、互动、合作、福利和推荐分组。",
            "看哪类来源带来的用户后续互动更高，而不是只看数量。",
            "下一月预算时间优先给高质量来源，而不是盲目追最高曝光。",
        ],
        ["来源新增关注", "来源后续互动率", "来源私信质量"],
        ["来源审计", "增长来源", "复盘", "质量关注"],
    ),
    strategy(
        "IGS-S9-01",
        "建立官方学习路径",
        "S9",
        ["形成专家感", "提升主页信任感", "增加被看见"],
        ["Reels 策略", "Live 策略", "Bio 策略"],
        ["提升专业感", "提升安全感", "提升持续关注理由"],
        ["META_BLUEPRINT", "GOOGLE_SKILLSHOP_DIGITAL_MARKETING", "META_SOCIAL_CERT"],
        "平台基础、数字营销和社媒体系要从官方与系统课程补齐，避免只听碎片经验。",
        [
            "先学 Meta Instagram marketing 和 Google 数字营销基础，再补 Meta 社媒证书。",
            "每学完一个模块，转成一条账号 SOP 或复盘清单。",
            "把学习成果转成内容，但要结合自己的实践，不做搬运式总结。",
        ],
        ["学习模块完成数", "转化为 SOP 的数量", "学习内容带来的互动"],
        ["学习路径", "官方课程", "Meta", "Google Skillshop"],
    ),
    strategy(
        "IGS-S9-02",
        "建立平台更新观察机制",
        "S9",
        ["增加被看见", "形成专家感", "建立长期关系"],
        ["Reels 策略", "Story 策略", "Carousel 策略"],
        ["提升专业感", "提升持续关注理由", "提升安全感"],
        ["INSTAGRAM_BEST_PRACTICES", "HOOTSUITE_INSTAGRAM_RESOURCES", "SPROUT_INSTAGRAM_STRATEGY"],
        "Instagram 的功能、指标和推荐机制会变，策略要定期对齐最新平台信号。",
        [
            "每月查看 Instagram Best Practices、Hootsuite 和 Sprout 的平台更新。",
            "把变化分成必须调整、可以测试、暂不相关三类。",
            "只对自己的账号数据验证有效后，才写入长期 SOP。",
        ],
        ["更新检查次数", "新机制测试数", "测试成功率"],
        ["平台更新", "算法", "Best Practices", "学习提升"],
    ),
    strategy(
        "IGS-S9-03",
        "系统训练视觉生产能力",
        "S9",
        ["提升主页信任感", "形成专家感", "提高福利领取率"],
        ["Carousel 策略", "Story 策略", "福利策略"],
        ["提升专业感", "降低怀疑感", "提升安全感"],
        ["CANVA_SOCIAL_MEDIA_MASTERY", "COURSERA_DIGITAL_MARKETING_CANVA", "HUBSPOT_INSTAGRAM"],
        "视觉不是装饰，而是降低理解成本和提升信任感的运营资产。",
        [
            "建立品牌套件：颜色、字体、按钮、封面、图标和照片风格。",
            "每周复盘 3 个高表现设计，分析信息层级、留白、标题和行动入口。",
            "把福利、Carousel 和 Story 模板化，减少临时设计导致的不一致。",
        ],
        ["模板复用率", "封面点击率", "视觉一致性问题数"],
        ["视觉设计", "Canva", "模板", "品牌一致性"],
    ),
    strategy(
        "IGS-S9-04",
        "训练可复用写作系统",
        "S9",
        ["形成专家感", "增加评论互动", "提升关注转化率"],
        ["Reels 策略", "Carousel 策略", "Bio 策略"],
        ["提升专业感", "提升被理解感", "提升持续关注理由"],
        ["EVERYBODY_WRITES", "MADE_TO_STICK", "HUBSPOT_INSTAGRAM"],
        "稳定内容质量来自写作系统，而不是每次临场找灵感。",
        [
            "为标题、开头、案例、CTA、私信回复各建立 10 个模板。",
            "每条内容发布前做一次删减：删抽象词、删重复句、删无关背景。",
            "把高表现文案拆成结构，沉淀进模板库。",
        ],
        ["文案模板数量", "内容生产时间", "评论和保存率"],
        ["写作系统", "文案模板", "内容写作", "可复用"],
    ),
    strategy(
        "IGS-S9-05",
        "建立说服伦理清单",
        "S9",
        ["提升主页信任感", "建立长期关系", "提高后续对话率"],
        ["私信策略", "福利策略", "Bio 策略"],
        ["提升安全感", "降低怀疑感", "提升互惠感"],
        ["CIALDINI_INFLUENCE", "CIALDINI_PRESUASION", "NONVIOLENT_COMMUNICATION"],
        "说服技巧必须服务用户利益；透明、可选择和不夸大，是长期信任的底线。",
        [
            "每次活动前检查：是否夸大结果、是否隐藏条件、是否制造不必要焦虑。",
            "福利和私信里说明适用对象和不适用对象。",
            "所有紧迫感、社会认同和权威证明都必须真实可解释。",
        ],
        ["用户投诉数", "取消关注率", "信任类反馈"],
        ["说服伦理", "互惠", "预先说服", "安全感"],
    ),
    strategy(
        "IGS-S9-06",
        "练习提问和倾听能力",
        "S9",
        ["开启私信对话", "提高后续对话率", "建立长期关系"],
        ["私信策略", "评论策略", "Story 策略"],
        ["提升被理解感", "提升安全感", "降低陌生感"],
        ["NEVER_SPLIT_DIFFERENCE", "CARNEGIE", "NONVIOLENT_COMMUNICATION"],
        "提问质量决定对话质量，好的运营不是更会说，而是更会听出用户真正的顾虑。",
        [
            "每周复盘 10 段私信，标出哪里过早建议、哪里没有追问。",
            "为常见场景准备开放问题、澄清问题和校准问题。",
            "训练回复前先总结对方意思，再给建议。",
        ],
        ["二次回复率", "用户补充信息量", "私信满意反馈"],
        ["倾听", "提问", "私信训练", "沟通"],
    ),
    strategy(
        "IGS-S9-07",
        "补齐数据实验能力",
        "S9",
        ["增加被看见", "提升关注转化率", "提高福利领取率"],
        ["Reels 策略", "Carousel 策略", "福利策略"],
        ["提升专业感", "提升安全感"],
        ["CXL_INSTITUTE", "GOOGLE_SKILLSHOP_DIGITAL_MARKETING", "SPROUT_SOCIAL_GUIDES"],
        "数据能力不是做复杂报表，而是能提出假设、测试变量、判断是否继续。",
        [
            "每周写一个假设，例如“问题型封面会提高 Carousel 完读”。",
            "明确变量、样本周期和判断指标，避免发布后才找理由。",
            "把实验结论写入内容 SOP，而不是停留在截图收藏。",
        ],
        ["实验完成数", "有效结论数", "SOP 更新数"],
        ["数据实验", "增长", "CXL", "复盘能力"],
    ),
    strategy(
        "IGS-S9-08",
        "建立优秀案例拆解库",
        "S9",
        ["增加被看见", "形成专家感", "提升主页信任感"],
        ["Reels 策略", "Carousel 策略", "Story 策略"],
        ["提升专业感", "提升持续关注理由", "提升真实感"],
        ["HUBSPOT_INSTAGRAM", "BUFFER_INSTAGRAM", "SPROUT_INSTAGRAM_STRATEGY"],
        "拆解不是模仿外壳，而是学习别人如何组织受众、信息、证据和行动。",
        [
            "每周拆 5 条同领域和跨领域内容，记录钩子、结构、证据、CTA、视觉。",
            "只提炼结构，不复制具体表达和创意资产。",
            "把可迁移结构放入选题库，用自己的用户语言重写。",
        ],
        ["案例拆解数", "迁移后内容表现", "原创度审查通过率"],
        ["案例拆解", "swipe file", "内容学习", "结构"],
    ),
    strategy(
        "IGS-S9-09",
        "季度更新完整 Instagram 策略",
        "S9",
        ["建立长期关系", "形成专家感", "增加被看见"],
        ["Bio 策略", "Reels 策略", "社群策略"],
        ["提升专业感", "提升持续关注理由", "提升安全感"],
        ["SPROUT_INSTAGRAM_STRATEGY", "HOOTSUITE_INSTAGRAM_RESOURCES", "THIS_IS_MARKETING"],
        "策略不是一次性文件；用户、平台和业务目标变化后，需要回到定位和数据重新选择。",
        [
            "每季度复盘定位、内容支柱、主页、福利、互动、私信和数据。",
            "保留有效资产，停止低质量高消耗动作。",
            "为下一季度设置一个主目标、两个辅助目标和三项关键实验。",
        ],
        ["季度目标达成率", "停止动作数量", "关键实验完成率"],
        ["季度复盘", "策略更新", "Instagram 策略", "长期运营"],
    ),
]


SUPPLEMENTAL_STAGE_PLANS = {
    "S1": {
        "sources": ["THIS_IS_MARKETING", "GOOGLE_SKILLSHOP_DIGITAL_MARKETING", "CXL_INSTITUTE", "HBR_BETTER_LISTENER", "CNVC_FEELINGS_NEEDS"],
        "goals": [["提升关注转化率", "形成专家感"], ["开启私信对话", "提升主页信任感"], ["增加评论互动", "建立长期关系"]],
        "formats": [["Bio 策略", "社群策略"], ["Story 策略", "私信策略"], ["Carousel 策略", "评论策略"]],
        "psychology": [["提升被理解感", "降低陌生感"], ["提升安全感", "降低怀疑感"], ["提升参与感", "提升持续关注理由"]],
        "items": [
            ("新粉来源画像", "新关注来自 Reels 推荐、搜索、评论区或朋友转发时", "在用户记录里标注来源，并为每个来源写一句不同的欢迎语"),
            ("三层痛点地图", "用户表达的问题停留在表面症状时", "把痛点拆成外显问题、隐藏焦虑、真正想要的结果"),
            ("反画像排除", "账号想服务所有人导致表达发散时", "写清楚不服务谁、不解决什么问题、不承诺什么结果"),
            ("小众人群用语扫描", "文案听起来像品牌自嗨时", "从评论、私信和竞品评论区收集 30 句用户原话"),
            ("购买动机四象限", "福利或产品吸引到大量低意向用户时", "按省时间、省钱、被认可、少犯错四类标注动机"),
            ("内容成熟度分层", "同一条教程让新手看不懂、高手嫌浅时", "把用户分为入门、执行、优化、放大四层并分别写选题"),
            ("常见误解标签", "用户反复问同一个基础误解时", "为误解建标签并做成 FAQ、置顶帖和私信快捷回复"),
            ("关键人生事件入口", "目标用户只有模糊画像时", "找出他们最可能需要你的三个事件节点并围绕节点写内容"),
            ("关注前疑虑清单", "主页访问多但关注少时", "列出用户关注前的五个担心并逐一放到 Bio、置顶和 Highlight"),
            ("同温层账号列表", "主动互动不知道去哪找人时", "建立 50 个受众重合账号清单，按互动质量排序"),
            ("竞品评论高频词", "选题靠猜导致命中率不稳时", "每周抓取竞品评论中的高频名词、动词和情绪词"),
            ("私信意图分类", "私信多但后续对话质量参差时", "把私信分成求资料、求建议、求证明、求报价、求安慰五类"),
            ("用户成功定义", "内容指标好但用户不知道下一步价值时", "让用户用自己的话定义什么叫成功，再反写内容承诺"),
            ("禁忌话题边界", "账号容易引发无效争议时", "列出不公开讨论、只私下讨论、可以公开教育的边界"),
            ("低门槛行动能力评估", "CTA 过大导致用户不行动时", "判断目标用户现在能否完成评论、保存、私信、填写表单四种动作"),
            ("受众作息窗口", "发布时间只按通用建议时", "用 Story 投票和 Insights 找到目标用户真实在线情境"),
            ("本地/全球语境拆分", "内容同时面向本地客户和全球受众时", "把地理位置、语言、价格、案例证据分开表达"),
            ("预算敏感度分层", "用户一问价格就消失时", "把受众按免费探索、低价试用、正式购买、长期合作分层"),
            ("角色冲突卡", "用户想行动但一直拖延时", "记录他同时扮演的身份冲突，例如妈妈、创业者、员工、学习者"),
            ("触发物列表", "内容缺少可持续记忆点时", "列出用户每天会遇到的触发物，并把内容绑定到这些场景"),
            ("用户自称词库", "账号称呼让用户觉得被标签化时", "记录用户如何称呼自己，而不是团队替他们命名"),
            ("目标用户一句话测试", "定位句写完但不确定是否清楚时", "把定位发给 5 个陌生人，看他们能否复述你服务谁"),
            ("从 0 到 1 路径图", "新手用户不知道先做什么时", "画出从第一次看见到第一次完成任务的 6 个微步骤"),
            ("用户变化证明点", "案例讲得像炫耀时", "把证明点改成用户前后变化、过程证据和仍需努力的部分"),
        ],
    },
    "S2": {
        "sources": ["HUBSPOT_INSTAGRAM", "BUFFER_INSTAGRAM", "STORYBRAND", "CANVA_SOCIAL_MEDIA_MASTERY", "CRUCIAL_MAKE_IT_SAFE"],
        "goals": [["提升主页信任感", "提升关注转化率"], ["开启私信对话", "提高福利领取率"], ["形成专家感", "增加被看见"]],
        "formats": [["Bio 策略"], ["Highlights 策略", "Bio 策略"], ["Carousel 策略", "Highlights 策略"]],
        "psychology": [["降低陌生感", "提升专业感"], ["降低怀疑感", "提升安全感"], ["提升真实感", "提升持续关注理由"]],
        "items": [
            ("Bio 第一行人群锁定", "用户点进主页 3 秒内无法判断是否相关时", "第一行只写具体服务对象，不写抽象愿景"),
            ("Name 字段关键词化", "账号搜索曝光弱时", "把用户会搜索的品类词放进名称字段"),
            ("头像眼神信任测试", "个人品牌头像识别度弱时", "用正脸、清晰背景和统一色调替代复杂图形"),
            ("主页三证据顺序", "主页显得专业但不可信时", "按资格证据、过程证据、用户反馈的顺序排列信息"),
            ("置顶帖行动导览", "新访客看完置顶仍不知道下一步时", "每条置顶帖结尾指向一个明确动作"),
            ("Highlight 首屏命名", "Highlight 名称像内部文件夹时", "改成用户能理解的利益名称，如先看这里、案例、免费资源"),
            ("FAQ 防御性问题前置", "私信反复出现担心和质疑时", "把价格、时间、适用人群、隐私和结果边界放进 FAQ"),
            ("链接页三入口限制", "Bio 链接页选择过载时", "只保留入门资源、预约/咨询、案例证明三个入口"),
            ("无压力 CTA", "主页 CTA 像强推销售时", "用可以、如果需要、先看这个替代立刻报名"),
            ("联系方式一致性", "用户在主页和私信之间迷路时", "统一邮箱、表单、DM 关键词和预约入口名称"),
            ("九宫格首屏检查", "主页第一屏内容互相打架时", "让前 9 条至少覆盖身份、价值、案例、教程和互动"),
            ("Reels 封面标题区", "Reels 缩略图在主页看不懂时", "把封面标题限制在 8-12 个字并固定位置"),
            ("视觉模板风险审计", "视觉好看但信息不清时", "检查标题层级、对比度、字号和按钮是否被装饰淹没"),
            ("主页自我介绍短视频", "Bio 文字不够建立人感时", "置顶一条 30 秒自我介绍 Reel，讲对象、问题和方法"),
            ("案例 Highlight 边界说明", "用户担心案例不可复制时", "每个案例说明背景、投入、限制和下一步"),
            ("本地信任元素", "服务有地域属性但主页没有本地感时", "加入城市、线下场景、当地案例或语言习惯"),
            ("服务菜单轻量化", "用户不知道你具体能提供什么时", "用 3 个服务场景替代完整复杂产品页"),
            ("个人故事压缩", "主页故事太长抢走价值判断时", "把个人故事压缩为一句转折和一句为什么能帮你"),
            ("隐私承诺可见化", "用户不敢私信真实问题时", "在 FAQ 或 Highlight 写明截图、案例和信息使用边界"),
            ("免费资源门牌", "福利分散在旧帖里找不到时", "在主页放一个固定免费资源 Highlight"),
            ("新访客路线图", "主页内容资产多但没有路径时", "用 Start Here 说明先看哪三条内容"),
            ("品牌语气样本", "主页文字风格前后不一致时", "固定 5 句代表账号语气的样本文案"),
            ("证书和经验翻译", "资历看起来像自我炫耀时", "把证书翻译成用户能获得的具体好处"),
            ("安全区视觉检查", "Reels 广告或封面被按钮遮挡时", "所有关键信息避开底部、右侧按钮和顶部头像区域"),
        ],
    },
    "S3": {
        "sources": ["HOOTSUITE_ALGORITHM_2026", "HOOTSUITE_REELS_2026", "HOOTSUITE_CAROUSEL_2025", "META_REELS_ADS", "INSTAGRAM_REELS_ADS_HELP", "LATER_STORIES_CAMPAIGN", "MADE_TO_STICK"],
        "goals": [["增加被看见", "形成专家感"], ["增加评论互动", "提升关注转化率"], ["增加 Story 回复", "开启私信对话"]],
        "formats": [["Reels 策略"], ["Carousel 策略"], ["Story 策略"], ["Live 策略", "Reels 策略"]],
        "psychology": [["提升参与感", "提升持续关注理由"], ["提升专业感", "提升互惠感"], ["提升真实感", "降低陌生感"]],
        "items": [
            ("1.5 秒画面动作钩子", "用户还没读完标题就划走时", "第一秒放动作、表情或结果画面，再补字幕解释"),
            ("Reels 安全区字幕", "字幕被按钮、用户名或说明遮挡时", "把核心字幕放在画面中上部并预览实际发布界面"),
            ("无声也能懂的 Reels", "受众常在通勤、带娃或办公间隙刷内容时", "用字幕、手势、物品和画面顺序让静音也能看懂"),
            ("循环结尾", "Reels 完播不错但重看弱时", "让最后一句接回第一句或最后画面接回开头画面"),
            ("创作者脸部开场", "账号缺少人感时", "每周至少一条 Reel 用真人开场讲具体场景"),
            ("幕后三镜头", "幕后内容流水账时", "用准备、卡住、解决三个镜头讲清过程"),
            ("产品/服务一镜到底", "演示内容显得过度包装时", "用不剪或少剪的短片展示真实操作流程"),
            ("反常识标题", "教程内容被同质化淹没时", "用一个违背常识的判断开头，再马上给理由"),
            ("错误纠正型 Reel", "用户常犯同一类错时", "先展示错误做法，再给替换动作和判断标准"),
            ("客户问题口播", "选题不知道怎么贴近用户时", "直接用一条真实问题作为开场"),
            ("UGC 反应剪辑", "品牌说服力不足时", "把用户使用前疑虑、使用中反应、使用后反馈剪成一条"),
            ("Founder POV", "品牌太像机构缺少人格时", "用创始人视角讲一次真实选择和取舍"),
            ("趋势音频过滤", "追热点导致账号定位变散时", "只选能自然表达用户场景的音频，不为音频改变定位"),
            ("Reels 封面 A/B", "内容播放好但主页点击弱时", "同主题测试人物封面、结果封面、问题封面"),
            ("Carousel 第一页单承诺", "第一页塞太多信息导致滑动低时", "第一页只写一个承诺或一个痛点"),
            ("每页一个 aha", "Carousel 滑到中间掉点时", "每页只放一个可独立保存的发现"),
            ("决策树 Carousel", "用户需要判断自己该不该行动时", "用如果/那么结构帮用户做选择"),
            ("清单式 Carousel", "用户想收藏但内容难执行时", "把步骤改成可勾选清单"),
            ("误区对照 Carousel", "评论区反复争论概念时", "一页误区、一页替代说法、一页例子"),
            ("案例拆解 Carousel", "案例内容像成果炫耀时", "按背景、动作、变化、限制拆解"),
            ("反对意见 Carousel", "用户看完仍有顾虑时", "一页一个顾虑，并给具体证据或边界"),
            ("Story 三帧小剧场", "Story 看完率低时", "用问题、转折、邀请三帧完成一个小闭环"),
            ("投票阶梯", "Story 投票只有表态没有后续时", "第一票问现状，第二票问阻碍，第三票引导 DM"),
            ("开放问题限缩", "问答框无人回答时", "把你有什么问题改成 A/B/C 哪个最卡"),
            ("Story 证据碎片", "案例太正式不适合天天发时", "把截图、过程、反馈、复盘拆成日常证据"),
            ("Live 开场 60 秒承诺", "直播开头流失快时", "开场先说今天解决什么、不解决什么、适合谁"),
            ("Live 问题停车场", "直播被零散问题打断时", "把非主题问题放进停车场，结尾集中答"),
            ("直播回放切片", "Live 做完就沉没时", "剪成 3 条 Reel、1 条 Carousel 和 1 个 FAQ"),
            ("数据故事化", "数据内容枯燥难传播时", "把数字放进用户前后对比场景里讲"),
            ("保存型结尾", "内容有价值但保存低时", "结尾明确告诉用户何时会用到它，并提醒保存"),
        ],
    },
    "S4": {
        "sources": ["SPROUT_INSTAGRAM_ENGAGEMENT_CASE", "SPROUT_CASE_STUDIES", "CARNEGIE", "GREATER_GOOD_LISTENING", "HOOTSUITE_ALGORITHM_2026"],
        "goals": [["增加被看见", "增加评论互动"], ["开启私信对话", "建立长期关系"], ["提升主页信任感", "形成专家感"]],
        "formats": [["评论策略"], ["Story 策略", "私信策略"], ["社群策略", "Reels 策略"]],
        "psychology": [["降低陌生感", "提升参与感"], ["提升被理解感", "提升安全感"], ["提升专业感", "提升真实感"]],
        "items": [
            ("评论前 10 秒判断", "准备在同行内容下互动时", "先判断自己能否补充信息、共鸣或提问，不能就不评论"),
            ("补充型评论", "想被相关受众看见但不想硬广时", "用一个具体例子补充原帖观点"),
            ("经验型评论", "同领域用户讨论真实问题时", "分享一次真实踩坑和一个可执行建议"),
            ("提问型评论", "想开启对话但不抢主题时", "问一个能让原作者继续展开的问题"),
            ("评论串延长", "自己的内容有评论但很快结束时", "每次回复只追问一个具体细节"),
            ("置顶评论补入口", "帖文 CTA 不够醒目时", "把补充资源、问题或关键词放进置顶评论"),
            ("品牌关键词巡逻", "用户提到你但没有 tag 时", "每周搜品牌名、产品名、错别字和相关关键词"),
            ("UGC 感谢顺序", "用户自发分享内容时", "先感谢、再请求授权、再说明会如何使用"),
            ("相邻行业串联", "只在同行圈互动导致增长慢时", "进入用户上游和下游行业账号评论区"),
            ("位置标签互动", "本地业务需要真实附近用户时", "每天查看本地位置标签下的最新内容并真诚互动"),
            ("小账号优先", "大号评论区互动太拥挤时", "优先回复小而活跃账号的高质量内容"),
            ("Story mention 回礼", "用户在 Story 提到你时", "二次转发时补一句对用户有价值的观察"),
            ("合作账号预热", "直接邀约合作回复率低时", "先连续两周参与对方内容，再提出轻合作"),
            ("评论区 FAQ 收集", "同一个问题出现三次以上时", "把它转为 FAQ、Carousel 或下一场 Live"),
            ("分歧降温回应", "评论区出现不同意见时", "先指出共同目标，再回应具体差异"),
            ("高意向评论转私信", "评论暴露具体需求时", "公开简短回复，再询问是否可以私信给具体资料"),
            ("粉丝互相连接", "评论区有用户能互相帮助时", "用点名方式让两位用户看见彼此经验"),
            ("创作者名单分层", "想做 UGC 或合作但名单混乱时", "按受众匹配、内容质量、互动真实性三项评分"),
            ("轻量共创邀请", "合作门槛太高时", "先邀对方提供一句观点、一张截图或一个问题"),
            ("评论后主页检查", "外部评论带来访问但不关注时", "确保评论内容与主页置顶承诺一致"),
            ("社群问题接龙", "粉丝只看不说时", "用一个固定句式让用户接龙当前状态"),
            ("反垃圾互动规则", "自动化互动损害信任时", "禁止复制粘贴式夸奖，只保留具体回应"),
            ("客户服务公开承接", "公开评论提出售后或投诉时", "先公开确认收到，再转私信处理细节"),
            ("互动复盘标签", "主动互动做了但不知道有效性时", "为每次外部互动标注主页访问、回复、互关或私信结果"),
        ],
    },
    "S5": {
        "sources": ["MINDTOOLS_ACTIVE_LISTENING", "CNVC_FEELINGS_NEEDS", "CRUCIAL_CONVERSATIONS", "CRUCIAL_MAKE_IT_SAFE", "NEVER_SPLIT_DIFFERENCE", "GOLEMAN_EQ"],
        "goals": [["开启私信对话", "提高后续对话率"], ["提升主页信任感", "建立长期关系"], ["提高福利领取率", "增加 Story 回复"]],
        "formats": [["私信策略"], ["私信策略", "福利策略"], ["Story 策略", "私信策略"]],
        "psychology": [["提升安全感", "降低陌生感"], ["提升被理解感", "降低怀疑感"], ["提升互惠感", "提升真实感"]],
        "items": [
            ("许可式第一句", "用户评论关键词或回复 Story 后", "先问是否可以根据他的情况给一个建议"),
            ("复述再建议", "用户描述问题但你已经想给答案时", "先用一句话复述对方处境，再给建议"),
            ("情绪命名", "用户表达焦虑、犹豫或不确定时", "用听起来你有点担心/卡住/纠结来承接"),
            ("需求猜测", "用户只说我不知道怎么办时", "轻轻猜测他可能需要清晰步骤、时间确定性或安全感"),
            ("澄清问题三选一", "开放问题让用户不知道怎么答时", "给三个选项让用户选最贴近的情况"),
            ("延迟长方案", "用户刚开口就想要完整方案时", "先问目标、限制和已尝试动作，再发方案"),
            ("对比声明", "对方觉得你在推销或评判时", "说明我不是想逼你决定，我是想帮你判断是否适合"),
            ("共同目的重建", "对话开始跑偏或防御时", "回到共同目标：让你少踩坑、先看清下一步"),
            ("低风险下一步", "用户还没准备好购买或报名时", "给一个免费检查、案例阅读或 10 分钟动作"),
            ("一句一问", "私信回复太长导致对方沉默时", "每轮最多一个建议加一个问题"),
            ("已读未回轻提醒", "用户领取资料后没有反馈时", "48 小时后只问是否卡在某一步，不催促"),
            ("退出权声明", "对话可能让用户有压力时", "明确说不适合也没关系，你可以先收藏慢慢看"),
            ("截图授权", "想把用户反馈用于案例时", "先问是否可以匿名使用，再说明用途和可撤回"),
            ("价格异议拆分", "用户说太贵时", "区分预算不足、价值不清、风险太高和时机不对"),
            ("时间异议拆分", "用户说没时间时", "问他能接受 5 分钟、15 分钟还是每周一次的动作"),
            ("结果异议承接", "用户担心做了没用时", "提供可验证的小实验，而不是保证结果"),
            ("边界清楚", "用户把私信当免费无限咨询时", "给一次小建议，并说明更深诊断需要预约或服务"),
            ("语音消息克制", "关系还不熟时想发语音时", "先问对方是否方便听语音，避免增加负担"),
            ("表情降温", "文字看起来太硬时", "少量使用表情软化语气，但不替代实质回应"),
            ("镜像关键词", "用户反复使用一个词时", "原样引用那个词并请他解释具体含义"),
            ("校准问题", "用户想要方案但目标模糊时", "问怎样做会让你觉得这次对话是有帮助的"),
            ("反问转共情", "用户语气强硬或质疑时", "先回应背后担心，再答事实问题"),
            ("福利后反馈钩", "资料已经发送完时", "问你准备用它改哪一部分，我可以帮你看方向"),
            ("私信标签化", "对话多到难以跟进时", "给用户打上阶段、需求、顾虑和已发资料标签"),
            ("高情商暂停", "自己急着证明或反驳时", "先停 10 秒，确认自己是在帮用户还是在保护面子"),
            ("冲突不公开升级", "评论区争议延伸到私信时", "承认对方感受并把事实核对放在私下完成"),
            ("感谢具体化", "用户给反馈或拒绝时", "感谢他具体说出的时间、担心或真实想法"),
            ("二次价值回访", "用户曾表达明确目标但暂未行动时", "一周后发送一个与他目标相关的新资源"),
            ("转介绍询问", "用户明确满意但暂不购买时", "询问他是否认识也卡在同类问题的人"),
            ("对话结束摘要", "私信聊得很长时", "用三点总结用户现状、建议动作和约定下一步"),
        ],
    },
    "S6": {
        "sources": ["CIALDINI_INFLUENCE", "CXL_INSTITUTE", "LATER_STORIES_CAMPAIGN", "CANVA_SOCIAL_MEDIA_MASTERY", "META_REELS_ADS"],
        "goals": [["提高福利领取率", "提高后续对话率"], ["开启私信对话", "提升关注转化率"], ["提升主页信任感", "建立长期关系"]],
        "formats": [["福利策略"], ["福利策略", "私信策略"], ["Story 策略", "福利策略"], ["Carousel 策略", "福利策略"]],
        "psychology": [["提升互惠感", "提升安全感"], ["提升专业感", "降低怀疑感"], ["提升参与感", "提升持续关注理由"]],
        "items": [
            ("10 分钟小胜利福利", "资料太大导致用户不使用时", "把福利缩成 10 分钟内能完成的一步"),
            ("阶段匹配福利", "新手和进阶用户领取同一资料效果差时", "为入门、执行、优化三个阶段分别设计资源"),
            ("检查表福利", "教程内容收藏多但行动少时", "把教程变成可勾选检查表"),
            ("脚本库福利", "用户卡在表达而不是理解时", "提供评论、私信、Story 的可改写话术"),
            ("诊断模板福利", "用户不知道问题出在哪时", "提供自评问题而不是直接给答案"),
            ("案例拆解福利", "用户需要信任证据时", "把一个真实案例拆成背景、动作、指标、限制"),
            ("Story 测验福利", "福利预热冷淡时", "先用测验让用户发现自己的缺口，再给资源"),
            ("DM 关键词福利", "链接点击低但评论热情高时", "用一个关键词把领取入口放回 Instagram 内"),
            ("直播加餐福利", "Live 后关系断掉时", "直播结束发讲义、清单或回放重点"),
            ("内容升级福利", "公开内容有明显未展开部分时", "只把更完整模板提供给真正需要的人"),
            ("资源包分层", "一个大资源包让用户选择困难时", "按目标拆成入门包、转化包、复盘包"),
            ("挑战型福利", "用户需要陪伴而不是资料时", "设计 3 天或 5 天的小挑战"),
            ("免费微诊断", "高意向用户需要证明你的判断力时", "提供一次范围明确的微诊断"),
            ("办公时间福利", "用户问题高度个性化时", "固定每周 30 分钟回答领取者问题"),
            ("感谢页下一步", "福利领取完没有后续动作时", "感谢页只放一个反馈问题或一个相关案例"),
            ("福利适用边界", "领取者期待过高时", "清楚写明适合谁、不适合谁、不能保证什么"),
            ("福利反馈收集", "不知道资料是否真的有用时", "领取 48 小时后问完成了哪一步"),
            ("福利使用证明", "潜在用户怀疑资源质量时", "展示匿名使用反馈和前后变化"),
            ("福利视觉模板", "资料看起来廉价影响信任时", "用统一封面、页眉、编号和行动区"),
            ("福利再利用", "福利只发一次就沉没时", "把资源拆回 3 条 Reel、1 条 Carousel、1 场 Live"),
            ("付费入口软承接", "福利用户已经完成小胜利时", "只在反馈后提供更深服务选项"),
        ],
    },
    "S7": {
        "sources": ["SPROUT_CASE_STUDIES", "CARNEGIE", "SHOW_YOUR_WORK", "GREATER_GOOD_LISTENING", "SPROUT_SOCIAL_GUIDES"],
        "goals": [["建立长期关系", "增加 Story 回复"], ["提升主页信任感", "形成专家感"], ["提高后续对话率", "增加评论互动"]],
        "formats": [["社群策略"], ["Story 策略", "社群策略"], ["私信策略", "评论策略"], ["Highlights 策略", "社群策略"]],
        "psychology": [["提升参与感", "提升持续关注理由"], ["提升真实感", "降低陌生感"], ["提升被理解感", "提升安全感"]],
        "items": [
            ("周一目标仪式", "社群缺少固定参与节奏时", "每周一让用户用一句话写本周目标"),
            ("周五复盘仪式", "用户行动后没有回流时", "每周五邀请用户分享完成、卡住和下周调整"),
            ("成员称呼", "粉丝关系松散时", "为社群成员设置自然、不幼稚的共同称呼"),
            ("高质量用户置顶", "贡献用户没有被看见时", "每周公开感谢一个提供真实问题或反馈的人"),
            ("用户成功墙", "成果分散在私信里时", "获得许可后把用户小胜利沉淀到 Highlight"),
            ("旧内容路线", "新粉追不上旧内容时", "每月把旧内容整理成一条新手路线"),
            ("沉默用户唤醒", "老粉开始只看不互动时", "用你最近还卡在这里吗这种轻问句重新连接"),
            ("社群规范", "评论区和私信边界模糊时", "写明欢迎的问题、不欢迎的行为和处理方式"),
            ("共同词汇", "社群没有记忆点时", "把常见方法命名成固定短词并反复使用"),
            ("用户故事追踪", "案例只展示一次就结束时", "30 天后回访用户变化并更新故事"),
            ("月度公开复盘", "账号长期运营缺少透明感时", "公开分享本月学到的用户洞察和下月调整"),
            ("主题月", "内容日历散乱时", "每月围绕一个主题连续做教程、故事、Live 和福利"),
            ("合作日历", "合作靠临时灵感时", "每月安排一个相邻账号共创主题"),
            ("社群聆听小时", "运营只发布不倾听时", "固定一小时只读评论、回复和用户内容，不发新内容"),
            ("冲突修复模板", "出现误解后关系受损时", "公开澄清意图、承认影响、说明后续调整"),
            ("贡献者标签", "用户愿意帮忙但没有身份感时", "给经常反馈和分享的人设置贡献者标签"),
            ("私信长期档案", "关系无法延续到下一次对话时", "记录用户关键节点、偏好和上次约定"),
            ("线下/线上桥接", "真实关系只停留在屏幕里时", "为高信任用户设计直播、工作坊或小群活动"),
            ("节日关怀内容", "节日内容只剩促销时", "用问候、故事和轻资源维护关系"),
            ("取消关注复盘", "粉丝增长但留存不稳时", "每月复盘取消关注高峰对应的内容和频率"),
            ("长期承诺声明", "用户不知道为什么持续关注你时", "明确告诉用户未来 90 天会持续提供什么"),
        ],
    },
    "S8": {
        "sources": ["CXL_INSTITUTE", "GOOGLE_SKILLSHOP_DIGITAL_MARKETING", "HOOTSUITE_STATS_2026", "HOOTSUITE_ALGORITHM_2026", "SPROUT_INSTAGRAM_STRATEGY"],
        "goals": [["增加被看见", "提升关注转化率"], ["提高福利领取率", "提高后续对话率"], ["建立长期关系", "形成专家感"]],
        "formats": [["Reels 策略"], ["Carousel 策略"], ["Story 策略"], ["私信策略", "福利策略"], ["社群策略"]],
        "psychology": [["提升专业感", "提升安全感"], ["提升参与感", "提升互惠感"], ["提升持续关注理由", "提升被理解感"]],
        "items": [
            ("反虚荣仪表盘", "团队只看播放量和点赞时", "把保存、分享、主页访问、私信和领取放进核心看板"),
            ("来源质量评分", "新增关注很多但互动弱时", "按 7 日内互动、私信、福利使用给来源评分"),
            ("Reels 前 3 秒流失表", "短视频播放不稳定时", "记录每条前 3 秒钩子类型和留存"),
            ("Carousel 页码掉点", "滑动完成率低时", "记录用户从第几页开始掉点并修改那一页信息密度"),
            ("Story 退出点", "Story 发很多但回复少时", "记录退出发生在铺垫、价值、CTA 哪一帧"),
            ("私信阶段漏斗", "私信多但转化低时", "按开启、诊断、建议、异议、下一步、回访统计"),
            ("福利使用率", "领取数漂亮但业务没动时", "追踪打开、完成、反馈和二次对话"),
            ("主题热力图", "不知道哪些内容支柱值得加码时", "按主题统计触达、保存、评论、私信四项"),
            ("钩子实验日志", "改标题没有沉淀经验时", "记录钩子类型、样本、结果和下一步结论"),
            ("创意疲劳提醒", "同一模板表现下滑时", "连续三次低于均值就更换开头、画面或结构"),
            ("发布时间个体化", "使用通用最佳发布时间时", "只用自己账号最近 60 天数据判断发布时间"),
            ("UGC 内容表现", "用户内容是否值得复用不清楚时", "单独统计 UGC 的保存、分享、信任私信和授权率"),
            ("付费放大资格", "广告预算放大低质量内容时", "只有有机保存、分享或私信超过均值的内容才测试广告"),
            ("领先/滞后指标", "只到月底才发现问题时", "把发帖完成率、回复速度作为领先指标，销售/咨询作为滞后指标"),
            ("评论情绪标签", "评论数量多但不知道情绪方向时", "标注感谢、困惑、质疑、求助、反对五类"),
            ("客服响应时间", "评论和私信影响信任时", "记录首次响应时间和问题解决时间"),
            ("内容债务清单", "旧内容持续误导新用户时", "每月找出需要更新、删除或重新包装的内容"),
            ("实验最小样本", "一次失败就放弃策略时", "每个实验至少做 3 条内容或 7 天 Story 再判断"),
            ("行业基准谨慎使用", "外部平均数让团队焦虑时", "只把行业基准当方向，决策看自己历史均值"),
            ("复盘会议三问", "复盘变成罗列数据时", "每次只问什么有效、为什么有效、下次改什么"),
            ("停做清单", "动作很多但注意力分散时", "每月列出三个低收益高消耗动作并暂停"),
            ("高意向行为权重", "点赞多但咨询少时", "给保存、分享、评论问题、Story 回复、DM 不同权重"),
            ("转化路径回放", "用户从看见到私信路径不清时", "回看高质量私信用户之前看过和互动过的内容"),
            ("学习结论入库", "复盘结论散落在聊天记录时", "把有效结论写回策略卡关键词和执行动作"),
        ],
    },
    "S9": {
        "sources": ["META_SOCIAL_CERT", "GOLEMAN_EQ", "CRUCIAL_CONVERSATIONS", "HBR_BETTER_LISTENER", "LATER_CASE_STUDIES", "SPROUT_CASE_STUDIES", "CXL_INSTITUTE"],
        "goals": [["形成专家感", "提升主页信任感"], ["建立长期关系", "提高后续对话率"], ["增加被看见", "提升关注转化率"]],
        "formats": [["Reels 策略", "Carousel 策略"], ["私信策略", "评论策略"], ["社群策略", "Story 策略"], ["福利策略", "Bio 策略"]],
        "psychology": [["提升专业感", "提升安全感"], ["提升被理解感", "降低陌生感"], ["提升持续关注理由", "提升真实感"]],
        "items": [
            ("每周官方更新阅读", "平台功能和规则变化快时", "固定阅读官方和可信行业资料并记录可测试项"),
            ("沟通复盘日记", "私信中容易急着证明自己时", "记录触发情绪、当时回应和更好的替代回应"),
            ("NVC 句式练习", "回复容易像评判或说教时", "每天把一个用户问题改写成观察、感受、需要、请求"),
            ("主动倾听训练", "对话里总想立刻给建议时", "练习复述、澄清、总结后再建议"),
            ("关键对话脚本库", "遇到质疑、拒绝、投诉时临场慌乱时", "为高风险场景准备对比声明和共同目的句"),
            ("案例拆解会", "看案例只看结果数字时", "拆解目标、受众、创意、证据、渠道和复用方式"),
            ("UGC 审美训练", "UGC 内容不是太假就是太乱时", "收集真实但清晰的 UGC 样本并总结结构"),
            ("视觉层级练习", "设计模板越来越花时", "每周重做一张旧封面，只优化标题、留白和对比"),
            ("广告规格学习", "内容准备投放时频繁返工时", "学习竖屏、安全区、音乐授权和目标设置"),
            ("数据假设训练", "复盘只描述现象时", "每周写一个可证伪假设并设计最小实验"),
            ("用户访谈练习", "用户画像来自猜测时", "每月访谈 5 个真实用户并更新语言库"),
            ("创作者合作学习", "找达人只看粉丝量时", "学习用受众匹配、内容质量、历史互动和交付稳定性筛选"),
            ("客服表达训练", "评论区负面反馈影响心态时", "练习确认事实、承认影响、给下一步三段式"),
            ("伦理边界复训", "增长技巧可能变成操控时", "每月检查稀缺、权威、社会认同是否真实透明"),
            ("跨行业灵感库", "同领域内容同质化时", "拆解教育、餐饮、美妆、SaaS、亲子等行业表达结构"),
            ("专家主题论文", "账号观点不稳定时", "每季度写一份 1000 字主题判断并拆成内容"),
            ("知识图谱维护", "策略越来越多难以查询时", "每次新增策略都补阶段、目标、形式、心理和关联边"),
            ("团队话术校准", "多人运营导致语气不一致时", "每月用 10 段评论/私信做语气校准"),
            ("失败案例库", "只记录成功导致误判时", "保存低表现内容、失败原因和下次避免动作"),
            ("技能路线图", "学习资料很多但没有优先级时", "按平台、内容、沟通、数据、设计五条线排季度学习"),
            ("季度策略答辩", "策略更新流于形式时", "用数据、用户反馈和案例证据解释下季度为什么这样做"),
        ],
    },
}


def build_supplemental_strategies() -> list[dict]:
    stage_frames = {
        "S1": "定位要落到用户语言、情境和行动能力，而不是只写年龄、职业或兴趣",
        "S2": "主页要承担陌生人判断风险的任务，每个元素都应该减少一个疑虑",
        "S3": "内容要为具体入口设计：Reels 抢注意、Carousel 承载理解、Story 促成回应",
        "S4": "主动互动的目的不是刷存在感，而是在相关语境里留下可信贡献",
        "S5": "私信的关键是让用户持续感到有选择、有被理解、有下一步",
        "S6": "福利要制造可完成的小胜利，而不是堆砌看似丰富的资料",
        "S7": "长期关系靠固定节奏、用户参与和真实回访，而不是偶尔热闹",
        "S8": "复盘要找到可改变的动作变量，而不是只记录漂亮或难看的数字",
        "S9": "学习提升要转成 SOP、模板和实验，不停留在收藏资料",
    }
    stage_requirements = {
        "S1": "沉淀到用户画像、语言库或选题库里，并在下一轮内容中使用。",
        "S2": "同步更新 Bio、置顶帖、Highlight 或链接页，避免主页信息断层。",
        "S3": "至少做 3 个同主题变体，用留存、保存、回复或分享判断是否保留。",
        "S4": "记录互动对象、上下文和结果，保留能带来真实关系的入口。",
        "S5": "每轮只推进一个问题或一个动作，保留用户拒绝和暂停的空间。",
        "S6": "把领取、打开、完成、反馈和二次对话都记录下来。",
        "S7": "把动作固定到周/月节奏里，并明确谁负责回访和沉淀。",
        "S8": "写下假设、变量、样本周期和下一步决定，避免凭感觉复盘。",
        "S9": "把学习结论写回模板、话术、检查表或图谱关系里。",
    }
    generated: list[dict] = []
    for stage_id, plan in SUPPLEMENTAL_STAGE_PLANS.items():
        for index, (title, trigger, move) in enumerate(plan["items"], 1):
            goals = plan["goals"][(index - 1) % len(plan["goals"])]
            formats = plan["formats"][(index - 1) % len(plan["formats"])]
            psychology = plan["psychology"][(index - 1) % len(plan["psychology"])]
            sources = [
                plan["sources"][(index - 1) % len(plan["sources"])],
                plan["sources"][index % len(plan["sources"])],
            ]
            sid = f"IGS-{stage_id}-G{index:02d}"
            generated.append(
                strategy(
                    sid,
                    title,
                    stage_id,
                    goals,
                    formats,
                    psychology,
                    sources,
                    f"{trigger}，{stage_frames[stage_id]}；“{title}”的作用是把这个判断变成一个可执行、可观察、可复盘的动作。",
                    [
                        f"触发条件：{trigger}。",
                        f"具体动作：{move}。",
                        f"落地要求：{stage_requirements[stage_id]}",
                    ],
                    [
                        f"{title}执行次数",
                        "相关内容互动率",
                        "后续对话或行动率",
                    ],
                    [title, trigger.split("时")[0], move[:18], STAGES[stage_id]],
                )
            )
    return generated


STRATEGIES.extend(build_supplemental_strategies())


def reframe_terms(text: str) -> str:
    for old, new in TEXT_REPLACEMENTS:
        text = text.replace(old, new)
    return text


def unique_sequence(values: list[str]) -> list[str]:
    seen = set()
    result = []
    for value in values:
        if value and value not in seen:
            result.append(value)
            seen.add(value)
    return result


def reframe_values(values: list[str], mapping: dict[str, str], fallback: list[str]) -> list[str]:
    reframed = unique_sequence([mapping.get(value, value) for value in values])
    reframed = [value for value in reframed if value in fallback]
    return reframed or fallback[:2]


def reframe_strategy_for_relationship(card: dict) -> dict:
    reframed = dict(card)
    original_principle = reframe_terms(card["principle"]).rstrip("。")
    stage_intro = STAGE_RELATIONSHIP_INTRO[card["stage"]]
    reframed["title"] = reframe_terms(card["title"])
    reframed["stage_name"] = STAGES[card["stage"]]
    reframed["goals"] = reframe_values(card["goals"], GOAL_REFRAME, GOALS)
    reframed["formats"] = reframe_values(card["formats"], FORMAT_REFRAME, FORMATS)
    reframed["principle"] = (
        f"{stage_intro}{original_principle}。"
        "执行时只把它当作建立熟悉感和互相信任的入口，不把对方当作被推进的对象。"
    )
    reframed["actions"] = [
        reframe_terms(action)
        for action in card["actions"]
    ] + [f"边界要求：{SAFETY_BOUNDARY}"]
    reframed["metrics"] = unique_sequence(
        [reframe_terms(metric) for metric in card["metrics"]]
        + ["对方主动回应率", "重复互动率", "信任类正反馈"]
    )[:5]
    reframed["keywords"] = unique_sequence(
        [reframe_terms(keyword) for keyword in card["keywords"]]
        + ["认识陌生人", "成为朋友", "建立信任", "真诚互动"]
    )
    reframed["template"] = reframe_terms(card.get("template", ""))
    reframed["relationship_focus"] = RELATIONSHIP_MISSION
    reframed["safety_boundary"] = SAFETY_BOUNDARY
    return reframed


STRATEGIES = [reframe_strategy_for_relationship(card) for card in STRATEGIES]


def slugify(value: str) -> str:
    value = re.sub(r"[^A-Za-z0-9_-]+", "-", value).strip("-")
    return value or "item"


def source_label(source_id: str) -> str:
    source = SOURCES[source_id]
    name = source["name"]
    if "url" in source:
        return f"[{name}]({source['url']})"
    return f"{name} ({source.get('author', 'unknown author')})"


def card_path(card: dict) -> str:
    return f"cards/{card['id']}.md"


def validate() -> list[str]:
    errors: list[str] = []
    strategy_ids = [item["id"] for item in STRATEGIES]
    if len(strategy_ids) != len(set(strategy_ids)):
        errors.append("Duplicate strategy id found.")
    if len(STRATEGIES) != 300:
        errors.append(f"Expected 300 strategies, found {len(STRATEGIES)}.")

    used_stages = {item["stage"] for item in STRATEGIES}
    used_goals = {goal for item in STRATEGIES for goal in item["goals"]}
    used_formats = {fmt for item in STRATEGIES for fmt in item["formats"]}
    used_psychology = {p for item in STRATEGIES for p in item["psychology"]}
    used_sources = {src for item in STRATEGIES for src in item["sources"]}

    missing = {
        "stages": set(STAGES) - used_stages,
        "goals": set(GOALS) - used_goals,
        "formats": set(FORMATS) - used_formats,
        "psychology": set(PSYCHOLOGY) - used_psychology,
        "sources": set(SOURCES) - used_sources,
    }
    for group, values in missing.items():
        if values:
            errors.append(f"Missing {group}: {', '.join(sorted(values))}")

    known_goals = set(GOALS)
    known_formats = set(FORMATS)
    known_psychology = set(PSYCHOLOGY)
    for item in STRATEGIES:
        if item["stage"] not in STAGES:
            errors.append(f"{item['id']} has unknown stage {item['stage']}")
        for goal in item["goals"]:
            if goal not in known_goals:
                errors.append(f"{item['id']} has unknown goal {goal}")
        for fmt in item["formats"]:
            if fmt not in known_formats:
                errors.append(f"{item['id']} has unknown format {fmt}")
        for p in item["psychology"]:
            if p not in known_psychology:
                errors.append(f"{item['id']} has unknown psychology {p}")
        for source_id in item["sources"]:
            if source_id not in SOURCES:
                errors.append(f"{item['id']} has unknown source {source_id}")
    return errors


def enrich_cards() -> list[dict]:
    cards = []
    for item in STRATEGIES:
        card = dict(item)
        card["path"] = card_path(card)
        card["source_names"] = [SOURCES[source_id]["name"] for source_id in card["sources"]]
        card["all_tags"] = (
            [card["stage"], card["stage_name"]]
            + card["goals"]
            + card["formats"]
            + card["psychology"]
            + card["keywords"]
            + card["sources"]
        )
        cards.append(card)
    return cards


def relation_score(left: dict, right: dict) -> int:
    return (
        len(set(left["goals"]) & set(right["goals"])) * 3
        + len(set(left["formats"]) & set(right["formats"])) * 2
        + len(set(left["psychology"]) & set(right["psychology"])) * 2
        + len(set(left["sources"]) & set(right["sources"]))
    )


def attach_related(cards: list[dict]) -> list[dict]:
    stage_order = list(STAGES)
    by_stage: dict[str, list[dict]] = defaultdict(list)
    for card in cards:
        by_stage[card["stage"]].append(card)

    def best_match(card: dict, candidates: list[dict], relation: str, reason: str) -> dict | None:
        ranked = sorted(
            (candidate for candidate in candidates if candidate["id"] != card["id"]),
            key=lambda candidate: (relation_score(card, candidate), candidate["id"]),
            reverse=True,
        )
        if not ranked or relation_score(card, ranked[0]) <= 0:
            return None
        return {"id": ranked[0]["id"], "relation": relation, "reason": reason}

    for card in cards:
        related = []
        stage_index = stage_order.index(card["stage"])
        if stage_index > 0:
            previous_stage = stage_order[stage_index - 1]
            match = best_match(
                card,
                by_stage[previous_stage],
                "depends_on",
                f"承接上一阶段 {previous_stage} 的定位、信任或互动基础",
            )
            if match:
                related.append(match)
        if stage_index < len(stage_order) - 1:
            next_stage = stage_order[stage_index + 1]
            match = best_match(
                card,
                by_stage[next_stage],
                "continues_to",
                f"可继续推进到下一阶段 {next_stage}",
            )
            if match:
                related.append(match)
        match = best_match(
            card,
            by_stage[card["stage"]],
            "reinforces",
            "同阶段内目标、内容形式或用户心理相互增强",
        )
        if match:
            related.append(match)

        source_candidates = [
            candidate
            for candidate in cards
            if candidate["id"] != card["id"] and set(candidate["sources"]) & set(card["sources"])
        ]
        match = best_match(card, source_candidates, "same_source_family", "来自相近资料来源，可作为同一方法论的延伸")
        if match:
            related.append(match)

        seen = set()
        clean_related = []
        for item in related:
            if item["id"] not in seen:
                clean_related.append(item)
                seen.add(item["id"])
        card["related_strategies"] = clean_related[:4]
    return cards


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.rstrip() + "\n", encoding="utf-8")


def table_row(values: list[str]) -> str:
    return "| " + " | ".join(value.replace("\n", "<br>") for value in values) + " |"


def render_readme(cards: list[dict]) -> str:
    return f"""# Instagram 策略知识库

生成日期：{GENERATED_ON}

这个目录把用户提供的官方平台资料、Instagram 实战资料、数字营销资料、设计资料和经典书籍方法论，整理成可查询的策略卡片。当前版本统一聚焦：在社交平台上认识合适的陌生人，通过真诚互动、持续小帮助和清楚边界，逐步成为朋友并赢得长期信任。

## 快速使用

- 全量策略：`all_strategies.md`
- 机器可读数据：`data/strategies.json`、`data/strategies.jsonl`、`data/strategies.csv`
- 按阶段查：`indexes/by_stage.md`
- 按目标查：`indexes/by_goal.md`
- 按内容形式查：`indexes/by_format.md`
- 按用户心理查：`indexes/by_psychology.md`
- 按资料来源查：`indexes/by_source.md`
- 覆盖校验：`coverage_report.md`
- 知识图谱说明：`graph/knowledge_graph.md`
- 完整图谱数据：`graph/strategy_knowledge_graph.json`

## 命令行查询示例

```bash
python instagram_strategy_kb/tools/query_strategies.py --stage S3
python instagram_strategy_kb/tools/query_strategies.py --goal "开启私信对话"
python instagram_strategy_kb/tools/query_strategies.py --format "Reels 策略" --psychology "提升真实感"
python instagram_strategy_kb/tools/query_strategies.py --q "小资源 私信"
python instagram_strategy_kb/tools/query_strategies.py --source CIALDINI_INFLUENCE
python instagram_strategy_kb/tools/query_strategies.py --q "倾听" --show-related
python instagram_strategy_kb/tools/relationship_strategy_generator.py --serve
python instagram_strategy_kb/tools/relationship_strategy_generator.py --input book.pdf --source-name "书籍名" --review --output generated_strategies.md
python instagram_strategy_kb/tools/strategy_selector.py --situation "对方刚回复了 Story，但只说哈哈，我不知道是否该继续问" --session-id default
```

AI 生成器默认读取环境变量 `OPENAI_API_KEY`、`OPENAI_MODEL` 和 `OPENAI_API_BASE_URL`，也可以在本地可视化界面的 API Key / API Base URL 输入框里临时填写。默认官方接口会走 Responses API；如果 API Base URL 指向第三方 OpenAI-compatible 服务，系统会自动改用 `/chat/completions`。可视化界面启动后支持上传 PDF、TXT、Markdown 或直接粘贴文本；生成策略会进入右侧结果区，并可用 AI 审核是否适合加入策略库。审核通过并点击加入后，会写入 `data/user_strategies.json` 和 `cards/generated/`，查询工具会同时读取这些新增策略。

可视化界面最左侧包含“搜集 Agent”：它会按搜索主题主动搜集公开网页资料，清洗正文后每分钟尝试生成 1 条策略，AI 审核通过才进入有效策略池。有效策略池固定维护 300 条，新增策略入池时，审核/清理逻辑会把重复、空泛、风险边界不足或质量较低的策略移出并归档到 `data/rejected_strategies.json` 和 `cards/rejected/`。

可视化界面也包含“策略选择”：输入当前状况描述后，系统会优先用 embedding 在 300 条有效策略中语义召回候选策略，再由 LLM 判断当前阶段、读取同一 `session-id` 的上一次情况，最后只选择 1 条具体策略并给出第一步行动。如果接入端点不支持 embeddings，会自动退到本地语义召回，再继续用 LLM 裁决。选择历史会写入 `data/situation_history.json`，用于下一次综合判断。

## 当前规模

- 策略卡片：{len(cards)} 条
- 阶段分类：{len(STAGES)} 类
- 目标分类：{len(GOALS)} 类
- 内容形式分类：{len(FORMATS)} 类
- 用户心理分类：{len(PSYCHOLOGY)} 类
- 资料来源：{len(SOURCES)} 个

## 策略卡片字段

每条策略都包含：阶段、目标、内容形式、用户心理、资料来源、核心判断、关系应用、执行动作、观察指标、检索关键词和可选话术模板。

## 知识图谱

图谱节点包含策略、阶段、目标、内容形式、用户心理、资料来源和关键词。图谱边包含分类关系、来源关系，以及策略之间的 `depends_on`、`continues_to`、`reinforces`、`same_source_family` 四类关联。
"""


def render_sources(cards: list[dict]) -> str:
    by_source = defaultdict(list)
    for card in cards:
        for source_id in card["sources"]:
            by_source[source_id].append(card)

    lines = [
        "# 资料来源与策略映射",
        "",
        f"生成日期：{GENERATED_ON}",
        "",
        table_row(["来源 ID", "资料", "分组", "用途", "提炼原则", "关联策略数"]),
        table_row(["---", "---", "---", "---", "---", "---"]),
    ]
    for source_id, source in SOURCES.items():
        name = source_label(source_id)
        lines.append(
            table_row(
                [
                    source_id,
                    name,
                    source["group"],
                    source["use_for"],
                    source["distilled"],
                    str(len(by_source[source_id])),
                ]
            )
        )
    return "\n".join(lines)


def render_card(card: dict) -> str:
    sources = "、".join(source_label(source_id) for source_id in card["sources"])
    actions = "\n".join(f"{idx}. {action}" for idx, action in enumerate(card["actions"], 1))
    metrics = "\n".join(f"- {metric}" for metric in card["metrics"])
    keywords = "、".join(card["keywords"])
    template = f"\n## 可复制话术/结构\n\n{card['template']}\n" if card.get("template") else ""
    related = "\n".join(
        f"- {item['relation']} -> [{item['id']}](./{item['id']}.md)：{item['reason']}"
        for item in card.get("related_strategies", [])
    )
    related_section = f"\n## 知识图谱关联\n\n{related}\n" if related else ""
    return f"""# {card['id']} {card['title']}

- 阶段：{card['stage']} {card['stage_name']}
- 目标：{"、".join(card['goals'])}
- 内容形式：{"、".join(card['formats'])}
- 用户心理：{"、".join(card['psychology'])}
- 资料来源：{sources}

## 核心判断

{card['principle']}

## 关系应用

{card.get('relationship_focus', RELATIONSHIP_MISSION)}

底线：{card.get('safety_boundary', SAFETY_BOUNDARY)}

## 执行动作

{actions}
{template}
## 观察指标

{metrics}
{related_section}

## 检索关键词

{keywords}
"""


def render_all_cards(cards: list[dict]) -> str:
    lines = ["# 全量策略卡片", "", f"共 {len(cards)} 条。", ""]
    for card in cards:
        lines.append(f"## {card['id']} {card['title']}")
        lines.append("")
        lines.append(f"- 文件：[{card['path']}]({card['path']})")
        lines.append(f"- 阶段：{card['stage']} {card['stage_name']}")
        lines.append(f"- 目标：{'、'.join(card['goals'])}")
        lines.append(f"- 内容形式：{'、'.join(card['formats'])}")
        lines.append(f"- 用户心理：{'、'.join(card['psychology'])}")
        lines.append(f"- 来源：{'、'.join(card['source_names'])}")
        lines.append("")
        lines.append(card["principle"])
        lines.append("")
        lines.append(f"关系应用：{card.get('relationship_focus', RELATIONSHIP_MISSION)}")
        lines.append("")
    return "\n".join(lines)


def render_index(title: str, ordered_keys: list[str], grouped: dict[str, list[dict]], key_label=None) -> str:
    lines = [f"# {title}", ""]
    for key in ordered_keys:
        label = key_label(key) if key_label else key
        lines.append(f"## {label}")
        lines.append("")
        for card in grouped.get(key, []):
            lines.append(f"- [{card['id']} {card['title']}](../{card['path']})：{card['principle']}")
        lines.append("")
    return "\n".join(lines)


def render_stage_files(cards: list[dict]) -> None:
    by_stage = defaultdict(list)
    for card in cards:
        by_stage[card["stage"]].append(card)

    for stage_id in STAGES:
        lines = [f"# {stage_id} {STAGES[stage_id]}", ""]
        for card in by_stage[stage_id]:
            lines.append(f"## [{card['id']} {card['title']}](../{card['path']})")
            lines.append("")
            lines.append(f"- 目标：{'、'.join(card['goals'])}")
            lines.append(f"- 内容形式：{'、'.join(card['formats'])}")
            lines.append(f"- 用户心理：{'、'.join(card['psychology'])}")
            lines.append(f"- 来源：{'、'.join(card['source_names'])}")
            lines.append("")
            lines.append(card["principle"])
            lines.append("")
        write_text(ROOT / "stages" / f"{stage_id}.md", "\n".join(lines))


def render_coverage(cards: list[dict]) -> str:
    counters = {
        "阶段": defaultdict(int),
        "目标": defaultdict(int),
        "内容形式": defaultdict(int),
        "用户心理": defaultdict(int),
        "资料来源": defaultdict(int),
    }
    for card in cards:
        counters["阶段"][f"{card['stage']} {card['stage_name']}"] += 1
        for goal in card["goals"]:
            counters["目标"][goal] += 1
        for fmt in card["formats"]:
            counters["内容形式"][fmt] += 1
        for p in card["psychology"]:
            counters["用户心理"][p] += 1
        for source_id in card["sources"]:
            counters["资料来源"][source_id] += 1

    lines = [
        "# 覆盖校验报告",
        "",
        f"生成日期：{GENERATED_ON}",
        "",
        "校验结论：所有用户指定的阶段、目标、内容形式、用户心理和资料来源均已覆盖，并已统一重写到陌生人关系建立与信任维护场景。",
        "",
    ]
    for section, values in counters.items():
        lines.append(f"## {section}")
        lines.append("")
        lines.append(table_row([section, "策略数"]))
        lines.append(table_row(["---", "---"]))
        for key in sorted(values):
            lines.append(table_row([key, str(values[key])]))
        lines.append("")
    return "\n".join(lines)


def write_data(cards: list[dict]) -> None:
    data_dir = ROOT / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    write_text(data_dir / "strategies.json", json.dumps(cards, ensure_ascii=False, indent=2))
    write_text(data_dir / "sources.json", json.dumps(SOURCES, ensure_ascii=False, indent=2))
    write_text(data_dir / "categories.json", json.dumps({
        "stages": STAGES,
        "goals": GOALS,
        "formats": FORMATS,
        "psychology": PSYCHOLOGY,
    }, ensure_ascii=False, indent=2))

    with (data_dir / "strategies.jsonl").open("w", encoding="utf-8") as handle:
        for card in cards:
            handle.write(json.dumps(card, ensure_ascii=False) + "\n")

    with (data_dir / "strategies.csv").open("w", encoding="utf-8", newline="") as handle:
        fieldnames = [
            "id",
            "title",
            "stage",
            "stage_name",
            "goals",
            "formats",
            "psychology",
            "sources",
            "principle",
            "actions",
            "metrics",
            "keywords",
            "related_strategies",
            "path",
            "relationship_focus",
            "safety_boundary",
        ]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for card in cards:
            row = {field: card.get(field, "") for field in fieldnames}
            for field in ["goals", "formats", "psychology", "sources", "actions", "metrics", "keywords"]:
                row[field] = "；".join(row[field])
            row["related_strategies"] = "；".join(item["id"] for item in card.get("related_strategies", []))
            writer.writerow(row)


def graph_node_id(kind: str, value: str) -> str:
    return f"{kind}:{value}"


def build_knowledge_graph(cards: list[dict]) -> dict:
    nodes: dict[str, dict] = {}
    edges: list[dict] = []

    def add_node(node_id: str, label: str, kind: str, **attrs) -> None:
        if node_id not in nodes:
            nodes[node_id] = {"id": node_id, "label": label, "type": kind, **attrs}

    def add_edge(source: str, target: str, relation: str, **attrs) -> None:
        edges.append({"source": source, "target": target, "relation": relation, **attrs})

    for stage_id, stage_name in STAGES.items():
        add_node(graph_node_id("stage", stage_id), f"{stage_id} {stage_name}", "stage")
    for goal in GOALS:
        add_node(graph_node_id("goal", goal), goal, "goal")
    for fmt in FORMATS:
        add_node(graph_node_id("format", fmt), fmt, "format")
    for p in PSYCHOLOGY:
        add_node(graph_node_id("psychology", p), p, "psychology")
    for source_id, source in SOURCES.items():
        add_node(graph_node_id("source", source_id), source["name"], "source", group=source["group"])

    keyword_counts: defaultdict[str, int] = defaultdict(int)
    for card in cards:
        for keyword in card["keywords"]:
            keyword_counts[keyword] += 1
    for keyword, count in keyword_counts.items():
        if count >= 2:
            add_node(graph_node_id("keyword", keyword), keyword, "keyword", count=count)

    for card in cards:
        strategy_id = graph_node_id("strategy", card["id"])
        add_node(
            strategy_id,
            f"{card['id']} {card['title']}",
            "strategy",
            stage=card["stage"],
            path=card["path"],
        )
        add_edge(strategy_id, graph_node_id("stage", card["stage"]), "classified_as")
        for goal in card["goals"]:
            add_edge(strategy_id, graph_node_id("goal", goal), "aims_at")
        for fmt in card["formats"]:
            add_edge(strategy_id, graph_node_id("format", fmt), "uses_format")
        for p in card["psychology"]:
            add_edge(strategy_id, graph_node_id("psychology", p), "addresses_psychology")
        for source_id in card["sources"]:
            add_edge(strategy_id, graph_node_id("source", source_id), "derived_from")
        for keyword in card["keywords"]:
            if keyword_counts[keyword] >= 2:
                add_edge(strategy_id, graph_node_id("keyword", keyword), "tagged_with")
        for related in card.get("related_strategies", []):
            add_edge(
                strategy_id,
                graph_node_id("strategy", related["id"]),
                related["relation"],
                reason=related["reason"],
            )

    return {
        "generated_on": GENERATED_ON,
        "node_count": len(nodes),
        "edge_count": len(edges),
        "nodes": list(nodes.values()),
        "edges": edges,
    }


def render_graph_mermaid(cards: list[dict]) -> str:
    chains = [
        ["IGS-S1-G04", "IGS-S2-G01", "IGS-S3-G10", "IGS-S4-G16", "IGS-S5-G02", "IGS-S6-G04", "IGS-S7-G01", "IGS-S8-G15", "IGS-S9-G03"],
        ["IGS-S1-G09", "IGS-S2-G07", "IGS-S3-G21", "IGS-S4-G15", "IGS-S5-G07", "IGS-S6-G16", "IGS-S7-G15", "IGS-S8-G06", "IGS-S9-G05"],
        ["IGS-S1-G11", "IGS-S2-G11", "IGS-S3-G15", "IGS-S4-G14", "IGS-S5-G23", "IGS-S6-G08", "IGS-S7-G14", "IGS-S8-G08", "IGS-S9-G10"],
        ["IGS-S1-G01", "IGS-S2-G20", "IGS-S3-G24", "IGS-S4-G12", "IGS-S5-G01", "IGS-S6-G07", "IGS-S7-G03", "IGS-S8-G05", "IGS-S9-G17"],
    ]
    id_to_card = {card["id"]: card for card in cards}
    lines = [
        "flowchart LR",
        "  classDef stage fill:#eef6ff,stroke:#4b86c5,color:#14395b;",
        "  classDef strategy fill:#fffdf5,stroke:#d1a83a,color:#312400;",
    ]
    for stage_id, stage_name in STAGES.items():
        lines.append(f'  {stage_id}["{stage_id} {stage_name}"]:::stage')
    for left, right in zip(list(STAGES), list(STAGES)[1:]):
        lines.append(f"  {left} --> {right}")
    lines.append("")
    for chain_index, chain in enumerate(chains, 1):
        previous_node = None
        for strategy_id in chain:
            card = id_to_card[strategy_id]
            node = strategy_id.replace("-", "_")
            title = card["title"].replace('"', "'")
            lines.append(f'  {node}["{strategy_id}<br/>{title}"]:::strategy')
            lines.append(f"  {card['stage']} -.包含.-> {node}")
            if previous_node:
                lines.append(f"  {previous_node} --> {node}")
            previous_node = node
        lines.append(f"  %% chain {chain_index}")
    return "\n".join(lines)


def render_graph_doc(graph: dict) -> str:
    relation_counts: defaultdict[str, int] = defaultdict(int)
    node_counts: defaultdict[str, int] = defaultdict(int)
    for edge in graph["edges"]:
        relation_counts[edge["relation"]] += 1
    for node in graph["nodes"]:
        node_counts[node["type"]] += 1

    lines = [
        "# 策略知识图谱",
        "",
        f"生成日期：{GENERATED_ON}",
        "",
        "这个图谱把 300 条陌生人关系建立策略连接到阶段、目标、内容形式、用户心理、资料来源和关键词，并额外生成策略之间的前置、承接、增强和同源关系。",
        "",
        "## 图谱文件",
        "",
        "- `strategy_knowledge_graph.json`：完整节点和边，适合程序读取。",
        "- `strategy_knowledge_graph.mmd`：Mermaid 摘要图，适合快速看阶段链路和典型策略路径。",
        "- `strategy_edges.csv`：策略间关系边，适合表格查询。",
        "",
        "## 节点统计",
        "",
        table_row(["节点类型", "数量"]),
        table_row(["---", "---"]),
    ]
    for kind in sorted(node_counts):
        lines.append(table_row([kind, str(node_counts[kind])]))
    lines.extend(["", "## 边统计", "", table_row(["关系", "数量"]), table_row(["---", "---"])])
    for relation in sorted(relation_counts):
        lines.append(table_row([relation, str(relation_counts[relation])]))
    lines.extend(
        [
            "",
            "## Mermaid 摘要",
            "",
            "```mermaid",
            Path(ROOT / "graph" / "strategy_knowledge_graph.mmd").read_text(encoding="utf-8") if (ROOT / "graph" / "strategy_knowledge_graph.mmd").exists() else "",
            "```",
        ]
    )
    return "\n".join(lines)


def write_graph(cards: list[dict]) -> None:
    graph_dir = ROOT / "graph"
    graph_dir.mkdir(parents=True, exist_ok=True)
    graph = build_knowledge_graph(cards)
    write_text(graph_dir / "strategy_knowledge_graph.json", json.dumps(graph, ensure_ascii=False, indent=2))
    write_text(graph_dir / "strategy_knowledge_graph.mmd", render_graph_mermaid(cards))

    strategy_edges = [
        edge
        for edge in graph["edges"]
        if edge["source"].startswith("strategy:") and edge["target"].startswith("strategy:")
    ]
    with (graph_dir / "strategy_edges.csv").open("w", encoding="utf-8", newline="") as handle:
        fieldnames = ["source", "target", "relation", "reason"]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for edge in strategy_edges:
            writer.writerow({field: edge.get(field, "") for field in fieldnames})
    write_text(graph_dir / "knowledge_graph.md", render_graph_doc(graph))


def generate() -> None:
    errors = validate()
    if errors:
        raise SystemExit("\n".join(errors))

    cards = attach_related(enrich_cards())
    for subdir in ["cards", "indexes", "stages", "data", "graph"]:
        (ROOT / subdir).mkdir(parents=True, exist_ok=True)

    write_text(ROOT / "README.md", render_readme(cards))
    write_text(ROOT / "SOURCES.md", render_sources(cards))
    write_text(ROOT / "all_strategies.md", render_all_cards(cards))
    write_text(ROOT / "coverage_report.md", render_coverage(cards))

    for card in cards:
        write_text(ROOT / card["path"], render_card(card))

    by_stage = defaultdict(list)
    by_goal = defaultdict(list)
    by_format = defaultdict(list)
    by_psychology = defaultdict(list)
    by_source = defaultdict(list)
    for card in cards:
        by_stage[card["stage"]].append(card)
        for goal in card["goals"]:
            by_goal[goal].append(card)
        for fmt in card["formats"]:
            by_format[fmt].append(card)
        for p in card["psychology"]:
            by_psychology[p].append(card)
        for source_id in card["sources"]:
            by_source[source_id].append(card)

    write_text(
        ROOT / "indexes" / "by_stage.md",
        render_index("按阶段分类索引", list(STAGES), by_stage, lambda key: f"{key} {STAGES[key]}"),
    )
    write_text(ROOT / "indexes" / "by_goal.md", render_index("按目标分类索引", GOALS, by_goal))
    write_text(ROOT / "indexes" / "by_format.md", render_index("按内容形式分类索引", FORMATS, by_format))
    write_text(ROOT / "indexes" / "by_psychology.md", render_index("按用户心理分类索引", PSYCHOLOGY, by_psychology))
    write_text(ROOT / "indexes" / "by_source.md", render_index("按资料来源索引", list(SOURCES), by_source, lambda key: f"{key} {SOURCES[key]['name']}"))
    render_stage_files(cards)
    write_data(cards)
    write_graph(cards)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate the Instagram strategy knowledge base.")
    parser.add_argument("--check", action="store_true", help="Only validate source/category coverage.")
    args = parser.parse_args()

    errors = validate()
    if errors:
        raise SystemExit("\n".join(errors))
    if args.check:
        print("Coverage check passed.")
        return
    generate()
    print(f"Generated {len(STRATEGIES)} strategies into {ROOT}")


if __name__ == "__main__":
    main()
