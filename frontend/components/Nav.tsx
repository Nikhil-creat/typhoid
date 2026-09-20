import Link from "next/link";
export function Nav() {
  return (
    <header className="flex items-center justify-between px-6 py-4 border-b border-rim bg-slide">
      <Link href="/" className="font-display text-2xl font-bold tracking-tight">Typhoid</Link>
      <nav className="flex gap-6 text-sm">
        <Link href="/">Observatory</Link><Link href="/studio">Test Studio</Link><Link href="/incidents">Patch review</Link>
      </nav>
    </header>
  );
}
