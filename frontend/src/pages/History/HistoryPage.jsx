import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import AppNavbar from '../../components/AppNavbar/AppNavbar';
import Footer from '../../components/Footer/Footer';

/* ── Icons ── */
const CalendarIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
    <rect x="3" y="4" width="18" height="18" rx="2" ry="2" />
    <line x1="16" y1="2" x2="16" y2="6" /><line x1="8" y1="2" x2="8" y2="6" />
    <line x1="3" y1="10" x2="21" y2="10" />
  </svg>
);

const ArrowRightIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <line x1="5" y1="12" x2="19" y2="12" /><polyline points="12 5 19 12 12 19" />
  </svg>
);

const TrashIcon = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="3 6 5 6 21 6" />
    <path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6" />
    <path d="M10 11v6" /><path d="M14 11v6" />
    <path d="M9 6V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2" />
  </svg>
);

const HistoryClockIcon = () => (
  <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="#2563EB" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
    <path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8" />
    <path d="M3 3v5h5" />
    <path d="M12 7v5l4 2" />
  </svg>
);

const SparkleIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
    <path d="M12 3l1.5 4.5L18 9l-4.5 1.5L12 15l-1.5-4.5L6 9l4.5-1.5z" />
    <path d="M5 3v3" /><path d="M3 5h3" /><path d="M19 15v3" /><path d="M17 17h3" />
  </svg>
);

const SortIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
    <line x1="3" y1="6" x2="21" y2="6" /><line x1="3" y1="12" x2="15" y2="12" /><line x1="3" y1="18" x2="9" y2="18" />
  </svg>
);

/* ── Helpers ── */
const formatDate = (iso) => {
  if (!iso) return '';
  return new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
};

const getSkillCount = (analysis) => {
  const topSkills = analysis.top_skills;
  if (Array.isArray(topSkills) && topSkills.length > 0) return topSkills.length;
  const extracted = analysis.extracted_skills;
  if (Array.isArray(extracted)) return extracted.length;
  return 0;
};

const getCompatibility = (analysis) => {
  const gemini = analysis.gemini_roles;
  if (!gemini) return null;
  const roles = gemini.recommended_roles || gemini;
  if (Array.isArray(roles) && roles.length > 0) return roles[0].compatibility_percentage;
  return null;
};

/* ── History List Item ── */
const HistoryItem = ({ analysis, onView }) => {
  const skillCount = getSkillCount(analysis);
  const compat = getCompatibility(analysis);

  return (
    <div className="bg-white border border-black/[0.06] rounded-xl px-6 py-5 flex items-center gap-4 hover:shadow-sm transition-shadow">
      <div className="flex flex-col gap-1.5 flex-1 min-w-0">
        <p className="text-lg font-bold text-[#0D1C2D] truncate">
          {analysis.target_role || 'Untitled Analysis'}
        </p>
        <div className="flex items-center gap-3 flex-wrap">
          {skillCount > 0 && (
            <span className="text-xs font-medium text-[#2563EB] bg-[#EFF6FF] px-2.5 py-1 rounded-full">
              {skillCount} {analysis.top_skills?.length > 0 ? 'Priority Skills' : 'Extracted Skills'}
            </span>
          )}
          {compat !== null && (
            <span className="text-xs font-medium text-emerald-700 bg-emerald-50 px-2.5 py-1 rounded-full">
              {compat}% Match
            </span>
          )}
        </div>
      </div>

      <div className="flex items-center gap-1.5 text-sm text-[#75777D] flex-shrink-0">
        <CalendarIcon />
        <span>{formatDate(analysis.created_at)}</span>
      </div>

      <div className="flex items-center gap-2 flex-shrink-0">
        <button
          onClick={() => onView(analysis.id)}
          className="flex items-center gap-2 px-4 py-2 bg-[#2563EB] text-white text-sm font-semibold rounded-lg hover:bg-[#1D4ED8] transition-colors active:scale-[0.98]"
        >
          View Analysis <ArrowRightIcon />
        </button>
        <button
          className="p-2 text-[#75777D] hover:text-red-500 transition-colors rounded-lg hover:bg-red-50"
          title="Delete"
          disabled
        >
          <TrashIcon />
        </button>
      </div>
    </div>
  );
};

/* ── Empty State ── */
const EmptyState = ({ onAnalyze }) => (
  <div className="bg-white border border-black/[0.06] rounded-xl flex flex-col items-center justify-center py-20 gap-5">
    <div className="w-24 h-24 rounded-full bg-[#EFF6FF] flex items-center justify-center">
      <HistoryClockIcon />
    </div>
    <div className="flex flex-col items-center gap-1">
      <p className="text-xl font-bold text-[#0D1C2D]">Your analysis history is empty.</p>
      <p className="text-sm text-[#75777D]">Upload your first CV to start tracking your career readiness journey.</p>
    </div>
    <button
      onClick={onAnalyze}
      className="flex items-center gap-2 px-5 py-2.5 bg-[#2563EB] text-white text-sm font-semibold rounded-lg hover:bg-[#1D4ED8] transition-colors"
    >
      <SparkleIcon /> Analyze CV
    </button>
  </div>
);

/* ── Main Page ── */
const HistoryPage = () => {
  const navigate = useNavigate();
  const [analyses, setAnalyses] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [sortDesc, setSortDesc] = useState(true);

  useEffect(() => {
    fetchHistory();
  }, []);

  const fetchHistory = async () => {
    setIsLoading(true);
    try {
      const token = localStorage.getItem('token');
      const res = await fetch(`${import.meta.env.VITE_API_URL}/api/cv/history`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      const data = await res.json();
      if (res.status === 401) {
        localStorage.removeItem('token');
        navigate('/login');
        return;
      }
      if (!res.ok) { setError(data.message || 'Gagal memuat riwayat.'); return; }
      setAnalyses(data.data.analyses || []);
    } catch {
      setError('Tidak dapat terhubung ke server.');
    } finally {
      setIsLoading(false);
    }
  };

  const sorted = [...analyses].sort((a, b) => {
    const diff = new Date(b.created_at) - new Date(a.created_at);
    return sortDesc ? diff : -diff;
  });

  return (
    <div className="min-h-screen flex flex-col bg-[#F8F9FF]">
      <AppNavbar activeTab="history" />

      <main className="flex-1 flex flex-col gap-6 px-8 py-8 pt-[104px] pb-[104px]">
        {/* Header */}
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-[40px] font-bold leading-[48px] tracking-[-0.8px] text-black">
              Analysis History
            </h1>
            <p className="text-base text-[#75777D] mt-1">
              Showing {analyses.length} past {analyses.length === 1 ? 'analysis' : 'analyses'}.
            </p>
          </div>
          <button
            onClick={() => setSortDesc((p) => !p)}
            className="flex items-center gap-2 px-4 py-2.5 bg-[#2563EB] text-white text-sm font-semibold rounded-lg hover:bg-[#1D4ED8] transition-colors"
          >
            <SortIcon /> Sort {sortDesc ? '↓' : '↑'}
          </button>
        </div>

        {/* Body */}
        {isLoading ? (
          <div className="flex flex-col gap-3">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-[88px] bg-white border border-black/[0.06] rounded-xl animate-pulse" />
            ))}
          </div>
        ) : error ? (
          <div className="px-4 py-3 bg-red-50 border border-red-200 rounded-xl text-sm text-red-600">{error}</div>
        ) : sorted.length === 0 ? (
          <EmptyState onAnalyze={() => navigate('/analyze')} />
        ) : (
          <div className="flex flex-col gap-3">
            {sorted.map((a) => (
              <HistoryItem key={a.id} analysis={a} onView={(id) => navigate(`/history/${id}`)} />
            ))}
          </div>
        )}
      </main>

      <Footer />
    </div>
  );
};

export default HistoryPage;
