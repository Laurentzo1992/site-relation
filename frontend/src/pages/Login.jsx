import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { PlusIcon } from "../components/icons";

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      await login(email, password);
      navigate("/");
    } catch (err) {
      setError(err.response?.data?.detail || "Connexion impossible");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="card form-card fade-in-up">
      <div className="form-icon">👋</div>
      <h1>Content de vous revoir</h1>
      <p className="meta">Connectez-vous pour retrouver vos annonces et vos demandes.</p>
      <form onSubmit={handleSubmit}>
        <label>
          Email
          <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
        </label>
        <label>
          Mot de passe
          <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
        </label>
        {error && <p className="error">{error}</p>}
        <button type="submit" disabled={busy}>
          {busy ? "Connexion..." : "Se connecter"}
        </button>
      </form>
      <div className="signup-prompt">
        <p className="meta">Pas encore de compte ?</p>
        <Link to="/register" className="btn btn-cta">
          <PlusIcon />
          Inscrivez-vous
        </Link>
      </div>
    </div>
  );
}
