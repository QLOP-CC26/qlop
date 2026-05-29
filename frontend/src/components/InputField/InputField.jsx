import { useState } from 'react';

const EyeIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
    <path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7Z" />
    <circle cx="12" cy="12" r="3" />
  </svg>
);

const EyeOffIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
    <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94" />
    <path d="M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19" />
    <line x1="1" y1="1" x2="23" y2="23" />
  </svg>
);

const MailIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
    <rect x="2" y="4" width="20" height="16" rx="2" />
    <path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7" />
  </svg>
);

const LockIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
    <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
    <path d="M7 11V7a5 5 0 0 1 10 0v4" />
  </svg>
);

const UserIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="12" cy="8" r="4" />
    <path d="M4 20c0-4 3.6-7 8-7s8 3 8 7" />
  </svg>
);

const icons = { mail: MailIcon, lock: LockIcon, user: UserIcon };

const InputField = ({
  label,
  hint,
  onHintClick,
  type = 'text',
  placeholder,
  value,
  onChange,
  icon,
  error,
  id,
}) => {
  const [showPassword, setShowPassword] = useState(false);
  const isPassword = type === 'password';
  const inputType = isPassword ? (showPassword ? 'text' : 'password') : type;
  const IconComponent = icon ? icons[icon] : null;

  return (
    <div className="flex flex-col gap-2 w-full">
      {label && (
        <div className="flex justify-between items-center w-full">
          <label htmlFor={id} className="text-sm font-semibold text-[#45474C]">
            {label}
          </label>
          {hint && (
            <span
              onClick={onHintClick}
              className="text-sm text-[#0058BE] cursor-pointer hover:opacity-75 transition-opacity"
            >
              {hint}
            </span>
          )}
        </div>
      )}

      <div className={`flex items-center gap-2 px-2 py-3 w-full h-[50px] bg-white rounded-lg border transition-all
        ${error ? 'border-red-400 focus-within:ring-2 focus-within:ring-red-100' : 'border-[#C5C6CD] focus-within:border-[#2563EB] focus-within:ring-2 focus-within:ring-blue-100'}`}
      >
        {IconComponent && (
          <span className="text-[#75777D] flex-shrink-0">
            <IconComponent />
          </span>
        )}
        <input
          id={id}
          type={inputType}
          placeholder={placeholder}
          value={value}
          onChange={onChange}
          autoComplete="off"
          className="flex-1 border-none bg-transparent text-base text-[#0F172A] placeholder-[#75777D] outline-none"
        />
        {isPassword && (
          <button
            type="button"
            onClick={() => setShowPassword((prev) => !prev)}
            tabIndex={-1}
            aria-label={showPassword ? 'Hide password' : 'Show password'}
            className="text-[#75777D] hover:text-[#0F172A] transition-colors flex-shrink-0"
          >
            {showPassword ? <EyeOffIcon /> : <EyeIcon />}
          </button>
        )}
      </div>

      {error && <span className="text-xs text-red-500">{error}</span>}
    </div>
  );
};

export default InputField;
