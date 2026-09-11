import {
  Activity,
  BookOpen,
  ClipboardList,
  FlaskConical,
  Home,
  Info,
  ShieldAlert,
  BarChart3,
} from "lucide-react";

export const NAV = [
  { to: "/", label: "Overview", title: "Overview", icon: Home, end: true },
  { to: "/monitor", label: "Live Monitor", title: "Live Monitor", icon: Activity, live: true },
  { to: "/tester", label: "Transaction Tester", title: "Transaction Tester", icon: FlaskConical, live: true },
  { to: "/scenarios", label: "Scam Scenarios", title: "Scam Scenarios: how scams are detected", icon: ShieldAlert, live: true },
  { to: "/cases", label: "Case Queue", title: "Case Queue", icon: ClipboardList, live: true },
  { to: "/results", label: "Results", title: "Model & Research Results", icon: BarChart3 },
  { to: "/report", label: "Project Report", title: "Project Report & Progress", icon: BookOpen },
  { to: "/about", label: "Architecture", title: "Architecture & How to run", icon: Info },
];

export function titleFor(pathname) {
  const hit = NAV.find((n) => (n.end ? pathname === n.to : pathname.startsWith(n.to)));
  return hit?.title || "FraudLens";
}
