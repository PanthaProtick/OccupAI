const SESSION_KEY = "occupai.demo.session";

export function hasActiveSession() {
  return sessionStorage.getItem(SESSION_KEY) === "active";
}

export function startSession() {
  sessionStorage.setItem(SESSION_KEY, "active");
}

export function endSession() {
  sessionStorage.removeItem(SESSION_KEY);
}
