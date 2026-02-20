import Sidebar from "./Sidebar";

interface AppLayoutProps {
  children: React.ReactNode;
  title: string;
  subtitle?: string;
}

export default function AppLayout({ children, title, subtitle }: AppLayoutProps) {
  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar />
      <div className="flex-1 flex flex-col ml-60 overflow-hidden">
        {/* Simple header inline */}
        <header className="h-14 border-b border-border flex items-center justify-between px-6 shrink-0" style={{ background: "hsl(var(--card))" }}>
          <div>
            <h1 className="text-base font-semibold text-foreground">{title}</h1>
            {subtitle && <p className="text-xs text-muted-foreground">{subtitle}</p>}
          </div>
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-mono" style={{ background: "hsl(var(--low) / 0.1)", border: "1px solid hsl(var(--low) / 0.3)", color: "hsl(var(--low))" }}>
              <span>● OFFLINE MODE</span>
            </div>
            <div className="text-xs font-mono text-muted-foreground border-l border-border pl-3">
              <div>{new Date().toLocaleTimeString("en-US", { hour12: false })}</div>
              <div>{new Date().toLocaleDateString("en-US", { month: "short", day: "2-digit", year: "numeric" })}</div>
            </div>
          </div>
        </header>
        <main className="flex-1 overflow-y-auto p-6">
          {children}
        </main>
      </div>
    </div>
  );
}
