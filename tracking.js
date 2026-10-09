(function () {
  const TRACK_DB = "DealDhamakaTracking";
  const TRACK_VER = 2;
  let trackDB = null;
  let batchQueue = [];
  let batchIndex = 0;

  const $ = id => document.getElementById(id);
  const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({
    "&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"
  }[c]));

  function uid() {
    return crypto.randomUUID ? crypto.randomUUID() :
      Date.now() + "-" + Math.random();
  }

  function openTrackingDB() {
    return new Promise((resolve, reject) => {
      const r = indexedDB.open(TRACK_DB, TRACK_VER);

      r.onupgradeneeded = () => {
        const db = r.result;

        if (!db.objectStoreNames.contains("productMeta")) {
          db.createObjectStore("productMeta", { keyPath: "productId" });
        }

        if (!db.objectStoreNames.contains("shares")) {
          db.createObjectStore("shares", { keyPath: "id" });
        }
      };

      r.onsuccess = () => {
        trackDB = r.result;
        resolve(trackDB);
      };

      r.onerror = () => reject(r.error);
    });
  }

  function allTracking(store) {
    return new Promise((resolve, reject) => {
      const tx = trackDB.transaction(store, "readonly");
      const req = tx.objectStore(store).getAll();
      req.onsuccess = () => resolve(req.result);
      req.onerror = () => reject(req.error);
    });
  }

  function putTracking(store, obj) {
    return new Promise((resolve, reject) => {
      const tx = trackDB.transaction(store, "readwrite");
      tx.objectStore(store).put(obj);
      tx.oncomplete = resolve;
      tx.onerror = () => reject(tx.error);
    });
  }

  async function getMain(store) {
    return new Promise((resolve, reject) => {
      const req = indexedDB.open("DealDhamakaAgent", 1);

      req.onsuccess = () => {
        const db = req.result;
        const tx = db.transaction(store, "readonly");
        const r = tx.objectStore(store).getAll();

        r.onsuccess = () => {
          resolve(r.result);
          db.close();
        };

        r.onerror = () => reject(r.error);
      };

      req.onerror = () => reject(req.error);
    });
  }

  function injectStyles() {
    if ($("trackingEnhancedStyles")) return;

    const style = document.createElement("style");
    style.id = "trackingEnhancedStyles";

    style.textContent = `
      .multiBox{
        background:#fff;
        border-radius:18px;
        padding:16px;
        margin-top:12px;
        box-shadow:0 3px 15px #00000010;
      }

      .multiHead{
        display:flex;
        justify-content:space-between;
        align-items:center;
        gap:10px;
        margin-bottom:12px;
      }

      .multiHead h3{
        margin:0;
      }

      .multiActions{
        display:flex;
        gap:8px;
      }

      .multiActions button{
        border:0;
        background:#e8eefc;
        color:#2878ed;
        padding:8px 12px;
        border-radius:10px;
        font-weight:700;
      }

      .multiList{
        max-height:260px;
        overflow:auto;
      }

      .multiItem{
        display:flex;
        align-items:center;
        gap:12px;
        padding:12px 4px;
        border-bottom:1px solid #eee;
      }

      .multiItem:last-child{
        border-bottom:0;
      }

      .multiItem input{
        width:20px;
        height:20px;
      }

      .multiItem div{
        flex:1;
      }

      .multiItem strong{
        display:block;
      }

      .multiItem small{
        color:#6b7280;
      }

      .batchInfo{
        background:#eef7f0;
        color:#166534;
        padding:12px;
        border-radius:12px;
        margin-top:12px;
        font-weight:700;
      }

      .batchNext{
        margin-top:12px;
        width:100%;
        border:0;
        border-radius:14px;
        padding:15px;
        background:#16a34a;
        color:#fff;
        font-size:17px;
        font-weight:800;
      }

      .trackSummary{
        display:grid;
        grid-template-columns:1fr 1fr;
        gap:12px;
        margin:15px 0;
      }

      .trackCard{
        background:#fff;
        border-radius:18px;
        padding:18px;
        box-shadow:0 3px 15px #00000010;
      }

      .trackCard b{
        display:block;
        font-size:30px;
      }

      .trackCard span{
        color:#6b7280;
        font-weight:700;
      }

      .trackSection{
        background:#fff;
        border-radius:18px;
        padding:18px;
        margin-top:15px;
        box-shadow:0 3px 15px #00000010;
      }

      .trackSection h3{
        margin-top:0;
      }

      .trackRow{
        padding:13px 0;
        border-bottom:1px solid #eee;
      }

      .trackRow:last-child{
        border-bottom:0;
      }

      .trackRow strong{
        display:block;
        font-size:17px;
      }

      .trackRow small{
        color:#6b7280;
      }

      .metaSave{
        width:100%;
        margin-top:8px;
      }

      .queueBadge{
        display:inline-block;
        background:#111827;
        color:white;
        border-radius:20px;
        padding:5px 10px;
        font-size:13px;
      }
    `;

    document.head.appendChild(style);
  }

  async function getProductsAndContacts() {
    const products = await getMain("products");
    const contacts = await getMain("contacts");
    return { products, contacts };
  }

  async function getMetaMap() {
    const rows = await allTracking("productMeta");
    const map = {};
    rows.forEach(x => map[x.productId] = x);
    return map;
  }

  async function saveMeta(productId, brand, productType) {
    await putTracking("productMeta", {
      productId,
      brand: brand.trim(),
      productType: productType.trim()
    });
  }

  async function renderTrackingPage() {
    const page = $("tracking");
    if (!page) return;

    const { products } = await getProductsAndContacts();
    const meta = await getMetaMap();
    const shares = await allTracking("shares");

    const brands = new Set(
      shares.map(x => x.brand).filter(Boolean)
    );

    const types = new Set(
      shares.map(x => x.productType).filter(Boolean)
    );

    const recipients = new Set(
      shares.map(x => x.contactName).filter(Boolean)
    );

    page.innerHTML = `
      <div class="sectionhead">
        <div>
          <h2>Tracking</h2>
          <p>Brand, product type & recipient tracking</p>
        </div>
      </div>

      <div class="trackSummary">
        <div class="trackCard">
          <b>${shares.length}</b>
          <span>Total Shares</span>
        </div>

        <div class="trackCard">
          <b>${brands.size}</b>
          <span>Brands</span>
        </div>

        <div class="trackCard">
          <b>${types.size}</b>
          <span>Product Types</span>
        </div>

        <div class="trackCard">
          <b>${recipients.size}</b>
          <span>Recipients</span>
        </div>
      </div>

      <div class="trackSection">
        <h3>Product Information</h3>
        <p class="hint">
          Set the Brand Name and Product Type for each product.
        </p>

        ${
          products.length
          ? products.map(p => `
            <div class="multiBox">
              <h3>${esc(p.name)}</h3>
              <p class="hint">${esc(p.platform || "")}</p>

              <input
                id="brand_${p.id}"
                placeholder="Brand Name e.g. Nike"
                value="${esc(meta[p.id]?.brand || "")}"
              >

              <input
                id="type_${p.id}"
                placeholder="Product Type e.g. Shoes"
                value="${esc(meta[p.id]?.productType || "")}"
              >

              <button
                class="primary big metaSave"
                onclick="window.saveTrackingMeta('${p.id}')"
              >
                Save Product Info
              </button>
            </div>
          `).join("")
          : `<div class="empty">No products found.<br>Add products first.</div>`
        }
      </div>

      <div class="trackSection">
        <h3>Brand & Product Type Summary</h3>

        ${
          shares.length
          ? buildBrandSummary(shares)
          : `<div class="empty">No shares tracked yet.</div>`
        }
      </div>

      <div class="trackSection">
      <h3>Date-wise Summary</h3>
      ${shares.length ? buildDateSummary(shares) : `<div class="empty">No shares tracked yet.</div>`}
</div>
        <h3>Recipient Summary</h3>

        ${
          shares.length
          ? buildRecipientSummary(shares)
          : `<div class="empty">No shares tracked yet.</div>`
        }
      </div>

      <div class="trackSection">
        <h3>Recent Shares</h3>

        ${
          shares.length
          ? shares
            .sort((a,b) => b.time - a.time)
            .slice(0,50)
            .map(x => `
              <div class="trackRow">
                <strong>
                  ${esc(x.contactName)} → ${esc(x.productName)}
                </strong>

                <small>
                  ${esc(x.brand || "No Brand")} ·
                  ${esc(x.productType || "No Type")} ·
                  ${new Date(x.time).toLocaleString()}
                </small>
              </div>
            `).join("")
          : `<div class="empty">No shares tracked yet.</div>`
        }
      </div>
    `;
  }

  function buildBrandSummary(shares) {
    const map = {};

    shares.forEach(x => {
      const key =
        (x.brand || "No Brand") +
        "||" +
        (x.productType || "No Type");

      if (!map[key]) {
        map[key] = {
          brand: x.brand || "No Brand",
          type: x.productType || "No Type",
          count: 0,
          people: new Set()
        };
      }

      map[key].count++;
      map[key].people.add(x.contactName);
    });

    return Object.values(map)
      .sort((a,b) => b.count - a.count)
      .map(x => `
        <div class="trackRow">
          <strong>
            ${esc(x.brand)} → ${esc(x.type)}
            <span class="queueBadge">${x.count} shares</span>
          </strong>

          <small>
            Recipients: ${esc([...x.people].join(", "))}
          </small>
        </div>
      `).join("");
  }

  function buildRecipientSummary(shares) {
    const map = {};

    shares.forEach(x => {
      if (!map[x.contactName]) {
        map[x.contactName] = {
          count:0,
          products:new Set()
        };
      }

      map[x.contactName].count++;
      map[x.contactName].products.add(x.productName);
    });

    return Object.entries(map)
      .sort((a,b) => b[1].count - a[1].count)
      .map(([name,x]) => `
        <div class="trackRow">
          <strong>
            ${esc(name)}
            <span class="queueBadge">${x.count} shares</span>
          </strong>

          <small>
            Products: ${esc([...x.products].join(", "))}
          </small>
        </div>
      `).join("");
  }

  window.saveTrackingMeta = async function (productId) {
    const brand = $("brand_" + productId)?.value || "";
    const type = $("type_" + productId)?.value || "";

    if (!brand.trim() || !type.trim()) {
      alert("Please enter both Brand Name and Product Type.");
      return;
    }

    await saveMeta(productId, brand, type);
    alert("Product information saved.");
    renderTrackingPage();
  };

  async function recordShare(contact, product) {
    const meta = await getMetaMap();
    const m = meta[product.id] || {};

    await putTracking("shares", {
      id: uid(),
      contactId: contact.id,
      contactName: contact.name,
      phone: contact.phone,
      productId: product.id,
      productName: product.name,
      brand: m.brand || "",
      productType: m.productType || "",
      time: Date.now()
    });
  }

  async function createSendUI() {
    const send = $("send");
    if (!send) return;

    if ($("multiSendUI")) return;

    const card = send.querySelector(".card");
    if (!card) return;

    const ui = document.createElement("div");
    ui.id = "multiSendUI";

    ui.innerHTML = `
      <div class="multiBox">
        <div class="multiHead">
          <h3>Select Contacts</h3>

          <div class="multiActions">
            <button id="selectAllContacts">All</button>
            <button id="clearContacts">Clear</button>
          </div>
        </div>

        <div id="multiContacts" class="multiList"></div>
      </div>

      <div class="multiBox">
        <div class="multiHead">
          <h3>Select Products</h3>

          <div class="multiActions">
            <button id="selectAllProducts">All</button>
            <button id="clearProducts">Clear</button>
          </div>
        </div>

        <div id="multiProducts" class="multiList"></div>
      </div>

      <div id="batchInfo" class="batchInfo">
        Select contacts and products to create a batch.
      </div>

      <button id="batchNext" class="batchNext">
        Open WhatsApp
      </button>
    `;

    card.insertBefore(ui, card.firstChild);

    const oldContact = $("sendContact")?.parentElement;
    const oldProduct = $("sendProduct")?.parentElement;

    if (oldContact) oldContact.style.display = "none";
    if (oldProduct) oldProduct.style.display = "none";

    const oldButton = $("openWhatsApp");
    if (oldButton) oldButton.style.display = "none";

    await renderMultiLists();
    setupMultiEvents();
    updateBatchInfo();
  }

  async function renderMultiLists() {
    const { contacts, products } = await getProductsAndContacts();

    $("multiContacts").innerHTML = contacts.length
      ? contacts.map(c => `
        <label class="multiItem">
          <input
            type="checkbox"
            class="contactCheck"
            value="${esc(c.id)}"
          >
          <div>
            <strong>${esc(c.name)}</strong>
            <small>${esc(c.phone)}</small>
          </div>
        </label>
      `).join("")
      : `<div class="empty">No contacts available.</div>`;

    $("multiProducts").innerHTML = products.length
      ? products.map(p => `
        <label class="multiItem">
          <input
            type="checkbox"
            class="productCheck"
            value="${esc(p.id)}"
          >
          <div>
            <strong>${esc(p.name)}</strong>
            <small>${esc(p.platform || "")}</small>
          </div>
        </label>
      `).join("")
      : `<div class="empty">No products available.</div>`;

    document.querySelectorAll(".contactCheck,.productCheck")
      .forEach(x => x.onchange = updateBatchInfo);
  }

  function setupMultiEvents() {
    $("selectAllContacts").onclick = () => {
      document.querySelectorAll(".contactCheck")
        .forEach(x => x.checked = true);
      updateBatchInfo();
    };

    $("clearContacts").onclick = () => {
      document.querySelectorAll(".contactCheck")
        .forEach(x => x.checked = false);
      updateBatchInfo();
    };

    $("selectAllProducts").onclick = () => {
      document.querySelectorAll(".productCheck")
        .forEach(x => x.checked = true);
      updateBatchInfo();
    };

    $("clearProducts").onclick = () => {
      document.querySelectorAll(".productCheck")
        .forEach(x => x.checked = false);
      updateBatchInfo();
    };

    $("batchNext").onclick = processNextBatch;
  }

  async function getSelectedBatch() {
    const { contacts, products } = await getProductsAndContacts();

    const contactIds = [...document.querySelectorAll(".contactCheck:checked")]
      .map(x => x.value);

    const productIds = [...document.querySelectorAll(".productCheck:checked")]
      .map(x => x.value);

    const selectedContacts =
      contacts.filter(x => contactIds.includes(x.id));

    const selectedProducts =
      products.filter(x => productIds.includes(x.id));

    const queue = [];

    selectedContacts.forEach(c => {
      selectedProducts.forEach(p => {
        queue.push({
          contactId:c.id,
          productId:p.id
        });
      });
    });

    return {
      contacts:selectedContacts,
      products:selectedProducts,
      queue
    };
  }

  async function updateBatchInfo() {
    const batch = await getSelectedBatch();

    const total = batch.queue.length;

    if (!total) {
      $("batchInfo").textContent =
        "Select contacts and products to create a batch.";

      $("batchNext").textContent = "Open WhatsApp";
      return;
    }

    $("batchInfo").textContent =
      `${batch.contacts.length} contact(s) × ` +
      `${batch.products.length} product(s) = ` +
      `${total} WhatsApp message(s)`;
  }

  async function prepareQueue() {
    const batch = await getSelectedBatch();

    if (!batch.queue.length) {
      alert("Please select at least one contact and one product.");
      return false;
    }

    batchQueue = batch.queue;
    batchIndex = 0;

    localStorage.setItem(
      "dealDhamakaBatchQueue",
      JSON.stringify(batchQueue)
    );

    localStorage.setItem(
      "dealDhamakaBatchIndex",
      "0"
    );

    return true;
  }

  function loadSavedQueue() {
    try {
      batchQueue =
        JSON.parse(
          localStorage.getItem("dealDhamakaBatchQueue") || "[]"
        );

      batchIndex =
        Number(
          localStorage.getItem("dealDhamakaBatchIndex") || 0
        );
    } catch {
      batchQueue = [];
      batchIndex = 0;
    }
  }

  async function processNextBatch() {
  if (!batchQueue.length || batchIndex >= batchQueue.length) {
    const ok = await prepareQueue();
    if (!ok) return;
  }

  const item = batchQueue[batchIndex];

  const { contacts, products } = await getProductsAndContacts();

  const contact = contacts.find(x => x.id === item.contactId);
  const product = products.find(x => x.id === item.productId);

  if (!contact || !product) {
    batchIndex++;
    localStorage.setItem(
      "dealDhamakaBatchIndex",
      String(batchIndex)
    );
    return processNextBatch();
  }

  const message =
    `🔥 *Deal Alert!*\n\n` +
    `Hi ${contact.name} 👋\n\n` +
    `Check out this amazing deal:\n` +
    `🛍️ *${product.name}*\n` +
    `${product.price ? `💰 ₹${product.price}\n` : ""}` +
    `${product.description ? `\n${product.description}\n` : ""}` +
    `\n🔗 Buy Now: ${product.link}\n\n` +
    `Happy Shopping! ❤️`;

  const phone = contact.phone.replace(/\D/g, "");

  if (phone.length < 10) {
    alert("Invalid WhatsApp number for " + contact.name);
    return;
  }

  /*
   * Record this share only when this WhatsApp step is opened.
   * The user still has to tap Send inside WhatsApp.
   */
  await recordShare(contact, product);

  const remaining = batchQueue.length - batchIndex - 1;

  $("batchInfo").textContent =
    remaining > 0
      ? `✅ ${batchIndex + 1} of ${batchQueue.length} opened. ${remaining} remaining.`
      : `🎉 Batch completed. ${batchQueue.length} message(s) opened.`;

  $("batchNext").textContent =
    remaining > 0
      ? `Open Next WhatsApp (${remaining} left)`
      : "Start New Batch";

  batchIndex++;

  localStorage.setItem(
    "dealDhamakaBatchIndex",
    String(batchIndex)
  );

  window.location.href =
    `https://wa.me/${phone}?text=${encodeURIComponent(message)}`;
}

  function enhanceNavigation() {
    const trackingTab =
      [...document.querySelectorAll(".tabbar button")]
        .find(x => x.dataset.page === "tracking");

    if (!trackingTab) return;

    trackingTab.onclick = async () => {
      if (typeof showPage === "function") {
        showPage("tracking");
      }

      await renderTrackingPage();
    };
  }

  async function init() {
    try {
      injectStyles();
      await openTrackingDB();

      loadSavedQueue();

      await createSendUI();
      enhanceNavigation();

      if ($("tracking")) {
        await renderTrackingPage();
      }

      const originalShowPage = window.showPage;

      if (originalShowPage && !originalShowPage.__trackingEnhanced) {
        const wrapped = function(name) {
          originalShowPage(name);

          if (name === "send") {
            setTimeout(async () => {
              await createSendUI();
              loadSavedQueue();
              updateBatchInfo();
            }, 50);
          }

          if (name === "tracking") {
            setTimeout(renderTrackingPage, 50);
          }
        };

        wrapped.__trackingEnhanced = true;
        window.showPage = wrapped;
      }

    } catch (e) {
      console.error("Tracking initialization error:", e);
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }

})();