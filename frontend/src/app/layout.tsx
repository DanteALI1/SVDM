import type { Metadata } from "next";
import { Manrope } from "next/font/google";
import "./globals.css";
import { AppProvider } from "@/components/AppProvider";

const manrope = Manrope({
  subsets: ["latin", "latin-ext", "cyrillic"],
  weight: ["400", "500", "600", "700", "800"],
  variable: "--font-manrope",
  display: "swap",
});

export const metadata: Metadata = {
  title: "SVDB",
  description: "Security Vulnerability Database",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ru" className={manrope.variable}>
      <body style={{ fontFamily: "var(--font-manrope), var(--font-body)" }}>
        <AppProvider>{children}</AppProvider>
      </body>
    </html>
  );
}
