import { Bell, RefreshCw, Search, Wifi, WifiOff } from "lucide-react";
import { useState } from "react";

interface HeaderProps {
  title: string;
  subtitle?: string;
}

export default function Header({ title, subtitle }: HeaderProps) {
  const [refreshing, setRefreshing] = useState(false);

  const handleRefresh = () => {
    setRefreshing(true);
    setTimeout(() => setRefreshing(false), 1000);
  };

  return (
    <header className="h-14 border-b border-border flex items-center justify-between px-6 shrink-0" style={{ background: "hsl(var(--card))" }}>
      <div>
        <h1 className="text-base font-semibold text-foreground">{title}</h1>
        {subtitle && <p className="text-xs text-muted-foreground">{subtitle}</p>}
      </div>

      <div className="flex items-center gap-2">
        {/* Offline indicator */}
        <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-mono" style={{ background: "hsl(var(--low) / 0.1)", border: "1px solid hsl(var(--low) / 0.3)", color: "hsl(var(--low))" }}>
          <WifiOff className="w-3 h-3" />
          <span>OFFLINE</span>
        </div>

        {/* Alerts button */}
        <button className="relative p-2 rounded-md hover:bg-muted transition-colors">
          <Bell className="w-4 h-4 text-muted-foreground" />
          <span className="absolute top-1 right-1 w-1.5 h-1.5 rounded-full bg-cyber-critical animate-pulse" />
        </button>

        {/* Refresh button */}
        <button
          onClick={handleRefresh}
          className="p-2 rounded-md hover:bg-muted transition-colors"
        >
          <RefreshCw className={`w-4 h-4 text-muted-foreground ${refreshing ? "animate-spin" : ""}`} />
        </button>

        {/* Time */}
        <div className="pl-2 border-l border-border">
          <p className="text-xs font-mono text-muted-foreground">
            {new Date().toLocaleTimeString("en-US", { hour12: false })}
          </p>
          <p className="text-xs font-mono text-muted-foreground text-right">
            {new Date().toLocaleDateString("en-US", { month: "short", day: "2-digit" })}
          </p>
        </div>
      </div>
    </header>
  );
}
