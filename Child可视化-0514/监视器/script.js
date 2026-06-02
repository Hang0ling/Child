const monitorGrid = document.getElementById("monitorGrid");
const monitorSummary = document.getElementById("monitorSummary");

const states = [
  ["存活", "state-ok"],
  ["观察中", "state-warn"],
  ["需接管", "state-bad"],
];

const actions = [
  "打开任务页",
  "读取验证码区域",
  "等待按钮可点击",
  "滑动列表定位目标",
  "提交当前步骤",
  "检测页面跳转",
  "同步执行结果",
  "回传截图摘要",
];

const results = [
  "通过",
  "等待",
  "重试",
  "已完成",
  "需复核",
];

const totalDevices = 3;
let visibleCount = totalDevices;
let tick = 0;

function escapeHtml(value) {
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function deviceData(index) {
  const state = states[(index + Math.floor(tick / 3)) % states.length];
  const action = actions[(index + tick) % actions.length];
  const result = results[(index * 2 + tick) % results.length];
  const progress = Math.min(99, 18 + ((tick * 9 + index * 13) % 76));
  return {
    id: index + 1,
    title: `手机 ${String(index + 1).padStart(2, "0")}`,
    state,
    action,
    result,
    progress,
  };
}

function renderSummary() {
  const devices = Array.from({ length: visibleCount }, (_, index) => deviceData(index));
  const alive = devices.filter((device) => device.state[1] === "state-ok").length;
  const review = devices.filter((device) => device.state[1] === "state-bad").length;
  monitorSummary.innerHTML = `
    <span class="summary-pill"><i class="summary-dot"></i>在线 <b>${visibleCount}</b></span>
    <span class="summary-pill"><i class="summary-dot ok"></i>存活 <b>${alive}</b></span>
    <span class="summary-pill"><i class="summary-dot bad"></i>接管 <b>${review}</b></span>
  `;
}

function renderCard(device, isNew) {
  return `
    <article class="phone-card ${isNew ? "is-new" : ""}" data-phone="${device.id}">
      <div class="phone-top">
        <div class="phone-title">
          <b>${escapeHtml(device.title)}</b>
          <span>实时屏幕 / Live Screen</span>
        </div>
        <span class="live-badge">LIVE</span>
      </div>
      <div class="phone-screen">
        <div class="screen-ui">
          <div class="screen-task">
            <div class="screen-status">
              <b>Child Task</b>
              <span>${device.progress}%</span>
            </div>
            <i class="task-progress" style="--progress:${device.progress}%"></i>
          </div>
          <div class="screen-feed">
            <span class="scan-line"></span>
          </div>
        </div>
      </div>
      <div class="telemetry">
        <div class="telemetry-item wide">
          <span>日志</span>
          <b>${escapeHtml(device.action)}</b>
        </div>
        <div class="telemetry-item">
          <span>结果</span>
          <b>${escapeHtml(device.result)}</b>
        </div>
        <div class="telemetry-item ${device.state[1]}">
          <span>存活状态</span>
          <b>${escapeHtml(device.state[0])}</b>
        </div>
      </div>
    </article>
  `;
}

function render() {
  const cards = Array.from({ length: visibleCount }, (_, index) => renderCard(deviceData(index), false));
  monitorGrid.innerHTML = cards.join("");
  renderSummary();
}

function updateLiveData() {
  tick += 1;
  render();
}

render();
window.setInterval(updateLiveData, 1800);
