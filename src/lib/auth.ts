import NextAuth from "next-auth";
import Google from "next-auth/providers/google";
import Kakao from "next-auth/providers/kakao";
import Naver from "next-auth/providers/naver";

export const { handlers, signIn, signOut, auth } = NextAuth({
  providers: [Google, Kakao, Naver],
  trustHost: true,
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
