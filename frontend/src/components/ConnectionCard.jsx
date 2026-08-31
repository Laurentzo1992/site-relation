import { useState } from "react";
import { getContact } from "../api/connections";
import PaymentBox from "./PaymentBox";
import { ChatIcon } from "./icons";
import { CONNECTION_REQUEST_PRICE, CONNECTION_STATUS_LABELS, CURRENCY } from "../constants";

export default function ConnectionCard({ request, label, onChanged, showPayment }) {
  const [contact, setContact] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const revealContact = async () => {
    setError("");
    setBusy(true);
    try {
      const res = await getContact(request.id);
      setContact(res.data);
    } catch (err) {
      setError(err.response?.data?.detail || "Impossible d'afficher le contact");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="card fade-in-up">
      <h2>{label}</h2>
      <span className={`status-pill ${request.status}`}>
        {CONNECTION_STATUS_LABELS[request.status] || request.status}
      </span>

      {request.status === "pending_admin" && (
        <p className="hint" style={{ marginTop: "0.8rem" }}>
          Votre paiement est confirme. Un administrateur valide chaque mise en relation
          manuellement pour proteger la communaute — cela prend generalement peu de temps.
        </p>
      )}

      {showPayment && request.status === "pending_payment" && (
        <PaymentBox
          type="connection_request"
          referenceId={request.id}
          amount={CONNECTION_REQUEST_PRICE}
          currency={CURRENCY}
          onPaid={onChanged}
        />
      )}

      {request.status === "rejected" && request.rejection_reason && (
        <p className="hint" style={{ marginTop: "0.8rem" }}>Motif : {request.rejection_reason}</p>
      )}

      {request.status === "approved" && !contact && (
        <button style={{ marginTop: "0.8rem" }} disabled={busy} onClick={revealContact}>
          Voir les coordonnees
        </button>
      )}

      {contact && (
        <div className="contact-box">
          <p>
            <strong>{contact.full_name}</strong>
          </p>
          <p>Telephone : {contact.phone}</p>
          <p>Email : {contact.email}</p>
          {contact.whatsapp && (
            <a
              className="btn btn-whatsapp"
              href={`https://wa.me/${contact.phone.replace("+", "")}`}
              target="_blank"
              rel="noreferrer"
            >
              <ChatIcon />
              Contacter sur WhatsApp
            </a>
          )}
        </div>
      )}

      {error && <p className="error">{error}</p>}
    </div>
  );
}
