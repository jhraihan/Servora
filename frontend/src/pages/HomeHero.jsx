import PropTypes from "prop-types";

export default function HomeHero({ children }) {
  return (
    <section className="on-dark surface-forest relative overflow-hidden rounded-4xl px-5 py-12 sm:px-10 sm:py-16">
      <div aria-hidden="true" className="pointer-events-none absolute -top-24 -right-16 h-64 w-64 rounded-full bg-brand-300/20 blur-3xl" />
      <div aria-hidden="true" className="pointer-events-none absolute -bottom-28 -left-12 h-72 w-72 rounded-full bg-brand-500/20 blur-3xl" />
      <div className="relative">
        <p className="inline-flex items-center gap-2 rounded-full border border-white/25 bg-white/10 px-3 py-1.5 text-xs font-semibold tracking-wide text-white/90 uppercase backdrop-blur-xl">
          Dhaka&apos;s verified tradespeople
        </p>
        <h1 className="mt-4 max-w-2xl text-4xl font-bold leading-[1.1] tracking-tight sm:text-6xl">
          Find a technician you can actually trust.
        </h1>
        <p className="mt-4 max-w-xl text-base text-brand-100 sm:text-lg">
          Electricians, plumbers, AC technicians and more — ranked by what they have really done, not by who shouts loudest.
        </p>
        {children}
      </div>
    </section>
  );
}

HomeHero.propTypes = { children: PropTypes.node };
