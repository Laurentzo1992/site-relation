import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { createAd } from "../api/ads";
import PaymentBox from "../components/PaymentBox";
import { AD_PRICE, CURRENCY } from "../constants";

export default function CreateAd() {
  const navigate = useNavigate();
  const [form, setForm] = useState({
    title: "",
    description: "",
    looking_for_gender: "homme",
    min_age: "",
    max_age: "",
    city: "",
  });
  const [ad, setAd] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const update = (field) => (e) => setForm({ ...form, [field]: e.target.value });

  const handleSubmit = async (e) => {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      const payload = {
        ...form,
        min_age: form.min_age ? Number(form.min_age) : null,
        max_age: form.max_age ? Number(form.max_age) : null,
      };
      const res = await createAd(payload);
      setAd(res.data);
    } catch (err) {
      setError(err.response?.data?.detail || "Impossible de creer l'annonce");
    } finally {
      setBusy(false);
    }
  };

  if (ad) {
    return (
      <div className="card form-card fade-in-up">
        <div className="form-icon">✨</div>
        <h1>Plus qu'une etape !</h1>
        <p>
          Votre annonce <strong>{ad.title}</strong> a ete enregistree. Elle sera visible par
          toute la communaute des que le paiement est confirme.
        </p>
        <PaymentBox
          type="ad_publication"
          referenceId={ad.id}
          amount={AD_PRICE}
          currency={CURRENCY}
          onPaid={() => navigate("/my-ads")}
        />
      </div>
    );
  }

  return (
    <div className="card form-card fade-in-up">
      <div className="form-icon">💘</div>
      <h1>Racontez votre histoire</h1>
      <p className="meta">Une bonne annonce, sincere et precise, attire les bonnes personnes.</p>
      <form onSubmit={handleSubmit}>
        <label>
          Titre
          <input value={form.title} onChange={update("title")} required />
        </label>
        <label>
          Description
          <textarea value={form.description} onChange={update("description")} required rows={5} />
        </label>
        <label>
          Je recherche
          <select value={form.looking_for_gender} onChange={update("looking_for_gender")}>
            <option value="homme">Homme</option>
            <option value="femme">Femme</option>
          </select>
        </label>
        <div className="row">
          <label>
            Age min
            <input type="number" value={form.min_age} onChange={update("min_age")} min={18} />
          </label>
          <label>
            Age max
            <input type="number" value={form.max_age} onChange={update("max_age")} min={18} />
          </label>
        </div>
        <label>
          Ville
          <input value={form.city} onChange={update("city")} />
        </label>
        {error && <p className="error">{error}</p>}
        <button type="submit" disabled={busy}>
          {busy ? "Enregistrement..." : `Continuer vers le paiement (${AD_PRICE} ${CURRENCY})`}
        </button>
      </form>
    </div>
  );
}
