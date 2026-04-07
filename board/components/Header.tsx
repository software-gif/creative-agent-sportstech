"use client";

import Link from "next/link";
import Image from "next/image";
import { usePathname } from "next/navigation";

export default function Header() {
  const pathname = usePathname();

  const navItems = [
    { href: "/", label: "Board", icon: "M4 6h16M4 12h16M4 18h7" },
    { href: "/library", label: "Library", icon: "M5 8h14M5 8a2 2 0 110-4h14a2 2 0 110 4M5 8v10a2 2 0 002 2h10a2 2 0 002-2V8m-9 4h4" },
  ];

  return (
    <header className="sticky top-0 z-50 bg-surface/95 backdrop-blur-sm border-b border-border px-6 py-3">
      <nav className="flex items-center justify-between">
        <div className="flex items-center gap-8">
          <Link href="/" className="flex items-center gap-3">
            <Image
              src="/logo_dark.png"
              alt="Sportstech"
              width={120}
              height={32}
              className="h-7 w-auto"
            />
            <div className="border-l border-border pl-3">
              <span className="text-[10px] font-semibold text-primary uppercase tracking-widest">
                Creative Board
              </span>
            </div>
          </Link>

          <div className="flex items-center gap-1 bg-background rounded-lg p-0.5">
            {navItems.map((item) => {
              const isActive =
                item.href === "/"
                  ? pathname === "/"
                  : pathname.startsWith(item.href);
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`flex items-center gap-1.5 text-sm font-medium px-3 py-1.5 rounded-md transition-all ${
                    isActive
                      ? "bg-surface text-primary shadow-sm"
                      : "text-muted hover:text-accent"
                  }`}
                >
                  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} className="w-3.5 h-3.5">
                    <path strokeLinecap="round" strokeLinejoin="round" d={item.icon} />
                  </svg>
                  {item.label}
                </Link>
              );
            })}
          </div>
        </div>

        <div className="flex items-center gap-2">
          <span className="text-[10px] text-muted">
            Creative Agent
          </span>
        </div>
      </nav>
    </header>
  );
}
