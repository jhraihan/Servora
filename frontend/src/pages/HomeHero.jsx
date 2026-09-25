import PropTypes from "prop-types";

export default function HomeHero({ children }) {
  return (
    <section className="overflow-hidden rounded-3xl bg-gradient-to-br from-brand-800 to-brand-600 px-5 py-10 text-white sm:px-10 sm:py-14">
      <p className="text-sm font-semibold uppercase tracking-wider text-brand-100">Dhaka&apos;s verified tradespeople</p>
      <h1 className="mt-2 max-w-2xl text-3xl font-bold leading-tight sm:text-5xl">
        Find a technician you can actually trust.
      </h1>
      <p className="mt-3 max-w-xl text-brand-100">
        Electricians, plumbers, AC technicians and more — ranked by what they have really done, not by who shouts loudest.
      </p>
      {children}
    </section>
  );
}

HomeHero.propTypes = { children: PropTypes.node };
