# Instagram 策略知识库

生成日期：2026-05-20

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

- 策略卡片：300 条
- 阶段分类：9 类
- 目标分类：10 类
- 内容形式分类：10 类
- 用户心理分类：9 类
- 资料来源：41 个

## 策略卡片字段

每条策略都包含：阶段、目标、内容形式、用户心理、资料来源、核心判断、关系应用、执行动作、观察指标、检索关键词和可选话术模板。

## 知识图谱

图谱节点包含策略、阶段、目标、内容形式、用户心理、资料来源和关键词。图谱边包含分类关系、来源关系，以及策略之间的 `depends_on`、`continues_to`、`reinforces`、`same_source_family` 四类关联。
