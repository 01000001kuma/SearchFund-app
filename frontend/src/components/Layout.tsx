import { NavLink, Outlet } from "react-router-dom"
import { LayoutDashboard, List, Filter, MessageSquare, Sparkles } from "lucide-react"
import { cn } from "@/lib/utils"

const navItems = [
  { to: "/", label: "Panel de Control", icon: LayoutDashboard, end: true },
  { to: "/chat", label: "Agente", icon: MessageSquare },
  { to: "/candidatas", label: "Candidatas", icon: Sparkles },
  { to: "/buscar", label: "Filtrar", icon: Filter },
  { to: "/listas", label: "Listas", icon: List },
]

export function Layout() {
  return (
    <div className="flex min-h-screen">
      <aside className="flex w-64 flex-col border-r bg-muted/30">
        <div className="flex items-center gap-2 border-b px-6 py-4">
          <img src="/logo.png" alt="Logo" className="size-10 object-contain" />
          <span className="text-lg font-semibold">SearchFund Agent</span>
        </div>
        <nav className="flex flex-1 flex-col gap-1 p-3">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) =>
                cn(
                  "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                  isActive
                    ? "bg-primary text-primary-foreground"
                    : "hover:bg-accent hover:text-accent-foreground",
                )
              }
            >
              <item.icon className="size-4" />
              {item.label}
            </NavLink>
          ))}
        </nav>
      </aside>
      <main className="flex-1 overflow-y-auto p-6">
        <Outlet />
      </main>
    </div>
  )
}
