import { useCallback, useEffect, useState } from "react";
import { api } from "./api.js";

const VEHICLE_TYPES = { bus: "Автобус", tram: "Трамвай", shuttle: "Шаттл", municipal_car: "Служебный авто" };
const VEHICLE_STATUS = { active: "На линии", idle: "Простаивает", maintenance: "На обслуживании", offline: "Не на связи" };
const RES_STATUS = { active: "Активна", cancelled: "Отменена" };
const vehicleClass = { active: "resolved", idle: "in_progress", maintenance: "in_progress", offline: "rejected" };

// значение для <input type="datetime-local"> в локальном времени
function localInput(date) {
  const d = new Date(date.getTime() - date.getTimezoneOffset() * 60000);
  return d.toISOString().slice(0, 16);
}
const fmt = (iso) => new Date(iso).toLocaleString("ru-RU", { dateStyle: "short", timeStyle: "short" });

function ReserveForm({ token, lots, onReserved }) {
  const hour = 3600000;
  const [form, setForm] = useState({
    parking: "",
    start: localInput(new Date(Date.now() + hour)),
    end: localInput(new Date(Date.now() + 3 * hour)),
  });
  const [error, setError] = useState("");
  const [done, setDone] = useState("");
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  async function submit(e) {
    e.preventDefault();
    setError(""); setDone("");
    try {
      await api.reserve(token, form.parking, {
        start_time: new Date(form.start).toISOString(),
        end_time: new Date(form.end).toISOString(),
      });
      setDone("Место забронировано. Подтверждение придёт в «Уведомления».");
      onReserved();
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <form onSubmit={submit} className="panel stack">
      <h2>Забронировать парковку</h2>
      <label>Парковка
        <select required value={form.parking} onChange={set("parking")}>
          <option value="">Выберите…</option>
          {lots.map((l) => (
            <option key={l.id} value={l.id} disabled={l.available_spaces <= 0}>
              {l.name} — свободно {l.available_spaces}
            </option>
          ))}
        </select>
      </label>
      <label>С<input type="datetime-local" required value={form.start} onChange={set("start")} /></label>
      <label>До<input type="datetime-local" required value={form.end} onChange={set("end")} /></label>
      {error && <p className="error" role="alert">{error}</p>}
      {done && <p className="ok-text" role="status">{done}</p>}
      <button>Забронировать</button>
    </form>
  );
}

function VehicleForm({ token, onCreated }) {
  const empty = { plate_number: "", vehicle_type: "bus", model: "", status: "active" };
  const [form, setForm] = useState(empty);
  const [error, setError] = useState("");
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  async function submit(e) {
    e.preventDefault();
    setError("");
    try {
      await api.createVehicle(token, { ...form, model: form.model.trim() || null });
      setForm(empty);
      onCreated();
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <form onSubmit={submit} className="panel stack">
      <h2>Добавить транспорт</h2>
      <label>Госномер<input required minLength={2} value={form.plate_number} onChange={set("plate_number")} /></label>
      <label>Тип
        <select value={form.vehicle_type} onChange={set("vehicle_type")}>
          {Object.entries(VEHICLE_TYPES).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
        </select>
      </label>
      <label>Модель<input value={form.model} onChange={set("model")} /></label>
      <label>Статус
        <select value={form.status} onChange={set("status")}>
          {Object.entries(VEHICLE_STATUS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
        </select>
      </label>
      {error && <p className="error" role="alert">{error}</p>}
      <button>Добавить</button>
    </form>
  );
}

function ParkingForm({ token, onCreated }) {
  const empty = { name: "", address: "", total_spaces: "" };
  const [form, setForm] = useState(empty);
  const [error, setError] = useState("");
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  async function submit(e) {
    e.preventDefault();
    setError("");
    try {
      await api.createParking(token, { ...form, total_spaces: Number(form.total_spaces) });
      setForm(empty);
      onCreated();
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <form onSubmit={submit} className="panel stack">
      <h2>Добавить парковку</h2>
      <label>Название<input required minLength={2} value={form.name} onChange={set("name")} /></label>
      <label>Адрес<input required minLength={2} value={form.address} onChange={set("address")} /></label>
      <label>Всего мест<input type="number" required min="1" step="1" value={form.total_spaces} onChange={set("total_spaces")} /></label>
      {error && <p className="error" role="alert">{error}</p>}
      <button>Добавить</button>
    </form>
  );
}

export default function Transport({ token, user }) {
  const isAdmin = user.role === "admin";
  const [vehicles, setVehicles] = useState([]);
  const [lots, setLots] = useState([]);
  const [reservations, setReservations] = useState([]);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    try {
      const [v, l, r] = await Promise.all([api.vehicles(token), api.parking(token), api.reservations(token)]);
      setVehicles(v); setLots(l); setReservations(r);
      setError("");
    } catch (err) {
      setError(err.message);
    }
  }, [token]);

  useEffect(() => { load(); }, [load]);

  async function cancel(id) {
    setError("");
    try {
      await api.cancelReservation(token, id);
      load();
    } catch (err) {
      setError(err.message);
    }
  }

  async function run(action) {
    setError("");
    try {
      await action();
      load();
    } catch (err) {
      setError(err.message);
    }
  }
  const removeLot = (l) =>
    window.confirm(`Удалить парковку «${l.name}»?`) && run(() => api.deleteParking(token, l.id));
  const removeVehicle = (v) =>
    window.confirm(`Удалить транспорт ${v.plate_number}?`) && run(() => api.deleteVehicle(token, v.id));

  const lotName = (id) => lots.find((l) => l.id === id)?.name || "Парковка";

  return (
    <div className="layout">
      <div className="stack">
        <ReserveForm token={token} lots={lots} onReserved={load} />
        {isAdmin && <ParkingForm token={token} onCreated={load} />}
        {isAdmin && <VehicleForm token={token} onCreated={load} />}
      </div>
      <div className="stack">
        {error && <p className="error panel" role="alert">{error}</p>}

        <section className="panel">
          <h2>Парковки</h2>
          {lots.length === 0 && (
            <p className="muted">{isAdmin ? "Парковок пока нет. Добавьте первую в форме слева." : "Парковок пока нет."}</p>
          )}
          <ul className="issues">
            {lots.map((l) => (
              <li key={l.id} className={`issue ${l.available_spaces > 0 ? "s-resolved" : "s-alert"}`}>
                <div className="row">
                  <strong>{l.name}</strong>
                  <span className="badge">свободно {l.available_spaces} из {l.total_spaces}</span>
                </div>
                <p className="muted">{l.address}</p>
                {isAdmin && <button className="secondary danger" onClick={() => removeLot(l)}>Удалить</button>}
              </li>
            ))}
          </ul>
        </section>

        <section className="panel">
          <h2>{user.role === "admin" ? "Все брони" : "Мои брони"}</h2>
          {reservations.length === 0 && <p className="muted">Броней пока нет.</p>}
          <ul className="issues">
            {reservations.map((r) => (
              <li key={r.id} className={`issue ${r.status === "active" ? "s-new" : "s-rejected"}`}>
                <div className="row">
                  <strong>{lotName(r.parking_lot_id)}</strong>
                  <span className="badge">{RES_STATUS[r.status] || r.status}</span>
                </div>
                <p className="muted">
                  {fmt(r.start_time)} — {fmt(r.end_time)}
                  {user.role === "admin" && <>, пользователь id {r.user_id}</>}
                </p>
                {r.status === "active" && <button className="secondary" onClick={() => cancel(r.id)}>Отменить</button>}
              </li>
            ))}
          </ul>
        </section>

        <section className="panel">
          <h2>Транспорт</h2>
          {vehicles.length === 0 && (
            <p className="muted">{isAdmin ? "Транспорта пока нет. Добавьте его в форме слева." : "Транспорт пока не добавлен."}</p>
          )}
          <ul className="issues">
            {vehicles.map((v) => (
              <li key={v.id} className={`issue s-${vehicleClass[v.status] || "new"}`}>
                <div className="row">
                  <strong>{VEHICLE_TYPES[v.vehicle_type] || v.vehicle_type} {v.plate_number}</strong>
                  {isAdmin ? (
                    <select aria-label="Статус транспорта" value={v.status}
                      onChange={(e) => run(() => api.setVehicleStatus(token, v.id, e.target.value))}>
                      {Object.entries(VEHICLE_STATUS).map(([k, label]) => <option key={k} value={k}>{label}</option>)}
                    </select>
                  ) : (
                    <span className="badge">{VEHICLE_STATUS[v.status] || v.status}</span>
                  )}
                </div>
                {v.model && <p className="muted">{v.model}</p>}
                {isAdmin && <button className="secondary danger" onClick={() => removeVehicle(v)}>Удалить</button>}
              </li>
            ))}
          </ul>
        </section>
      </div>
    </div>
  );
}
