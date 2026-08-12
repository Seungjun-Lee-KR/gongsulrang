import NextAuth from "next-auth";
import Google from "next-auth/providers/google";
import Kakao from "next-auth/providers/kakao";
import Naver from "next-auth/providers/naver";

export const { handlers, signIn, signOut, auth } = NextAuth({
  providers: [
    Google,
    // 카카오 콘솔에서 Client Secret이 "사용함"이므로 secret 필수.
    // 미전송/오전송 시 토큰 교환이 KOE010(Bad client credentials)로 실패한다.
    // token_endpoint_auth_method는 provider 기본값(client_secret_post)을 그대로 쓴다.
    Kakao({
      clientId: process.env.AUTH_KAKAO_ID,
      clientSecret: process.env.AUTH_KAKAO_SECRET,
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
  session: { strategy: "jwt" },
  callbacks: {
    async jwt({ token, account }) {
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
