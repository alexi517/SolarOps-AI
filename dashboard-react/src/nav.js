import {
  IconGrid,
  IconBolt,
  IconTrendingUp,
  IconAlertTriangle,
  IconLightbulb,
  IconCheckCircle,
  IconList,
} from "./icons.jsx";

// Shared nav item list — used by both the desktop Sidebar and the mobile tab
// strip in App.jsx, so the two stay in sync automatically.
export const NAV_ITEMS = [
  { key: "overview", label: "Overview", icon: IconGrid },
  { key: "energy-flow", label: "Energy Flow", icon: IconBolt },
  { key: "forecasts", label: "Forecasts", icon: IconTrendingUp },
  { key: "anomalies", label: "Anomalies", icon: IconAlertTriangle },
  { key: "recommendations", label: "Recommendations", icon: IconLightbulb },
  { key: "approvals", label: "Approvals", icon: IconCheckCircle },
  { key: "commands", label: "Commands", icon: IconList },
];
