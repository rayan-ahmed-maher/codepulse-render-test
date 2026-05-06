import { Inter } from "next/font/google";
import ThemeProvider from "@/components/ThemeProvider";
import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  weight: ["300", "400", "500", "600", "700", "800", "900"],
  variable: "--font-inter",
  display: "swap",
});

export const metadata = {
  title: "DeployAI — Deploy at the Speed of Thought",
  description:
    "Production-grade SaaS deployment platform. AI-powered project analysis, multi-platform orchestration, and intelligent domain management.",
  keywords: ["deployment", "AI", "DevOps", "Vercel", "Netlify", "Cloudflare", "SaaS"],
};

export default function RootLayout({ children }) {
  return (
    <html lang="en" className={inter.variable} data-theme="dark">
      <body>
        <ThemeProvider>{children}</ThemeProvider>
      </body>
    </html>
  );
}
