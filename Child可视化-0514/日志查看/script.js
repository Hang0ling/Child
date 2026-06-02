const topicMap = {
  "core-gene": ["核心基因", "Core Gene", "DNA"],
  "strategy-playbook": ["策略手册", "Strategy Playbook", "Strategy"],
  "experience-memory": ["经验记忆", "Experience Memory", "Memory"],
  "prior-knowledge": ["先验知识", "Prior Knowledge", "Knowledge"],
  "mission-spec": ["任务规格", "Mission Spec", "Spec"],
  "risk-policy": ["风险制度", "Risk Policy", "Risk"],
  "closure-policy": ["结束制度", "Closure Policy", "Closure"],
  "execution-brief": ["执行说明", "Execution Brief", "Brief"],
  "history-context": ["历史信息", "History Context", "History"],
  "opponent-state": ["对手状态", "Opponent State", "Opponent"],
  "execution-result": ["执行结果", "Execution Result", "Result"],
  "think-log": ["思考日志", "Think Log", "Think"],
  "act-log": ["行为日志", "Act Log", "Act"],
  "trajectory-package": ["轨迹追踪", "Trajectory Package", "Trajectory"],
  "judge-result": ["评判结果", "Judge Result", "Judge"],
};

const topicOrder = Object.keys(topicMap);
const relatedByTopic = {
  "core-gene": ["strategy-playbook", "experience-memory", "history-context", "mission-spec"],
  "strategy-playbook": ["core-gene", "mission-spec", "risk-policy", "selected-strategy", "experience-memory"],
  "experience-memory": ["history-context", "trajectory-package", "execution-result", "judge-result"],
  "execution-brief": ["mission-spec", "prior-knowledge", "history-context", "run-plan", "execution-result"],
  "judge-result": ["execution-result", "think-log", "act-log", "trajectory-package", "risk-policy"],
};

const debugByTopic = {
  "core-gene": "core-gene",
  "strategy-playbook": "long-term-strategy",
  "experience-memory": "experience-memory",
  "execution-brief": "run-plan",
  "judge-result": "judge-result",
  "execution-result": "autoglm",
  "think-log": "autoglm",
  "act-log": "openclaw",
  "trajectory-package": "summarizer",
};

const logListItems = document.getElementById("logListItems");
const relatedDocs = document.getElementById("relatedDocs");
const inputAccordion = document.getElementById("inputAccordion");
const processTitle = document.getElementById("processTitle");
const processCopy = document.getElementById("processCopy");
const resultTitle = document.getElementById("resultTitle");
const resultCopy = document.getElementById("resultCopy");
const logSearch = document.getElementById("logSearch");
const copyResult = document.getElementById("copyResult");
const openDebug = document.getElementById("openDebug");

const params = new URLSearchParams(window.location.search);
let activeTopic = topicMap[params.get("topic")] ? params.get("topic") : "execution-brief";
let query = "";

function dateStamp(offsetMinutes = 0) {
  const date = new Date(Date.now() - offsetMinutes * 60000);
  const parts = new Intl.DateTimeFormat("zh-CN", {
    timeZone: "Asia/Shanghai",
    year: "numeric",
    month: "numeric",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).formatToParts(date);
  const map = Object.fromEntries(parts.map((part) => [part.type, part.value]));
  return `${map.year}/${map.month}/${map.day} ${map.hour}:${map.minute}`;
}

const logs = topicOrder.map((topic, index) => {
  const [cn, en, shortName] = topicMap[topic];
  const childId = `CHILD-${String((index % 3) + 1).padStart(3, "0")}`;
  return {
    topic,
    cn,
    en,
    shortName,
    childId,
    displayName: `${childId} · ${en}`,
    time: dateStamp(index * 37),
    summary: `${cn} 文档记录了当前 child 生成流程里 ${en} 的输入、生成过程和最终内容。`,
  };
});

const logByTopic = new Map(logs.map((log) => [log.topic, log]));

function escapeHtml(value) {
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function paragraph(text, count) {
  return Array.from({ length: count }, (_, index) => `<p>${escapeHtml(text)} 第 ${index + 1} 段。</p>`).join("");
}

function visibleLogs() {
  if (!query) return logs;
  return logs.filter((log) => {
    const haystack = `${log.cn} ${log.en} ${log.childId} ${log.time} ${log.summary}`.toLowerCase();
    return haystack.includes(query);
  });
}

function setActiveTopic(topic, updateUrl = true) {
  if (!topicMap[topic]) return;
  activeTopic = topic;
  if (updateUrl) window.history.replaceState(null, "", `?topic=${encodeURIComponent(topic)}`);
  render();
}

function renderLogList() {
  const items = visibleLogs();
  if (!items.length) {
    logListItems.innerHTML = `<div class="empty-state">没有匹配的日志。换一个关键词试试。</div>`;
    return;
  }

  logListItems.innerHTML = items
    .map(
      (log) => `
        <button class="log-item ${log.topic === activeTopic ? "active" : ""}" type="button" data-topic="${log.topic}">
          <span class="log-icon" aria-hidden="true"></span>
          <span>
            <em>${escapeHtml(log.childId)}</em>
            <strong>${escapeHtml(log.en)}</strong>
            <time>${escapeHtml(log.time)}</time>
            <small>${escapeHtml(log.cn)}</small>
          </span>
        </button>
      `,
    )
    .join("");
}

function renderRelatedDocs() {
  const related = relatedByTopic[activeTopic] || topicOrder.filter((topic) => topic !== activeTopic).slice(0, 6);
  const chips = [activeTopic, ...related.filter((topic) => topicMap[topic])];

  relatedDocs.innerHTML = chips
    .map((topic) => {
      const [cn, en] = topicMap[topic];
      const log = logByTopic.get(topic);
      return `
        <button class="doc-chip ${topic === activeTopic ? "active" : ""}" type="button" data-topic="${topic}">
          <b>${escapeHtml(cn)}</b>
          ${log ? `<em>${escapeHtml(log.childId)}</em>` : ""}
          <span>${escapeHtml(en)}</span>
        </button>
      `;
    })
    .join("");
}

function renderAccordion() {
  const inputs = relatedByTopic[activeTopic] || ["prior-knowledge", "mission-spec", "history-context", "risk-policy"];
  inputAccordion.innerHTML = inputs
    .filter((topic) => topicMap[topic])
    .map((topic, index) => {
      const [cn, en] = topicMap[topic];
      return `
        <details ${index === 0 ? "open" : ""}>
          <summary>${escapeHtml(en)}</summary>
          <div class="detail-copy">
            ${paragraph(`这里是 ${cn} 输入内容，包含提示、约束、上下文和上一轮执行留下的材料。`, 3)}
          </div>
        </details>
      `;
    })
    .join("");
}

function renderContent() {
  const [cn, en, shortName] = topicMap[activeTopic];
  const activeLog = logByTopic.get(activeTopic);
  processTitle.textContent = `Agent- ${cn}`;
  resultTitle.textContent = activeLog ? activeLog.displayName : en;
  processCopy.innerHTML = paragraph(`这里是生成 ${shortName} 时使用的提示词、代码片段和中间推理记录。`, 9);
  resultCopy.innerHTML = paragraph(`这里是 ${cn} 的最终文件内容，点击左侧日志或关联文档会切换当前结果。`, 10);
  openDebug.href = `../调试台/index.html?module=${encodeURIComponent(debugByTopic[activeTopic] || "long-term-strategy")}&v=debug-title-controls-11`;
}

function render() {
  renderLogList();
  renderRelatedDocs();
  renderAccordion();
  renderContent();
}

logListItems.addEventListener("click", (event) => {
  const button = event.target.closest("[data-topic]");
  if (button) setActiveTopic(button.dataset.topic);
});

relatedDocs.addEventListener("click", (event) => {
  const button = event.target.closest("[data-topic]");
  if (button) setActiveTopic(button.dataset.topic);
});

logSearch.addEventListener("input", () => {
  query = logSearch.value.trim().toLowerCase();
  renderLogList();
});

copyResult.addEventListener("click", async () => {
  const text = resultCopy.innerText.trim();
  try {
    await navigator.clipboard.writeText(text);
    copyResult.textContent = "已复制";
  } catch {
    const selection = window.getSelection();
    const range = document.createRange();
    range.selectNodeContents(resultCopy);
    selection.removeAllRanges();
    selection.addRange(range);
    copyResult.textContent = "已选中";
  }

  window.setTimeout(() => {
    copyResult.textContent = "复制结果";
  }, 1200);
});

render();
