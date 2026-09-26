import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import { TooltipProvider } from "@/components/ui/tooltip";
import { AppShell } from "@/components/app-shell";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "ArgusIDX",
  description:
    "Lapisan bukti untuk investor ritel Indonesia: apa yang data sebenarnya katakan, bukan opini.",
};

export default async function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="id"
      className={`${geistSans.variable} ${geistMono.variable} dark h-full antialiased`}
      suppressHydrationWarning
    >
      <head>
        {/* Restore the sidebar state before first paint so a collapsed sidebar does not flash open. */}
        <script
          dangerouslySetInnerHTML={{
            __html: `try{if(localStorage.getItem("argus_sidebar")==="collapsed")document.documentElement.dataset.sidebar="collapsed"}catch(e){}`,
          }}
        />
      </head>
      <body className="min-h-full flex flex-col">
        <TooltipProvider delay={150}>
          <AppShell>{children}</AppShell>
        </TooltipProvider>
      </body>
    </html>
  );
}
