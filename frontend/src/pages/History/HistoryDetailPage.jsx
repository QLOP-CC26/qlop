import { useState, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import AppNavbar from '../../components/AppNavbar/AppNavbar';
import Footer from '../../components/Footer/Footer';

/* ── Icons ── */
const ArrowLeftIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
    <line x1="19" y1="12" x2="5" y2="12" /><polyline points="12 19 5 12 12 5" />
  </svg>
);

const ExternalLinkIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
    <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" />
    <polyline points="15 3 21 3 21 9" /><line x1="10" y1="14" x2="21" y2="3" />
  </svg>
);

const VideoIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
    <rect x="2" y="7" width="15" height="10" rx="2" ry="2" />
    <polygon points="17 8 22 5 22 19 17 16" />
  </svg>
);

const SparkleIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
    <path d="M12 3l1.5 4.5L18 9l-4.5 1.5L12 15l-1.5-4.5L6 9l4.5-1.5z" />
    <path d="M5 3v3" /><path d="M3 5h3" /><path d="M19 15v3" /><path d="M17 17h3" />
  </svg>
);

/* ── Helpers ── */
const formatDifficulty = (d) => {
  if (!d) return '';
  return d.charAt(0) + d.slice(1).toLowerCase();
};

const formatDuration = (d) => {
  if (!d) return '';
  return d.replace(/_/g, ' ').toLowerCase().replace(/\b\w/g, (c) => c.toUpperCase());
};

const getCompatibility = (geminiRoles) => {
  if (!geminiRoles) return null;
  const roles = geminiRoles.recommended_roles || geminiRoles;
  if (Array.isArray(roles) && roles.length > 0) return roles[0]?.compatibility_percentage ?? null;
  return null;
};

const getGeminiRolesList = (geminiRoles) => {
  if (!geminiRoles) return [];
  return geminiRoles.recommended_roles || geminiRoles || [];
};

/* ── Missing Skills: top_skills NOT found in extracted_skills ── */
const getMissingSkills = (topSkills = [], extractedSkills = []) => {
  const userSkillSet = new Set(
    extractedSkills.map((s) => (s.normalized_guess || s.surface || '').toLowerCase())
  );
  return topSkills.filter(
    (s) => !userSkillSet.has((s.skill_linkedin || '').toLowerCase())
  );
};

/* ── Course Card ── */
const CourseCard = ({ course }) => (
  <a
    href={course.url || '#'}
    target="_blank"
    rel="noopener noreferrer"
    className="flex items-start justify-between gap-3 p-4 bg-[#F8F9FF] border border-black/[0.06] rounded-lg hover:border-[#2563EB]/30 hover:bg-blue-50/30 transition-all group"
  >
    <div className="flex flex-col gap-0.5 flex-1 min-w-0">
      <p className="text-sm font-semibold text-[#0D1C2D] group-hover:text-[#2563EB] transition-colors truncate">
        {course.name}
      </p>
      <div className="flex items-center gap-2 flex-wrap">
        {course.difficulty && (
          <span className="text-xs text-[#75777D]">{formatDifficulty(course.difficulty)}</span>
        )}
        {course.duration && (
          <span className="text-xs text-[#75777D]">· {formatDuration(course.duration)}</span>
        )}
        {course.match_score && (
          <span className="text-xs font-medium text-[#2563EB]">· {Math.round(course.match_score * 100)}% match</span>
        )}
      </div>
    </div>
    <span className="text-[#75777D] group-hover:text-[#2563EB] transition-colors flex-shrink-0 mt-0.5">
      <ExternalLinkIcon />
    </span>
  </a>
);

/* ── Section Card wrapper ── */
const SectionCard = ({ children, className = '' }) => (
  <div className={`bg-white border border-black/[0.06] rounded-xl p-6 ${className}`}>
    {children}
  </div>
);

/* ── Main Page ── */
const HistoryDetailPage = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [geminiLoading, setGeminiLoading] = useState(false);
  const [geminiError, setGeminiError] = useState('');

  useEffect(() => { fetchDetail(); }, [id]);

  const fetchDetail = async () => {
    setIsLoading(true);
    try {
      const token = localStorage.getItem('token');
      const res = await fetch(`${import.meta.env.VITE_API_URL}/api/cv/history/${id}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      const json = await res.json();
      if (res.status === 401) {
        localStorage.removeItem('token');
        navigate('/login');
        return;
      }
      if (!res.ok) { setError(json.message || 'Gagal memuat detail.'); return; }
      setData(json.data);
    } catch {
      setError('Tidak dapat terhubung ke server.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleGemini = async () => {
    setGeminiLoading(true);
    setGeminiError('');
    try {
      const token = localStorage.getItem('token');
      const res = await fetch(`${import.meta.env.VITE_API_URL}/api/cv/gemini-roles/${id}`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      });
      const json = await res.json();
      if (res.status === 401) {
        localStorage.removeItem('token');
        navigate('/login');
        return;
      }
      if (!res.ok) { setGeminiError(json.message || 'Gagal generate Gemini roles.'); return; }
      setData((prev) => ({ ...prev, gemini_roles: json.data }));
    } catch {
      setGeminiError('Tidak dapat terhubung ke server.');
    } finally {
      setGeminiLoading(false);
    }
  };

  /* derived data */
  const topSkills = data?.top_skills || [];
  const extractedSkills = data?.extracted_skills || [];
  const recommendedCourses = data?.recommended_courses || [];
  const missingSkills = getMissingSkills(topSkills, extractedSkills);
  const compatibility = getCompatibility(data?.gemini_roles);
  const geminiRoles = getGeminiRolesList(data?.gemini_roles);

  if (isLoading) return (
    <div className="min-h-screen flex flex-col bg-[#F8F9FF]">
      <AppNavbar activeTab="history" />
      <main className="flex-1 flex flex-col gap-5 px-8 pt-[104px] pb-[104px]">
        {[1, 2, 3].map((i) => (
          <div key={i} className="h-28 bg-white border border-black/[0.06] rounded-xl animate-pulse" />
        ))}
      </main>
      <Footer />
    </div>
  );

  if (error) return (
    <div className="min-h-screen flex flex-col bg-[#F8F9FF]">
      <AppNavbar activeTab="history" />
      <main className="flex-1 flex flex-col gap-5 px-8 pt-[104px] pb-[104px]">
        <button onClick={() => navigate('/history')} className="flex items-center gap-2 text-sm text-[#45474C] hover:text-[#2563EB] transition-colors w-fit">
          <ArrowLeftIcon /> Back
        </button>
        <div className="px-4 py-3 bg-red-50 border border-red-200 rounded-xl text-sm text-red-600">{error}</div>
      </main>
      <Footer />
    </div>
  );

  return (
    <div className="min-h-screen flex flex-col bg-[#F8F9FF]">
      <AppNavbar activeTab="history" />

      <main className="flex-1 flex flex-col gap-5 px-8 py-8 pt-[104px] pb-[104px] max-w-[1280px] w-full mx-auto">

        {/* Back */}
        <button
          onClick={() => navigate('/history')}
          className="flex items-center gap-2 text-sm text-[#45474C] hover:text-[#2563EB] transition-colors w-fit"
        >
          <ArrowLeftIcon />
        </button>

        {/* Hero — Target Role + Compatibility */}
        <SectionCard>
          <div className="flex items-center justify-between gap-4">
            <h1 className="text-3xl font-bold text-[#0D1C2D]">
              {data?.target_role || 'Untitled Analysis'}
            </h1>
            {compatibility !== null && (
              <span className="text-3xl font-bold text-[#0D1C2D]">{compatibility}%</span>
            )}
          </div>
        </SectionCard>

        {/* Skills Row */}
        <div className="grid grid-cols-2 gap-5">
          {/* Top Skills */}
          <SectionCard>
            <p className="text-base font-semibold text-[#0D1C2D] mb-3">Skills Value</p>
            {topSkills.length > 0 ? (
              <div className="flex flex-wrap gap-2">
                {topSkills.map((sk, i) => (
                  <span
                    key={i}
                    className="text-sm text-[#2563EB] bg-[#EFF6FF] px-3 py-1.5 rounded-full font-medium"
                  >
                    {sk.skill_linkedin} | {Number(sk.priority_score).toFixed(2)}
                  </span>
                ))}
              </div>
            ) : (
              <p className="text-sm text-[#75777D]">No skill data yet. Run a recommendation first.</p>
            )}
          </SectionCard>

          {/* Missing Skills */}
          <SectionCard className="border-red-200">
            <p className="text-base font-semibold text-[#0D1C2D] mb-3">Missing Skills</p>
            {missingSkills.length > 0 ? (
              <div className="flex flex-wrap gap-2">
                {missingSkills.map((sk, i) => (
                  <span
                    key={i}
                    className="text-sm text-red-600 bg-red-50 border border-red-200 px-3 py-1.5 rounded-full font-medium"
                  >
                    {sk.skill_linkedin}
                  </span>
                ))}
              </div>
            ) : topSkills.length > 0 ? (
              <p className="text-sm text-emerald-600">All required skills found in your CV!</p>
            ) : (
              <p className="text-sm text-[#75777D]">No data yet.</p>
            )}
          </SectionCard>
        </div>

        {/* Recommended Courses */}
        {recommendedCourses.length > 0 && (
          <div className="flex flex-col gap-4">
            <h2 className="text-2xl font-bold text-[#0D1C2D]">Recommended Course</h2>
            <div className="grid grid-cols-3 gap-5">
              {/* Group courses by skill if match_score, else just show all */}
              {(() => {
                // Group by matching missing skill name
                const grouped = {};
                recommendedCourses.forEach((course) => {
                  const matchedSkill = missingSkills.find((sk) =>
                    course.name?.toLowerCase().includes(sk.skill_linkedin?.toLowerCase())
                  );
                  const key = matchedSkill?.skill_linkedin || 'Other';
                  if (!grouped[key]) grouped[key] = [];
                  grouped[key].push(course);
                });

                if (Object.keys(grouped).length <= 1) {
                  return recommendedCourses.map((course, i) => (
                    <SectionCard key={i} className="flex flex-col gap-3">
                      <div className="flex items-center gap-2 text-sm font-semibold text-[#45474C]">
                        <VideoIcon /> {course.name}
                      </div>
                      <CourseCard course={course} />
                    </SectionCard>
                  ));
                }

                return Object.entries(grouped).map(([skill, courses]) => (
                  <SectionCard key={skill} className="flex flex-col gap-3">
                    <div className="flex items-center gap-2 text-sm font-semibold text-[#45474C]">
                      <VideoIcon /> {skill}
                    </div>
                    <div className="flex flex-col gap-2">
                      {courses.map((c, i) => <CourseCard key={i} course={c} />)}
                    </div>
                  </SectionCard>
                ));
              })()}
            </div>
          </div>
        )}

        {/* Gemini Roles */}
        {geminiRoles.length > 0 && (
          <div className="flex flex-col gap-4">
            <h2 className="text-2xl font-bold text-[#0D1C2D]">AI Role Recommendations</h2>
            <div className="grid grid-cols-1 gap-3">
              {geminiRoles.map((role, i) => (
                <SectionCard key={i} className="flex items-start justify-between gap-4">
                  <div className="flex flex-col gap-1 flex-1">
                    <div className="flex items-center gap-3">
                      <p className="text-base font-semibold text-[#0D1C2D]">{role.role_name}</p>
                      {role.compatibility_percentage && (
                        <span className="text-sm font-bold text-[#2563EB]">{role.compatibility_percentage}%</span>
                      )}
                    </div>
                    <p className="text-sm text-[#45474C]">{role.match_explanation}</p>
                  </div>
                </SectionCard>
              ))}
            </div>
          </div>
        )}

        {/* Error Gemini */}
        {geminiError && (
          <div className="px-4 py-3 bg-red-50 border border-red-200 rounded-xl text-sm text-red-600">{geminiError}</div>
        )}

        {/* Generate with Gemini Button */}
        <div className="flex justify-center py-4">
          <button
            onClick={handleGemini}
            disabled={geminiLoading}
            className="flex items-center gap-2 px-6 py-3 bg-[#2563EB] text-white text-base font-semibold rounded-lg hover:bg-[#1D4ED8] disabled:opacity-60 disabled:cursor-not-allowed transition-all active:scale-[0.98]"
          >
            {geminiLoading
              ? <span className="w-4 h-4 border-2 border-white/40 border-t-white rounded-full animate-spin" />
              : <SparkleIcon />
            }
            {geminiRoles.length > 0 ? 'Regenerate with Gemini' : 'Generate with Gemini'}
          </button>
        </div>

      </main>
      <Footer />
    </div>
  );
};

export default HistoryDetailPage;
