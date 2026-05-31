import { Link } from 'react-router-dom';

const Navbar = ({ actionLabel, actionTo }) => {
  return (
    <nav className="fixed top-0 left-0 w-full h-18 bg-white border-b border-black/5 flex items-center px-5 gap-5 z-50">
      <Link to="/" className="flex items-center gap-2 text-2xl font-bold tracking-[-1.2px] text-[#0F172A]">
        <img src="/logo.png" alt="QLOP Logo" className="w-8 h-8 object-contain" />
        QLOP
      </Link>
      <div className="flex-1" />
      {actionLabel && actionTo && (
        <Link
          to={actionTo}
          className="text-sm font-medium text-[#45474C] hover:text-[#2563EB] transition-colors"
        >
          {actionLabel}
        </Link>
      )}
    </nav>
  );
};

export default Navbar;
