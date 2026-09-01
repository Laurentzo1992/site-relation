export const AD_PRICE = 500;
export const CONNECTION_REQUEST_PRICE = 500;
export const CURRENCY = "XOF";
export const ADS_PAGE_SIZE = 12;

// Single source of truth for selectable genders in the UI. The backend
// Gender enum also has "autre" (kept for backward compatibility with any
// pre-existing data), but it's intentionally not offered as a choice here --
// every gender <select> in the app should import this instead of hardcoding
// its own option list.
export const SELECTABLE_GENDERS = [
  { value: "homme", label: "Homme" },
  { value: "femme", label: "Femme" },
];

export const AD_STATUS_LABELS = {
  draft: "Brouillon",
  pending_payment: "En attente de paiement",
  published: "Publiee",
  rejected: "Rejetee",
  archived: "Archivee",
};

export const CONNECTION_STATUS_LABELS = {
  pending_payment: "En attente de paiement",
  pending_admin: "En cours de validation",
  approved: "Validee",
  rejected: "Rejetee",
};
