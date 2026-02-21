import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'AidSight | Portfolio Stress-Testing Terminal',
  description: 'Decision Sandbox for humanitarian funding',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-slate-950 text-slate-100 antialiased">
        <nav className="border-b border-slate-800 bg-slate-900/80 backdrop-blur">
          <div className="mx-auto flex h-14 max-w-7xl items-center gap-6 px-4">
            <a href="/sandbox" className="font-semibold text-amber-400">
              AidSight
            </a>
            <a href="/sandbox" className="text-sm text-slate-300 hover:text-white">
              Sandbox
            </a>
            <a href="/projects" className="text-sm text-slate-300 hover:text-white">
              Projects
            </a>
          </div>
        </nav>
        {children}
      </body>
    </html>
  );
}
