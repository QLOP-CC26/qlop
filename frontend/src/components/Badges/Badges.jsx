import React from 'react';

export const DifficultyBadge = ({ level }) => {
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

export const TransitionBadge = ({ difficulty }) => {
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
