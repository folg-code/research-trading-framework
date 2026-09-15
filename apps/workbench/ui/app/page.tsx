"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import {
  ApiError,
  JobSummary,
  TemplateSummary,
  listJobs,
  listTemplates,
} from "./lib/api";

function StateBadge({ state }: { state: JobSummary["state"] }) {
  const color: Record<JobSummary["state"], string> = {
    QUEUED: "bg-gray-200 text-gray-800",
    RUNNING: "bg-blue-100 text-blue-800",
    SUCCEEDED: "bg-green-100 text-green-800",
    FAILED: "bg-red-100 text-red-800",
    CANCELLED: "bg-yellow-100 text-yellow-800",
    INTERRUPTED: "bg-orange-100 text-orange-800",
  };
  return (
    <span className={`px-2 py-0.5 rounded text-xs font-medium ${color[state]}`}>
      {state}
    </span>
  );
}

export default function HomePage() {
  const [templates, setTemplates] = useState<TemplateSummary[] | null>(null);
  const [jobs, setJobs] = useState<JobSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listTemplates()
      .then((body) => setTemplates(body.templates))
      .catch((err: unknown) => setError(describeError(err)));
    listJobs()
      .then((body) => setJobs([...body.jobs].reverse()))
      .catch((err: unknown) => setError(describeError(err)));
  }, []);

  return (
    <main className="max-w-4xl mx-auto w-full px-4 py-8 flex flex-col gap-8">
      <header>
        <h1 className="text-2xl font-semibold">Research Workbench</h1>
        <p className="text-gray-600 mt-1">
          Configure and run Market & Signal Studies without a terminal.
        </p>
      </header>

      {error && (
        <p className="rounded border border-red-300 bg-red-50 text-red-800 px-3 py-2 text-sm">
          {error}
        </p>
      )}

      <section>
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-lg font-medium">Start a Market & Signal Study</h2>
        </div>
        {templates === null ? (
          <p className="text-gray-500 text-sm">Loading templates…</p>
        ) : templates.length === 0 ? (
          <p className="text-gray-500 text-sm">No templates found.</p>
        ) : (
          <ul className="grid gap-3 sm:grid-cols-2">
            {templates.map((template) => (
              <li
                key={`${template.source}:${template.template_id}`}
                className="border rounded-lg p-4 bg-white flex flex-col gap-2"
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="font-medium">
                    {template.title ?? template.template_id}
                  </span>
                  <span className="text-xs text-gray-500">
                    {template.source}
                  </span>
                </div>
                <p className="text-sm text-gray-600">{template.description}</p>
                {template.status !== "SUPPORTED" ? (
                  <p className="text-xs text-amber-700">
                    {template.status}: {template.reason}
                  </p>
                ) : (
                  <Link
                    prefetch={false}
                    href={`/new?template=${encodeURIComponent(template.template_id)}`}
                    className="text-sm text-blue-700 hover:underline mt-1"
                  >
                    Use this template →
                  </Link>
                )}
              </li>
            ))}
          </ul>
        )}
        <Link
          prefetch={false}
          href="/new"
          className="inline-block mt-3 text-sm text-blue-700 hover:underline"
        >
          Or start from a blank definition →
        </Link>
      </section>

      <section>
        <h2 className="text-lg font-medium mb-3">Recent jobs</h2>
        {jobs === null ? (
          <p className="text-gray-500 text-sm">Loading jobs…</p>
        ) : jobs.length === 0 ? (
          <p className="text-gray-500 text-sm">No jobs submitted yet.</p>
        ) : (
          <ul className="divide-y border rounded-lg bg-white">
            {jobs.map((job) => (
              <li
                key={job.job_id}
                className="px-4 py-3 flex items-center justify-between gap-3"
              >
                <div className="flex flex-col">
                  <Link
                    prefetch={false}
                    href={`/jobs?id=${encodeURIComponent(job.job_id)}`}
                    className="font-mono text-sm text-blue-700 hover:underline"
                  >
                    {job.job_id}
                  </Link>
                  <span className="text-xs text-gray-500">
                    {job.latest_phase
                      ? `${job.latest_phase.name} (${job.latest_phase.index}/${job.latest_phase.of})`
                      : job.job_kind}
                  </span>
                </div>
                <StateBadge state={job.state} />
              </li>
            ))}
          </ul>
        )}
      </section>
    </main>
  );
}

function describeError(err: unknown): string {
  if (err instanceof ApiError) return err.message;
  if (err instanceof Error) return err.message;
  return "an unknown error occurred";
}
