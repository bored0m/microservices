import { useCallback, useEffect, useState } from "react";
import { api } from "./api.js";

const SOURCES = {
  utility: "Заявки ЖКХ",
  billing: "Счета и оплата",
  transport: "Транспорт",
  environment: "Экология",
};
const STATUS = { queued: "В очереди", sent: "Доставлено", failed: "Ошибка доставки" };

export default function Notifications({ token, user }) {
  const isAdmin = user.role === "admin";
  const [items, setItems] = useState([]);
  const [viewUser, setViewUser] = useState(user.id);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    try {
      setItems(await api.notifications(token, viewUser !== user.id ? viewUser : undefined));
      setError("");
    } catch (err) {
      setError(err.message);
    }
  }, [token, viewUser, user.id]);

  useEffect(() => { load(); }, [load]);

  return (
    <div className="page">
      <section className="panel">
        <div className="row">
          <h2>{viewUser === user.id ? "Мои уведомления" : `Уведомления пользователя id ${viewUser}`}</h2>
          <button className="secondary" onClick={load}>Обновить</button>
        </div>
        {isAdmin && (
          <label>Показать уведомления пользователя (id)
            <input type="number" min="1" value={viewUser} onChange={(e) => setViewUser(Number(e.target.value) || user.id)} />
          </label>
        )}
        {error && <p className="error" role="alert">{error}</p>}
        {items.length === 0 && <p className="muted">Уведомлений пока нет.</p>}
        <ul className="issues">
          {items.map((n) => (
            <li key={n.id} className={`issue ${n.status === "failed" ? "s-alert" : n.source_service === "environment" ? "s-in_progress" : "s-new"}`}>
              <div className="row">
                <strong>{n.title || "Уведомление"}</strong>
                <span className="badge">{STATUS[n.status] || n.status}</span>
              </div>
              <p>{n.message}</p>
              <p className="muted">
                {SOURCES[n.source_service] || n.source_service}, {new Date(n.created_at).toLocaleString("ru-RU", { dateStyle: "short", timeStyle: "short" })}
              </p>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
