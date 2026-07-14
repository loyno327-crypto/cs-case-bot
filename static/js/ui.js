// Общее состояние и UI-утилиты.
const Store = {
  state: null,
  cases: null,
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
