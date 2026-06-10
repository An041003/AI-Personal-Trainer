import { useEffect, useMemo, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";

import { login, register } from "../api/auth";

export default function AuthPage({ onAuth }) {
  const navigate = useNavigate();
  const location = useLocation();

  const initialMode = useMemo(
    () => (location.pathname.startsWith("/register") ? "signup" : "signin"),
    [location.pathname],
  );

  const [mode, setMode] = useState(initialMode);
  const [signin, setSignin] = useState({ username: "", password: "" });
  const [signup, setSignup] = useState({ username: "", email: "", password: "" });
  const [loadingMode, setLoadingMode] = useState("");
  const [errorMsg, setErrorMsg] = useState("");

  useEffect(() => {
    setMode(initialMode);
    setErrorMsg("");
  }, [initialMode]);

  const isRightActive = mode === "signup";
  const isLoading = Boolean(loadingMode);

  function goSignUp() {
    setMode("signup");
    setErrorMsg("");
    navigate("/register", { replace: true });
  }

  function goSignIn() {
    setMode("signin");
    setErrorMsg("");
    navigate("/login", { replace: true });
  }

  function finishAuth(result) {
    if (onAuth) {
      onAuth(result);
      return;
    }
    navigate("/dashboard", { replace: true });
  }

  async function onSubmitSignIn(event) {
    event.preventDefault();
    setErrorMsg("");
    setLoadingMode("signin");

    try {
      const data = await login({
        username: signin.username,
        password: signin.password,
      });
      finishAuth(data);
    } catch (err) {
      setErrorMsg(formatAuthError(err, "Sign in failed."));
      console.error(err);
    } finally {
      setLoadingMode("");
    }
  }

  async function onSubmitSignUp(event) {
    event.preventDefault();
    setErrorMsg("");
    setLoadingMode("signup");

    try {
      const data = await register({
        username: signup.username,
        email: signup.email,
        password: signup.password,
      });
      finishAuth(data);
    } catch (err) {
      setErrorMsg(formatAuthError(err, "Sign up failed."));
      console.error(err);
    } finally {
      setLoadingMode("");
    }
  }

  return (
    <main className="flex min-h-[100dvh] flex-col items-center justify-center bg-[#f3f7ef] px-4 py-8">
      <h2 className="mb-6 text-center text-3xl font-extrabold text-brand-950">
        Plan smarter! Train better!
      </h2>

      <div className="relative min-h-[560px] w-full max-w-[880px] overflow-hidden rounded-3xl border border-black/10 bg-white/85 shadow-[0_24px_80px_rgba(35,48,30,0.14)] backdrop-blur-xl md:h-[520px] md:min-h-0">
        <div
          className={[
            "absolute left-0 top-0 h-full w-full transition-all duration-700 ease-in-out md:w-1/2",
            isRightActive
              ? "translate-x-0 opacity-100 z-20 pointer-events-auto md:translate-x-full"
              : "translate-x-0 opacity-0 z-[1] pointer-events-none",
          ].join(" ")}
        >
          <form
            onSubmit={onSubmitSignUp}
            className="flex h-full flex-col items-center justify-center gap-3 px-6 text-center sm:px-12"
          >
            <h1 className="text-3xl font-extrabold text-slate-900">Create Account</h1>

            <div className="mt-2 flex items-center justify-center gap-3">
              <SocialCircle label="Facebook" />
              <SocialCircle label="Google" />
              <SocialCircle label="X" />
            </div>

            <span className="text-xs text-slate-500">or use your email for registration</span>

            <AuthInput
              autoComplete="username"
              placeholder="Username"
              required
              value={signup.username}
              onChange={(value) => setSignup((current) => ({ ...current, username: value }))}
            />
            <AuthInput
              autoComplete="email"
              type="email"
              placeholder="Email (optional)"
              value={signup.email}
              onChange={(value) => setSignup((current) => ({ ...current, email: value }))}
            />
            <AuthInput
              autoComplete="new-password"
              type="password"
              placeholder="Password"
              required
              minLength={8}
              value={signup.password}
              onChange={(value) => setSignup((current) => ({ ...current, password: value }))}
            />

            {errorMsg && isRightActive ? <ErrorBox msg={errorMsg} /> : null}

            <button
              type="submit"
              disabled={isLoading}
              className="mt-2 rounded-full border border-brand-800 bg-brand-800 px-12 py-3 text-xs font-extrabold uppercase tracking-widest text-white shadow-lg shadow-brand-900/15 transition hover:bg-brand-900 active:scale-95 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {loadingMode === "signup" ? "PLEASE WAIT..." : "SIGN UP"}
            </button>

            <button
              type="button"
              onClick={goSignIn}
              className="mt-1 text-sm font-semibold text-brand-700 hover:text-brand-900 md:hidden"
            >
              Already have an account?
            </button>
          </form>
        </div>

        <div
          className={[
            "absolute left-0 top-0 h-full w-full transition-all duration-700 ease-in-out md:w-1/2",
            isRightActive
              ? "translate-x-0 opacity-0 z-10 pointer-events-none md:translate-x-full"
              : "translate-x-0 opacity-100 z-10 pointer-events-auto",
          ].join(" ")}
        >
          <form
            onSubmit={onSubmitSignIn}
            className="flex h-full flex-col items-center justify-center gap-3 px-6 text-center sm:px-12"
          >
            <h1 className="text-3xl font-extrabold text-slate-900">Sign in</h1>

            <div className="mt-2 flex items-center justify-center gap-3">
              <SocialCircle label="Facebook" />
              <SocialCircle label="Google" />
              <SocialCircle label="X" />
            </div>

            <span className="text-xs text-slate-500">or use your account</span>

            <AuthInput
              autoComplete="username"
              placeholder="Username"
              required
              value={signin.username}
              onChange={(value) => setSignin((current) => ({ ...current, username: value }))}
            />
            <AuthInput
              autoComplete="current-password"
              type="password"
              placeholder="Password"
              required
              value={signin.password}
              onChange={(value) => setSignin((current) => ({ ...current, password: value }))}
            />

            <button
              type="button"
              className="text-sm text-slate-700 hover:text-slate-900"
              onClick={() => window.alert("TODO: forgot password")}
            >
              Forgot your password?
            </button>

            {errorMsg && !isRightActive ? <ErrorBox msg={errorMsg} /> : null}

            <button
              type="submit"
              disabled={isLoading}
              className="mt-1 rounded-full border border-brand-800 bg-brand-800 px-12 py-3 text-xs font-extrabold uppercase tracking-widest text-white shadow-lg shadow-brand-900/15 transition hover:bg-brand-900 active:scale-95 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {loadingMode === "signin" ? "PLEASE WAIT..." : "SIGN IN"}
            </button>

            <button
              type="button"
              onClick={goSignUp}
              className="mt-1 text-sm font-semibold text-brand-700 hover:text-brand-900 md:hidden"
            >
              Need a new account?
            </button>
          </form>
        </div>

        <div
          className={[
            "absolute left-1/2 top-0 z-30 hidden h-full w-1/2 overflow-hidden transition-transform duration-700 ease-in-out md:block",
            isRightActive ? "-translate-x-full" : "translate-x-0",
          ].join(" ")}
        >
          <div
            className={[
              "relative left-[-100%] h-full w-[200%] bg-gradient-to-r from-brand-800 via-brand-700 to-brand-950 text-white transition-transform duration-700 ease-in-out",
              isRightActive ? "translate-x-1/2" : "translate-x-0",
            ].join(" ")}
          >
            <div
              className={[
                "absolute top-0 flex h-full w-1/2 flex-col items-center justify-center px-10 text-center transition-transform duration-700 ease-in-out",
                isRightActive ? "translate-x-0" : "-translate-x-[20%]",
              ].join(" ")}
            >
              <h1 className="text-4xl font-extrabold">Welcome Back!</h1>
              <p className="mt-4 max-w-sm text-sm leading-6 text-white/90">
                To keep connected with us please login with your personal info
              </p>
              <button
                type="button"
                onClick={goSignIn}
                className="mt-7 rounded-full border border-white bg-transparent px-12 py-3 text-xs font-extrabold uppercase tracking-widest transition hover:bg-white/10 active:scale-95"
              >
                Sign In
              </button>
            </div>

            <div
              className={[
                "absolute right-0 top-0 flex h-full w-1/2 flex-col items-center justify-center px-10 text-center transition-transform duration-700 ease-in-out",
                isRightActive ? "translate-x-[20%]" : "translate-x-0",
              ].join(" ")}
            >
              <h1 className="text-4xl font-extrabold">Hello, Friend!</h1>
              <p className="mt-4 max-w-sm text-sm leading-6 text-white/90">
                Enter your personal details and start journey with us
              </p>
              <button
                type="button"
                onClick={goSignUp}
                className="mt-7 rounded-full border border-white bg-transparent px-12 py-3 text-xs font-extrabold uppercase tracking-widest transition hover:bg-white/10 active:scale-95"
              >
                Sign Up
              </button>
            </div>
          </div>
        </div>
      </div>

      <div className="mt-6 text-center">
        <Link className="inline-block text-sm font-semibold text-brand-700 hover:text-brand-950" to="/">
          Back to landing
        </Link>
      </div>
    </main>
  );
}

function AuthInput({ type = "text", placeholder, value, onChange, ...props }) {
  return (
    <input
      {...props}
      type={type}
      placeholder={placeholder}
      value={value}
      onChange={(event) => onChange(event.target.value)}
      className="w-full rounded-xl border border-black/5 bg-brand-50/65 px-4 py-3 text-sm text-slate-900 outline-none ring-1 ring-transparent transition placeholder:text-slate-400 focus:border-brand-600 focus:bg-white focus:ring-4 focus:ring-brand-600/10"
    />
  );
}

function SocialCircle({ label }) {
  return (
    <button
      type="button"
      aria-label={label}
      className="grid h-10 w-10 place-items-center rounded-full border border-brand-100 bg-white/75 text-brand-800 transition hover:bg-brand-50"
      onClick={() => window.alert(`TODO: ${label} auth`)}
    >
      <span className="text-sm font-bold">{label[0]}</span>
    </button>
  );
}

function ErrorBox({ msg }) {
  return (
    <div className="mt-2 w-full rounded-xl bg-red-50 px-4 py-3 text-left text-sm text-red-700 ring-1 ring-red-100">
      {msg}
    </div>
  );
}

function formatAuthError(err, fallback) {
  if (err?.message) return err.message;
  if (err?.data && typeof err.data === "object") return JSON.stringify(err.data);
  return fallback;
}
