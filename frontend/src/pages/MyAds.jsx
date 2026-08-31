import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getMyAds } from "../api/ads";
import PaymentBox from "../components/PaymentBox";
import { AD_PRICE, AD_STATUS_LABELS, CURRENCY } from "../constants";

export default function MyAds() {
  const [ads, setAds] = useState([]);
  const [loading, setLoading] = useState(true);

  const load = () => {
    getMyAds()
      .then((res) => setAds(res.data))
      .finally(() => setLoading(false));
  };

  useEffect(load, []);

  if (loading) {
    return (
      <div>
        <h1>Mes annonces</h1>
        <div className="spinner" />
      </div>
    );
  }

  return (
    <div>
      <h1>Mes annonces</h1>
      {ads.length === 0 && (
        <div className="empty-state fade-in">
          <div className="empty-icon">📝</div>
          <p>Vous n'avez pas encore d'annonce.</p>
          <Link to="/ads/new" className="btn">
            Publier ma premiere annonce
          </Link>
        </div>
      )}
      <div className="grid">
        {ads.map((ad, i) => (
          <div className="card fade-in-up" key={ad.id} style={{ animationDelay: `${i * 0.05}s` }}>
            <h2>{ad.title}</h2>
            <span className={`status-pill ${ad.status}`}>{AD_STATUS_LABELS[ad.status] || ad.status}</span>
            <p style={{ marginTop: "0.7rem" }}>{ad.description.slice(0, 140)}</p>
            {ad.status === "pending_payment" && (
              <PaymentBox
                type="ad_publication"
                referenceId={ad.id}
                amount={AD_PRICE}
                currency={CURRENCY}
                onPaid={load}
              />
            )}
            {ad.status === "published" && <Link to={`/ads/${ad.id}`}>Voir l'annonce publique →</Link>}
          </div>
        ))}
      </div>
    </div>
  );
}
