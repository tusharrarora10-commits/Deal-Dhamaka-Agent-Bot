(function () {
  const TRACK_DB = "DealDhamakaTracking";
  const TRACK_VER = 1;
  let trackDB = null;

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

  function saveTracking(store, data) {
    return new Promise((resolve, reject) => {
      const tx = trackDB.transaction(store, "readwrite");
      tx.objectStore(store).put(data);

      tx.oncomplete = () => resolve();
      tx.onerror = () => reject(tx.error);
    });
  }

  function uid() {
    return crypto.randomUUID
      ? crypto.randomUUID()
      : Date.now() + "-" + Math.random();
  }

  function esc(s) {
    return String(s ?? "").replace(/[&<>"']/g, c => ({
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
      "'": "&#39;"
    }[c]));
  }

  function getAppData(store) {
    return new Promise((resolve, reject) => {
      const r = indexedDB.open("DealDhamakaAgent", 1);

      r.onsuccess = () => {
        const db = r.result;

        if (!db.objectStoreNames.contains(store)) {
          resolve([]);
          return;
        }

        const tx = db.transaction(store, "readonly");
        const req = tx.objectStore(store).getAll();

        req.onsuccess = () => resolve(req.result);
        req.onerror = () => reject(req.error);
      };

      r.onerror = () => reject(r.error);
    });
  }

  function addStyles() {
    if (document.getElementById("trackingStyles")) return;

    const style = document.createElement("style");
    style.id = "trackingStyles";

    style.textContent = `
      #tracking .trackstats {
        display:grid;
        grid-template-columns:repeat(2,1fr);
        gap:10px;
        margin-bottom:14px;
      }

      #tracking .trackstat {
        background:#fff;
        border-radius:16px;
        padding:16px;
        box-shadow:0 2px 8px #00000012;
      }

      #tracking .trackstat b {
        display:block;
        font-size:25px;
        margin-bottom:4px;
      }

      #tracking .trackstat span {
        color:#6b7280;
        font-size:13px;
      }

      #tracking .trackcard {
        background:#fff;
        border-radius:16px;
        padding:16px;
        margin-bottom:12px;
        box-shadow:0 2px 8px #00000012;
      }

      #tracking .trackcard h3 {
        margin:0 0 6px;
      }

      #tracking .trackcard p {
        margin:5px 0;
        color:#6b7280;
        font-size:14px;
      }

      #tracking .trackinput {
        width:100%;
        box-sizing:border-box;
        margin-top:8px;
        padding:12px;
        border:1px solid #d1d5db;
        border-radius:10px;
        font-size:16px;
      }

      #tracking .trackbtn {
        width:100%;
        margin-top:10px;
        padding:12px;
        border:0;
        border-radius:10px;
        background:#111827;
        color:white;
        font-weight:700;
      }

      #tracking .trackbadge {
        display:inline-block;
        background:#eef2ff;
        padding:5px 9px;
        border-radius:999px;
        font-size:12px;
        margin-top:5px;
      }

      #tracking .empty {
        text-align:center;
        padding:25px;
        color:#6b7280;
      }
    `;

    document.head.appendChild(style);
  }

  function createTrackingPage() {
    if (document.getElementById("tracking")) return;

    const main = document.querySelector("main");

    const section = document.createElement("section");
    section.id = "tracking";
    section.className = "page";

    section.innerHTML = `
      <div class="sectionhead">
        <div>
          <h2>Tracking</h2>
          <p>Brand, product type & recipient tracking</p>
        </div>
      </div>

      <div class="trackstats">
        <div class="trackstat">
          <b id="trackTotal">0</b>
          <span>Total Shares</span>
        </div>

        <div class="trackstat">
          <b id="trackBrands">0</b>
          <span>Brands</span>
        </div>

        <div class="trackstat">
          <b id="trackTypes">0</b>
          <span>Product Types</span>
        </div>

        <div class="trackstat">
          <b id="trackRecipients">0</b>
          <span>Recipients</span>
        </div>
      </div>

      <div class="trackcard">
        <h3>Product Information</h3>
        <p>Set the Brand Name and Product Type for each product.</p>
      </div>

      <div id="trackingProducts"></div>

      <div class="trackcard">
        <h3>Brand & Product Type Summary</h3>
      </div>

      <div id="trackingSummary"></div>

      <div class="trackcard">
        <h3>Recipient Summary</h3>
      </div>

      <div id="trackingRecipients"></div>
    `;

    main.appendChild(section);

    const nav = document.querySelector(".tabbar");

    const button = document.createElement("button");
    button.dataset.page = "tracking";
    button.innerHTML = `📊<span>Tracking</span>`;

    button.onclick = () => {
      if (typeof showPage === "function") {
        showPage("tracking");
      } else {
        document.querySelectorAll(".page").forEach(x =>
          x.classList.toggle("active", x.id === "tracking")
        );
      }

      renderTracking();
    };

    nav.appendChild(button);
  }

  async function renderTracking() {
    if (!trackDB) return;

    const products = await getAppData("products");
    const shares = await allTracking("shares");
    const meta = await allTracking("productMeta");

    const metaMap = {};
    meta.forEach(x => metaMap[x.productId] = x);

    const brands = new Set(
      shares.map(x => x.brand).filter(Boolean)
    );

    const types = new Set(
      shares.map(x => x.productType).filter(Boolean)
    );

    const recipients = new Set(
      shares.map(x => x.contactName).filter(Boolean)
    );

    document.getElementById("trackTotal").textContent = shares.length;
    document.getElementById("trackBrands").textContent = brands.size;
    document.getElementById("trackTypes").textContent = types.size;
    document.getElementById("trackRecipients").textContent = recipients.size;

    const productBox = document.getElementById("trackingProducts");

    if (!products.length) {
      productBox.innerHTML = `
        <div class="empty">
          No products found.<br>
          Add products from the Products section first.
        </div>
      `;
    } else {
      productBox.innerHTML = products.map(p => {
        const m = metaMap[p.id] || {};

        return `
          <div class="trackcard">
            <h3>${esc(p.name)}</h3>
            <p>${esc(p.platform || "")}</p>

            <input
              class="trackinput"
              id="brand_${esc(p.id)}"
              placeholder="Brand Name e.g. Nike"
              value="${esc(m.brand || "")}"
            >

            <input
              class="trackinput"
              id="type_${esc(p.id)}"
              placeholder="Product Type e.g. Shoes"
              value="${esc(m.productType || "")}"
            >

            <button
              class="trackbtn"
              data-save-product="${esc(p.id)}"
            >
              Save Product Info
            </button>
          </div>
        `;
      }).join("");

      document.querySelectorAll("[data-save-product]").forEach(btn => {
        btn.onclick = async () => {
          const id = btn.dataset.saveProduct;

          const brand =
            document.getElementById("brand_" + id).value.trim();

          const productType =
            document.getElementById("type_" + id).value.trim();

          if (!brand || !productType) {
            alert("Please enter Brand Name and Product Type.");
            return;
          }

          await saveTracking("productMeta", {
            productId: id,
            brand,
            productType
          });

          alert("Product information saved.");
          renderTracking();
        };
      });
    }

    const groups = {};

    shares.forEach(x => {
      const key =
        (x.brand || "Unknown Brand") +
        "||" +
        (x.productType || "Unknown Type");

      if (!groups[key]) {
        groups[key] = {
          brand: x.brand || "Unknown Brand",
          type: x.productType || "Unknown Type",
          count: 0,
          recipients: new Set()
        };
      }

      groups[key].count++;
      groups[key].recipients.add(x.contactName);
    });

    const summaryBox = document.getElementById("trackingSummary");

    const groupList = Object.values(groups);

    summaryBox.innerHTML = groupList.length
      ? groupList
          .sort((a, b) => b.count - a.count)
          .map(x => `
            <div class="trackcard">
              <h3>${esc(x.brand)}</h3>
              <span class="trackbadge">${esc(x.type)}</span>
              <p><b>${x.count}</b> share(s)</p>
              <p>Recipients: ${esc(
                Array.from(x.recipients).join(", ")
              )}</p>
            </div>
          `)
          .join("")
      : `<div class="empty">No shares tracked yet.</div>`;

    const recipientGroups = {};

    shares.forEach(x => {
      if (!recipientGroups[x.contactName]) {
        recipientGroups[x.contactName] = {
          count: 0,
          products: new Set()
        };
      }

      recipientGroups[x.contactName].count++;

      recipientGroups[x.contactName].products.add(
        (x.brand || "Unknown") +
        " - " +
        (x.productType || "Unknown")
      );
    });

    const recipientBox =
      document.getElementById("trackingRecipients");

    const recipientList =
      Object.entries(recipientGroups)
        .sort((a, b) => b[1].count - a[1].count);

    recipientBox.innerHTML = recipientList.length
      ? recipientList.map(([name, data]) => `
          <div class="trackcard">
            <h3>${esc(name)}</h3>
            <p><b>${data.count}</b> share(s) received</p>
            <p>${esc(
              Array.from(data.products).join(", ")
            )}</p>
          </div>
        `).join("")
      : `<div class="empty">No recipient data yet.</div>`;
  }

  async function setupWhatsAppTracking() {
    const btn = document.getElementById("openWhatsApp");

    if (!btn) return;

    const originalHandler = btn.onclick;

    if (!originalHandler) return;

    btn.onclick = async function (event) {
      const contacts = await getAppData("contacts");
      const products = await getAppData("products");

      const contact =
        contacts.find(x =>
          x.id === document.getElementById("sendContact").value
        );

      const product =
        products.find(x =>
          x.id === document.getElementById("sendProduct").value
        );

      if (!contact || !product) {
        return originalHandler.call(this, event);
      }

      let metaList = await allTracking("productMeta");

      let meta =
        metaList.find(x => x.productId === product.id);

      if (!meta || !meta.brand || !meta.productType) {
        const brand = prompt(
          "Enter Brand Name for:\n" + product.name
        );

        if (!brand) {
          alert("Brand Name is required for tracking.");
          return;
        }

        const productType = prompt(
          "Enter Product Type for:\n" + product.name
        );

        if (!productType) {
          alert("Product Type is required for tracking.");
          return;
        }

        meta = {
          productId: product.id,
          brand: brand.trim(),
          productType: productType.trim()
        };

        await saveTracking("productMeta", meta);
      }

      await saveTracking("shares", {
        id: uid(),
        productId: product.id,
        productName: product.name,
        brand: meta.brand,
        productType: meta.productType,
        contactName: contact.name,
        phone: contact.phone,
        time: Date.now()
      });

      return originalHandler.call(this, event);
    };
  }

  async function initTracking() {
    try {
      await openTrackingDB();

      addStyles();
      createTrackingPage();
      await setupWhatsAppTracking();
      await renderTracking();

      console.log("Deal Dhamaka Tracking ready.");
    } catch (error) {
      console.error("Tracking error:", error);
    }
  }

  initTracking();
})();