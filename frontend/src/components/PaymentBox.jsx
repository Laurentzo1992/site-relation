import { useState } from "react";
import { confirmPayment, initiatePayment } from "../api/payments";

/**
 * Initiates a payment for the given (type, referenceId).
 *
 * - If the backend responds with a checkout_url (real LigdiCash payment),
 *   the browser is redirected there; LigdiCash later sends the user back to
 *   /payments/:id/return (see PaymentReturn.jsx) once they've paid.
 * - Otherwise (mock provider, local dev) a "simulate" button lets the
 *   frontend confirm the payment itself, for testing without real money.
 */
export default function PaymentBox({ type, referenceId, amount, currency, onPaid }) {
  const [payment, setPayment] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const initiate = async () => {
    setBusy(true);
    setError("");
    try {
      const res = await initiatePayment(type, referenceId);
      if (res.data.checkout_url) {
        window.location.href = res.data.checkout_url;
        return;
      }
      setPayment(res.data);
    } catch (err) {
      setError(err.response?.data?.detail || "Erreur lors de l'initialisation du paiement");
    } finally {
      setBusy(false);
    }
  };

  const confirm = async () => {
    setBusy(true);
    setError("");
    try {
      const res = await confirmPayment(payment.id);
      setPayment(res.data);
      onPaid?.(res.data);
    } catch (err) {
      setError(err.response?.data?.detail || "Erreur lors de la confirmation du paiement");
    } finally {
      setBusy(false);
    }
  };

  if (payment?.status === "success") {
    return (
      <p className="payment-box success">
        <span className="payment-check">✓</span> Paiement confirme ({payment.amount} {payment.currency}).
      </p>
    );
  }

  return (
    <div className="payment-box">
      <p className="payment-amount">
        Frais requis : <strong>{amount} {currency}</strong>
      </p>
      {error && <p className="error">{error}</p>}
      {!payment ? (
        <button className="btn-pay" disabled={busy} onClick={initiate}>
          {busy ? "Redirection..." : `Payer ${amount} ${currency}`}
        </button>
      ) : (
        <button className="btn-pay" disabled={busy} onClick={confirm}>
          Simuler la confirmation du paiement
        </button>
      )}
    </div>
  );
}
