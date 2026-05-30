const Button = ({
  children,
  type = 'button',
  variant = 'primary',
  loading = false,
  disabled = false,
  onClick,
  id,
}) => {
  const base = 'flex items-center justify-center gap-2 w-full h-10 rounded-lg text-base font-semibold transition-all duration-200 ease-out hover:scale-[1.02] active:scale-[0.97] disabled:opacity-60 disabled:cursor-not-allowed disabled:transform-none disabled:shadow-none cursor-pointer';

  const variants = {
    primary: 'bg-[#2563EB] text-white hover:bg-[#1D4ED8] shadow-[0_2px_4px_rgba(37,99,235,0.15)] hover:shadow-[0_4px_12px_rgba(37,99,235,0.25)]',
    outline: 'bg-white text-[#0F172A] border border-[#C5C6CD] hover:bg-slate-50 shadow-[0_1px_2px_rgba(0,0,0,0.05)] hover:shadow-[0_4px_8px_rgba(0,0,0,0.05)]',
  };

  return (
    <button
      id={id}
      type={type}
      className={`${base} ${variants[variant]}`}
      onClick={onClick}
      disabled={disabled || loading}
    >
      {loading && (
        <span className={`w-4 h-4 rounded-full border-2 animate-spin
          ${variant === 'primary' ? 'border-white/40 border-t-white' : 'border-black/20 border-t-gray-700'}`}
        />
      )}
      {children}
    </button>
  );
};

export default Button;
