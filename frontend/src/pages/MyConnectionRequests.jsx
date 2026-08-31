import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { listMyConnectionRequests } from "../api/connections";
import ConnectionCard from "../components/ConnectionCard";

export default function MyConnectionRequests() {
  const [requests, setRequests] = useState([]);
  const [loading, setLoading] = useState(true);

  const load = () => {
    listMyConnectionRequests()
      .then((res) => setRequests(res.data))
      .finally(() => setLoading(false));
  };

  useEffect(load, []);

  if (loading) {
    return (
      <div>
        <h1>Mes demandes de mise en relation</h1>
        <div className="spinner" />
      </div>
    );
  }

  return (
    <div>
      <h1>Mes demandes de mise en relation</h1>
      {requests.length === 0 && (
        <div className="empty-state fade-in">
          <div className="empty-icon">💬</div>
          <p>Vous n'avez envoye aucune demande pour l'instant.</p>
          <Link to="/" className="btn">
            Parcourir les annonces
          </Link>
        </div>
      )}
      <div className="grid">
        {requests.map((req) => (
          <ConnectionCard
            key={req.id}
            request={req}
            label={`Annonce : ${req.ad.title} (${req.ad.owner.full_name})`}
            showPayment
            onChanged={load}
          />
        ))}
      </div>
    </div>
  );
}
