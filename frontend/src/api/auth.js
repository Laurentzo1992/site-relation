import client from "./client";

export function login(email, password) {
  const form = new URLSearchParams();
  form.set("username", email);
  form.set("password", password);
  return client.post("/auth/login", form, {
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
  });
}

export function register(payload) {
  return client.post("/auth/register", payload);
}

export function getMe() {
  return client.get("/auth/me");
}
