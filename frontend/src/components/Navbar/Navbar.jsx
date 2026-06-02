import { Link } from 'react-router-dom';

const Navbar = ({ actionLabel, actionTo }) => {
  return (
    <nav className="fixed top-0 left-0 z-50 w-full bg-white/90 backdrop-blur-md border-b border-gray-200">
      <div className="max-w-[1440px] mx-auto px-4 sm:px-6 lg:px-12 w-full">
        <div className="flex items-center justify-between h-16 w-full">
          {/* Logo */}
          <div className="flex-shrink-0">
            <Link to="/" className="flex items-center gap-2">
              <img
                src="/logo.png"
                alt="QLOP Logo"
                className="w-8 h-8 object-contain"
              />
              <span className="text-2xl font-black text-gray-900 tracking-tighter">
                QLOP
              </span>
            </Link>
          </div>

          {/* Action Link */}
          {actionLabel && actionTo && (
            <Link
              to={actionTo}
              className="text-sm font-semibold text-blue-600 hover:text-blue-700 transition-colors"
            >
              {actionLabel}
            </Link>
          )}
        </div>
      </div>
    </nav>
  );
};

export default Navbar;
