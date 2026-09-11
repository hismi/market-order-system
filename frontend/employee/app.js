const API_BASE_URL = "http://127.0.0.1:8000";
const TOKEN_STORAGE_KEY = "market-order-system-employee-token";
const SOUND_ENABLED_STORAGE_KEY = "market-order-system-employee-sound-enabled";
const ORDER_REFRESH_INTERVAL_MS = 15000;

const statusLabels = {
  NEW: "Yeni",
  PREPARING: "Hazırlanıyor",
  ON_THE_WAY: "Yolda",
  DELIVERED: "Tamamlandı",
  CANCELLED: "İptal",
};

const paymentLabels = {
  CASH_ON_DELIVERY: "Kapıda Nakit",
  CARD_ON_DELIVERY: "Kapıda Kart / POS",
};

const unavailableLabels = {
  CALL_CUSTOMER: "Beni ara",
  REMOVE_ITEM: "Ürünü çıkar",
  SEND_SIMILAR: "Benzer ürün gönderilebilir",
};

const state = {
  token: window.localStorage.getItem(TOKEN_STORAGE_KEY),
  currentUser: null,
  selectedStatus: "NEW",
  orders: [],
};

let orderRefreshTimer = null;
let isLoadingOrders = false;
const audioAlerts = {
  enabled: window.localStorage.getItem(SOUND_ENABLED_STORAGE_KEY) !== "false",
  context: null,
  unlocked: false,
  knownNewOrderKeys: new Set(),
  hasOrderSnapshot: false,
};

const elements = {
  loginPanel: document.querySelector("#loginPanel"),
  loginForm: document.querySelector("#loginForm"),
  loginMessage: document.querySelector("#loginMessage"),
  ordersPanel: document.querySelector("#ordersPanel"),
  ordersTitle: document.querySelector("#ordersTitle"),
  statusTabs: document.querySelector("#statusTabs"),
  ordersList: document.querySelector("#ordersList"),
  orderCount: document.querySelector("#orderCount"),
  autoRefreshText: document.querySelector("#autoRefreshText"),
  userText: document.querySelector("#userText"),
  soundToggleButton: document.querySelector("#soundToggleButton"),
  refreshButton: document.querySelector("#refreshButton"),
  logoutButton: document.querySelector("#logoutButton"),
};

function money(value) {
  return new Intl.NumberFormat("tr-TR", {
    style: "currency",
    currency: "TRY",
  }).format(Number(value));
}

function bindEvents() {
  elements.loginForm.addEventListener("submit", login);
  elements.logoutButton.addEventListener("click", logout);
  elements.soundToggleButton.addEventListener("click", handleSoundToggleClick);
  elements.refreshButton.addEventListener("click", () => {
    unlockAudioAlerts();
    loadOrders();
  });
  elements.statusTabs.addEventListener("click", (event) => {
    const button = event.target.closest("button[data-status]");
    if (!button) return;
    unlockAudioAlerts();
    state.selectedStatus = button.dataset.status;
    renderStatusTabs();
    loadOrders();
  });
}

async function init() {
  bindEvents();
  renderSoundToggle();

  if (!state.token) {
    showLogin();
    return;
  }

  try {
    state.currentUser = await apiFetch("/api/auth/me");
    showOrders();
    await loadOrders();
  } catch {
    logout();
  }
}

async function login(event) {
  event.preventDefault();
  unlockAudioAlerts();
  elements.loginMessage.hidden = true;

  const formData = new FormData(elements.loginForm);
  try {
    const data = await apiFetch("/api/auth/login", {
      method: "POST",
      body: {
        username: formData.get("username"),
        password: formData.get("password"),
      },
      includeAuth: false,
    });

    state.token = data.access_token;
    state.currentUser = {
      username: data.username,
      full_name: data.full_name,
      role: data.role,
    };
    window.localStorage.setItem(TOKEN_STORAGE_KEY, state.token);
    showOrders();
    await loadOrders();
  } catch (error) {
    elements.loginMessage.textContent = error.message;
    elements.loginMessage.hidden = false;
  }
}

function logout() {
  stopOrderAutoRefresh();
  state.token = null;
  state.currentUser = null;
  state.orders = [];
  window.localStorage.removeItem(TOKEN_STORAGE_KEY);
  showLogin();
}

function showLogin() {
  elements.loginPanel.hidden = false;
  elements.ordersPanel.hidden = true;
  elements.logoutButton.hidden = true;
}

function showOrders() {
  elements.loginPanel.hidden = true;
  elements.ordersPanel.hidden = false;
  elements.logoutButton.hidden = false;
  elements.userText.textContent = `${state.currentUser.full_name} (${state.currentUser.role})`;
  renderSoundToggle();
  startOrderAutoRefresh();
}

async function loadOrders(options = {}) {
  const silent = options.silent === true;
  if (isLoadingOrders && silent) return;

  isLoadingOrders = true;
  if (!silent) {
    elements.ordersList.innerHTML = `<div class="empty-state">Siparişler yükleniyor.</div>`;
  }

  try {
    state.orders = await apiFetch(`/api/employee/orders?status=${state.selectedStatus}`);
    renderOrders();
    updateAutoRefreshText();
    if (state.selectedStatus === "NEW") {
      handleNewOrderSnapshot(state.orders, { alert: true });
    }
  } catch (error) {
    if (error.status === 401) {
      logout();
      return;
    }

    if (silent) {
      updateAutoRefreshText("Bağlantı bekleniyor");
    } else {
      elements.ordersList.innerHTML = `<div class="empty-state">${escapeHtml(error.message)}</div>`;
    }
  } finally {
    isLoadingOrders = false;
  }
}

function startOrderAutoRefresh() {
  stopOrderAutoRefresh();
  updateAutoRefreshText("Otomatik yenileme açık");
  orderRefreshTimer = window.setInterval(
    refreshOrdersAndAlerts,
    ORDER_REFRESH_INTERVAL_MS,
  );
}

async function refreshOrdersAndAlerts() {
  await loadOrders({ silent: true });
  if (state.selectedStatus !== "NEW") {
    await checkNewOrdersForAlert();
  }
}

function stopOrderAutoRefresh() {
  if (!orderRefreshTimer) return;
  window.clearInterval(orderRefreshTimer);
  orderRefreshTimer = null;
}

function updateAutoRefreshText(message) {
  const text = message || `Son güncelleme ${formatClock(new Date())}`;
  elements.autoRefreshText.textContent = text;
}

async function checkNewOrdersForAlert() {
  try {
    const newOrders = await apiFetch("/api/employee/orders?status=NEW");
    handleNewOrderSnapshot(newOrders, { alert: true });
  } catch (error) {
    if (error.status === 401) {
      logout();
    }
  }
}

function handleNewOrderSnapshot(orders, options = {}) {
  const shouldAlert = options.alert === true;
  const newOrderKeys = new Set(
    orders
      .filter((order) => order.status === "NEW")
      .map(getOrderAlertKey),
  );
  const newArrivalCount = audioAlerts.hasOrderSnapshot
    ? Array.from(newOrderKeys).filter((key) => !audioAlerts.knownNewOrderKeys.has(key)).length
    : 0;

  audioAlerts.knownNewOrderKeys = newOrderKeys;
  audioAlerts.hasOrderSnapshot = true;

  if (shouldAlert && newArrivalCount > 0) {
    notifyNewOrders(newArrivalCount);
  }
}

function getOrderAlertKey(order) {
  return String(order.id || order.order_number);
}

function notifyNewOrders(count) {
  updateAutoRefreshText(count === 1 ? "Yeni sipariş geldi" : `${count} yeni sipariş geldi`);
  flashDocumentTitle(count);
  playNewOrderAlert();
}

function handleSoundToggleClick() {
  if (!audioAlerts.enabled) {
    audioAlerts.enabled = true;
    window.localStorage.setItem(SOUND_ENABLED_STORAGE_KEY, "true");
    unlockAudioAlerts({ playTest: true });
    return;
  }

  if (!audioAlerts.unlocked) {
    unlockAudioAlerts({ playTest: true });
    return;
  }

  audioAlerts.enabled = false;
  window.localStorage.setItem(
    SOUND_ENABLED_STORAGE_KEY,
    "false",
  );
  renderSoundToggle();
}

async function unlockAudioAlerts(options = {}) {
  if (!audioAlerts.enabled) {
    renderSoundToggle();
    return;
  }

  const AudioContextConstructor = window.AudioContext || window.webkitAudioContext;
  if (!AudioContextConstructor) {
    audioAlerts.enabled = false;
    window.localStorage.setItem(SOUND_ENABLED_STORAGE_KEY, "false");
    renderSoundToggle();
    return;
  }

  try {
    if (!audioAlerts.context) {
      audioAlerts.context = new AudioContextConstructor();
    }
    if (audioAlerts.context.state === "suspended") {
      await audioAlerts.context.resume();
    }
    audioAlerts.unlocked = audioAlerts.context.state === "running";
  } catch {
    audioAlerts.unlocked = false;
  }

  renderSoundToggle();
  if (audioAlerts.unlocked && options.playTest === true) {
    playNewOrderAlert();
  }
}

function playNewOrderAlert() {
  if (!audioAlerts.enabled || !audioAlerts.unlocked || !audioAlerts.context) {
    unlockAudioAlerts();
    return;
  }

  try {
    const startTime = audioAlerts.context.currentTime + 0.02;
    playTone(880, startTime, 0.16);
    playTone(1175, startTime + 0.2, 0.18);
  } catch {
    audioAlerts.unlocked = false;
    renderSoundToggle();
  }
}

function playTone(frequency, startTime, duration) {
  const oscillator = audioAlerts.context.createOscillator();
  const gain = audioAlerts.context.createGain();
  oscillator.type = "sine";
  oscillator.frequency.setValueAtTime(frequency, startTime);
  gain.gain.setValueAtTime(0.0001, startTime);
  gain.gain.exponentialRampToValueAtTime(0.22, startTime + 0.03);
  gain.gain.exponentialRampToValueAtTime(0.0001, startTime + duration);
  oscillator.connect(gain);
  gain.connect(audioAlerts.context.destination);
  oscillator.start(startTime);
  oscillator.stop(startTime + duration + 0.04);
}

function renderSoundToggle() {
  const isReady = audioAlerts.enabled && audioAlerts.unlocked;
  elements.soundToggleButton.classList.toggle("is-muted", !isReady);
  elements.soundToggleButton.setAttribute("aria-pressed", String(audioAlerts.enabled));

  if (!audioAlerts.enabled) {
    elements.soundToggleButton.textContent = "Ses kapalı";
  } else if (!audioAlerts.unlocked) {
    elements.soundToggleButton.textContent = "Sesi Aç";
  } else {
    elements.soundToggleButton.textContent = "Ses açık";
  }
}

function flashDocumentTitle(count) {
  const originalTitle = document.title.replace(/^Yeni sipariş(?: \(\d+\))? - /, "");
  document.title = count === 1
    ? `Yeni sipariş - ${originalTitle}`
    : `Yeni sipariş (${count}) - ${originalTitle}`;

  window.setTimeout(() => {
    if (document.title.startsWith("Yeni sipariş")) {
      document.title = originalTitle;
    }
  }, 8000);
}

function renderStatusTabs() {
  for (const button of elements.statusTabs.querySelectorAll("button[data-status]")) {
    button.classList.toggle("is-active", button.dataset.status === state.selectedStatus);
  }
  elements.ordersTitle.textContent = `${statusLabels[state.selectedStatus]} Siparişler`;
}

function renderOrders() {
  renderStatusTabs();
  elements.orderCount.textContent = `${state.orders.length} sipariş`;

  if (!state.orders.length) {
    elements.ordersList.innerHTML = `<div class="empty-state">Bu durumda sipariş yok.</div>`;
    return;
  }

  elements.ordersList.innerHTML = state.orders.map(renderOrderCard).join("");
}

function renderOrderCard(order) {
  return `
    <article class="order-card">
      <div class="order-top">
        <div>
          <div class="order-number">${escapeHtml(order.order_number)}</div>
          <div class="order-time">${timeAgo(order.created_at)}</div>
        </div>
        <span class="status-badge">${statusLabels[order.status] || order.status}</span>
      </div>

      <div class="order-grid">
        <div class="info-row"><span>Müşteri</span><strong>${escapeHtml(order.customer_first_name)} ${escapeHtml(order.customer_last_name)}</strong></div>
        <div class="info-row"><span>Telefon</span><strong>${escapeHtml(order.phone)}</strong></div>
        <div class="info-row"><span>Bölge</span><strong>${escapeHtml(order.delivery_area_name_snapshot)}</strong></div>
        <div class="info-row"><span>Ödeme</span><strong>${paymentLabels[order.payment_method] || order.payment_method}</strong></div>
        <div class="info-row"><span>Bulunamazsa</span><strong>${unavailableLabels[order.unavailable_policy] || order.unavailable_policy}</strong></div>
        <div class="info-row"><span>Adres</span><strong>${escapeHtml(formatAddress(order))}</strong></div>
        ${order.order_note ? `<div class="info-row"><span>Not</span><strong>${escapeHtml(order.order_note)}</strong></div>` : ""}
        ${order.cancellation_reason ? `<div class="info-row"><span>İptal Sebebi</span><strong>${escapeHtml(order.cancellation_reason)}</strong></div>` : ""}
        <div class="info-row"><span>Ara Toplam</span><strong>${money(order.subtotal)}</strong></div>
        <div class="info-row"><span>Gönderim</span><strong>${money(order.delivery_fee)}</strong></div>
        <div class="info-row"><span>Genel Toplam</span><strong>${money(order.grand_total)}</strong></div>
      </div>

      <div class="items-list">
        ${order.items.map((item) => `
          <div class="item-line">
            <span>${escapeHtml(item.product_name_snapshot)} x ${item.quantity}</span>
            <strong>${money(item.line_total)}</strong>
          </div>
        `).join("")}
      </div>

      ${renderActions(order)}
    </article>
  `;
}

function renderActions(order) {
  if (order.status === "NEW") {
    return `
      <div class="order-actions">
        <button class="primary-button" type="button" onclick="runAction(${order.id}, 'approve')">Onayla</button>
        ${renderCancelControls(order.id, "Reddet")}
      </div>
    `;
  }

  if (order.status === "PREPARING") {
    return `
      <div class="order-actions">
        <button class="primary-button" type="button" onclick="runAction(${order.id}, 'on-the-way')">Yola Çıktı</button>
        ${renderCancelControls(order.id, "İptal Et")}
      </div>
    `;
  }

  if (order.status === "ON_THE_WAY") {
    return `
      <div class="order-actions">
        <button class="primary-button" type="button" onclick="runAction(${order.id}, 'delivered')">Teslim Edildi</button>
        ${renderCancelControls(order.id, "İptal Et")}
      </div>
    `;
  }

  return "";
}

function renderCancelControls(orderId, buttonText) {
  return `
    <div class="action-row">
      <label>
        <span>İptal sebebi</span>
        <select id="rejectReason-${orderId}">
          <option value="OUT_OF_STOCK">Ürün stokta yok</option>
          <option value="OUT_OF_DELIVERY_AREA">Teslimat bölgesi dışında</option>
          <option value="BUSY">Yoğunluk</option>
          <option value="CLOSING_SOON">Market kapanmak üzere</option>
          <option value="CUSTOMER_UNREACHABLE">Müşteriye ulaşılamadı</option>
          <option value="OTHER">Diğer</option>
        </select>
      </label>
      <button class="danger-button" type="button" onclick="rejectOrder(${orderId})">${buttonText}</button>
    </div>
  `;
}

async function runAction(orderId, action) {
  await apiFetch(`/api/employee/orders/${orderId}/${action}`, {
    method: "POST",
  });
  await loadOrders();
}

async function rejectOrder(orderId) {
  const select = document.querySelector(`#rejectReason-${orderId}`);
  await apiFetch(`/api/employee/orders/${orderId}/reject`, {
    method: "POST",
    body: {
      reason: select.value,
    },
  });
  await loadOrders();
}

async function apiFetch(path, options = {}) {
  const includeAuth = options.includeAuth !== false;
  const headers = {
    "Content-Type": "application/json",
  };

  if (includeAuth && state.token) {
    headers.Authorization = `Bearer ${state.token}`;
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: options.method || "GET",
    headers,
    body: options.body ? JSON.stringify(options.body) : undefined,
  });
  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    const message = data?.detail?.message || data?.detail || "İstek başarısız oldu.";
    const error = new Error(message);
    error.status = response.status;
    throw error;
  }

  return data;
}

function formatAddress(order) {
  return [
    order.neighborhood,
    order.street,
    order.apartment,
    order.flat ? `Daire ${order.flat}` : "",
    order.address_line,
  ].filter(Boolean).join(", ");
}

function timeAgo(value) {
  const diffMs = Date.now() - parseApiDate(value).getTime();
  const minutes = Math.max(Math.floor(diffMs / 60000), 0);
  if (minutes < 1) return "Az önce";
  if (minutes < 60) return `${minutes} dakika önce`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours} saat önce`;
  return `${Math.floor(hours / 24)} gün önce`;
}

function parseApiDate(value) {
  const text = String(value || "").trim();
  if (!text) return new Date(Number.NaN);
  if (/[zZ]$|[+-]\d{2}:?\d{2}$/.test(text)) return new Date(text);
  return new Date(`${text}Z`);
}

function formatClock(value) {
  return new Intl.DateTimeFormat("tr-TR", {
    timeStyle: "medium",
  }).format(value);
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

window.runAction = runAction;
window.rejectOrder = rejectOrder;

init();
