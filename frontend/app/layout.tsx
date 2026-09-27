import "@fontsource-variable/inter";
import "@fontsource-variable/vazirmatn";
import "./globals.css";
import type { Metadata, Viewport } from "next";
import { cookies } from "next/headers";
import type { ReactNode } from "react";
import { Shell } from "@/components/shell";
import type { Lang, Theme } from "@/lib/i18n";

export const metadata: Metadata = {
  title: "پارسلی · Parsely",
  description: "Real-time content analytics for Persian publishers",
};
export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#f5f5f7" },
    { media: "(prefers-color-scheme: dark)", color: "#000000" },
  ],
};

export default async function RootLayout({ children }: { children: ReactNode }) {
  const c = await cookies();
  const lang: Lang = c.get("lang")?.value === "en" ? "en" : "fa";
  const saved = c.get("theme")?.value;
  const theme: Theme = saved === "light" || saved === "dark" ? saved : "system";
  return (
    <html lang={lang} dir={lang === "fa" ? "rtl" : "ltr"} data-theme={theme === "system" ? undefined : theme}>
      <body>
        <Shell lang={lang} theme={theme}>{children}</Shell>
      </body>
    </html>
  );
}
