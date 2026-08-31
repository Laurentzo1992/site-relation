import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { getAd } from "../api/ads";
import { createConnectionRequest } from "../api/connections";
import { useAuth } from "../context/AuthContext";
import { CONNECTION_REQUEST_PRICE, CURRENCY } from "../constants";

export default function AdDetail() {
  const { id } = useParams();
  const { user } = useAuth();
  const navigate = useNavigate();
  const [ad, setAd] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [requestSent, setRequestSent] = useState(false);

  useEffect(() => {
    getAd(id)
      .then((res) => setAd(res.data))
      .catch(() => setError("Annonce introuvable"));
  }, [id]);

  const askConnection = async () => {
    if (!user) {
      navigate("/login");
      return;
    }
    setBusy(true);
    setError("");
    try {
      const res = await createConnectionRequest(Number(id));
      setRequestSent(true);
      navigate(`/my-requests`, { state: { newRequestId: res.data.id } });
    } catch (err) {
      setError(err.response?.data?.detail || "Impossible d'envoyer la demande");
    } finally {
      setBusy(false);
    }
  };

  if (error && !ad) {
    return (
      <div className="empty-state fade-in">
        <div className="empty-icon">🔍</div>
        <p className="error">{error}</p>
        <Link to="/" className="btn">
          Retour aux annonces
        </Link>
      </div>
    );
  }

  if (!ad) return <div className="spinner" />;

  const isOwnAd = user && user.id === ad.owner.id;

  return (
    <div className="card fade-in-up" style={{ maxWidth: 640, margin: "0 auto" }}>
      <Link to="/" className="meta" style={{ textDecoration: "none" }}>
        ← Retour aux annonces
      </Link>
      <h1 style={{ marginTop: "0.8rem" }}>{ad.title}</h1>
      <p className="meta">
        {ad.owner.gender}
        {ad.city ? ` · ${ad.city}` : ""}
      </p>
      <p>{ad.description}</p>
      {(ad.min_age || ad.max_age) && (
        <p className="meta">
          Recherche un(e) {ad.looking_for_gender}
          {ad.min_age ? ` de ${ad.min_age}` : ""}
          {ad.max_age ? ` a ${ad.max_age} ans` : ""}
        </p>
      )}
      {error && <p className="error">{error}</p>}
      {!isOwnAd && !requestSent && (
        <>
          <button disabled={busy} onClick={askConnection}>
            {busy ? "Envoi..." : "💌 Demander la mise en relation"}
          </button>
          <p className="hint" style={{ marginTop: "0.9rem" }}>
            Un petit geste de {CONNECTION_REQUEST_PRICE} {CURRENCY} valide votre demande, puis notre
            equipe verifie et valide la mise en relation. L'identite et les coordonnees ne sont
            devoilees qu'apres cette validation.
          </p>
        </>
      )}
      {isOwnAd && <p className="hint">Ceci est votre annonce.</p>}
    </div>
  );
}
