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

const EMPTY_SEARCH = { q: "", city: "" };
const EMPTY_FILTERS = { q: "", city: "", gender: "" };

export default function AdsList() {
  const { user } = useAuth();
  const [data, setData] = useState(null);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [searchInput, setSearchInput] = useState(EMPTY_SEARCH);
  const [gender, setGender] = useState("");
  const [filters, setFilters] = useState(EMPTY_FILTERS);

  // Debounce free-text search / city so we don't fire a request per keystroke.
  useEffect(() => {
    const timer = setTimeout(() => {
      setFilters((f) => ({ ...f, q: searchInput.q, city: searchInput.city }));
      setPage(1);
    }, 400);
    return () => clearTimeout(timer);
  }, [searchInput]);

  useEffect(() => {
    setFilters((f) => ({ ...f, gender }));
    setPage(1);
  }, [gender]);

  useEffect(() => {
    setLoading(true);
    setError("");
    listAds({ page, pageSize: ADS_PAGE_SIZE, ...filters })
      .then((res) => setData(res.data))
      .catch(() => setError("Impossible de charger les annonces pour le moment."))
      .finally(() => setLoading(false));
    window.scrollTo({ top: 0, behavior: "smooth" });
  }, [page, filters]);

  const hasActiveFilters = filters.q || filters.city || filters.gender;

  const clearFilters = () => {
    setSearchInput(EMPTY_SEARCH);
    setGender("");
  };

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

      <div className="search-bar">
        <input
          type="search"
          placeholder="Rechercher une annonce..."
          value={searchInput.q}
          onChange={(e) => setSearchInput((s) => ({ ...s, q: e.target.value }))}
          aria-label="Rechercher une annonce"
        />
        <input
          type="text"
          placeholder="Ville"
          value={searchInput.city}
          onChange={(e) => setSearchInput((s) => ({ ...s, city: e.target.value }))}
          aria-label="Filtrer par ville"
        />
        <select value={gender} onChange={(e) => setGender(e.target.value)} aria-label="Filtrer par genre">
          <option value="">Tous les genres</option>
          <option value="homme">Homme</option>
          <option value="femme">Femme</option>
        </select>
        {hasActiveFilters && (
          <button type="button" className="btn-outline" onClick={clearFilters}>
            Effacer
          </button>
        )}
      </div>

      {error && <p className="error">{error}</p>}

      {loading && (
        <div className="grid">
          {Array.from({ length: 6 }).map((_, i) => (
            <div className="skeleton-card" key={i} />
          ))}
        </div>
      )}

      {!loading && data && data.items.length === 0 && hasActiveFilters && (
        <div className="empty-state fade-in">
          <div className="empty-icon">🔍</div>
          <p>Aucune annonce ne correspond a ta recherche.</p>
          <button type="button" className="btn" onClick={clearFilters}>
            Effacer les filtres
          </button>
        </div>
      )}

      {!loading && data && data.items.length === 0 && !hasActiveFilters && (
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
