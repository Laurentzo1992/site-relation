import client from "./client";

export function createConnectionRequest(adId) {
  return client.post("/connections", { ad_id: adId });
}

export function listMyConnectionRequests() {
  return client.get("/connections/mine");
}

export function listReceivedConnectionRequests() {
  return client.get("/connections/received");
}

export function getConnectionRequest(id) {
  return client.get(`/connections/${id}`);
}

export function getContact(requestId) {
  return client.get(`/connections/${requestId}/contact`);
}
