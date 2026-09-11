import { lazy, Suspense } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import Layout from "./components/layout/Layout.jsx";
import { PageLoader } from "./components/ui/Spinner.jsx";
import Overview from "./pages/Overview.jsx";
import Monitor from "./pages/Monitor.jsx";
import Tester from "./pages/Tester.jsx";
import Scenarios from "./pages/Scenarios.jsx";
import Cases from "./pages/Cases.jsx";
import Report from "./pages/Report.jsx";
import About from "./pages/About.jsx";

// The results page pulls in every research JSON + many charts: code-split it.
const Results = lazy(() => import("./pages/Results.jsx"));

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<Overview />} />
        <Route path="/monitor" element={<Monitor />} />
        <Route path="/tester" element={<Tester />} />
        <Route path="/scenarios" element={<Scenarios />} />
        <Route path="/cases" element={<Cases />} />
        <Route
          path="/results"
          element={
            <Suspense fallback={<PageLoader label="Loading research results" />}>
              <Results />
            </Suspense>
          }
        />
        <Route path="/report" element={<Report />} />
        <Route path="/about" element={<About />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}
