// Рендеринг экранов. Каждая функция заполняет свой контейнер.

function itemCardHTML(item, extra = "") {
  const owner = item.owner
    ? `<div class="owner">${item.owner}</div>`
    : `<div class="s">${item.subtitle}</div>`;
  return `
    <div class="drop r-${item.rarity}">
      <div class="thumb"><img src="${item.image}" alt="${item.name}" loading="lazy"></div>
      <div class="info">
        <div class="n">${item.name}</div>
        ${owner}
        <div class="p">${fmt(item.price)} ${COIN}</div>
        ${extra}
      </div>
    </div>`;
}

// ---------- Меню «Ещё»: ТОП игроков ----------
let lbTab = "level";
let lbData = null;

async function openMoreMenu() {
  openModal(`
    <h3>Ещё</h3>
    <div class="more-menu">
      <button class="more-item" data-more="leaderboard">
        <span class="mi-ic">▤</span>
        <span><span class="mi-t">ТОП игроков</span><span class="mi-d">Рейтинг по уровню и балансу</span></span>
      </button>
    </div>
    <div class="actions"><button class="btn ghost block" onclick="closeModal()">Закрыть</button></div>
  `);
}

async function openLeaderboard() {
  lbData = null;
  renderLeaderboard();
  try { lbData = await API.leaderboard(); } catch (e) { lbData = { by_level: [], by_balance: [] }; }
  renderLeaderboard();
}

function renderLeaderboard() {
  const list = lbData ? (lbTab === "level" ? lbData.by_level : lbData.by_balance) : null;
  let rows;
  if (!lbData) {
    rows = `<div class="loader">Загрузка…</div>`;
  } else if (!list.length) {
    rows = `<div class="empty">Пока пусто</div>`;
  } else {
    rows = list.map((u, i) => {
      const rank = i + 1;
      const medal = rank <= 3 ? `rank-${rank}` : "";
      const value = lbTab === "level"
        ? `LVL ${u.level}`
        : `${fmt(u.balance)} ◎`;
      const avatar = u.photo_url || "/static/img/avatar.png";
      return `
        <div class="lb-row">
          <div class="lb-rank ${medal}">${rank}</div>
          <img class="lb-ava" src="${avatar}" alt="">
          <div class="lb-name">${u.first_name}</div>
          <div class="lb-val">${value}</div>
        </div>`;
    }).join("");
  }
  openModal(`
    <h3>ТОП игроков</h3>
    <div class="seg lb-seg">
      <button data-lb="level" class="${lbTab==='level'?'active':''}">По уровню</button>
      <button data-lb="balance" class="${lbTab==='balance'?'active':''}">По балансу</button>
    </div>
    <div class="lb-list">${rows}</div>
    <div class="actions"><button class="btn ghost block" onclick="closeModal()">Закрыть</button></div>
  `);
}

// ---------- HOME ----------
async function renderHome() {
  const s = Store.state;
  const el = document.getElementById("screen-home");
  const daily = s.daily_available;
  const dailyBox = daily
    ? `<div class="daily-card ready" id="dailyBtn"><div class="t">Ежедневный бонус</div><div class="time">Забрать →</div></div>`
    : `<div class="daily-card"><div class="t">Ежедневный бонус</div><div class="time" id="dailyTimer">${fmtTime(s.daily_seconds_left)}</div></div>`;

  const avatar = s.photo_url || "/static/img/avatar.png";

  el.innerHTML = `
    <div class="profile-row">
      <div class="card profile-card">
        <img class="avatar" src="${avatar}" alt="avatar">
        <div style="flex:1;min-width:0">
          <div class="pname">${s.first_name} <span class="verified">✔</span></div>
          <div class="level-line"><span class="level-badge">LEVEL ${s.level}</span><span>XP ${fmtInt(s.xp_into_level)} / ${fmtInt(s.xp_for_next)}</span></div>
          <div class="progress"><span style="width:${(s.level_progress*100).toFixed(1)}%"></span></div>
        </div>
      </div>
      ${dailyBox}
    </div>

    <div class="banner">
      <div class="b-text">
        <h2>ОТКРЫВАЙ <span class="g">КЕЙСЫ CS</span></h2>
        <p>Испытай удачу!</p>
        <button class="btn" data-nav="cases">ОТКРЫТЬ КЕЙСЫ</button>
      </div>
      <img src="/static/img/cases/green_case.png" alt="case">
    </div>

    <div class="tiles">
      <button class="tile" data-nav="cases"><div class="ti">▣</div><div class="tn">Кейсы</div><div class="td">Открывай</div></button>
      <button class="tile" data-nav="upgrade"><div class="ti">▲</div><div class="tn">Апгрейд</div><div class="td">Улучшай</div></button>
      <button class="tile" data-up-tab="contract" data-nav="upgrade"><div class="ti">▤</div><div class="tn">Контракты</div><div class="td">Создавай</div></button>
      <button class="tile" data-up-tab="battle" data-nav="upgrade"><div class="ti">⚔</div><div class="tn">Сражения</div><div class="td">Побеждай</div></button>
    </div>

    <div class="section-title"><span class="ico">◆</span> Лучшие дропы</div>
    <div class="drops-row" id="bestDrops"><div class="loader">Загрузка…</div></div>

    <div class="section-title"><span class="ico">▣</span> Бесплатные кейсы <span class="link" data-nav="cases">Смотреть все</span></div>
    <div class="case-grid" id="freeCases"><div class="loader">Загрузка…</div></div>
  `;

  // Лучшие дропы — последние дорогие предметы реальных игроков (> 15 000)
  try {
    const drops = (await API.bestDrops()).drops;
    const box = document.getElementById("bestDrops");
    if (box) {
      box.innerHTML = drops.length
        ? drops.map((i) => itemCardHTML(i)).join("")
        : `<div class="empty" style="grid-column:1/-1;padding:20px 10px">Пока нет дропов дороже 15 000 ◎</div>`;
    }
  } catch (e) {}

  // Бесплатные кейсы
  if (!Store.cases) { try { Store.cases = (await API.cases()).cases; } catch (e) {} }
  if (Store.cases) {
    const free = Store.cases.filter((c) => c.is_free);
    const list = free.length ? free : Store.cases.slice(0, 2);
    document.getElementById("freeCases").innerHTML = list.map((c) => caseCardHTML(c)).join("");
  }
}

// ---------- CASES ----------
function caseCardHTML(c) {
  let price;
  if (c.is_free) {
    const ready = Store.state ? Store.state.free_case_available : true;
    price = ready
      ? `<span class="free-tag">Бесплатно</span>`
      : `<span class="cd-tag" data-free-timer>${fmtTime(Store.state.free_case_seconds_left)}</span>`;
  } else {
    price = `${fmt(c.price)} ${COIN}`;
  }
  return `
    <div class="case-card" data-case="${c.id}">
      <div class="cimg"><img src="${c.image}" alt="${c.name}"></div>
      <div class="cn">${c.name}</div>
      <div class="cp">${price}</div>
    </div>`;
}

async function renderCases() {
  const el = document.getElementById("screen-cases");
  el.innerHTML = `<div class="section-title"><span class="ico">▣</span> Кейсы</div><div class="case-grid" id="allCases"><div class="loader">Загрузка…</div></div>`;
  if (!Store.cases) Store.cases = (await API.cases()).cases;
  document.getElementById("allCases").innerHTML = Store.cases.map((c) => caseCardHTML(c)).join("");
}

// Открытие кейса с анимацией рулетки
async function openCaseFlow(caseId) {
  const c = Store.cases.find((x) => x.id === caseId);
  if (!c) return;
  if (!c.is_free && Store.state.balance < c.price) { toast("Недостаточно монет"); return; }

  let result;
  try { result = await API.openCase(caseId); }
  catch (e) { toast(e.message); return; }
  if (!result.ok) {
    if (result.reason === "cooldown") toast(`Бесплатный кейс через ${fmtTime(result.seconds_left)}`);
    else if (result.reason === "not_enough") toast("Недостаточно монет");
    else toast("Ошибка");
    return;
  }
  Store.set(result.state);

  const won = result.item;
  // Строим ленту рулетки
  const pool = c.items.length ? c.items : [won];
  const strip = [];
  for (let i = 0; i < 40; i++) strip.push(pool[Math.floor(Math.random() * pool.length)]);
  const winIndex = 35;
  strip[winIndex] = won;

  const stripHTML = strip.map((i) => `<div class="roll-item r-${i.rarity}"><img src="${i.image}" alt=""></div>`).join("");
  openModal(`
    <h3>${c.name}</h3>
    <div class="roller-wrap"><div class="roller" id="roller">${stripHTML}</div></div>
    <div id="rollResult" style="min-height:20px;margin-top:12px"></div>
  `);

  requestAnimationFrame(() => {
    const roller = document.getElementById("roller");
    const itemW = 108; // 100 + 8 gap
    const center = roller.parentElement.offsetWidth / 2 - itemW / 2;
    const offset = winIndex * itemW - center;
    roller.style.transform = `translateX(${-offset}px)`;
  });

  setTimeout(() => {
    haptic("success");
    document.getElementById("rollResult").innerHTML = `
      <div style="font-weight:800;font-size:16px">${won.name}</div>
      <div class="muted">${won.subtitle} · ${fmt(won.price)} ◎</div>
      <div class="actions">
        <button class="btn ghost" onclick="closeModal()">В инвентарь</button>
        <button class="btn gold" id="sellWon">Продать за ${fmt(won.price)} ◎</button>
      </div>`;
    document.getElementById("sellWon").addEventListener("click", async () => {
      // Продаём последний полученный (по item) — берём свежий инвентарь
      const inv = (await API.inventory()).items;
      const match = inv.find((x) => x.id === won.id);
      if (match) {
        const r = await API.sell(match.inv_id);
        if (r.ok) { Store.set(r.state); toast(`+${fmt(r.amount)} ◎`); }
      }
      closeModal();
    });
  }, 4100);
}

// ---------- CLICKER ----------
function renderClicker() {
  const s = Store.state;
  const el = document.getElementById("screen-clicker");
  const boostLabel = s.boost_active ? fmtTime(s.boost_seconds_left) : "Активировать x2";
  el.innerHTML = `
    <div class="clicker-head"><span class="ti">☝</span><div><h2>Кликер</h2><p>Кликай и зарабатывай монеты!</p></div></div>

    <div class="click-zone">
      <div class="click-btn" id="clickBtn">CS</div>
      <div class="balance-big"><span class="coin-badge">◎</span> <span id="clickBalance">${fmt(s.balance)}</span></div>
      <div class="per-click">+${fmt(s.click_income)} за клик</div>
    </div>

    <div class="stat-grid" style="margin-top:16px">
      <div class="mini-stat"><div class="l">Доход за клик</div><div class="v">${fmt(s.click_income)} ${COIN}</div></div>
      <div class="mini-stat"><div class="l">Доход в секунду</div><div class="v">${fmt(s.per_second_income)} ${COIN}</div></div>
    </div>
    <div class="card" style="margin-top:10px;display:flex;align-items:center;gap:12px">
      <div class="si" style="width:38px;height:38px;border-radius:10px;background:var(--green-soft);color:var(--green);display:grid;place-items:center">⚡</div>
      <div style="flex:1"><div class="un" style="font-weight:700">Буст x2</div><div class="ud" style="color:var(--muted);font-size:12px">Активные усиления</div></div>
      <button class="btn ${s.boost_active ? 'ghost' : ''}" id="boostBtn" ${s.boost_active ? 'disabled' : ''}>${boostLabel}</button>
    </div>

    <div class="section-title"><span class="ico">▲</span> Улучшения</div>
    <div class="card" id="upgradeList">${upgradesHTML(s)}</div>
  `;
}

function upgradesHTML(s) {
  const icons = { click: "☝", income: "◷", autoclick: "▮" };
  return s.upgrades.map((u) => {
    const afford = s.balance >= u.cost;
    return `
      <div class="up-row">
        <div class="ui">${icons[u.kind] || "▲"}</div>
        <div class="um">
          <div class="un">${u.title}</div>
          <div class="ud">Уровень ${u.level}</div>
        </div>
        <div class="plus-val">+${fmt(u.step)}</div>
        <button class="buy" data-upgrade="${u.kind}" ${afford ? "" : "disabled"}>
          ${fmtInt(u.cost)} <span class="cc">◎</span>
        </button>
      </div>`;
  }).join("");
}

// ---------- UPGRADE / CONTRACTS / BATTLES ----------
let upgradeTab = "upgrade";
let selUpgradeInv = null, selUpgradeTarget = null;
let selContract = new Set();

async function renderUpgrade() {
  const el = document.getElementById("screen-upgrade");
  el.innerHTML = `
    <div class="seg">
      <button data-tab="upgrade" class="${upgradeTab==='upgrade'?'active':''}">Апгрейд</button>
      <button data-tab="contract" class="${upgradeTab==='contract'?'active':''}">Контракты</button>
      <button data-tab="battle" class="${upgradeTab==='battle'?'active':''}">Сражения</button>
    </div>
    <div id="upgradeBody"><div class="loader">Загрузка…</div></div>`;

  if (upgradeTab === "upgrade") await renderUpgradeTab();
  else if (upgradeTab === "contract") await renderContractTab();
  else await renderBattleTab();
}

async function renderUpgradeTab() {
  const inv = (await API.inventory()).items;
  if (!Store.items) Store.items = (await API.items()).items;
  const body = document.getElementById("upgradeBody");
  if (!inv.length) { body.innerHTML = `<div class="empty">Инвентарь пуст. Откройте кейсы, чтобы получ��ть предметы для апгрейда.</div>`; return; }

  const src = inv.find((x) => x.inv_id === selUpgradeInv) || null;
  const targets = Store.items.filter((i) => !src || i.price > src.item?.price || i.price > (src.price || 0));
  const validTargets = src ? Store.items.filter((i) => i.price > src.price) : [];
  const target = validTargets.find((x) => x.id === selUpgradeTarget) || null;

  let chance = 0;
  if (src && target) chance = Math.min(0.95, (src.price / target.price) * 0.95);

  body.innerHTML = `
    <div class="section-title" style="margin-top:6px"><span class="ico">1</span> Ваш предмет</div>
    <div class="inv-grid">${inv.map((i) => invPickHTML(i, i.inv_id === selUpgradeInv)).join("")}</div>
    ${src ? `
      <div class="section-title"><span class="ico">2</span> Цель апгрейда</div>
      <div class="inv-grid">${validTargets.map((t) => targetPickHTML(t, t.id === selUpgradeTarget)).join("") || '<div class="empty">Нет более дорогих предметов</div>'}</div>
    ` : ""}
    ${src && target ? `
      <div class="card" style="margin-top:14px;text-align:center">
        <div class="l" style="color:var(--muted)">Шанс успеха</div>
        <div style="font-size:30px;font-weight:800;color:var(--green)">${(chance*100).toFixed(1)}%</div>
        <button class="btn block" id="doUpgrade" style="margin-top:10px">Апгрейдить</button>
      </div>` : ""}
  `;
}

function invPickHTML(i, selected) {
  return `<div class="inv-item r-${i.rarity} ${selected?'selected':''}" data-inv-upgrade="${i.inv_id}">
    <img src="${i.image}" alt=""><div class="n">${i.name}</div><div class="p">${fmt(i.price)} ◎</div></div>`;
}
function targetPickHTML(i, selected) {
  return `<div class="inv-item r-${i.rarity} ${selected?'selected':''}" data-target="${i.id}">
    <img src="${i.image}" alt=""><div class="n">${i.name}</div><div class="p">${fmt(i.price)} ◎</div></div>`;
}

async function renderContractTab() {
  const inv = (await API.inventory()).items;
  const body = document.getElementById("upgradeBody");
  if (inv.length < 3) { body.innerHTML = `<div class="empty">Для контракта нужно минимум 3 предмета в инвентаре.</div>`; return; }
  const chosen = inv.filter((i) => selContract.has(i.inv_id));
  const total = chosen.reduce((a, b) => a + b.price, 0);
  body.innerHTML = `
    <p style="color:var(--muted);font-size:13px;margin:0 2px 10px">Выберите 3+ предмета. Вы получите один новый случайный предмет.</p>
    <div class="inv-grid">${inv.map((i) => `<div class="inv-item r-${i.rarity} ${selContract.has(i.inv_id)?'selected':''}" data-contract="${i.inv_id}">
      <img src="${i.image}" alt=""><div class="n">${i.name}</div><div class="p">${fmt(i.price)} ◎</div></div>`).join("")}</div>
    <div class="card" style="margin-top:14px;text-align:center">
      <div style="color:var(--muted)">Выбрано: ${chosen.length} · Сумма: ${fmt(total)} ◎</div>
      <button class="btn block" id="doContract" style="margin-top:10px" ${chosen.length>=3?'':'disabled'}>Создать контракт</button>
    </div>`;
}

async function renderBattleTab() {
  if (!Store.cases) Store.cases = (await API.cases()).cases;
  const body = document.getElementById("upgradeBody");
  const paidCases = Store.cases.filter((c) => !c.is_free);
  body.innerHTML = `
    <p style="color:var(--muted);font-size:13px;margin:0 2px 10px">Сразись с ботом на кейсе — у кого дороже дроп, тот забирает оба.</p>
    <div class="case-grid">${paidCases.map((c) => `
      <div class="case-card" data-battle="${c.id}">
        <div class="cimg"><img src="${c.image}" alt=""></div>
        <div class="cn">${c.name}</div>
        <div class="cp">${c.is_free ? '<span class="free-tag">Бесплатно</span>' : fmt(c.price)+' ◎'}</div>
        <button class="btn block" style="margin-top:8px">В бой</button>
      </div>`).join("")}</div>`;
}

// ---------- PROFILE ----------
async function renderProfile() {
  const s = Store.state;
  const el = document.getElementById("screen-profile");
  const avatar = s.photo_url || "/static/img/avatar.png";
  el.innerHTML = `
    <div class="card profile-card" style="margin-top:8px">
      <img class="avatar" style="width:64px;height:64px" src="${avatar}" alt="avatar">
      <div style="flex:1">
        <div class="pname" style="font-size:17px">${s.first_name} <span class="verified">✔</span></div>
        <div class="level-line"><span class="level-badge">LEVEL ${s.level}</span><span>XP ${fmtInt(s.xp_into_level)} / ${fmtInt(s.xp_for_next)}</span></div>
        <div class="progress"><span style="width:${(s.level_progress*100).toFixed(1)}%"></span></div>
      </div>
    </div>
    <div class="stat-grid">
      <div class="mini-stat"><div class="l">Баланс</div><div class="v">${fmt(s.balance)} ${COIN}</div></div>
      <div class="mini-stat"><div class="l">Всего кликов</div><div class="v">${fmtInt(s.total_clicks)}</div></div>
      <div class="mini-stat"><div class="l">Кейсов открыто</div><div class="v">${fmtInt(s.cases_opened)}</div></div>
      <div class="mini-stat"><div class="l">Доход/сек</div><div class="v">${fmt(s.per_second_income)} ${COIN}</div></div>
    </div>
    <div class="section-title"><span class="ico">▣</span> Инвентарь</div>
    <div class="inv-grid" id="profileInv"><div class="loader">Загрузка…</div></div>
  `;
  const inv = (await API.inventory()).items;
  const box = document.getElementById("profileInv");
  if (!inv.length) { box.outerHTML = `<div class="empty">Инвентарь пуст</div>`; return; }
  box.innerHTML = inv.map((i) => `
    <div class="inv-item r-${i.rarity}" data-sell="${i.inv_id}" data-price="${i.price}" data-name="${i.name}">
      <img src="${i.image}" alt=""><div class="n">${i.name}</div><div class="p">${fmt(i.price)} ◎</div>
    </div>`).join("");
}
