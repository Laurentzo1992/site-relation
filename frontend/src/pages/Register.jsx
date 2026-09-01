import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import PhoneInput from "react-phone-number-input";
import "react-phone-number-input/style.css";
import { useAuth } from "../context/AuthContext";
import { detectCountryFromIp } from "../api/geo";
import { SELECTABLE_GENDERS } from "../constants";

export default function Register() {
  const { register } = useAuth();
  const navigate = useNavigate();
  const [defaultCountry, setDefaultCountry] = useState("CI");
  const [form, setForm] = useState({
    email: "",
    password: "",
    full_name: "",
    phone: "",
    whatsapp: false,
    gender: "homme",
    city: "",
  });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    detectCountryFromIp().then(setDefaultCountry);
  }, []);

  const update = (field) => (e) => setForm({ ...form, [field]: e.target.value });

  const handleSubmit = async (e) => {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      await register(form);
      navigate("/");
    } catch (err) {
      setError(err.response?.data?.detail || "Inscription impossible");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="card form-card fade-in-up">
      <div className="form-icon">💌</div>
      <h1>Rejoignez la communaute</h1>
      <p className="hint">
        🔒 Votre telephone et votre email restent prives. Ils ne seront jamais affiches publiquement et ne seront
        communiques a un autre membre qu'apres validation d'une mise en relation par un administrateur.
      </p>
      <form onSubmit={handleSubmit}>
        <label>
          Nom complet
          <input value={form.full_name} onChange={update("full_name")} required />
        </label>
        <label>
          Email
          <input type="email" value={form.email} onChange={update("email")} required />
        </label>
        <label>
          Telephone (prive)
          <PhoneInput
            international
            defaultCountry={defaultCountry}
            value={form.phone}
            onChange={(value) => setForm({ ...form, phone: value || "" })}
            placeholder="Votre numero"
            required
          />
        </label>
        <label className="checkbox-label">
          <input
            type="checkbox"
            checked={form.whatsapp}
            onChange={(e) => setForm({ ...form, whatsapp: e.target.checked })}
          />
          Ce numero est disponible sur WhatsApp
        </label>
        <label>
          Mot de passe (8 caracteres minimum)
          <input type="password" value={form.password} onChange={update("password")} required minLength={8} />
        </label>
        <div className="row">
          <label>
            Genre
            <select value={form.gender} onChange={update("gender")}>
              {SELECTABLE_GENDERS.map((g) => (
                <option key={g.value} value={g.value}>
                  {g.label}
                </option>
              ))}
            </select>
          </label>
          <label>
            Ville
            <input value={form.city} onChange={update("city")} />
          </label>
        </div>
        {error && <p className="error">{error}</p>}
        <button type="submit" disabled={busy}>
          {busy ? "Creation..." : "Creer mon compte"}
        </button>
      </form>
      <div className="signup-prompt">
        <p className="meta">Deja inscrit ?</p>
        <Link to="/login" className="btn btn-outline">
          Connectez-vous
        </Link>
      </div>
    </div>
  );
}
