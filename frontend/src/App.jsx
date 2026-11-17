import { useCallback, useEffect, useState } from "react";
import { api } from "./api.js";
import Billing from "./Billing.jsx";
import Environment from "./Environment.jsx";
import Notifications from "./Notifications.jsx";
import Overview from "./Overview.jsx";
import Profile from "./Profile.jsx";
import Transport from "./Transport.jsx";

// Вкладки = страницы микросервисов. Адрес вида /#transport открывает нужную страницу сразу.
const TABS = [
  { id: "overview", label: "Сервисы" },
  { id: "profile", label: "Профиль" },
  { id: "issues", label: "Заявки ЖКХ" },
  { id: "billing", label: "Счета и оплата" },
  { id: "transport", label: "Транспорт" },
  { id: "environment", label: "Экология" },
  { id: "notifications", label: "Уведомления" },
];
const tabFromHash = () => {
  const id = window.location.hash.slice(1);
  return TABS.some((t) => t.id === id) ? id : "overview";
};

export const STATUSES = {
  new: "Новая",
  in_progress: "В работе",
  resolved: "Решена",
  rejected: "Отклонена",
};
export const CATEGORIES = {
  water: "Водоснабжение",
  heating: "Отопление",
  electricity: "Электричество",
  elevator: "Лифт",
  cleaning: "Уборка",
  other: "Другое",
};

function AuthForm({ onToken }) {
  const [mode, setMode] = useState("login");
  const [form, setForm] = useState({ email: "", username: "", password: "" });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  async function submit(e) {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      if (mode === "register") await api.register(form);
      const { access_token } = await api.login({ email: form.email, password: form.password });
      onToken(access_token);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="auth">
      <h1>Заявки ЖКХ</h1>
      <p className="muted">Сообщите о проблеме в доме и следите, как её решают.</p>
      <form onSubmit={submit} className="stack">
        <label>Email<input type="email" required value={form.email} onChange={set("email")} /></label>
        {mode === "register" && (
          <label>Имя пользователя<input required minLength={3} value={form.username} onChange={set("username")} /></label>
        )}
        <label>Пароль<input type="password" required minLength={8} value={form.password} onChange={set("password")} /></label>
        {error && <p className="error" role="alert">{error}</p>}
        <button disabled={busy}>{mode === "login" ? "Войти" : "Создать аккаунт"}</button>
      </form>
      <button className="link" onClick={() => { setMode(mode === "login" ? "register" : "login"); setError(""); }}>
        {mode === "login" ? "Нет аккаунта? Зарегистрируйтесь" : "Уже есть аккаунт? Войдите"}
      </button>
    </main>
  );
}

function IssueForm({ token, onCreated }) {
  const empty = { title: "", description: "", category: "other", address: "" };
  const [form, setForm] = useState(empty);
  const [error, setError] = useState("");
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  async function submit(e) {
    e.preventDefault();
    setError("");
    try {
      await api.createIssue(token, form);
      setForm(empty);
      onCreated();
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <form onSubmit={submit} className="panel stack">
      <h2>Новая заявка</h2>
      <label>Что случилось<input required minLength={3} value={form.title} onChange={set("title")} /></label>
      <label>Адрес<input required minLength={3} value={form.address} onChange={set("address")} /></label>
      <label>Категория
        <select value={form.category} onChange={set("category")}>
          {Object.entries(CATEGORIES).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
        </select>
      </label>
      <label>Подробности<textarea required minLength={5} rows={4} value={form.description} onChange={set("description")} /></label>
      {error && <p className="error" role="alert">{error}</p>}
      <button>Отправить заявку</button>
    </form>
  );
}

function IssueList({ token, user, issues, onChanged, filter, setFilter }) {
  const [error, setError] = useState("");
  async function change(id, status) {
    setError("");
    try {
      await api.setStatus(token, id, status);
      onChanged();
    } catch (err) {
      setError(err.message);
    }
  }
  return (
    <section className="panel">
      <div className="row">
        <h2>{user.role === "admin" ? "Все заявки" : "Мои заявки"}</h2>
        <select aria-label="Фильтр по статусу" value={filter} onChange={(e) => setFilter(e.target.value)}>
          <option value="">Все статусы</option>
          {Object.entries(STATUSES).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
        </select>
      </div>
      {error && <p className="error" role="alert">{error}</p>}
      {issues.length === 0 && <p className="muted">Заявок пока нет. Создайте первую в форме слева.</p>}
      <ul className="issues">
        {issues.map((i) => (
          <li key={i.id} className={`issue s-${i.status}`}>
            <div className="row">
              <strong>{i.title}</strong>
              {user.role === "admin" ? (
                <select value={i.status} onChange={(e) => change(i.id, e.target.value)} aria-label="Статус заявки">
                  {Object.entries(STATUSES).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
                </select>
              ) : (
                <span className="badge">{STATUSES[i.status]}</span>
              )}
            </div>
            <p>{i.description}</p>
            <p className="muted">
              {CATEGORIES[i.category]}, {i.address}
              {user.role === "admin" && <>, автор: {i.author_username}</>}
              , {new Date(i.created_at).toLocaleDateString("ru-RU")}
            </p>
          </li>
        ))}
      </ul>
    </section>
  );
}

export default function App() {
  const [token, setToken] = useState(() => localStorage.getItem("token"));
  const [user, setUser] = useState(null);
  const [issues, setIssues] = useState([]);
  const [filter, setFilter] = useState("");
  const [tab, setTabState] = useState(tabFromHash);

  const setTab = useCallback((id) => {
    window.location.hash = id;
    setTabState(id);
  }, []);

  useEffect(() => {
    const onHash = () => setTabState(tabFromHash());
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem("token");
    setToken(null);
    setUser(null);
  }, []);

  const login = (t) => { localStorage.setItem("token", t); setToken(t); };

  const load = useCallback(async () => {
    if (!token) return;
    try {
      setIssues(await api.issues(token, filter));
    } catch (err) {
      if (err.status === 401) logout();
    }
  }, [token, filter, logout]);

  useEffect(() => {
    if (!token) return;
    api.me(token).then(setUser).catch(logout);
  }, [token, logout]);

  useEffect(() => { load(); }, [load]);

  if (!token) return <AuthForm onToken={login} />;
  if (!user) return <p className="muted center">Загрузка…</p>;

  return (
    <>
      <header className="top">
        <strong>Умный город</strong>
        <span>
          {user.username}{user.role === "admin" && " (администратор)"}
          <button className="link" onClick={logout}>Выйти</button>
        </span>
      </header>
      <nav className="tabs" aria-label="Сервисы">
        {TABS.map((t) => (
          <button key={t.id} className={tab === t.id ? "active" : ""} onClick={() => setTab(t.id)}>
            {t.label}
          </button>
        ))}
      </nav>
      {tab === "overview" && <Overview onOpen={setTab} />}
      {tab === "profile" && <Profile token={token} user={user} />}
      {tab === "issues" && (
        <div className="layout">
          <IssueForm token={token} onCreated={load} />
          <IssueList token={token} user={user} issues={issues} onChanged={load} filter={filter} setFilter={setFilter} />
        </div>
      )}
      {tab === "billing" && <Billing token={token} user={user} />}
      {tab === "transport" && <Transport token={token} user={user} />}
      {tab === "environment" && <Environment token={token} user={user} />}
      {tab === "notifications" && <Notifications token={token} user={user} />}
    </>
  );
}
