import { useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";

import { auth } from "../api/endpoints";
import { Button, ErrorMessage, Field } from "../components/ui";
import { ROLE } from "../constants/domain";
import { useSession } from "../hooks/useSession";

function landingFor(user, from) {
  if (from) return from;
  return user.activeRole === ROLE.PROVIDER ? "/provider/dashboard" : "/";
}

export function Login() {
  const { login } = useSession();
  const navigate = useNavigate();
  const location = useLocation();
  const [phone, setPhone] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  async function submit(event) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const user = await login({ phone, password });
      navigate(landingFor(user, location.state?.from), { replace: true });
    } catch (err) {
      setError(err.status === 401 ? "That phone number and password do not match." : err);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto max-w-md">
      <div className="card p-6 sm:p-8">
        <h1 className="page-title">Welcome back</h1>
        <p className="mt-1 text-sm text-slate-600">Log in with your phone number or email.</p>
        <form onSubmit={submit} className="mt-6 space-y-4">
          <Field label="Phone number or email" htmlFor="login-phone">
            <input id="login-phone" className="input" autoComplete="username" inputMode="tel" placeholder="01712 345678" value={phone} onChange={(e) => setPhone(e.target.value)} required />
          </Field>
          <Field label="Password" htmlFor="login-password">
            <input id="login-password" type="password" className="input" autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} required />
          </Field>
          <ErrorMessage error={error} />
          <Button type="submit" size="lg" loading={busy} className="w-full">Log in</Button>
        </form>
        <p className="mt-6 text-center text-sm text-slate-600">
          New to ShebaLocal? <Link to="/register" className="font-semibold text-brand-700">Create an account</Link>
        </p>
      </div>
    </div>
  );
}

export function Register() {
  const { login } = useSession();
  const navigate = useNavigate();
  const [step, setStep] = useState("details");
  const [form, setForm] = useState({ fullName: "", phone: "", password: "", role: ROLE.CUSTOMER });
  const [code, setCode] = useState("");
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  function set(key) {
    return (e) => setForm((f) => ({ ...f, [key]: e.target.value }));
  }

  async function signIn() {
    const user = await login({ phone: form.phone, password: form.password });
    navigate(user.activeRole === ROLE.PROVIDER ? "/provider/profile" : "/", { replace: true });
  }

  async function submitDetails(event) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const result = await auth.register(form);
      setForm((f) => ({ ...f, phone: result.user.phone }));
      setStep("verify");
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }

  async function submitCode(event) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await auth.verifyOtp({ phone: form.phone, code });
      await signIn();
    } catch (err) {
      setError(err);
      setBusy(false);
    }
  }

  async function skip() {
    setBusy(true);
    try {
      await signIn();
    } catch (err) {
      setError(err);
      setBusy(false);
    }
  }

  if (step === "verify") {
    return (
      <div className="mx-auto max-w-md">
        <div className="card p-6 sm:p-8">
          <h1 className="page-title">Verify your phone</h1>
          <p className="mt-1 text-sm text-slate-600">We sent a 6-digit code to {form.phone}. It expires in 5 minutes.</p>
          <form onSubmit={submitCode} className="mt-6 space-y-4">
            <Field label="Verification code" htmlFor="otp-code">
              <input id="otp-code" className="input text-center text-2xl tracking-[0.5em]" inputMode="numeric" autoComplete="one-time-code" maxLength={6} pattern="\d{6}" value={code} onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))} required />
            </Field>
            <ErrorMessage error={error} />
            <Button type="submit" size="lg" loading={busy} className="w-full">Verify and continue</Button>
          </form>
          <div className="mt-4 flex justify-between text-sm">
            <button type="button" className="font-semibold text-brand-700" onClick={() => auth.sendOtp(form.phone).catch(setError)}>
              Send a new code
            </button>
            <button type="button" className="text-slate-500 hover:text-slate-700" onClick={skip} disabled={busy}>
              Skip for now
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-md">
      <div className="card p-6 sm:p-8">
        <h1 className="page-title">Create your account</h1>
        <form onSubmit={submitDetails} className="mt-6 space-y-4">
          <fieldset>
            <legend className="label">I want to</legend>
            <div className="grid grid-cols-2 gap-2">
              {[
                [ROLE.CUSTOMER, "Hire a provider"],
                [ROLE.PROVIDER, "Offer my services"],
              ].map(([role, label]) => (
                <label key={role} className={`cursor-pointer rounded-xl border p-3 text-center text-sm font-medium ${form.role === role ? "border-brand-600 bg-brand-50 text-brand-800" : "border-slate-300 text-slate-700"}`}>
                  <input type="radio" name="role" value={role} checked={form.role === role} onChange={set("role")} className="sr-only" />
                  {label}
                </label>
              ))}
            </div>
          </fieldset>
          <Field label="Full name" htmlFor="reg-name">
            <input id="reg-name" className="input" autoComplete="name" value={form.fullName} onChange={set("fullName")} required />
          </Field>
          <Field label="Mobile number" htmlFor="reg-phone" error={error?.fieldError?.("phone")} hint="Bangladeshi number, e.g. 01712 345678">
            <input id="reg-phone" className="input" inputMode="tel" autoComplete="tel" value={form.phone} onChange={set("phone")} required />
          </Field>
          <Field label="Password" htmlFor="reg-password" error={error?.fieldError?.("password")} hint="At least 8 characters">
            <input id="reg-password" type="password" className="input" autoComplete="new-password" minLength={8} value={form.password} onChange={set("password")} required />
          </Field>
          {error && !error.fieldError?.("phone") && !error.fieldError?.("password") && <ErrorMessage error={error} />}
          <Button type="submit" size="lg" loading={busy} className="w-full">Create account</Button>
        </form>
        <p className="mt-6 text-center text-sm text-slate-600">
          Already have an account? <Link to="/login" className="font-semibold text-brand-700">Log in</Link>
        </p>
      </div>
    </div>
  );
}
