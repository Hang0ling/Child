const BASE_WIDTH = 1280;
const BASE_HEIGHT = 832;
const EPISODE_MS = 10000;

const stage = document.getElementById("stage");
const dots = [...document.querySelectorAll(".global-dot")];
const runSegments = [...document.querySelectorAll(".run-segments i")];
const episodeFill = document.getElementById("episodeFill");
const episodePercent = document.getElementById("episodePercent");

const TOTAL_EPISODES = runSegments.length;

const workflowClasses = [
  "sources-active",
  "decision-active",
  "memory-selected",
  "agent-active",
  "transfer-active",
  "execution-active",
  "lane1-done",
  "lane2-done",
  "lane3-done",
  "judge-active",
  "judge-pulse",
  "choice-continue",
  "choice-next",
  "choice-close",
  "summarizer-active",
  "trajectory-active",
  "return-active",
];

const paths = {
  sources: [
    "M78 318 C78 366 72 424 68 466",
    "M204 318 C186 384 112 474 72 560",
    "M364 318 C338 348 316 382 310 418",
  ],
  decision: [
    "M68 466 L98 438 L132 462 L165 450 L206 424 L258 446 L220 492 L182 472 L145 506 L106 488 C92 532 86 574 84 610",
    "M72 560 L106 524 L150 548 L182 516 L224 537 L254 570 L196 586 L168 580 L128 560 L90 584 C128 606 188 610 238 610",
    "M310 418 L432 418 L432 458 L310 458 L310 500 L432 500 L432 548 L310 548 L310 592 C328 608 356 612 382 610",
  ],
  decisionToAgent: [
    "M84 610 C84 650 102 690 110 720",
    "M238 610 C238 650 248 690 250 720",
    "M382 610 C382 650 388 690 390 720",
  ],
  agentToExecution: [
    "M110 720 C250 722 478 438 552 438",
    "M250 720 C380 690 478 568 552 568",
    "M390 720 C465 720 480 698 552 698",
  ],
  lanes: [
    "M552 438 L637 438",
    "M552 568 L637 568",
    "M552 698 L637 698",
  ],
  laneDone: [
    "M552 438 C730 438 890 476 1000 486",
    "M552 568 C730 568 890 522 1008 486",
    "M552 698 C730 698 890 584 1016 486",
  ],
  choices: {
    "choice-continue": [
      "M1000 486 C980 490 958 498 956 508",
      "M1008 486 C984 492 960 500 956 508",
      "M1016 486 C988 494 962 502 956 508",
    ],
    "choice-next": [
      "M1000 486 C1022 490 1060 498 1064 508",
      "M1008 486 C1030 492 1062 500 1064 508",
      "M1016 486 C1038 494 1064 502 1064 508",
    ],
    "choice-close": [
      "M1000 486 C1060 490 1168 500 1174 508",
      "M1008 486 C1068 494 1170 502 1174 508",
      "M1016 486 C1076 498 1172 504 1174 508",
    ],
  },
  returns: {
    "choice-continue": [
      "M956 630 C850 666 620 650 438 492",
      "M956 630 C780 675 560 620 306 492",
      "M956 630 C720 688 470 604 164 492",
    ],
    "choice-next": [
      "M1064 630 C910 690 650 660 438 492",
      "M1064 630 C850 704 570 638 306 492",
      "M1064 630 C780 716 470 612 164 492",
    ],
  },
  closeToSummary: [
    "M1166 630 L1166 674",
    "M1174 630 L1174 674",
    "M1182 630 L1182 674",
  ],
  summaryToTrajectory: [
    "M1104 674 C1094 560 1134 410 1144 314",
    "M1112 674 C1098 560 1138 410 1144 314",
    "M1120 674 C1102 560 1142 410 1144 314",
  ],
};

const routeByDot = ["choice-continue", "choice-next", "choice-next"];
const laneDurations = [460, 560, 500];
const laneLoops = [8, 11, 12];
const laneDelays = [0, 120, 240];

let timers = [];
let progressFrame = 0;
let episodeIndex = 0;
let episodeStart = 0;
let currentProgress = 0;
let nextEpisodeRequested = false;
let episodeCompleted = false;
let planClosing = false;

function fitStage() {
  const scale = Math.min(window.innerWidth / BASE_WIDTH, window.innerHeight / BASE_HEIGHT);
  stage.style.transform = `translate(-50%, -50%) scale(${scale})`;
}

function after(delay, fn) {
  const timer = window.setTimeout(fn, delay);
  timers.push(timer);
  return timer;
}

function clearFlowTimers() {
  timers.forEach((timer) => window.clearTimeout(timer));
  timers = [];
}

function clearProgressTimer() {
  if (progressFrame) {
    window.cancelAnimationFrame(progressFrame);
    progressFrame = 0;
  }
}

function setDot(dot, path, options = {}) {
  const {
    duration = 1000,
    delay = 0,
    iterations = 1,
    mode = "travel",
    opacity = 1,
  } = options;

  dot.style.animation = "none";
  dot.style.offsetPath = `path("${path}")`;
  dot.style.offsetDistance = "0%";
  dot.style.opacity = opacity;
  dot.getBoundingClientRect();
  dot.style.animationName = mode === "ping" ? "flowPing" : "flowTravel";
  dot.style.animationDuration = `${duration}ms`;
  dot.style.animationDelay = `${delay}ms`;
  dot.style.animationIterationCount = iterations;
  dot.style.animationTimingFunction = "linear";
  dot.style.animationFillMode = "forwards";
}

function animateDot(index, path, options = {}, callback) {
  const dot = dots[index];
  const duration = options.duration || 1000;
  const delay = options.delay || 0;
  const iterations = options.iterations || 1;

  setDot(dot, path, options);

  if (callback && Number.isFinite(iterations)) {
    after(delay + duration * iterations, callback);
  }
}

function hideDots(exceptIndex = -1) {
  dots.forEach((dot, index) => {
    if (index === exceptIndex) return;
    dot.style.animation = "none";
    dot.style.opacity = 0;
  });
}

function clearFlowClasses() {
  stage.classList.remove(...workflowClasses);
}

function pulseJudgeBeam() {
  stage.classList.remove("judge-pulse");
  stage.getBoundingClientRect();
  stage.classList.add("judge-pulse");
  after(820, () => stage.classList.remove("judge-pulse"));
}

function setEpisodeProgress(progress) {
  const percent = Math.round(progress * 100);
  episodeFill.style.width = `${percent}%`;
  episodePercent.textContent = `${percent}%`;
}

function setRunPlanProgress(progress) {
  runSegments.forEach((segment, index) => {
    let fill = 0;

    if (index < episodeIndex) {
      fill = 100;
    } else if (index === episodeIndex) {
      fill = Math.round(progress * 100);
    }

    segment.style.setProperty("--fill", `${fill}%`);
    segment.classList.toggle("done", fill >= 100);
    segment.classList.toggle("active", index === episodeIndex && fill < 100);
  });
}

function updateProgress(now) {
  currentProgress = Math.min((now - episodeStart) / EPISODE_MS, 1);
  setEpisodeProgress(currentProgress);
  setRunPlanProgress(currentProgress);

  if (currentProgress >= 1) {
    if (nextEpisodeRequested || episodeIndex === TOTAL_EPISODES - 1) {
      completeEpisode();
      return;
    }

    progressFrame = window.requestAnimationFrame(updateProgress);
    return;
  }

  progressFrame = window.requestAnimationFrame(updateProgress);
}

function startProgress() {
  clearProgressTimer();
  currentProgress = 0;
  episodeStart = performance.now();
  setEpisodeProgress(0);
  setRunPlanProgress(0);
  progressFrame = window.requestAnimationFrame(updateProgress);
}

function requestNextEpisode() {
  nextEpisodeRequested = true;

  if (currentProgress >= 1) {
    completeEpisode();
  }
}

function completeEpisode() {
  if (episodeCompleted || planClosing) return;

  episodeCompleted = true;
  clearProgressTimer();
  currentProgress = 1;
  setEpisodeProgress(1);
  setRunPlanProgress(1);

  if (episodeIndex >= TOTAL_EPISODES - 1) {
    triggerPlanClose();
    return;
  }

  episodeIndex += 1;
  after(740, () => startEpisodeCycle(false));
}

function moveToChoice(index) {
  const route = routeByDot[index];

  pulseJudgeBeam();
  stage.classList.add("judge-active", route);
  animateDot(index, paths.choices[route][index], { duration: 360 }, () => {
    stage.classList.add("return-active");

    if (route === "choice-next") {
      requestNextEpisode();
    }

    if (planClosing) return;

    animateDot(index, paths.returns[route][index], { duration: 620 }, () => {
      if (route === "choice-continue" && !episodeCompleted && !planClosing) {
        startDotCycle(index);
      }
    });
  });
}

function finishLane(index) {
  stage.classList.add("judge-active", `lane${index + 1}-done`);
  animateDot(index, paths.laneDone[index], { duration: 340 }, () => moveToChoice(index));
}

function startLane(index) {
  animateDot(
    index,
    paths.lanes[index],
    {
      duration: laneDurations[index],
      delay: laneDelays[index],
      iterations: laneLoops[index],
      mode: "ping",
    },
    () => finishLane(index),
  );
}

function startExecution(index) {
  if (!stage.classList.contains("execution-active")) {
    stage.classList.add("execution-active");
  }

  startLane(index);
}

function enterExecution(index) {
  stage.classList.add("transfer-active");
  animateDot(
    index,
    paths.agentToExecution[index],
    { duration: 600 + index * 40 },
    () => startExecution(index),
  );
}

function enterAgent(index) {
  stage.classList.add("agent-active");
  animateDot(index, paths.decisionToAgent[index], { duration: 440 + index * 30 }, () => enterExecution(index));
}

function startDotCycle(index) {
  stage.classList.add("decision-active");
  animateDot(index, paths.decision[index], { duration: 1180 + index * 80 }, () => enterAgent(index));
}

function startDecisionCycle() {
  stage.classList.remove("sources-active");
  stage.classList.add("decision-active");

  after(980, () => stage.classList.add("memory-selected"));
  dots.forEach((_, index) => startDotCycle(index));
}

function startEpisodeCycle(withSources) {
  clearFlowTimers();
  clearFlowClasses();
  hideDots();

  nextEpisodeRequested = false;
  episodeCompleted = false;
  planClosing = false;
  startProgress();

  if (withSources) {
    stage.classList.add("sources-active");
    dots.forEach((_, index) => {
      animateDot(index, paths.sources[index], { duration: 720 + index * 80 }, () => startDotCycle(index));
    });
    after(980, () => stage.classList.add("memory-selected"));
    after(1120, () => stage.classList.remove("sources-active"));
    return;
  }

  startDecisionCycle();
}

function triggerPlanClose() {
  planClosing = true;
  clearFlowTimers();
  stage.classList.remove(
    "judge-pulse",
    "choice-continue",
    "choice-next",
    "return-active",
    "execution-active",
    "lane1-done",
    "lane2-done",
    "lane3-done",
  );
  stage.classList.add("judge-active", "choice-close");
  hideDots(1);

  animateDot(1, paths.choices["choice-close"][1], { duration: 520 }, () => {
    stage.classList.add("summarizer-active");
    animateDot(1, paths.closeToSummary[1], { duration: 760 }, () => {
      after(680, () => {
        stage.classList.add("trajectory-active");
        animateDot(1, paths.summaryToTrajectory[1], { duration: 1300 }, () => {
          after(1800, restartRunPlan);
        });
      });
    });
  });
}

function restartRunPlan() {
  clearFlowTimers();
  clearProgressTimer();
  clearFlowClasses();
  hideDots();
  episodeIndex = 0;
  nextEpisodeRequested = false;
  episodeCompleted = false;
  planClosing = false;
  setEpisodeProgress(0);
  setRunPlanProgress(0);
  after(360, () => startEpisodeCycle(true));
}

window.addEventListener("resize", fitStage);
document.addEventListener("click", (event) => {
  const logTarget = event.target.closest("[data-log-topic]");
  if (logTarget) {
    window.location.href = `../日志查看/index.html?topic=${encodeURIComponent(logTarget.dataset.logTopic)}`;
    return;
  }

  const debugTarget = event.target.closest("[data-debug-topic]");
  if (debugTarget) {
    window.location.href = `../调试台/index.html?module=${encodeURIComponent(debugTarget.dataset.debugTopic)}`;
  }
});
fitStage();
restartRunPlan();
