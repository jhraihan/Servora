export const CATEGORY_THEME = {
  electrical: {
    accent: "#92400e",
    tint: "#fef3c7",
    gradient: "from-amber-400 via-orange-400 to-amber-500",
    ring: "ring-amber-300",
    glow: "shadow-amber-500/25",
  },
  plumbing: {
    accent: "#0e4f7a",
    tint: "#dbeafe",
    gradient: "from-sky-400 via-blue-500 to-indigo-500",
    ring: "ring-sky-300",
    glow: "shadow-sky-500/25",
  },
  "ac-refrigeration": {
    accent: "#0e5f6b",
    tint: "#cffafe",
    gradient: "from-cyan-300 via-teal-400 to-cyan-500",
    ring: "ring-cyan-300",
    glow: "shadow-cyan-500/25",
  },
  "computer-it": {
    accent: "#3730a3",
    tint: "#e0e7ff",
    gradient: "from-indigo-400 via-violet-500 to-indigo-600",
    ring: "ring-indigo-300",
    glow: "shadow-indigo-500/25",
  },
  painting: {
    accent: "#9d174d",
    tint: "#fce7f3",
    gradient: "from-pink-400 via-rose-400 to-fuchsia-500",
    ring: "ring-pink-300",
    glow: "shadow-pink-500/25",
  },
  cleaning: {
    accent: "#5b21b6",
    tint: "#ede9fe",
    gradient: "from-violet-400 via-purple-500 to-violet-600",
    ring: "ring-violet-300",
    glow: "shadow-violet-500/25",
  },
  "appliance-repair": {
    accent: "#9a3412",
    tint: "#ffedd5",
    gradient: "from-orange-400 via-red-400 to-orange-500",
    ring: "ring-orange-300",
    glow: "shadow-orange-500/25",
  },
  "car-mechanic": {
    accent: "#164e63",
    tint: "#cffafe",
    gradient: "from-teal-400 via-cyan-500 to-sky-600",
    ring: "ring-teal-300",
    glow: "shadow-teal-500/25",
  },
};

export const DEFAULT_THEME = {
  accent: "#2c5a31",
  tint: "#dcecdc",
  gradient: "from-brand-500 via-brand-600 to-brand-700",
  ring: "ring-brand-300",
  glow: "shadow-brand-600/25",
};

export function categoryTheme(slug) {
  return CATEGORY_THEME[slug] ?? DEFAULT_THEME;
}
