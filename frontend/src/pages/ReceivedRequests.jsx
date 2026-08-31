import { useEffect, useState } from "react";
import { listReceivedConnectionRequests } from "../api/connections";
import ConnectionCard from "../components/ConnectionCard";

export default function ReceivedRequests() {
  const [requests, setRequests] = useState([]);
  const [loading, setLoading] = useState(true);

  const load = () => {
    listReceivedConnectionRequests()
      .then((res) => setRequests(res.data))
      .finally(() => setLoading(false));
  };

  useEffect(load, []);

  if (loading) {
    return (
      <div>
        <h1>Demandes recues sur mes annonces</h1>
        <div className="spinner" />
      </div>
    );
  }

  return (
    <div>
      <h1>Demandes recues sur mes annonces</h1>
      <p className="hint">
        Chaque demande est verifiee et validee par un administrateur avant que les coordonnees
        ne soient echangees — vous n'avez rien a faire ici, votre annonce reste protegee.
      </p>
      {requests.length === 0 && (
        <div className="empty-state fade-in">
          <div className="empty-icon">📭</div>
          <p>Aucune demande recue pour le moment.</p>
        </div>
      )}
      <div className="grid">
        {requests.map((req) => (
          <ConnectionCard
            key={req.id}
            request={req}
            label={`${req.requester.full_name} souhaite etre mis en relation (annonce : ${req.ad.title})`}
            onChanged={load}
          />
        ))}
      </div>
    </div>
  );
}
