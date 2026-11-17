import { useEffect, useState } from "react";
import { api } from "./api.js";

const ROLES = { admin: "Администратор", resident: "Житель" };

export default function Profile({ token, user }) {
  const [users, setUsers] = useState([]);
  const [error, setError] = useState("");

  useEffect(() => {
    if (user.role !== "admin") return;
    api.users(token).then(setUsers).catch((e) => setError(e.message));
  }, [token, user.role]);

  return (
    <div className="layout">
      <section className="panel">
        <h2>Мой профиль</h2>
        <dl className="facts">
          <dt>ID</dt><dd>{user.id}</dd>
          <dt>Имя пользователя</dt><dd>{user.username}</dd>
          <dt>Email</dt><dd>{user.email}</dd>
          <dt>Роль</dt><dd>{ROLES[user.role] || user.role}</dd>
          <dt>Регистрация</dt><dd>{new Date(user.created_at).toLocaleDateString("ru-RU")}</dd>
        </dl>
      </section>
      <section className="panel">
        <h2>Пользователи</h2>
        {user.role !== "admin" ? (
          <p className="muted">Список пользователей доступен администратору.</p>
        ) : (
          <>
            {error && <p className="error" role="alert">{error}</p>}
            <ul className="issues">
              {users.map((u) => (
                <li key={u.id} className="issue s-new">
                  <div className="row">
                    <strong>{u.username}</strong>
                    <span className="badge">{ROLES[u.role] || u.role}</span>
                  </div>
                  <p className="muted">id {u.id}, с {new Date(u.created_at).toLocaleDateString("ru-RU")}</p>
                </li>
              ))}
            </ul>
          </>
        )}
      </section>
    </div>
  );
}
