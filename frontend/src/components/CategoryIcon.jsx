import PropTypes from "prop-types";

const PATHS = {
  zap: "M13 2 4.5 13.2a.6.6 0 0 0 .48.96H10l-1 8.84 8.52-11.2a.6.6 0 0 0-.48-.96H12z",
  droplet: "M12 2.7c3.6 4.2 6 7.5 6 10.5a6 6 0 0 1-12 0c0-3 2.4-6.3 6-10.5z",
  wind: "M3 8h12a3 3 0 1 0-3-3M3 12h16a3 3 0 1 1-3 3M3 16h9a2.5 2.5 0 1 1-2.5 2.5",
  monitor: "M3 4.5h18v12H3zM8.5 21h7M12 16.5V21",
  paintbrush: "M4 20c0-2 1-3.5 3-4l1.8 1.8c-.5 2-2 3-4 3zM9.7 15 19 5.7a2 2 0 0 0-2.8-2.8L7 12.2z",
  sparkles: "M12 2.5l1.7 4.6 4.6 1.7-4.6 1.7L12 15.1l-1.7-4.6L5.7 8.8l4.6-1.7zM18.5 14l.9 2.4 2.4.9-2.4.9-.9 2.4-.9-2.4-2.4-.9 2.4-.9zM5 13l.7 1.9 1.9.7-1.9.7L5 18.2l-.7-1.9-1.9-.7 1.9-.7z",
  wrench: "M15.5 3a6 6 0 0 0-5.3 8.8L3 19l2 2 7.2-7.2A6 6 0 1 0 15.5 3zm.5 2.5a3.5 3.5 0 1 1 0 7 3.5 3.5 0 0 1 0-7z",
  car: "M5 11l1.6-4.2A2 2 0 0 1 8.5 5.5h7a2 2 0 0 1 1.9 1.3L19 11M4 11h16v6h-2.5M4 17h3M7 17h10M6.5 14h1M16.5 14h1",
};

const FILLED = new Set(["zap", "droplet", "sparkles", "paintbrush", "wrench"]);

export default function CategoryIcon({ name, className = "h-6 w-6" }) {
  const d = PATHS[name] ?? PATHS.wrench;
  const filled = FILLED.has(name);

  return (
    <svg
      viewBox="0 0 24 24"
      className={className}
      fill={filled ? "currentColor" : "none"}
      stroke={filled ? "none" : "currentColor"}
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d={d} />
    </svg>
  );
}

CategoryIcon.propTypes = {
  name: PropTypes.string,
  className: PropTypes.string,
};
