import { useEffect, useRef, useState } from "react";
import { Link, NavLink, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import Logo from "./Logo";
import { PlusIcon } from "./icons";

export default function Navbar() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [menuOpen, setMenuOpen] = useState(false);
  const [accountOpen, setAccountOpen] = useState(false);
  const accountRef = useRef(null);

  useEffect(() => {
    setMenuOpen(false);
    setAccountOpen(false);
  }, [location.pathname]);

  useEffect(() => {
    if (!accountOpen) return;
    const onClickOutside = (e) => {
      if (accountRef.current && !accountRef.current.contains(e.target)) {
        setAccountOpen(false);
      }
    };
    document.addEventListener("mousedown", onClickOutside);
    return () => document.removeEventListener("mousedown", onClickOutside);
  }, [accountOpen]);

  const handleLogout = () => {
    logout();
    navigate("/");
  };

  const topLinkClass = ({ isActive }) => (isActive ? "active" : "");
  const menuItemClass = ({ isActive }) => `menu-item ${isActive ? "active" : ""}`;

  return (
    <nav className="navbar">
      <div className="navbar-row">
        <Link to="/" className="brand">
          <Logo size={30} />
          <span>Trouver votre Amour</span>
        </Link>

        <button
          className="hamburger"
          aria-label="Menu"
          aria-expanded={menuOpen}
          onClick={() => setMenuOpen((v) => !v)}
        >
          <span />
          <span />
          <span />
        </button>

        <div className="nav-links desktop-only">
          <NavLink to="/" className={topLinkClass} end>
            Annonces
          </NavLink>
          {user ? (
            <>
              <Link to="/ads/new" className="btn btn-sm btn-cta">
                <PlusIcon />
                Publier une annonce
              </Link>
              <div className="account-menu" ref={accountRef}>
                <button className="account-trigger" onClick={() => setAccountOpen((v) => !v)}>
                  <span className="avatar">{user.full_name.charAt(0).toUpperCase()}</span>
                  {user.full_name.split(" ")[0]}
                  <span className={`chevron ${accountOpen ? "up" : ""}`}>⌄</span>
                </button>
                {accountOpen && (
                  <div className="account-dropdown fade-in">
                    <NavLink to="/my-ads" className={menuItemClass}>
                      Mes annonces
                    </NavLink>
                    <NavLink to="/my-requests" className={menuItemClass}>
                      Mes demandes
                    </NavLink>
                    <NavLink to="/received-requests" className={menuItemClass}>
                      Demandes recues
                    </NavLink>
                    <hr />
                    <button className="menu-item menu-item-danger" onClick={handleLogout}>
                      Deconnexion
                    </button>
                  </div>
                )}
              </div>
            </>
          ) : (
            <>
              <NavLink to="/login" className={topLinkClass}>
                Connexion
              </NavLink>
              <Link to="/register" className="btn btn-sm btn-cta">
                <PlusIcon />
                Inscription
              </Link>
            </>
          )}
        </div>
      </div>

      {menuOpen && (
        <div className="nav-panel fade-in">
          <NavLink to="/" className={menuItemClass} end>
            Annonces
          </NavLink>
          {user ? (
            <>
              <Link to="/ads/new" className="btn btn-cta">
                <PlusIcon />
                Publier une annonce
              </Link>
              <NavLink to="/my-ads" className={menuItemClass}>
                Mes annonces
              </NavLink>
              <NavLink to="/my-requests" className={menuItemClass}>
                Mes demandes
              </NavLink>
              <NavLink to="/received-requests" className={menuItemClass}>
                Demandes recues
              </NavLink>
              <hr />
              <button className="menu-item menu-item-danger" onClick={handleLogout}>
                Deconnexion ({user.full_name})
              </button>
            </>
          ) : (
            <>
              <NavLink to="/login" className={menuItemClass}>
                Connexion
              </NavLink>
              <Link to="/register" className="btn btn-cta">
                <PlusIcon />
                Inscription
              </Link>
            </>
          )}
        </div>
      )}
    </nav>
  );
}
