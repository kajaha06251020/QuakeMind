import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "QuakeMind",
  description: "自律型防災 AGI — リアルタイム地震アラートシステム",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ja">
      <body style={{ margin: 0, fontFamily: "system-ui, sans-serif", background: "#0f0f0f", color: "#e5e5e5" }}>
        {children}
      </body>
    </html>
  );
}
