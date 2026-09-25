import { useMutation, useQuery } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";

import { providers, requests } from "../api/endpoints";
import LocationSelect from "../components/LocationSelect";
import { Money } from "../components/domain";
import { Button, ErrorMessage, Field, PageHeader } from "../components/ui";
import { flattenAreas, useAllServices, useLocationTree } from "../hooks/useCatalogue";
import { dhakaLocalToIso, formatDate, formatTime, toDateInputValue } from "../lib/format";

const DRAFT_KEY = "shebalocal-request-draft";

const SLOTS = [
  { id: "morning", label: "Morning", start: "09:00", end: "12:00" },
  { id: "midday", label: "Midday", start: "12:00", end: "15:00" },
  { id: "afternoon", label: "Afternoon", start: "15:00", end: "18:00" },
  { id: "evening", label: "Evening", start: "18:00", end: "21:00" },
];

const STEPS = ["Service", "Where", "Problem", "When", "Who", "Confirm"];

const EMPTY = {
  serviceId: null,
  locationId: null,
  address: "",
  description: "",
  date: "",
  slot: "morning",
  targetProviderId: null,
};

function loadDraft() {
  try {
    return { ...EMPTY, ...JSON.parse(sessionStorage.getItem(DRAFT_KEY) ?? "{}") };
  } catch {
    return { ...EMPTY };
  }
}

function tomorrow() {
  return toDateInputValue(new Date(Date.now() + 24 * 60 * 60 * 1000));
}

export default function RequestService() {
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const [draft, setDraft] = useState(() => {
    const saved = loadDraft();
    const service = params.get("service");
    const provider = params.get("provider");
    return {
      ...saved,
      serviceId: service ? Number(service) : saved.serviceId,
      targetProviderId: provider ? Number(provider) : saved.targetProviderId,
      date: saved.date || tomorrow(),
    };
  });
  const [step, setStep] = useState(() => (params.get("service") ? 1 : 0));
  const [offeredProviderId] = useState(() => draft.targetProviderId);

  const { data: services } = useAllServices();
  const { data: tree } = useLocationTree();

  useEffect(() => {
    sessionStorage.setItem(DRAFT_KEY, JSON.stringify(draft));
  }, [draft]);

  const target = useQuery({
    queryKey: ["provider", String(offeredProviderId)],
    queryFn: () => providers.detail(offeredProviderId),
    enabled: Boolean(offeredProviderId),
  });

  const matches = useQuery({
    queryKey: ["provider-search", { service: draft.serviceId, location: draft.locationId }],
    queryFn: () => providers.search({ service: draft.serviceId, location: draft.locationId, page_size: 3 }),
    enabled: Boolean(draft.serviceId && draft.locationId),
  });

  const submit = useMutation({
    mutationFn: () => {
      const slot = SLOTS.find((s) => s.id === draft.slot);
      return requests.create({
        serviceId: draft.serviceId,
        locationId: draft.locationId,
        address: draft.address,
        description: draft.description,
        preferredStart: dhakaLocalToIso(draft.date, slot.start),
        preferredEnd: dhakaLocalToIso(draft.date, slot.end),
        targetProviderId: draft.targetProviderId,
      });
    },
    onSuccess: (created) => {
      sessionStorage.removeItem(DRAFT_KEY);
      navigate("/my-requests", { replace: true, state: { created: created.id } });
    },
  });

  const service = useMemo(
    () => (services ?? []).find((s) => s.id === draft.serviceId),
    [services, draft.serviceId],
  );
  const area = flattenAreas(tree).find((a) => a.id === draft.locationId);
  const slot = SLOTS.find((s) => s.id === draft.slot);
  const targetOffering = target.data?.offerings.find((o) => o.serviceId === draft.serviceId);

  function update(fields) {
    setDraft((d) => ({ ...d, ...fields }));
  }

  const canContinue = [
    Boolean(draft.serviceId),
    Boolean(draft.locationId) && draft.address.trim().length >= 5,
    draft.description.trim().length >= 10,
    Boolean(draft.date) && draft.date >= toDateInputValue(new Date()),
    true,
    true,
  ][step];

  return (
    <div className="mx-auto max-w-2xl">
      <PageHeader title="Request a service" subtitle={`Step ${step + 1} of ${STEPS.length} · ${STEPS[step]}`} />

      <ol className="mb-6 flex gap-1.5" aria-hidden="true">
        {STEPS.map((label, i) => (
          <li key={label} className={`h-1.5 flex-1 rounded-full ${i <= step ? "bg-brand-600" : "bg-slate-200"}`} />
        ))}
      </ol>

      <form
        className="card space-y-5 p-5 sm:p-6"
        onSubmit={(e) => {
          e.preventDefault();
          if (step < STEPS.length - 1) setStep(step + 1);
          else submit.mutate();
        }}
      >
        {step === 0 && (
          <Field label="What do you need done?" htmlFor="rs-service">
            <select id="rs-service" className="input" value={draft.serviceId ?? ""} onChange={(e) => update({ serviceId: Number(e.target.value) || null })} required>
              <option value="">Choose a service</option>
              {(services ?? []).map((s) => (
                <option key={s.id} value={s.id}>{s.name} — {s.categoryName}</option>
              ))}
            </select>
          </Field>
        )}

        {step === 1 && (
          <>
            <Field label="Area" htmlFor="rs-location">
              <LocationSelect id="rs-location" value={draft.locationId} onChange={(v) => update({ locationId: v })} placeholder="Choose your area" required />
            </Field>
            <Field label="Full address" htmlFor="rs-address" hint="Only shared with the provider who accepts your job.">
              <textarea id="rs-address" className="input" rows={2} value={draft.address} onChange={(e) => update({ address: e.target.value })} placeholder="House, road, flat, landmark" required />
            </Field>
          </>
        )}

        {step === 2 && (
          <Field label="Describe the problem" htmlFor="rs-description" hint="What is wrong, and anything the provider should bring. At least 10 characters.">
            <textarea id="rs-description" className="input" rows={5} value={draft.description} onChange={(e) => update({ description: e.target.value })} placeholder="e.g. The bedroom AC runs but does not cool. It is a 1.5 ton split unit." required />
          </Field>
        )}

        {step === 3 && (
          <>
            <Field label="Date" htmlFor="rs-date">
              <input id="rs-date" type="date" className="input" min={toDateInputValue(new Date())} value={draft.date} onChange={(e) => update({ date: e.target.value })} required />
            </Field>
            <fieldset>
              <legend className="label">Preferred time</legend>
              <div className="grid grid-cols-2 gap-2">
                {SLOTS.map((s) => (
                  <label key={s.id} className={`cursor-pointer rounded-xl border p-3 text-sm ${draft.slot === s.id ? "border-brand-600 bg-brand-50 text-brand-800" : "border-slate-300"}`}>
                    <input type="radio" name="slot" value={s.id} checked={draft.slot === s.id} onChange={() => update({ slot: s.id })} className="sr-only" />
                    <span className="block font-semibold">{s.label}</span>
                    <span className="text-xs">{formatTime(s.start)} – {formatTime(s.end)}</span>
                  </label>
                ))}
              </div>
            </fieldset>
          </>
        )}

        {step === 4 && (
          <fieldset className="space-y-2">
            <legend className="label">Who should see this request?</legend>
            {offeredProviderId && target.data && (
              <label className={`flex cursor-pointer gap-3 rounded-xl border p-4 ${draft.targetProviderId ? "border-brand-600 bg-brand-50" : "border-slate-300"}`}>
                <input type="radio" name="who" checked={Boolean(draft.targetProviderId)} onChange={() => update({ targetProviderId: offeredProviderId })} />
                <span>
                  <span className="block font-semibold text-ink">Only {target.data.displayName}</span>
                  <span className="text-sm text-slate-600">
                    {targetOffering ? <>Their price for this: <Money value={targetOffering.price} /></> : "They do not list this service — they may decline."}
                  </span>
                </span>
              </label>
            )}
            <label className={`flex cursor-pointer gap-3 rounded-xl border p-4 ${!draft.targetProviderId ? "border-brand-600 bg-brand-50" : "border-slate-300"}`}>
              <input type="radio" name="who" checked={!draft.targetProviderId} onChange={() => update({ targetProviderId: null })} />
              <span>
                <span className="block font-semibold text-ink">All matching providers in {area?.label ?? "your area"}</span>
                <span className="text-sm text-slate-600">
                  {matches.data ? `${matches.data.count} provider${matches.data.count === 1 ? "" : "s"} can see it. The first to accept gets the job.` : "The first provider to accept gets the job."}
                </span>
              </span>
            </label>
          </fieldset>
        )}

        {step === 5 && (
          <dl className="divide-y divide-slate-100 text-sm">
            {[
              ["Service", service?.name],
              ["Area", area?.label],
              ["Address", draft.address],
              ["Problem", draft.description],
              ["When", `${formatDate(draft.date)}, ${slot.label.toLowerCase()} (${formatTime(slot.start)}–${formatTime(slot.end)})`],
              ["Sent to", draft.targetProviderId ? target.data?.displayName : "All matching providers"],
            ].map(([k, v]) => (
              <div key={k} className="grid grid-cols-[110px_1fr] gap-2 py-2.5">
                <dt className="text-slate-500">{k}</dt>
                <dd className="whitespace-pre-line text-ink">{v}</dd>
              </div>
            ))}
          </dl>
        )}

        <ErrorMessage error={submit.error} />

        <div className="flex justify-between gap-3 pt-2">
          <Button variant="secondary" onClick={() => setStep(Math.max(0, step - 1))} disabled={step === 0}>
            Back
          </Button>
          <Button type="submit" disabled={!canContinue} loading={submit.isPending}>
            {step === STEPS.length - 1 ? "Send request" : "Continue"}
          </Button>
        </div>
      </form>
    </div>
  );
}
