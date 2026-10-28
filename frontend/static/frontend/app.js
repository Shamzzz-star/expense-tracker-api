"use strict";

// Single-page frontend for the Expense Tracker API. It runs on the same origin as the API,
// keeps the JWT pair in localStorage and builds every piece of user data with textContent.

const $ = (sel) => document.querySelector(sel);
const TOKEN_KEY = "expense-tracker.tokens";
const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
const money = new Intl.NumberFormat(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });

const state = {
  tokens: loadTokens(),
  categories: [],
  page: 1,
  editingExpense: null,
  editingCategory: null,
};

// ---------- helpers ----------

function el(tag, props = {}, ...children) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(props)) {
    if (key === "class") node.className = value;
    else if (key === "text") node.textContent = value;
    else if (key.startsWith("on")) node.addEventListener(key.slice(2), value);
    else node.setAttribute(key, value);
  }
  for (const child of children) {
    if (child != null) node.append(child);
  }
  return node;
}

function fmt(value) {
  return money.format(Number(value || 0));
}

function currentMonth() {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
}

function today() {
  const d = new Date();
  return `${currentMonth()}-${String(d.getDate()).padStart(2, "0")}`;
}

let toastTimer;
function toast(message) {
  const t = $("#toast");
  t.textContent = message;
  t.hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => (t.hidden = true), 2600);
}

function debounce(fn, ms) {
  let timer;
  return (...args) => {
    clearTimeout(timer);
    timer = setTimeout(() => fn(...args), ms);
  };
}

// ---------- tokens and API ----------

function loadTokens() {
  try {
    return JSON.parse(localStorage.getItem(TOKEN_KEY)) || null;
  } catch {
    return null;
  }
}

function saveTokens(tokens) {
  state.tokens = tokens;
  try {
    if (tokens) localStorage.setItem(TOKEN_KEY, JSON.stringify(tokens));
    else localStorage.removeItem(TOKEN_KEY);
  } catch {
    /* storage unavailable: stay signed in for this tab only */
  }
}

class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.status = status;
  }
}

function errorMessage(data, fallback) {
  if (!data || typeof data !== "object") return fallback;
  if (typeof data.detail === "string") return data.detail;
  const lines = [];
  for (const [field, messages] of Object.entries(data)) {
    const text = Array.isArray(messages) ? messages.join(" ") : String(messages);
    lines.push(field === "non_field_errors" ? text : `${field.replace(/_/g, " ")}: ${text}`);
  }
  return lines.join("\n") || fallback;
}

async function refreshAccess() {
  if (!state.tokens?.refresh) return false;
  const resp = await fetch("/api/auth/token/refresh/", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh: state.tokens.refresh }),
  });
  if (!resp.ok) return false;
  const data = await resp.json();
  saveTokens({ ...state.tokens, access: data.access, refresh: data.refresh || state.tokens.refresh });
  return true;
}

async function api(path, { method = "GET", body, raw = false } = {}) {
  const send = () => {
    const headers = {};
    if (state.tokens?.access) headers.Authorization = `Bearer ${state.tokens.access}`;
    if (body !== undefined) headers["Content-Type"] = "application/json";
    return fetch(path, { method, headers, body: body === undefined ? undefined : JSON.stringify(body) });
  };

  let resp = await send();
  if (resp.status === 401 && state.tokens) {
    if (await refreshAccess()) {
      resp = await send();
    } else {
      signOut("Your session expired. Please sign in again.");
      throw new ApiError("Session expired", 401);
    }
  }
  if (raw) {
    if (!resp.ok) throw new ApiError(`Request failed (${resp.status})`, resp.status);
    return resp;
  }
  const data = resp.status === 204 ? null : await resp.json().catch(() => null);
  if (!resp.ok) throw new ApiError(errorMessage(data, `Request failed (${resp.status})`), resp.status);
  return data;
}

// ---------- auth ----------

let authMode = "login";

function setAuthMode(mode) {
  authMode = mode;
  document.querySelectorAll(".tab").forEach((t) => t.classList.toggle("active", t.dataset.mode === mode));
  document.querySelectorAll(".register-only").forEach((n) => (n.hidden = mode !== "register"));
  $("#auth-submit").textContent = mode === "login" ? "Sign in" : "Create account";
  $("#auth-form").password.autocomplete = mode === "login" ? "current-password" : "new-password";
  $("#auth-error").textContent = "";
}

async function onAuthSubmit(event) {
  event.preventDefault();
  const form = event.target;
  const username = form.username.value.trim();
  const password = form.password.value;
  const errorBox = $("#auth-error");
  errorBox.textContent = "";
  if (!username || !password) {
    errorBox.textContent = "Enter a username and password.";
    return;
  }
  const submit = $("#auth-submit");
  submit.disabled = true;
  try {
    if (authMode === "register") {
      const payload = { username, password };
      if (form.email.value.trim()) payload.email = form.email.value.trim();
      await api("/api/auth/register/", { method: "POST", body: payload });
    }
    const tokens = await api("/api/auth/token/", { method: "POST", body: { username, password } });
    saveTokens(tokens);
    form.reset();
    await startApp();
  } catch (err) {
    errorBox.textContent = err.status === 401 ? "Wrong username or password." : err.message;
  } finally {
    submit.disabled = false;
  }
}

function signOut(message) {
  saveTokens(null);
  $("#app-view").hidden = true;
  $("#auth-view").hidden = false;
  setAuthMode("login");
  if (message) $("#auth-error").textContent = message;
}

// ---------- dashboard ----------

function selectedMonth() {
  return $("#month").value || currentMonth();
}

async function loadSummary() {
  const month = selectedMonth();
  const year = month.slice(0, 4);
  const [summary, trend] = await Promise.all([
    api(`/api/expenses/summary/?month=${month}`),
    api(`/api/expenses/trend/?year=${year}`),
  ]);

  const overCount = summary.by_category.filter((c) => c.over_budget).length;
  $("#stat-total").textContent = fmt(summary.total);
  $("#stat-count").textContent = summary.count;
  $("#stat-over").textContent = overCount;
  $("#stat-over").classList.toggle("bad", overCount > 0);
  $("#stat-year").textContent = fmt(trend.total);
  $("#budget-month").textContent = `${MONTHS[Number(month.slice(5)) - 1]} ${year}`;
  $("#trend-year").textContent = year;

  renderBudgets(summary);
  renderTrend(trend, month);
}

function renderBudgets(summary) {
  const box = $("#budgets");
  box.replaceChildren();

  // Spending rows from the summary, plus budgeted categories with nothing spent yet.
  const rows = summary.by_category.map((c) => ({ name: c.category, total: Number(c.total), budget: c.budget }));
  for (const cat of state.categories) {
    if (cat.monthly_budget != null && !summary.by_category.some((c) => c.category_id === cat.id)) {
      rows.push({ name: cat.name, total: 0, budget: cat.monthly_budget });
    }
  }
  if (!rows.length) {
    box.append(el("p", { class: "empty", text: "No spending this month yet." }));
    return;
  }

  for (const row of rows) {
    const budget = row.budget == null ? null : Number(row.budget);
    const ratio = budget ? row.total / budget : null;
    const meter = el("div", { class: "meter" }, el("span"));
    let detail;
    if (budget == null) {
      detail = el("span", { class: "amt", text: `${fmt(row.total)} · no budget` });
      meter.hidden = true;
    } else {
      meter.firstChild.style.width = `${Math.min(ratio, 1) * 100}%`;
      if (ratio > 1) meter.classList.add("over");
      else if (ratio >= 0.8) meter.classList.add("warn");
      detail = el(
        "span",
        { class: ratio > 1 ? "amt over-text" : "amt" },
        `${fmt(row.total)} / ${fmt(budget)}`,
        ratio > 1 ? ` · over by ${fmt(row.total - budget)}` : "",
      );
    }
    box.append(
      el("div", { class: "budget-row" }, el("div", { class: "budget-top" }, el("span", { text: row.name }), detail), meter),
    );
  }
}

function renderTrend(trend, month) {
  const ns = "http://www.w3.org/2000/svg";
  const svgEl = (tag, attrs) => {
    const node = document.createElementNS(ns, tag);
    for (const [k, v] of Object.entries(attrs)) node.setAttribute(k, v);
    return node;
  };
  const W = 600, H = 220, left = 46, bottom = 24, top = 10;
  const values = trend.months.map((m) => Number(m.total));
  const max = Math.max(...values, 1);
  const svg = svgEl("svg", { viewBox: `0 0 ${W} ${H}`, role: "img", "aria-label": `Spending per month in ${trend.year}` });

  for (let i = 0; i <= 2; i++) {
    const y = top + ((H - top - bottom) * i) / 2;
    svg.append(svgEl("line", { x1: left, x2: W, y1: y, y2: y, class: "grid" }));
    const label = svgEl("text", { x: left - 6, y: y + 4, "text-anchor": "end", class: "axis" });
    label.textContent = fmt((max * (2 - i)) / 2);
    svg.append(label);
  }

  const slot = (W - left) / 12;
  values.forEach((value, i) => {
    const h = ((H - top - bottom) * value) / max;
    const isCurrent = trend.months[i].month === month;
    const bar = svgEl("rect", {
      x: left + i * slot + slot * 0.18,
      y: H - bottom - h,
      width: slot * 0.64,
      height: Math.max(h, value > 0 ? 2 : 0),
      rx: 3,
      class: isCurrent ? "bar current" : "bar",
    });
    const title = svgEl("title", {});
    title.textContent = `${MONTHS[i]} ${trend.year}: ${fmt(value)}`;
    bar.append(title);
    svg.append(bar);
    const label = svgEl("text", { x: left + i * slot + slot / 2, y: H - 6, "text-anchor": "middle", class: "axis" });
    label.textContent = MONTHS[i];
    svg.append(label);
  });

  $("#trend").replaceChildren(svg);
}

// ---------- expenses ----------

function filterParams() {
  const params = new URLSearchParams();
  for (const [key, value] of new FormData($("#filters"))) {
    if (String(value).trim()) params.set(key, String(value).trim());
  }
  return params;
}

async function loadExpenses() {
  const params = filterParams();
  params.set("page", state.page);
  let data;
  try {
    data = await api(`/api/expenses/?${params}`);
  } catch (err) {
    // A filter change can leave us past the last page.
    if (err.status === 404 && state.page > 1) {
      state.page = 1;
      return loadExpenses();
    }
    throw err;
  }

  const body = $("#expense-rows");
  body.replaceChildren();
  if (!data.results.length) {
    body.append(el("tr", {}, el("td", { colspan: 5, class: "empty", text: "No expenses match." })));
  }
  for (const e of data.results) {
    body.append(
      el(
        "tr",
        {},
        el("td", { text: e.date }),
        el("td", { text: e.description || "—" }),
        el("td", {}, el("span", { class: e.category_name ? "chip" : "chip none", text: e.category_name || "Uncategorized" })),
        el("td", { class: "num", text: fmt(e.amount) }),
        el(
          "td",
          { class: "row-actions" },
          el("button", { class: "btn small ghost", type: "button", text: "Edit", onclick: () => openExpenseDialog(e) }),
          el("button", { class: "btn small ghost danger", type: "button", text: "Delete", onclick: () => deleteExpense(e) }),
        ),
      ),
    );
  }

  const pages = Math.max(1, Math.ceil(data.count / 20));
  $("#page-info").textContent = `${data.count} expense${data.count === 1 ? "" : "s"} · page ${state.page} of ${pages}`;
  $("#prev").disabled = !data.previous;
  $("#next").disabled = !data.next;
}

function openExpenseDialog(expense = null) {
  state.editingExpense = expense;
  const form = $("#expense-form");
  form.reset();
  form.querySelector(".error").textContent = "";
  $("#expense-title").textContent = expense ? "Edit expense" : "Add expense";
  form.amount.value = expense?.amount ?? "";
  form.date.value = expense?.date ?? today();
  form.category.value = expense?.category ?? "";
  form.description.value = expense?.description ?? "";
  $("#expense-dialog").showModal();
  form.amount.focus();
}

async function saveExpense(form) {
  const payload = {
    amount: form.amount.value,
    date: form.date.value,
    category: form.category.value ? Number(form.category.value) : null,
    description: form.description.value.trim(),
  };
  const editing = state.editingExpense;
  await api(editing ? `/api/expenses/${editing.id}/` : "/api/expenses/", {
    method: editing ? "PUT" : "POST",
    body: payload,
  });
  toast(editing ? "Expense updated" : "Expense added");
  await refreshData();
}

async function deleteExpense(expense) {
  if (!confirm(`Delete the ${fmt(expense.amount)} expense from ${expense.date}?`)) return;
  await api(`/api/expenses/${expense.id}/`, { method: "DELETE" });
  toast("Expense deleted");
  await refreshData();
}

async function exportCsv() {
  const params = filterParams();
  const resp = await api(`/api/expenses/export/?${params}`, { raw: true });
  const url = URL.createObjectURL(await resp.blob());
  const link = el("a", { href: url, download: `expenses-${today()}.csv` });
  document.body.append(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

// ---------- categories ----------

async function loadCategories() {
  // Categories are paginated like everything else; follow every page.
  let all = [];
  let url = "/api/categories/?ordering=name";
  while (url) {
    const data = await api(url);
    all = all.concat(data.results);
    url = data.next ? new URL(data.next).pathname + new URL(data.next).search : null;
  }
  state.categories = all;

  const list = $("#categories");
  list.replaceChildren();
  if (!all.length) list.append(el("li", { class: "empty", text: "No categories yet. Add one to organise your spending." }));
  for (const cat of all) {
    list.append(
      el(
        "li",
        {},
        el(
          "div",
          {},
          el("div", { class: "name", text: cat.name }),
          el("div", { class: "budget", text: cat.monthly_budget == null ? "No budget" : `Budget ${fmt(cat.monthly_budget)} / month` }),
        ),
        el(
          "div",
          {},
          el("button", { class: "btn small ghost", type: "button", text: "Edit", onclick: () => openCategoryDialog(cat) }),
          el("button", { class: "btn small ghost danger", type: "button", text: "Delete", onclick: () => deleteCategory(cat) }),
        ),
      ),
    );
  }

  for (const select of [$("#filters").category, $("#expense-form").category]) {
    const keep = select.value;
    select.replaceChildren(select.options[0]);
    for (const cat of all) select.append(el("option", { value: cat.id, text: cat.name }));
    select.value = all.some((c) => String(c.id) === keep) ? keep : "";
  }
}

function openCategoryDialog(category = null) {
  state.editingCategory = category;
  const form = $("#category-form");
  form.reset();
  form.querySelector(".error").textContent = "";
  $("#category-title").textContent = category ? "Edit category" : "Add category";
  form.name.value = category?.name ?? "";
  form.monthly_budget.value = category?.monthly_budget ?? "";
  $("#category-dialog").showModal();
  form.name.focus();
}

async function saveCategory(form) {
  const payload = {
    name: form.name.value.trim(),
    monthly_budget: form.monthly_budget.value === "" ? null : form.monthly_budget.value,
  };
  const editing = state.editingCategory;
  await api(editing ? `/api/categories/${editing.id}/` : "/api/categories/", {
    method: editing ? "PUT" : "POST",
    body: payload,
  });
  toast(editing ? "Category updated" : "Category added");
  await refreshData();
}

async function deleteCategory(category) {
  if (!confirm(`Delete "${category.name}"? Its expenses will become uncategorized.`)) return;
  await api(`/api/categories/${category.id}/`, { method: "DELETE" });
  toast("Category deleted");
  await refreshData();
}

// ---------- wiring ----------

async function refreshData() {
  await loadCategories();
  await Promise.all([loadSummary(), loadExpenses()]);
}

function bindDialog(dialogSel, formSel, save) {
  const dialog = $(dialogSel);
  const form = $(formSel);
  form.addEventListener("submit", async (event) => {
    if (event.submitter?.value === "cancel") return; // let the dialog close
    event.preventDefault();
    const errorBox = form.querySelector(".error");
    errorBox.textContent = "";
    if (!form.checkValidity()) {
      errorBox.textContent = "Please fill in the required fields with valid values.";
      return;
    }
    try {
      await save(form);
      dialog.close();
    } catch (err) {
      errorBox.textContent = err.message;
    }
  });
}

function reportErrors(fn) {
  return async (...args) => {
    try {
      await fn(...args);
    } catch (err) {
      if (err.status !== 401) toast(err.message);
    }
  };
}

async function startApp() {
  $("#auth-view").hidden = true;
  $("#app-view").hidden = false;
  if (!$("#month").value) $("#month").value = currentMonth();
  try {
    const me = await api("/api/auth/me/");
    $("#username").textContent = me.username;
    state.page = 1;
    await refreshData();
  } catch (err) {
    if (err.status !== 401) toast(err.message);
  }
}

document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll(".tab").forEach((t) => t.addEventListener("click", () => setAuthMode(t.dataset.mode)));
  $("#auth-form").addEventListener("submit", onAuthSubmit);
  $("#logout").addEventListener("click", () => signOut());

  $("#month").addEventListener("change", reportErrors(loadSummary));
  $("#add-expense").addEventListener("click", () => openExpenseDialog());
  $("#add-category").addEventListener("click", () => openCategoryDialog());
  $("#export").addEventListener("click", reportErrors(exportCsv));

  const reloadList = reportErrors(() => {
    state.page = 1;
    return loadExpenses();
  });
  const filters = $("#filters");
  filters.addEventListener("input", debounce(reloadList, 300));
  filters.addEventListener("reset", () => setTimeout(reloadList));
  filters.addEventListener("submit", (e) => e.preventDefault());

  $("#prev").addEventListener("click", reportErrors(() => (state.page--, loadExpenses())));
  $("#next").addEventListener("click", reportErrors(() => (state.page++, loadExpenses())));

  bindDialog("#expense-dialog", "#expense-form", saveExpense);
  bindDialog("#category-dialog", "#category-form", saveCategory);

  if (state.tokens) startApp();
  else signOut();
});
