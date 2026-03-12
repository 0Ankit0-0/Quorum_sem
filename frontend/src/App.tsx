import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useEffect } from "react";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import Dashboard from "./pages/Dashboard";
import Logs from "./pages/Logs";
import Monitor from "./pages/Monitor";
import Devices from "./pages/Devices";
import Analysis from "./pages/Analysis";
import Hub from "./pages/Hub";
import Reports from "./pages/Reports";
import Terminal from "./pages/Terminal";
import Settings from "./pages/Settings";
import Updates from "./pages/Updates";
import NotFound from "./pages/NotFound";
import BackendGate from "@/components/BackendGate";
import { launchBackend } from "@/lib/backendLauncher";

const queryClient = new QueryClient();

const App = () => {
  useEffect(() => {
    void launchBackend();
  }, []);

  return (
    <QueryClientProvider client={queryClient}>
      <TooltipProvider>
        <Toaster />
        <Sonner />
        <BackendGate>
          <BrowserRouter
            future={{
              v7_startTransition: true,
              v7_relativeSplatPath: true,
            }}
          >
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/logs" element={<Logs />} />
              <Route path="/monitor" element={<Monitor />} />
              <Route path="/devices" element={<Devices />} />
              <Route path="/analysis" element={<Analysis />} />
              <Route path="/hub" element={<Hub />} />
              <Route path="/reports" element={<Reports />} />
              <Route path="/terminal" element={<Terminal />} />
              <Route path="/updates" element={<Updates />} />
              <Route path="/settings" element={<Settings />} />
              <Route path="*" element={<NotFound />} />
            </Routes>
          </BrowserRouter>
        </BackendGate>
      </TooltipProvider>
    </QueryClientProvider>
  );
};

export default App;
