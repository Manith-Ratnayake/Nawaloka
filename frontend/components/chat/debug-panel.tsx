"use client";

import { useState } from "react";
import { cn } from "@/lib/utils";

type ChunkPreview = {
  id?: string;
  rerank_score?: number | null;
  source?: string;
  content_preview?: string;
};

type PerQueryDebug = {
  query: string;
  chunks_retrieved: number;
  chunks?: ChunkPreview[];
};

type PerQueryRerankDebug = {
  query: string;
  reranked_count: number;
  chunks?: ChunkPreview[];
};

type VectorStepDebug = {
  total_unique_chunks_before_rerank?: number;
  per_query?: PerQueryDebug[];
  per_query_rerank?: PerQueryRerankDebug[];
  reranked_chunks?: ChunkPreview[];
  context_length?: number;
};

type SqlAttempt = {
  sql: string | null;
  error: string | null;
  row_count?: number;
};

type SqlStepDebug = {
  attempts?: SqlAttempt[];
  result?: string;
};

type DebugTrace = {
  cache?: "hit";
  step1_router?: {
    plan?: {
      use_vector?: boolean;
      use_sql?: boolean;
      vector_question?: string;
      sql_question?: string;
    };
  };
  step2_query_agent?: {
    queries?: string[];
    skipped?: boolean;
  };
  step3_search?: {
    vector?: VectorStepDebug;
    sql?: SqlStepDebug;
  };
  step4_answer?: {
    vector_context_chars?: number;
    sql_context_chars?: number;
    answer_chars?: number;
  };
};

function Chevron({ open }: { open: boolean }) {
  return (
    <span className={cn("inline-block transition-transform", open && "rotate-180")}>
      ▾
    </span>
  );
}

function CollapsibleSection({
  title,
  meta,
  defaultOpen = false,
  nested = false,
  children,
}: {
  title: string;
  meta?: string;
  defaultOpen?: boolean;
  nested?: boolean;
  children: React.ReactNode;
}) {
  const [open, setOpen] = useState(defaultOpen);

  return (
    <div
      className={cn(
        "overflow-hidden rounded-md border border-border/40",
        nested ? "bg-background/40" : "bg-background/60"
      )}
    >
      <button
        className="flex w-full items-center justify-between px-2.5 py-1.5 text-left text-muted-foreground text-xs hover:text-foreground"
        onClick={() => setOpen((v) => !v)}
        type="button"
      >
        <span className="flex min-w-0 items-baseline gap-2">
          <span className="truncate font-medium">{title}</span>
          {meta && (
            <span className="shrink-0 text-[10px] text-muted-foreground/80">
              {meta}
            </span>
          )}
        </span>
        <Chevron open={open} />
      </button>

      {open && (
        <div className="space-y-1.5 border-border/40 border-t px-2.5 py-2">
          {children}
        </div>
      )}
    </div>
  );
}

function ChunkList({ chunks }: { chunks?: ChunkPreview[] }) {
  if (!chunks || chunks.length === 0) {
    return <div className="text-muted-foreground">No chunks.</div>;
  }

  return (
    <div className="space-y-1.5">
      {chunks.map((chunk, i) => (
        <div
          className="rounded border border-border/40 bg-background/60 p-1.5"
          key={chunk.id ?? i}
        >
          <div className="flex items-baseline justify-between gap-2">
            <span className="truncate text-foreground/80">
              {chunk.source || chunk.id}
            </span>
            {typeof chunk.rerank_score === "number" && (
              <span className="shrink-0 rounded bg-muted px-1.5 py-0.5 text-[10px] text-foreground/80">
                score {chunk.rerank_score.toFixed(3)}
              </span>
            )}
          </div>
          {chunk.content_preview && (
            <div className="mt-0.5 line-clamp-2 text-muted-foreground">
              {chunk.content_preview}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

export function DebugPanel({ data }: { data: unknown }) {
  const [open, setOpen] = useState(false);
  const trace = data as DebugTrace;

  const plan = trace?.step1_router?.plan;
  const subqueries = trace?.step2_query_agent?.queries;
  const vectorDebug = trace?.step3_search?.vector;
  const sqlDebug = trace?.step3_search?.sql;
  const answerStats = trace?.step4_answer;

  return (
    <div className="w-[min(100%,560px)] overflow-hidden rounded-lg border border-border/50 bg-muted/30 text-[12px]">
      <button
        className="flex w-full items-center justify-between px-3 py-2 text-left text-muted-foreground text-xs hover:text-foreground"
        onClick={() => setOpen((v) => !v)}
        type="button"
      >
        <span>Pipeline trace</span>
        <Chevron open={open} />
      </button>

      {open && (
        <div className="space-y-2 border-border/50 border-t px-3 py-2.5">
          {trace?.cache === "hit" && (
            <div className="flex items-center gap-2 rounded-md border border-border/40 bg-background/60 px-2.5 py-2 text-xs text-foreground/80">
              <span className="text-green-500">⚡</span>
              <span>Cache hit — answered from FAQ cache, pipeline skipped</span>
            </div>
          )}

          {plan && (
            <CollapsibleSection defaultOpen title="Router">
              <div className="text-foreground/90">
                use_vector: {String(plan.use_vector)} · use_sql:{" "}
                {String(plan.use_sql)}
              </div>
              {plan.vector_question && (
                <div className="text-muted-foreground">
                  vector_question: “{plan.vector_question}”
                </div>
              )}
              {plan.sql_question && plan.use_sql && (
                <div className="text-muted-foreground">
                  sql_question: “{plan.sql_question}”
                </div>
              )}
            </CollapsibleSection>
          )}

          {subqueries && subqueries.length > 0 && (
            <CollapsibleSection
              defaultOpen
              meta={`${subqueries.length}`}
              title="Query agent — subqueries"
            >
              <ul className="list-disc space-y-0.5 pl-4">
                {subqueries.map((q) => (
                  <li className="text-foreground/90" key={q}>
                    {q}
                  </li>
                ))}
              </ul>
            </CollapsibleSection>
          )}

          {vectorDebug?.per_query && vectorDebug.per_query.length > 0 && (
            <CollapsibleSection
              meta={`${vectorDebug.total_unique_chunks_before_rerank ?? 0} unique`}
              title="Retrieval"
            >
              {vectorDebug.per_query.map((pq) => (
                <CollapsibleSection
                  key={pq.query}
                  meta={`${pq.chunks_retrieved} chunks`}
                  nested
                  title={pq.query}
                >
                  <ChunkList chunks={pq.chunks} />
                </CollapsibleSection>
              ))}
            </CollapsibleSection>
          )}

          {vectorDebug?.per_query_rerank &&
            vectorDebug.per_query_rerank.length > 0 && (
              <CollapsibleSection title="Reranking (per subquery)">
                {vectorDebug.per_query_rerank.map((pq) => (
                  <CollapsibleSection
                    key={pq.query}
                    meta={`${pq.reranked_count} kept`}
                    nested
                    title={pq.query}
                  >
                    <ChunkList chunks={pq.chunks} />
                  </CollapsibleSection>
                ))}
              </CollapsibleSection>
            )}

          {vectorDebug?.reranked_chunks &&
            vectorDebug.reranked_chunks.length > 0 && (
              <CollapsibleSection
                defaultOpen
                meta={`${vectorDebug.reranked_chunks.length} chunks`}
                title="Final chunks used for answer"
              >
                <ChunkList chunks={vectorDebug.reranked_chunks} />
              </CollapsibleSection>
            )}

          {sqlDebug && (
            <CollapsibleSection title="SQL search">
              <div className="text-muted-foreground">
                result: {sqlDebug.result ?? "n/a"}
              </div>
              {sqlDebug.attempts?.map((attempt, i) => (
                <div
                  className="rounded border border-border/40 bg-background/60 p-1.5"
                  key={i}
                >
                  {attempt.sql && (
                    <pre className="overflow-auto whitespace-pre-wrap text-foreground/80">
                      {attempt.sql}
                    </pre>
                  )}
                  {attempt.error && (
                    <div className="text-red-500">error: {attempt.error}</div>
                  )}
                  {typeof attempt.row_count === "number" && (
                    <div className="text-muted-foreground">
                      rows: {attempt.row_count}
                    </div>
                  )}
                </div>
              ))}
            </CollapsibleSection>
          )}

          {answerStats && (
            <CollapsibleSection defaultOpen title="Answer">
              <div className="text-muted-foreground">
                vector context: {answerStats.vector_context_chars ?? 0} chars
                · sql context: {answerStats.sql_context_chars ?? 0} chars ·
                answer: {answerStats.answer_chars ?? 0} chars
              </div>
            </CollapsibleSection>
          )}

          <details className="pt-1">
            <summary className="cursor-pointer text-muted-foreground">
              raw JSON
            </summary>
            <pre className="mt-1 max-h-64 overflow-auto whitespace-pre-wrap text-[10px] text-foreground/70">
              {JSON.stringify(trace, null, 2)}
            </pre>
          </details>
        </div>
      )}
    </div>
  );
}
