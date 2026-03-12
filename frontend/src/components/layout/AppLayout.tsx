import { useState, useEffect, useCallback, useRef } from "react";
import Sidebar from "./Sidebar";
import { apiClient } from "@/lib/api";

const SIDEBAR_KEY = "quorum-sidebar-collapsed";

interface AppLayoutProps {
  children: React.ReactNode;
  title: string;
  subtitle?: string;
}

export default function AppLayout({ children, title, subtitle }: AppLayoutProps) {
  const [collapsed, setCollapsed] = useState<boolean>(() => {
    return localStorage.getItem(SIDEBAR_KEY) === "true";
  });
  const [time, setTime] = useState(() => new Date());
  const [isBackendOnline, setIsBackendOnline] = useState(false);
  const failedChecksRef = useRef(0);

  const handleToggle = useCallback(() => {
    setCollapsed((c) => {
      const next = !c;
      localStorage.setItem(SIDEBAR_KEY, String(next));
      return next;
    });
  }, []);

  useEffect(() => {
    const id = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(id);
  }, []);

  useEffect(() => {
    let mounted = true;

    const isOnlinePayload = (data: any) => {
      const status = String(data?.status ?? "").toLowerCase();
      if (status === "online" || status === "healthy") {
        return true;
      }
      // If status is missing but we got a response, assume reachable.
      return Boolean(data);
    };

    const checkBackend = async () => {
      try {
        const status = await apiClient.get("/system/status", { timeout: 2000 });
        if (!mounted) return;
        setIsBackendOnline(isOnlinePayload(status.data));
        failedChecksRef.current = 0;
      } catch {
        try {
          const root = await apiClient.get("/", { timeout: 2000 });
          if (!mounted) return;
          setIsBackendOnline(isOnlinePayload(root.data));
          failedChecksRef.current = 0;
        } catch {
          if (!mounted) return;
          failedChecksRef.current += 1;
          if (failedChecksRef.current >= 3) {
            setIsBackendOnline(false);
          }
        }
      }
    };

    void checkBackend();
    const id = setInterval(() => {
      void checkBackend();
    }, 15000);

    return () => {
      mounted = false;
      clearInterval(id);
    };
  }, []);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === "b") {
        e.preventDefault();
        handleToggle();
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [handleToggle]);

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar collapsed={collapsed} onToggle={handleToggle} systemOnline={isBackendOnline} />

      <div
        className="flex-1 flex flex-col overflow-hidden transition-all duration-[250ms] ease-[cubic-bezier(0.4,0,0.2,1)]"
        style={{ marginLeft: collapsed ? 64 : 240 }}
      >
        <header
          className="h-14 border-b border-border flex items-center justify-between px-6 shrink-0"
          style={{ background: "hsl(var(--card))" }}
        >
          <div>
            <h1 className="text-base font-semibold text-foreground">{title}</h1>
            {subtitle && <p className="text-xs text-muted-foreground">{subtitle}</p>}
          </div>
          <div className="flex items-center gap-3">
            <div
              className="flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-mono"
              style={{
                background: isBackendOnline
                  ? "hsl(var(--low) / 0.1)"
                  : "hsl(var(--critical) / 0.1)",
                border: isBackendOnline
                  ? "1px solid hsl(var(--low) / 0.3)"
                  : "1px solid hsl(var(--critical) / 0.3)",
                color: isBackendOnline ? "hsl(var(--low))" : "hsl(var(--critical))",
              }}
            >
              <span>{isBackendOnline ? "● ONLINE MODE" : "● OFFLINE MODE"}</span>
            </div>
            <div className="text-xs font-mono text-muted-foreground border-l border-border pl-3 tabular-nums">
              <div>{time.toLocaleTimeString("en-US", { hour12: false })}</div>
              <div>
                {time.toLocaleDateString("en-US", {
                  month: "short",
                  day: "2-digit",
                  year: "numeric",
                })}
              </div>
            </div>
          </div>
        </header>

        <main className="flex-1 overflow-y-auto p-6">{children}</main>
      </div>
    </div>
  );
}
