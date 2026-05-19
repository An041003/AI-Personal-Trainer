import {
  BarChart3,
  CalendarDays,
  Check,
  Mail,
  Play,
  Plus,
  Ruler,
  Utensils,
} from "lucide-react";
import { Link } from "react-router-dom";

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-white text-slate-900">
      <header className="sticky top-0 z-50 border-b border-slate-200/60 bg-white/80 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3">
          <Link className="flex items-center gap-3" to="/">
            <div className="grid h-10 w-10 place-items-center rounded-xl bg-emerald-600 text-white shadow-sm">
              <span className="text-lg font-extrabold">A</span>
            </div>
            <div className="leading-tight">
              <div className="text-base font-semibold">AIPT</div>
              <div className="text-xs text-slate-500">AI Personal Trainer</div>
            </div>
          </Link>

          <nav className="hidden items-center gap-6 text-sm text-slate-600 md:flex">
            <a href="#features" className="hover:text-slate-900">
              Tính năng
            </a>
            <a href="#how" className="hover:text-slate-900">
              Cách hoạt động
            </a>
            <a href="#demo" className="hover:text-slate-900">
              Demo
            </a>
            <a href="#faq" className="hover:text-slate-900">
              FAQ
            </a>
          </nav>

          <div className="flex items-center gap-2">
            <Link
              to="/register"
              className="rounded-xl bg-blue-600 px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-blue-700 active:scale-[0.99]"
            >
              Đăng ký
            </Link>
            <Link
              to="/login"
              className="rounded-xl bg-emerald-600 px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-emerald-700 active:scale-[0.99]"
            >
              Đăng nhập
            </Link>
          </div>
        </div>
      </header>

      <section className="relative min-h-[calc(100vh-65px)] overflow-hidden">
        <div
          className="absolute inset-0 bg-cover bg-center"
          style={{
            backgroundImage:
              "url(https://images.unsplash.com/photo-1517836357463-d25dfeac3438?auto=format&fit=crop&w=2000&q=80)",
          }}
          aria-hidden="true"
        />
        <div
          className="absolute inset-0 bg-gradient-to-b from-emerald-700/75 via-emerald-700/55 to-emerald-900/75"
          aria-hidden="true"
        />

        <div className="relative mx-auto flex min-h-[calc(100vh-65px)] max-w-6xl items-center px-4 py-20 md:py-24">
          <div className="mx-auto max-w-3xl text-center text-white">
            <div className="inline-flex items-center gap-2 rounded-full bg-white/10 px-4 py-2 text-xs font-semibold tracking-wide ring-1 ring-white/20">
              <span className="h-2 w-2 rounded-full bg-lime-300" />
              Lịch tập và thực đơn cá nhân hóa theo chỉ số cơ thể
            </div>

            <h1 className="mt-6 text-4xl font-extrabold leading-tight md:text-6xl">
              AIPT
              <span className="block text-3xl md:text-5xl">AI Personal Trainer</span>
            </h1>

            <p className="mx-auto mt-5 max-w-2xl text-base font-semibold text-white md:text-xl">
              Biến mục tiêu thành hiện thực với tập luyện và dinh dưỡng tối ưu bằng AI.
            </p>

            <p className="mx-auto mt-4 max-w-2xl text-base text-white/85 md:text-lg">
              Nhập chỉ số cơ thể, mục tiêu và lịch rảnh. AIPT tạo kế hoạch tập và thực đơn theo ngày,
              bám sát calories và macro, dễ theo dõi tiến độ.
            </p>

            <div className="mt-8 flex flex-col items-center justify-center gap-3 sm:flex-row">
              <Link
                to="/register"
                className="w-full rounded-2xl bg-orange-500 px-6 py-3 text-center text-sm font-bold text-white shadow-md transition hover:bg-orange-600 active:scale-[0.99] sm:w-auto"
              >
                Trải nghiệm ngay
              </Link>
              <a
                href="#demo"
                className="w-full rounded-2xl bg-white px-6 py-3 text-center text-sm font-bold text-slate-900 shadow-md transition hover:bg-slate-100 active:scale-[0.99] sm:w-auto"
              >
                Xem demo
              </a>
            </div>

            <div className="mt-8 flex flex-col items-center justify-center gap-3 text-xs text-white/80 sm:flex-row">
              <div className="rounded-full bg-white/10 px-4 py-2 ring-1 ring-white/15">Tạo plan trong 2 phút</div>
              <div className="rounded-full bg-white/10 px-4 py-2 ring-1 ring-white/15">Theo dõi tiến độ hằng ngày</div>
              <div className="rounded-full bg-white/10 px-4 py-2 ring-1 ring-white/15">Phù hợp lịch bận rộn</div>
            </div>
          </div>
        </div>
      </section>

      <section id="features" className="mx-auto max-w-6xl px-4 py-16 md:py-20">
        <div className="text-center">
          <h2 className="text-2xl font-extrabold md:text-3xl">Tính năng nổi bật</h2>
          <p className="mx-auto mt-3 max-w-2xl text-sm text-slate-600 md:text-base">
            Tập trung vào thứ bạn cần nhất: rõ mục tiêu, dễ thực hiện, theo dõi được kết quả.
          </p>
        </div>

        <div className="mt-10 grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
          <FeatureCard
            title="Theo dõi tiến độ"
            desc="Ghi nhận buổi tập, calories, nước và thói quen hằng ngày."
            icon={<BarChart3 className="h-7 w-7" />}
          />
          <FeatureCard
            title="AI tư vấn dinh dưỡng"
            desc="Gợi ý thực đơn theo mục tiêu, sở thích và món không thích."
            icon={<Utensils className="h-7 w-7" />}
          />
          <FeatureCard
            title="Lịch tập cá nhân"
            desc="Tạo lịch theo số buổi, thời gian rảnh và level hiện tại."
            icon={<CalendarDays className="h-7 w-7" />}
          />
          <FeatureCard
            title="Tính chỉ số cơ thể"
            desc="Tính BMI, BMR, TDEE và mục tiêu macro rõ ràng."
            icon={<Ruler className="h-7 w-7" />}
          />
        </div>
      </section>

      <section id="how" className="bg-slate-50">
        <div className="mx-auto max-w-6xl px-4 py-16 md:py-20">
          <div className="text-center">
            <h2 className="text-2xl font-extrabold md:text-3xl">Cách hoạt động</h2>
            <p className="mx-auto mt-3 max-w-2xl text-sm text-slate-600 md:text-base">
              Quy trình đơn giản, tập trung vào dữ liệu cá nhân và kế hoạch dễ theo.
            </p>
          </div>

          <div className="mt-10 grid gap-4 md:grid-cols-4">
            <StepCard num="01" title="Nhập chỉ số" desc="Chiều cao, cân nặng, mục tiêu, lịch rảnh và sở thích." />
            <StepCard num="02" title="Tính mục tiêu" desc="Tính calories và macro theo tình trạng và mức hoạt động." />
            <StepCard num="03" title="Sinh kế hoạch" desc="Tạo lịch tập và thực đơn theo ngày, có phân bổ hợp lý." />
            <StepCard num="04" title="Theo dõi và tối ưu" desc="Cập nhật tiến độ, chỉnh plan theo mức độ bận và kết quả." />
          </div>
        </div>
      </section>

      <section id="demo" className="mx-auto max-w-6xl px-4 py-16 md:py-20">
        <div className="text-center">
          <h2 className="text-2xl font-extrabold md:text-3xl">Xem hoạt động như thế nào</h2>
          <p className="mx-auto mt-3 max-w-2xl text-sm text-slate-600 md:text-base">
            Khu vực này có thể thay bằng video demo khi bạn có bản deploy ổn định.
          </p>
        </div>

        <div className="mt-10 overflow-hidden rounded-3xl border border-slate-200 bg-white shadow-sm">
          <div className="aspect-video w-full bg-slate-900/5">
            <div className="flex h-full w-full items-center justify-center">
              <div className="text-center">
                <div className="mx-auto grid h-14 w-14 place-items-center rounded-2xl bg-emerald-600 text-white shadow-sm">
                  <Play className="h-7 w-7 fill-current" />
                </div>
                <p className="mt-3 text-sm font-semibold text-slate-800">Khu vực video demo</p>
                <p className="mt-1 text-xs text-slate-500">Thay bằng iframe YouTube hoặc video tự host</p>
              </div>
            </div>
          </div>

          <div className="flex flex-col items-center justify-between gap-3 px-6 py-6 sm:flex-row">
            <div className="text-sm">
              <div className="font-semibold">Bắt đầu với AIPT</div>
              <div className="text-slate-600">Tạo tài khoản để nhập chỉ số và tạo plan đầu tiên</div>
            </div>
            <Link
              to="/register"
              className="rounded-2xl bg-emerald-600 px-5 py-3 text-sm font-bold text-white shadow-sm transition hover:bg-emerald-700 active:scale-[0.99]"
            >
              Đăng ký ngay
            </Link>
          </div>
        </div>
      </section>

      <section id="faq" className="bg-slate-50">
        <div className="mx-auto max-w-6xl px-4 py-16 md:py-20">
          <div className="text-center">
            <h2 className="text-2xl font-extrabold md:text-3xl">FAQ</h2>
            <p className="mx-auto mt-3 max-w-2xl text-sm text-slate-600 md:text-base">
              Một vài câu hỏi phổ biến trước khi bắt đầu.
            </p>
          </div>

          <div className="mx-auto mt-10 max-w-3xl space-y-3">
            <FaqItem
              q="AIPT có thay thế bác sĩ hoặc chuyên gia không?"
              a="Không. AIPT là công cụ hỗ trợ lập kế hoạch. Nếu bạn có bệnh lý hoặc chống chỉ định, hãy tham khảo chuyên gia y tế."
            />
            <FaqItem
              q="Tôi bận, ít thời gian thì có dùng được không?"
              a="Có. Bạn chỉ cần chọn số buổi và khung giờ rảnh, hệ thống sẽ tạo lịch phù hợp."
            />
            <FaqItem
              q="Có tùy chỉnh món thích và món không thích không?"
              a="Có. Bạn có thể thêm sở thích ăn uống để thực đơn hợp hơn và dễ theo hơn."
            />
            <FaqItem
              q="Tôi có thể xem lại lịch sử không?"
              a="Có. Bạn có thể theo dõi tiến độ theo ngày và xem lại kế hoạch đã tạo."
            />
          </div>
        </div>
      </section>

      <footer className="bg-slate-900 text-slate-200">
        <div className="mx-auto max-w-6xl px-4 py-14">
          <div className="grid gap-10 md:grid-cols-3">
            <div>
              <div className="flex items-center gap-3">
                <div className="grid h-10 w-10 place-items-center rounded-xl bg-emerald-600 text-white">
                  <span className="text-lg font-extrabold">A</span>
                </div>
                <div>
                  <div className="text-base font-semibold">AIPT</div>
                  <div className="text-xs text-slate-400">AI Personal Trainer</div>
                </div>
              </div>
              <p className="mt-4 max-w-sm text-sm text-slate-400">
                Lịch tập và thực đơn cá nhân hóa, hỗ trợ bạn theo dõi mục tiêu và duy trì thói quen.
              </p>

              <div className="mt-5 flex items-center gap-3">
                <SocialIcon />
                <SocialIcon />
                <SocialIcon />
              </div>
            </div>

            <div className="grid gap-2 text-sm">
              <div className="text-base font-semibold text-white">Liên kết</div>
              <a href="#features" className="text-slate-400 hover:text-white">
                Tính năng
              </a>
              <a href="#how" className="text-slate-400 hover:text-white">
                Cách hoạt động
              </a>
              <a href="#demo" className="text-slate-400 hover:text-white">
                Demo
              </a>
              <Link to="/login" className="text-slate-400 hover:text-white">
                Đăng nhập
              </Link>
              <Link to="/register" className="text-slate-400 hover:text-white">
                Đăng ký
              </Link>
            </div>

            <div>
              <div className="text-base font-semibold text-white">Nhận cập nhật</div>
              <p className="mt-2 text-sm text-slate-400">
                Đăng ký email để nhận thông tin về bản cập nhật tính năng.
              </p>
              <form className="mt-4 flex gap-2" onSubmit={(event) => event.preventDefault()}>
                <input
                  type="email"
                  placeholder="Email của bạn"
                  className="w-full rounded-xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-white outline-none placeholder:text-slate-500 focus:border-emerald-500/70"
                />
                <button className="inline-flex items-center gap-2 rounded-xl bg-emerald-600 px-5 py-3 text-sm font-bold text-white transition hover:bg-emerald-700 active:scale-[0.99]">
                  <Mail className="h-4 w-4" />
                  Gửi
                </button>
              </form>
            </div>
          </div>

          <div className="mt-10 border-t border-white/10 pt-6 text-xs text-slate-500">
            © {new Date().getFullYear()} AIPT. All rights reserved.
          </div>
        </div>
      </footer>
    </div>
  );
}

function FeatureCard({ title, desc, icon }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-6 text-center shadow-sm transition hover:-translate-y-0.5 hover:shadow-md">
      <div className="mx-auto grid h-12 w-12 place-items-center rounded-2xl bg-emerald-50 text-emerald-700 ring-1 ring-emerald-100">
        {icon}
      </div>
      <div className="mt-4 text-base font-bold">{title}</div>
      <div className="mt-2 text-sm text-slate-600">{desc}</div>
    </div>
  );
}

function StepCard({ num, title, desc }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
      <div className="text-xs font-extrabold tracking-widest text-emerald-700">{num}</div>
      <div className="mt-2 text-base font-bold">{title}</div>
      <div className="mt-2 text-sm text-slate-600">{desc}</div>
    </div>
  );
}

function FaqItem({ q, a }) {
  return (
    <details className="group rounded-2xl border border-slate-200 bg-white px-5 py-4 shadow-sm">
      <summary className="flex cursor-pointer list-none items-center justify-between gap-3">
        <span className="text-sm font-semibold text-slate-900">{q}</span>
        <span className="grid h-9 w-9 shrink-0 place-items-center rounded-xl bg-slate-50 text-slate-600 ring-1 ring-slate-200 transition group-open:rotate-45">
          <Plus className="h-5 w-5" />
        </span>
      </summary>
      <div className="mt-3 text-sm text-slate-600">{a}</div>
    </details>
  );
}

function SocialIcon() {
  return (
    <button
      type="button"
      className="grid h-10 w-10 place-items-center rounded-xl bg-white/5 text-slate-300 ring-1 ring-white/10 transition hover:bg-white/10 hover:text-white"
      aria-label="social"
    >
      <Check className="h-5 w-5" />
    </button>
  );
}
