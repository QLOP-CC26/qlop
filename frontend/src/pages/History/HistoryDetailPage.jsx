import { useState, useEffect, useMemo } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { ArrowLeft, ExternalLink, Sparkles, Check, AlertTriangle, Clock } from 'lucide-react';
import { Radar } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  RadialLinearScale,
  PointElement,
  LineElement,
  Filler,
  Tooltip,
  Legend,
} from 'chart.js';

ChartJS.register(RadialLinearScale, PointElement, LineElement, Filler, Tooltip, Legend);
import AppNavbar from '../../components/AppNavbar/AppNavbar';
import Footer from '../../components/Footer/Footer';

/* ── Career Pivot Loading Steps (UX hint dari API_CONTRACT.md) ── */
const PIVOT_STEPS = [
  'AI model is retrieving matching alternative roles…',
  'Analyzing fit and your transferable skills…',
  'AI is exploring career paths outside the database…',
  'Almost done — formatting your personalized career recommendations…',
];

/* ── Duration label formatter ── */
const FORMAT_DURATION = {
  LESS_THAN_TWO_HOURS: '< 2 hours',
  ONE_TO_FOUR_WEEKS: '1–4 weeks',
  ONE_TO_THREE_MONTHS: '1–3 months',
  THREE_TO_SIX_MONTHS: '3–6 months',
  SIX_TO_TWELVE_MONTHS: '6–12 months',
};
const fmtDuration = (d) => FORMAT_DURATION[d] || d;

/* ── Helpers ── */
const SectionCard = ({ children, className = '' }) => (
  <div className={`bg-white border border-black/[0.06] rounded-xl p-6 ${className}`}>
    {children}
  </div>
);

const DifficultyBadge = ({ level }) => {
  const map = {
    beginner: 'bg-emerald-50 text-emerald-700 border-emerald-200',
    intermediate: 'bg-amber-50 text-amber-700 border-amber-200',
    advanced: 'bg-red-50 text-red-700 border-red-200',
  };
  const cls = map[(level || '').toLowerCase()] || 'bg-[#F0F5FF] text-[#2563EB] border-blue-200';
  return (
    <span className={`text-xs font-semibold px-2 py-0.5 rounded-full border ${cls}`}>
      {level}
    </span>
  );
};

const TransitionBadge = ({ difficulty }) => {
  const map = {
    easy: 'bg-emerald-50 text-emerald-700 border-emerald-200',
    moderate: 'bg-amber-50 text-amber-700 border-amber-200',
    challenging: 'bg-red-50 text-red-700 border-red-200',
  };
  const cls = map[(difficulty || '').toLowerCase()] || 'bg-[#F0F5FF] text-[#2563EB] border-blue-200';
  const labels = { easy: 'Easy', moderate: 'Moderate', challenging: 'Challenging' };
  return (
    <span className={`text-xs font-semibold px-2.5 py-0.5 rounded-full border ${cls}`}>
      {labels[(difficulty || '').toLowerCase()] || difficulty}
    </span>
  );
};

/* ── Course Card ── */
const CourseCard = ({ course }) => (
  <a
    href={course.url || '#'}
    target="_blank"
    rel="noopener noreferrer"
    className="flex flex-col gap-3 p-5 bg-white border border-black/[0.06] rounded-xl hover:border-[#2563EB]/30 hover:shadow-[0_4px_20px_rgba(37,99,235,0.08)] transition-all duration-200 group"
  >
    <div className="flex items-start justify-between gap-2">
      <p className="text-sm font-semibold text-[#0D1C2D] group-hover:text-[#2563EB] transition-colors leading-snug flex-1">
        {course.name}
      </p>
      <ExternalLink className="w-3.5 h-3.5 text-[#C5C6CD] group-hover:text-[#2563EB] transition-colors flex-shrink-0 mt-0.5" />
    </div>

    <div className="flex items-center gap-2 flex-wrap">
      {course.difficulty && <DifficultyBadge level={course.difficulty} />}
      {course.duration && (
        <span className="flex items-center gap-1 text-xs text-[#75777D]">
          <Clock className="w-3 h-3" />
          {fmtDuration(course.duration)}
        </span>
      )}
      {course.match_score != null && (
        <span className="ml-auto text-xs font-bold text-[#2563EB]">
          {Math.round(course.match_score * 100)}% match
        </span>
      )}
    </div>

    {course.covered_skills?.length > 0 && (
      <div className="flex flex-wrap gap-1.5">
        {course.covered_skills.slice(0, 4).map((sk, i) => (
          <span key={i} className="text-xs px-2 py-0.5 bg-[#F0F5FF] border border-[#2563EB]/15 rounded-full text-[#45474C]">
            {sk}
          </span>
        ))}
        {course.covered_skills.length > 4 && (
          <span className="text-xs text-[#75777D]">+{course.covered_skills.length - 4} more</span>
        )}
      </div>
    )}
  </a>
);

/* ── Role Card (CareerPivot) ── */
const AlternativeRoleCard = ({ role }) => (
  <SectionCard className="flex flex-col gap-3">
    <div className="flex items-start justify-between gap-3">
      <div>
        <p className="text-base font-bold text-[#0D1C2D]">{role.role_name}</p>
        <p className="text-sm text-[#45474C] mt-1">{role.why_good_fit}</p>
      </div>
      <div className="flex flex-col items-end gap-1 flex-shrink-0">
        <span className="text-lg font-bold text-[#2563EB]">
          {Math.round(role.skill_overlap_pct ?? role.skill_readiness_pct ?? 0)}%
        </span>
        <TransitionBadge difficulty={role.transition_difficulty} />
      </div>
    </div>

    {role.transferable_skills && role.transferable_skills.length > 0 && (
      <div>
        <p className="text-xs font-semibold text-[#75777D] mb-1.5 uppercase tracking-wide">Transferable skills</p>
        <div className="flex flex-wrap gap-1.5">
          {(role.transferable_skills || []).slice(0, 6).map((sk, i) => (
            <span key={i} className="flex items-center gap-1 text-xs px-2 py-1 bg-emerald-50 border border-emerald-200 text-emerald-700 rounded-full font-medium">
              <Check className="w-3 h-3" /> {typeof sk === 'string' ? sk : sk.skill}
            </span>
          ))}
        </div>
      </div>
    )}

    {role.gap_skills && role.gap_skills.length > 0 && (
      <div>
        <p className="text-xs font-semibold text-[#75777D] mb-1.5 uppercase tracking-wide">Skills to develop</p>
        <div className="flex flex-wrap gap-1.5">
          {(role.gap_skills || role.skills_to_develop || []).slice(0, 5).map((sk, i) => (
            <span key={i} className="flex items-center gap-1 text-xs px-2 py-1 bg-amber-50 border border-amber-200 text-amber-700 rounded-full font-medium">
              <AlertTriangle className="w-3 h-3" /> {sk}
            </span>
          ))}
        </div>
      </div>
    )}

    {role.first_step && (
      <p className="text-xs text-[#45474C] italic border-t border-black/[0.05] pt-2">
        <span className="font-semibold not-italic">First step: </span>{role.first_step}
      </p>
    )}

    <div className="flex items-center gap-3 text-xs text-[#75777D] border-t border-black/[0.05] pt-2">
      {role.estimated_transition_time && (
        <span>⏱ {role.estimated_transition_time}</span>
      )}
      {role.estimated_transition_months && (
        <span>⏱ ~{role.estimated_transition_months} months</span>
      )}
      {role.market_demand && (
        <span className={`font-semibold ${role.market_demand === 'high' ? 'text-emerald-600' : role.market_demand === 'medium' ? 'text-amber-600' : 'text-red-500'}`}>
          {role.market_demand} demand
        </span>
      )}
    </div>
  </SectionCard>
);

/* ── Readiness Bar ── */
const ReadinessBar = ({ score, interpretation }) => {
  // score dari AI engine adalah 0–1, kalikan 100 untuk jadi persentase
  const pct = Math.round((score || 0) * 100);
  const color = pct >= 75 ? '#22c55e' : pct >= 50 ? '#f59e0b' : '#ef4444';
  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <span className="text-sm font-semibold text-[#45474C]">Readiness Score</span>
        <span className="text-2xl font-bold" style={{ color }}>{pct}%</span>
      </div>
      <div className="w-full h-2 bg-[#F0F5FF] rounded-full overflow-hidden">
        <div
          className="h-full rounded-full transition-all"
          style={{ width: `${pct}%`, backgroundColor: color }}
        />
      </div>
      {interpretation && (
        <p className="text-sm text-[#45474C]">{interpretation}</p>
      )}
    </div>
  );
};

/* ── Pivot Radar Chart (chart.js – React 19 compatible) ── */
// 10 warna agar support lebih banyak role
const RADAR_COLORS = [
  { stroke: '#2563EB', fill: 'rgba(37,99,235,0.13)'   },
  { stroke: '#6366F1', fill: 'rgba(99,102,241,0.13)'  },
  { stroke: '#10B981', fill: 'rgba(16,185,129,0.13)'  },
  { stroke: '#F59E0B', fill: 'rgba(245,158,11,0.13)'  },
  { stroke: '#EF4444', fill: 'rgba(239,68,68,0.13)'   },
  { stroke: '#8B5CF6', fill: 'rgba(139,92,246,0.13)'  },
  { stroke: '#EC4899', fill: 'rgba(236,72,153,0.13)'  },
  { stroke: '#14B8A6', fill: 'rgba(20,184,166,0.13)'  },
  { stroke: '#F97316', fill: 'rgba(249,115,22,0.13)'  },
  { stroke: '#64748B', fill: 'rgba(100,116,139,0.13)' },
];

const _normalizeRole = (role) => {
  const skillMatch = Math.min(100, role.skill_overlap_pct ?? role.skill_readiness_pct ?? 0);
  const demandMap  = { high: 100, medium: 65, low: 30 };
  const demand     = demandMap[(role.market_demand || '').toLowerCase()] ?? 50;
  const easeMap    = { easy: 100, moderate: 60, challenging: 25 };
  const ease       = easeMap[(role.transition_difficulty || '').toLowerCase()] ?? 50;
  const months     = role.estimated_transition_months ?? 12;
  const speed      = Math.round(Math.max(10, (1 - (months - 1) / 24) * 100));
  const overall    = Math.round((skillMatch + demand + ease + speed) / 4);
  return [skillMatch, demand, ease, speed, overall];
};

const PivotRadarChart = ({ roles }) => {
  const roleKey = roles.map(r => r.role_name).join(',');

  const chartData = useMemo(() => ({
    labels: ['Skill Match', 'Market Demand', 'Ease', 'Speed', 'Overall Fit'],
    datasets: roles.map((role, i) => {
      const c = RADAR_COLORS[i % RADAR_COLORS.length];
      return {
        label: role.role_name,
        data: _normalizeRole(role),
        borderColor: c.stroke,
        backgroundColor: c.fill,
        borderWidth: 2,
        pointBackgroundColor: c.stroke,
        pointBorderColor: '#fff',
        pointBorderWidth: 2,
        pointRadius: 5,
        pointHoverRadius: 7,
        pointHoverBorderWidth: 2,
      };
    }),
  }), [roleKey]); // eslint-disable-line react-hooks/exhaustive-deps

  const options = useMemo(() => ({
    responsive: true,
    maintainAspectRatio: true,
    animation: false,          // ← matikan animasi → tidak lag saat re-render
    scales: {
      r: {
        min: 0,
        max: 100,
        ticks: {
          stepSize: 25,
          color: '#94A3B8',
          font: { size: 10, family: 'Inter, system-ui, sans-serif' },
          backdropColor: 'transparent',
          callback: (v) => `${v}%`,
        },
        grid: { color: '#E2E8F0' },
        angleLines: { color: '#CBD5E1' },
        pointLabels: {
          color: '#475569',
          font: { size: 11, weight: '600', family: 'Inter, system-ui, sans-serif' },
        },
      },
    },
    plugins: {
      legend: {
        position: 'bottom',
        labels: {
          boxWidth: 12,
          boxHeight: 12,
          borderRadius: 6,
          useBorderRadius: true,
          color: '#45474C',
          font: { size: 12, family: 'Inter, system-ui, sans-serif' },
          padding: 16,
        },
      },
      tooltip: {
        backgroundColor: '#fff',
        borderColor: 'rgba(0,0,0,0.08)',
        borderWidth: 1,
        titleColor: '#0D1C2D',
        bodyColor: '#45474C',
        titleFont: { size: 12, weight: '700', family: 'Inter, system-ui, sans-serif' },
        bodyFont: { size: 12, family: 'Inter, system-ui, sans-serif' },
        padding: 12,
        boxWidth: 10,
        boxHeight: 10,
        borderRadius: 10,
        callbacks: {
          label: (ctx) => `  ${ctx.dataset.label}: ${ctx.raw}%`,
        },
      },
    },
  }), []); // options tidak bergantung state — cukup dibuat sekali

  return (
    <div className="w-full flex justify-center" style={{ maxWidth: 480, margin: '0 auto' }}>
      <Radar data={chartData} options={options} />
    </div>
  );
};


/* ── Main Page ── */
/* ── Radar Section with role toggles ── */
const RADAR_COLS = [
  { label: 'Skill Match',   fn: r => Math.min(100, r.skill_overlap_pct ?? r.skill_readiness_pct ?? 0) },
  { label: 'Market Demand', fn: r => ({ high: 100, medium: 65, low: 30 })[(r.market_demand||'').toLowerCase()] ?? 50 },
  { label: 'Ease',          fn: r => ({ easy: 100, moderate: 60, challenging: 25 })[(r.transition_difficulty||'').toLowerCase()] ?? 50 },
  { label: 'Speed',         fn: r => Math.round(Math.max(10, (1 - ((r.estimated_transition_months??12) - 1) / 24) * 100)) },
  { label: 'Overall Fit',   fn: r => { const v=[Math.min(100,r.skill_overlap_pct??r.skill_readiness_pct??0),({ high:100,medium:65,low:30 })[(r.market_demand||'').toLowerCase()]??50,({ easy:100,moderate:60,challenging:25 })[(r.transition_difficulty||'').toLowerCase()]??50,Math.round(Math.max(10,(1-((r.estimated_transition_months??12)-1)/24)*100))]; return Math.round(v.reduce((a,b)=>a+b,0)/v.length); }},
];
const cellCls = (v) => v >= 75 ? 'text-emerald-600 bg-emerald-50' : v >= 50 ? 'text-amber-600 bg-amber-50' : 'text-red-500 bg-red-50';

const RadarSection = ({ alternativeRoles, aiDiscoveredRoles }) => {
  const allRoles = [...alternativeRoles, ...aiDiscoveredRoles];
  // Setiap role punya index warna tetap (by position in allRoles)
  const colorOf = (roleName) => {
    const idx = allRoles.findIndex(r => r.role_name === roleName);
    return RADAR_COLORS[idx % RADAR_COLORS.length];
  };

  const [selected, setSelected] = useState(() => new Set(allRoles.map(r => r.role_name)));

  const toggle = (name) => {
    setSelected(prev => {
      if (prev.has(name) && prev.size === 1) return prev; // minimal 1 tetap aktif
      const next = new Set(prev);
      next.has(name) ? next.delete(name) : next.add(name);
      return next;
    });
  };

  const visibleRoles = allRoles.filter(r => selected.has(r.role_name));

  return (
    <SectionCard>
      <p className="text-xs font-semibold text-[#75777D] uppercase tracking-widest mb-4">Role Comparison Radar</p>

      {/* ── Toggle chips ── */}
      <div className="flex flex-wrap gap-2 mb-5">
        {allRoles.map((role) => {
          const c      = colorOf(role.role_name);
          const active = selected.has(role.role_name);
          return (
            <button
              key={role.role_name}
              onClick={() => toggle(role.role_name)}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full border text-xs font-semibold transition-all duration-150
                ${active
                  ? 'border-current shadow-sm scale-100'
                  : 'border-black/[0.08] text-[#C5C6CD] bg-[#F8F9FF] scale-95 opacity-60'
                }`}
              style={active ? { color: c.stroke, borderColor: c.stroke, backgroundColor: c.fill } : {}}
            >
              <span className="w-2 h-2 rounded-full flex-shrink-0"
                style={{ backgroundColor: active ? c.stroke : '#C5C6CD' }} />
              {role.role_name}
            </button>
          );
        })}
      </div>

      {/* ── Radar chart (hanya role yang dipilih) ── */}
      <PivotRadarChart roles={visibleRoles} />

      {/* ── Comparison table (semua role) ── */}
      <div className="mt-5 pt-4 border-t border-black/[0.05] overflow-x-auto">
        <table className="w-full text-sm border-collapse">
          <thead>
            <tr>
              <th className="text-left text-xs font-bold text-[#75777D] uppercase tracking-wide pb-2 pr-4">Role</th>
              {RADAR_COLS.map(c => (
                <th key={c.label} className="text-center text-xs font-bold text-[#75777D] uppercase tracking-wide pb-2 px-2 whitespace-nowrap">{c.label}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {allRoles.map((role) => {
              const c      = colorOf(role.role_name);
              const active = selected.has(role.role_name);
              return (
                <tr
                  key={role.role_name}
                  className={`border-t border-black/[0.04] cursor-pointer transition-opacity ${active ? 'opacity-100' : 'opacity-40'}`}
                  onClick={() => toggle(role.role_name)}
                >
                  <td className="py-2 pr-4">
                    <div className="flex items-center gap-2">
                      <span className="w-2.5 h-2.5 rounded-full flex-shrink-0" style={{ backgroundColor: c.stroke }} />
                      <span className="font-medium text-[#0D1C2D] truncate max-w-[140px]">{role.role_name}</span>
                    </div>
                  </td>
                  {RADAR_COLS.map(col => {
                    const val = Math.round(col.fn(role));
                    return (
                      <td key={col.label} className="text-center py-2 px-2">
                        <span className={`text-xs font-bold px-2 py-0.5 rounded-full ${cellCls(val)}`}>{val}%</span>
                      </td>
                    );
                  })}
                </tr>
              );
            })}
          </tbody>
        </table>
        <p className="text-[10px] text-[#C5C6CD] mt-2 text-right">Click role to toggle visibility</p>
      </div>
    </SectionCard>
  );
};

/* ── Main Page ── */
const HistoryDetailPage = () => {

  const { id } = useParams();
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [pivotLoading, setPivotLoading] = useState(false);
  const [pivotStep, setPivotStep] = useState(0);
  const [pivotError, setPivotError] = useState('');

  useEffect(() => { fetchDetail(); }, [id]);

  const fetchDetail = async () => {
    setIsLoading(true);
    try {
      const token = localStorage.getItem('token');
      const res = await fetch(`${import.meta.env.VITE_API_URL}/api/cv/history/${id}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      const json = await res.json();
      if (res.status === 401) { localStorage.removeItem('token'); navigate('/login'); return; }
      if (!res.ok) { setError(json.message || 'Failed to load details.'); return; }
      setData(json.data);
    } catch {
      setError('Unable to connect to the server.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleCareerPivot = async () => {
    setPivotLoading(true);
    setPivotStep(0);
    setPivotError('');
    // Animasi steps
    const t = setInterval(() => {
      setPivotStep((prev) => {
        if (prev < PIVOT_STEPS.length - 1) return prev + 1;
        clearInterval(t);
        return prev;
      });
    }, 4000);
    try {
      const token = localStorage.getItem('token');
      const res = await fetch(`${import.meta.env.VITE_API_URL}/api/cv/career-pivot/${id}`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      });
      const json = await res.json();
      clearInterval(t);
      if (res.status === 401) { localStorage.removeItem('token'); navigate('/login'); return; }
      if (!res.ok) { setPivotError(json.message || 'Failed to generate Career Pivot.'); return; }
      setData((prev) => ({ ...prev, gemini_roles: json.data, pivot_metadata: json.metadata }));
    } catch {
      setPivotError('Unable to connect to the server.');
    } finally {
      setPivotLoading(false);
    }
  };

  /* ── Derive structured data from DB row ── */
  const profile = data?.profile_entities || {};
  const extractedSkills = data?.extracted_skills || profile?.skills || [];

  // top_skills stores { skill_gap, readiness_score } from Phase 2
  const topSkillsRaw = data?.top_skills;
  const skillGap = topSkillsRaw?.skill_gap || null;
  const readinessScore = topSkillsRaw?.readiness_score || null;

  // Deduplicate matched_skills (AI engine kadang kembalikan duplikat e.g. "nodejs" dua kali)
  const matchedSkills = [...new Set(skillGap?.matched_skills || [])];
  const missingSkills = skillGap?.missing_skills || [];
  const recommendedCourses = data?.recommended_courses || [];

  // gemini_roles stores CareerPivotOutput from Phase 3
  const careerPivot = data?.gemini_roles;
  const alternativeRoles = careerPivot?.alternative_roles || [];
  const aiDiscoveredRoles = careerPivot?.ai_discovered_roles || [];
  const currentAssessment = careerPivot?.current_role_assessment || null;
  const suggestedCerts = careerPivot?.suggested_certifications || [];
  const universalAdvice = careerPivot?.universal_advice || '';
  const hasCareerPivot = alternativeRoles.length > 0 || aiDiscoveredRoles.length > 0;

  // metadata
  const pivotMeta = data?.pivot_metadata || null;

  if (isLoading) return (
    <div className="min-h-screen flex flex-col bg-[#F8F9FF]">
      <AppNavbar activeTab="history" />
      <main className="flex-1 flex flex-col gap-6 px-8 py-8 pt-[104px] pb-[104px] max-w-[1280px] w-full mx-auto animate-pulse">
        {/* Back button */}
        <div className="w-28 h-5 bg-[#C5C6CD]/30 rounded-md mb-2" />

        {/* Hero Card */}
        <div className="bg-white border border-black/[0.06] rounded-xl p-6 flex flex-col md:flex-row md:items-start justify-between gap-6">
          <div className="flex flex-col gap-3 flex-1">
            <div className="w-16 h-3.5 bg-[#C5C6CD]/30 rounded" />
            <div className="w-64 h-8 bg-[#C5C6CD]/30 rounded-md" />
            <div className="w-48 h-4 bg-[#C5C6CD]/30 rounded" />
          </div>
          <div className="w-full md:w-72 flex-shrink-0 flex flex-col gap-2.5">
            <div className="flex justify-between">
              <div className="w-24 h-4 bg-[#C5C6CD]/30 rounded" />
              <div className="w-12 h-6 bg-[#C5C6CD]/30 rounded" />
            </div>
            <div className="w-full h-2 bg-[#C5C6CD]/20 rounded-full" />
            <div className="w-48 h-4 bg-[#C5C6CD]/30 rounded" />
          </div>
        </div>

        {/* Two Columns Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          <div className="bg-white border border-black/[0.06] rounded-xl p-6 flex flex-col gap-4">
            <div className="w-36 h-5 bg-[#C5C6CD]/30 rounded-md" />
            <div className="flex flex-col gap-3">
              <div className="w-full h-4 bg-[#C5C6CD]/30 rounded" />
              <div className="w-3/4 h-3 bg-[#C5C6CD]/30 rounded" />
              <div className="w-1/2 h-3.5 bg-[#C5C6CD]/20 rounded" />
            </div>
            <div className="flex flex-col gap-3 mt-2">
              <div className="w-full h-4 bg-[#C5C6CD]/30 rounded" />
              <div className="w-2/3 h-3 bg-[#C5C6CD]/30 rounded" />
            </div>
          </div>
          <div className="bg-white border border-black/[0.06] rounded-xl p-6 flex flex-col gap-4">
            <div className="w-28 h-5 bg-[#C5C6CD]/30 rounded-md" />
            <div className="flex flex-col gap-3">
              <div className="w-full h-4 bg-[#C5C6CD]/30 rounded" />
              <div className="w-3/4 h-3 bg-[#C5C6CD]/30 rounded" />
            </div>
            <div className="flex flex-col gap-3 mt-2">
              <div className="w-full h-4 bg-[#C5C6CD]/30 rounded" />
              <div className="w-2/3 h-3 bg-[#C5C6CD]/30 rounded" />
            </div>
          </div>
        </div>

        {/* Skill details */}
        <div className="bg-white border border-black/[0.06] rounded-xl p-6 flex flex-col gap-4">
          <div className="w-48 h-6 bg-[#C5C6CD]/30 rounded-md" />
          <div className="flex flex-wrap gap-2 mt-2">
            {[1, 2, 3, 4, 5, 6, 7, 8].map((i) => (
              <div key={i} className="w-24 h-8 bg-[#C5C6CD]/20 rounded-full" />
            ))}
          </div>
        </div>
      </main>
      <Footer />
    </div>
  );

  if (error) return (
    <div className="min-h-screen flex flex-col bg-[#F8F9FF]">
      <AppNavbar activeTab="history" />
      <main className="flex-1 flex flex-col gap-5 px-8 pt-[104px] pb-[104px]">
        <button onClick={() => navigate('/history')} className="flex items-center gap-2 text-sm text-[#45474C] hover:text-[#2563EB] transition-all duration-200 hover:-translate-x-0.5 w-fit">
          <ArrowLeft className="w-5 h-5" /> Back
        </button>
        <div className="px-4 py-3 bg-red-50 border border-red-200 rounded-xl text-sm text-red-600">{error}</div>
      </main>
      <Footer />
    </div>
  );

  return (
    <div className="min-h-screen flex flex-col bg-[#F8F9FF]">
      <AppNavbar activeTab="history" />

      <main className="flex-1 flex flex-col gap-6 px-8 py-8 pt-[104px] pb-[104px] max-w-[1280px] w-full mx-auto">

        {/* Back */}
        <button
          onClick={() => navigate('/history')}
          className="flex items-center gap-2 text-sm text-[#45474C] hover:text-[#2563EB] transition-all duration-200 hover:-translate-x-0.5 w-fit"
        >
          <ArrowLeft className="w-5 h-5" /> Back to history
        </button>

        {/* Hero – Target Role + Readiness */}
        <SectionCard className="flex flex-col md:flex-row md:items-start justify-between gap-6">
          <div className="flex flex-col gap-1">
            <p className="text-xs font-semibold text-[#75777D] uppercase tracking-widest">Target Role</p>
            <h1 className="text-3xl font-bold text-[#0D1C2D]">{data?.target_role || 'Untitled Analysis'}</h1>
            {profile.name && (
              <p className="text-sm text-[#45474C] mt-1">{profile.name} · {profile.location || ''}</p>
            )}
          </div>
          {readinessScore && (
            <div className="w-full md:w-72 flex-shrink-0">
              <ReadinessBar score={readinessScore.score} interpretation={readinessScore.interpretation} />
            </div>
          )}
        </SectionCard>

        {/* Work Experience + Education row */}
        {(profile.work_experience?.length > 0 || profile.education?.length > 0) && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            {profile.work_experience?.length > 0 && (
              <SectionCard>
                <p className="text-base font-semibold text-[#0D1C2D] mb-3">Work Experience</p>
                <div className="flex flex-col gap-3">
                  {profile.work_experience.map((we, i) => (
                    <div key={i} className="flex flex-col gap-0.5">
                      <span className="text-sm font-semibold text-[#0D1C2D]">{we.designation}</span>
                      <span className="text-sm text-[#45474C]">{we.company}</span>
                      {we.duration && <span className="text-xs text-[#75777D]">{we.duration}</span>}
                    </div>
                  ))}
                </div>
              </SectionCard>
            )}
            {profile.education?.length > 0 && (
              <SectionCard>
                <p className="text-base font-semibold text-[#0D1C2D] mb-3">Education</p>
                <div className="flex flex-col gap-3">
                  {profile.education.map((ed, i) => (
                    <div key={i} className="flex flex-col gap-0.5">
                      <span className="text-sm font-semibold text-[#0D1C2D]">{ed.degree}</span>
                      <span className="text-sm text-[#45474C]">{ed.institution}</span>
                      {ed.year && <span className="text-xs text-[#75777D]">{ed.year}</span>}
                    </div>
                  ))}
                </div>
              </SectionCard>
            )}
          </div>
        )}

        {/* Skill Gap Row */}
        {skillGap ? (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            {/* Matched Skills */}
            <SectionCard>
              <p className="text-base font-semibold text-[#0D1C2D] mb-3">
                Matched Skills
                {matchedSkills.length > 0 && (
                  <span className="ml-2 text-sm font-normal text-emerald-600">({matchedSkills.length})</span>
                )}
              </p>
              {matchedSkills.length > 0 ? (
                <div className="flex flex-wrap gap-2">
                  {matchedSkills.map((sk, i) => (
                    <span key={i} className="flex items-center gap-1 text-sm text-emerald-700 bg-emerald-50 border border-emerald-200 px-3 py-1.5 rounded-full font-medium">
                      <Check className="w-3.5 h-3.5" /> {sk}
                    </span>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-[#75777D]">No matched skills yet.</p>
              )}
            </SectionCard>

            {/* Missing Skills */}
            <SectionCard>
              <p className="text-base font-semibold text-[#0D1C2D] mb-3">
                Missing Skills
                {missingSkills.length > 0 && (
                  <span className="ml-2 text-sm font-normal text-red-500">({missingSkills.length})</span>
                )}
              </p>
              {missingSkills.length > 0 ? (
                <div className="flex flex-wrap gap-2">
                  {missingSkills.map((sk, i) => (
                    <span key={i} className="flex items-center gap-1.5 text-sm text-red-600 bg-red-50 border border-red-200 px-3 py-1.5 rounded-full font-medium">
                      {sk.skill}
                      <span className="text-xs font-normal opacity-70">{(sk.priority_score * 100).toFixed(0)}%</span>
                    </span>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-emerald-600">🎉 All required skills are in your CV!</p>
              )}
            </SectionCard>
          </div>
        ) : (
          !data?.target_role && (
            <SectionCard>
              <p className="text-sm text-[#75777D]">
                No skill gap analysis yet.{' '}
                <button onClick={() => navigate(`/recommend/${id}`)} className="text-[#2563EB] hover:underline font-medium">
                  Run analysis →
                </button>
              </p>
            </SectionCard>
          )
        )}

        {/* Recommended Courses */}
        {recommendedCourses.length > 0 && (
          <div className="flex flex-col gap-4">
            <h2 className="text-xl font-bold text-[#0D1C2D]">
              Recommended Courses
              <span className="ml-2 text-base font-normal text-[#75777D]">({recommendedCourses.length})</span>
            </h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
              {recommendedCourses.map((course, i) => (
                <CourseCard key={i} course={course} />
              ))}
            </div>
          </div>
        )}

        {/* Career Pivot Section */}
        {hasCareerPivot ? (
          <div className="flex flex-col gap-6">
            <div className="flex items-center justify-between">
              <h2 className="text-xl font-bold text-[#0D1C2D]">Career Pivot Radar</h2>
              <button
                onClick={handleCareerPivot}
                disabled={pivotLoading}
                className="flex items-center gap-2 px-4 py-2 text-sm bg-white border border-[#C5C6CD] text-[#45474C] rounded-lg hover:border-[#2563EB] hover:text-[#2563EB] disabled:opacity-50 transition-all duration-200 ease-out hover:scale-[1.02] active:scale-[0.97] shadow-[0_1px_2px_rgba(0,0,0,0.05)] hover:shadow-[0_4px_8px_rgba(0,0,0,0.05)] disabled:transform-none"
              >
                {pivotLoading
                  ? <span className="w-3.5 h-3.5 border-2 border-[#2563EB]/30 border-t-[#2563EB] rounded-full animate-spin" />
                  : <Sparkles className="w-4 h-4" />
                }
                Refresh Analysis
              </button>
            </div>

            {currentAssessment && (
              <SectionCard className="bg-gradient-to-r from-[#EFF6FF] to-white">
                <div className="flex items-start gap-4">
                  <div className="flex flex-col gap-1">
                    <p className="text-xs font-semibold text-[#75777D] uppercase tracking-widest">Current Assessment</p>
                    <p className="text-base font-bold text-[#0D1C2D]">{currentAssessment.target_role}</p>
                    <p className="text-sm text-[#45474C]">{currentAssessment.verdict}</p>
                  </div>
                  <div className="ml-auto text-right flex-shrink-0">
                    <span className={`text-xs font-bold px-3 py-1 rounded-full border ${
                      currentAssessment.readiness_level === 'excellent' ? 'bg-emerald-50 text-emerald-700 border-emerald-200' :
                      currentAssessment.readiness_level === 'high' ? 'bg-blue-50 text-blue-700 border-blue-200' :
                      currentAssessment.readiness_level === 'moderate' ? 'bg-amber-50 text-amber-700 border-amber-200' :
                      'bg-red-50 text-red-700 border-red-200'
                    }`}>
                      {currentAssessment.readiness_level?.toUpperCase()}
                    </span>
                  </div>
                </div>
              </SectionCard>
            )}

            {/* ── Radar Section with toggle ── */}
            {(alternativeRoles.length > 0 || aiDiscoveredRoles.length > 0) && (
              <RadarSection
                alternativeRoles={alternativeRoles}
                aiDiscoveredRoles={aiDiscoveredRoles}
              />
            )}


            {alternativeRoles.length > 0 && (
              <div className="flex flex-col gap-3">
                <h3 className="text-base font-bold text-[#0D1C2D]">Data-Backed Alternative Roles</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {alternativeRoles.map((role, i) => (
                    <AlternativeRoleCard key={i} role={role} />
                  ))}
                </div>
              </div>
            )}

            {aiDiscoveredRoles.length > 0 && (
              <div className="flex flex-col gap-3">
                <h3 className="text-base font-bold text-[#0D1C2D]">AI-Discovered Roles</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {aiDiscoveredRoles.map((role, i) => (
                    <AlternativeRoleCard key={i} role={role} />
                  ))}
                </div>
              </div>
            )}

            {suggestedCerts.length > 0 && (
              <SectionCard>
                <p className="text-base font-semibold text-[#0D1C2D] mb-3">Suggested Certifications</p>
                <div className="flex flex-col gap-2">
                  {suggestedCerts.map((cert, i) => (
                    <div key={i} className="flex items-start gap-2">
                      <span className="text-[#2563EB] mt-0.5">✦</span>
                      <div>
                        <p className="text-sm font-semibold text-[#0D1C2D]">{cert.name}</p>
                        {cert.relevance && <p className="text-xs text-[#75777D]">{cert.relevance}</p>}
                      </div>
                    </div>
                  ))}
                </div>
              </SectionCard>
            )}

            {universalAdvice && (
              <SectionCard className="border-[#2563EB]/20 bg-[#EFF6FF]">
                <p className="text-xs font-semibold text-[#2563EB] uppercase tracking-wide mb-2">AI Advice</p>
                <p className="text-sm text-[#0D1C2D]">{universalAdvice}</p>
              </SectionCard>
            )}

            {/* Pivot Metadata */}
            {pivotMeta && (
              <div className="flex flex-wrap gap-2">
                {pivotMeta.llm_model && (
                  <span className="text-xs px-2.5 py-1 bg-[#F0F5FF] text-[#2563EB] rounded-full border border-[#2563EB]/20 font-medium">
                    {pivotMeta.llm_model}
                  </span>
                )}
                {pivotMeta.roles_evaluated && (
                  <span className="text-xs px-2.5 py-1 bg-[#F8F9FF] text-[#75777D] rounded-full border border-black/[0.06]">
                    {pivotMeta.roles_evaluated} roles evaluated
                  </span>
                )}
                {pivotMeta.roles_returned && (
                  <span className="text-xs px-2.5 py-1 bg-[#F8F9FF] text-[#75777D] rounded-full border border-black/[0.06]">
                    {pivotMeta.roles_returned} returned
                  </span>
                )}
                {pivotMeta.processing_time_ms && (
                  <span className="text-xs px-2.5 py-1 bg-[#F8F9FF] text-[#75777D] rounded-full border border-black/[0.06]">
                    {(pivotMeta.processing_time_ms / 1000).toFixed(1)}s
                  </span>
                )}
              </div>
            )}
          </div>
        ) : data?.target_role ? (
          <div className="flex flex-col gap-3">
            {pivotError && (
              <div className="px-4 py-3 bg-red-50 border border-red-200 rounded-xl text-sm text-red-600">{pivotError}</div>
            )}
            {/* Career Pivot loading progress steps */}
            {pivotLoading && (
              <div className="flex flex-col gap-4 p-6 bg-white border border-black/[0.06] rounded-xl shadow-[0_2px_8px_rgba(0,0,0,0.04)]">
                {PIVOT_STEPS.map((msg, i) => {
                  const isDone = i < pivotStep;
                  const isActive = i === pivotStep;
                  return (
                    <div key={i} className="flex items-start gap-3.5 relative">
                      <div className="flex flex-col items-center flex-shrink-0 mt-0.5">
                        {isDone ? (
                          <div className="w-5 h-5 rounded-full bg-[#2563EB] flex items-center justify-center">
                            <Check className="w-3 h-3 text-white" />
                          </div>
                        ) : isActive ? (
                          <div className="w-5 h-5 rounded-full border-2 border-[#2563EB] flex items-center justify-center">
                            <div className="w-1.5 h-1.5 rounded-full bg-[#2563EB] animate-pulse" />
                          </div>
                        ) : (
                          <div className="w-5 h-5 rounded-full border-2 border-[#C5C6CD]" />
                        )}
                      </div>
                      <div>
                        <p className={`text-sm leading-5 font-medium ${isActive ? 'text-[#2563EB]' : isDone ? 'text-[#0D1C2D]' : 'text-[#75777D]'}`}>
                          {msg}
                        </p>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
            <div className="flex justify-center py-4">
              <button
                onClick={handleCareerPivot}
                disabled={pivotLoading}
                className="flex items-center gap-2 px-6 py-3 bg-[#2563EB] text-white text-base font-semibold rounded-lg hover:bg-[#1D4ED8] disabled:opacity-60 disabled:cursor-not-allowed transition-all duration-200 ease-out hover:scale-[1.02] active:scale-[0.97] shadow-[0_2px_4px_rgba(37,99,235,0.15)] hover:shadow-[0_4px_12px_rgba(37,99,235,0.25)] disabled:transform-none disabled:shadow-none"
              >
                {pivotLoading
                  ? <span className="w-4 h-4 border-2 border-white/40 border-t-white rounded-full animate-spin" />
                  : <Sparkles className="w-4 h-4" />
                }
                {pivotLoading ? PIVOT_STEPS[pivotStep] : 'Generate Career Pivot Radar'}
              </button>
            </div>
          </div>
        ) : null}

      </main>
      <Footer />
    </div>
  );
};

export default HistoryDetailPage;
