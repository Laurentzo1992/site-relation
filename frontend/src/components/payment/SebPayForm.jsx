import { useEffect, useRef, useState } from "react";
import PhoneInput, { parsePhoneNumber } from "react-phone-number-input";
import "react-phone-number-input/style.css";
import { getPaymentStatus, getSebPayOperators, initiatePayment, paymentErrorMessage } from "../../api/payments";
import { useAuth } from "../../context/AuthContext";

const POLL_INTERVAL_MS = 3000;
const MAX_POLLS = 60; // ~3 minutes to approve on the phone

/**
 * Direct Mobile Money payment through SebPay: the customer gives the number to
 * debit, picks their operator (some also need an OTP obtained by USSD) and
 * then approves the debit on their phone. We poll the backend meanwhile; the
 * backend itself re-verifies with SebPay, so a missed webhook is harmless.
 */
export default function SebPayForm({ type, referenceId, amount, currency, onSuccess }) {
  const { user } = useAuth();
  // Preselect the country of the member's own profile number (the number to
  // debit is entered separately and need not be the same one).
  const defaultCountry = (user?.phone && parsePhoneNumber(user.phone)?.country) || "CI";
  const [phone, setPhone] = useState("");
  const [operators, setOperators] = useState([]);
  const [operatorCode, setOperatorCode] = useState("");
  const [otp, setOtp] = useState("");
  const [payment, setPayment] = useState(null);
  const [timedOut, setTimedOut] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const onSuccessRef = useRef(onSuccess);
  onSuccessRef.current = onSuccess;

  const country = phone ? parsePhoneNumber(phone)?.country : undefined;
  const operator = operators.find((o) => o.code === operatorCode);
  const waiting = payment?.status === "pending";

  useEffect(() => {
    setOperators([]);
    setOperatorCode("");
    setOtp("");
    if (!country) return;

    let stale = false;
    getSebPayOperators(country)
      .then((res) => {
        if (stale) return;
        setOperators(res.data);
        if (res.data.length === 1) setOperatorCode(res.data[0].code);
      })
      .catch((err) => {
        if (!stale) setError(paymentErrorMessage(err, "Impossible de charger les operateurs"));
      });
    return () => {
      stale = true;
    };
  }, [country]);

  useEffect(() => {
    if (!waiting) return;

    let stopped = false;
    let timer;
    let polls = 0;

    const poll = async () => {
      try {
        const res = await getPaymentStatus(payment.id);
        if (stopped) return;
        if (res.data.status !== "pending") {
          setPayment(res.data);
          if (res.data.status === "success") onSuccessRef.current(res.data);
          return;
        }
      } catch {
        // transient network/API error: keep trying until the time limit
      }
      polls += 1;
      if (polls >= MAX_POLLS) {
        setTimedOut(true);
        return;
      }
      timer = setTimeout(poll, POLL_INTERVAL_MS);
    };

    timer = setTimeout(poll, POLL_INTERVAL_MS);
    return () => {
      stopped = true;
      clearTimeout(timer);
    };
  }, [waiting, payment?.id]);

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    setError("");
    setTimedOut(false);
    try {
      const res = await initiatePayment(type, referenceId, {
        provider: "sebpay",
        phone,
        country,
        operator: operatorCode,
        ...(operator?.otp_required ? { otp_code: otp.trim() } : {}),
      });
      setPayment(res.data);
      if (res.data.status === "success") {
        onSuccess(res.data);
      } else if (res.data.status === "failed") {
        setError("Le paiement a ete refuse. Verifiez le numero, le solde et le code, puis reessayez.");
      } else if (res.data.checkout_url) {
        // Wave-style operators: the customer approves on the operator's page.
        window.open(res.data.checkout_url, "_blank", "noopener");
      }
    } catch (err) {
      setError(paymentErrorMessage(err, "Erreur lors de l'initialisation du paiement"));
    } finally {
      setBusy(false);
    }
  };

  if (waiting) {
    return (
      <div className="payment-waiting">
        <div className="spinner" />
        {timedOut ? (
          <p>
            Toujours en attente de votre validation. Si vous avez deja valide sur votre telephone, le paiement sera
            pris en compte automatiquement : revenez sur cette page dans quelques instants.
          </p>
        ) : (
          <p>
            Validez le paiement de <strong>{amount} {currency}</strong> sur votre telephone
            {payment.checkout_url && (
              <>
                {" "}(ou <a href={payment.checkout_url} target="_blank" rel="noopener noreferrer">ouvrez la page de validation</a>)
              </>
            )}
            . Cette page se met a jour toute seule.
          </p>
        )}
      </div>
    );
  }

  return (
    <form className="payment-form" onSubmit={submit}>
      <label>
        Numero Mobile Money a debiter
        <PhoneInput
          international
          defaultCountry={defaultCountry}
          value={phone}
          onChange={(value) => setPhone(value || "")}
          placeholder="Numero Mobile Money"
          required
        />
      </label>

      {country && operators.length > 0 && (
        <label>
          Operateur
          <select value={operatorCode} onChange={(e) => setOperatorCode(e.target.value)} required>
            <option value="">Choisir...</option>
            {operators.map((o) => (
              <option key={o.code} value={o.code}>{o.name}</option>
            ))}
          </select>
        </label>
      )}
      {country && operators.length === 0 && !error && (
        <p className="payment-hint">Chargement des operateurs...</p>
      )}

      {operator?.otp_required && (
        <label>
          Code de validation (OTP)
          <input
            value={otp}
            onChange={(e) => setOtp(e.target.value)}
            inputMode="numeric"
            autoComplete="one-time-code"
            required
          />
          {operator.ussd_code && (
            <span className="payment-hint">
              Composez <strong>{operator.ussd_code.replace("montant", amount)}</strong> sur votre telephone pour
              recevoir ce code, puis saisissez-le ici.
            </span>
          )}
        </label>
      )}

      {error && <p className="error">{error}</p>}
      <button className="btn-pay" disabled={busy || !operatorCode}>
        {busy ? "Envoi..." : `Payer ${amount} ${currency}`}
      </button>
    </form>
  );
}
