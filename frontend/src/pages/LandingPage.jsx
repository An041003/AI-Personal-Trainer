import {
  ArrowRight,
  BarChart3,
  CalendarDays,
  CheckCircle2,
  Dumbbell,
  Ruler,
  ShieldCheck,
  Sparkles,
  Utensils,
} from "lucide-react";
import { Link } from "react-router-dom";

const features = [
  {
    title: "Profile as the source of truth",
    desc: "Height, weight, body measurements, goals, food preferences, and health limits are reused across every planning flow.",
    icon: Ruler,
  },
  {
    title: "Workout intent comes first",
    desc: "AI turns your goal into focus muscles and weekly training intent before any workout plan is generated.",
    icon: Dumbbell,
  },
  {
    title: "Nutrition uses a rulebase",
    desc: "Calories, macros, and medical constraints are calculated with clear logic before the meal draft is created.",
    icon: Utensils,
  },
  {
    title: "Plans stay available",
    desc: "Return to your latest workout and meal plans without regenerating everything from scratch.",
    icon: CalendarDays,
  },
];

const steps = [
  "Complete your profile and body metrics.",
  "Review BMI, BMR, TDEE, and safety-aware advice.",
  "Generate workout or nutrition plans from saved profile data.",
  "Track your latest plan and adjust it when your schedule changes.",
];

const faqs = [
  {
    q: "Does AIPT replace a doctor or medical professional?",
    a: "No. AIPT is a planning assistant. If you have a medical condition or contraindication, you should consult a qualified professional.",
  },
  {
    q: "Do I need to enter body metrics on every page?",
    a: "No. Your profile is the shared data source for workout, nutrition, and advice.",
  },
  {
    q: "Does workout planning generate directly from a goal prompt?",
    a: "No. The app analyzes intent first to identify focus muscles, then generates a plan from that structured intent.",
  },
  {
    q: "Does the meal plan invent calories?",
    a: "No. The backend resolves ingredients to NutritionAtom records and calculates totals from seeded nutrition data.",
  },
];

export default function LandingPage() {
  return (
    <div className="min-h-[100dvh] bg-[#f3f7ef] text-slate-950">
      <header className="sticky top-0 z-50 border-b border-black/10 bg-[#f3f7ef]/88 backdrop-blur-xl">
        <div className="mx-auto flex h-[72px] max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
          <Link className="flex items-center gap-3" to="/">
            <img
              src="/android-chrome-192x192.png"
              alt=""
              className="h-11 w-11 rounded-2xl bg-white object-cover shadow-lg shadow-brand-900/15 ring-1 ring-black/10"
            />
            <span className="leading-tight">
              <span className="block text-base font-semibold tracking-tight">AIPT</span>
              <span className="block text-xs font-medium text-slate-500">AI Personal Trainer</span>
            </span>
          </Link>

          <nav className="hidden items-center gap-7 text-sm font-semibold text-slate-600 md:flex">
            <a href="#features" className="transition hover:text-brand-800">
              Features
            </a>
            <a href="#how" className="transition hover:text-brand-800">
              How it works
            </a>
            <a href="#preview" className="transition hover:text-brand-800">
              Preview
            </a>
            <a href="#faq" className="transition hover:text-brand-800">
              FAQ
            </a>
          </nav>

          <div className="flex items-center gap-2">
            <Link
              to="/login"
              className="hidden rounded-2xl border border-black/10 bg-white/75 px-4 py-2.5 text-sm font-semibold text-slate-700 transition hover:bg-white sm:inline-flex"
            >
              Sign in
            </Link>
            <Link
              to="/register"
              className="inline-flex items-center gap-2 rounded-2xl bg-brand-900 px-4 py-2.5 text-sm font-semibold text-white shadow-lg shadow-brand-900/15 transition hover:-translate-y-0.5 hover:bg-brand-800 active:translate-y-0"
            >
              Sign up
              <ArrowRight className="h-4 w-4" />
            </Link>
          </div>
        </div>
      </header>

      <main>
        <section className="relative overflow-hidden">
          <div
            className="absolute inset-0 bg-cover bg-center"
            style={{
              backgroundImage:
                "url(https://images.unsplash.com/photo-1518611012118-696072aa579a?auto=format&fit=crop&w=2200&q=85)",
            }}
            aria-hidden="true"
          />
          <div className="absolute inset-0 bg-gradient-to-r from-brand-950/95 via-brand-900/72 to-brand-900/18" aria-hidden="true" />

          <div className="relative mx-auto flex min-h-[76dvh] max-w-7xl items-center px-4 py-16 sm:px-6 lg:px-8">
            <div className="max-w-3xl text-white">
              <p className="inline-flex rounded-full border border-white/18 bg-white/10 px-4 py-2 text-xs font-semibold text-lime-100 backdrop-blur">
                Personalized workout and nutrition from your profile
              </p>
              <h1 className="mt-6 text-5xl font-semibold leading-[1.02] tracking-tight sm:text-6xl lg:text-7xl">
                AI Personal Trainer
              </h1>
              <p className="mt-6 max-w-2xl text-lg font-medium leading-8 text-white/82">
                Build workout and meal plans from your body metrics, goals, preferences, and health limits.
              </p>

              <div className="mt-8 flex flex-col gap-3 sm:flex-row">
                <Link
                  to="/register"
                  className="inline-flex h-12 items-center justify-center gap-2 rounded-2xl bg-white px-5 text-sm font-bold text-brand-950 shadow-xl transition hover:-translate-y-0.5 hover:bg-lime-50 active:translate-y-0"
                >
                  Start with your profile
                  <ArrowRight className="h-4 w-4" />
                </Link>
                <a
                  href="#preview"
                  className="inline-flex h-12 items-center justify-center rounded-2xl border border-white/24 bg-white/10 px-5 text-sm font-bold text-white backdrop-blur transition hover:-translate-y-0.5 hover:bg-white/16 active:translate-y-0"
                >
                  View preview
                </a>
              </div>

              <div className="mt-8 grid max-w-2xl gap-3 text-sm text-white/78 sm:grid-cols-3">
                <HeroFact icon={ShieldCheck} text="Not medical advice" />
                <HeroFact icon={BarChart3} text="Metrics from profile" />
                <HeroFact icon={Sparkles} text="AI runs on backend" />
              </div>
            </div>
          </div>
        </section>

        <section id="features" className="mx-auto grid max-w-7xl gap-5 px-4 py-14 sm:px-6 md:grid-cols-2 lg:grid-cols-4 lg:px-8">
          {features.map((feature) => {
            const Icon = feature.icon;
            return (
              <article key={feature.title} className="surface-panel p-5 transition hover:-translate-y-1 hover:shadow-[0_26px_80px_rgba(35,48,30,0.14)]">
                <div className="grid h-12 w-12 place-items-center rounded-2xl bg-brand-50 text-brand-800 ring-1 ring-brand-100">
                  <Icon className="h-6 w-6" />
                </div>
                <h2 className="mt-5 text-lg font-semibold tracking-tight">{feature.title}</h2>
                <p className="mt-2 text-sm leading-6 text-slate-600">{feature.desc}</p>
              </article>
            );
          })}
        </section>

        <section id="how" className="border-y border-black/10 bg-white/55">
          <div className="mx-auto grid max-w-7xl gap-10 px-4 py-16 sm:px-6 lg:grid-cols-[0.9fr_1.1fr] lg:px-8">
            <div>
              <p className="text-sm font-semibold text-brand-800">Planning flow</p>
              <h2 className="mt-3 max-w-xl text-4xl font-semibold tracking-tight md:text-5xl">Start from real profile data, not a blank prompt.</h2>
              <p className="mt-5 max-w-xl text-base leading-7 text-slate-600">
                AIPT keeps profile data at the center so workout, nutrition, and advice stay aligned.
              </p>
            </div>

            <div className="grid gap-3">
              {steps.map((step, index) => (
                <div key={step} className="flex items-start gap-4 rounded-[1.25rem] border border-black/10 bg-white/80 p-4">
                  <span className="grid h-10 w-10 shrink-0 place-items-center rounded-2xl bg-brand-900 text-sm font-bold text-white">
                    {index + 1}
                  </span>
                  <p className="pt-2 text-sm font-semibold leading-6 text-slate-800">{step}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section id="preview" className="mx-auto grid max-w-7xl gap-8 px-4 py-16 sm:px-6 lg:grid-cols-[1fr_1.15fr] lg:px-8">
          <div>
            <p className="text-sm font-semibold text-brand-800">Preview</p>
            <h2 className="mt-3 text-4xl font-semibold tracking-tight md:text-5xl">One app for training and meal planning.</h2>
            <p className="mt-5 max-w-xl text-base leading-7 text-slate-600">
              The product experience is built for repeat actions: review metrics, generate plans, edit plans, and return to the latest version.
            </p>
            <div className="mt-6 flex flex-wrap gap-2">
              <span className="muted-chip">
                <CheckCircle2 className="h-4 w-4 text-brand-700" />
                Token auth REST API
              </span>
              <span className="muted-chip">
                <CheckCircle2 className="h-4 w-4 text-brand-700" />
                PostgreSQL and pgvector
              </span>
              <span className="muted-chip">
                <CheckCircle2 className="h-4 w-4 text-brand-700" />
                OpenAI through backend
              </span>
            </div>
          </div>

          <div className="surface-panel overflow-hidden p-4">
            <div className="rounded-[1.35rem] bg-brand-950 p-5 text-white">
              <div className="flex items-center justify-between gap-4">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.24em] text-lime-100/65">Today</p>
                  <h3 className="mt-2 text-2xl font-semibold tracking-tight">Foundation is ready</h3>
                </div>
                <BarChart3 className="h-8 w-8 text-lime-100" />
              </div>
              <div className="mt-6 grid gap-3 sm:grid-cols-3">
                <Metric label="BMI" value="22.8" />
                <Metric label="TDEE" value="2400" />
                <Metric label="Protein" value="145g" />
              </div>
            </div>

            <div className="grid gap-3 pt-4 md:grid-cols-2">
              <PreviewCard title="Workout intent" text="shoulders, core, back" icon={Dumbbell} />
              <PreviewCard title="Meal target" text="4 meals, balanced macros" icon={Utensils} />
            </div>
          </div>
        </section>

        <section id="faq" className="bg-white/55">
          <div className="mx-auto max-w-4xl px-4 py-16 sm:px-6 lg:px-8">
            <div className="text-center">
              <p className="text-sm font-semibold text-brand-800">FAQ</p>
              <h2 className="mt-3 text-4xl font-semibold tracking-tight md:text-5xl">What to know before using AIPT.</h2>
            </div>
            <div className="mt-9 space-y-3">
              {faqs.map((item) => (
                <details key={item.q} className="group rounded-[1.25rem] border border-black/10 bg-white/80 p-5 shadow-sm">
                  <summary className="flex cursor-pointer list-none items-center justify-between gap-4 text-left">
                    <span className="text-sm font-semibold text-slate-950">{item.q}</span>
                    <span className="text-brand-800 transition group-open:rotate-45">+</span>
                  </summary>
                  <p className="mt-3 text-sm leading-6 text-slate-600">{item.a}</p>
                </details>
              ))}
            </div>
          </div>
        </section>
      </main>

      <footer className="border-t border-black/10 bg-brand-950 text-white">
        <div className="mx-auto flex max-w-7xl flex-col gap-6 px-4 py-8 text-sm sm:px-6 md:flex-row md:items-center md:justify-between lg:px-8">
          <div>
            <p className="font-semibold">AIPT</p>
            <p className="mt-1 text-white/58">AI Personal Trainer for workout and nutrition planning.</p>
          </div>
          <div className="flex flex-wrap gap-4 text-white/70">
            <a href="#features" className="hover:text-white">
              Features
            </a>
            <a href="#how" className="hover:text-white">
              How it works
            </a>
            <Link to="/login" className="hover:text-white">
              Sign in
            </Link>
          </div>
        </div>
      </footer>
    </div>
  );
}

function HeroFact({ icon: Icon, text }) {
  return (
    <div className="flex items-center gap-2 rounded-2xl border border-white/14 bg-white/9 px-3 py-2 backdrop-blur">
      <Icon className="h-4 w-4 shrink-0 text-lime-100" />
      <span>{text}</span>
    </div>
  );
}

function Metric({ label, value }) {
  return (
    <div className="rounded-2xl bg-white/9 p-4 ring-1 ring-white/12">
      <p className="text-xs font-semibold text-lime-100/70">{label}</p>
      <p className="mt-2 text-2xl font-semibold tracking-tight">{value}</p>
    </div>
  );
}

function PreviewCard({ title, text, icon: Icon }) {
  return (
    <div className="rounded-[1.25rem] border border-black/10 bg-white/80 p-4">
      <div className="flex items-start gap-3">
        <div className="grid h-10 w-10 place-items-center rounded-2xl bg-brand-50 text-brand-800">
          <Icon className="h-5 w-5" />
        </div>
        <div>
          <p className="font-semibold text-slate-950">{title}</p>
          <p className="mt-1 text-sm text-slate-600">{text}</p>
        </div>
      </div>
    </div>
  );
}
