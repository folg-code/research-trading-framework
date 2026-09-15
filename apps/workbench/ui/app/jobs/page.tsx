"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Fragment, Suspense, useEffect, useRef, useState } from "react";
import { ApiError, JobSummary, cancelJob, getJob, getJobLog } from "../lib/api";

const TERMINAL_STATES: JobSummary["state"][] = [
  "SUCCEEDED",
  "FAILED",
  "CANCELLED",
  "INTERRUPTED",
];
const POLL_INTERVAL_MS = 1500;

function isTerminal(state: JobSummary["state"]): boolean {
  return TERMINAL_STATES.includes(state);
}

function JobStatusPage() {
  const jobId = useSearchParams().get("id");
  const [job, setJob] = useState<JobSummary | null>(null);
  const [log, setLog] = useState<string>("");
  const [error, setError] = useState<string | null>(null);
  const [cancelling, setCancelling] = useState(false);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (!jobId) return;

    let cancelled = false;
    async function poll() {
      try {
        const [nextJob, nextLog] = await Promise.all([
          getJob(jobId!),
          getJobLog(jobId!),
        ]);
        if (cancelled) return;
        setJob(nextJob);
        setLog(nextLog.stdout);
        if (isTerminal(nextJob.state) && pollRef.current) {
          clearInterval(pollRef.current);
          pollRef.current = null;
        }
      } catch (err) {
        if (!cancelled) setError(describeError(err));
      }
    }

    poll();
    pollRef.current = setInterval(poll, POLL_INTERVAL_MS);
    return () => {
      cancelled = true;
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [jobId]);

  async function handleCancel() {
    if (!jobId) return;
    setCancelling(true);
    try {
      setJob(await cancelJob(jobId));
    } catch (err) {
      setError(describeError(err));
    } finally {
      setCancelling(false);
    }
  }

  if (!jobId) {
    return (
      <main className="max-w-3xl mx-auto w-full px-4 py-8">
        <p className="text-gray-600">
          No job selected.{" "}
          <Link
            prefetch={false}
            href="/"
            className="text-blue-700 hover:underline"
          >
            Go home
          </Link>
          .
        </p>
      </main>
    );
  }

  return (
    <main className="max-w-3xl mx-auto w-full px-4 py-8 flex flex-col gap-6">
      <header>
        <Link
          prefetch={false}
          href="/"
          className="text-sm text-blue-700 hover:underline"
        >
          ← Home
        </Link>
        <h1 className="text-2xl font-semibold mt-1 font-mono">{jobId}</h1>
      </header>

      {error && (
        <p className="rounded border border-red-300 bg-red-50 text-red-800 px-3 py-2 text-sm">
          {error}
        </p>
      )}

      {job === null ? (
        <p className="text-gray-500 text-sm">Loading…</p>
      ) : (
        <>
          <section className="border rounded-lg bg-white p-4 flex flex-col gap-2">
            <div className="flex items-center justify-between">
              <span className="font-medium">{job.state}</span>
              {!isTerminal(job.state) && (
                <button
                  type="button"
                  onClick={handleCancel}
                  disabled={cancelling}
                  className="px-3 py-1.5 rounded border border-red-300 text-red-700 text-sm hover:bg-red-50 disabled:opacity-50"
                >
                  {cancelling ? "Cancelling…" : "Cancel"}
                </button>
              )}
            </div>
            {job.latest_phase && (
              <p className="text-sm text-gray-700">
                Phase: {job.latest_phase.name} ({job.latest_phase.index}/
                {job.latest_phase.of})
              </p>
            )}
            {job.started_at && (
              <p className="text-xs text-gray-500">
                Started {job.started_at}
                {job.finished_at ? ` · finished ${job.finished_at}` : ""}
              </p>
            )}
            {job.termination_path && (
              <p className="text-xs text-gray-500">
                Termination: {job.termination_path}
              </p>
            )}
            {job.interrupted_reason && (
              <p className="text-xs text-gray-500">{job.interrupted_reason}</p>
            )}
          </section>

          {job.state === "SUCCEEDED" && job.result && (
            <section className="border rounded-lg bg-green-50 border-green-300 p-4">
              <h2 className="font-medium text-green-900 mb-2">Result</h2>
              <dl className="text-sm text-green-900 grid grid-cols-[auto_1fr] gap-x-3 gap-y-1">
                {Object.entries(job.result).map(([key, value]) => (
                  <Fragment key={key}>
                    <dt className="font-mono text-xs text-green-700">{key}</dt>
                    <dd className="font-mono text-xs break-all">
                      {String(value)}
                    </dd>
                  </Fragment>
                ))}
              </dl>
              <p className="text-xs text-green-800 mt-2">
                Config: <span className="font-mono">{job.config_path}</span>
              </p>
            </section>
          )}

          {(job.state === "FAILED" || job.state === "INTERRUPTED") && (
            <section className="border rounded-lg bg-red-50 border-red-300 p-4 text-sm text-red-900">
              {job.state === "FAILED" && job.exit_code !== null && (
                <p>Exited with code {job.exit_code}.</p>
              )}
              {job.state === "INTERRUPTED" && <p>{job.interrupted_reason}</p>}
            </section>
          )}

          <section>
            <h2 className="font-medium text-sm mb-2">Log</h2>
            <pre className="text-xs font-mono bg-gray-900 text-gray-100 rounded-lg p-3 overflow-auto max-h-96 whitespace-pre-wrap">
              {log || "(no output yet)"}
            </pre>
          </section>
        </>
      )}
    </main>
  );
}

function describeError(err: unknown): string {
  if (err instanceof ApiError) return err.message;
  if (err instanceof Error) return err.message;
  return "an unknown error occurred";
}

export default function JobStatusPageWithSuspense() {
  return (
    <Suspense fallback={null}>
      <JobStatusPage />
    </Suspense>
  );
}
