import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Menu, X, BarChart3, History, LogOut } from 'lucide-react';

const AppNavbar = ({ activeTab }) => {
  const navigate = useNavigate();
  const [isOpen, setIsOpen] = useState(false);

  const handleLogout = () => {
    localStorage.removeItem('token');
    navigate('/login');
  };

  const tabClass = (tab) =>
    tab === activeTab
      ? 'px-2 py-2 text-base font-semibold text-[#2563EB] border-b-4 border-[#2563EB] md:border-b-4 md:rounded-t-lg transition-colors'
      : 'px-2 py-2 text-base font-medium text-[#475569] hover:text-[#2563EB] transition-colors';

  const mobileTabClass = (tab) =>
    tab === activeTab
      ? 'flex items-center gap-3 px-4 py-3 text-base font-semibold text-[#2563EB] bg-[#EFF6FF] rounded-xl transition-all w-full text-left'
      : 'flex items-center gap-3 px-4 py-3 text-base font-medium text-[#475569] hover:text-[#2563EB] hover:bg-[#F8F9FF] rounded-xl transition-all w-full text-left';

  return (
    <>
      <nav className="fixed top-0 left-0 w-full h-18 bg-white border-b border-black/5 flex items-center px-5 gap-5 z-40">
        <Link to="/" className="flex items-center gap-2 text-2xl font-bold tracking-[-1.2px] text-[#0F172A] flex-shrink-0">
          <img src="/logo.png" alt="QLOP Logo" className="w-8 h-8 object-contain" />
          QLOP
        </Link>

        {/* Desktop navigation */}
        <div className="hidden md:flex items-center gap-4 ml-4 h-full">
          <Link to="/analyze" className={tabClass('analyze')}>Analyze</Link>
          <Link to="/history" className={tabClass('history')}>History</Link>
        </div>

        <button
          onClick={handleLogout}
          className="hidden md:flex items-center gap-2 ml-auto px-4 py-2 border border-red-200 text-red-600 hover:bg-red-50 text-sm font-semibold rounded-lg transition-all active:scale-[0.98]"
        >
          <LogOut className="w-4 h-4" />
          Logout
        </button>

        {/* Mobile menu button */}
        <button
          onClick={() => setIsOpen(true)}
          className="ml-auto md:hidden p-2 text-[#475569] hover:text-[#2563EB] transition-colors"
          aria-label="Open Menu"
        >
          <Menu className="w-6 h-6" />
        </button>
      </nav>

      {/* Mobile nav drawer with backdrop overlay */}
      {isOpen && (
        <div className="fixed inset-0 z-50 md:hidden">
          {/* Backdrop blur overlay */}
          <div 
            className="fixed inset-0 bg-[#0F172A]/40 backdrop-blur-sm transition-opacity duration-300"
            onClick={() => setIsOpen(false)}
          />

          {/* Drawer container panel */}
          <div className="fixed top-0 right-0 bottom-0 w-[280px] bg-white shadow-2xl z-50 flex flex-col p-6 gap-6 transform transition-transform duration-300 ease-out border-l border-black/5">
            {/* Header */}
            <div className="flex items-center justify-between pb-4 border-b border-black/[0.05]">
              <div className="flex items-center gap-2 text-xl font-bold tracking-[-0.8px] text-[#0F172A]">
                <img src="/logo.png" alt="QLOP Logo" className="w-7 h-7 object-contain" />
                QLOP
              </div>
              <button
                onClick={() => setIsOpen(false)}
                className="p-1.5 hover:bg-slate-100 rounded-lg text-[#475569] hover:text-[#0F172A] transition-all"
                aria-label="Close Menu"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Menu Items */}
            <div className="flex flex-col gap-2 flex-1">
              <Link
                to="/analyze"
                onClick={() => setIsOpen(false)}
                className={mobileTabClass('analyze')}
              >
                <BarChart3 className="w-5 h-5" />
                Analyze
              </Link>
              <Link
                to="/history"
                onClick={() => setIsOpen(false)}
                className={mobileTabClass('history')}
              >
                <History className="w-5 h-5" />
                History
              </Link>
            </div>

            {/* Footer / Logout */}
            <div className="pt-4 border-t border-black/[0.05]">
              <button
                onClick={() => {
                  setIsOpen(false);
                  handleLogout();
                }}
                className="flex items-center gap-3 w-full px-4 py-3 text-base font-semibold text-red-600 hover:bg-red-50/70 rounded-xl transition-all text-left"
              >
                <LogOut className="w-5 h-5" />
                Logout
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
};

export default AppNavbar;
