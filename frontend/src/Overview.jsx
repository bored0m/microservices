import { useEffect, useState } from "react";
import { SERVICES, checkHealth } from "./api.js";

export default function Overview({ onOpen }) {
  const [health, setHealth] = useState({});

  useEffect(() => {
    let alive = true;
    SERVICES.forEach(async (s) => {
      const ok = await checkHealth(s.base);
      if (alive) setHealth((h) => ({ ...h, [s.tab]: ok }));
    });
    return () => { alive = false; };
  }, []);

  return (
    <div className="page">
      <section className="panel">
        <h2>Сервисы «Умного города»</h2>
        <p className="muted">Каждый микросервис работает независимо, со своей базой данных. Откройте страницу сервиса или его API-документацию.</p>
        <ul className="cards">
          {SERVICES.map((s) => {
            const state = health[s.tab];
            return (
              <li key={s.tab} className="card">
                <div className="row">
                  <strong>{s.name}</strong>
                  <span className="badge">
                    <span className={`dot ${state === undefined ? "wait" : state ? "ok" : "bad"}`} aria-hidden="true" />
                    {state === undefined ? "проверка…" : state ? "работает" : "недоступен"}
                  </span>
                </div>
                <p className="muted">{s.desc}</p>
                <div className="row start">
                  <button onClick={() => onOpen(s.tab)}>Открыть страницу</button>
                  <a className="btn-link" href={`${s.base}/docs`} target="_blank" rel="noreferrer">API docs ↗</a>
                </div>
              </li>
            );
          })}
        </ul>
      </section>
    </div>
  );
}
