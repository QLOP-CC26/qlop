import LandingNavbar from '../../components/Navbar/LandingNavbar';

const GithubIcon = ({ className }) => (
  <svg 
    xmlns="http://www.w3.org/2000/svg" 
    viewBox="0 0 24 24" 
    width="16" 
    height="16" 
    fill="currentColor" 
    className={className}
  >
    <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z" />
  </svg>
);

const teamMembers = [
  {
    id: 1,
    name: 'Fauzan Arif Tricahya',
    role: 'Full-Stack Web Developer',
    github: 'fauzan-arift',
    image: '/Fauzan-qlop.png',
  },
  {
    id: 2,
    name: 'Dinaranaya Putri Hutauruk',
    role: 'Data Scientist',
    github: 'Dnrany',
    image: '/Dinar-qlop.png',
  },
  {
    id: 3,
    name: 'Husni Abdillah',
    role: 'AI Engineer',
    github: 'HusniAbdillah',
    image: '/Husni-qlop.png',
  },
  {
    id: 4,
    name: 'Wandy Chandra Wijaya',
    role: 'Full-Stack Web Developer',
    github: 'wandychandra',
    image: '/Wandy-qlop.png',
  },
  {
    id: 5,
    name: 'Diko Duwi Saputra',
    role: 'Data Scientist',
    github: 'dikosaputra1231',
    image: '/Diko-qlop.png',
  },
  {
    id: 6,
    name: 'Gilang Agung Prakoso',
    role: 'AI Engineer',
    github: 'prakoso09',
    image: '/Gilang-qlop.png',
  },
];

const AboutUsPage = () => {
  return (
    <div className="min-h-screen bg-white font-sans">
      <LandingNavbar />

      <section 
        className="relative py-32 md:py-48 flex items-center justify-center bg-fixed bg-center bg-cover"
        style={{
          backgroundImage: "url('/aboutqlop.jpeg')"
        }}
      >
        <div className="absolute inset-0 bg-slate-950/75 backdrop-blur-[2px]"></div>

        <div className="relative z-10 text-center px-4 max-w-4xl mx-auto">
          <h1 className="text-4xl md:text-5xl lg:text-[56px] font-bold text-white mb-6 tracking-tight">
            The People Behind QLOP
          </h1>
          <p className="text-lg md:text-xl text-gray-300 mb-10 leading-relaxed font-medium">
            A small team trying to make career preparation less confusing for future developers.
          </p>
          <a 
            href="#mission" 
            className="inline-flex items-center justify-center px-8 py-3.5 rounded-xl bg-white text-gray-900 font-bold hover:bg-gray-100 transition-all hover:scale-105 shadow-xl"
          >
            Explore the Project
          </a>
        </div>
      </section>

      {/* Team Section */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-24">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">

          {teamMembers.map((member) => (
            <div key={member.id} className="bg-white p-6 rounded-[2rem] shadow-sm border border-gray-100 hover:shadow-lg transition-all duration-300 flex items-center gap-5 group">
              
              {/* Foto Profil */}
              <div className="flex-shrink-0 w-20 h-20 rounded-full bg-slate-100 border border-gray-200 flex items-center justify-center overflow-hidden">
                {member.image ? (
                  <img src={member.image} alt={member.name} className="w-full h-full object-cover" />
                ) : (
                  <span className="text-gray-400 text-xs font-semibold text-center leading-tight">Foto<br/>{member.name.split(' ')[0]}</span>
                )}
              </div>

              {/* Teks Identitas */}
              <div className="flex flex-col items-start">
                <h3 className="text-lg font-bold text-gray-900 mb-1">{member.name}</h3>
                
                <a 
                  href={`https://github.com/${member.github}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-1.5 text-sm font-medium text-gray-500 hover:text-gray-900 transition-colors mb-3"
                >
                  <GithubIcon className="w-4 h-4 text-gray-400 group-hover:text-gray-900 transition-colors" />
                  {member.github}
                </a>

                <span className="px-3 py-1 bg-blue-50 text-blue-700 text-[11px] uppercase tracking-wider font-bold rounded-full">
                  {member.role}
                </span>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Why We Built QLOP Section */}
      <section id="mission" className="bg-slate-50 py-24 border-t border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex flex-col lg:flex-row gap-12 lg:gap-20 items-center">
            
            <div className="lg:w-1/3">
              <h2 className="text-3xl md:text-4xl font-bold text-gray-900 mb-6 tracking-tight">
                Why We Built QLOP
              </h2>
              <div className="space-y-4 text-gray-600 leading-relaxed">
                <p>
                  Navigating the transition from learning to doing is daunting. We built QLOP because we experienced firsthand the confusion of trying to map academic skills to real-world job requirements.
                </p>
                <p>
                  Our mission is to provide clear, actionable intelligence that bridges the gap between potential and performance, helping future developers chart their path with confidence and precision.
                </p>
              </div>
            </div>

            <div className="lg:w-2/3 flex flex-col gap-5">
              <div className="bg-white p-6 md:p-8 rounded-3xl shadow-sm border border-gray-100 hover:shadow-md transition-shadow">
                <h3 className="text-xl font-bold text-gray-900 mb-3">Unclear Career Direction</h3>
                <p className="text-gray-600">You have skills, but don't know which roles they best align with or what's missing to land the job.</p>
              </div>

              <div className="bg-white p-6 md:p-8 rounded-3xl shadow-sm border border-gray-100 hover:shadow-md transition-shadow">
                <h3 className="text-xl font-bold text-gray-900 mb-3">Skill Gaps Slow Hiring</h3>
                <p className="text-gray-600">Hidden gaps in your CV lead to immediate rejections by ATS systems before a human ever sees it.</p>
              </div>

              <div className="bg-white p-6 md:p-8 rounded-3xl shadow-sm border border-gray-100 hover:shadow-md transition-shadow">
                <h3 className="text-xl font-bold text-gray-900 mb-3">AI-Powered Guidance</h3>
                <p className="text-gray-600">Get precise, data-driven insights to focus your learning on the skills that actually matter right now.</p>
              </div>
            </div>

          </div>
        </div>
      </section>

      {/* Footer */}
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

export default AboutUsPage;