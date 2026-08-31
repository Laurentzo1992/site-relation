import client from "./client";

export function listAds({ page, pageSize }) {
  return client.get("/ads", { params: { page, page_size: pageSize } });
}

export function getAd(id) {
  return client.get(`/ads/${id}`);
}

export function getMyAds() {
  return client.get("/ads/mine");
}

export function createAd(payload) {
  return client.post("/ads", payload);
}

export function deleteAd(id) {
  return client.delete(`/ads/${id}`);
}
