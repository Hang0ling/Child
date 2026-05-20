const moduleMap = {
  "long-term-strategy": ["长期策略册", "Long Term Strategy"],
  "transition-index": ["转移索引", "Transition Index"],
  "short-term-strategy": ["短期策略册", "Short Term Strategy"],
  "selected-strategy": ["选定策略", "Selected Strategy"],
  "experience-memory": ["经验记忆", "Experience Memory"],
  "run-plan": ["运行计划", "Run Plan"],
  "core-gene": ["核心基因", "DNA"],
  "history-context": ["历史信息", "History Context"],
  "environment-settings": ["环境配置", "Environment Settings"],
  openclaw: ["Openclaw", "Openclaw"],
  autoglm: ["AutoGLM", "AutoGLM"],
  phone: ["手机", "Phone"],
  timer: ["计时器", "Timer"],
  "judge-result": ["评判结果", "Judge Result"],
  "continuing-episode": ["继续当前节", "Continuing Episode"],
  "next-episode": ["下一节", "Next Episode"],
  "run-plan-close": ["运行计划结束", "Run Plan Close"],
  summarizer: ["总结块", "Summarizer"],
};

const params = new URLSearchParams(window.location.search);
let activeModule = moduleMap[params.get("module")] ? params.get("module") : "long-term-strategy";
let activeVersion = 2;
let versionQuery = "";
let dirty = false;

const moduleName = document.getElementById("moduleName");
const moduleToggle = document.getElementById("moduleToggle");
const moduleMenu = document.getElementById("moduleMenu");
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

  moduleName.textContent = cn;
  updatedAt.textContent = `最近更新：${stamp()}`;
  definitionCopy.innerHTML = paragraph(`这里是 ${cn} / ${en} 的定义、边界、输入输出标准和失败条件。`, 3);
  inputCopy.innerHTML = paragraph(`这里是 ${cn} 的统一输入测试用例，可以直接编辑并运行。`, 3);
  outputCopy.innerHTML = paragraph(`这里会显示 ${cn} 在当前版本 ${version.revision} 下的运行输出。`, 4);
  versionCopy.innerHTML = paragraph(`const moduleName = "${en}"; 这里是 ${version.date} ${version.revision} 的版本内容。`, 20);
  testCopy.innerHTML = paragraph(`function test_${activeModule.replace(/-/g, "_")}() { return "这里是要调试的内容"; }`, 18);
  testStatus.textContent = "当前内容仍未保存";
  dirty = false;
  renderModuleMenu();
  renderDates();
  renderChecks();
  window.history.replaceState(null, "", `?module=${encodeURIComponent(activeModule)}`);
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
  const [cn] = moduleMap[activeModule];
  const version = versions.find((item) => item.id === activeVersion);
  versionCopy.innerHTML = paragraph(`const selectedVersion = "${version.date}"; 这里是 ${cn} 的 ${version.revision} 版本内容。`, 20);
  testCopy.innerHTML = paragraph(`// ${version.date} ${version.revision}\nfunction candidate() { return "当前测试内容"; }`, 18);
  dirty = false;
  testStatus.textContent = "已切换版本";
  renderDates();
  renderChecks();
}

moduleToggle.addEventListener("click", () => {
  const open = !moduleMenu.classList.contains("open");
  moduleMenu.classList.toggle("open", open);
  moduleToggle.setAttribute("aria-expanded", String(open));
});

moduleMenu.addEventListener("click", (event) => {
  const button = event.target.closest("[data-module]");
  if (button) setModule(button.dataset.module);
});

document.addEventListener("click", (event) => {
  if (!event.target.closest(".definition-card")) {
    moduleMenu.classList.remove("open");
    moduleToggle.setAttribute("aria-expanded", "false");
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
    outputCopy.innerHTML = paragraph(`运行完成：${cn} 在当前输入下生成了新的输出，耗时 ${(Math.random() * 2 + 0.8).toFixed(2)}s。`, 4);
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
