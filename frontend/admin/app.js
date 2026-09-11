const API_BASE_URL = "http://127.0.0.1:8000";
const TOKEN_STORAGE_KEY = "market-order-system-admin-token";
const SOUND_ENABLED_STORAGE_KEY = "market-order-system-admin-sound-enabled";
const ORDER_REFRESH_INTERVAL_MS = 15000;

const statusLabels = {
  NEW: "Yeni",
  PREPARING: "Hazırlanıyor",
  ON_THE_WAY: "Yolda",
  DELIVERED: "Teslim edildi",
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

const roleLabels = {
  ADMIN: "Admin",
  EMPLOYEE: "Çalışan",
};

const auditActionLabels = {
  CATEGORY_CREATED: "Kategori oluşturuldu",
  CATEGORY_UPDATED: "Kategori güncellendi",
  DELIVERY_AREA_CREATED: "Teslimat bölgesi oluşturuldu",
  DELIVERY_AREA_UPDATED: "Teslimat bölgesi güncellendi",
  MARKET_SETTINGS_UPDATED: "Market ayarları güncellendi",
  ORDER_STATUS_CHANGED: "Sipariş durumu değişti",
  PRODUCT_CREATED: "Ürün oluşturuldu",
  PRODUCT_UPDATED: "Ürün güncellendi",
  PRODUCT_DEACTIVATED: "Ürün pasife alındı",
  PRODUCT_IMAGE_UPLOADED: "Ürün görseli yüklendi",
  USER_CREATED: "Kullanıcı oluşturuldu",
  USER_UPDATED: "Kullanıcı güncellendi",
  PASSWORD_CHANGED: "Şifre değiştirildi",
  BACKUP_EXPORTED: "Yedek indirildi",
  BACKUP_RESTORED: "Yedekten geri yüklendi",
};

const auditTargetLabels = {
  categories: "Kategori",
  category: "Kategori",
  delivery_area: "Teslimat Bölgesi",
  delivery_areas: "Teslimat Bölgesi",
  market_settings: "Market Ayarları",
  order: "Sipariş",
  orders: "Sipariş",
  product: "Ürün",
  product_images: "Ürün Görseli",
  products: "Ürün",
  user: "Kullanıcı",
  users: "Kullanıcı",
  backups: "Yedekleme",
};

const state = {
  token: window.localStorage.getItem(TOKEN_STORAGE_KEY),
  currentUser: null,
  activeSection: "system-status",
  settings: null,
  systemStatus: null,
  categories: [],
  products: [],
  deliveryAreas: [],
  orders: [],
  users: [],
  report: null,
  auditLogs: [],
  orderSummary: null,
  orderStatusFilter: "",
  productSearch: "",
};

let orderRefreshTimer = null;
let isLoadingOrders = false;
let isLoadingSystemStatus = false;
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
  adminPanel: document.querySelector("#adminPanel"),
  logoutButton: document.querySelector("#logoutButton"),
  userText: document.querySelector("#userText"),
  sectionTabs: document.querySelector(".section-tabs"),
  sectionPanels: document.querySelectorAll("[data-section-panel]"),

  refreshSystemStatusButton: document.querySelector("#refreshSystemStatusButton"),
  systemStatusMessage: document.querySelector("#systemStatusMessage"),
  statusApiText: document.querySelector("#statusApiText"),
  statusMarketText: document.querySelector("#statusMarketText"),
  statusEnvText: document.querySelector("#statusEnvText"),
  statusPaymentText: document.querySelector("#statusPaymentText"),
  statusProductsText: document.querySelector("#statusProductsText"),
  statusCategoriesText: document.querySelector("#statusCategoriesText"),
  statusDeliveryAreasText: document.querySelector("#statusDeliveryAreasText"),
  statusOrdersText: document.querySelector("#statusOrdersText"),
  statusLastOrderText: document.querySelector("#statusLastOrderText"),
  statusLastAuditText: document.querySelector("#statusLastAuditText"),
  statusLastBackupText: document.querySelector("#statusLastBackupText"),
  statusSecurityList: document.querySelector("#statusSecurityList"),

  ordersSummary: document.querySelector("#ordersSummary"),
  activeOrdersText: document.querySelector("#activeOrdersText"),
  newOrdersText: document.querySelector("#newOrdersText"),
  deliveredRevenueText: document.querySelector("#deliveredRevenueText"),
  activeGrandTotalText: document.querySelector("#activeGrandTotalText"),
  ordersList: document.querySelector("#ordersList"),
  refreshOrdersButton: document.querySelector("#refreshOrdersButton"),
  orderAutoRefreshText: document.querySelector("#orderAutoRefreshText"),
  soundToggleButton: document.querySelector("#soundToggleButton"),
  orderStatusFilter: document.querySelector("#orderStatusFilter"),

  reportFilterForm: document.querySelector("#reportFilterForm"),
  reportStartDate: document.querySelector("#reportStartDate"),
  reportEndDate: document.querySelector("#reportEndDate"),
  clearReportDatesButton: document.querySelector("#clearReportDatesButton"),
  reportMessage: document.querySelector("#reportMessage"),
  reportTotalOrdersText: document.querySelector("#reportTotalOrdersText"),
  reportDeliveredOrdersText: document.querySelector("#reportDeliveredOrdersText"),
  reportCancelledOrdersText: document.querySelector("#reportCancelledOrdersText"),
  reportActiveOrdersText: document.querySelector("#reportActiveOrdersText"),
  reportDeliveredRevenueText: document.querySelector("#reportDeliveredRevenueText"),
  reportDeliveryFeesText: document.querySelector("#reportDeliveryFeesText"),
  reportAverageOrderText: document.querySelector("#reportAverageOrderText"),
  reportActiveGrandTotalText: document.querySelector("#reportActiveGrandTotalText"),
  topProductsList: document.querySelector("#topProductsList"),
  dailyTotalsList: document.querySelector("#dailyTotalsList"),

  settingsForm: document.querySelector("#settingsForm"),
  settingsMessage: document.querySelector("#settingsMessage"),
  saveButton: document.querySelector("#saveButton"),
  minimumPreview: document.querySelector("#minimumPreview"),
  deliveryPreview: document.querySelector("#deliveryPreview"),

  categoryForm: document.querySelector("#categoryForm"),
  categoryFormTitle: document.querySelector("#categoryFormTitle"),
  categoryMessage: document.querySelector("#categoryMessage"),
  categoriesList: document.querySelector("#categoriesList"),
  refreshCategoriesButton: document.querySelector("#refreshCategoriesButton"),
  cancelCategoryEditButton: document.querySelector("#cancelCategoryEditButton"),

  productForm: document.querySelector("#productForm"),
  productFormTitle: document.querySelector("#productFormTitle"),
  productMessage: document.querySelector("#productMessage"),
  productImageFileInput: document.querySelector("#productImageFileInput"),
  productImageUploadMessage: document.querySelector("#productImageUploadMessage"),
  uploadProductImageButton: document.querySelector("#uploadProductImageButton"),
  productsList: document.querySelector("#productsList"),
  refreshProductsButton: document.querySelector("#refreshProductsButton"),
  cancelProductEditButton: document.querySelector("#cancelProductEditButton"),
  productCategorySelect: document.querySelector("#productCategorySelect"),
  productSearchInput: document.querySelector("#productSearchInput"),

  deliveryAreaForm: document.querySelector("#deliveryAreaForm"),
  deliveryAreaFormTitle: document.querySelector("#deliveryAreaFormTitle"),
  deliveryAreaMessage: document.querySelector("#deliveryAreaMessage"),
  deliveryAreasList: document.querySelector("#deliveryAreasList"),
  refreshDeliveryAreasButton: document.querySelector("#refreshDeliveryAreasButton"),
  cancelDeliveryAreaEditButton: document.querySelector("#cancelDeliveryAreaEditButton"),

  userForm: document.querySelector("#userForm"),
  userFormTitle: document.querySelector("#userFormTitle"),
  userMessage: document.querySelector("#userMessage"),
  usersList: document.querySelector("#usersList"),
  refreshUsersButton: document.querySelector("#refreshUsersButton"),
  cancelUserEditButton: document.querySelector("#cancelUserEditButton"),

  auditLogsList: document.querySelector("#auditLogsList"),
  refreshAuditLogsButton: document.querySelector("#refreshAuditLogsButton"),

  downloadBackupButton: document.querySelector("#downloadBackupButton"),
  restoreBackupFileInput: document.querySelector("#restoreBackupFileInput"),
  restoreBackupButton: document.querySelector("#restoreBackupButton"),
  backupMessage: document.querySelector("#backupMessage"),

  accountUsernameText: document.querySelector("#accountUsernameText"),
  accountFullNameText: document.querySelector("#accountFullNameText"),
  accountRoleText: document.querySelector("#accountRoleText"),
  passwordChangeForm: document.querySelector("#passwordChangeForm"),
  passwordChangeMessage: document.querySelector("#passwordChangeMessage"),
  changePasswordButton: document.querySelector("#changePasswordButton"),
};

function bindEvents() {
  elements.loginForm.addEventListener("submit", login);
  elements.logoutButton.addEventListener("click", logout);
  elements.sectionTabs.addEventListener("click", (event) => {
    unlockAudioAlerts();
    switchSectionFromClick(event);
  });

  elements.refreshSystemStatusButton.addEventListener("click", () => {
    unlockAudioAlerts();
    loadSystemStatus();
  });

  elements.soundToggleButton.addEventListener("click", toggleSoundAlerts);
  elements.refreshOrdersButton.addEventListener("click", () => {
    unlockAudioAlerts();
    loadOrders();
  });
  elements.orderStatusFilter.addEventListener("change", () => {
    unlockAudioAlerts();
    state.orderStatusFilter = elements.orderStatusFilter.value;
    loadOrders();
  });

  elements.reportFilterForm.addEventListener("submit", loadReport);
  elements.clearReportDatesButton.addEventListener("click", clearReportDates);

  elements.settingsForm.addEventListener("submit", saveSettings);
  elements.settingsForm.addEventListener("input", updatePreviewFromForm);

  elements.categoryForm.addEventListener("submit", saveCategory);
  elements.refreshCategoriesButton.addEventListener("click", loadCategories);
  elements.cancelCategoryEditButton.addEventListener("click", resetCategoryForm);

  elements.productForm.addEventListener("submit", saveProduct);
  elements.uploadProductImageButton.addEventListener("click", uploadProductImage);
  elements.refreshProductsButton.addEventListener("click", loadProducts);
  elements.cancelProductEditButton.addEventListener("click", resetProductForm);
  elements.productSearchInput.addEventListener("input", () => {
    state.productSearch = elements.productSearchInput.value.trim().toLowerCase();
    renderProducts();
  });

  elements.deliveryAreaForm.addEventListener("submit", saveDeliveryArea);
  elements.refreshDeliveryAreasButton.addEventListener("click", loadDeliveryAreas);
  elements.cancelDeliveryAreaEditButton.addEventListener("click", resetDeliveryAreaForm);

  elements.userForm.addEventListener("submit", saveUser);
  elements.refreshUsersButton.addEventListener("click", loadUsers);
  elements.cancelUserEditButton.addEventListener("click", resetUserForm);

  elements.refreshAuditLogsButton.addEventListener("click", loadAuditLogs);

  elements.downloadBackupButton.addEventListener("click", downloadBackup);
  elements.restoreBackupButton.addEventListener("click", restoreBackup);

  elements.passwordChangeForm.addEventListener("submit", changeOwnPassword);
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
    if (state.currentUser.role !== "ADMIN") {
      throw new Error("Bu panel icin ADMIN yetkisi gerekli.");
    }
    showAdmin();
    await loadAdminData();
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
      includeAuth: false,
      body: {
        username: formData.get("username"),
        password: formData.get("password"),
      },
    });

    if (data.role !== "ADMIN") {
      throw new Error("Bu panel icin ADMIN yetkisi gerekli.");
    }

    state.token = data.access_token;
    window.localStorage.setItem(TOKEN_STORAGE_KEY, state.token);
    state.currentUser = await apiFetch("/api/auth/me");
    showAdmin();
    await loadAdminData();
  } catch (error) {
    elements.loginMessage.textContent = error.message;
    elements.loginMessage.hidden = false;
  }
}

function logout() {
  stopOrderAutoRefresh();
  state.token = null;
  state.currentUser = null;
  state.settings = null;
  state.systemStatus = null;
  state.categories = [];
  state.products = [];
  state.deliveryAreas = [];
  state.orders = [];
  state.users = [];
  state.report = null;
  state.auditLogs = [];
  state.orderSummary = null;
  window.localStorage.removeItem(TOKEN_STORAGE_KEY);
  showLogin();
}

function showLogin() {
  elements.loginPanel.hidden = false;
  elements.adminPanel.hidden = true;
  elements.logoutButton.hidden = true;
}

function showAdmin() {
  elements.loginPanel.hidden = true;
  elements.adminPanel.hidden = false;
  elements.logoutButton.hidden = false;
  elements.userText.textContent = `${state.currentUser.full_name} (${state.currentUser.role})`;
  fillAccountPanel();
  renderActiveSection();
  renderSoundToggle();
  startOrderAutoRefresh();
}

function fillAccountPanel() {
  if (!state.currentUser) return;

  elements.accountUsernameText.textContent = state.currentUser.username;
  elements.accountFullNameText.textContent = state.currentUser.full_name;
  elements.accountRoleText.textContent =
    roleLabels[state.currentUser.role] || state.currentUser.role;
}

async function loadAdminData() {
  await Promise.all([
    loadSystemStatus(),
    loadOrders(),
    loadSettings(),
    loadCategories(),
    loadProducts(),
    loadDeliveryAreas(),
    loadUsers(),
    loadReport(),
    loadAuditLogs(),
  ]);
}

function switchSectionFromClick(event) {
  const button = event.target.closest("button[data-section]");
  if (!button) return;
  state.activeSection = button.dataset.section;
  renderActiveSection();
}

function renderActiveSection() {
  for (const button of elements.sectionTabs.querySelectorAll("button[data-section]")) {
    button.classList.toggle("is-active", button.dataset.section === state.activeSection);
  }

  for (const panel of elements.sectionPanels) {
    panel.hidden = panel.dataset.sectionPanel !== state.activeSection;
  }
}

async function loadSystemStatus(options = {}) {
  const silent = options.silent === true;
  if (isLoadingSystemStatus && silent) return;

  isLoadingSystemStatus = true;
  if (!silent) {
    elements.systemStatusMessage.hidden = true;
  }

  try {
    state.systemStatus = await apiFetch("/api/admin/system-status");
    renderSystemStatus();
  } catch (error) {
    if (error.status === 401) {
      logout();
      return;
    }

    if (!silent) {
      showSystemStatusMessage(error.message, true);
    }
  } finally {
    isLoadingSystemStatus = false;
  }
}

function renderSystemStatus() {
  const status = state.systemStatus;
  if (!status) return;

  elements.statusApiText.textContent = status.api_status === "OK" ? "Çalışıyor" : status.api_status;
  elements.statusMarketText.textContent =
    status.market_accepting_orders ? "Siparişe açık" : formatMarketClosedReason(status.market_closed_reason);
  elements.statusEnvText.textContent = status.app_env;
  elements.statusPaymentText.textContent = status.online_payment_enabled
    ? "Online ödeme açık"
    : "Kapıda ödeme";
  elements.statusProductsText.textContent = formatProductHealth(status);
  elements.statusCategoriesText.textContent = `${status.active_category_count}/${status.category_count} aktif`;
  elements.statusDeliveryAreasText.textContent = `${status.active_delivery_area_count}/${status.delivery_area_count} aktif`;
  elements.statusOrdersText.textContent = `${status.total_orders} toplam / ${status.active_orders} aktif`;
  elements.statusLastOrderText.textContent = formatLastOrder(status);
  elements.statusLastAuditText.textContent = formatLastAction(
    status.last_audit_action,
    status.last_audit_at,
  );
  elements.statusLastBackupText.textContent = formatLastAction(
    status.last_backup_action,
    status.last_backup_at,
  );
  renderSystemChecks(status);
}

function formatProductHealth(status) {
  const details = [`${status.active_product_count}/${status.product_count} aktif`];
  if (status.out_of_stock_product_count > 0) {
    details.push(`${status.out_of_stock_product_count} stok yok`);
  }
  if (status.low_stock_product_count > 0) {
    details.push(`${status.low_stock_product_count} az stok`);
  }
  return details.join(", ");
}

function formatLastOrder(status) {
  if (!status.last_order_number || !status.last_order_at) {
    return "Henüz yok";
  }
  return `${status.last_order_number} - ${formatDateTime(status.last_order_at)}`;
}

function formatLastAction(action, date) {
  if (!action || !date) {
    return "Henüz yok";
  }
  return `${auditActionLabels[action] || action} - ${formatDateTime(date)}`;
}

function renderSystemChecks(status) {
  const checks = [
    {
      label: "Online ödeme",
      passed: status.online_payment_enabled === false,
      detail: "Kapalı",
    },
    {
      label: "Gönderim ücreti",
      passed: status.delivery_fee_always_charged === true,
      detail: `Her siparişte ${money(status.delivery_fee)}`,
    },
    {
      label: "Minimum sipariş",
      passed: Number(status.minimum_order_amount) >= 0,
      detail: money(status.minimum_order_amount),
    },
    {
      label: "Çalışma saatleri",
      passed: status.market_accepting_orders === true,
      detail: status.market_accepting_orders
        ? `Açık saat dilimi (${status.market_timezone})`
        : formatMarketClosedReason(status.market_closed_reason),
    },
    {
      label: "WhatsApp kullanımı",
      passed: status.whatsapp_mode === "LIVE_SUPPORT_ONLY",
      detail: "Canlı destek",
    },
    {
      label: "Admin kullanıcı adı",
      passed: !status.has_default_admin_username,
      detail: status.has_default_admin_username ? "Varsayılan ad duruyor" : "Özel ad",
    },
    {
      label: "Çalışan kullanıcı adı",
      passed: !status.has_default_employee_username,
      detail: status.has_default_employee_username ? "Varsayılan ad duruyor" : "Özel ad",
    },
  ];

  elements.statusSecurityList.innerHTML = checks.map((check) => `
    <li class="${check.passed ? "is-ok" : "is-warning"}">
      <span>${escapeHtml(check.label)}</span>
      <strong>${escapeHtml(check.detail)}</strong>
    </li>
  `).join("");
}

async function loadOrders(options = {}) {
  const silent = options.silent === true;
  if (isLoadingOrders && silent) return;

  isLoadingOrders = true;
  if (!silent) {
    elements.ordersList.innerHTML = `<div class="empty-state">Siparişler yükleniyor.</div>`;
  }

  try {
    const query = state.orderStatusFilter
      ? `?status=${encodeURIComponent(state.orderStatusFilter)}`
      : "";
    const [summary, orders] = await Promise.all([
      apiFetch("/api/admin/orders/summary"),
      apiFetch(`/api/admin/orders${query}`),
    ]);
    state.orderSummary = summary;
    state.orders = orders;
    renderOrderSummary();
    renderOrders();
    updateOrderAutoRefreshText();
    if (canUseLoadedOrdersForNewOrderAlerts()) {
      handleNewOrderSnapshot(state.orders, { alert: true });
    }
  } catch (error) {
    if (error.status === 401) {
      logout();
      return;
    }

    if (silent) {
      updateOrderAutoRefreshText("Bağlantı bekleniyor");
    } else {
      elements.ordersList.innerHTML = `<div class="empty-state">${escapeHtml(error.message)}</div>`;
    }
  } finally {
    isLoadingOrders = false;
  }
}

function startOrderAutoRefresh() {
  stopOrderAutoRefresh();
  updateOrderAutoRefreshText("Otomatik yenileme açık");
  orderRefreshTimer = window.setInterval(refreshOrdersAndAlerts, ORDER_REFRESH_INTERVAL_MS);
}

async function refreshOrdersAndAlerts() {
  await loadOrders({ silent: true });
  await loadSystemStatus({ silent: true });
  if (!canUseLoadedOrdersForNewOrderAlerts()) {
    await checkNewOrdersForAlert();
  }
}

function stopOrderAutoRefresh() {
  if (!orderRefreshTimer) return;
  window.clearInterval(orderRefreshTimer);
  orderRefreshTimer = null;
}

function updateOrderAutoRefreshText(message) {
  const text = message || `Son güncelleme ${formatClock(new Date())}`;
  elements.orderAutoRefreshText.textContent = text;
}

function canUseLoadedOrdersForNewOrderAlerts() {
  return state.orderStatusFilter === "" || state.orderStatusFilter === "NEW";
}

async function checkNewOrdersForAlert() {
  try {
    const newOrders = await apiFetch("/api/admin/orders?status=NEW");
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
  updateOrderAutoRefreshText(count === 1 ? "Yeni sipariş geldi" : `${count} yeni sipariş geldi`);
  flashDocumentTitle(count);
  playNewOrderAlert();
}

function toggleSoundAlerts() {
  audioAlerts.enabled = !audioAlerts.enabled;
  window.localStorage.setItem(
    SOUND_ENABLED_STORAGE_KEY,
    audioAlerts.enabled ? "true" : "false",
  );

  if (audioAlerts.enabled) {
    unlockAudioAlerts();
  } else {
    renderSoundToggle();
  }
}

async function unlockAudioAlerts() {
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

function renderOrderSummary() {
  const summary = state.orderSummary || {
    active_orders: 0,
    new_orders: 0,
    delivered_revenue: "0.00",
    active_grand_total: "0.00",
  };

  elements.activeOrdersText.textContent = summary.active_orders;
  elements.newOrdersText.textContent = summary.new_orders;
  elements.deliveredRevenueText.textContent = money(summary.delivered_revenue);
  elements.activeGrandTotalText.textContent = money(summary.active_grand_total);
}

function renderOrders() {
  if (!state.orders.length) {
    elements.ordersList.innerHTML = `<div class="empty-state">Bu filtrede sipariş yok.</div>`;
    return;
  }

  elements.ordersList.innerHTML = state.orders.map(renderOrderCard).join("");
}

function renderOrderCard(order) {
  return `
    <article class="record-card order-card">
      <div class="record-top">
        <div class="record-title">
          <strong>${escapeHtml(order.order_number)}</strong>
          <span>${formatDateTime(order.created_at)}</span>
        </div>
        <span class="status-pill ${order.status === "CANCELLED" ? "is-passive" : ""}">
          ${statusLabels[order.status] || order.status}
        </span>
      </div>

      <div class="record-meta">
        <div><span>Müşteri</span><strong>${escapeHtml(order.customer_first_name)} ${escapeHtml(order.customer_last_name)}</strong></div>
        <div><span>Telefon</span><strong>${escapeHtml(order.phone)}</strong></div>
        <div><span>Bölge</span><strong>${escapeHtml(order.delivery_area_name_snapshot)}</strong></div>
        <div><span>Adres</span><strong>${escapeHtml(formatAddress(order))}</strong></div>
        <div><span>Ödeme</span><strong>${paymentLabels[order.payment_method] || order.payment_method}</strong></div>
        <div><span>Bulunamazsa</span><strong>${unavailableLabels[order.unavailable_policy] || order.unavailable_policy}</strong></div>
        ${order.order_note ? `<div><span>Not</span><strong>${escapeHtml(order.order_note)}</strong></div>` : ""}
        ${order.cancellation_reason ? `<div><span>İptal Sebebi</span><strong>${escapeHtml(order.cancellation_reason)}</strong></div>` : ""}
        <div><span>Ara Toplam</span><strong>${money(order.subtotal)}</strong></div>
        <div><span>Gönderim</span><strong>${money(order.delivery_fee)}</strong></div>
        <div><span>Genel Toplam</span><strong>${money(order.grand_total)}</strong></div>
      </div>

      <div class="order-items">
        ${order.items.map((item) => `
          <div class="order-item-line">
            <span>${escapeHtml(item.product_name_snapshot)} x ${item.quantity}</span>
            <strong>${money(item.line_total)}</strong>
          </div>
        `).join("")}
      </div>

      ${renderOrderActions(order)}
    </article>
  `;
}

function renderOrderActions(order) {
  if (order.status === "NEW") {
    return `
      <div class="order-actions">
        <button class="primary-button" type="button" onclick="runAdminOrderAction(${order.id}, 'approve')">Onayla</button>
        ${renderAdminCancelControls(order.id, "İptal Et")}
      </div>
    `;
  }

  if (order.status === "PREPARING") {
    return `
      <div class="order-actions">
        <button class="primary-button" type="button" onclick="runAdminOrderAction(${order.id}, 'on-the-way')">Yola Çıktı</button>
        ${renderAdminCancelControls(order.id, "İptal Et")}
      </div>
    `;
  }

  if (order.status === "ON_THE_WAY") {
    return `
      <div class="order-actions">
        <button class="primary-button" type="button" onclick="runAdminOrderAction(${order.id}, 'delivered')">Teslim Edildi</button>
        ${renderAdminCancelControls(order.id, "İptal Et")}
      </div>
    `;
  }

  return "";
}

function renderAdminCancelControls(orderId, buttonText) {
  return `
    <div class="action-row">
      <label>
        <span>İptal sebebi</span>
        <select id="cancelReason-${orderId}">
          <option value="OUT_OF_STOCK">Ürün stokta yok</option>
          <option value="OUT_OF_DELIVERY_AREA">Teslimat bölgesi dışında</option>
          <option value="BUSY">Yoğunluk</option>
          <option value="CLOSING_SOON">Market kapanmak üzere</option>
          <option value="CUSTOMER_UNREACHABLE">Müşteriye ulaşılamadı</option>
          <option value="OTHER">Diğer</option>
        </select>
      </label>
      <button class="danger-button" type="button" onclick="cancelAdminOrder(${orderId})">${buttonText}</button>
    </div>
  `;
}

async function runAdminOrderAction(orderId, action) {
  try {
    await apiFetch(`/api/employee/orders/${orderId}/${action}`, {
      method: "POST",
    });
    await refreshOrderViews();
  } catch (error) {
    showOrdersInlineError(error.message);
  }
}

async function cancelAdminOrder(orderId) {
  const reasonSelect = document.querySelector(`#cancelReason-${orderId}`);
  try {
    await apiFetch(`/api/employee/orders/${orderId}/reject`, {
      method: "POST",
      body: {
        reason: reasonSelect.value,
      },
    });
    await refreshOrderViews();
  } catch (error) {
    showOrdersInlineError(error.message);
  }
}

function showOrdersInlineError(message) {
  elements.ordersList.insertAdjacentHTML(
    "afterbegin",
    `<div class="form-message is-error">${escapeHtml(message)}</div>`,
  );
}

async function refreshOrderViews() {
  await loadOrders();
  await Promise.allSettled([loadReport(), loadAuditLogs()]);
}

async function loadReport(event) {
  if (event) {
    event.preventDefault();
  }

  elements.reportMessage.hidden = true;
  elements.topProductsList.innerHTML = `<div class="empty-state">Ürün raporu yükleniyor.</div>`;
  elements.dailyTotalsList.innerHTML = `<div class="empty-state">Günlük özet yükleniyor.</div>`;

  try {
    const query = buildReportQuery();
    state.report = await apiFetch(`/api/admin/reports/orders${query}`);
    renderReport();
  } catch (error) {
    showReportMessage(error.message, true);
    elements.topProductsList.innerHTML = `<div class="empty-state">Rapor alınamadı.</div>`;
    elements.dailyTotalsList.innerHTML = `<div class="empty-state">Rapor alınamadı.</div>`;
  }
}

function clearReportDates() {
  elements.reportStartDate.value = "";
  elements.reportEndDate.value = "";
  loadReport();
}

function buildReportQuery() {
  const params = new URLSearchParams();
  const startDate = elements.reportStartDate.value;
  const endDate = elements.reportEndDate.value;

  if (startDate) {
    params.set("start_date", startDate);
  }

  if (endDate) {
    params.set("end_date", endDate);
  }

  const query = params.toString();
  return query ? `?${query}` : "";
}

function renderReport() {
  const report = state.report || {
    total_orders: 0,
    delivered_orders: 0,
    cancelled_orders: 0,
    active_orders: 0,
    delivered_revenue: "0.00",
    delivered_delivery_fees: "0.00",
    average_delivered_order_total: "0.00",
    active_grand_total: "0.00",
    top_products: [],
    daily_totals: [],
  };

  elements.reportTotalOrdersText.textContent = report.total_orders;
  elements.reportDeliveredOrdersText.textContent = report.delivered_orders;
  elements.reportCancelledOrdersText.textContent = report.cancelled_orders;
  elements.reportActiveOrdersText.textContent = report.active_orders;
  elements.reportDeliveredRevenueText.textContent = money(report.delivered_revenue);
  elements.reportDeliveryFeesText.textContent = money(report.delivered_delivery_fees);
  elements.reportAverageOrderText.textContent = money(report.average_delivered_order_total);
  elements.reportActiveGrandTotalText.textContent = money(report.active_grand_total);

  renderTopProducts(report.top_products || []);
  renderDailyTotals(report.daily_totals || []);
}

function renderTopProducts(products) {
  if (!products.length) {
    elements.topProductsList.innerHTML = `<div class="empty-state">Teslim edilmiş ürün satışı yok.</div>`;
    return;
  }

  elements.topProductsList.innerHTML = products.map((product) => `
    <article class="record-card compact-record">
      <div class="record-top">
        <div class="record-title">
          <strong>${escapeHtml(product.product_name)}</strong>
          <span>${product.quantity} adet</span>
        </div>
        <strong class="money-value">${money(product.revenue)}</strong>
      </div>
    </article>
  `).join("");
}

function renderDailyTotals(days) {
  if (!days.length) {
    elements.dailyTotalsList.innerHTML = `<div class="empty-state">Bu aralıkta sipariş yok.</div>`;
    return;
  }

  elements.dailyTotalsList.innerHTML = days.map((day) => `
    <article class="record-card compact-record">
      <div class="record-top">
        <div class="record-title">
          <strong>${formatDate(day.day)}</strong>
          <span>${day.order_count} sipariş · ${day.delivered_count} teslim · ${day.cancelled_count} iptal</span>
        </div>
        <strong class="money-value">${money(day.revenue)}</strong>
      </div>
      <div class="record-meta">
        <div><span>Gönderim gelirleri</span><strong>${money(day.delivery_fees)}</strong></div>
      </div>
    </article>
  `).join("");
}

async function loadSettings() {
  showSettingsMessage("Ayarlar yükleniyor.", false);
  state.settings = await apiFetch("/api/market-settings/admin");
  fillSettingsForm(state.settings);
  elements.settingsMessage.hidden = true;
}

function fillSettingsForm(settings) {
  const form = elements.settingsForm;
  form.elements.namedItem("market_name").value = settings.market_name || "";
  form.elements.namedItem("phone").value = settings.phone || "";
  form.elements.namedItem("whatsapp_number").value = settings.whatsapp_number || "";
  form.elements.namedItem("is_open").checked = Boolean(settings.is_open);
  form.elements.namedItem("opening_time").value = formatTimeInput(settings.opening_time);
  form.elements.namedItem("closing_time").value = formatTimeInput(settings.closing_time);
  form.elements.namedItem("minimum_order_amount").value = settings.minimum_order_amount;
  form.elements.namedItem("delivery_fee").value = settings.delivery_fee;
  updatePreviewFromForm();
}

async function saveSettings(event) {
  event.preventDefault();
  elements.saveButton.disabled = true;
  showSettingsMessage("Ayarlar kaydediliyor.", false);

  const form = elements.settingsForm;
  const payload = {
    market_name: form.elements.namedItem("market_name").value,
    phone: optionalFormValue(form.elements.namedItem("phone").value),
    whatsapp_number: optionalFormValue(form.elements.namedItem("whatsapp_number").value),
    is_open: form.elements.namedItem("is_open").checked,
    opening_time: optionalTimeValue(form.elements.namedItem("opening_time").value),
    closing_time: optionalTimeValue(form.elements.namedItem("closing_time").value),
    minimum_order_amount: form.elements.namedItem("minimum_order_amount").value,
    delivery_fee: form.elements.namedItem("delivery_fee").value,
  };

  try {
    state.settings = await apiFetch("/api/market-settings/admin", {
      method: "PATCH",
      body: payload,
    });
    fillSettingsForm(state.settings);
    await loadAuditLogs();
    showSettingsMessage("Ayarlar kaydedildi. Yeni siparişlerde bu değerler kullanılacak.", false);
  } catch (error) {
    showSettingsMessage(error.message, true);
  } finally {
    elements.saveButton.disabled = false;
  }
}

async function loadCategories() {
  elements.categoriesList.innerHTML = `<div class="empty-state">Kategoriler yükleniyor.</div>`;
  state.categories = await apiFetch("/api/admin/categories");
  renderCategoryOptions();
  renderCategories();
}

function renderCategoryOptions() {
  elements.productCategorySelect.innerHTML = [
    `<option value="">Kategori seçilmedi</option>`,
    ...state.categories.map((category) => `
      <option value="${category.id}">${escapeHtml(category.name)}${category.is_active ? "" : " (pasif)"}</option>
    `),
  ].join("");
}

function renderCategories() {
  if (!state.categories.length) {
    elements.categoriesList.innerHTML = `<div class="empty-state">Kategori yok.</div>`;
    return;
  }

  elements.categoriesList.innerHTML = state.categories.map((category) => `
    <article class="record-card">
      <div class="record-top">
        <div class="record-title">
          <strong>${escapeHtml(category.name)}</strong>
          <span>${escapeHtml(category.slug)}</span>
        </div>
        <span class="status-pill ${category.is_active ? "" : "is-passive"}">
          ${category.is_active ? "Aktif" : "Pasif"}
        </span>
      </div>
      <div class="record-meta">
        <div><span>Sıralama</span><strong>${category.display_order}</strong></div>
        <div><span>Açıklama</span><strong>${escapeHtml(category.description || "-")}</strong></div>
      </div>
      <div class="button-row">
        <button class="ghost-button" type="button" onclick="editCategory(${category.id})">Düzenle</button>
      </div>
    </article>
  `).join("");
}

async function saveCategory(event) {
  event.preventDefault();
  showCategoryMessage("Kategori kaydediliyor.", false);

  const form = elements.categoryForm;
  const categoryId = optionalFormValue(form.elements.namedItem("category_id").value);
  const payload = {
    name: form.elements.namedItem("name").value,
    slug: optionalFormValue(form.elements.namedItem("slug").value),
    description: optionalFormValue(form.elements.namedItem("description").value),
    display_order: Number(form.elements.namedItem("display_order").value || 0),
    is_active: form.elements.namedItem("is_active").checked,
  };

  try {
    if (categoryId) {
      await apiFetch(`/api/admin/categories/${categoryId}`, {
        method: "PATCH",
        body: payload,
      });
    } else {
      await apiFetch("/api/admin/categories", {
        method: "POST",
        body: payload,
      });
    }

    resetCategoryForm();
    await loadCategories();
    await loadAuditLogs();
    showCategoryMessage("Kategori kaydedildi.", false);
  } catch (error) {
    showCategoryMessage(error.message, true);
  }
}

function editCategory(categoryId) {
  const category = state.categories.find((item) => item.id === categoryId);
  if (!category) return;

  const form = elements.categoryForm;
  form.elements.namedItem("category_id").value = category.id;
  form.elements.namedItem("name").value = category.name;
  form.elements.namedItem("slug").value = category.slug;
  form.elements.namedItem("description").value = category.description || "";
  form.elements.namedItem("display_order").value = category.display_order;
  form.elements.namedItem("is_active").checked = category.is_active;
  elements.categoryFormTitle.textContent = "Kategori düzenle";
  elements.categoryMessage.hidden = true;
  form.scrollIntoView({ behavior: "smooth", block: "start" });
}

function resetCategoryForm() {
  elements.categoryForm.reset();
  elements.categoryForm.elements.namedItem("category_id").value = "";
  elements.categoryForm.elements.namedItem("display_order").value = "0";
  elements.categoryForm.elements.namedItem("is_active").checked = true;
  elements.categoryFormTitle.textContent = "Kategori ekle";
}

async function loadProducts() {
  elements.productsList.innerHTML = `<div class="empty-state">Ürünler yükleniyor.</div>`;
  state.products = await apiFetch("/api/admin/products");
  renderProducts();
}

function renderProducts() {
  const products = state.products.filter((product) => {
    if (!state.productSearch) return true;
    return product.name.toLowerCase().includes(state.productSearch);
  });

  if (!products.length) {
    elements.productsList.innerHTML = `<div class="empty-state">Ürün bulunamadı.</div>`;
    return;
  }

  elements.productsList.innerHTML = products.map((product) => `
    <article class="record-card">
      <div class="record-top">
        <div class="record-title">
          <strong>${escapeHtml(product.name)}</strong>
          <span>${escapeHtml(product.slug)}</span>
        </div>
        <span class="status-pill ${product.is_active ? "" : "is-passive"}">
          ${product.is_active ? "Aktif" : "Pasif"}
        </span>
      </div>
      <div class="record-meta">
        <div><span>Kategori</span><strong>${escapeHtml(product.category?.name || "-")}</strong></div>
        <div><span>Fiyat</span><strong>${money(product.price)}</strong></div>
        <div><span>Stok</span><strong>${product.stock_quantity}</strong></div>
        <div><span>SKU</span><strong>${escapeHtml(product.sku || "-")}</strong></div>
      </div>
      <div class="button-row">
        <button class="ghost-button" type="button" onclick="editProduct(${product.id})">Düzenle</button>
        ${product.is_active ? `<button class="danger-button" type="button" onclick="deactivateProduct(${product.id})">Pasife Al</button>` : ""}
      </div>
    </article>
  `).join("");
}

async function uploadProductImage() {
  const file = elements.productImageFileInput.files[0];
  if (!file) {
    showProductImageUploadMessage("Önce bir fotoğraf seçin.", true);
    return;
  }

  elements.uploadProductImageButton.disabled = true;
  showProductImageUploadMessage("Fotoğraf yükleniyor.", false);

  const formData = new FormData();
  formData.append("file", file);

  try {
    const response = await fetch(`${API_BASE_URL}/api/admin/products/images`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${state.token}`,
      },
      body: formData,
    });
    const data = await response.json().catch(() => ({}));

    if (!response.ok) {
      throw new Error(getApiErrorMessage(data));
    }

    elements.productForm.elements.namedItem("image_url").value = data.image_url;
    elements.productImageFileInput.value = "";
    await loadAuditLogs();
    showProductImageUploadMessage("Fotoğraf yüklendi. Ürünü kaydedince müşteri ekranında görünür.", false);
  } catch (error) {
    showProductImageUploadMessage(error.message, true);
  } finally {
    elements.uploadProductImageButton.disabled = false;
  }
}

async function saveProduct(event) {
  event.preventDefault();
  showProductMessage("Ürün kaydediliyor.", false);

  const form = elements.productForm;
  const productId = optionalFormValue(form.elements.namedItem("product_id").value);
  const payload = {
    category_id: optionalNumberValue(form.elements.namedItem("category_id").value),
    name: form.elements.namedItem("name").value,
    slug: optionalFormValue(form.elements.namedItem("slug").value),
    description: optionalFormValue(form.elements.namedItem("description").value),
    sku: optionalFormValue(form.elements.namedItem("sku").value),
    image_url: optionalFormValue(form.elements.namedItem("image_url").value),
    price: form.elements.namedItem("price").value,
    stock_quantity: Number(form.elements.namedItem("stock_quantity").value || 0),
    is_active: form.elements.namedItem("is_active").checked,
  };

  try {
    if (productId) {
      await apiFetch(`/api/admin/products/${productId}`, {
        method: "PATCH",
        body: payload,
      });
    } else {
      await apiFetch("/api/admin/products", {
        method: "POST",
        body: payload,
      });
    }

    resetProductForm();
    await loadProducts();
    await loadAuditLogs();
    showProductMessage("Ürün kaydedildi.", false);
  } catch (error) {
    showProductMessage(error.message, true);
  }
}

function editProduct(productId) {
  const product = state.products.find((item) => item.id === productId);
  if (!product) return;

  const form = elements.productForm;
  form.elements.namedItem("product_id").value = product.id;
  form.elements.namedItem("category_id").value = product.category_id || "";
  form.elements.namedItem("name").value = product.name;
  form.elements.namedItem("slug").value = product.slug;
  form.elements.namedItem("description").value = product.description || "";
  form.elements.namedItem("sku").value = product.sku || "";
  form.elements.namedItem("image_url").value = product.image_url || "";
  form.elements.namedItem("price").value = product.price;
  form.elements.namedItem("stock_quantity").value = product.stock_quantity;
  form.elements.namedItem("is_active").checked = product.is_active;
  elements.productFormTitle.textContent = "Ürün düzenle";
  elements.productMessage.hidden = true;
  elements.productImageUploadMessage.hidden = true;
  elements.productImageFileInput.value = "";
  form.scrollIntoView({ behavior: "smooth", block: "start" });
}

async function deactivateProduct(productId) {
  showProductMessage("Ürün pasife alınıyor.", false);
  try {
    await apiFetch(`/api/admin/products/${productId}/deactivate`, {
      method: "POST",
    });
    await loadProducts();
    await loadAuditLogs();
    showProductMessage("Ürün pasife alındı. Eski sipariş kayıtları etkilenmez.", false);
  } catch (error) {
    showProductMessage(error.message, true);
  }
}

function resetProductForm() {
  elements.productForm.reset();
  elements.productForm.elements.namedItem("product_id").value = "";
  elements.productForm.elements.namedItem("category_id").value = "";
  elements.productForm.elements.namedItem("stock_quantity").value = "0";
  elements.productForm.elements.namedItem("is_active").checked = true;
  elements.productImageFileInput.value = "";
  elements.productImageUploadMessage.hidden = true;
  elements.productFormTitle.textContent = "Ürün ekle";
}

async function loadDeliveryAreas() {
  elements.deliveryAreasList.innerHTML = `<div class="empty-state">Teslimat bölgeleri yükleniyor.</div>`;
  state.deliveryAreas = await apiFetch("/api/admin/delivery-areas");
  renderDeliveryAreas();
}

function renderDeliveryAreas() {
  if (!state.deliveryAreas.length) {
    elements.deliveryAreasList.innerHTML = `<div class="empty-state">Teslimat bölgesi yok.</div>`;
    return;
  }

  elements.deliveryAreasList.innerHTML = state.deliveryAreas.map((area) => `
    <article class="record-card">
      <div class="record-top">
        <div class="record-title">
          <strong>${escapeHtml(area.name)}</strong>
          <span>${escapeHtml(area.slug)}</span>
        </div>
        <span class="status-pill ${area.is_active ? "" : "is-passive"}">
          ${area.is_active ? "Aktif" : "Pasif"}
        </span>
      </div>
      <div class="record-meta">
        <div><span>Sıralama</span><strong>${area.display_order}</strong></div>
        <div><span>Checkout</span><strong>${area.is_active ? "Görünür" : "Gizli"}</strong></div>
      </div>
      <div class="button-row">
        <button class="ghost-button" type="button" onclick="editDeliveryArea(${area.id})">Düzenle</button>
      </div>
    </article>
  `).join("");
}

async function saveDeliveryArea(event) {
  event.preventDefault();
  showDeliveryAreaMessage("Teslimat bölgesi kaydediliyor.", false);

  const form = elements.deliveryAreaForm;
  const deliveryAreaId = optionalFormValue(
    form.elements.namedItem("delivery_area_id").value,
  );
  const payload = {
    name: form.elements.namedItem("name").value,
    slug: optionalFormValue(form.elements.namedItem("slug").value),
    display_order: Number(form.elements.namedItem("display_order").value || 0),
    is_active: form.elements.namedItem("is_active").checked,
  };

  try {
    if (deliveryAreaId) {
      await apiFetch(`/api/admin/delivery-areas/${deliveryAreaId}`, {
        method: "PATCH",
        body: payload,
      });
    } else {
      await apiFetch("/api/admin/delivery-areas", {
        method: "POST",
        body: payload,
      });
    }

    resetDeliveryAreaForm();
    await loadDeliveryAreas();
    await loadAuditLogs();
    showDeliveryAreaMessage("Teslimat bölgesi kaydedildi.", false);
  } catch (error) {
    showDeliveryAreaMessage(error.message, true);
  }
}

function editDeliveryArea(deliveryAreaId) {
  const area = state.deliveryAreas.find((item) => item.id === deliveryAreaId);
  if (!area) return;

  const form = elements.deliveryAreaForm;
  form.elements.namedItem("delivery_area_id").value = area.id;
  form.elements.namedItem("name").value = area.name;
  form.elements.namedItem("slug").value = area.slug;
  form.elements.namedItem("display_order").value = area.display_order;
  form.elements.namedItem("is_active").checked = area.is_active;
  elements.deliveryAreaFormTitle.textContent = "Bölge düzenle";
  elements.deliveryAreaMessage.hidden = true;
  form.scrollIntoView({ behavior: "smooth", block: "start" });
}

function resetDeliveryAreaForm() {
  elements.deliveryAreaForm.reset();
  elements.deliveryAreaForm.elements.namedItem("delivery_area_id").value = "";
  elements.deliveryAreaForm.elements.namedItem("display_order").value = "0";
  elements.deliveryAreaForm.elements.namedItem("is_active").checked = true;
  elements.deliveryAreaFormTitle.textContent = "Bölge ekle";
}

async function loadUsers() {
  elements.usersList.innerHTML = `<div class="empty-state">Kullanıcılar yükleniyor.</div>`;
  state.users = await apiFetch("/api/admin/users");
  renderUsers();
}

function renderUsers() {
  if (!state.users.length) {
    elements.usersList.innerHTML = `<div class="empty-state">Kullanıcı yok.</div>`;
    return;
  }

  elements.usersList.innerHTML = state.users.map((user) => {
    const isCurrentUser = state.currentUser?.id === user.id;
    return `
      <article class="record-card">
        <div class="record-top">
          <div class="record-title">
            <strong>${escapeHtml(user.full_name)}</strong>
            <span>${escapeHtml(user.username)}${isCurrentUser ? " · sen" : ""}</span>
          </div>
          <span class="status-pill ${user.is_active ? "" : "is-passive"}">
            ${user.is_active ? "Aktif" : "Pasif"}
          </span>
        </div>
        <div class="record-meta">
          <div><span>Rol</span><strong>${roleLabels[user.role] || escapeHtml(user.role)}</strong></div>
          <div><span>Oluşturma</span><strong>${formatDateTime(user.created_at)}</strong></div>
        </div>
        <div class="button-row">
          <button class="ghost-button" type="button" onclick="editUser(${user.id})">Düzenle</button>
        </div>
      </article>
    `;
  }).join("");
}

async function saveUser(event) {
  event.preventDefault();
  showUserMessage("Kullanıcı kaydediliyor.", false);

  const form = elements.userForm;
  const userId = optionalFormValue(form.elements.namedItem("user_id").value);
  const password = optionalFormValue(form.elements.namedItem("password").value);
  const payload = {
    full_name: form.elements.namedItem("full_name").value,
    role: form.elements.namedItem("role").value,
    is_active: form.elements.namedItem("is_active").checked,
  };

  if (password) {
    payload.password = password;
  }

  try {
    if (userId) {
      await apiFetch(`/api/admin/users/${userId}`, {
        method: "PATCH",
        body: payload,
      });
    } else {
      await apiFetch("/api/admin/users", {
        method: "POST",
        body: {
          ...payload,
          username: form.elements.namedItem("username").value,
          password: form.elements.namedItem("password").value,
        },
      });
    }

    resetUserForm();
    await loadUsers();
    await loadAuditLogs();
    showUserMessage("Kullanıcı kaydedildi.", false);
  } catch (error) {
    showUserMessage(error.message, true);
  }
}

function editUser(userId) {
  const user = state.users.find((item) => item.id === userId);
  if (!user) return;

  const form = elements.userForm;
  const passwordInput = form.elements.namedItem("password");
  const usernameInput = form.elements.namedItem("username");
  form.elements.namedItem("user_id").value = user.id;
  usernameInput.value = user.username;
  usernameInput.disabled = true;
  form.elements.namedItem("full_name").value = user.full_name;
  form.elements.namedItem("role").value = user.role;
  form.elements.namedItem("is_active").checked = user.is_active;
  passwordInput.value = "";
  passwordInput.required = false;
  passwordInput.placeholder = "Boş bırakırsan değişmez";
  elements.userFormTitle.textContent = "Kullanıcı düzenle";
  elements.userMessage.hidden = true;
  form.scrollIntoView({ behavior: "smooth", block: "start" });
}

function resetUserForm() {
  elements.userForm.reset();
  const passwordInput = elements.userForm.elements.namedItem("password");
  const usernameInput = elements.userForm.elements.namedItem("username");
  elements.userForm.elements.namedItem("user_id").value = "";
  usernameInput.disabled = false;
  passwordInput.required = true;
  passwordInput.placeholder = "En az 8 karakter";
  elements.userForm.elements.namedItem("role").value = "EMPLOYEE";
  elements.userForm.elements.namedItem("is_active").checked = true;
  elements.userFormTitle.textContent = "Kullanıcı ekle";
}

async function loadAuditLogs() {
  elements.auditLogsList.innerHTML = `<div class="empty-state">İşlem geçmişi yükleniyor.</div>`;
  try {
    state.auditLogs = await apiFetch("/api/admin/audit-logs");
    renderAuditLogs();
  } catch (error) {
    elements.auditLogsList.innerHTML = `<div class="empty-state">${escapeHtml(error.message)}</div>`;
  }
}

function renderAuditLogs() {
  if (!state.auditLogs.length) {
    elements.auditLogsList.innerHTML = `<div class="empty-state">Henüz işlem kaydı yok.</div>`;
    return;
  }

  elements.auditLogsList.innerHTML = state.auditLogs.map((log) => `
    <article class="record-card compact-record">
      <div class="record-top">
        <div class="record-title">
          <strong>${escapeHtml(auditActionLabels[log.action] || log.action)}</strong>
          <span>${formatDateTime(log.created_at)}</span>
        </div>
        <span class="status-pill">${escapeHtml(log.actor_username_snapshot || "Sistem")}</span>
      </div>
      <p class="record-description">${escapeHtml(log.description)}</p>
      <div class="record-meta">
        <div><span>Hedef</span><strong>${escapeHtml(formatAuditTarget(log))}</strong></div>
      </div>
    </article>
  `).join("");
}

async function downloadBackup() {
  elements.downloadBackupButton.disabled = true;
  showBackupMessage("Yedek hazırlanıyor.", false);

  try {
    const response = await fetch(`${API_BASE_URL}/api/admin/backups/export`, {
      headers: {
        Authorization: `Bearer ${state.token}`,
      },
    });

    if (!response.ok) {
      const data = await response.json().catch(() => ({}));
      throw new Error(getApiErrorMessage(data));
    }

    const blob = await response.blob();
    const downloadUrl = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = downloadUrl;
    link.download = getDownloadFilename(response.headers.get("Content-Disposition"));
    document.body.append(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(downloadUrl);
    await loadAuditLogs();
    showBackupMessage("Yedek indirildi. Bu dosyayı güvenli bir yerde saklayın.", false);
  } catch (error) {
    showBackupMessage(error.message, true);
  } finally {
    elements.downloadBackupButton.disabled = false;
  }
}

async function restoreBackup() {
  const file = elements.restoreBackupFileInput.files[0];
  if (!file) {
    showBackupMessage("Önce bir yedek ZIP dosyası seçin.", true);
    return;
  }

  const confirmed = window.confirm(
    "Bu işlem mevcut market verilerini seçilen yedekle değiştirecek. Devam edilsin mi?",
  );
  if (!confirmed) return;

  elements.restoreBackupButton.disabled = true;
  showBackupMessage("Yedek geri yükleniyor.", false);

  const formData = new FormData();
  formData.append("file", file);

  try {
    const response = await fetch(`${API_BASE_URL}/api/admin/backups/restore`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${state.token}`,
      },
      body: formData,
    });
    const data = await response.json().catch(() => ({}));

    if (!response.ok) {
      throw new Error(getApiErrorMessage(data));
    }

    elements.restoreBackupFileInput.value = "";
    showBackupMessage(formatRestoreMessage(data), false);

    try {
      await loadAdminData();
    } catch {
      logout();
    }
  } catch (error) {
    showBackupMessage(error.message, true);
  } finally {
    elements.restoreBackupButton.disabled = false;
  }
}

async function changeOwnPassword(event) {
  event.preventDefault();
  elements.passwordChangeMessage.hidden = true;

  const form = elements.passwordChangeForm;
  const currentPassword = form.elements.namedItem("current_password").value;
  const newPassword = form.elements.namedItem("new_password").value;
  const confirmPassword = form.elements.namedItem("confirm_password").value;

  if (newPassword !== confirmPassword) {
    showPasswordChangeMessage("Yeni şifreler aynı değil.", true);
    return;
  }

  elements.changePasswordButton.disabled = true;
  try {
    const data = await apiFetch("/api/auth/me/password", {
      method: "PATCH",
      body: {
        current_password: currentPassword,
        new_password: newPassword,
      },
    });
    form.reset();
    showPasswordChangeMessage(data.message || "Şifre güncellendi.", false);
    await Promise.all([loadAuditLogs(), loadSystemStatus()]);
  } catch (error) {
    showPasswordChangeMessage(error.message, true);
  } finally {
    elements.changePasswordButton.disabled = false;
  }
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
    const error = new Error(getApiErrorMessage(data));
    error.status = response.status;
    throw error;
  }

  return data;
}

function updatePreviewFromForm() {
  elements.minimumPreview.textContent = money(
    elements.settingsForm.elements.namedItem("minimum_order_amount").value || 0,
  );
  elements.deliveryPreview.textContent = money(
    elements.settingsForm.elements.namedItem("delivery_fee").value || 0,
  );
}

function showSettingsMessage(message, isError) {
  showMessage(elements.settingsMessage, message, isError);
}

function showCategoryMessage(message, isError) {
  showMessage(elements.categoryMessage, message, isError);
}

function showProductMessage(message, isError) {
  showMessage(elements.productMessage, message, isError);
}

function showProductImageUploadMessage(message, isError) {
  showMessage(elements.productImageUploadMessage, message, isError);
}

function showDeliveryAreaMessage(message, isError) {
  showMessage(elements.deliveryAreaMessage, message, isError);
}

function showUserMessage(message, isError) {
  showMessage(elements.userMessage, message, isError);
}

function showReportMessage(message, isError) {
  showMessage(elements.reportMessage, message, isError);
}

function showBackupMessage(message, isError) {
  showMessage(elements.backupMessage, message, isError);
}

function showSystemStatusMessage(message, isError) {
  showMessage(elements.systemStatusMessage, message, isError);
}

function showPasswordChangeMessage(message, isError) {
  showMessage(elements.passwordChangeMessage, message, isError);
}

function showMessage(element, message, isError) {
  element.textContent = message;
  element.classList.toggle("is-error", isError);
  element.hidden = false;
}

function optionalFormValue(value) {
  const text = String(value || "").trim();
  return text ? text : null;
}

function optionalNumberValue(value) {
  const text = String(value || "").trim();
  return text ? Number(text) : null;
}

function optionalTimeValue(value) {
  const text = String(value || "").trim();
  return text ? `${text}:00` : null;
}

function formatTimeInput(value) {
  if (!value) return "";
  return String(value).slice(0, 5);
}

function formatDateTime(value) {
  return new Intl.DateTimeFormat("tr-TR", {
    dateStyle: "short",
    timeStyle: "short",
  }).format(new Date(value));
}

function formatClock(value) {
  return new Intl.DateTimeFormat("tr-TR", {
    timeStyle: "medium",
  }).format(value);
}

function formatMarketClosedReason(reason) {
  if (reason === "OUTSIDE_WORKING_HOURS") {
    return "Çalışma saati dışında";
  }

  if (reason === "MANUALLY_CLOSED") {
    return "Manuel kapalı";
  }

  return "Kapalı";
}

function formatDate(value) {
  const [year, month, day] = String(value || "").split("-").map(Number);
  if (!year || !month || !day) return "-";

  return new Intl.DateTimeFormat("tr-TR", {
    dateStyle: "medium",
  }).format(new Date(year, month - 1, day));
}

function formatAddress(order) {
  return [
    order.neighborhood,
    order.street,
    order.apartment,
    order.flat ? `Daire ${order.flat}` : "",
    order.address_line,
    order.address_directions,
  ].filter(Boolean).join(", ");
}

function formatAuditTarget(log) {
  const targetType = auditTargetLabels[log.target_type] || log.target_type;
  return log.target_id ? `${targetType} #${log.target_id}` : targetType;
}

function getDownloadFilename(contentDisposition) {
  const fallback = `market-yedek-${new Date().toISOString().slice(0, 10)}.zip`;
  if (!contentDisposition) return fallback;

  const match = contentDisposition.match(/filename="?(?<filename>[^";]+)"?/i);
  return match?.groups?.filename || fallback;
}

function formatRestoreMessage(data) {
  const counts = data?.table_counts || {};
  const orderCount = counts.orders || 0;
  const productCount = counts.products || 0;
  const userCount = counts.users || 0;
  return `Yedek geri yüklendi. ${orderCount} sipariş, ${productCount} ürün ve ${userCount} kullanıcı kaydı işlendi.`;
}

function getApiErrorMessage(data) {
  if (data?.detail?.message) {
    return data.detail.message;
  }

  if (Array.isArray(data?.detail)) {
    return "Lütfen alanları kontrol edin.";
  }

  if (typeof data?.detail === "string") {
    return data.detail;
  }

  return "İstek başarısız oldu.";
}

function money(value) {
  return new Intl.NumberFormat("tr-TR", {
    style: "currency",
    currency: "TRY",
  }).format(Number(value));
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

window.editCategory = editCategory;
window.editProduct = editProduct;
window.deactivateProduct = deactivateProduct;
window.editDeliveryArea = editDeliveryArea;
window.runAdminOrderAction = runAdminOrderAction;
window.cancelAdminOrder = cancelAdminOrder;
window.editUser = editUser;

init();
