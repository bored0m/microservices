import { useCallback, useEffect, useState } from "react";
import { api } from "./api.js";

const TYPES = {
  air_quality: "Качество воздуха",
  noise: "Шум",
  temperature: "Температура",
  water_quality: "Качество воды",
  radiation: "Радиация",
};
const STATUS = { active: "Работает", maintenance: "На обслуживании", offline: "Не на связи" };
const DEFAULT_UNITS = { air_quality: "µg/m³", noise: "дБ", temperature: "°C", water_quality: "pH", radiation: "µSv/h" };
const num = (v) => Number(v).toLocaleString("ru-RU", { maximumFractionDigits: 2 });
const when = (iso) => new Date(iso).toLocaleString("ru-RU", { dateStyle: "short", timeStyle: "short" });
const exceeded = (s) => s.threshold != null && s.latest_value != null && Number(s.latest_value) > Number(s.threshold);

function ReadingForm({ token, sensors, onAdded }) {
  const [form, setForm] = useState({ sensor: "", value: "" });
  const [error, setError] = useState("");
  const [done, setDone] = useState("");
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  async function submit(e) {
    e.preventDefault();
    setError(""); setDone("");
    try {
      await api.addSensorData(token, { sensor_id: form.sensor, value: form.value });
      const s = sensors.find((x) => x.id === form.sensor);
      const over = s?.threshold != null && Number(form.value) > Number(s.threshold);
      setDone(over ? "Показание принято. Порог превышен — администраторам отправлено оповещение." : "Показание принято.");
      setForm({ ...form, value: "" });
      onAdded();
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <form onSubmit={submit} className="panel stack">
      <h2>Передать показание</h2>
      <label>Датчик
        <select required value={form.sensor} onChange={set("sensor")}>
          <option value="">Выберите…</option>
          {sensors.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
        </select>
      </label>
      <label>Значение<input type="number" step="any" required value={form.value} onChange={set("value")} /></label>
      {error && <p className="error" role="alert">{error}</p>}
      {done && <p className="ok-text" role="status">{done}</p>}
      <button>Отправить</button>
    </form>
  );
}

function SensorForm({ token, onCreated }) {
  const empty = { name: "", sensor_type: "air_quality", location: "", unit: "", status: "active" };
  const [form, setForm] = useState(empty);
  const [error, setError] = useState("");
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  async function submit(e) {
    e.preventDefault();
    setError("");
    try {
      await api.createSensor(token, { ...form, unit: form.unit.trim() || null });
      setForm(empty);
      onCreated();
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <form onSubmit={submit} className="panel stack">
      <h2>Добавить датчик</h2>
      <label>Название<input required minLength={2} value={form.name} onChange={set("name")} /></label>
      <label>Тип
        <select value={form.sensor_type} onChange={set("sensor_type")}>
          {Object.entries(TYPES).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
        </select>
      </label>
      <label>Место установки<input required minLength={2} value={form.location} onChange={set("location")} /></label>
      <label>Единица измерения
        <input placeholder={DEFAULT_UNITS[form.sensor_type]} value={form.unit} onChange={set("unit")} />
      </label>
      <label>Статус
        <select value={form.status} onChange={set("status")}>
          {Object.entries(STATUS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
        </select>
      </label>
      {error && <p className="error" role="alert">{error}</p>}
      <button>Добавить</button>
    </form>
  );
}

export default function Environment({ token, user }) {
  const [sensors, setSensors] = useState([]);
  const [open, setOpen] = useState(null);
  const [history, setHistory] = useState([]);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    try {
      setSensors(await api.sensors(token));
      setError("");
    } catch (err) {
      setError(err.message);
    }
  }, [token]);

  useEffect(() => { load(); }, [load]);

  useEffect(() => {
    if (!open) return;
    api.sensorData(token, open, 8).then(setHistory).catch(() => setHistory([]));
  }, [token, open, sensors]);

  async function run(action) {
    setError("");
    try {
      await action();
      load();
    } catch (err) {
      setError(err.message);
    }
  }
  const remove = (s) =>
    window.confirm(`Удалить датчик «${s.name}» вместе с историей показаний?`) &&
    run(async () => {
      await api.deleteSensor(token, s.id);
      if (open === s.id) setOpen(null);
    });

  return (
    <div className="layout">
      {user.role === "admin" ? (
        <div className="stack">
          <SensorForm token={token} onCreated={load} />
          <ReadingForm token={token} sensors={sensors} onAdded={load} />
        </div>
      ) : (
        <section className="panel">
          <h2>Показания датчиков</h2>
          <p className="muted">Новые показания передаёт администратор. При превышении порога ему приходит уведомление.</p>
        </section>
      )}
      <section className="panel">
        <div className="row"><h2>Датчики</h2><button className="secondary" onClick={load}>Обновить</button></div>
        {error && <p className="error" role="alert">{error}</p>}
        {sensors.length === 0 && (
          <p className="muted">{user.role === "admin" ? "Датчиков пока нет. Добавьте первый в форме слева." : "Датчики пока не добавлены."}</p>
        )}
        <ul className="issues">
          {sensors.map((s) => (
            <li key={s.id} className={`issue ${exceeded(s) ? "s-alert" : "s-resolved"}`}>
              <div className="row">
                <strong>{s.name}</strong>
                <span className="badge">
                  {s.latest_value != null ? `${num(s.latest_value)} ${s.unit || ""}` : "нет данных"}
                  {exceeded(s) && " — выше нормы"}
                </span>
              </div>
              <p className="muted">
                {TYPES[s.sensor_type] || s.sensor_type}, {s.location}
                {s.threshold != null && <>, порог {num(s.threshold)}</>}
                {s.latest_at && <>, обновлено {when(s.latest_at)}</>}
              </p>
              <div className="row start">
                <button className="link" onClick={() => setOpen(open === s.id ? null : s.id)}>
                  {open === s.id ? "Скрыть историю" : "История показаний"}
                </button>
                {user.role === "admin" && (
                  <>
                    <select aria-label="Статус датчика" value={s.status}
                      onChange={(ev) => run(() => api.setSensorStatus(token, s.id, ev.target.value))}>
                      {Object.entries(STATUS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
                    </select>
                    <button className="secondary danger" onClick={() => remove(s)}>Удалить</button>
                  </>
                )}
              </div>
              {open === s.id && (
                <ul className="history">
                  {history.length === 0 && <li className="muted">Показаний нет.</li>}
                  {history.map((h) => <li key={h.id}>{when(h.recorded_at)} — <strong>{num(h.value)} {s.unit}</strong></li>)}
                </ul>
              )}
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
