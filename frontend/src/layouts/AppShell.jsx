import { Activity, Dumbbell, LayoutDashboard, LogOut, Salad, User } from "lucide-react";
import { useEffect, useState } from "react";
import { NavLink, useNavigate } from "react-router-dom";

import { logout } from "../api/auth";
import { getProfile } from "../api/profile";
import { FocusMuscles } from "../components/FocusMuscles";


const navItems = [
  { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { to: "/profile", label: "Profile", icon: User },
  { to: "/workout", label: "Workout", icon: Dumbbell },
  { to: "/nutrition", label: "Nutrition", icon: Salad },
];

export default function AppShell({ children, user, onLogout }) {
  const navigate = useNavigate();
  const [focusMuscles, setFocusMuscles] = useState([]);

  useEffect(() => {
    let active = true;

    async function loadFocusMuscles() {
      try {
        const data = await getProfile();
        if (active) {
          setFocusMuscles(data.profile?.focus_muscles || []);
        }
      } catch {
        if (active) {
          setFocusMuscles([]);
        }
      }
    }

    loadFocusMuscles();
    window.addEventListener("aipt:profile-focus-updated", loadFocusMuscles);
    return () => {
      active = false;
      window.removeEventListener("aipt:profile-focus-updated", loadFocusMuscles);
    };
  }, [user?.id]);

  async function handleLogout() {
    await logout();
    onLogout?.();
    navigate("/login");
  }

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <aside className="fixed inset-y-0 left-0 hidden w-64 border-r border-slate-200 bg-white px-4 py-5 md:block">
        <div className="mb-8 flex items-center gap-3">
          <div className="grid h-10 w-10 place-items-center rounded bg-brand-600 text-white">
            <Activity size={22} />
          </div>
          <div>
            <p className="text-sm font-semibold uppercase tracking-wide text-brand-700">AIPT</p>
            <h1 className="text-lg font-semibold">Personal Trainer</h1>
          </div>
        </div>

        <nav className="space-y-1">
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) =>
                  `flex h-11 items-center gap-3 rounded px-3 text-sm font-medium transition ${
                    isActive ? "bg-brand-50 text-brand-700" : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
                  }`
                }
              >
                <Icon size={18} />
                {item.label}
              </NavLink>
            );
          })}
        </nav>

        <div className="absolute bottom-5 left-4 right-4">
          <div className="mb-3 rounded border border-brand-100 bg-brand-50/60 p-3">
            <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-brand-700">Current focus</p>
            <FocusMuscles muscles={focusMuscles} compact />
          </div>
          <div className="mb-3 rounded border border-slate-200 bg-slate-50 p-3 text-sm">
            <p className="font-medium">{user?.username || "User"}</p>
            <p className="text-slate-500">{user?.email || "Token auth"}</p>
          </div>
          <button className="btn-secondary w-full justify-center" onClick={handleLogout}>
            <LogOut size={16} />
            Logout
          </button>
        </div>
      </aside>

      <main className="md:pl-64">
        <div className="border-b border-slate-200 bg-white px-4 py-3 md:hidden">
          <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-brand-700">Current focus</p>
          <FocusMuscles muscles={focusMuscles} compact />
        </div>
        <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">{children}</div>
      </main>
    </div>
  );
}
