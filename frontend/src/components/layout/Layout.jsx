import { useEffect, useState } from "react";
import { Outlet, useLocation } from "react-router-dom";
import Sidebar from "./Sidebar.jsx";
import TopBar from "./TopBar.jsx";
import { titleFor } from "./nav.js";

export default function Layout() {
  const [open, setOpen] = useState(false);
  const { pathname } = useLocation();
  const title = titleFor(pathname);

  useEffect(() => {
    document.title = `${title} · FraudLens`;
    window.scrollTo({ top: 0 });
  }, [title, pathname]);

  return (
    <div className="min-h-screen bg-surface">
      <Sidebar open={open} onClose={() => setOpen(false)} />
      <div className="lg:pl-[264px] flex min-h-screen flex-col">
        <TopBar title={title} onMenu={() => setOpen(true)} />
        <main className="mx-auto w-full max-w-[1500px] flex-1 px-4 py-5 sm:px-6 sm:py-6">
          <Outlet />
        </main>
        <footer className="no-print mx-auto w-full max-w-[1500px] px-4 pb-6 pt-2 text-[11.5px] text-muted sm:px-6">
          FraudLens · Explainable hybrid credit-card fraud detection · Final-year project (Cyber Security / ML)
        </footer>
      </div>
    </div>
  );
}
