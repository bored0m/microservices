const AUTH = import.meta.env.VITE_AUTH_URL || "http://localhost:8001";
const UTILITY = import.meta.env.VITE_UTILITY_URL || "http://localhost:8002";
const BILLING = import.meta.env.VITE_BILLING_URL || "http://localhost:8003";
const NOTIFICATION = import.meta.env.VITE_NOTIFICATION_URL || "http://localhost:8004";
const TRANSPORT = import.meta.env.VITE_TRANSPORT_URL || "http://localhost:8005";
const ENVIRONMENT = import.meta.env.VITE_ENVIRONMENT_URL || "http://localhost:8006";

// Все микросервисы: для страницы «Сервисы» (проверка /health и ссылка на Swagger).
export const SERVICES = [
  { tab: "profile", name: "Identity & Auth", base: AUTH, desc: "Регистрация, вход, профили и роли пользователей" },
  { tab: "issues", name: "Utility", base: UTILITY, desc: "Заявки ЖКХ: подача и обработка" },
  { tab: "billing", name: "Billing & Payment", base: BILLING, desc: "Лицевые счета, счета на оплату, платежи" },
  { tab: "transport", name: "Transport", base: TRANSPORT, desc: "Городской транспорт и бронирование парковок" },
  { tab: "environment", name: "Environment", base: ENVIRONMENT, desc: "Датчики воздуха, шума, температуры и пороговые оповещения" },
  { tab: "notifications", name: "Notification", base: NOTIFICATION, desc: "Уведомления от всех сервисов" },
];

export async function checkHealth(base) {
  try {
    const res = await fetch(base + "/health", { signal: AbortSignal.timeout(4000) });
    return res.ok;
  } catch {
    return false;
  }
}

async function request(base, path, { method = "GET", body, token } = {}) {
  let res;
  try {
    res = await fetch(base + path, {
      method,
      headers: {
        ...(body ? { "Content-Type": "application/json" } : {}),
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: body ? JSON.stringify(body) : undefined,
    });
  } catch {
    throw new Error("Сервер недоступен. Проверьте, что сервисы запущены.");
  }
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    const d = err.detail;
    const msg = Array.isArray(d) ? d.map((x) => x.msg).join("; ") : d;
    const e = new Error(msg || `Ошибка ${res.status}`);
    e.status = res.status;
    throw e;
  }
  if (res.status === 204) return null;
  return res.json();
}

export const api = {
  register: (b) => request(AUTH, "/auth/register", { method: "POST", body: b }),
  login: (b) => request(AUTH, "/auth/login", { method: "POST", body: b }),
  me: (token) => request(AUTH, "/users/me", { token }),
  issues: (token, status) =>
    request(UTILITY, "/issues" + (status ? `?status=${status}` : ""), { token }),
  createIssue: (token, b) => request(UTILITY, "/issues", { method: "POST", body: b, token }),
  setStatus: (token, id, status) =>
    request(UTILITY, `/issues/${id}`, { method: "PUT", body: { status }, token }),
  users: (token) => request(AUTH, "/users", { token }),
  invoices: (token, userId) => request(BILLING, `/accounts/${userId}/invoices`, { token }),
  createAccount: (token, userId) =>
    request(BILLING, "/accounts", { method: "POST", body: { user_id: userId }, token }),
  createInvoice: (token, userId, b) =>
    request(BILLING, `/accounts/${userId}/invoices`, { method: "POST", body: b, token }),
  pay: (token, invoiceId, method) =>
    request(BILLING, "/payments", { method: "POST", body: { invoice_id: invoiceId, method }, token }),

  // Transport
  vehicles: (token) => request(TRANSPORT, "/vehicles", { token }),
  parking: (token) => request(TRANSPORT, "/parking", { token }),
  reservations: (token) => request(TRANSPORT, "/parking/reservations", { token }),
  reserve: (token, parkingId, b) =>
    request(TRANSPORT, `/parking/${parkingId}/reserve`, { method: "POST", body: b, token }),
  createVehicle: (token, b) => request(TRANSPORT, "/vehicles", { method: "POST", body: b, token }),
  setVehicleStatus: (token, id, status) =>
    request(TRANSPORT, `/vehicles/${id}`, { method: "PATCH", body: { status }, token }),
  deleteVehicle: (token, id) => request(TRANSPORT, `/vehicles/${id}`, { method: "DELETE", token }),
  createParking: (token, b) => request(TRANSPORT, "/parking", { method: "POST", body: b, token }),
  deleteParking: (token, id) => request(TRANSPORT, `/parking/${id}`, { method: "DELETE", token }),
  cancelReservation: (token, id) =>
    request(TRANSPORT, `/parking/reservations/${id}/cancel`, { method: "POST", token }),

  // Environment
  sensors: (token) => request(ENVIRONMENT, "/sensors", { token }),
  createSensor: (token, b) => request(ENVIRONMENT, "/sensors", { method: "POST", body: b, token }),
  setSensorStatus: (token, id, status) =>
    request(ENVIRONMENT, `/sensors/${id}`, { method: "PATCH", body: { status }, token }),
  deleteSensor: (token, id) => request(ENVIRONMENT, `/sensors/${id}`, { method: "DELETE", token }),
  sensorData: (token, id, limit = 10) =>
    request(ENVIRONMENT, `/sensors/${id}/data?limit=${limit}`, { token }),
  addSensorData: (token, b) =>
    request(ENVIRONMENT, "/sensors/data", { method: "POST", body: b, token }),

  // Notification
  notifications: (token, userId) =>
    request(NOTIFICATION, "/notifications" + (userId ? `?user_id=${userId}` : ""), { token }),
};
