// Общее состояние и UI-утилиты.
const Store = {
  state: null,
  cases: null,
  leaderKind: "level",
  set(s) { if (s) { this.state = s; renderHeader(); } },
};

// Форматирование чисел: 12 450.50
function fmt(n) {
  n = Number(n) || 0;
  return n.toLocaleString("ru-RU", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}
function fmtInt(n) {
  return (Number(n) || 0).toLocaleString("ru-RU");
}
function fmtTime(sec) {
  sec = Math.max(0, Math.floor(sec));
  const h = String(Math.floor(sec / 3600)).padStart(2, "0");
  const m = String(Math.floor((sec % 3600) / 60)).padStart(2, "0");
  const s = String(sec % 60).padStart(2, "0");
  return `${h}:${m}:${s}`;
}

const COIN = '<span class="coin">◎</span>';

// Хедер (баланс)
function renderHeader() {
  const s = Store.state;
  if (!s) return;
  document.getElementById("balanceText").textContent = fmt(s.balance);
}

// Тосты
let toastTimer;
function toast(msg) {
  const el = document.getElementById("toast");
  el.textContent = msg;
  el.classList.add("show");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => el.classList.remove("show"), 1800);
  if (window.Telegram && Telegram.WebApp && Telegram.WebApp.HapticFeedback) {
    try { Telegram.WebApp.HapticFeedback.impactOccurred("light"); } catch (e) {}
  }
}

// Модалка
function openModal(html) {
  document.getElementById("modalContent").innerHTML = html;
  document.getElementById("modal").classList.add("show");
}
function closeModal() {
  document.getElementById("modal").classList.remove("show");
}
document.getElementById("modal").addEventListener("click", (e) => {
  if (e.target.id === "modal") closeModal();
});

// Тактильная отдача
function haptic(type = "light") {
  if (window.Telegram && Telegram.WebApp && Telegram.WebApp.HapticFeedback) {
    try {
      if (type === "success") Telegram.WebApp.HapticFeedback.notificationOccurred("success");
      else Telegram.WebApp.HapticFeedback.impactOccurred(type);
    } catch (e) {}
  }
}

function rarityLabel(r) {
  return {
    common: "Обычный", uncommon: "Необычный", rare: "Редкий",
    mythical: "Мифический", legendary: "Легендарный", ancient: "Тайный",
  }[r] || "Обычный";
}

function playerName(p) {
  return p.first_name || (p.username ? `@${p.username}` : "Игрок");
}

function leaderboardHTML(players, kind) {
  if (!players.length) return `<div class="empty" style="padding:20px 0">Пока нет игроков</div>`;
  return players.map((p, i) => `
    <div class="leader-row">
      <div class="leader-rank">${i + 1}</div>
      <div>
        <div class="leader-name">${playerName(p)}</div>
        <div class="leader-meta">LEVEL ${p.level}</div>
      </div>
      <div class="leader-value">${kind === "balance" ? fmt(p.balance) + " ◎" : "LVL " + p.level}</div>
    </div>`).join("");
}

async function renderLeaderboard(kind = Store.leaderKind) {
  Store.leaderKind = kind;
  const body = document.getElementById("leaderBody");
  if (!body) return;
  body.innerHTML = `<div class="loader" style="padding:20px 0">Загрузка…</div>`;
  try {
    const r = await API.leaderboard(kind);
    body.innerHTML = leaderboardHTML(r.players, kind);
    document.querySelectorAll("[data-leader]").forEach((btn) =>
      btn.classList.toggle("ghost", btn.dataset.leader !== kind));
  } catch (e) {
    body.innerHTML = `<div class="empty" style="padding:20px 0">${e.message}</div>`;
  }
}

function openMoreMenu() {
  openModal(`
    <h3>Еще</h3>
    <div class="leader-tabs">
      <button class="btn" data-leader="level">ТОП уровень</button>
      <button class="btn ghost" data-leader="balance">ТОП баланс</button>
    </div>
    <div class="leader-list" id="leaderBody"></div>
    <div class="actions"><button class="btn ghost" onclick="closeModal()">Закрыть</button></div>
  `);
  renderLeaderboard(Store.leaderKind);
}
