"use client";

import yaml from "js-yaml";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import {
  ApiError,
  DatasetSummary,
  ValidateResult,
  applyTemplate,
  listDatasets,
  listDefinitions,
  loadDefinition,
  saveDefinition,
  submitJob,
  validateDefinition,
} from "../lib/api";

const BLANK_DEFINITION = {
  research_id: "",
  research_scope: "SIGNAL_MODEL_ONLY",
  dataset_ref: "",
  time_range: { start: "", end: "" },
  horizons: ["5m"],
  signal_model: "",
};

function NewStudyPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const templateId = searchParams.get("template");
  const loadName = searchParams.get("load");

  const [yamlText, setYamlText] = useState(() => yaml.dump(BLANK_DEFINITION));
  const [datasets, setDatasets] = useState<DatasetSummary[] | null>(null);
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
    listDefinitions()
      .then((body) => setSavedDefinitions(body.definitions))
      .catch((err: unknown) => setError(describeError(err)));
  }, []);

  useEffect(() => {
    if (templateId) {
      applyTemplate(templateId, {})
        .then((body) => setYamlText(yaml.dump(body.definition)))
        .catch((err: unknown) => setError(describeError(err)));
    }
  }, [templateId]);

  useEffect(() => {
    if (loadName) {
      loadDefinition(loadName)
        .then((body) => {
          setYamlText(yaml.dump(body.definition));
          setSaveName(loadName);
        })
        .catch((err: unknown) => setError(describeError(err)));
    }
  }, [loadName]);

  function parseYamlOrNull(): Record<string, unknown> | null {
    try {
      const parsed = yaml.load(yamlText);
      if (
        parsed === null ||
        typeof parsed !== "object" ||
        Array.isArray(parsed)
      ) {
        setError("the definition must be a YAML mapping, not a list or scalar");
        return null;
      }
      return parsed as Record<string, unknown>;
    } catch (err) {
      setError(
        err instanceof Error ? `invalid YAML: ${err.message}` : "invalid YAML",
      );
      return null;
    }
  }

  function insertDatasetRef(datasetRef: string) {
    const definition = parseYamlOrNull();
    if (definition === null) return;
    definition.dataset_ref = datasetRef;
    setYamlText(yaml.dump(definition));
  }

  async function handleValidate() {
    const definition = parseYamlOrNull();
    if (definition === null) return;
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
    const definition = parseYamlOrNull();
    if (definition === null) return null;
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
      </header>

      {error && (
        <p className="rounded border border-red-300 bg-red-50 text-red-800 px-3 py-2 text-sm">
          {error}
        </p>
      )}

      <div className="grid md:grid-cols-3 gap-6">
        <div className="md:col-span-2 flex flex-col gap-3">
          <label className="font-medium text-sm">Definition (YAML)</label>
          <textarea
            value={yamlText}
            onChange={(event) => setYamlText(event.target.value)}
            spellCheck={false}
            className="font-mono text-sm border rounded-lg p-3 bg-white min-h-96 resize-y"
          />

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
                {datasets.map((dataset) => (
                  <li key={dataset.dataset_ref}>
                    <button
                      type="button"
                      onClick={() => insertDatasetRef(dataset.dataset_ref)}
                      className="text-left text-xs font-mono border rounded px-2 py-1 w-full bg-white hover:bg-gray-100"
                      title={`${dataset.row_count} rows, ${dataset.start_at} – ${dataset.end_at}`}
                    >
                      {dataset.dataset_ref}
                    </button>
                  </li>
                ))}
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
