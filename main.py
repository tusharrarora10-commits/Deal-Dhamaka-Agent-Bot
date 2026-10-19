"""Product Quantity Tracker + WhatsApp sender - desktop app entry point."""
import queue
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog

import db
import file_import
import whatsapp


class DuplicateDialog(tk.Toplevel):
    """Asks the user how to handle a product name that already exists."""

    def __init__(self, parent, product_name, existing_qty, incoming_qty):
        super().__init__(parent)
        self.title("Product already exists")
        self.resizable(False, False)
        self.result = None  # "increase" | "new" | None (cancelled)
        self.transient(parent)
        self.grab_set()

        msg = (
            f"'{product_name}' already exists with quantity {existing_qty}.\n\n"
            f"Incoming quantity from file: {incoming_qty}\n\n"
            "Do you want to increase the existing quantity, "
            "or create this as a new separate product entry?"
        )
        tk.Label(self, text=msg, justify="left", wraplength=360, padx=16, pady=16).pack()

        btn_frame = tk.Frame(self, pady=10)
        btn_frame.pack()

        ttk.Button(btn_frame, text="Increase Quantity", command=self._on_increase).pack(side="left", padx=6)
        ttk.Button(btn_frame, text="Create New Entry", command=self._on_new).pack(side="left", padx=6)
        ttk.Button(btn_frame, text="Cancel this item", command=self._on_cancel).pack(side="left", padx=6)

        self.protocol("WM_DELETE_WINDOW", self._on_cancel)
        self.update_idletasks()
        self.geometry(f"+{parent.winfo_rootx() + 40}+{parent.winfo_rooty() + 40}")
        self.wait_window(self)

    def _on_increase(self):
        self.result = "increase"
        self.destroy()

    def _on_new(self):
        self.result = "new"
        self.destroy()

    def _on_cancel(self):
        self.result = None
        self.destroy()


class ProductEditDialog(tk.Toplevel):
    """Edit a product's saved Description/Amazon Link, and see who it's been sent to."""

    def __init__(self, parent, product):
        super().__init__(parent)
        self.title(f"{product['product_name']} (Qty: {product['quantity']})")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        self.product_id = product["id"]
        self.saved = False

        frame = tk.Frame(self, padx=12, pady=12)
        frame.pack()

        tk.Label(frame, text="Description:").grid(row=0, column=0, sticky="nw", pady=4)
        self.desc_text = tk.Text(frame, width=44, height=5, wrap="word")
        self.desc_text.insert("1.0", product.get("description") or "")
        self.desc_text.grid(row=0, column=1, pady=4)

        tk.Label(frame, text="Amazon Link:").grid(row=1, column=0, sticky="w", pady=4)
        self.link_entry = tk.Entry(frame, width=44)
        self.link_entry.insert(0, product.get("amazon_link") or "")
        self.link_entry.grid(row=1, column=1, pady=4)

        btn_frame = tk.Frame(self, pady=10)
        btn_frame.pack()
        ttk.Button(btn_frame, text="Save", command=self._on_save).pack(side="left", padx=6)
        ttk.Button(btn_frame, text="Cancel", command=self.destroy).pack(side="left", padx=6)

        tk.Label(self, text="Sent to:", padx=12).pack(anchor="w")
        history = db.get_message_log_for_product(self.product_id)
        columns = ("contact", "phone", "sent_at")
        history_tree = ttk.Treeview(self, columns=columns, show="headings", height=6)
        history_tree.heading("contact", text="Contact")
        history_tree.heading("phone", text="Phone")
        history_tree.heading("sent_at", text="Sent At")
        history_tree.column("contact", width=140)
        history_tree.column("phone", width=130)
        history_tree.column("sent_at", width=150)
        history_tree.pack(fill="x", padx=12, pady=(0, 12))
        if history:
            for row in history:
                history_tree.insert("", "end", values=(row["contact_name"], row["contact_phone"], row["sent_at"]))
        else:
            tk.Label(self, text="No WhatsApp messages sent for this product yet.", fg="gray40", padx=12).pack(anchor="w", pady=(0, 12))

        self.update_idletasks()
        self.geometry(f"+{parent.winfo_rootx() + 60}+{parent.winfo_rooty() + 60}")
        self.wait_window(self)

    def _on_save(self):
        description = self.desc_text.get("1.0", "end").strip()
        amazon_link = self.link_entry.get().strip()
        db.update_product_details(self.product_id, description, amazon_link)
        self.saved = True
        self.destroy()


class ContactFormDialog(tk.Toplevel):
    """Add or edit a single contact (Name + Phone)."""

    def __init__(self, parent, contact=None):
        super().__init__(parent)
        self.title("Edit Contact" if contact else "Add Contact")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        self.contact = contact
        self.result = None  # (name, phone) on save

        frame = tk.Frame(self, padx=12, pady=12)
        frame.pack()

        tk.Label(frame, text="Name:").grid(row=0, column=0, sticky="w", pady=4)
        self.name_entry = tk.Entry(frame, width=32)
        self.name_entry.insert(0, contact["name"] if contact else "")
        self.name_entry.grid(row=0, column=1, pady=4)

        tk.Label(frame, text="Phone (with country code):").grid(row=1, column=0, sticky="w", pady=4)
        self.phone_entry = tk.Entry(frame, width=32)
        self.phone_entry.insert(0, contact["phone"] if contact else "+91")
        self.phone_entry.grid(row=1, column=1, pady=4)

        btn_frame = tk.Frame(self, pady=10)
        btn_frame.pack()
        ttk.Button(btn_frame, text="Save", command=self._on_save).pack(side="left", padx=6)
        ttk.Button(btn_frame, text="Cancel", command=self.destroy).pack(side="left", padx=6)

        self.update_idletasks()
        self.geometry(f"+{parent.winfo_rootx() + 80}+{parent.winfo_rooty() + 80}")
        self.wait_window(self)

    def _on_save(self):
        name = self.name_entry.get().strip()
        phone = self.phone_entry.get().strip()
        if not name or not phone:
            messagebox.showerror("Missing info", "Please enter both a name and a phone number.")
            return
        if not phone.startswith("+"):
            messagebox.showerror("Invalid phone", "Phone number should include the country code, e.g. +91XXXXXXXXXX.")
            return
        self.result = (name, phone)
        self.destroy()


class ContactsDialog(tk.Toplevel):
    """Manage the local contact list used for sending WhatsApp messages."""

    def __init__(self, parent, on_change):
        super().__init__(parent)
        self.title("Manage Contacts")
        self.geometry("380x360")
        self.transient(parent)
        self.grab_set()
        self.on_change = on_change

        columns = ("name", "phone")
        self.tree = ttk.Treeview(self, columns=columns, show="headings")
        self.tree.heading("name", text="Name")
        self.tree.heading("phone", text="Phone")
        self.tree.column("name", width=180)
        self.tree.column("phone", width=160)
        self.tree.pack(fill="both", expand=True, padx=8, pady=8)

        btn_frame = tk.Frame(self, pady=6)
        btn_frame.pack()
        ttk.Button(btn_frame, text="Add", command=self._on_add).pack(side="left", padx=4)
        ttk.Button(btn_frame, text="Edit", command=self._on_edit).pack(side="left", padx=4)
        ttk.Button(btn_frame, text="Delete", command=self._on_delete).pack(side="left", padx=4)
        ttk.Button(btn_frame, text="Import from File", command=self._on_import).pack(side="left", padx=4)
        ttk.Button(btn_frame, text="Close", command=self.destroy).pack(side="left", padx=4)

        self._refresh()

    def _refresh(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        for contact in db.get_all_contacts():
            self.tree.insert("", "end", iid=str(contact["id"]), values=(contact["name"], contact["phone"]))

    def _selected_id(self):
        sel = self.tree.selection()
        return int(sel[0]) if sel else None

    def _on_add(self):
        dialog = ContactFormDialog(self)
        if dialog.result:
            db.insert_contact(*dialog.result)
            self._refresh()
            self.on_change()

    def _on_edit(self):
        contact_id = self._selected_id()
        if contact_id is None:
            messagebox.showinfo("No selection", "Select a contact to edit.")
            return
        contact = next((c for c in db.get_all_contacts() if c["id"] == contact_id), None)
        dialog = ContactFormDialog(self, contact=contact)
        if dialog.result:
            db.update_contact(contact_id, *dialog.result)
            self._refresh()
            self.on_change()

    def _on_delete(self):
        contact_id = self._selected_id()
        if contact_id is None:
            messagebox.showinfo("No selection", "Select a contact to delete.")
            return
        if messagebox.askyesno("Confirm delete", "Delete this contact?"):
            db.delete_contact(contact_id)
            self._refresh()
            self.on_change()

    def _on_import(self):
        file_path = filedialog.askopenfilename(
            title="Select contacts file",
            filetypes=[("CSV / Excel files", "*.csv *.xlsx *.xlsm *.xls"), ("All files", "*.*")],
        )
        if not file_path:
            return
        try:
            contacts = file_import.read_contacts(file_path)
        except file_import.ImportError_ as exc:
            messagebox.showerror("Import failed", str(exc))
            return
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Import failed", f"Could not read the file:\n{exc}")
            return

        added, skipped = db.sync_contacts_bulk(contacts)
        self._refresh()
        self.on_change()
        messagebox.showinfo(
            "Import complete",
            f"{added} contact(s) added\n{skipped} already existed (skipped, same phone number)",
        )


class ProductsPanel(tk.LabelFrame):
    def __init__(self, parent, on_products_changed):
        super().__init__(parent, text="Products", padx=8, pady=8)
        self.on_products_changed = on_products_changed

        toolbar = tk.Frame(self)
        toolbar.pack(fill="x")
        ttk.Button(toolbar, text="Import CSV / Excel File", command=self._on_import).pack(side="left", padx=4)
        ttk.Button(toolbar, text="Download Sample File", command=self._on_download_sample).pack(side="left", padx=4)
        ttk.Button(toolbar, text="Delete Selected", command=self._on_delete_selected).pack(side="left", padx=4)
        ttk.Button(toolbar, text="Refresh", command=self.refresh).pack(side="left", padx=4)

        search_row = tk.Frame(self)
        search_row.pack(fill="x", pady=(6, 0))
        tk.Label(search_row, text="Search:").pack(side="left")
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *_args: self._apply_filter())
        tk.Entry(search_row, textvariable=self.search_var, width=30).pack(side="left", padx=6)

        hint = tk.Label(self, fg="gray30", text="Double-click a product to set its Description / Amazon Link for WhatsApp messages.")
        hint.pack(fill="x", pady=(4, 0))

        columns = ("name", "quantity", "description", "amazon_link")
        self.tree = ttk.Treeview(self, columns=columns, show="headings", height=8)
        self.tree.heading("name", text="Product Name")
        self.tree.heading("quantity", text="Quantity")
        self.tree.heading("description", text="Description")
        self.tree.heading("amazon_link", text="Amazon Link")
        self.tree.column("name", width=180, anchor="w")
        self.tree.column("quantity", width=80, anchor="center")
        self.tree.column("description", width=220, anchor="w")
        self.tree.column("amazon_link", width=200, anchor="w")
        self.tree.pack(fill="both", expand=True, pady=6)
        self.tree.bind("<Double-1>", self._on_edit_selected)

        self.status_var = tk.StringVar(value="Ready.")
        tk.Label(self, textvariable=self.status_var, anchor="w", fg="gray20").pack(fill="x")

        self.refresh()

    def refresh(self):
        self._all_products = db.get_all_products()
        self._apply_filter()

    def _apply_filter(self):
        query = self.search_var.get().strip().lower()
        for item in self.tree.get_children():
            self.tree.delete(item)
        for product in self._all_products:
            if query and query not in product["product_name"].lower():
                continue
            self.tree.insert(
                "", "end", iid=str(product["id"]),
                values=(product["product_name"], product["quantity"],
                        product.get("description") or "", product.get("amazon_link") or ""),
            )

    def _on_delete_selected(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("No selection", "Select a product to delete.")
            return
        product_id = int(sel[0])
        product = db.get_product_by_id(product_id)
        if not product:
            return
        if db.get_message_log_for_product(product_id):
            confirmed = messagebox.askyesno(
                "Delete product with send history",
                f"'{product['product_name']}' has WhatsApp messages already sent for it. "
                "Deleting it will also remove that send history. Continue?",
                icon="warning",
            )
        else:
            confirmed = messagebox.askyesno("Confirm delete", f"Delete '{product['product_name']}'?")
        if confirmed:
            db.delete_product(product_id)
            self.refresh()
            self.on_products_changed()

    def _on_download_sample(self):
        fmt = simpledialog.askstring(
            "Sample file format", "Type 'csv' or 'xlsx' for the sample file format:", initialvalue="xlsx"
        )
        if not fmt:
            return
        fmt = fmt.strip().lower()
        if fmt not in ("csv", "xlsx"):
            messagebox.showerror("Invalid format", "Please type 'csv' or 'xlsx'.")
            return

        default_name = f"sample_products.{fmt}"
        file_path = filedialog.asksaveasfilename(
            title="Save sample file",
            defaultextension=f".{fmt}",
            initialfile=default_name,
            filetypes=[(fmt.upper(), f"*.{fmt}")],
        )
        if not file_path:
            return

        try:
            if fmt == "csv":
                file_import.write_sample_csv(file_path)
            else:
                file_import.write_sample_xlsx(file_path)
            messagebox.showinfo("Sample saved", f"Sample file saved to:\n{file_path}")
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Could not save sample", str(exc))

    def _on_import(self):
        file_path = filedialog.askopenfilename(
            title="Select product file",
            filetypes=[("CSV / Excel files", "*.csv *.xlsx *.xlsm *.xls"), ("All files", "*.*")],
        )
        if not file_path:
            return

        try:
            products = file_import.read_products(file_path)
        except file_import.ImportError_ as exc:
            messagebox.showerror("Import failed", str(exc))
            return
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Import failed", f"Could not read the file:\n{exc}")
            return

        added, increased, skipped = 0, 0, 0
        for name, qty in products:
            existing = db.find_products_by_name(name)
            if not existing:
                db.insert_product(name, qty)
                added += 1
                continue

            target = existing[0]
            dialog = DuplicateDialog(self, name, target["quantity"], qty)
            if dialog.result == "increase":
                db.increase_quantity(target["id"], qty)
                increased += 1
            elif dialog.result == "new":
                db.insert_product(name, qty)
                added += 1
            else:
                skipped += 1

        self.refresh()
        self.on_products_changed()
        self.status_var.set(f"Import complete: {added} added, {increased} updated, {skipped} skipped.")
        messagebox.showinfo(
            "Import complete",
            f"{added} product(s) added\n{increased} product(s) updated\n{skipped} skipped",
        )

    def _on_edit_selected(self, _event):
        sel = self.tree.selection()
        if not sel:
            return
        product = db.get_product_by_id(int(sel[0]))
        if not product:
            return
        dialog = ProductEditDialog(self, product)
        if dialog.saved:
            self.refresh()
            self.on_products_changed()


class WhatsAppPanel(tk.LabelFrame):
    def __init__(self, parent, on_product_updated):
        super().__init__(parent, text="Send WhatsApp Message", padx=8, pady=8)
        self._work_queue = queue.Queue()
        self.on_product_updated = on_product_updated

        # -- Connection row --
        conn_row = tk.Frame(self)
        conn_row.pack(fill="x", pady=(0, 6))
        self.connect_status_var = tk.StringVar(value="Not connected")
        ttk.Button(conn_row, text="Connect WhatsApp", command=self._on_connect).pack(side="left", padx=(0, 8))
        self.sync_contacts_btn = ttk.Button(conn_row, text="Sync WhatsApp Contacts", command=self._on_sync_contacts)
        # Only shown once connected — packed in _poll_queue when the connect succeeds.
        tk.Label(conn_row, textvariable=self.connect_status_var, fg="gray20").pack(side="left")
        browser_name = "Safari" if whatsapp.IS_MAC else "Chrome"
        hint = (
            f"First time only: a {browser_name} window opens showing a WhatsApp QR code — "
            "scan it with your phone (WhatsApp > Linked Devices)."
        )
        if whatsapp.IS_MAC:
            hint += " " + whatsapp.SAFARI_SETUP_HINT
        else:
            hint += " Requires Google Chrome and, for the very first connect, internet access."
        tk.Label(self, fg="gray30", wraplength=560, justify="left", text=hint).pack(fill="x", pady=(0, 8))

        # -- Contact + Product selection --
        select_row = tk.Frame(self)
        select_row.pack(fill="x", pady=4)
        tk.Label(select_row, text="Contacts:").grid(row=0, column=0, sticky="nw")
        contact_list_frame = tk.Frame(select_row)
        contact_list_frame.grid(row=0, column=1, padx=6, sticky="w")
        self.contact_listbox = tk.Listbox(
            contact_list_frame, selectmode=tk.EXTENDED, exportselection=False, width=28, height=5,
        )
        contact_scroll = ttk.Scrollbar(contact_list_frame, orient="vertical", command=self.contact_listbox.yview)
        self.contact_listbox.configure(yscrollcommand=contact_scroll.set)
        self.contact_listbox.pack(side="left", fill="y")
        contact_scroll.pack(side="left", fill="y")
        tk.Label(select_row, fg="gray30", text="(ctrl/shift/cmd-click to select multiple)").grid(
            row=0, column=2, padx=6, sticky="nw"
        )
        ttk.Button(select_row, text="Manage Contacts", command=self._on_manage_contacts).grid(
            row=0, column=3, padx=6, sticky="n"
        )

        tk.Label(select_row, text="Product:").grid(row=1, column=0, sticky="w", pady=(6, 0))
        self.product_combo = ttk.Combobox(select_row, state="readonly", width=28)
        self.product_combo.grid(row=1, column=1, padx=6, pady=(6, 0), sticky="w")
        self.product_combo.bind("<<ComboboxSelected>>", lambda _e: self._on_product_selected())

        # -- Description / link --
        tk.Label(self, text="Description:").pack(anchor="w", pady=(8, 0))
        self.desc_text = tk.Text(self, width=60, height=4, wrap="word")
        self.desc_text.pack(fill="x")
        self.desc_text.bind("<KeyRelease>", lambda _e: self._update_preview())

        tk.Label(self, text="Amazon Link:").pack(anchor="w", pady=(6, 0))
        self.link_entry = tk.Entry(self, width=60)
        self.link_entry.pack(fill="x")
        self.link_entry.bind("<KeyRelease>", lambda _e: self._update_preview())

        tk.Label(self, text="Message preview:").pack(anchor="w", pady=(8, 0))
        self.preview_text = tk.Text(self, width=60, height=5, wrap="word", state="disabled", bg="#f4f4f4")
        self.preview_text.pack(fill="x")

        ttk.Button(self, text="Send WhatsApp Message", command=self._on_send).pack(pady=10)

        self.status_var = tk.StringVar(value="")
        tk.Label(self, textvariable=self.status_var, fg="gray20").pack(anchor="w")

        self._contacts = []
        self._products = []
        self._batch_in_progress = False
        self.refresh_contacts()
        self.refresh_products()

    # -- data refresh --
    def refresh_contacts(self):
        self._contacts = db.get_all_contacts()
        self.contact_listbox.delete(0, "end")
        for c in self._contacts:
            self.contact_listbox.insert("end", f"{c['name']} ({c['phone']})")

    def refresh_products(self):
        self._products = db.get_all_products()
        self.product_combo["values"] = [
            f"{p['product_name']} (Qty: {p['quantity']})" for p in self._products
        ]

    def _on_manage_contacts(self):
        ContactsDialog(self, on_change=self.refresh_contacts)

    def _on_product_selected(self):
        idx = self.product_combo.current()
        if idx < 0:
            return
        product = self._products[idx]
        self.desc_text.delete("1.0", "end")
        self.desc_text.insert("1.0", product.get("description") or "")
        self.link_entry.delete(0, "end")
        self.link_entry.insert(0, product.get("amazon_link") or "")
        self._update_preview()

    def _compose_message(self):
        p_idx = self.product_combo.current()
        product_name = self._products[p_idx]["product_name"] if p_idx >= 0 else ""
        description = self.desc_text.get("1.0", "end").strip()
        link = self.link_entry.get().strip()

        parts = []
        if product_name:
            parts.append(f"*{product_name}*")
        if description:
            parts.append(description)
        if link:
            parts.append(link)
        return "\n\n".join(parts)

    def _update_preview(self):
        message = self._compose_message()
        self.preview_text.configure(state="normal")
        self.preview_text.delete("1.0", "end")
        self.preview_text.insert("1.0", message)
        self.preview_text.configure(state="disabled")

    # -- connect --
    def _on_connect(self):
        browser_name = "Safari" if whatsapp.IS_MAC else "Chrome"
        self.connect_status_var.set(f"Connecting... scan the QR code in the {browser_name} window")
        threading.Thread(target=self._connect_worker, daemon=True).start()
        self.after(200, self._poll_queue)

    def _connect_worker(self):
        try:
            ok = whatsapp.session.connect()
            self._work_queue.put(("connect", ok, None))
        except Exception as exc:  # noqa: BLE001
            self._work_queue.put(("connect", False, str(exc)))

    def _poll_queue(self):
        try:
            kind, ok, payload = self._work_queue.get_nowait()
        except queue.Empty:
            self.after(200, self._poll_queue)
            return

        if kind == "connect":
            if ok:
                self.connect_status_var.set("Connected")
                self.sync_contacts_btn.pack(side="left", padx=(0, 8))
            else:
                self.connect_status_var.set("Not connected")
                messagebox.showerror("Connection failed", payload or "Could not connect to WhatsApp Web (timed out).")
        elif kind == "send_progress":
            name = payload
            self.status_var.set(f"Sent to {name}." if ok else f"Failed to send to {name}.")
            self.after(200, self._poll_queue)
        elif kind == "send_done":
            self._batch_in_progress = False
            result = payload
            self.refresh_products()
            self.on_product_updated()
            summary_parts = [f"Sent: {len(result['sent'])}"]
            if result["skipped_stock"]:
                summary_parts.append(f"skipped (out of stock): {len(result['skipped_stock'])}")
            if result["failed"]:
                summary_parts.append(f"failed: {len(result['failed'])}")
            self.status_var.set(", ".join(summary_parts))
            if result["failed"] or result["skipped_stock"]:
                details = []
                if result["failed"]:
                    details.append("Failed: " + ", ".join(result["failed"]))
                if result["skipped_stock"]:
                    details.append("Skipped (out of stock): " + ", ".join(result["skipped_stock"]))
                messagebox.showwarning("Send complete with issues", "\n".join(details))
            else:
                messagebox.showinfo("Send complete", f"Message sent to {len(result['sent'])} contact(s).")
        elif kind == "sync":
            self.sync_contacts_btn.config(state="normal")
            if ok:
                contacts = payload
                added, skipped = db.sync_contacts_bulk(contacts)
                self.refresh_contacts()
                self.status_var.set(
                    f"WhatsApp contact sync complete: {added} added, {skipped} already existed "
                    f"(of {len(contacts)} chats scanned)."
                )
                messagebox.showinfo(
                    "Sync complete",
                    f"Scanned {len(contacts)} chat contact(s) with a phone number.\n"
                    f"{added} added, {skipped} already existed.",
                )
            else:
                self.status_var.set("WhatsApp contact sync failed.")
                messagebox.showerror("Sync failed", payload or "Could not sync WhatsApp contacts.")

    # -- send --
    def _on_send(self):
        c_indices = self.contact_listbox.curselection()
        if not c_indices:
            messagebox.showinfo("No contact selected", "Please select at least one contact.")
            return
        p_idx = self.product_combo.current()
        if p_idx < 0:
            messagebox.showinfo("No product selected", "Please select a product.")
            return
        product = self._products[p_idx]
        if product["quantity"] <= 0:
            messagebox.showerror(
                "Out of stock",
                f"'{product['product_name']}' has 0 quantity remaining. Cannot send a WhatsApp message for it.",
            )
            return
        if not whatsapp.session.is_connected():
            messagebox.showinfo("Not connected", "Click 'Connect WhatsApp' first and scan the QR code.")
            return

        message = self._compose_message()
        if not message:
            messagebox.showinfo("Empty message", "Select a product or type a description first.")
            return

        contacts = [self._contacts[i] for i in c_indices]
        self._batch_in_progress = True
        self.status_var.set(f"Sending to {len(contacts)} contact(s)...")
        threading.Thread(
            target=self._send_batch_worker, args=(product["id"], contacts, message), daemon=True
        ).start()
        self.after(200, self._poll_queue)

    def _send_batch_worker(self, product_id, contacts, message):
        sent, failed, skipped_stock = [], [], []
        for contact in contacts:
            product = db.get_product_by_id(product_id)
            if not product or product["quantity"] <= 0:
                skipped_stock.append(contact["name"])
                self._work_queue.put(("send_progress", False, contact["name"]))
                continue
            try:
                whatsapp.session.send_message(contact["phone"], message, contact_name=contact["name"])
                db.decrement_quantity(product_id)
                db.log_message_sent(product_id, contact["name"], contact["phone"])
                sent.append(contact["name"])
                self._work_queue.put(("send_progress", True, contact["name"]))
            except Exception:  # noqa: BLE001
                failed.append(contact["name"])
                self._work_queue.put(("send_progress", False, contact["name"]))
        self._work_queue.put(
            ("send_done", True, {"sent": sent, "failed": failed, "skipped_stock": skipped_stock})
        )

    # -- sync contacts --
    def _on_sync_contacts(self):
        if not whatsapp.session.is_connected():
            messagebox.showinfo("Not connected", "Click 'Connect WhatsApp' first and scan the QR code.")
            return
        self.sync_contacts_btn.config(state="disabled")
        self.status_var.set("Syncing WhatsApp contacts from your chat list... this can take a while.")
        threading.Thread(target=self._sync_worker, daemon=True).start()
        self.after(200, self._poll_queue)

    def _sync_worker(self):
        try:
            contacts = whatsapp.session.sync_chat_contacts()
            self._work_queue.put(("sync", True, contacts))
        except Exception as exc:  # noqa: BLE001
            self._work_queue.put(("sync", False, str(exc)))


class ScrollableFrame(tk.Frame):
    """A frame whose content scrolls vertically once it's taller than the window.

    Needed because this app's content can end up taller than a laptop screen's
    usable height (especially on Windows, once the taskbar and display scaling
    eat into it) — without this, widgets near the bottom (like the Send button)
    are simply unreachable, with no scrollbar to get to them.
    """

    def __init__(self, parent):
        super().__init__(parent)
        canvas = tk.Canvas(self, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.inner = tk.Frame(canvas)
        inner_window = canvas.create_window((0, 0), window=self.inner, anchor="nw")

        self.inner.bind("<Configure>", lambda _e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(inner_window, width=e.width))

        def _on_mousewheel(event):
            delta = event.delta if event.delta else (120 if event.num == 4 else -120)
            canvas.yview_scroll(int(-1 * (delta / 120)), "units")

        canvas.bind_all("<MouseWheel>", _on_mousewheel)  # Windows / macOS
        canvas.bind_all("<Button-4>", _on_mousewheel)     # Linux scroll up
        canvas.bind_all("<Button-5>", _on_mousewheel)     # Linux scroll down


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Product Quantity Tracker")
        self.geometry("640x820")
        self.minsize(480, 400)

        db.init_db()

        scroll_area = ScrollableFrame(self)
        scroll_area.pack(fill="both", expand=True)
        content = scroll_area.inner

        self.products_panel = ProductsPanel(content, on_products_changed=self._on_products_changed)
        self.products_panel.pack(fill="both", expand=True, padx=10, pady=(10, 6))

        self.whatsapp_panel = WhatsAppPanel(content, on_product_updated=self._on_product_updated_from_whatsapp)
        self.whatsapp_panel.pack(fill="both", expand=False, padx=10, pady=(0, 10))

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _on_products_changed(self):
        self.whatsapp_panel.refresh_products()

    def _on_product_updated_from_whatsapp(self):
        self.products_panel.refresh()

    def _on_close(self):
        whatsapp.session.close()
        self.destroy()


def main():
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
