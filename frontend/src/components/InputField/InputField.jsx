import { useState } from 'react';
import { Eye, EyeOff, Mail, Lock, User } from 'lucide-react';

const icons = { mail: Mail, lock: Lock, user: User };

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
            <IconComponent className="w-5 h-5" />
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
            {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
          </button>
        )}
      </div>

      {error && <span className="text-xs text-red-500">{error}</span>}
    </div>
  );
};

export default InputField;
