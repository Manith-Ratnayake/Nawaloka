"use client";

import { useState } from "react";
import { cn } from "@/lib/utils";

type RerankedChunk = {
  id?: string;
  rerank_score?: number;
  source?: string;
  content_preview?: string;
};

type PerQueryDebug = {
  query: string;
  chunks_retrieved: number;
  chunk_ids: string[];
};

type VectorStepDebug = {
  total_unique_chunks_before_rerank?: number;
  per_query?: PerQueryDebug[];
  reranked_chunks?: RerankedChunk[];
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

function Section({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div className="space-y-1.5 border-border/50 border-t pt-2 first:border-t-0 first:pt-0">
      <div className="font-medium text-[11px] text-muted-foreground uppercase tracking-wide">
        {title}
      </div>
      {children}
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
    <div className="w-[min(100%,520px)] overflow-hidden rounded-lg border border-border/50 bg-muted/30 text-[12px]">
      <button
        className="flex w-full items-center justify-between px-3 py-2 text-left text-muted-foreground text-xs hover:text-foreground"
        onClick={() => setOpen((v) => !v)}
        type="button"
      >
        <span>Pipeline trace</span>
        <span className={cn("transition-transform", open && "rotate-180")}>
          ▾
        </span>
      </button>

      {open && (
        <div className="space-y-3 border-border/50 border-t px-3 py-2.5">
          {plan && (
            <Section title="Router">
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
            </Section>
          )}

          {subqueries && subqueries.length > 0 && (
            <Section title="Query agent — subqueries">
              <ul className="list-disc space-y-0.5 pl-4">
                {subqueries.map((q) => (
                  <li className="text-foreground/90" key={q}>
                    {q}
                  </li>
                ))}
              </ul>
            </Section>
          )}

          {vectorDebug && (
            <Section title="Vector search">
              <div className="text-muted-foreground">
                {vectorDebug.total_unique_chunks_before_rerank ?? 0} unique
                chunks retrieved before rerank
              </div>

              {vectorDebug.per_query?.map((pq) => (
                <div className="pl-2 text-muted-foreground" key={pq.query}>
                  “{pq.query}” → {pq.chunks_retrieved} chunks
                </div>
              ))}

              {vectorDebug.reranked_chunks &&
                vectorDebug.reranked_chunks.length > 0 && (
                  <div className="space-y-1.5 pt-1">
                    <div className="text-muted-foreground">
                      Reranked (top {vectorDebug.reranked_chunks.length}):
                    </div>
                    {vectorDebug.reranked_chunks.map((chunk, i) => (
                      <div
                        className="rounded border border-border/40 bg-background/60 p-1.5"
                        key={chunk.id ?? i}
                      >
                        <div className="flex justify-between text-foreground/80">
                          <span className="truncate">
                            {chunk.source || chunk.id}
                          </span>
                          <span className="shrink-0 text-muted-foreground">
                            score: {chunk.rerank_score?.toFixed(3)}
                          </span>
                        </div>
                        {chunk.content_preview && (
                          <div className="mt-0.5 line-clamp-2 text-muted-foreground">
                            {chunk.content_preview}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
            </Section>
          )}

          {sqlDebug && (
            <Section title="SQL search">
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
            </Section>
          )}

          {answerStats && (
            <Section title="Answer">
              <div className="text-muted-foreground">
                vector context: {answerStats.vector_context_chars ?? 0} chars
                · sql context: {answerStats.sql_context_chars ?? 0} chars ·
                answer: {answerStats.answer_chars ?? 0} chars
              </div>
            </Section>
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
