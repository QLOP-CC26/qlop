import { useState, useEffect } from 'react';
import { useNavigate, useParams, useLocation } from 'react-router-dom';
import AppNavbar from '../../components/AppNavbar/AppNavbar';
import Footer from '../../components/Footer/Footer';

const UserIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="12" cy="8" r="4" /><path d="M4 20c0-4 3.6-7 8-7s8 3 8 7" />
  </svg>
);

const PlusIcon = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
    <line x1="12" y1="5" x2="12" y2="19" /><line x1="5" y1="12" x2="19" y2="12" />
  </svg>
);

const XIcon = () => (
  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
    <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
  </svg>
);

const BrainIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
    <path d="M12 5a3 3 0 1 0-5.997.142 4 4 0 0 0-2.526 5.77 4 4 0 0 0 .556 6.588A4 4 0 1 0 12 18Z" />
    <path d="M12 5a3 3 0 1 1 5.997.142 4 4 0 0 1 2.526 5.77 4 4 0 0 1-.556 6.588A4 4 0 1 1 12 18Z" />
    <path d="M15 13a4.5 4.5 0 0 1-3-4 4.5 4.5 0 0 1-3 4" />
  </svg>
);

const RecommendPage = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const location = useLocation();

  const [profile, setProfile] = useState(location.state?.profile || null);
  const [skills, setSkills] = useState(location.state?.skills || []);
  const [targetRole, setTargetRole] = useState('');
  const [newSkill, setNewSkill] = useState('');
  const [showAddInput, setShowAddInput] = useState(false);
  const [fetching, setFetching] = useState(!location.state);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!location.state) {
      fetchAnalysisDetails();
    }
  }, [id]);

  const fetchAnalysisDetails = async () => {
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
      if (res.ok && json.data) {
        setProfile(json.data.profile_entities || {});
        setSkills(json.data.extracted_skills || []);
      } else {
        setError(json.message || 'Gagal memuat data analisis CV.');
      }
    } catch {
      setError('Tidak dapat terhubung ke server untuk memuat detail.');
    } finally {
      setFetching(false);
    }
  };

  const removeSkill = (index) => {
    setSkills((prev) => prev.filter((_, i) => i !== index));
  };

  const addSkill = () => {
    const trimmed = newSkill.trim();
    if (!trimmed) return;
    setSkills((prev) => [...prev, { surface: trimmed, normalized_guess: trimmed.toLowerCase() }]);
    setNewSkill('');
    setShowAddInput(false);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!targetRole.trim()) {
      setError('Target role wajib diisi.');
      return;
    }
    setError('');
    setSubmitting(true);

    try {
      const token = localStorage.getItem('token');
      const res = await fetch(`${import.meta.env.VITE_API_URL}/api/cv/recommend/${id}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          target_role: targetRole.trim(),
          skills: skills.map((sk) => sk.surface || sk.normalized_guess),
        }),
      });

      const json = await res.json();

      if (res.status === 401) {
        localStorage.removeItem('token');
        navigate('/login');
        return;
      }

      if (!res.ok) {
        setError(json.message || 'Gagal menganalisis kesenjangan skill.');
        return;
      }

      navigate(`/history/${id}`);
    } catch {
      setError('Tidak dapat terhubung ke server.');
    } finally {
      setSubmitting(false);
    }
  };

  if (fetching) {
    return (
      <div className="min-h-screen flex flex-col bg-[#F8F9FF]">
        <AppNavbar activeTab="analyze" />
        <main className="flex-1 flex flex-col items-center justify-center p-8">
          <div className="w-12 h-12 border-4 border-[#2563EB]/25 border-t-[#2563EB] rounded-full animate-spin" />
        </main>
        <Footer />
      </div>
    );
  }

  return (
    <div className="min-h-screen flex flex-col bg-[#F8F9FF]">
      <AppNavbar activeTab="analyze" />

      <main className="flex-1 flex flex-col gap-8 px-8 py-8 pt-[104px] pb-[104px] max-w-[1280px] w-full mx-auto animate-fade-in">
        <div className="flex flex-col gap-1">
          <h1 className="text-[40px] font-bold leading-[48px] tracking-[-0.8px] text-black">
            Define Target Career
          </h1>
          <p className="text-lg text-[#45474C]">
            Select your desired role to match your current profile skills against digital industry standards.
          </p>
        </div>

        <div className="flex gap-8 items-start w-full">
          <div className="flex-1 flex flex-col gap-6">
            <form onSubmit={handleSubmit} className="bg-white border border-black/[0.08] shadow-[0_1px_2px_rgba(0,0,0,0.05)] rounded-xl p-6 flex flex-col gap-6">
              <div className="flex flex-col gap-2">
                <label className="text-sm font-semibold text-[#45474C]">Target Career Role</label>
                <input
                  type="text"
                  required
                  value={targetRole}
                  onChange={(e) => setTargetRole(e.target.value)}
                  placeholder="e.g. Data Scientist, Frontend Developer, Backend Engineer"
                  className="w-full px-4 py-3 h-[48px] border border-[#C5C6CD] rounded-lg text-base text-[#0F172A] focus:outline-none focus:border-[#2563EB] focus:ring-2 focus:ring-blue-100 transition-all placeholder:text-[#C5C6CD]"
                />
              </div>

              {error && (
                <div className="px-4 py-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-600">
                  {error}
                </div>
              )}

              <button
                type="submit"
                disabled={submitting}
                className="w-full h-11 bg-[#2563EB] text-white text-base font-semibold rounded-lg hover:bg-[#1D4ED8] disabled:opacity-50 disabled:cursor-not-allowed transition-all active:scale-[0.99] flex items-center justify-center gap-2"
              >
                {submitting && (
                  <span className="w-4 h-4 border-2 border-white/40 border-t-white rounded-full animate-spin" />
                )}
                Analyze Skill Gap
              </button>
            </form>

            {profile && (profile.name || profile.email_address) && (
              <div className="bg-white border border-black/[0.08] shadow-[0_1px_2px_rgba(0,0,0,0.05)] rounded-xl p-6 flex flex-col gap-4">
                <div className="flex items-center gap-2 border-b border-black/[0.05] pb-3">
                  <UserIcon />
                  <span className="text-base font-bold text-[#0D1C2D]">User Profile Info</span>
                </div>
                <div className="grid grid-cols-2 gap-4 text-sm">
                  {profile.name && (
                    <div className="flex flex-col">
                      <span className="text-[#75777D] font-medium">Name</span>
                      <span className="text-[#0D1C2D] font-semibold mt-0.5">{profile.name}</span>
                    </div>
                  )}
                  {profile.email_address && (
                    <div className="flex flex-col">
                      <span className="text-[#75777D] font-medium">Email</span>
                      <span className="text-[#0D1C2D] font-semibold mt-0.5">{profile.email_address}</span>
                    </div>
                  )}
                  {profile.phone && (
                    <div className="flex flex-col">
                      <span className="text-[#75777D] font-medium">Phone</span>
                      <span className="text-[#0D1C2D] font-semibold mt-0.5">{profile.phone}</span>
                    </div>
                  )}
                  {profile.location && (
                    <div className="flex flex-col">
                      <span className="text-[#75777D] font-medium">Location</span>
                      <span className="text-[#0D1C2D] font-semibold mt-0.5">{profile.location}</span>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>

          <div className="w-[480px] bg-white border border-black/[0.08] shadow-[0_1px_2px_rgba(0,0,0,0.05)] rounded-xl p-6 flex flex-col gap-4 flex-shrink-0">
            <div className="flex items-center gap-2 border-b border-black/[0.05] pb-3">
              <BrainIcon />
              <span className="text-base font-bold text-[#0D1C2D]">Profile Skills</span>
            </div>
            <p className="text-sm text-[#75777D]">
              These skills will be matched. Feel free to refine them before proceeding.
            </p>

            <div className="flex flex-wrap gap-2 pt-2">
              {skills.map((sk, i) => (
                <div key={i} className="flex items-center gap-1 px-3 py-1.5 bg-[#EFF6FF] border border-[#2563EB]/20 rounded-full">
                  <span className="text-sm font-medium text-[#2563EB]">{sk.surface || sk.normalized_guess}</span>
                  <button
                    type="button"
                    onClick={() => removeSkill(i)}
                    className="ml-1 text-[#2563EB] hover:text-[#1D4ED8] transition-colors"
                  >
                    <XIcon />
                  </button>
                </div>
              ))}

              {showAddInput ? (
                <div className="flex items-center gap-2">
                  <input
                    autoFocus
                    type="text"
                    value={newSkill}
                    onChange={(e) => setNewSkill(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') addSkill();
                      if (e.key === 'Escape') setShowAddInput(false);
                    }}
                    placeholder="e.g. Python"
                    className="px-3 py-1.5 border border-[#C5C6CD] rounded-full text-sm focus:outline-none focus:border-[#2563EB] w-32 transition-all placeholder:text-[#C5C6CD]"
                  />
                  <button
                    type="button"
                    onClick={addSkill}
                    className="text-xs text-[#2563EB] font-bold hover:underline"
                  >
                    Add
                  </button>
                  <button
                    type="button"
                    onClick={() => setShowAddInput(false)}
                    className="text-xs text-[#75777D] hover:underline"
                  >
                    Cancel
                  </button>
                </div>
              ) : (
                <button
                  type="button"
                  onClick={() => setShowAddInput(true)}
                  className="flex items-center gap-1.5 px-3 py-1.5 border border-dashed border-[#C5C6CD] rounded-full text-sm text-[#45474C] hover:border-[#2563EB] hover:text-[#2563EB] transition-colors"
                >
                  <PlusIcon /> Add Skill
                </button>
              )}
            </div>
          </div>
        </div>
      </main>

      <Footer />
    </div>
  );
};

export default RecommendPage;
