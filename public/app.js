const form = document.querySelector("#downloadForm");
const urlsInput = document.querySelector("#urls");
const message = document.querySelector("#message");
const jobsNode = document.querySelector("#jobs");
const jobCount = document.querySelector("#jobCount");
const toolStatus = document.querySelector("#toolStatus");
const clearButton = document.querySelector("#clearButton");
const setupBox = document.querySelector("#setupBox");

let polling = null;

function statusText(status) {
  return {
    queued: "รอคิว",
    downloading: "กำลังโหลด",
    done: "เสร็จแล้ว",
    failed: "ไม่สำเร็จ"
  }[status] || status;
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function setMessage(text, isError = false) {
  message.textContent = text;
  message.style.color = isError ? "#bb1d2a" : "#52616f";
}

async function fetchJson(url, options) {
  const response = await fetch(url, options);
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || "เกิดข้อผิดพลาด");
  return data;
}

async function checkTools() {
  try {
    const tools = await fetchJson("/api/tools");
    toolStatus.className = `status-pill ${tools.ready ? "ready" : "missing"}`;
    toolStatus.textContent = tools.ready ? "พร้อมใช้งาน" : "ยังขาดเครื่องมือ";
    setupBox.hidden = tools.ready;
  } catch {
    toolStatus.className = "status-pill missing";
    toolStatus.textContent = "ตรวจไม่ได้";
    setupBox.hidden = false;
  }
}

function renderJobs(jobs) {
  jobCount.textContent = `${jobs.length} รายการ`;

  if (jobs.length === 0) {
    jobsNode.innerHTML = '<p class="empty">ยังไม่มีรายการ</p>';
    return;
  }

  jobsNode.innerHTML = jobs.map((job) => {
    const title = job.title || job.url;
    const progress = job.error || job.progress || "รอข้อมูล";
    const link = job.downloadUrl
      ? `<a class="download-link" href="${job.downloadUrl}">ดาวน์โหลด MP3</a>`
      : "";

    return `
      <article class="job">
        <div class="job-top">
          <p class="job-title">${escapeHtml(title)}</p>
          <span class="badge ${job.status}">${statusText(job.status)}</span>
        </div>
        <p class="job-meta">${escapeHtml(progress)}</p>
        ${link}
      </article>
    `;
  }).join("");
}

const downloadedJobs = new Set();
let isInitialLoad = true;

function triggerDownload(url, filename) {
  const a = document.createElement("a");
  a.href = url;
  a.download = filename || "";
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
}

async function refreshJobs() {
  const jobs = await fetchJson("/api/jobs");
  
  for (const job of jobs) {
    if (job.status === "done" && job.downloadUrl) {
      if (isInitialLoad) {
        downloadedJobs.add(job.id);
      } else if (!downloadedJobs.has(job.id)) {
        downloadedJobs.add(job.id);
        triggerDownload(job.downloadUrl, job.title + ".mp3");
      }
    }
  }
  isInitialLoad = false;
  
  renderJobs(jobs);
}

function startPolling() {
  if (polling) return;
  polling = window.setInterval(() => {
    refreshJobs().catch(() => {});
    checkTools().catch(() => {});
  }, 1800);
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  setMessage("กำลังเพิ่มเข้าคิว...");

  try {
    const result = await fetchJson("/api/jobs", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ urls: urlsInput.value })
    });

    const ignored = result.ignored > 0 ? ` ข้ามลิงก์ที่ไม่ใช่ YouTube ${result.ignored} รายการ` : "";
    setMessage(`เพิ่มแล้ว ${result.jobs.length} รายการ${ignored}`);
    urlsInput.value = "";
    await refreshJobs();
  } catch (error) {
    setMessage(error.message, true);
  }
});

clearButton.addEventListener("click", () => {
  urlsInput.value = "";
  setMessage("");
  urlsInput.focus();
});

checkTools();
refreshJobs().then(startPolling).catch(() => renderJobs([]));
