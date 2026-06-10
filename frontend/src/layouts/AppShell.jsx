import { ChevronLeft, ChevronRight, Dumbbell, LayoutDashboard, LogOut, Salad, User } from "lucide-react";
import { useEffect, useState } from "react";
import { NavLink, useNavigate } from "react-router-dom";

import { logout } from "../api/auth";
import { getProfile } from "../api/profile";
import { FocusMuscles } from "../components/FocusMuscles";


const navItems = [
  { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { to: "/workout", label: "Workout", icon: Dumbbell },
  { to: "/nutrition", label: "Nutrition", icon: Salad },
  { to: "/profile", label: "Profile", icon: User },
];

const SIDEBAR_COLLAPSED_KEY = "aipt_sidebar_collapsed";

function readStoredSidebarState() {
  return localStorage.getItem(SIDEBAR_COLLAPSED_KEY) === "1";
}

export default function AppShell({ children, user, onLogout }) {
  const navigate = useNavigate();
  const [focusMuscles, setFocusMuscles] = useState([]);
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(readStoredSidebarState);

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

  function toggleSidebar() {
    setIsSidebarCollapsed((value) => {
      const nextValue = !value;
      localStorage.setItem(SIDEBAR_COLLAPSED_KEY, nextValue ? "1" : "0");
      return nextValue;
    });
  }

  return (
    <div className="min-h-[100dvh] bg-[#f3f7ef] text-slate-900">
      <aside
        className={`fixed bottom-4 left-4 top-4 z-20 hidden rounded-[1.75rem] border border-black/10 bg-white/80 shadow-[0_24px_80px_rgba(35,48,30,0.12)] backdrop-blur-xl transition-all duration-300 lg:block ${
          isSidebarCollapsed ? "w-20 p-3" : "w-72 p-4"
        }`}
      >
        <button
          type="button"
          className="absolute -right-5 top-1/2 z-30 grid h-9 w-9 -translate-y-1/2 place-items-center rounded-full border border-black/5 bg-white/55 text-slate-500 shadow-sm backdrop-blur transition hover:border-brand-200 hover:bg-white/80 hover:text-brand-900"
          onClick={toggleSidebar}
          aria-label={isSidebarCollapsed ? "Expand sidebar" : "Collapse sidebar"}
          title={isSidebarCollapsed ? "Expand sidebar" : "Collapse sidebar"}
        >
          {isSidebarCollapsed ? <ChevronRight size={17} /> : <ChevronLeft size={17} />}
        </button>

        <div className={`overflow-hidden rounded-[1.25rem] bg-brand-900 text-white shadow-lg shadow-brand-900/15 ${isSidebarCollapsed ? "p-2" : "p-5"}`}>
          <div className={`flex items-center ${isSidebarCollapsed ? "justify-center" : "gap-3"}`}>
            <img
              src="/android-chrome-192x192.png"
              alt=""
              className={`shrink-0 bg-white/95 object-cover ring-1 ring-white/20 ${isSidebarCollapsed ? "h-10 w-10 rounded-xl" : "h-11 w-11 rounded-2xl"}`}
            />
            {!isSidebarCollapsed ? (
              <div className="min-w-0 overflow-hidden">
                <h1 className="whitespace-nowrap text-lg font-semibold tracking-tight">AI Personal Trainer</h1>
              </div>
            ) : null}
          </div>
        </div>

        <nav className="mt-5 space-y-2">
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.to}
                to={item.to}
                title={item.label}
                className={({ isActive }) =>
                  `group flex h-12 items-center rounded-2xl text-sm font-semibold transition ${
                    isSidebarCollapsed ? "justify-center px-0" : "gap-3 px-4"
                  } ${
                    isActive
                      ? "bg-brand-800 text-white shadow-lg shadow-brand-900/15"
                      : "text-slate-600 hover:bg-slate-950/5 hover:text-slate-950"
                  }`
                }
              >
                <Icon size={18} />
                {!isSidebarCollapsed ? <span className="whitespace-nowrap">{item.label}</span> : null}
              </NavLink>
            );
          })}
        </nav>

        <div className="absolute bottom-4 left-4 right-4">
          {!isSidebarCollapsed ? (
            <>
              <div className="mb-3 overflow-hidden rounded-[1.25rem] border border-brand-100 bg-brand-50/80 p-4">
                <p className="mb-2 whitespace-nowrap text-xs font-semibold uppercase tracking-[0.22em] text-brand-800">Current focus</p>
                <FocusMuscles muscles={focusMuscles} compact />
              </div>
              <div className="mb-3 rounded-[1.25rem] border border-black/10 bg-white/85 p-4 text-sm">
                <p className="font-medium">{user?.username || "User"}</p>
                <p className="text-slate-500">{user?.email || "Token auth"}</p>
              </div>
            </>
          ) : null}
          <button
            className={`btn-secondary w-full justify-center ${isSidebarCollapsed ? "px-0" : ""}`}
            onClick={handleLogout}
            title="Logout"
            aria-label="Logout"
          >
            <LogOut size={16} />
            {!isSidebarCollapsed ? "Logout" : null}
          </button>
        </div>
      </aside>

      <main className={`relative z-10 pb-24 transition-all duration-300 lg:pb-0 ${isSidebarCollapsed ? "lg:pl-28" : "lg:pl-80"}`}>
        <div className="sticky top-0 z-20 border-b border-black/10 bg-white/85 px-4 py-3 backdrop-blur lg:hidden">
          <div className="flex items-center justify-between gap-4">
            <div>
              <p className="text-sm font-semibold text-slate-950">AI Personal Trainer</p>
            </div>
            <button className="btn-secondary h-10 px-3" onClick={handleLogout} aria-label="Logout">
              <LogOut size={16} />
            </button>
          </div>
          <div className="mt-3 rounded-2xl bg-brand-50/80 px-3 py-2">
            <FocusMuscles muscles={focusMuscles} compact />
          </div>
        </div>
        <div className="mx-auto max-w-[1400px] px-4 py-5 sm:px-6 lg:px-8 lg:py-8">{children}</div>
      </main>

      <nav className="fixed inset-x-3 bottom-3 z-30 grid grid-cols-4 rounded-[1.4rem] border border-black/10 bg-white/90 p-2 shadow-2xl backdrop-blur-xl lg:hidden">
        {navItems.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                `flex flex-col items-center gap-1 rounded-2xl py-2 text-[11px] font-semibold transition ${
                  isActive ? "bg-brand-800 text-white" : "text-slate-600"
                }`
              }
            >
              <Icon size={20} />
              {item.label}
            </NavLink>
          );
        })}
      </nav>
    </div>
  );
}
