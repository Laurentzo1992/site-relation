import Logo from "./Logo";

export default function Footer() {
  return (
    <footer className="footer">
      <div className="footer-brand">
        <Logo size={20} />
        <strong>Trouver votre Amour</strong>
      </div>
      <p>Des connexions sincères, des coordonnées toujours protégées.</p>
    </footer>
  );
}
