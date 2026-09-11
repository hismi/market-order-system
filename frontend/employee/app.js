const API_BASE_URL = "http://127.0.0.1:8000";
const TOKEN_STORAGE_KEY = "market-order-system-employee-token";

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

const elements = {
  loginPanel: document.querySelector("#loginPanel"),
  loginForm: document.querySelector("#loginForm"),
  loginMessage: document.querySelector("#loginMessage"),
  ordersPanel: document.querySelector("#ordersPanel"),
  ordersTitle: document.querySelector("#ordersTitle"),
  statusTabs: document.querySelector("#statusTabs"),
  ordersList: document.querySelector("#ordersList"),
  orderCount: document.querySelector("#orderCount"),
  userText: document.querySelector("#userText"),
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
  elements.refreshButton.addEventListener("click", loadOrders);
  elements.statusTabs.addEventListener("click", (event) => {
    const button = event.target.closest("button[data-status]");
    if (!button) return;
    state.selectedStatus = button.dataset.status;
    renderStatusTabs();
    loadOrders();
  });
}

async function init() {
  bindEvents();

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
}

async function loadOrders() {
  elements.ordersList.innerHTML = `<div class="empty-state">Siparişler yükleniyor.</div>`;
  try {
    state.orders = await apiFetch(`/api/employee/orders?status=${state.selectedStatus}`);
    renderOrders();
  } catch (error) {
    elements.ordersList.innerHTML = `<div class="empty-state">${escapeHtml(error.message)}</div>`;
  }
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
    throw new Error(data?.detail?.message || data?.detail || "İstek başarısız oldu.");
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
  const diffMs = Date.now() - new Date(value).getTime();
  const minutes = Math.max(Math.floor(diffMs / 60000), 0);
  if (minutes < 1) return "Az önce";
  if (minutes < 60) return `${minutes} dakika önce`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours} saat önce`;
  return `${Math.floor(hours / 24)} gün önce`;
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
