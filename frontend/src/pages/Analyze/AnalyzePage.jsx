import { useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { CloudUpload, FileText, X } from 'lucide-react';
import AppNavbar from '../../components/AppNavbar/AppNavbar';
import Footer from '../../components/Footer/Footer';

const AnalyzePage = () => {
  const navigate = useNavigate();
  const fileInputRef = useRef(null);
  const [file, setFile] = useState(null);
  const [error, setError] = useState('');
  const [isDragActive, setIsDragActive] = useState(false);

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setIsDragActive(true);
    } else if (e.type === 'dragleave') {
      setIsDragActive(false);
    }
  };

  const validateAndSetFile = (selectedFile) => {
    setError('');
    if (!selectedFile) return;

    const validTypes = ['application/pdf'];
    const nameLower = selectedFile.name.toLowerCase();

    if (!validTypes.includes(selectedFile.type) && !nameLower.endsWith('.pdf')) {
      setError('Unsupported file format. Please upload a PDF file.');
      setFile(null);
      return;
    }

    if (selectedFile.size > 10 * 1024 * 1024) {
      setError('File size is too large. Maximum file size is 10 MB.');
      setFile(null);
      return;
    }

    setFile(selectedFile);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      validateAndSetFile(e.dataTransfer.files[0]);
    }
  };

  const handleChange = (e) => {
    e.preventDefault();
    if (e.target.files && e.target.files[0]) {
      validateAndSetFile(e.target.files[0]);
    }
  };

  const handleButtonClick = () => {
    fileInputRef.current.click();
  };

  const handleRemove = () => {
    setFile(null);
    setError('');
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const handleAnalyze = () => {
    if (!file) return;
    navigate('/analyzing', { state: { file } });
  };

  return (
    <div className="min-h-screen flex flex-col bg-slate-50">
      <AppNavbar activeTab="analyze" />

      <main className="flex-1 flex flex-col items-center justify-center px-4 py-8 pt-[104px] pb-[104px]">
        <div className="w-full max-w-[640px] flex flex-col gap-8">
          <div className="flex flex-col gap-2 text-center">
            <h1 className="text-[40px] font-bold leading-[48px] tracking-[-0.8px] text-black">
              Analyze Your CV
            </h1>
            <p className="text-lg text-[#45474C]">
              Upload your CV to extract skill entities and identify professional recommendations.
            </p>
          </div>

          <div className="bg-white border border-black/[0.08] shadow-[0_4px_20px_rgba(30,41,59,0.05)] rounded-xl p-8 flex flex-col gap-6">
            <div
              onDragEnter={handleDrag}
              onDragOver={handleDrag}
              onDragLeave={handleDrag}
              onDrop={handleDrop}
              onClick={!file ? handleButtonClick : undefined}
              className={`border-2 border-dashed rounded-xl p-8 flex flex-col items-center justify-center gap-4 transition-all cursor-pointer ${
                file ? 'border-[#2563EB]/40 bg-[#EFF6FF]/10' :
                isDragActive ? 'border-[#2563EB] bg-[#EFF6FF]/50 scale-[1.01]' :
                'border-[#C5C6CD] hover:border-[#2563EB] bg-slate-50'
              }`}
            >
              <input
                ref={fileInputRef}
                type="file"
                className="hidden"
                accept=".pdf"
                onChange={handleChange}
              />

              {!file ? (
                <>
                  <div className="w-16 h-16 rounded-full bg-[#EFF6FF] flex items-center justify-center animate-pulse">
                    <CloudUpload className="w-10 h-10 text-[#2563EB]" />
                  </div>
                  <div className="flex flex-col items-center gap-1">
                    <p className="text-base font-semibold text-[#0D1C2D]">
                      Drag and drop your CV file here
                    </p>
                    <p className="text-sm text-[#75777D]">
                      or click to browse your files
                    </p>
                  </div>
                  <p className="text-xs text-[#C5C6CD]">
                    Supports PDF up to 10 MB
                  </p>
                </>
              ) : (
                <div className="flex items-center justify-between w-full p-4 bg-slate-50 border border-black/[0.05] rounded-lg">
                  <div className="flex items-center gap-3 min-w-0">
                    <FileText className="w-6 h-6 text-[#45474C]" />
                    <div className="flex flex-col min-w-0">
                      <span className="text-sm font-semibold text-[#0D1C2D] truncate">
                        {file.name}
                      </span>
                      <span className="text-xs font-semibold text-[#75777D] tracking-wide">
                        {(file.size / 1024 / 1024).toFixed(2)} MB
                      </span>
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      handleRemove();
                    }}
                    className="p-2 text-[#75777D] hover:text-red-500 transition-colors rounded-lg hover:bg-red-50"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>
              )}
            </div>

            {error && (
              <div className="w-full px-4 py-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-600 text-center">
                {error}
              </div>
            )}

            <button
              type="button"
              onClick={handleAnalyze}
              disabled={!file}
              className="w-full h-11 bg-[#2563EB] text-white text-base font-semibold rounded-lg hover:bg-[#1D4ED8] disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200 ease-out hover:scale-[1.02] active:scale-[0.97] shadow-[0_2px_4px_rgba(37,99,235,0.15)] hover:shadow-[0_4px_12px_rgba(37,99,235,0.25)] disabled:transform-none disabled:shadow-none"
            >
              Analyze CV
            </button>
          </div>
        </div>
      </main>

      <Footer />
    </div>
  );
};

export default AnalyzePage;
