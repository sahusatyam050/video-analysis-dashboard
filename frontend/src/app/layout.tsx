import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { Sidebar } from "@/components/layout/sidebar";
import { Header } from "@/components/layout/header";
import { Toaster } from "sonner";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Video Analysis Dashboard",
  description: "Enterprise video evidence tracking and analysis system",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={`${inter.className} bg-slate-50 overflow-hidden flex flex-col h-screen text-slate-900`}>
        <Header />
        <div className="flex flex-1 overflow-hidden">
          <Sidebar />
          <main className="flex-1 overflow-y-auto bg-slate-50 p-6 relative">
            <div className="relative z-10 max-w-7xl mx-auto">
              {children}
            </div>
          </main>
        </div>
        <Toaster position="bottom-right" richColors />
      </body>
    </html>
  );
}
