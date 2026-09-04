import type { Metadata } from "next";
import "./globals.css";
import { AppProvider } from "@/components/AppProvider";

export const metadata: Metadata = {
  title: "SVDB",
  description: "Security Vulnerability Database",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ru">
      <body>
        <AppProvider>{children}</AppProvider>
      </body>
    </html>
  );
}
