import React from 'react';

export const ReadinessBar = ({ score, interpretation }) => {
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

export default ReadinessBar;
