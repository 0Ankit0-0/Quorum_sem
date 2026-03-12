import { useEffect, useMemo, useState } from "react";

const API_BASE = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

const useBackendStatus = () => {
  const [ready, setReady] = useState(false);
  const [message, setMessage] = useState("Starting local services...");

  useEffect(() => {
    let active = true;
    let attempts = 0;
    const maxAttempts = 90;

    const check = async () => {
      try {
        const response = await fetch(`${API_BASE}/system/status`, {
          cache: "no-store",
        });
        if (!active) return;
        if (response.ok) {
          setReady(true);
          setMessage("Backend is ready.");
          return;
        }
      } catch {
        // ignore
      }

      attempts += 1;
      if (!active) return;
      if (attempts >= maxAttempts) {
        setMessage("Backend is still starting. Please wait...");
        return;
      }
      setTimeout(check, 1000);
    };

    check();
    return () => {
      active = false;
    };
  }, []);

  return { ready, message };
};

export default function BackendGate({ children }: { children: React.ReactNode }) {
  const { ready, message } = useBackendStatus();
  const loading = useMemo(() => !ready, [ready]);

  if (!loading) return <>{children}</>;

  return (
    <div className="min-h-screen flex items-center justify-center bg-background text-foreground">
      <div className="text-center space-y-3">
        <div className="text-2xl font-semibold tracking-wide">QUORUM</div>
        <div className="text-sm text-muted-foreground">{message}</div>
        <div className="flex items-center justify-center">
          <div className="h-2 w-2 rounded-full bg-cyan animate-pulse" />
          <div className="ml-2 h-2 w-2 rounded-full bg-cyan/70 animate-pulse" />
          <div className="ml-2 h-2 w-2 rounded-full bg-cyan/50 animate-pulse" />
        </div>
      </div>
    </div>
  );
}
