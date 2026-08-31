import client from "./client";

export function initiatePayment(type, referenceId) {
  return client.post("/payments/initiate", { type, reference_id: referenceId });
}

export function confirmPayment(paymentId) {
  return client.post(`/payments/${paymentId}/confirm`);
}

export function getPaymentStatus(paymentId) {
  return client.get(`/payments/${paymentId}/status`);
}

export function listMyPayments() {
  return client.get("/payments/mine");
}
