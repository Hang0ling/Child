const moduleMap = {
  "core-gene": ["DNA", "ChildGenome/DNA.md"],
  "experience-memory": ["Experience Memory", "ChildGenome/ExperienceMemory.md"],
  "long-term-strategy": ["A层策略", "ChildGenome/StrategyPlayBook/LongTermStrategyGraph.md"],
  "transition-index": ["Transition Index", "ChildGenome/StrategyPlayBook/TransitionIndex.md"],
  "short-term-strategy": ["B层策略", "ChildGenome/StrategyPlayBook/ShortTermStrategyGraph.md"],
  "pre-scorer-a": ["Pre Scorer A", "A Layer Strategy Scorer"],
  "pre-scorer-b": ["Pre Scorer B", "B Layer Strategy Scorer"],
  generator: ["Generator", "Decision Core Generator"],
  openclaw: ["Openclaw", "Openclaw"],
  autoglm: ["AutoGLM", "AutoGLM"],
  selector: ["Post Scorer", "Judge Core Post Scorer"],
};

const params = new URLSearchParams(window.location.search);
let activeModule = moduleMap[params.get("module")] ? params.get("module") : "long-term-strategy";
let activeVersion = 2;
let activeInputVersion = 2;
let versionQuery = "";
let dirty = false;

const moduleName = document.getElementById("moduleName");
const moduleToggle = document.getElementById("moduleToggle");
const moduleMenu = document.getElementById("moduleMenu");
const inputToggle = document.getElementById("inputToggle");
const inputMenu = document.getElementById("inputMenu");
const updatedAt = document.getElementById("updatedAt");
const definitionCopy = document.getElementById("definitionCopy");
const inputCopy = document.getElementById("inputCopy");
const outputCopy = document.getElementById("outputCopy");
const versionCopy = document.getElementById("versionCopy");
const testCopy = document.getElementById("testCopy");
const checkList = document.getElementById("checkList");
const testStatus = document.getElementById("testStatus");
const runTest = document.getElementById("runTest");
const saveTest = document.getElementById("saveTest");
const dateList = document.getElementById("dateList");
const versionSearch = document.getElementById("versionSearch");

document.body.appendChild(moduleMenu);
document.body.appendChild(inputMenu);

function escapeHtml(value) {
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function stamp() {
  const parts = new Intl.DateTimeFormat("zh-CN", {
    timeZone: "Asia/Shanghai",
    year: "numeric",
    month: "numeric",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).formatToParts(new Date());
  const map = Object.fromEntries(parts.map((part) => [part.type, part.value]));
  return `${map.year}/${map.month}/${map.day} ${map.hour}:${map.minute}`;
}

function dateOnly(offset = 0) {
  const date = new Date(Date.now() - offset * 86400000);
  const parts = new Intl.DateTimeFormat("zh-CN", {
    timeZone: "Asia/Shanghai",
    year: "numeric",
    month: "numeric",
    day: "numeric",
  }).formatToParts(date);
  const map = Object.fromEntries(parts.map((part) => [part.type, part.value]));
  return `${map.year}/${map.month}/${map.day}`;
}

const versions = Array.from({ length: 14 }, (_, index) => ({
  id: index,
  date: dateOnly(index),
  revision: `v${14 - index}.${(index * 7) % 10}`,
}));

function paragraph(text, count) {
  return Array.from({ length: count }, (_, index) => `<p>${escapeHtml(text)} // ${index + 1}</p>`).join("");
}

function runtimeSummary(moduleName, version, elapsed = "0.00s") {
  return `
    <div class="runtime-strip">
      <span>运行时间 <b>${escapeHtml(elapsed)}</b></span>
      <span>版本 <b>${escapeHtml(version.revision)}</b></span>
      <span>状态 <b>Ready</b></span>
    </div>
    <details class="output-details">
      <summary>展开运行详情</summary>
      <div>
        <p>模块：${escapeHtml(moduleName)}</p>
        <p>输入校验：通过基本结构检测，等待真实执行器接入。</p>
        <p>输出摘要：包含运行耗时、版本号、状态和关键日志。</p>
      </div>
    </details>
  `;
}

function checksFor(text) {
  const length = text.trim().length;
  return [
    ["输入内容不为空", length > 10],
    ["包含可执行的测试上下文", /测试|执行|策略|计时|结果/.test(text)],
    ["输出内容长度符合最低要求", outputCopy.innerText.trim().length > 20],
    ["当前版本已与测试内容同步", !dirty],
  ];
}

function renderModuleMenu() {
  moduleMenu.innerHTML = Object.entries(moduleMap)
    .map(
      ([id, [cn, en]]) => `
        <button class="${id === activeModule ? "active" : ""}" type="button" data-module="${id}">
          ${escapeHtml(cn)} <small>${escapeHtml(en)}</small>
        </button>
      `,
    )
    .join("");
}

function positionModuleMenu() {
  const rect = moduleToggle.getBoundingClientRect();
  moduleMenu.style.left = `${Math.round(rect.left)}px`;
  moduleMenu.style.top = `${Math.round(rect.bottom + 8)}px`;
  moduleMenu.style.width = `${Math.max(320, Math.round(rect.width + 160))}px`;
}

function renderInputMenu() {
  inputMenu.innerHTML = versions
    .map(
      (version) => `
        <button class="${version.id === activeInputVersion ? "active" : ""}" type="button" data-input-version="${version.id}">
          ${escapeHtml(version.date)} <small>${escapeHtml(version.revision)} 输入</small>
        </button>
      `,
    )
    .join("");
}

function positionInputMenu() {
  const rect = inputToggle.getBoundingClientRect();
  inputMenu.style.left = `${Math.round(rect.left)}px`;
  inputMenu.style.top = `${Math.round(rect.bottom + 8)}px`;
  inputMenu.style.width = `${Math.max(260, Math.round(rect.width + 160))}px`;
}

function renderDates() {
  const items = versions.filter((version) => {
    const haystack = `${version.date} ${version.revision}`.toLowerCase();
    return haystack.includes(versionQuery);
  });

  dateList.innerHTML = items.length
    ? items
        .map(
          (version) => `
            <button class="${version.id === activeVersion ? "active" : ""}" type="button" data-version="${version.id}">
              ${escapeHtml(version.date)}
            </button>
          `,
        )
        .join("")
    : `<p class="empty-state">没有匹配版本</p>`;
}

function renderChecks() {
  checkList.innerHTML = checksFor(testCopy.innerText)
    .map(([label, passed]) => {
      const cls = passed ? "pass" : "fail";
      const mark = passed ? "✓" : "×";
      return `<p>${escapeHtml(label)} <span class="${cls}">${mark}</span></p>`;
    })
    .join("");
}

function renderModule() {
  const [cn, en] = moduleMap[activeModule];
  const version = versions.find((item) => item.id === activeVersion) || versions[0];
  activeInputVersion = activeVersion;

  moduleName.textContent = cn;
  updatedAt.textContent = `最近更新：${stamp()}`;
  definitionCopy.innerHTML = paragraph(`这里是 ${cn} / ${en} 的定义、边界、输入输出标准和失败条件。`, 3);
  inputCopy.innerHTML = paragraph(`这里是 ${cn} 的统一输入测试用例，可以直接编辑并运行。`, 3);
  outputCopy.innerHTML = runtimeSummary(cn, version) + paragraph(`这里会显示 ${cn} 在当前版本 ${version.revision} 下的运行输出。`, 3);
  versionCopy.innerHTML = paragraph(`这里是 ${cn} / ${en} 的生成过程，包含版本 ${version.date} ${version.revision} 的提示、检查点和中间输出。`, 12);
  testCopy.innerHTML = paragraph(`这里是 ${cn} 的文件结果和当前测试输出，可编辑后运行测试。`, 12);
  testStatus.textContent = "当前内容仍未保存";
  dirty = false;
  renderModuleMenu();
  renderInputMenu();
  renderDates();
  renderChecks();
  window.history.replaceState(null, "", `?module=${encodeURIComponent(activeModule)}&v=debug-title-controls-11`);
}

function setModule(moduleId) {
  if (!moduleMap[moduleId]) return;
  activeModule = moduleId;
  moduleMenu.classList.remove("open");
  moduleToggle.setAttribute("aria-expanded", "false");
  renderModule();
}

function setVersion(versionId) {
  activeVersion = Number(versionId);
  activeInputVersion = Number(versionId);
  const [cn] = moduleMap[activeModule];
  const version = versions.find((item) => item.id === activeVersion);
  inputCopy.innerHTML = paragraph(`这里是 ${cn} 在 ${version.date} ${version.revision} 使用的历史输入内容，可以切换版本对比。`, 3);
  outputCopy.innerHTML = runtimeSummary(cn, version) + paragraph(`这里会显示 ${cn} 在历史版本 ${version.revision} 下的运行输出。`, 3);
  versionCopy.innerHTML = paragraph(`这里是 ${cn} 在 ${version.date} ${version.revision} 下的生成过程、输入摘要和关键步骤。`, 12);
  testCopy.innerHTML = paragraph(`这里是 ${version.date} ${version.revision} 对应的文件结果和当前测试输出。`, 12);
  dirty = false;
  testStatus.textContent = "已切换版本";
  renderInputMenu();
  renderDates();
  renderChecks();
}

function setInputVersion(versionId) {
  activeInputVersion = Number(versionId);
  const [cn] = moduleMap[activeModule];
  const version = versions.find((item) => item.id === activeInputVersion) || versions[0];
  inputCopy.innerHTML = paragraph(`这里是 ${cn} 在 ${version.date} ${version.revision} 使用的历史输入内容，可以单独选择并用于当前调试。`, 3);
  inputMenu.classList.remove("open");
  inputToggle.setAttribute("aria-expanded", "false");
  dirty = true;
  testStatus.textContent = "已切换输入历史版本";
  renderInputMenu();
  renderChecks();
}

moduleToggle.addEventListener("click", () => {
  const open = !moduleMenu.classList.contains("open");
  moduleMenu.classList.toggle("open", open);
  moduleToggle.setAttribute("aria-expanded", String(open));
  if (open) positionModuleMenu();
});

inputToggle.addEventListener("click", () => {
  const open = !inputMenu.classList.contains("open");
  inputMenu.classList.toggle("open", open);
  inputToggle.setAttribute("aria-expanded", String(open));
  if (open) positionInputMenu();
});

moduleMenu.addEventListener("click", (event) => {
  const button = event.target.closest("[data-module]");
  if (button) setModule(button.dataset.module);
});

inputMenu.addEventListener("click", (event) => {
  const button = event.target.closest("[data-input-version]");
  if (button) setInputVersion(button.dataset.inputVersion);
});

document.addEventListener("click", (event) => {
  if (!event.target.closest(".definition-card")) {
    moduleMenu.classList.remove("open");
    moduleToggle.setAttribute("aria-expanded", "false");
  }
  if (!event.target.closest(".io-card") && !event.target.closest(".input-menu")) {
    inputMenu.classList.remove("open");
    inputToggle.setAttribute("aria-expanded", "false");
  }
});

dateList.addEventListener("click", (event) => {
  const button = event.target.closest("[data-version]");
  if (button) setVersion(button.dataset.version);
});

versionSearch.addEventListener("input", () => {
  versionQuery = versionSearch.value.trim().toLowerCase();
  renderDates();
});

window.addEventListener("resize", () => {
  if (moduleMenu.classList.contains("open")) positionModuleMenu();
  if (inputMenu.classList.contains("open")) positionInputMenu();
});

inputCopy.addEventListener("input", () => {
  dirty = true;
  testStatus.textContent = "输入已修改，等待运行";
  renderChecks();
});

testCopy.addEventListener("input", () => {
  dirty = true;
  testStatus.textContent = "当前内容仍未保存";
  renderChecks();
});

runTest.addEventListener("click", () => {
  testStatus.textContent = "正在运行测试...";
  checkList.innerHTML = `
    <p>测试队列已提交 <span class="pending">…</span></p>
    <p>等待输出内容生成 <span class="pending">…</span></p>
    <p>智能检测即将更新 <span class="pending">…</span></p>
  `;

  window.setTimeout(() => {
    const [cn] = moduleMap[activeModule];
    const version = versions.find((item) => item.id === activeVersion) || versions[0];
    const elapsed = `${(Math.random() * 2 + 0.8).toFixed(2)}s`;
    outputCopy.innerHTML = runtimeSummary(cn, version, elapsed) + paragraph(`运行完成：${cn} 在当前输入下生成了新的输出。`, 3);
    dirty = true;
    testStatus.textContent = "测试完成，检测结果已更新";
    renderChecks();
  }, 520);
});

saveTest.addEventListener("click", () => {
  dirty = false;
  updatedAt.textContent = `最近更新：${stamp()}`;
  testStatus.textContent = "已保存并发布";
  renderChecks();
});

renderModule();
