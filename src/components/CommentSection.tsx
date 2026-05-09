"use client";

import { signIn, signOut, useSession } from "next-auth/react";
import { useCallback, useEffect, useState } from "react";

type Comment = {
  id: string;
  content: string;
  userId: string;
  userName: string;
  userImage?: string;
  provider: string;
  createdAt: number;
};

const PROVIDER_LABEL: Record<string, string> = {
  google: "Google",
  kakao: "카카오",
  naver: "네이버",
};

const PROVIDER_BADGE_CLASS: Record<string, string> = {
  google: "bg-[#1a1a1f] border-line2 text-[#a3c9ff]",
  kakao: "bg-[#3a2f0a] border-[#5e4e1a] text-[#fee500]",
  naver: "bg-[#0d2a18] border-[#1a4a2c] text-[#03c75a]",
};

export default function CommentSection({ rank }: { rank: number }) {
  const { data: session, status } = useSession();
  const [comments, setComments] = useState<Comment[]>([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [content, setContent] = useState("");
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const r = await fetch(`/api/comments/${rank}`, { cache: "no-store" });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const data = (await r.json()) as { comments: Comment[] };
      setComments(data.comments);
    } catch (e) {
      setError(e instanceof Error ? e.message : "로딩 실패");
    } finally {
      setLoading(false);
    }
  }, [rank]);

  useEffect(() => {
    void load();
  }, [load]);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!content.trim()) return;
    setSubmitting(true);
    setError(null);
    try {
      const r = await fetch(`/api/comments/${rank}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content }),
      });
      if (!r.ok) {
        const body = (await r.json().catch(() => ({}))) as { error?: string };
        throw new Error(body.error ?? `HTTP ${r.status}`);
      }
      setContent("");
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "전송 실패");
    } finally {
      setSubmitting(false);
    }
  };

  const remove = async (id: string) => {
    if (!confirm("이 댓글을 삭제할까요?")) return;
    try {
      const r = await fetch(`/api/comments/${rank}?id=${id}`, {
        method: "DELETE",
      });
      if (!r.ok) {
        const body = (await r.json().catch(() => ({}))) as { error?: string };
        throw new Error(body.error ?? `HTTP ${r.status}`);
      }
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "삭제 실패");
    }
  };

  const myUserId = session?.user
    ? (session.user as { id?: string }).id ?? session.user.email
    : undefined;

  return (
    <div className="space-y-5">
      {status === "authenticated" ? (
        <form onSubmit={submit} className="rounded-xl border border-line bg-elev p-4">
          <div className="mb-3 flex items-center justify-between gap-3 text-xs text-mute">
            <div className="flex items-center gap-2">
              {session.user?.image && (
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  src={session.user.image}
                  alt=""
                  className="h-6 w-6 rounded-full"
                />
              )}
              <span className="font-medium text-ink">
                {session.user?.name ?? "사용자"}
              </span>
              <span>로그인됨</span>
            </div>
            <button
              type="button"
              onClick={() => signOut()}
              className="text-mute transition hover:text-ink"
            >
              로그아웃
            </button>
          </div>
          <textarea
            value={content}
            onChange={(e) => setContent(e.target.value)}
            maxLength={1000}
            rows={3}
            placeholder="가본 후기, 정정 의견, 정보 추천 등 자유롭게 (최대 1000자)"
            className="w-full resize-y rounded-lg border border-line bg-base p-3 text-sm text-ink placeholder:text-mute focus:border-accent focus:outline-none"
          />
          <div className="mt-2 flex items-center justify-between text-xs text-mute">
            <span>{content.length}/1000</span>
            <button
              type="submit"
              disabled={submitting || !content.trim()}
              className="rounded-md border border-accent bg-accent px-4 py-1.5 text-sm font-semibold text-[#1a0f08] transition hover:bg-accent/90 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {submitting ? "전송 중…" : "댓글 등록"}
            </button>
          </div>
        </form>
      ) : (
        <div className="rounded-xl border border-line bg-elev p-4">
          <p className="mb-3 text-sm text-ink">댓글을 남기려면 로그인하세요.</p>
          <div className="flex flex-wrap gap-2">
            <SignInButton provider="google" label="Google" />
            <SignInButton provider="kakao" label="카카오" />
            <SignInButton provider="naver" label="네이버" />
          </div>
        </div>
      )}

      {error && (
        <div className="rounded-lg border border-[#5a1a1a] bg-[#2a0e0e] px-3 py-2 text-sm text-[#ff9a8a]">
          {error}
        </div>
      )}

      {loading ? (
        <div className="text-sm text-mute">댓글 불러오는 중…</div>
      ) : comments.length === 0 ? (
        <div className="rounded-xl border border-dashed border-line bg-elev/50 p-6 text-center text-sm text-mute">
          아직 댓글이 없습니다. 가장 먼저 후기를 남겨주세요.
        </div>
      ) : (
        <ul className="space-y-3">
          {comments.map((c) => (
            <li
              key={c.id}
              className="rounded-xl border border-line bg-elev p-4"
            >
              <div className="mb-1.5 flex items-center justify-between gap-3">
                <div className="flex items-center gap-2">
                  {c.userImage && (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img
                      src={c.userImage}
                      alt=""
                      className="h-7 w-7 rounded-full"
                    />
                  )}
                  <span className="text-sm font-semibold text-ink">
                    {c.userName}
                  </span>
                  <span
                    className={`rounded border px-1.5 py-0.5 text-[10px] font-medium ${
                      PROVIDER_BADGE_CLASS[c.provider] ??
                      "border-line2 bg-base text-mute"
                    }`}
                  >
                    {PROVIDER_LABEL[c.provider] ?? c.provider}
                  </span>
                </div>
                <div className="flex items-center gap-2 text-[11px] text-mute">
                  <time>{formatRelative(c.createdAt)}</time>
                  {c.userId === myUserId && (
                    <button
                      type="button"
                      onClick={() => remove(c.id)}
                      className="hover:text-ink"
                      aria-label="삭제"
                    >
                      삭제
                    </button>
                  )}
                </div>
              </div>
              <p className="whitespace-pre-wrap break-words text-sm text-ink/90">
                {c.content}
              </p>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function SignInButton({
  provider,
  label,
}: {
  provider: "google" | "kakao" | "naver";
  label: string;
}) {
  const cls: Record<string, string> = {
    google:
      "bg-white text-[#1f1f1f] hover:bg-white/90 border-white",
    kakao:
      "bg-[#fee500] text-[#3c1e1e] hover:bg-[#fee500]/90 border-[#fee500]",
    naver:
      "bg-[#03c75a] text-white hover:bg-[#03c75a]/90 border-[#03c75a]",
  };
  return (
    <button
      type="button"
      onClick={() => signIn(provider)}
      className={`rounded-md border px-3 py-1.5 text-sm font-semibold transition ${cls[provider]}`}
    >
      {label}로 로그인
    </button>
  );
}

function formatRelative(ts: number): string {
  const diff = Date.now() - ts;
  if (diff < 60_000) return "방금 전";
  if (diff < 3_600_000) return `${Math.floor(diff / 60_000)}분 전`;
  if (diff < 86_400_000) return `${Math.floor(diff / 3_600_000)}시간 전`;
  if (diff < 604_800_000) return `${Math.floor(diff / 86_400_000)}일 전`;
  const d = new Date(ts);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}
