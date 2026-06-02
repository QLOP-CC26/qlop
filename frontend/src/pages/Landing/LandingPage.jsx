import { Link } from 'react-router-dom';
import { Sparkles, ArrowRight, FileText, CloudUpload } from 'lucide-react';
import LandingNavbar from '../../components/Navbar/LandingNavbar';
import Button from '../../components/Button/Button';
import { useState, useEffect, useRef } from 'react';

import CursorPdf from '../../assets/cursor-pdf.png';
import HeroImg from '../../assets/hero-img.png';

const LandingPage = () => {

  const analyzeStates = [
    { score: 51, missing: 15, color: 'text-orange-500', bg: 'bg-orange-500' },
    { score: 85, missing: 4, color: 'text-green-500', bg: 'bg-green-500' },
    { score: 32, missing: 24, color: 'text-red-500', bg: 'bg-red-500' },
  ];
  
  const [step3Index, setStep3Index] = useState(0);
  useEffect(() => {
    const interval = setInterval(() => {
      setStep3Index((prev) => (prev + 1) % analyzeStates.length);
    }, 2500); // Berganti setiap 2.5 detik
    return () => clearInterval(interval);
  }, []);
  const currentStep3 = analyzeStates[step3Index];

  // 
  const step1Ref = useRef(null);
  const [cursorPos, setCursorPos] = useState({ x: 0, y: 0 });
  const [isHovering, setIsHovering] = useState(false);
  const handleMouseMove = (e) => {
    const rect = step1Ref.current.getBoundingClientRect();
    setCursorPos({
      x: e.clientX - rect.left,
      y: e.clientY - rect.top,
    });
  };
  // 

  return (
    <div className="min-h-screen bg-slate-50 font-sans">
      <LandingNavbar />

      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16 md:py-24 lg:py-32">
        <div className="flex flex-col lg:flex-row items-center gap-12 lg:gap-10">
          
          <div className="flex-1 space-y-6 md:space-y-8 text-center lg:text-left">
            <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-blue-100/60 text-blue-700 mx-auto lg:mx-0">
              <Sparkles className="w-4 h-4 fill-blue-700" />
              <span className="text-sm font-semibold tracking-wide">AI-Powered Analysis</span>
            </div>
            
            <h1 className="text-4xl md:text-5xl lg:text-6xl font-bold text-gray-900 leading-[1.15] tracking-tight">
              Understand Your Skill Gap Before Entering the Job Market
            </h1>
            
            <p className="text-base md:text-lg text-gray-600 max-w-2xl mx-auto lg:mx-0 leading-relaxed">
              QLOP uses advanced AI to analyze your CV against current market demands, identifying critical skill gaps and providing actionable learning paths.
            </p>
            
            <div className="flex flex-col sm:flex-row justify-center lg:justify-start gap-4 pt-4">
              <div className="w-full sm:w-48">
                <Link to="/register">
                  <Button variant="primary">
                    Register Now <ArrowRight className="w-4 h-4 ml-1" />
                  </Button>
                </Link>
              </div>
              <div className="w-full sm:w-56">
                <Link to="/login">
                  <Button variant="outline">Login to Dashboard</Button>
                </Link>
              </div>
            </div>
          </div>

          <div className="flex-1 w-full relative mt-8 lg:mt-0">
          <div className="w-full aspect-[4/3] rounded-3xl overflow-hidden">
              <img src={HeroImg} alt="QLOP Hero" className="w-full h-full object-cover" />
          </div>
          </div>

        </div>
      </section>

      <section id="how-to-use" className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-20 md:py-32">
        <div className="text-center max-w-3xl mx-auto mb-12 md:mb-16 px-4">
          <h2 className="text-3xl md:text-4xl font-bold text-gray-900 mb-4 tracking-tight">The Intelligence Engine</h2>
          <p className="text-base md:text-lg text-gray-600">Three steps from raw data to actionable professional growth.</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 md:gap-8">

          {/* Step 1 */}
          <div className="bg-white p-6 md:p-8 rounded-[2rem] shadow-sm border border-gray-100 hover:shadow-lg transition-all duration-300">
            <div className="w-12 h-12 rounded-full bg-blue-50 text-blue-600 font-bold text-lg flex items-center justify-center mb-6">1</div>
            <h3 className="text-xl font-bold text-gray-900 mb-3 tracking-tight">Upload Your CV</h3>
            <p className="text-gray-500 mb-6 leading-relaxed text-sm md:text-base">Drop your current resume in PDF format.</p>

            <div className="w-full aspect-video bg-slate-50/80 rounded-2xl border border-gray-100 p-4 flex items-center justify-center overflow-hidden relative">

              <div
                ref={step1Ref}
                onMouseEnter={() => setIsHovering(true)}
                onMouseLeave={() => setIsHovering(false)}
                onMouseMove={handleMouseMove}
                className={`w-full h-full border-2 border-dashed rounded-xl flex flex-col items-center justify-center gap-2 transition-all relative select-none
                  ${isHovering 
                    ? 'cursor-none border-[#2563EB] bg-[#EFF6FF]/50' 
                    : 'border-[#C5C6CD] bg-white/60'
                  }`}
              >
                <div className="w-10 h-10 rounded-full bg-[#EFF6FF] flex items-center justify-center animate-pulse">
                  <CloudUpload className="w-5 h-5 text-[#2563EB]" />
                </div>
                <p className="text-[11px] font-semibold text-[#0D1C2D]">Drag and drop your CV file here</p>
                <p className="text-[10px] text-[#75777D]">or click to browse your files</p>

                <img
                  src={CursorPdf}
                  alt="PDF cursor"
                  className={`absolute pointer-events-none z-20 w-14 h-auto hidden md:block transition-opacity duration-200 ${isHovering ? 'opacity-100' : 'opacity-0'}`}
                  style={{
                    left: `${cursorPos.x}px`,
                    top: `${cursorPos.y}px`,
                    transform: 'translate(-30%, -30%)',
                  }}
                />

                <img
                  src={CursorPdf}
                  alt="PDF file"
                  className="absolute bottom-2 left-2 w-10 h-auto md:hidden opacity-70"
                />
              </div>

            </div>
          </div>

          {/* Step 2 */}
          <div className="bg-white p-6 md:p-8 rounded-[2rem] shadow-sm border border-gray-100 hover:shadow-lg transition-all duration-300">
            <div className="w-12 h-12 rounded-full bg-blue-50 text-blue-600 font-bold text-lg flex items-center justify-center mb-6">2</div>
            <h3 className="text-xl font-bold text-gray-900 mb-3 tracking-tight">AI Extract Your Info</h3>
            <p className="text-gray-500 mb-6 leading-relaxed text-sm md:text-base">Our NLP engine parses your experience into structured data.</p>
            
            <div className="w-full aspect-video bg-slate-50/80 rounded-2xl border border-gray-100 p-4 flex flex-col gap-3 overflow-hidden relative">
              
              <style>
                {`
                  @keyframes scanLine {
                    0%, 100% { top: -5%; opacity: 0; }
                    10% { opacity: 1; }
                    50% { top: 105%; opacity: 1; }
                    90% { opacity: 1; }
                  }
                  .animate-scan {
                    animation: scanLine 2s ease-in-out infinite;
                  }
                  @keyframes pulseRing {
                    0% { box-shadow: 0 0 0 0 rgba(37, 99, 235, 0.4); transform: scale(0.95); }
                    70% { box-shadow: 0 0 0 8px rgba(37, 99, 235, 0); transform: scale(1); }
                    100% { box-shadow: 0 0 0 0 rgba(37, 99, 235, 0); transform: scale(0.95); }
                  }
                  .animate-ring {
                    animation: pulseRing 1.5s infinite;
                  }
                `}
              </style>

              <div className="relative bg-white rounded-xl shadow-sm border border-gray-100 p-3 flex items-center gap-3 overflow-hidden">
                <div className="absolute left-0 right-0 h-[2px] bg-blue-500 shadow-[0_0_12px_2px_rgba(59,130,246,0.8)] z-10 animate-scan pointer-events-none"></div>
                
                <div className="w-10 h-10 rounded-lg bg-blue-50 flex items-center justify-center text-blue-600 flex-shrink-0">
                  <FileText className="w-5 h-5" />
                </div>
                <div className="flex flex-col">
                  <span className="text-[13px] font-bold text-gray-800 leading-tight">Your CV file.pdf</span>
                  <span className="text-[11px] font-medium text-gray-400 mt-0.5">0.1 MB</span>
                </div>
              </div>
              <div className="flex items-start gap-3 px-2 mt-1">
                <div className="flex flex-col items-center mt-0.5">
                  <div className="w-[18px] h-[18px] rounded-full border-[2.5px] border-blue-500 flex items-center justify-center bg-white z-10 animate-ring flex-shrink-0">
                    <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
                  </div>
                  <div className="w-0.5 h-8 bg-gray-200 mt-1 rounded-full"></div>
                </div>
                
                <div className="flex flex-col pt-0.5">
                  <span className="text-[13px] font-bold text-gray-700">AI extracting profile</span>
                  <span className="text-[12px] text-indigo-500 mt-0.5 animate-pulse font-medium leading-tight">
                    AI model is extracting your CV information...
                  </span>
                </div>
              </div>

            </div>
          </div>

          {/* Step 3 */}
          <div className="bg-white p-6 md:p-8 rounded-[2rem] shadow-sm border border-gray-100 hover:shadow-lg transition-all duration-300">
            <div className="w-12 h-12 rounded-full bg-blue-50 text-blue-600 font-bold text-lg flex items-center justify-center mb-6">3</div>
            <h3 className="text-xl font-bold text-gray-900 mb-3 tracking-tight">Analyze Your Skill Gap</h3>
            <p className="text-gray-500 mb-6 leading-relaxed text-sm md:text-base">Compare your profile against target roles in your industry.</p>
            
            <div className="w-full aspect-video bg-slate-50/80 rounded-2xl border border-gray-100 p-4 flex flex-col justify-center gap-4 overflow-hidden relative">
              
              <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-3">
                 <div className="flex justify-between items-end mb-2">
                    <span className="text-[12px] font-bold text-gray-500">Readiness Score</span>
                    <span className={`text-[15px] font-bold transition-colors duration-500 ${currentStep3.color}`}>
                      {currentStep3.score}%
                    </span>
                 </div>
                 <div className="w-full h-1.5 bg-gray-100 rounded-full overflow-hidden">
                    <div 
                      className={`h-full rounded-full transition-all duration-[800ms] ease-out ${currentStep3.bg}`} 
                      style={{ width: `${currentStep3.score}%` }}
                    ></div>
                 </div>
              </div>
              <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-3.5 flex items-center justify-between">
                 <span className="text-[15px] font-bold text-gray-800">Missing Skills</span>
                 <span className="text-[15px] font-bold text-[#F43F5E] transition-all duration-500">
                   ({currentStep3.missing})
                 </span>
              </div>
            </div>
          </div>

          {/*  */}

        </div>
      </section>

      <section id="streamlit" className="bg-[#2563EB] py-8 md:py-10">
        <div className="max-w-[1440px] mx-auto px-4 sm:px-6 lg:px-12">
          <div className="w-full h-[65vh] md:h-[85vh] min-h-[500px] bg-slate-900 rounded-2xl md:rounded-3xl shadow-2xl overflow-hidden relative">
            <iframe 
              src="https://dashboard-qlop.streamlit.app/?embed=true" 
              className="w-full h-full border-0 absolute top-0 left-0"
              title="Streamlit App"
              allowFullScreen
            ></iframe>
          </div>
        </div>
      </section>

      <footer className="bg-white py-8 border-t border-gray-200">
        <div className="max-w-7xl mx-auto px-4 text-center">
          <p className="text-sm text-gray-500 font-medium">
            © 2026 QLOP. All rights reserved.
          </p>
        </div>
      </footer>
    </div>
  );
};

export default LandingPage;