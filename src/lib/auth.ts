import NextAuth from "next-auth";
import Google from "next-auth/providers/google";
import Kakao from "next-auth/providers/kakao";
import Naver from "next-auth/providers/naver";

export const { handlers, signIn, signOut, auth } = NextAuth({
  providers: [
    Google,
    // Kakao 콘솔에서 Client Secret 사용 안 함으로 두면 secret 비어있어도 OK
    Kakao({
      clientId: process.env.AUTH_KAKAO_ID,
      clientSecret: process.env.AUTH_KAKAO_SECRET ?? "",
      client: { token_endpoint_auth_method: "none" },
    }),
    Naver({
      clientId: process.env.AUTH_NAVER_ID,
      clientSecret: process.env.AUTH_NAVER_SECRET,
      authorization: {
        url: "https://nid.naver.com/oauth2.0/authorize",
        params: { scope: "name email profile_image" },
      },
      checks: ["state", "pkce"],
    }),
  ],
  trustHost: true,
  debug: true,
  logger: {
    error: (error) => console.error("[next-auth][error]", error),
    warn: (msg) => console.warn("[next-auth][warn]", msg),
    debug: (msg, meta) =>
      console.debug("[next-auth][debug]", msg, meta ?? ""),
  },
  session: { strategy: "jwt" },
  callbacks: {
    async jwt({ token, profile, account }) {
      if (account) {
        token.provider = account.provider;
      }
      return token;
    },
    async session({ session, token }) {
      if (session.user) {
        session.user.id =
          (token.sub as string | undefined) ?? session.user.email ?? "";
        (session.user as { provider?: string }).provider =
          token.provider as string | undefined;
      }
      return session;
    },
  },
});
