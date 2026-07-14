// Точка входа: инициализация, роутинг, обработчики.

const screens = {
  home: renderHome,
  cases: renderCases,
  upgrade: renderUpgrade,
  clicker: renderClicker,
  profile: renderProfile,
};
let currentScreen = "home";

async function go(name) {
  currentScreen = name;
  document.querySelectorAll(".screen").forEach((s) => s.classList.remove("active"));
  document.getElementById("screen-" + name).classList.add("active");
  document.querySelectorAll(".nav-item").forEach((n) =>
    n.classList.toggle("active", n.dataset.screen === name));
  window.scrollTo(0, 0);
  try { await screens[name](); } catch (e) { toast(e.message); }
}

// Инициализация Telegram
function initTelegram() {
  if (window.Telegram && Telegram.WebApp) {
    const w = Telegram.WebApp;
    try { w.ready(); w.expand(); } catch (e) {}
  }
}

// Локальное «живое» обновление баланса пассивным доходом
function startLiveTimers() {
  setInterval(() => {
    const s = Store.state;
    if (!s) return;
    // пассивный доход
    if (s.per_second_income > 0) {
      s.balance += (s.per_second_income * s.income_multiplier) / 10;
      renderHeader();
      const cb = document.getElementById("clickBalance");
      if (cb && currentScreen === "clicker") cb.textContent = fmt(s.balance);
    }
  }, 100);

  // Таймеры каждую секунду (ежедневный бонус, буст)
  setInterval(() => {
    const s = Store.state;
    if (!s) return;
    if (s.daily_seconds_left > 0) s.daily_seconds_left--;
    if (s.boost_active && s.boost_seconds_left > 0) {
      s.boost_seconds_left--;
      if (s.boost_seconds_left <= 0) { s.boost_active = false; s.income_multiplier = 1; }
    }
    const dt = document.getElementById("dailyTimer");
    if (dt) dt.textContent = fmtTime(s.daily_seconds_left);
    const boostBtn = document.getElementById("boostBtn");
    if (boostBtn && s.boost_active) boostBtn.textContent = fmtTime(s.boost_seconds_left);
  }, 1000);
}

// ---------- Обработчики (делегирование) ----------
document.addEventListener("click", async (e) => {
  const t = e.target;

  // Навигация по нижнему меню
  const nav = t.closest(".nav-item");
  if (nav) { go(nav.dataset.screen); return; }

  // Кнопки с data-nav
  const navBtn = t.closest("[data-nav]");
  if (navBtn) {
    if (navBtn.dataset.upTab) upgradeTab = navBtn.dataset.upTab;
    go(navBtn.dataset.nav);
    return;
  }

  // Ежедневный бонус
  if (t.closest("#dailyBtn")) {
    const r = await API.daily();
    if (r.ok) { Store.set(r.state); toast(`Бонус +${fmt(r.reward)} ◎`); haptic("success"); renderHome(); }
    else toast("Бонус ещё не готов");
    return;
  }

  // Открытие кейса (страница кейсов)
  const caseCard = t.closest("[data-case]");
  if (caseCard) { openCaseFlow(Number(caseCard.dataset.case)); return; }

  // Буст
  if (t.closest("#boostBtn")) {
    const r = await API.boost();
    if (r.ok) { Store.set(r.state); toast("Буст x2 активирован!"); haptic("success"); renderClicker(); }
    else toast(r.reason === "not_enough" ? "Недостаточно монет" : "Буст уже активен");
    return;
  }

  // Покупка улучшения
  const upBtn = t.closest("[data-upgrade]");
  if (upBtn) {
    const r = await API.upgrade(upBtn.dataset.upgrade);
    if (r.ok) { Store.set(r.state); toast("Улучшено!"); haptic("light"); renderClicker(); }
    else toast("Недостаточно монет");
    return;
  }

  // Табы апгрейда
  const tab = t.closest("[data-tab]");
  if (tab) { upgradeTab = tab.dataset.tab; selUpgradeInv = null; selUpgradeTarget = null; selContract.clear(); renderUpgrade(); return; }

  // Выбор предмета для апгрейда
  const invUp = t.closest("[data-inv-upgrade]");
  if (invUp) { selUpgradeInv = Number(invUp.dataset.invUpgrade); selUpgradeTarget = null; renderUpgradeTab(); return; }
  const targetPick = t.closest("[data-target]");
  if (targetPick) { selUpgradeTarget = Number(targetPick.dataset.target); renderUpgradeTab(); return; }

  // Выполнить апгрейд предмета
  if (t.closest("#doUpgrade")) {
    const r = await API.upgradeItem(selUpgradeInv, selUpgradeTarget);
    if (r.ok) {
      Store.set(r.state);
      if (r.success) { toast("Успех! Предмет улучшен"); haptic("success"); }
      else { toast("Неудача. Предмет сгорел"); }
      selUpgradeInv = null; selUpgradeTarget = null;
      renderUpgradeTab();
    } else toast("Ошибка апгрейда");
    return;
  }

  // Контракты: выбор
  const contractPick = t.closest("[data-contract]");
  if (contractPick) {
    const id = Number(contractPick.dataset.contract);
    if (selContract.has(id)) selContract.delete(id); else selContract.add(id);
    renderContractTab();
    return;
  }
  if (t.closest("#doContract")) {
    const r = await API.contract([...selContract]);
    if (r.ok) {
      Store.set(r.state); haptic("success");
      selContract.clear();
      openModal(`<h3>Контракт готов!</h3><div class="drop-view"><img src="${r.result.image}"></div>
        <div style="font-weight:800">${r.result.name}</div><div class="muted">${r.result.subtitle} · ${fmt(r.result.price)} ◎</div>
        <div class="actions"><button class="btn block" onclick="closeModal()">Отлично</button></div>`);
      renderUpgrade();
    } else toast(r.reason === "need_three" ? "Нужно минимум 3 предмета" : "Ошибка");
    return;
  }

  // Сражения
  const battleCard = t.closest("[data-battle]");
  if (battleCard) {
    const r = await API.battle(Number(battleCard.dataset.battle));
    if (!r.ok) { toast(r.reason === "not_enough" ? "Недостаточно монет" : "Ошибка"); return; }
    Store.set(r.state); haptic(r.win ? "success" : "medium");
    openModal(`
      <h3>${r.win ? "Победа! 🟢" : "Поражение"}</h3>
      <div style="display:flex;gap:10px;justify-content:center;margin:12px 0">
        <div><div class="muted">Вы</div><img src="${r.my_item.image}" style="height:80px"><div style="font-size:12px">${fmt(r.my_item.price)} ◎</div></div>
        <div style="align-self:center;font-weight:800">VS</div>
        <div><div class="muted">Бот</div><img src="${r.bot_item.image}" style="height:80px"><div style="font-size:12px">${fmt(r.bot_item.price)} ◎</div></div>
      </div>
      <div class="muted">${r.win ? `Вы выиграли ${fmt(r.pot)} ◎` : "Удачи в следующий раз"}</div>
      <div class="actions"><button class="btn block" onclick="closeModal()">Ок</button></div>`);
    return;
  }

  // Продажа предмета из профиля
  const sellItem = t.closest("[data-sell]");
  if (sellItem) {
    const price = sellItem.dataset.price, name = sellItem.dataset.name;
    const invId = Number(sellItem.dataset.sell);
    openModal(`<h3>Продать предмет?</h3><div class="muted" style="margin:8px 0">${name} за ${fmt(price)} ◎</div>
      <div class="actions"><button class="btn ghost" onclick="closeModal()">Отмена</button>
      <button class="btn gold" id="confirmSell">Продать</button></div>`);
    document.getElementById("confirmSell").addEventListener("click", async () => {
      const r = await API.sell(invId);
      if (r.ok) { Store.set(r.state); toast(`+${fmt(r.amount)} ◎`); }
      closeModal(); renderProfile();
    });
    return;
  }
});

// Клик по кнопке кликера (отдельно, с накоплением тапов)
let pendingTaps = 0, tapTimer = null;
document.addEventListener("pointerdown", (e) => {
  const btn = e.target.closest("#clickBtn");
  if (!btn) return;

  // Мгновенная визуализация
  const s = Store.state;
  const inc = s.click_income * s.income_multiplier;
  s.balance += inc;
  renderHeader();
  const cb = document.getElementById("clickBalance");
  if (cb) cb.textContent = fmt(s.balance);

  // Плавающая монетка
  const float = document.createElement("div");
  float.className = "float-coin";
  float.textContent = "+" + fmt(inc);
  float.style.left = (e.clientX - btn.getBoundingClientRect().left) + "px";
  float.style.top = "80px";
  btn.appendChild(float);
  setTimeout(() => float.remove(), 800);
  haptic("light");

  // Батчим отправку тапов на сервер
  pendingTaps++;
  clearTimeout(tapTimer);
  tapTimer = setTimeout(flushTaps, 400);
});

async function flushTaps() {
  if (pendingTaps <= 0) return;
  const taps = pendingTaps;
  pendingTaps = 0;
  try {
    const r = await API.click(taps);
    // Синхронизируем серверный баланс (авторитетный)
    Store.set(r.state);
    const cb = document.getElementById("clickBalance");
    if (cb && currentScreen === "clicker") cb.textContent = fmt(r.state.balance);
  } catch (e) { /* игнорируем сетевые сбои тапов */ }
}

// ---------- Подменю "Ещё" ----------
document.getElementById("moreBtn").addEventListener("click", (e) => {
  e.stopPropagation();
  const menu = document.getElementById("moreMenu");
  const btn = document.getElementById("moreBtn");
  const isHidden = menu.hidden;
  menu.hidden = !isHidden;
  btn.setAttribute("aria-expanded", String(isHidden));
});
document.addEventListener("click", () => {
  const menu = document.getElementById("moreMenu");
  if (!menu.hidden) {
    menu.hidden = true;
    document.getElementById("moreBtn").setAttribute("aria-expanded", "false");
  }
});

async function openTopModal(sort) {
  document.getElementById("moreMenu").hidden = true;
  openModal(`<div class="loader">Загрузка…</div>`);
  try {
    const data = await API.topPlayers(sort);
    const players = data.players || [];
    const title = sort === "level" ? "ТОП по уровню" : "ТОП по балансу";
    const rows = players.map((p) => `
      <div class="top-row">
        <span class="top-rank">#${p.rank}</span>
        <img class="top-avatar" src="${p.photo_url || "/static/img/avatar.png"}" alt="">
        <span class="top-name">${p.first_name}</span>
        <span class="top-val">${sort === "level" ? "LVL " + p.level : fmt(p.balance) + " ◎"}</span>
      </div>`).join("");
    document.getElementById("modalContent").innerHTML = `
      <h3>${title}</h3>
      <div class="top-list">${rows || '<div class="empty">Нет данных</div>'}</div>
      <div class="actions"><button class="btn block" onclick="closeModal()">Закрыть</button></div>`;
  } catch (e) {
    document.getElementById("modalContent").innerHTML = `<div class="empty">Ошибка загрузки</div>
      <div class="actions"><button class="btn block" onclick="closeModal()">Закрыть</button></div>`;
  }
}

document.getElementById("topLevelBtn").addEventListener("click", () => openTopModal("level"));
document.getElementById("topBalanceBtn").addEventListener("click", () => openTopModal("balance"));

// ---------- Старт ----------
(async function init() {
  initTelegram();
  try {
    Store.set(await API.state());
  } catch (e) {
    document.getElementById("screen-home").innerHTML =
      `<div class="empty">Не удалось загрузить игру.<br>${e.message}</div>`;
    return;
  }
  startLiveTimers();
  go("home");
})();
