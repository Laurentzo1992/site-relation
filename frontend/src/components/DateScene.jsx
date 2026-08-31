/**
 * A small animated illustration: a couple on a bench under a blossom tree
 * at sunset, with rising hearts, falling petals, twinkling stars and birds.
 * Pure inline SVG + CSS animations (see .date-scene rules in index.css) —
 * no external assets, theme-consistent with the rose/amber/plum palette.
 */
export default function DateScene() {
  return (
    <svg
      className="date-scene"
      viewBox="0 0 800 280"
      xmlns="http://www.w3.org/2000/svg"
      role="img"
      aria-label="Illustration d'un couple assis sur un banc au coucher du soleil"
    >
      <defs>
        <linearGradient id="ds-sky" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#ffe4ec" />
          <stop offset="1" stopColor="#fff3e0" />
        </linearGradient>
        <radialGradient id="ds-sun-glow" cx="0.5" cy="0.5" r="0.5">
          <stop offset="0" stopColor="#ffb454" stopOpacity="0.45" />
          <stop offset="1" stopColor="#ffb454" stopOpacity="0" />
        </radialGradient>
      </defs>

      <rect x="0" y="0" width="800" height="280" rx="24" fill="url(#ds-sky)" />

      {/* sun */}
      <circle cx="672" cy="56" r="70" fill="url(#ds-sun-glow)" />
      <circle cx="672" cy="56" r="30" fill="#ffb454" />

      {/* stars */}
      <path className="twinkle twinkle-1" d="M120 40l3 8 8 3-8 3-3 8-3-8-8-3 8-3z" fill="#ffb454" />
      <path className="twinkle twinkle-2" d="M220 70l2.4 6.4 6.4 2.4-6.4 2.4-2.4 6.4-2.4-6.4-6.4-2.4 6.4-2.4z" fill="#ff5c8a" />
      <path className="twinkle twinkle-3" d="M550 36l2 5.4 5.4 2-5.4 2-2 5.4-2-5.4-5.4-2 5.4-2z" fill="#ffb454" />

      {/* birds */}
      <path className="bird bird-1" d="M60 70q6-8 12 0q6-8 12 0" fill="none" stroke="#4a3350" strokeWidth="2.4" strokeLinecap="round" />
      <path className="bird bird-2" d="M0 0q5-7 10 0q5-7 10 0" transform="translate(300,44)" fill="none" stroke="#4a3350" strokeWidth="2.2" strokeLinecap="round" />

      {/* ground */}
      <path d="M0,232 Q200,204 400,218 T800,208 L800,280 L0,280 Z" fill="#ffeef2" />

      {/* tree */}
      <rect x="149" y="150" width="15" height="92" rx="6" fill="#a97155" />
      <g className="tree-canopy" style={{ transformOrigin: "156px 150px" }}>
        <circle cx="156" cy="103" r="42" fill="#ffe4ec" />
        <circle cx="122" cy="124" r="28" fill="#fff5f7" />
        <circle cx="190" cy="118" r="30" fill="#ffd3e2" />
        <circle cx="156" cy="76" r="26" fill="#fff3e0" />
      </g>
      <ellipse className="petal petal-1" cx="140" cy="118" rx="4" ry="6" fill="#ff5c8a" />
      <ellipse className="petal petal-2" cx="182" cy="106" rx="4" ry="6" fill="#ffb454" />
      <ellipse className="petal petal-3" cx="160" cy="140" rx="3.5" ry="5.5" fill="#ef4577" />
      <ellipse className="petal petal-4" cx="200" cy="128" rx="4" ry="6" fill="#ff5c8a" />

      {/* bench */}
      <g>
        <rect x="386" y="222" width="6" height="20" fill="#6e4530" />
        <rect x="500" y="222" width="6" height="20" fill="#6e4530" />
        <rect x="380" y="212" width="140" height="10" rx="4" fill="#a97155" />
        <rect x="380" y="228" width="140" height="7" rx="3" fill="#8a5a3c" />
      </g>

      {/* couple */}
      <g className="couple" style={{ transformOrigin: "450px 240px" }}>
        <ellipse cx="428" cy="196" rx="24" ry="30" fill="#2a1a2e" />
        <circle cx="428" cy="151" r="17" fill="#2a1a2e" />
        <path d="M411,143 Q428,120 445,143 Q439,130 428,128 Q417,130 411,143 Z" fill="#ef4577" />

        <ellipse cx="474" cy="199" rx="24" ry="30" fill="#2a1a2e" transform="rotate(-5 474 199)" />
        <circle cx="470" cy="153" r="16" fill="#2a1a2e" />
        <path d="M455,146 L470,122 L485,146 Q470,136 455,146 Z" fill="#ffb454" />

        <path
          className="pulse-heart"
          style={{ transformOrigin: "450px 132px" }}
          transform="translate(444,124) scale(0.5)"
          d="M12 21s-6.7-4.35-9.3-8.2C.9 9.9 1.7 6.3 4.8 4.9c2-.9 4.2-.3 5.6 1.3l1.6 1.8 1.6-1.8c1.4-1.6 3.6-2.2 5.6-1.3 3.1 1.4 3.9 5 2.1 7.9C18.7 16.65 12 21 12 21z"
          fill="#ff5c8a"
        />
      </g>

      {/* rising hearts */}
      {[
        { x: 360, y: 190, s: 0.42, cls: "rise-1", fill: "#ff5c8a" },
        { x: 545, y: 175, s: 0.36, cls: "rise-2", fill: "#ffb454" },
        { x: 400, y: 165, s: 0.3, cls: "rise-3", fill: "#c2255c" },
        { x: 520, y: 205, s: 0.34, cls: "rise-4", fill: "#ff5c8a" },
      ].map((h) => (
        <path
          key={h.cls}
          className={`rise-heart ${h.cls}`}
          transform={`translate(${h.x},${h.y}) scale(${h.s})`}
          d="M12 21s-6.7-4.35-9.3-8.2C.9 9.9 1.7 6.3 4.8 4.9c2-.9 4.2-.3 5.6 1.3l1.6 1.8 1.6-1.8c1.4-1.6 3.6-2.2 5.6-1.3 3.1 1.4 3.9 5 2.1 7.9C18.7 16.65 12 21 12 21z"
          fill={h.fill}
        />
      ))}
    </svg>
  );
}
