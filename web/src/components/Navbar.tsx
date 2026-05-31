"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  MessageSquare,
  Shield,
  FileText,
  CreditCard,
  ScrollText,
} from "lucide-react";

const NAV_ITEMS = [
  { href: "/", label: "Chat", icon: MessageSquare },
  { href: "/logs", label: "Logs", icon: ScrollText },
  { href: "/admin", label: "Admin", icon: Shield },
  { href: "/reports", label: "Reports", icon: FileText },
];

export default function Navbar() {
  const pathname = usePathname();

  return (
    <header className="sticky top-0 z-50 w-full relative border-b border-transparent bg-transparent aero-navbar">
      <div className="flex h-14 items-center px-4 max-w-7xl mx-auto">
        <Link
          href="/"
          className="flex items-center gap-2 font-semibold mr-8"
        >
          <CreditCard className="h-5 w-5 text-black" />
          <span className="hidden sm:inline">Aero Intel</span>
        </Link>

        <nav className="flex items-center gap-1">
          {NAV_ITEMS.map((item) => {
            const isActive = pathname === item.href;
              return (
              <Link
                key={item.href}
                href={item.href}
                className={`flex items-center gap-2 px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
                  isActive
                    ? "bg-white/10 text-white dark:bg-white/10 dark:text-white"
                    : "text-white hover:text-white hover:bg-white/10 dark:text-white dark:hover:text-white dark:hover:bg-white/10"
                }`}
              >
                <item.icon className="h-4 w-4" />
                <span className="hidden sm:inline">{item.label}</span>
              </Link>
            );
          })}
        </nav>
      </div>
    </header>
  );
}
