import { Dumbbell, Salad, UserRound } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";

import { getProfile } from "../api/profile";
import { ProfileCompletionNotice } from "../components/ProfileCompletionNotice";
import { getProfileCompleteness } from "../utils/profileCompleteness";


const cards = [
  { to: "/profile", title: "Profile", text: "Body metrics, preferences, and AI advice.", icon: UserRound },
  { to: "/workout", title: "Workout", text: "Intent analysis before weekly plan generation.", icon: Dumbbell },
  { to: "/nutrition", title: "Nutrition", text: "Metrics, deterministic targets, and meal planning.", icon: Salad },
];

export default function DashboardPage() {
  const [profile, setProfile] = useState(null);

  useEffect(() => {
    getProfile()
      .then((data) => setProfile(data.profile || {}))
      .catch(() => setProfile(null));
  }, []);

  const completeness = useMemo(() => (profile ? getProfileCompleteness(profile) : null), [profile]);

  return (
    <div>
      <header className="mb-6">
        <h1 className="page-title">Dashboard</h1>
        <p className="page-subtitle">Work from profile data into workout and nutrition plans.</p>
      </header>

      <div className="grid gap-4 md:grid-cols-3">
        {cards.map((card) => {
          const Icon = card.icon;
          return (
            <Link key={card.to} to={card.to} className="section block transition hover:-translate-y-0.5 hover:shadow-md">
              <Icon className="mb-4 text-brand-600" size={28} />
              <h2 className="text-lg font-semibold">{card.title}</h2>
              <p className="mt-2 text-sm leading-6 text-slate-500">{card.text}</p>
            </Link>
          );
        })}
      </div>
    </div>
  );
}
