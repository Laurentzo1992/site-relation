import { useEffect, useState } from "react";
import { confirmPayment, getPaymentOptions, initiatePayment, paymentErrorMessage } from "../api/payments";
import SebPayForm from "./payment/SebPayForm";

const PROVIDER_LABELS = {
  ligdicash: "LigdiCash",
  sebpay: "Mobile Money (SebPay)",
  mock: "Paiement de test",
};

/**
 * Pays for the given (type, referenceId) with one of the providers the
 * backend has enabled (GET /payments/options); when several are, the member
 * picks one.
 *
 * - LigdiCash: the browser is redirected to its checkout_url and LigdiCash
 *   later sends the user back to /payments/:id/return (see PaymentReturn.jsx).
 * - SebPay: a direct Mobile Money debit handled inline (see SebPayForm.jsx).
 * - Mock (local dev): a "simulate" button confirms the payment itself, for
 *   testing without real money.
 */
export default function PaymentBox({ type, referenceId, amount, currency, onPaid }) {
  const [providers, setProviders] = useState([]);
  const [provider, setProvider] = useState(null);
  const [payment, setPayment] = useState(null);
  const [paid, setPaid] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    getPaymentOptions()
      .then((res) => {
        setProviders(res.data.providers);
        setProvider(res.data.default);
      })
      .catch(() => {
        // Options unreachable: let the backend pick its default provider.
        setProvider("default");
      });
  }, []);

  const succeeded = (result) => {
    setPaid(result);
    onPaid?.(result);
  };

  const initiate = async () => {
    setBusy(true);
    setError("");
    try {
      const res = await initiatePayment(type, referenceId, provider === "default" ? {} : { provider });
      if (res.data.checkout_url) {
        window.location.href = res.data.checkout_url;
        return;
      }
      setPayment(res.data);
    } catch (err) {
      setError(paymentErrorMessage(err, "Erreur lors de l'initialisation du paiement"));
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
      succeeded(res.data);
    } catch (err) {
      setError(paymentErrorMessage(err, "Erreur lors de la confirmation du paiement"));
    } finally {
      setBusy(false);
    }
  };

  const done = paid ?? (payment?.status === "success" ? payment : null);
  if (done) {
    return (
      <p className="payment-box success">
        <span className="payment-check">✓</span> Paiement confirme ({done.amount} {done.currency}).
      </p>
    );
  }

  if (provider === null) {
    return (
      <div className="payment-box">
        <div className="spinner" />
      </div>
    );
  }

  return (
    <div className="payment-box">
      <p className="payment-amount">
        Frais requis : <strong>{amount} {currency}</strong>
      </p>

      {providers.length > 1 && !payment && (
        <div className="payment-providers" role="radiogroup" aria-label="Moyen de paiement">
          {providers.map((p) => (
            <label key={p} className={`payment-provider${p === provider ? " selected" : ""}`}>
              <input
                type="radio"
                name={`provider-${type}-${referenceId}`}
                checked={p === provider}
                onChange={() => {
                  setProvider(p);
                  setError("");
                }}
              />
              {PROVIDER_LABELS[p] ?? p}
            </label>
          ))}
        </div>
      )}

      {provider === "sebpay" ? (
        <SebPayForm
          type={type}
          referenceId={referenceId}
          amount={amount}
          currency={currency}
          onSuccess={succeeded}
        />
      ) : (
        <>
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
        </>
      )}
    </div>
  );
}
