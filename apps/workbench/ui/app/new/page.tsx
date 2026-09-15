"use client";

import yaml from "js-yaml";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useMemo, useState } from "react";
import { Tile, TilePicker } from "../components/TilePicker";
import {
  ApiError,
  DatasetSummary,
  ModelAliases,
  ValidateResult,
  applyTemplate,
  listDatasets,
  listDefinitions,
  listModels,
  listTemplates,
  loadDefinition,
  saveDefinition,
  submitJob,
  validateDefinition,
} from "../lib/api";

const BLANK_DEFINITION: Record<string, unknown> = {
  research_id: "",
  research_scope: "SIGNAL_MODEL_ONLY",
  dataset_ref: "",
  time_range: { start: "", end: "" },
  horizons: ["5m"],
  signal_model: "",
  baseline: { type: "AFTER_SIGNAL" },
};

const SCOPE_TILES: Tile[] = [
  {
    value: "SIGNAL_MODEL_ONLY",
    label: "Signal only",
    description: "Evaluate a signal model against forward outcomes",
  },
  {
    value: "MARKET_MODEL_ONLY",
    label: "Market only",
    description: "Observe a market-state model, no signal",
  },
  {
    value: "MARKET_AND_SIGNAL",
    label: "Market + signal",
    description: "A signal, in the context of a market-state model",
  },
];

const BASELINE_TILES: Tile[] = [
  {
    value: "AFTER_SIGNAL",
    label: "After signal",
    description: "Compare to the period right after a signal",
  },
  {
    value: "SIGNAL_ONLY",
    label: "Signal only",
    description: "No baseline comparison",
  },
  {
    value: "MODEL_ACTIVE",
    label: "Model active",
    description: "Compare to the market model's active windows",
  },
];

const HORIZON_PRESETS = ["1m", "5m", "15m", "30m", "1h", "4h", "1d"];

const MODEL_DESCRIPTIONS: Record<string, string> = {
  high_volatility: "Flags windows of elevated realized volatility",
  higher_low_long: "A rising sequence of swing lows",
  high_volatility_long_edge: "A volatility edge crossing on the long side",
  high_vol_and_higher_low:
    "Combines the volatility edge with the higher-low pattern",
};

function modelTiles(aliases: string[]): Tile[] {
  return aliases.map((alias) => ({
    value: alias,
    label: alias.replaceAll("_", " "),
    description: MODEL_DESCRIPTIONS[alias],
  }));
}

function asRecord(value: unknown): Record<string, unknown> {
  return value !== null && typeof value === "object" && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : {};
}

function asStringArray(value: unknown): string[] {
  return Array.isArray(value)
    ? value.filter((item): item is string => typeof item === "string")
    : [];
}

function NewStudyPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const templateId = searchParams.get("template");
  const loadName = searchParams.get("load");

  const [definition, setDefinition] =
    useState<Record<string, unknown>>(BLANK_DEFINITION);
  const [showYaml, setShowYaml] = useState(false);
  const [yamlText, setYamlText] = useState("");
  const [yamlError, setYamlError] = useState<string | null>(null);

  const [templateTiles, setTemplateTiles] = useState<Tile[] | null>(null);
  const [datasets, setDatasets] = useState<DatasetSummary[] | null>(null);
  const [models, setModels] = useState<ModelAliases | null>(null);
  const [savedDefinitions, setSavedDefinitions] = useState<string[] | null>(
    null,
  );
  const [validation, setValidation] = useState<ValidateResult | null>(null);
  const [busy, setBusy] = useState<"validate" | "save" | "run" | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [saveName, setSaveName] = useState("");

  useEffect(() => {
    listDatasets()
      .then((body) => setDatasets(body.datasets))
      .catch((err: unknown) => setError(describeError(err)));
    listModels()
      .then(setModels)
      .catch((err: unknown) => setError(describeError(err)));
    listDefinitions()
      .then((body) => setSavedDefinitions(body.definitions))
      .catch((err: unknown) => setError(describeError(err)));
    listTemplates()
      .then((body) =>
        setTemplateTiles(
          body.templates
            .filter((t) => t.status === "SUPPORTED")
            .map((t) => ({
              value: t.template_id,
              label: t.title ?? t.template_id,
              description: t.description ?? undefined,
            })),
        ),
      )
      .catch((err: unknown) => setError(describeError(err)));
  }, []);

  useEffect(() => {
    if (templateId) {
      applyTemplate(templateId, {})
        .then((body) =>
          setDefinition({ ...BLANK_DEFINITION, ...body.definition }),
        )
        .catch((err: unknown) => setError(describeError(err)));
    }
  }, [templateId]);

  useEffect(() => {
    if (loadName) {
      loadDefinition(loadName)
        .then((body) => {
          setDefinition(body.definition);
          setSaveName(loadName);
        })
        .catch((err: unknown) => setError(describeError(err)));
    }
  }, [loadName]);

  const scope =
    typeof definition.research_scope === "string"
      ? definition.research_scope
      : "";
  const showsMarket =
    scope === "MARKET_MODEL_ONLY" || scope === "MARKET_AND_SIGNAL";
  const showsSignal =
    scope === "SIGNAL_MODEL_ONLY" || scope === "MARKET_AND_SIGNAL";
  const timeRange = asRecord(definition.time_range);
  const horizons = asStringArray(definition.horizons);
  const baseline = asRecord(definition.baseline);

  const marketTiles = useMemo(
    () => modelTiles(models?.market_models ?? []),
    [models],
  );
  const signalTiles = useMemo(
    () => modelTiles(models?.signal_models ?? []),
    [models],
  );
  const horizonTiles = useMemo<Tile[]>(
    () => HORIZON_PRESETS.map((value) => ({ value, label: value })),
    [],
  );

  function setField(key: string, value: unknown) {
    setDefinition((prev) => ({ ...prev, [key]: value }));
  }

  function setScope(value: string) {
    setDefinition((prev) => {
      const next: Record<string, unknown> = { ...prev, research_scope: value };
      if (value === "SIGNAL_MODEL_ONLY") delete next.market_model;
      if (value === "MARKET_MODEL_ONLY") {
        delete next.signal_model;
        delete next.baseline;
      }
      return next;
    });
  }

  function toggleHorizon(value: string) {
    const current = asStringArray(definition.horizons);
    const next = current.includes(value)
      ? current.filter((h) => h !== value)
      : [...current, value];
    setField("horizons", next);
  }

  function openYamlView() {
    setYamlText(yaml.dump(definition));
    setYamlError(null);
    setShowYaml(true);
  }

  function closeYamlView() {
    try {
      const parsed = yaml.load(yamlText);
      if (
        parsed === null ||
        typeof parsed !== "object" ||
        Array.isArray(parsed)
      ) {
        setYamlError(
          "the definition must be a YAML mapping, not a list or scalar",
        );
        return;
      }
      setDefinition(parsed as Record<string, unknown>);
      setShowYaml(false);
      setYamlError(null);
    } catch (err) {
      setYamlError(
        err instanceof Error ? `invalid YAML: ${err.message}` : "invalid YAML",
      );
    }
  }

  async function handleValidate() {
    setError(null);
    setBusy("validate");
    try {
      setValidation(await validateDefinition(definition));
    } catch (err) {
      setError(describeError(err));
    } finally {
      setBusy(null);
    }
  }

  async function handleSave(): Promise<string | null> {
    const name = saveName.trim() || defaultName(definition);
    setError(null);
    setBusy("save");
    try {
      const saved = await saveDefinition(name, definition);
      setSaveName(saved.name);
      setSavedDefinitions((prev) =>
        Array.from(new Set([...(prev ?? []), saved.name])).sort(),
      );
      return saved.path;
    } catch (err) {
      setError(describeError(err));
      return null;
    } finally {
      setBusy(null);
    }
  }

  async function handleRun() {
    setBusy("run");
    const path = await handleSave();
    if (path === null) {
      setBusy(null);
      return;
    }
    try {
      const job = await submitJob(path);
      router.push(`/jobs?id=${encodeURIComponent(job.job_id)}`);
    } catch (err) {
      setError(describeError(err));
      setBusy(null);
    }
  }

  return (
    <main className="max-w-5xl mx-auto w-full px-4 py-8 flex flex-col gap-6">
      <header className="flex items-center justify-between">
        <div>
          <Link
            prefetch={false}
            href="/"
            className="text-sm text-blue-700 hover:underline"
          >
            ← Home
          </Link>
          <h1 className="text-2xl font-semibold mt-1">
            New Signal Research study
          </h1>
        </div>
        <button
          type="button"
          onClick={showYaml ? closeYamlView : openYamlView}
          className="text-sm text-gray-600 hover:underline"
        >
          {showYaml ? "← Back to form" : "Edit as YAML →"}
        </button>
      </header>

      {error && (
        <p className="rounded border border-red-300 bg-red-50 text-red-800 px-3 py-2 text-sm">
          {error}
        </p>
      )}

      {showYaml ? (
        <div className="flex flex-col gap-3">
          <textarea
            value={yamlText}
            onChange={(event) => setYamlText(event.target.value)}
            spellCheck={false}
            className="font-mono text-sm border rounded-lg p-3 bg-white min-h-96 resize-y"
          />
          {yamlError && <p className="text-sm text-red-700">{yamlError}</p>}
          <button
            type="button"
            onClick={closeYamlView}
            className="self-start px-3 py-1.5 rounded bg-blue-600 text-white text-sm hover:bg-blue-700"
          >
            Apply YAML
          </button>
        </div>
      ) : (
        <div className="grid md:grid-cols-3 gap-6">
          <div className="md:col-span-2 flex flex-col gap-6">
            {templateTiles && templateTiles.length > 0 && (
              <section>
                <h2 className="font-medium text-sm mb-2">
                  1. Start from a template
                </h2>
                <TilePicker
                  tiles={templateTiles}
                  selected={null}
                  onSelect={(id) =>
                    applyTemplate(id, {})
                      .then((body) =>
                        setDefinition({
                          ...BLANK_DEFINITION,
                          ...body.definition,
                        }),
                      )
                      .catch((err: unknown) => setError(describeError(err)))
                  }
                  columns={3}
                />
              </section>
            )}

            <section>
              <h2 className="font-medium text-sm mb-2">Name</h2>
              <input
                type="text"
                value={
                  typeof definition.research_id === "string"
                    ? definition.research_id
                    : ""
                }
                onChange={(event) =>
                  setField("research_id", event.target.value)
                }
                placeholder="a short name for this study"
                className="border rounded px-3 py-2 text-sm w-full max-w-sm"
              />
            </section>

            <section>
              <h2 className="font-medium text-sm mb-2">Scope</h2>
              <TilePicker
                tiles={SCOPE_TILES}
                selected={scope}
                onSelect={setScope}
                columns={3}
              />
            </section>

            {showsMarket && (
              <section>
                <h2 className="font-medium text-sm mb-2">Market model</h2>
                {models === null ? (
                  <p className="text-gray-500 text-sm">Loading…</p>
                ) : (
                  <TilePicker
                    tiles={marketTiles}
                    selected={
                      typeof definition.market_model === "string"
                        ? definition.market_model
                        : null
                    }
                    onSelect={(value) => setField("market_model", value)}
                    columns={3}
                  />
                )}
              </section>
            )}

            {showsSignal && (
              <>
                <section>
                  <h2 className="font-medium text-sm mb-2">Signal model</h2>
                  {models === null ? (
                    <p className="text-gray-500 text-sm">Loading…</p>
                  ) : (
                    <TilePicker
                      tiles={signalTiles}
                      selected={
                        typeof definition.signal_model === "string"
                          ? definition.signal_model
                          : null
                      }
                      onSelect={(value) => setField("signal_model", value)}
                      columns={3}
                    />
                  )}
                </section>

                <section>
                  <h2 className="font-medium text-sm mb-2">Baseline</h2>
                  <TilePicker
                    tiles={BASELINE_TILES}
                    selected={
                      typeof baseline.type === "string" ? baseline.type : null
                    }
                    onSelect={(value) => setField("baseline", { type: value })}
                    columns={3}
                  />
                </section>
              </>
            )}

            <section>
              <h2 className="font-medium text-sm mb-2">Horizons</h2>
              <TilePicker
                tiles={horizonTiles}
                selected={horizons}
                onSelect={toggleHorizon}
                columns={4}
              />
            </section>

            <section>
              <h2 className="font-medium text-sm mb-2">Time range</h2>
              <div className="flex items-center gap-3">
                <input
                  type="date"
                  value={
                    typeof timeRange.start === "string" ? timeRange.start : ""
                  }
                  onChange={(event) =>
                    setField("time_range", {
                      ...timeRange,
                      start: event.target.value,
                    })
                  }
                  className="border rounded px-3 py-2 text-sm"
                />
                <span className="text-gray-500 text-sm">to</span>
                <input
                  type="date"
                  value={typeof timeRange.end === "string" ? timeRange.end : ""}
                  onChange={(event) =>
                    setField("time_range", {
                      ...timeRange,
                      end: event.target.value,
                    })
                  }
                  className="border rounded px-3 py-2 text-sm"
                />
              </div>
            </section>

            <div className="flex flex-wrap items-center gap-2">
              <input
                type="text"
                placeholder="save as…"
                value={saveName}
                onChange={(event) => setSaveName(event.target.value)}
                className="border rounded px-2 py-1 text-sm"
              />
              <button
                type="button"
                onClick={handleSave}
                disabled={busy !== null}
                className="px-3 py-1.5 rounded border text-sm hover:bg-gray-100 disabled:opacity-50"
              >
                Save
              </button>
              <button
                type="button"
                onClick={handleValidate}
                disabled={busy !== null}
                className="px-3 py-1.5 rounded border text-sm hover:bg-gray-100 disabled:opacity-50"
              >
                Validate
              </button>
              <button
                type="button"
                onClick={handleRun}
                disabled={busy !== null}
                className="px-3 py-1.5 rounded bg-blue-600 text-white text-sm hover:bg-blue-700 disabled:opacity-50"
              >
                {busy === "run" ? "Starting…" : "Run"}
              </button>
            </div>

            {validation && (
              <div
                className={`rounded border px-3 py-2 text-sm ${
                  validation.ok
                    ? "border-green-300 bg-green-50 text-green-900"
                    : "border-red-300 bg-red-50 text-red-900"
                }`}
              >
                {validation.ok ? (
                  <>
                    <p className="font-medium">Resolves.</p>
                    <pre className="text-xs mt-1 whitespace-pre-wrap">
                      {JSON.stringify(validation.plan, null, 2)}
                    </pre>
                  </>
                ) : (
                  <>
                    <p className="font-medium">
                      {validation.error_type ?? "Error"}
                    </p>
                    <p className="text-xs mt-1 whitespace-pre-wrap">
                      {validation.error_message}
                    </p>
                  </>
                )}
              </div>
            )}
          </div>

          <div className="flex flex-col gap-6">
            <section>
              <h2 className="font-medium text-sm mb-2">Published datasets</h2>
              {datasets === null ? (
                <p className="text-gray-500 text-sm">Loading…</p>
              ) : datasets.length === 0 ? (
                <p className="text-gray-500 text-sm">None published yet.</p>
              ) : (
                <ul className="flex flex-col gap-1">
                  {datasets.map((dataset) => {
                    const active =
                      definition.dataset_ref === dataset.dataset_ref;
                    return (
                      <li key={dataset.dataset_ref}>
                        <button
                          type="button"
                          onClick={() =>
                            setField("dataset_ref", dataset.dataset_ref)
                          }
                          className={`text-left text-xs font-mono border rounded px-2 py-1 w-full ${
                            active
                              ? "border-blue-600 bg-blue-50 ring-1 ring-blue-600"
                              : "bg-white hover:bg-gray-100"
                          }`}
                          title={`${dataset.row_count} rows, ${dataset.start_at} – ${dataset.end_at}`}
                        >
                          {dataset.dataset_ref}
                        </button>
                      </li>
                    );
                  })}
                </ul>
              )}
            </section>

            <section>
              <h2 className="font-medium text-sm mb-2">Saved definitions</h2>
              {savedDefinitions === null ? (
                <p className="text-gray-500 text-sm">Loading…</p>
              ) : savedDefinitions.length === 0 ? (
                <p className="text-gray-500 text-sm">None saved yet.</p>
              ) : (
                <ul className="flex flex-col gap-1">
                  {savedDefinitions.map((name) => (
                    <li key={name}>
                      <Link
                        prefetch={false}
                        href={`/new?load=${encodeURIComponent(name)}`}
                        className="text-xs font-mono border rounded px-2 py-1 block bg-white hover:bg-gray-100"
                      >
                        {name}
                      </Link>
                    </li>
                  ))}
                </ul>
              )}
            </section>
          </div>
        </div>
      )}
    </main>
  );
}

function defaultName(definition: Record<string, unknown>): string {
  const researchId = definition.research_id;
  if (typeof researchId === "string" && researchId.trim()) {
    return researchId.trim();
  }
  return `study-${Date.now()}`;
}

function describeError(err: unknown): string {
  if (err instanceof ApiError) return err.message;
  if (err instanceof Error) return err.message;
  return "an unknown error occurred";
}

export default function NewStudyPageWithSuspense() {
  // useSearchParams requires a Suspense boundary, static export included.
  return (
    <Suspense fallback={null}>
      <NewStudyPage />
    </Suspense>
  );
}
