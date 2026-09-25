import PropTypes from "prop-types";
import { useEffect, useState } from "react";
import { Link, NavLink, Navigate, Outlet, useLocation, useNavigate } from "react-router-dom";

import { ROLE } from "../constants/domain";
import { useSession } from "../hooks/useSession";
import { useCompareStore } from "../store/compare";

const CUSTOMER_LINKS = [
  { to: "/services", label: "Find services" },
  { to: "/my-requests", label: "My requests" },
  { to: "/my-bookings", label: "My bookings" },
];

const PROVIDER_LINKS = [
  { to: "/provider/dashboard", label: "Dashboard" },
  { to: "/provider/bookings", label: "Jobs" },
  { to: "/provider/earnings", label: "Earnings" },
  { to: "/provider/trust", label: "Trust" },
  { to: "/provider/profile", label: "Profile" },
];

const GUEST_LINKS = [
  { to: "/services", label: "Find services" },
  { to: "/providers", label: "Browse providers" },
];

function navClass({ isActive }) {
  return [
    "block rounded-lg px-3 py-2 text-sm font-medium",
    isActive ? "bg-brand-50 text-brand-800" : "text-slate-700 hover:bg-slate-100",
  ].join(" ");
}

export default function Layout() {
  const { user, isAuthenticated, isProvider, logout, switchRole } = useSession();
  const compareCount = useCompareStore((s) => s.ids.length);
  const [open, setOpen] = useState(false);
  const location = useLocation();
  const navigate = useNavigate();

  useEffect(() => {
    setOpen(false);
  }, [location.pathname]);

  const links = !isAuthenticated ? GUEST_LINKS : isProvider ? PROVIDER_LINKS : CUSTOMER_LINKS;
  const otherRole = isProvider ? ROLE.CUSTOMER : ROLE.PROVIDER;
  const canSwitch = user?.roles?.includes(otherRole);

  async function handleSwitch() {
    await switchRole(otherRole);
    navigate(otherRole === ROLE.PROVIDER ? "/provider/dashboard" : "/");
  }

  async function handleLogout() {
    await logout();
    navigate("/");
  }

  return (
    <div className="flex min-h-screen flex-col">
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:fixed focus:top-3 focus:left-3 focus:z-50 focus:rounded-lg focus:bg-brand-700 focus:px-4 focus:py-2 focus:text-sm focus:font-semibold focus:text-white"
      >
        Skip to main content
      </a>
      <header className="sticky top-0 z-30 border-b border-slate-200 bg-white/95 backdrop-blur">
        <div className="mx-auto flex h-16 max-w-6xl items-center justify-between gap-4 px-4">
          <Link to={isProvider ? "/provider/dashboard" : "/"} className="flex items-center gap-2">
            <img src="/favicon.svg" alt="" className="h-8 w-8" />
            <span className="text-lg font-bold tracking-tight text-ink">
              Sheba<span className="text-brand-700">Local</span>
            </span>
          </Link>

          <nav className="hidden items-center gap-1 md:flex" aria-label="Main">
            {links.map((l) => (
              <NavLink key={l.to} to={l.to} className={navClass}>
                {l.label}
              </NavLink>
            ))}
            {!isProvider && compareCount > 0 && (
              <NavLink to="/compare" className={navClass}>
                Compare ({compareCount})
              </NavLink>
            )}
          </nav>

          <div className="hidden items-center gap-2 md:flex">
            <AccountActions
              isAuthenticated={isAuthenticated}
              name={user?.fullName}
              canSwitch={canSwitch}
              otherRole={otherRole}
              onSwitch={handleSwitch}
              onLogout={handleLogout}
            />
          </div>

          <button
            type="button"
            className="rounded-lg p-2 text-slate-700 hover:bg-slate-100 md:hidden"
            onClick={() => setOpen((v) => !v)}
            aria-expanded={open}
            aria-controls="mobile-menu"
            aria-label="Menu"
          >
            <svg viewBox="0 0 24 24" className="h-6 w-6" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
              {open ? <path d="M6 6l12 12M18 6L6 18" /> : <path d="M4 7h16M4 12h16M4 17h16" />}
            </svg>
          </button>
        </div>

        {open && (
          <div id="mobile-menu" className="border-t border-slate-200 bg-white px-4 py-3 md:hidden">
            <nav className="flex flex-col gap-1" aria-label="Mobile">
              {links.map((l) => (
                <NavLink key={l.to} to={l.to} className={navClass}>
                  {l.label}
                </NavLink>
              ))}
              {!isProvider && compareCount > 0 && (
                <NavLink to="/compare" className={navClass}>
                  Compare ({compareCount})
                </NavLink>
              )}
            </nav>
            <div className="mt-3 flex flex-col gap-2 border-t border-slate-100 pt-3">
              <AccountActions
                isAuthenticated={isAuthenticated}
                name={user?.fullName}
                canSwitch={canSwitch}
                otherRole={otherRole}
                onSwitch={handleSwitch}
                onLogout={handleLogout}
              />
            </div>
          </div>
        )}
      </header>

      <main id="main" tabIndex={-1} className="mx-auto w-full max-w-6xl flex-1 px-4 py-6 focus:outline-none sm:py-10">
        <Outlet />
      </main>

      <footer className="border-t border-slate-200 bg-white">
        <div className="mx-auto max-w-6xl px-4 py-6 text-xs text-slate-500">
          ShebaLocal · Verified local services in Dhaka · Trust scores are computed from recorded jobs, not self-reported.
        </div>
      </footer>
    </div>
  );
}

function AccountActions({ isAuthenticated, name, canSwitch, otherRole, onSwitch, onLogout }) {
  if (!isAuthenticated) {
    return (
      <>
        <Link to="/login" className="rounded-xl px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-100">
          Log in
        </Link>
        <Link to="/register" className="rounded-xl bg-brand-700 px-4 py-2 text-center text-sm font-semibold text-white hover:bg-brand-800">
          Sign up
        </Link>
      </>
    );
  }

  return (
    <>
      <span className="truncate px-1 text-sm text-slate-600">{name}</span>
      {canSwitch && (
        <button type="button" onClick={onSwitch} className="rounded-xl border border-slate-300 px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50">
          Switch to {otherRole}
        </button>
      )}
      <button type="button" onClick={onLogout} className="rounded-xl px-3 py-2 text-sm font-medium text-slate-600 hover:bg-slate-100">
        Log out
      </button>
    </>
  );
}

AccountActions.propTypes = {
  isAuthenticated: PropTypes.bool.isRequired,
  name: PropTypes.string,
  canSwitch: PropTypes.bool,
  otherRole: PropTypes.string.isRequired,
  onSwitch: PropTypes.func.isRequired,
  onLogout: PropTypes.func.isRequired,
};

export function RequireRole({ role, children }) {
  const { isAuthenticated, user } = useSession();
  const location = useLocation();

  if (!isAuthenticated) {
    return <Navigate to="/login" replace state={{ from: location.pathname + location.search }} />;
  }
  if (role && user?.activeRole !== role) {
    if (user?.roles?.includes(role)) {
      return <SwitchPrompt role={role} />;
    }
    return <Navigate to={user?.activeRole === ROLE.PROVIDER ? "/provider/dashboard" : "/"} replace />;
  }
  return children;
}

RequireRole.propTypes = {
  role: PropTypes.oneOf(Object.values(ROLE)),
  children: PropTypes.node.isRequired,
};

function SwitchPrompt({ role }) {
  const { switchRole } = useSession();
  return (
    <div className="card mx-auto max-w-md p-6 text-center">
      <p className="font-semibold text-ink">This page is for your {role} account.</p>
      <button
        type="button"
        onClick={() => switchRole(role)}
        className="mt-4 rounded-xl bg-brand-700 px-4 py-2 text-sm font-semibold text-white"
      >
        Switch to {role}
      </button>
    </div>
  );
}

SwitchPrompt.propTypes = { role: PropTypes.string.isRequired };
