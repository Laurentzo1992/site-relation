import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { listAds } from "../api/ads";
import { useAuth } from "../context/AuthContext";
import DateScene from "../components/DateScene";
import { ADS_PAGE_SIZE } from "../constants";

function buildPageList(current, totalPages) {
  const pages = new Set([1, totalPages, current, current - 1, current + 1]);
  return [...pages]
    .filter((p) => p >= 1 && p <= totalPages)
    .sort((a, b) => a - b);
}

export default function AdsList() {
  const { user } = useAuth();
  const [data, setData] = useState(null);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    setLoading(true);
    setError("");
    listAds({ page, pageSize: ADS_PAGE_SIZE })
      .then((res) => setData(res.data))
      .catch(() => setError("Impossible de charger les annonces pour le moment."))
      .finally(() => setLoading(false));
    window.scrollTo({ top: 0, behavior: "smooth" });
  }, [page]);

  const totalPages = data?.total_pages ?? 1;
  const pageList = buildPageList(page, totalPages);

  return (
    <div>
      <section className="hero">
        <span className="hero-blob one" />
        <span className="hero-blob two" />
        <div className="hero-content fade-in-up">
          <span className="hero-eyebrow">100% confidentiel</span>
          <h1>
            Faites de <em>vraies rencontres</em>, en toute confiance.
          </h1>
          <p className="hero-sub">
            Publiez votre annonce et laissez parler le coeur. Vos coordonnees restent
            privees jusqu'a ce qu'une mise en relation soit validee par notre equipe.
          </p>
          <div className="hero-actions">
            <Link to={user ? "/ads/new" : "/register"} className="btn btn-cta">
              Publier mon annonce
            </Link>
            <a href="#annonces" className="btn btn-outline">
              Decouvrir les annonces
            </a>
          </div>
          <div className="hero-badges">
            <span>🔒 Coordonnees protegees</span>
            <span>✅ Mise en relation validee</span>
            <span>💳 Paiement securise</span>
          </div>
        </div>
        <div className="date-scene-wrap">
          <DateScene />
        </div>
      </section>

      <h2 id="annonces">Annonces</h2>

      {error && <p className="error">{error}</p>}

      {loading && (
        <div className="grid">
          {Array.from({ length: 6 }).map((_, i) => (
            <div className="skeleton-card" key={i} />
          ))}
        </div>
      )}

      {!loading && data && data.items.length === 0 && (
        <div className="empty-state fade-in">
          <div className="empty-icon">💌</div>
          <p>Aucune annonce pour l'instant — soyez le premier a tenter votre chance !</p>
          <Link to={user ? "/ads/new" : "/register"} className="btn">
            Publier la premiere annonce
          </Link>
        </div>
      )}

      {!loading && data && data.items.length > 0 && (
        <>
          <div className="grid">
            {data.items.map((ad, i) => (
              <Link
                to={`/ads/${ad.id}`}
                key={ad.id}
                className="card ad-card fade-in-up"
                style={{ animationDelay: `${Math.min(i, 6) * 0.05}s` }}
              >
                {ad.is_new && <span className="new-badge">Nouveau</span>}
                <h2>{ad.title}</h2>
                <p className="meta">
                  {ad.owner.gender}
                  {ad.city ? ` · ${ad.city}` : ""}
                </p>
                <p>
                  {ad.description.slice(0, 140)}
                  {ad.description.length > 140 ? "..." : ""}
                </p>
              </Link>
            ))}
          </div>

          {totalPages > 1 && (
            <>
              <nav className="pagination" aria-label="Pagination des annonces">
                <button disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
                  ←
                </button>
                {pageList.map((p, i) => (
                  <span key={p} style={{ display: "contents" }}>
                    {i > 0 && p - pageList[i - 1] > 1 && <span className="meta">…</span>}
                    <button className={p === page ? "active" : ""} onClick={() => setPage(p)}>
                      {p}
                    </button>
                  </span>
                ))}
                <button disabled={page >= totalPages} onClick={() => setPage((p) => p + 1)}>
                  →
                </button>
              </nav>
              <p className="pagination-info">
                Page {page} sur {totalPages} · {data.total} annonce{data.total > 1 ? "s" : ""} au total
              </p>
            </>
          )}
        </>
      )}
    </div>
  );
}
