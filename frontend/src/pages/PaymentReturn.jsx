import { useEffect, useRef, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { getPaymentStatus } from "../api/payments";

const NEXT_STEP = {
  ad_publication: { to: "/my-ads", label: "Voir mes annonces" },
  connection_request: { to: "/my-requests", label: "Voir mes demandes" },
};

export default function PaymentReturn() {
  const { id } = useParams();
  const [searchParams] = useSearchParams();
  const cancelled = searchParams.get("status") === "cancelled";
  const [payment, setPayment] = useState(null);
  const [error, setError] = useState("");
  const attempts = useRef(0);

  useEffect(() => {
    if (cancelled) return;

    let cancelledEffect = false;

    const poll = async () => {
      try {
        const res = await getPaymentStatus(id);
        if (cancelledEffect) return;
        setPayment(res.data);
        attempts.current += 1;
        if (res.data.status === "pending" && attempts.current < 6) {
          setTimeout(poll, 2000);
        }
      } catch (err) {
        if (!cancelledEffect) {
          setError(err.response?.data?.detail || "Impossible de verifier le paiement");
        }
      }
    };

    poll();
    return () => {
      cancelledEffect = true;
    };
  }, [id, cancelled]);

  if (cancelled) {
    return (
      <div className="card status-card">
        <h1>Paiement annule</h1>
        <p>Vous avez annule le paiement. Vous pouvez reessayer a tout moment.</p>
        <Link to="/">Retour aux annonces</Link>
      </div>
    );
  }

  if (error) {
    return (
      <div className="card status-card">
        <h1>Erreur</h1>
        <p className="error">{error}</p>
      </div>
    );
  }

  if (!payment) {
    return (
      <div className="card status-card">
        <h1>Verification du paiement...</h1>
        <div className="spinner" />
      </div>
    );
  }

  const next = NEXT_STEP[payment.type];

  if (payment.status === "success") {
    return (
      <div className="card status-card success-card">
        <div className="status-icon">✓</div>
        <h1>Paiement confirme !</h1>
        <p>Merci, votre paiement de {payment.amount} {payment.currency} a bien ete recu.</p>
        {next && <Link to={next.to}>{next.label}</Link>}
      </div>
    );
  }

  if (payment.status === "failed") {
    return (
      <div className="card status-card failed-card">
        <div className="status-icon">✕</div>
        <h1>Le paiement a echoue</h1>
        <p>Aucun montant n'a ete debite avec succes. Vous pouvez reessayer.</p>
        {next && <Link to={next.to}>{next.label}</Link>}
      </div>
    );
  }

  return (
    <div className="card status-card">
      <h1>Paiement en cours de verification</h1>
      <div className="spinner" />
      <p>Cela peut prendre quelques instants. Vous pouvez revenir plus tard, votre paiement sera pris en compte automatiquement.</p>
      {next && <Link to={next.to}>{next.label}</Link>}
    </div>
  );
}
