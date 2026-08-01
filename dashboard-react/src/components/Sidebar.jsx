import { IconBolt2Solid } from "../icons.jsx";

// Desktop sidebar — hidden below `lg`, where the mobile tab strip in App.jsx
// takes over instead. Structural only: neutral grays for the active state,
// no new accent colors, no transitions (that's a later polish pass).
export default function Sidebar({ items, active, onSelect }) {
  return (
    <aside className="hidden border-r border-gray-200 bg-white lg:sticky lg:top-0 lg:flex lg:h-screen lg:w-64 lg:shrink-0 lg:flex-col">
      <div className="flex items-center gap-2 border-b border-gray-200 px-6 py-5">
        <span className="app-brand-icon">
          <IconBolt2Solid className="h-4 w-4" />
        </span>
        <span className="text-base font-bold text-gray-900">SolarOps AI</span>
      </div>
      <nav className="flex-1 space-y-1 overflow-y-auto px-3 py-4">
        {items.map((item) => {
          const isActive = item.key === active;
          const Icon = item.icon;
          return (
            <button
              key={item.key}
              type="button"
              onClick={() => onSelect(item.key)}
              className={
                "flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left text-sm font-medium " +
                (isActive ? "bg-gray-900 text-white" : "text-gray-600 hover:bg-gray-100")
              }
            >
              <Icon className="h-4 w-4 shrink-0" />
              {item.label}
            </button>
          );
        })}
      </nav>
    </aside>
  );
}
