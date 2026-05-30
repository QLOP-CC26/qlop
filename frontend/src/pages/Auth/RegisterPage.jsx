import { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import Navbar from '../../components/Navbar/Navbar';
import Footer from '../../components/Footer/Footer';
import InputField from '../../components/InputField/InputField';
import Button from '../../components/Button/Button';
import Divider from '../../components/Divider/Divider';

const RegisterPage = () => {
  const navigate = useNavigate();
  const [form, setForm] = useState({ name: '', email: '', password: '' });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleGoogleCallback = async (response) => {
    setError('');
    setLoading(true);
    try {
      const res = await fetch(`${import.meta.env.VITE_API_URL}/api/auth/google`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id_token: response.credential }),
      });

      const data = await res.json();

      if (!res.ok) {
        setError(data.message || 'Google registration failed. Please try again.');
        return;
      }

      localStorage.setItem('token', data.data.token);
      navigate('/analyze');
    } catch {
      setError('Unable to connect to the server.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (window.google) {
      const renderGoogleBtn = () => {
        const btnContainer = document.getElementById('google-signin-btn');
        if (!btnContainer) return;
        
        // Google GSI button width constraint: min 200, max 400
        const containerWidth = btnContainer.offsetWidth || 396;
        const targetWidth = Math.max(200, Math.min(396, containerWidth));
        
        btnContainer.innerHTML = '';
        
        window.google.accounts.id.initialize({
          client_id: '248938643014-g9kuq5abhqt6vk2mu4pak9qrr1cbnnp3.apps.googleusercontent.com',
          callback: handleGoogleCallback,
        });
        window.google.accounts.id.renderButton(
          btnContainer,
          { theme: 'outline', size: 'large', width: targetWidth }
        );
      };

      renderGoogleBtn();

      let resizeTimeout;
      const handleResize = () => {
        clearTimeout(resizeTimeout);
        resizeTimeout = setTimeout(renderGoogleBtn, 150);
      };

      window.addEventListener('resize', handleResize);
      return () => window.removeEventListener('resize', handleResize);
    }
  }, []);

  const handleChange = (field) => (e) => {
    setForm((prev) => ({ ...prev, [field]: e.target.value }));
    if (error) setError('');
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    if (!form.name || !form.email || !form.password) {
      setError('All fields are required.');
      return;
    }

    if (form.password.length < 8) {
      setError('Password must be at least 8 characters.');
      return;
    }

    setLoading(true);
    try {
      const res = await fetch(`${import.meta.env.VITE_API_URL}/api/auth/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(form),
      });

      const data = await res.json();

      if (!res.ok) {
        setError(data.message || 'Registration failed. Please try again.');
        return;
      }

      localStorage.setItem('token', data.data.token);
      navigate('/analyze');
    } catch {
      setError('Unable to connect to the server.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex flex-col bg-[#F8F9FF]">
      <Navbar actionLabel="Login" actionTo="/login" />

      <main className="flex-1 flex items-center justify-center px-4 py-[72px]">
        <div className="flex flex-col gap-6 w-full max-w-[448px] bg-white border border-black/[0.08] shadow-[0_4px_20px_rgba(30,41,59,0.05)] rounded-xl p-6">

          <div className="flex flex-col items-center gap-2">
            <h1 className="text-3xl font-semibold text-[#0D1C2D] text-center">Create Account</h1>
            <p className="text-sm text-[#45474C] text-center">
              Start analyzing your skills and get personalized recommendations
            </p>
          </div>

          {error && (
            <div className="w-full px-4 py-2.5 bg-red-50 border border-red-200 rounded-lg text-sm text-red-600 text-center">
              {error}
            </div>
          )}

          <form className="flex flex-col gap-6 pb-4" onSubmit={handleSubmit} noValidate>
            <InputField
              id="register-name"
              label="Full Name"
              type="text"
              placeholder="John Doe"
              icon="user"
              value={form.name}
              onChange={handleChange('name')}
            />
            <InputField
              id="register-email"
              label="Email Address"
              type="email"
              placeholder="you@gmail.com"
              icon="mail"
              value={form.email}
              onChange={handleChange('email')}
            />
            <InputField
              id="register-password"
              label="Password"
              type="password"
              placeholder="••••••••"
              icon="lock"
              value={form.password}
              onChange={handleChange('password')}
            />
            <Button id="register-submit" type="submit" variant="primary" loading={loading}>
              Create Account
            </Button>
          </form>

          <Divider />

          <div className="w-full flex justify-center">
            <div id="google-signin-btn" className="w-full max-w-[396px] flex justify-center"></div>
          </div>

          <p className="text-sm text-[#45474C] text-center pt-2">
            Already have an account?{' '}
            <Link to="/login" className="text-[#0058BE] font-semibold hover:opacity-75 transition-opacity">
              Login
            </Link>
          </p>
        </div>
      </main>

      <Footer />
    </div>
  );
};

export default RegisterPage;
