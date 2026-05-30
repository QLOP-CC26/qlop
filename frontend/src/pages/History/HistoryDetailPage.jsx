import React, { useState, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { ArrowLeft, Sparkles, Check } from 'lucide-react';
import AppNavbar from '../../components/AppNavbar/AppNavbar';
import Footer from '../../components/Footer/Footer';
import SectionCard from '../../components/SectionCard/SectionCard';
import CourseCard from '../../components/CourseCard/CourseCard';
import AlternativeRoleCard from '../../components/AlternativeRoleCard/AlternativeRoleCard';
import ReadinessBar from '../../components/ReadinessBar/ReadinessBar';
import RadarSection from '../../components/RadarSection/RadarSection';

const PIVOT_STEPS = [
  'AI model is retrieving matching alternative roles…',
  'Analyzing fit and your transferable skills…',
  'AI is exploring career paths outside the database…',
  'Almost done — formatting your personalized career recommendations…',
];

const HistoryDetailPage = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [pivotLoading, setPivotLoading] = useState(false);
  const [pivotStep, setPivotStep] = useState(0);
  const [pivotError, setPivotError] = useState('');

  useEffect(() => {
    fetchDetail();
  }, [id]);

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
      if (!res.ok) {
        setError(json.message || 'Failed to load details.');
        return;
      }
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
      if (res.status === 401) {
        localStorage.removeItem('token');
        navigate('/login');
        return;
      }
      if (!res.ok) {
        setPivotError(json.message || 'Failed to generate Career Pivot.');
        return;
      }
      setData((prev) => ({ ...prev, career_pivot: json.data, pivot_metadata: json.metadata }));
    } catch {
      setPivotError('Unable to connect to the server.');
    } finally {
      setPivotLoading(false);
    }
  };

  const profile = data?.profile_entities || {};
  const extractedSkills = data?.extracted_skills || profile?.skills || [];
  const topSkillsRaw = data?.top_skills;
  const skillGap = topSkillsRaw?.skill_gap || null;
  const readinessScore = topSkillsRaw?.readiness_score || null;
  const matchedSkills = [...new Set(skillGap?.matched_skills || [])];
  const missingSkills = skillGap?.missing_skills || [];
  const recommendedCourses = data?.recommended_courses || [];
  const careerPivot = data?.career_pivot;
  const alternativeRoles = careerPivot?.alternative_roles || [];
  const aiDiscoveredRoles = careerPivot?.ai_discovered_roles || [];
  const currentAssessment = careerPivot?.current_role_assessment || null;
  const suggestedCerts = careerPivot?.suggested_certifications || [];
  const universalAdvice = careerPivot?.universal_advice || '';
  const hasCareerPivot = alternativeRoles.length > 0 || aiDiscoveredRoles.length > 0;
  const pivotMeta = data?.pivot_metadata || null;

  if (isLoading) return (
    <div className="min-h-screen flex flex-col bg-[#F8F9FF]">
      <AppNavbar activeTab="history" />
      <main className="flex-1 flex flex-col gap-6 px-8 py-8 pt-[104px] pb-[104px] max-w-[1280px] w-full mx-auto animate-pulse">
        <div className="w-28 h-5 bg-[#C5C6CD]/30 rounded-md mb-2" />
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
        <button
          onClick={() => navigate('/history')}
          className="flex items-center gap-2 text-sm text-[#45474C] hover:text-[#2563EB] transition-all duration-200 hover:-translate-x-0.5 w-fit"
        >
          <ArrowLeft className="w-5 h-5" /> Back to history
        </button>

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

        {skillGap ? (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
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