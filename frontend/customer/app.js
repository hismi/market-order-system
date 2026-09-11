const API_BASE_URL = "http://127.0.0.1:8000";
const CART_STORAGE_KEY = "market-order-system-cart";
const MARKET_SETTINGS_REFRESH_INTERVAL_MS = 60000;

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

const state = {
  categories: [],
  deliveryAreas: [],
  products: [],
  selectedCategory: "",
  search: "",
  cart: loadCart(),
  settings: {
    market_name: "Yerel Market",
    whatsapp_number: null,
    is_open: true,
    accepting_orders: true,
    closed_reason: null,
    minimum_order_amount: "300.00",
    delivery_fee: "50.00",
  },
};

let marketSettingsRefreshTimer = null;

const elements = {
  marketName: document.querySelector("#marketName"),
  marketStatus: document.querySelector("#marketStatus"),
  whatsappSupportLink: document.querySelector("#whatsappSupportLink"),
  searchInput: document.querySelector("#searchInput"),
  categoryStrip: document.querySelector("#categoryStrip"),
  productGrid: document.querySelector("#productGrid"),
  productCount: document.querySelector("#productCount"),
  emptyState: document.querySelector("#emptyState"),
  trackingForm: document.querySelector("#trackingForm"),
  trackingResult: document.querySelector("#trackingResult"),
  trackOrderButton: document.querySelector("#trackOrderButton"),
  openCartButton: document.querySelector("#openCartButton"),
  closeCartButton: document.querySelector("#closeCartButton"),
  drawerBackdrop: document.querySelector("#drawerBackdrop"),
  cartDrawer: document.querySelector("#cartDrawer"),
  cartItemCount: document.querySelector("#cartItemCount"),
  cartBarTotal: document.querySelector("#cartBarTotal"),
  cartItems: document.querySelector("#cartItems"),
  subtotalText: document.querySelector("#subtotalText"),
  deliveryFeeText: document.querySelector("#deliveryFeeText"),
  grandTotalText: document.querySelector("#grandTotalText"),
  minimumMessage: document.querySelector("#minimumMessage"),
  checkoutButton: document.querySelector("#checkoutButton"),
  checkoutForm: document.querySelector("#checkoutForm"),
  deliveryAreaSelect: document.querySelector("#deliveryAreaSelect"),
  orderResult: document.querySelector("#orderResult"),
  submitOrderButton: document.querySelector("#submitOrderButton"),
};

function money(value) {
  return new Intl.NumberFormat("tr-TR", {
    style: "currency",
    currency: "TRY",
  }).format(Number(value));
}

function loadCart() {
  try {
    const savedCart = window.localStorage.getItem(CART_STORAGE_KEY);
    return savedCart ? JSON.parse(savedCart) : {};
  } catch {
    return {};
  }
}

function saveCart() {
  window.localStorage.setItem(CART_STORAGE_KEY, JSON.stringify(state.cart));
}

async function fetchJson(path) {
  const response = await fetch(`${API_BASE_URL}${path}`);
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(getApiErrorMessage(data) || `${path} isteği başarısız oldu.`);
  }
  return data;
}

async function init() {
  bindEvents();
  renderLoading();

  try {
    const [settings, categories, deliveryAreas, products] = await Promise.all([
      fetchJson("/api/market-settings/public"),
      fetchJson("/api/catalog/categories"),
      fetchJson("/api/delivery-areas"),
      fetchJson("/api/catalog/products"),
    ]);
    state.settings = settings;
    state.categories = categories;
    state.deliveryAreas = deliveryAreas;
    state.products = products;
  } catch (error) {
    renderError(error);
    return;
  }

  render();
  startMarketSettingsRefresh();
}

function bindEvents() {
  elements.searchInput.addEventListener("input", (event) => {
    state.search = event.target.value.trim().toLowerCase();
    renderProducts();
  });

  elements.categoryStrip.addEventListener("click", (event) => {
    const button = event.target.closest("button[data-category]");
    if (!button) return;

    state.selectedCategory = button.dataset.category;
    renderCategories();
    renderProducts();
  });

  elements.openCartButton.addEventListener("click", openCart);
  elements.closeCartButton.addEventListener("click", closeCart);
  elements.drawerBackdrop.addEventListener("click", closeCart);
  elements.trackingForm.addEventListener("submit", trackOrder);
  elements.checkoutButton.addEventListener("click", () => {
    elements.orderResult.hidden = true;
    elements.checkoutForm.scrollIntoView({ behavior: "smooth", block: "start" });
  });
  elements.checkoutForm.addEventListener("submit", submitOrder);
}

function renderLoading() {
  elements.productGrid.innerHTML = `
    <div class="empty-state">
      <strong>Ürünler yükleniyor</strong>
      <span>Lütfen bekleyin.</span>
    </div>
  `;
}

function renderError(error) {
  elements.productGrid.innerHTML = `
    <div class="empty-state">
      <strong>Bağlantı kurulamadı</strong>
      <span>${escapeHtml(error.message)}</span>
    </div>
  `;
}

function render() {
  renderMarketSettings();
  renderCategories();
  renderDeliveryAreas();
  renderProducts();
  renderCart();
}

function startMarketSettingsRefresh() {
  if (marketSettingsRefreshTimer) {
    window.clearInterval(marketSettingsRefreshTimer);
  }

  marketSettingsRefreshTimer = window.setInterval(
    refreshMarketSettings,
    MARKET_SETTINGS_REFRESH_INTERVAL_MS,
  );
}

async function refreshMarketSettings() {
  try {
    state.settings = await fetchJson("/api/market-settings/public");
    renderMarketSettings();
    renderProducts();
    renderCart();
  } catch {
    // Sessiz gecilir; siparis olusturma sirasinda backend son karari yine verir.
  }
}

function isAcceptingOrders() {
  return state.settings.is_open !== false && state.settings.accepting_orders !== false;
}

function getClosedMarketMessage() {
  if (state.settings.closed_reason === "OUTSIDE_WORKING_HOURS") {
    return "Market şu anda çalışma saatleri dışında.";
  }

  return "Market şu anda kapalı.";
}

function renderMarketSettings() {
  const acceptingOrders = isAcceptingOrders();

  elements.marketName.textContent = state.settings.market_name;
  elements.marketStatus.textContent = acceptingOrders ? "Açık" : "Kapalı";
  elements.marketStatus.classList.toggle("is-closed", !acceptingOrders);

  const supportUrl = buildWhatsappSupportUrl(state.settings.whatsapp_number);
  elements.whatsappSupportLink.hidden = !supportUrl;
  if (supportUrl) {
    elements.whatsappSupportLink.href = supportUrl;
  }
}

function renderDeliveryAreas() {
  elements.deliveryAreaSelect.innerHTML = [
    `<option value="">Bölge seçin</option>`,
    ...state.deliveryAreas.map((area) => `
      <option value="${area.id}">${escapeHtml(area.name)}</option>
    `),
  ].join("");
}

function renderCategories() {
  const buttons = [
    `<button class="category-chip ${state.selectedCategory === "" ? "is-active" : ""}" type="button" data-category="">Tümü</button>`,
    ...state.categories.map((category) => {
      const isActive = category.slug === state.selectedCategory ? "is-active" : "";
      return `
        <button class="category-chip ${isActive}" type="button" data-category="${escapeHtml(category.slug)}">
          ${escapeHtml(category.name)}
        </button>
      `;
    }),
  ];

  elements.categoryStrip.innerHTML = buttons.join("");
}

function getVisibleProducts() {
  return state.products.filter((product) => {
    const matchesCategory =
      !state.selectedCategory || product.category?.slug === state.selectedCategory;
    const matchesSearch =
      !state.search || product.name.toLowerCase().includes(state.search);
    return matchesCategory && matchesSearch;
  });
}

function renderProducts() {
  const products = getVisibleProducts();
  const acceptingOrders = isAcceptingOrders();
  elements.productCount.textContent = `${products.length} ürün`;
  elements.emptyState.hidden = products.length !== 0;

  elements.productGrid.innerHTML = products
    .map((product) => {
      const stockText = product.is_in_stock
        ? `${product.stock_quantity} adet stokta`
        : "Stokta yok";
      const disabled = product.is_in_stock && acceptingOrders ? "" : "disabled";

      return `
        <article class="product-card">
          <div class="product-image-wrap">
            ${renderProductImage(product)}
          </div>
          <div class="product-info">
            <h3 class="product-name">${escapeHtml(product.name)}</h3>
            <div class="product-meta">
              <span>${escapeHtml(product.category?.name || "Genel")}</span>
              <span class="stock-badge ${product.is_in_stock ? "" : "is-empty"}">${stockText}</span>
            </div>
            <div class="product-bottom">
              <span class="price">${money(product.price)}</span>
              <button class="add-button" type="button" ${disabled} onclick="addToCart(${product.id})">
                Sepete Ekle
              </button>
            </div>
          </div>
        </article>
      `;
    })
    .join("");
}

function addToCart(productId) {
  if (!isAcceptingOrders()) return;

  const product = state.products.find((item) => item.id === productId);
  if (!product || !product.is_in_stock) return;

  const currentQuantity = state.cart[productId]?.quantity || 0;
  if (currentQuantity >= product.stock_quantity) return;

  state.cart[productId] = {
    productId,
    quantity: currentQuantity + 1,
  };
  saveCart();
  elements.orderResult.hidden = true;
  renderCart();
}

function updateCartItem(productId, quantity) {
  if (quantity <= 0) {
    delete state.cart[productId];
  } else {
    const product = state.products.find((item) => item.id === productId);
    if (!product) return;

    state.cart[productId] = {
      productId,
      quantity: Math.min(quantity, product.stock_quantity),
    };
  }

  saveCart();
  elements.orderResult.hidden = true;
  renderCart();
}

function getCartLines() {
  return Object.values(state.cart)
    .map((item) => {
      const product = state.products.find((candidate) => candidate.id === item.productId);
      if (!product) return null;
      return {
        product,
        quantity: item.quantity,
        lineTotal: Number(product.price) * item.quantity,
      };
    })
    .filter(Boolean);
}

function getCartTotals() {
  const lines = getCartLines();
  const subtotal = lines.reduce((total, line) => total + line.lineTotal, 0);
  const deliveryFee = lines.length ? Number(state.settings.delivery_fee) : 0;
  const grandTotal = subtotal + deliveryFee;
  const minimumOrderAmount = Number(state.settings.minimum_order_amount);

  return {
    lines,
    subtotal,
    deliveryFee,
    grandTotal,
    minimumOrderAmount,
    remainingMinimum: Math.max(minimumOrderAmount - subtotal, 0),
    itemCount: lines.reduce((total, line) => total + line.quantity, 0),
  };
}

function renderCart() {
  const totals = getCartTotals();

  elements.cartItemCount.textContent = `${totals.itemCount} ürün`;
  elements.cartBarTotal.textContent = money(totals.subtotal);
  elements.subtotalText.textContent = money(totals.subtotal);
  elements.deliveryFeeText.textContent = money(totals.deliveryFee);
  elements.grandTotalText.textContent = money(totals.grandTotal);

  if (!totals.lines.length) {
    elements.cartItems.innerHTML = `<p class="cart-empty">Sepetiniz boş.</p>`;
  } else {
    elements.cartItems.innerHTML = totals.lines
      .map(({ product, quantity, lineTotal }) => `
        <div class="cart-item">
          ${renderCartProductImage(product)}
          <div class="cart-item-main">
            <div class="cart-item-title">
              <span>${escapeHtml(product.name)}</span>
              <span>${money(lineTotal)}</span>
            </div>
            <div class="cart-item-controls">
              <div class="quantity-control" aria-label="${escapeHtml(product.name)} adet">
                <button type="button" onclick="updateCartItem(${product.id}, ${quantity - 1})">−</button>
                <span>${quantity}</span>
                <button type="button" onclick="updateCartItem(${product.id}, ${quantity + 1})">+</button>
              </div>
              <button class="remove-button" type="button" onclick="updateCartItem(${product.id}, 0)">Sil</button>
            </div>
          </div>
        </div>
      `)
      .join("");
  }

  const acceptingOrders = isAcceptingOrders();
  const hasCartItems = acceptingOrders && totals.lines.length > 0;
  const canSubmit =
    hasCartItems && totals.subtotal >= totals.minimumOrderAmount;
  elements.checkoutButton.disabled = !hasCartItems;
  elements.submitOrderButton.disabled = !canSubmit;

  if (!acceptingOrders) {
    elements.minimumMessage.textContent = getClosedMarketMessage();
    elements.minimumMessage.classList.add("is-warning");
  } else if (!totals.lines.length) {
    elements.minimumMessage.textContent = `Minimum sipariş: ${money(totals.minimumOrderAmount)}`;
    elements.minimumMessage.classList.add("is-warning");
  } else if (totals.remainingMinimum > 0) {
    elements.minimumMessage.textContent = `Sipariş için ${money(totals.remainingMinimum)} daha ekleyin.`;
    elements.minimumMessage.classList.add("is-warning");
  } else {
    elements.minimumMessage.textContent = "Minimum sipariş tutarı tamam.";
    elements.minimumMessage.classList.remove("is-warning");
  }
}

async function submitOrder(event) {
  event.preventDefault();

  const totals = getCartTotals();
  if (!isAcceptingOrders()) {
    showOrderResult(getClosedMarketMessage(), true);
    renderCart();
    return;
  }
  if (!totals.lines.length || totals.subtotal < totals.minimumOrderAmount) return;

  elements.submitOrderButton.disabled = true;
  showOrderResult("Sipariş gönderiliyor...", false);

  const formData = new FormData(elements.checkoutForm);
  const payload = {
    items: totals.lines.map(({ product, quantity }) => ({
      product_id: product.id,
      quantity,
    })),
    customer_first_name: formData.get("customer_first_name"),
    customer_last_name: formData.get("customer_last_name"),
    phone: formData.get("phone"),
    delivery_area_id: Number(formData.get("delivery_area_id")),
    neighborhood: formData.get("neighborhood"),
    street: formData.get("street"),
    apartment: optionalFormValue(formData.get("apartment")),
    flat: optionalFormValue(formData.get("flat")),
    address_line: formData.get("address_line"),
    address_directions: optionalFormValue(formData.get("address_directions")),
    order_note: optionalFormValue(formData.get("order_note")),
    payment_method: formData.get("payment_method"),
    unavailable_policy: formData.get("unavailable_policy"),
  };

  try {
    const response = await fetch(`${API_BASE_URL}/api/orders`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    });
    const data = await response.json();

    if (!response.ok) {
      throw new Error(getApiErrorMessage(data));
    }

    state.cart = {};
    saveCart();
    elements.trackingForm.elements.namedItem("order_number").value = data.order_number;
    elements.trackingForm.elements.namedItem("phone").value = payload.phone;
    elements.checkoutForm.reset();
    showOrderResult(
      `${data.order_number} numaralı sipariş alındı. Genel toplam: ${money(data.grand_total)}. Durumu sipariş takibinden görebilirsiniz.`,
      false,
    );
    renderCart();
  } catch (error) {
    showOrderResult(error.message, true);
  } finally {
    const updatedTotals = getCartTotals();
    elements.submitOrderButton.disabled =
      !isAcceptingOrders() ||
      !updatedTotals.lines.length ||
      updatedTotals.subtotal < updatedTotals.minimumOrderAmount;
  }
}

async function trackOrder(event) {
  event.preventDefault();
  elements.trackOrderButton.disabled = true;
  showTrackingMessage("Sipariş durumu aranıyor.", false);

  const formData = new FormData(elements.trackingForm);
  const query = new URLSearchParams({
    order_number: String(formData.get("order_number") || "").trim(),
    phone: String(formData.get("phone") || "").trim(),
  });

  try {
    const order = await fetchJson(`/api/orders/track?${query}`);
    renderTrackingResult(order);
  } catch (error) {
    showTrackingMessage(error.message, true);
  } finally {
    elements.trackOrderButton.disabled = false;
  }
}

function renderTrackingResult(order) {
  elements.trackingResult.classList.remove("is-error");
  elements.trackingResult.innerHTML = `
    <div class="tracking-result-top">
      <div>
        <strong>${escapeHtml(order.order_number)}</strong>
        <span>${formatDateTime(order.created_at)}</span>
      </div>
      <strong>${statusLabels[order.status] || escapeHtml(order.status)}</strong>
    </div>
    ${renderTrackingTimeline(order.status)}
    <div class="tracking-result-row">
      <span>Müşteri</span>
      <strong>${escapeHtml(order.customer_name)}</strong>
    </div>
    <div class="tracking-result-row">
      <span>Telefon</span>
      <strong>${escapeHtml(order.phone)}</strong>
    </div>
    <div class="tracking-result-row">
      <span>Bölge</span>
      <strong>${escapeHtml(order.delivery_area)}</strong>
    </div>
    <div class="tracking-result-row">
      <span>Ödeme</span>
      <strong>${paymentLabels[order.payment_method] || escapeHtml(order.payment_method)}</strong>
    </div>
    <div class="tracking-result-row">
      <span>Bulunamazsa</span>
      <strong>${unavailableLabels[order.unavailable_policy] || escapeHtml(order.unavailable_policy)}</strong>
    </div>
    ${order.cancellation_reason ? `
      <div class="tracking-result-row">
        <span>İptal sebebi</span>
        <strong>${escapeHtml(order.cancellation_reason)}</strong>
      </div>
    ` : ""}
    <div class="tracking-items">
      ${order.items.map((item) => `
        <div class="tracking-item-line">
          <span>
            <strong>${escapeHtml(item.product_name_snapshot)}</strong>
            <small>${item.quantity} adet · ${money(item.unit_price_snapshot)} / adet</small>
          </span>
          <strong>${money(item.line_total)}</strong>
        </div>
      `).join("")}
    </div>
    <div class="tracking-result-row">
      <span>Gönderim</span>
      <strong>${money(order.delivery_fee)}</strong>
    </div>
    <div class="tracking-result-row">
      <span>Genel toplam</span>
      <strong>${money(order.grand_total)}</strong>
    </div>
  `;
  elements.trackingResult.hidden = false;
}

function renderTrackingTimeline(status) {
  const steps = [
    ["NEW", "Sipariş Alındı"],
    ["PREPARING", "Hazırlanıyor"],
    ["ON_THE_WAY", "Yola Çıktı"],
    ["DELIVERED", "Teslim Edildi"],
  ];
  const currentIndex = status === "CANCELLED"
    ? -1
    : steps.findIndex(([stepStatus]) => stepStatus === status);

  return `
    <div class="tracking-timeline ${status === "CANCELLED" ? "is-cancelled" : ""}">
      ${steps.map(([, label], index) => `
        <div class="timeline-step ${index <= currentIndex ? "is-complete" : ""}">
          <span></span>
          <strong>${label}</strong>
        </div>
      `).join("")}
    </div>
  `;
}

function showTrackingMessage(message, isError) {
  elements.trackingResult.textContent = message;
  elements.trackingResult.classList.toggle("is-error", isError);
  elements.trackingResult.hidden = false;
}

function optionalFormValue(value) {
  const text = String(value || "").trim();
  return text ? text : null;
}

function formatDateTime(value) {
  return new Intl.DateTimeFormat("tr-TR", {
    dateStyle: "short",
    timeStyle: "short",
  }).format(new Date(value));
}

function buildWhatsappSupportUrl(phoneNumber) {
  const digits = String(phoneNumber || "").replace(/\D/g, "");
  if (!digits) return null;

  let normalizedDigits = digits;
  if (normalizedDigits.startsWith("00")) {
    normalizedDigits = normalizedDigits.slice(2);
  } else if (normalizedDigits.startsWith("0") && normalizedDigits.length === 11) {
    normalizedDigits = `90${normalizedDigits.slice(1)}`;
  } else if (normalizedDigits.startsWith("5") && normalizedDigits.length === 10) {
    normalizedDigits = `90${normalizedDigits}`;
  }

  if (normalizedDigits.length < 10 || normalizedDigits.length > 15) return null;

  const message = encodeURIComponent("Merhaba, siparişim hakkında destek almak istiyorum.");
  return `https://wa.me/${normalizedDigits}?text=${message}`;
}

function showOrderResult(message, isError) {
  elements.orderResult.textContent = message;
  elements.orderResult.classList.toggle("is-error", isError);
  elements.orderResult.hidden = false;
}

function renderProductImage(product) {
  const image = resolveImageUrl(product.image_url);
  if (!image) {
    return `<div class="product-image-fallback" aria-hidden="true">Ürün</div>`;
  }

  return `<img class="product-image" src="${escapeHtml(image)}" alt="${escapeHtml(product.name)}" loading="lazy" />`;
}

function renderCartProductImage(product) {
  const image = resolveImageUrl(product.image_url);
  if (!image) {
    return `<div class="cart-image-fallback" aria-hidden="true">Ürün</div>`;
  }

  return `<img src="${escapeHtml(image)}" alt="${escapeHtml(product.name)}" />`;
}

function resolveImageUrl(imageUrl) {
  const text = String(imageUrl || "").trim();
  if (!text) return "";

  if (text.startsWith("/")) {
    return `${API_BASE_URL}${text}`;
  }

  return text;
}

function getApiErrorMessage(data) {
  if (data?.detail?.code === "MINIMUM_ORDER_NOT_MET") {
    return `Sipariş için ${money(data.detail.remaining)} daha ekleyin.`;
  }

  if (data?.detail?.message) {
    return data.detail.message;
  }

  if (Array.isArray(data?.detail)) {
    return "Lütfen teslimat bilgilerini kontrol edin.";
  }

  return "Sipariş oluşturulamadı.";
}

function openCart() {
  elements.drawerBackdrop.hidden = false;
  elements.cartDrawer.classList.add("is-open");
  elements.cartDrawer.setAttribute("aria-hidden", "false");
}

function closeCart() {
  elements.drawerBackdrop.hidden = true;
  elements.cartDrawer.classList.remove("is-open");
  elements.cartDrawer.setAttribute("aria-hidden", "true");
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

window.addToCart = addToCart;
window.updateCartItem = updateCartItem;

init();
