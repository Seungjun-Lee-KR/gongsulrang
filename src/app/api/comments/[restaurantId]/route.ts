import { kv } from "@vercel/kv";
import { auth } from "@/lib/auth";
import type { NextRequest } from "next/server";

export type Comment = {
  id: string;
  content: string;
  userId: string;
  userName: string;
  userImage?: string;
  provider: string;
  createdAt: number;
};

const MAX_CONTENT = 1000;
const RATE_LIMIT_MS = 30_000;
// 안정 식별자(restaurants.json의 id — kakaoId/placeId/해시) 기준.
// rank 키는 주간 재랭킹 때 댓글이 다른 가게로 떠내려가서 폐기했다.
const KEY = (restaurantId: string) => `comments:${restaurantId}`;
const RATE_KEY = (userId: string) => `rl:comment:${userId}`;

async function listComments(restaurantId: string): Promise<Comment[]> {
  const raw = await kv.lrange<string | Comment>(KEY(restaurantId), 0, -1);
  const out: Comment[] = [];
  for (const item of raw) {
    try {
      out.push(typeof item === "string" ? (JSON.parse(item) as Comment) : item);
    } catch {
      // skip malformed
    }
  }
  return out;
}

export async function GET(
  _req: NextRequest,
  ctx: { params: Promise<{ restaurantId: string }> },
) {
  const { restaurantId } = await ctx.params;
  if (!/^[A-Za-z0-9_-]{1,64}$/.test(restaurantId))
    return new Response("invalid restaurant id", { status: 400 });
  const comments = await listComments(restaurantId);
  return Response.json({ comments });
}

export async function POST(
  req: NextRequest,
  ctx: { params: Promise<{ restaurantId: string }> },
) {
  const { restaurantId } = await ctx.params;
  if (!/^[A-Za-z0-9_-]{1,64}$/.test(restaurantId))
    return new Response("invalid restaurant id", { status: 400 });

  const session = await auth();
  if (!session?.user) {
    return Response.json({ error: "로그인이 필요합니다." }, { status: 401 });
  }
  const userId = (session.user as { id?: string }).id ?? session.user.email;
  if (!userId) {
    return Response.json({ error: "사용자 식별 불가" }, { status: 401 });
  }

  const recent = await kv.get<number>(RATE_KEY(userId));
  if (recent && Date.now() - recent < RATE_LIMIT_MS) {
    return Response.json({ error: "잠시 후 다시 시도해 주세요." }, { status: 429 });
  }

  const body = await req.json().catch(() => ({}));
  const content = String((body as { content?: unknown }).content ?? "").trim();
  if (!content || content.length > MAX_CONTENT) {
    return Response.json(
      { error: `내용은 1~${MAX_CONTENT}자 사이여야 합니다.` },
      { status: 400 },
    );
  }

  const comment: Comment = {
    id: crypto.randomUUID(),
    content,
    userId,
    userName: session.user.name ?? "익명",
    userImage: session.user.image ?? undefined,
    provider:
      (session.user as { provider?: string }).provider ?? "unknown",
    createdAt: Date.now(),
  };

  await kv.lpush(KEY(restaurantId), JSON.stringify(comment));
  await kv.set(RATE_KEY(userId), Date.now(), { ex: 60 });

  return Response.json({ comment }, { status: 201 });
}

export async function DELETE(
  req: NextRequest,
  ctx: { params: Promise<{ restaurantId: string }> },
) {
  const { restaurantId } = await ctx.params;
  if (!/^[A-Za-z0-9_-]{1,64}$/.test(restaurantId))
    return new Response("invalid restaurant id", { status: 400 });

  const session = await auth();
  if (!session?.user) {
    return Response.json({ error: "로그인이 필요합니다." }, { status: 401 });
  }
  const userId = (session.user as { id?: string }).id ?? session.user.email;
  if (!userId) {
    return Response.json({ error: "사용자 식별 불가" }, { status: 401 });
  }

  const url = new URL(req.url);
  const id = url.searchParams.get("id");
  if (!id) return Response.json({ error: "id 누락" }, { status: 400 });

  const all = await listComments(restaurantId);
  const target = all.find((c) => c.id === id);
  if (!target) return Response.json({ error: "없음" }, { status: 404 });
  if (target.userId !== userId) {
    return Response.json({ error: "권한 없음" }, { status: 403 });
  }
  const remaining = all.filter((c) => c.id !== id);
  await kv.del(KEY(restaurantId));
  if (remaining.length > 0) {
    // lpush expects newest-first; remaining is oldest-first because we filtered list order.
    // We'll lpush in reverse to preserve order (first item ends up at head).
    await kv.lpush(
      KEY(restaurantId),
      ...remaining
        .slice()
        .reverse()
        .map((c) => JSON.stringify(c)),
    );
  }
  return Response.json({ ok: true });
}
