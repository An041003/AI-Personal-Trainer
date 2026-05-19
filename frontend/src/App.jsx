import { Navigate, Route, Routes, useLocation, useNavigate } from "react-router-dom";
import { useEffect, useState } from "react";

import { getAuthToken, setAuthToken } from "./api/client";
import { me } from "./api/auth";
import AppShell from "./layouts/AppShell";
import DashboardPage from "./pages/DashboardPage";
import LandingPage from "./pages/LandingPage";
import LoginPage from "./pages/LoginPage";
import NutritionPage from "./pages/NutritionPage";
import ProfilePage from "./pages/ProfilePage";
import RegisterPage from "./pages/RegisterPage";
import WorkoutPage from "./pages/WorkoutPage";


function ProtectedRoute({ user, children }) {
  if (!getAuthToken()) {
    return <Navigate to="/login" replace />;
  }
  return children;
}

export default function App() {
  const [user, setUser] = useState(null);
  const [booting, setBooting] = useState(
    Boolean(getAuthToken()) && !["/", "/login", "/register"].includes(window.location.pathname),
  );
  const location = useLocation();
  const navigate = useNavigate();
  const isPublicPath = ["/", "/login", "/register"].includes(location.pathname);

  useEffect(() => {
    if (!getAuthToken() || isPublicPath) {
      setBooting(false);
      return;
    }
    setBooting(true);
    me()
      .then(setUser)
      .catch(() => {
        setAuthToken("");
        navigate("/login");
      })
      .finally(() => setBooting(false));
  }, [isPublicPath, navigate]);

  if (booting) {
    return <div className="grid min-h-screen place-items-center bg-slate-50 text-sm text-slate-600">Loading</div>;
  }

  function handleAuth(result) {
    setUser(result.user);
    navigate("/dashboard");
  }

  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route path="/login" element={<LoginPage onAuth={handleAuth} />} />
      <Route path="/register" element={<RegisterPage onAuth={handleAuth} />} />
      <Route
        path="/*"
        element={
          <ProtectedRoute user={user}>
            <AppShell user={user} onLogout={() => setUser(null)}>
              <Routes>
                <Route path="/dashboard" element={<DashboardPage />} />
                <Route path="/profile" element={<ProfilePage />} />
                <Route path="/workout" element={<WorkoutPage />} />
                <Route path="/nutrition" element={<NutritionPage />} />
                <Route path="*" element={<Navigate to="/dashboard" replace />} />
              </Routes>
            </AppShell>
          </ProtectedRoute>
        }
      />
    </Routes>
  );
}
