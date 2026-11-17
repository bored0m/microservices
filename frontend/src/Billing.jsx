import { useCallback, useEffect, useState } from "react";
import { api } from "./api.js";

const INVOICE_STATUS = { pending: "Ожидает оплаты", paid: "Оплачен", overdue: "Просрочен", cancelled: "Отменён" };
const METHODS = { card: "Банковская карта", bank_transfer: "Банковский перевод", wallet: "Электронный кошелёк" };

function InvoiceForm({ token, onCreated }) {
  const [users, setUsers] = useState([]);
  const empty = { userId: "", amount: "", description: "", due_date: "" };
  const [form, setForm] = useState(empty);
  const [error, setError] = useState("");
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  useEffect(() => { api.users(token).then(setUsers).catch(() => {}); }, [token]);

  async function submit(e) {
    e.preventDefault();
    setError("");
    const userId = Number(form.userId);
    try {
      try {
        await api.createAccount(token, userId);
      } catch (err) {
        if (err.status !== 409) throw err; // счёт уже есть — это нормально
      }
      await api.createInvoice(token, userId, {
        amount: Number(form.amount),
        description: form.description,
        due_date: form.due_date,
      });
      setForm(empty);
      onCreated(userId);
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <form onSubmit={submit} className="panel stack">
      <h2>Выставить счёт</h2>
      <label>Жилец
        <select required value={form.userId} onChange={set("userId")}>
          <option value="">Выберите…</option>
          {users.map((u) => <option key={u.id} value={u.id}>{u.username} (id {u.id})</option>)}
        </select>
      </label>
      <label>Сумма, ₽<input type="number" required min="1" step="0.01" value={form.amount} onChange={set("amount")} /></label>
      <label>За что<input required value={form.description} onChange={set("description")} /></label>
      <label>Оплатить до<input type="date" required value={form.due_date} onChange={set("due_date")} /></label>
      {error && <p className="error" role="alert">{error}</p>}
      <button>Выставить</button>
    </form>
  );
}

export default function Billing({ token, user }) {
  const isAdmin = user.role === "admin";
  const [viewUser, setViewUser] = useState(user.id);
  const [invoices, setInvoices] = useState([]);
  const [method, setMethod] = useState("card");
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setError("");
    try {
      setInvoices(await api.invoices(token, viewUser));
    } catch (err) {
      if (err.status === 404) setInvoices([]); // лицевого счёта ещё нет
      else setError(err.message);
    }
  }, [token, viewUser]);

  useEffect(() => { load(); }, [load]);

  async function pay(id) {
    setError("");
    try {
      await api.pay(token, id, method);
      load();
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <div className="layout">
      {isAdmin ? <InvoiceForm token={token} onCreated={(id) => { setViewUser(id); load(); }} /> : <section className="panel"><h2>Оплата</h2>
        <label>Способ оплаты
          <select value={method} onChange={(e) => setMethod(e.target.value)}>
            {Object.entries(METHODS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
          </select>
        </label></section>}
      <section className="panel">
        <h2>{isAdmin ? `Счета пользователя id ${viewUser}` : "Мои счета"}</h2>
        {isAdmin && (
          <label>Показать счета пользователя (id)
            <input type="number" min="1" value={viewUser} onChange={(e) => setViewUser(Number(e.target.value) || user.id)} />
          </label>
        )}
        {error && <p className="error" role="alert">{error}</p>}
        {invoices.length === 0 && <p className="muted">Счетов пока нет.</p>}
        <ul className="issues">
          {invoices.map((i) => (
            <li key={i.id} className={`issue s-${i.status === "paid" ? "resolved" : i.status === "pending" ? "in_progress" : "rejected"}`}>
              <div className="row">
                <strong>{i.description || "Счёт"} — {Number(i.amount).toLocaleString("ru-RU")} {i.currency}</strong>
                <span className="badge">{INVOICE_STATUS[i.status]}</span>
              </div>
              <p className="muted">Оплатить до {new Date(i.due_date).toLocaleDateString("ru-RU")}</p>
              {i.status === "pending" && !isAdmin && <button onClick={() => pay(i.id)}>Оплатить</button>}
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
