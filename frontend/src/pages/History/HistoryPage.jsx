import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Calendar, ArrowRight, Trash2, History, Sparkles, ArrowUpDown } from 'lucide-react';
import AppNavbar from '../../components/AppNavbar/AppNavbar';
import Footer from '../../components/Footer/Footer';

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
const HistoryItem = ({ analysis, onView, onDelete }) => {
  const skillCount = getSkillCount(analysis);
  const compat = getCompatibility(analysis);

  return (
    <div className="bg-white border border-black/[0.06] rounded-xl px-6 py-5 flex flex-col sm:flex-row sm:items-center justify-between gap-4 hover:shadow-sm transition-shadow">
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

      <div className="flex items-center justify-between sm:justify-end gap-4 flex-wrap sm:flex-nowrap w-full sm:w-auto">
        <div className="flex items-center gap-1.5 text-sm text-[#75777D] flex-shrink-0">
          <Calendar className="w-4 h-4" />
          <span>{formatDate(analysis.created_at)}</span>
        </div>

        <div className="flex items-center gap-2 flex-shrink-0">
          <button
            onClick={() => onView(analysis.id)}
            className="flex items-center gap-2 px-4 py-2 bg-[#2563EB] text-white text-sm font-semibold rounded-lg hover:bg-[#1D4ED8] transition-all duration-200 ease-out hover:scale-[1.02] active:scale-[0.97] shadow-[0_2px_4px_rgba(37,99,235,0.15)] hover:shadow-[0_4px_12px_rgba(37,99,235,0.25)]"
          >
            View Analysis <ArrowRight className="w-4 h-4" />
          </button>
          <button
            onClick={() => onDelete(analysis.id)}
            className="p-2 text-[#75777D] hover:text-red-500 transition-all duration-200 ease-out hover:scale-[1.05] active:scale-[0.95] rounded-lg hover:bg-red-50"
            title="Delete"
          >
            <Trash2 className="w-4.5 h-4.5" />
          </button>
        </div>
      </div>
    </div>
  );
};

/* ── Empty State ── */
const EmptyState = ({ onAnalyze }) => (
  <div className="bg-white border border-black/[0.06] rounded-xl flex flex-col items-center justify-center py-20 gap-5">
    <div className="w-24 h-24 rounded-full bg-[#EFF6FF] flex items-center justify-center">
      <History className="w-12 h-12 text-[#2563EB]" />
    </div>
    <div className="flex flex-col items-center gap-1">
      <p className="text-xl font-bold text-[#0D1C2D]">Your analysis history is empty.</p>
      <p className="text-sm text-[#75777D]">Upload your first CV to start tracking your career readiness journey.</p>
    </div>
    <button
      onClick={onAnalyze}
      className="flex items-center gap-2 px-5 py-2.5 bg-[#2563EB] text-white text-sm font-semibold rounded-lg hover:bg-[#1D4ED8] transition-all duration-200 ease-out hover:scale-[1.02] active:scale-[0.97] shadow-[0_2px_4px_rgba(37,99,235,0.15)] hover:shadow-[0_4px_12px_rgba(37,99,235,0.25)]"
    >
      <Sparkles className="w-4 h-4" /> Analyze CV
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
  const [deleteTargetId, setDeleteTargetId] = useState(null);
  const [isDeleting, setIsDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState('');

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
      if (!res.ok) { setError(data.message || 'Failed to load history.'); return; }
      setAnalyses(data.data.analyses || []);
    } catch {
      setError('Cannot connect to the server.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleDelete = (id) => {
    setDeleteTargetId(id);
    setDeleteError('');
  };

  const confirmDelete = async () => {
    if (!deleteTargetId) return;
    setIsDeleting(true);
    setDeleteError('');
    try {
      const token = localStorage.getItem('token');
      const res = await fetch(`${import.meta.env.VITE_API_URL}/api/cv/history/${deleteTargetId}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` },
      });
      const data = await res.json();
      if (!res.ok) {
        setDeleteError(data.message || 'Failed to delete history.');
        return;
      }
      setAnalyses((prev) => prev.filter((a) => a.id !== deleteTargetId));
      setDeleteTargetId(null);
    } catch {
      setDeleteError('Cannot connect to the server.');
    } finally {
      setIsDeleting(false);
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
            <ArrowUpDown className="w-4 h-4" /> Sort {sortDesc ? '↓' : '↑'}
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
              <HistoryItem
                key={a.id}
                analysis={a}
                onView={(id) => navigate(`/history/${id}`)}
                onDelete={handleDelete}
              />
            ))}
          </div>
        )}
      </main>

      <Footer />

      {/* Delete Confirmation Modal */}
      {deleteTargetId && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40 backdrop-blur-sm">
          <div className="bg-white border border-black/[0.08] shadow-[0_10px_25px_rgba(0,0,0,0.1)] rounded-xl max-w-md w-full p-6 flex flex-col gap-4 animate-in fade-in zoom-in-95 duration-200">
            <div className="flex flex-col gap-2">
              <h2 className="text-xl font-bold text-black">Delete Analysis History</h2>
              <p className="text-sm text-[#75777D]">
                Are you sure you want to delete this CV analysis history? This action cannot be undone.
              </p>
            </div>
            {deleteError && (
              <div className="px-3 py-2 bg-red-50 border border-red-200 rounded-lg text-xs text-red-600">
                {deleteError}
              </div>
            )}
            <div className="flex justify-end gap-3 mt-2">
              <button
                type="button"
                onClick={() => setDeleteTargetId(null)}
                disabled={isDeleting}
                className="px-4 py-2 border border-[#C5C6CD] text-[#45474C] text-sm font-semibold rounded-lg hover:bg-slate-50 transition-all duration-200 ease-out hover:scale-[1.02] active:scale-[0.97] disabled:opacity-50 disabled:transform-none"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={confirmDelete}
                disabled={isDeleting}
                className="px-4 py-2 bg-red-600 text-white text-sm font-semibold rounded-lg hover:bg-red-700 transition-all duration-200 ease-out hover:scale-[1.02] active:scale-[0.97] shadow-[0_2px_4px_rgba(220,38,38,0.15)] hover:shadow-[0_4px_12px_rgba(220,38,38,0.25)] disabled:opacity-50 disabled:transform-none flex items-center gap-2"
              >
                {isDeleting ? (
                  <>
                    <span className="w-3.5 h-3.5 border-2 border-white/40 border-t-white rounded-full animate-spin" />
                    Deleting...
                  </>
                ) : (
                  'Delete'
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default HistoryPage;
