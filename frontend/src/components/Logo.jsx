import { useId } from "react";

/**
 * Brand mark: a heart formed from two converging strokes (the meeting of
 * two people) with a small sparkle to suggest the spark of a match found.
 */
export default function Logo({ size = 28 }) {
  const gradId = useId();

  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 32 32"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
    >
      <defs>
        <linearGradient id={gradId} x1="4" y1="4" x2="28" y2="28" gradientUnits="userSpaceOnUse">
          <stop offset="0" stopColor="var(--rose-500, #ff5c8a)" />
          <stop offset="1" stopColor="var(--rose-700, #c2255c)" />
        </linearGradient>
      </defs>
      <path
        d="M16 27.5s-8.6-5.4-12.2-10.2C1 13.6 2 8.9 6 7.1c2.6-1.2 5.5-.4 7.3 1.7L16 12l2.7-3.2c1.8-2.1 4.7-2.9 7.3-1.7 4 1.8 5 6.5 2.2 10.2C24.6 22.1 16 27.5 16 27.5z"
        fill={`url(#${gradId})`}
      />
      <path
        d="M25.5 3.5l1 2.6 2.6 1-2.6 1-1 2.6-1-2.6-2.6-1 2.6-1z"
        fill="var(--amber-400, #ffb454)"
      />
    </svg>
  );
}
