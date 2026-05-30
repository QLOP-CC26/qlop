import React from 'react';

export const SectionCard = ({ children, className = '' }) => (
  <div className={`bg-white border border-black/[0.06] rounded-xl p-6 ${className}`}>
    {children}
  </div>
);

export default SectionCard;
