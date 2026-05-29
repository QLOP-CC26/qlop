import { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import Navbar from '../../components/Navbar/Navbar';
import Footer from '../../components/Footer/Footer';
import InputField from '../../components/InputField/InputField';
import Button from '../../components/Button/Button';
import Divider from '../../components/Divider/Divider';

const GoogleIcon = () => (
  <svg width="20" height="20" viewBox="0 0 48 48" xmlns="http://www.w3.org/2000/svg">
    <path fill="#FFC107" d="M43.6 20.1H42V20H24v8h11.3C33.7 32.7 29.3 36 24 36c-6.6 0-12-5.4-12-12s5.4-12 12-12c3.1 0 5.8 1.1 7.9 3l5.7-5.7C34.1 6.5 29.3 4 24 4 12.9 4 4 12.9 4 24s8.9 20 20 20 20-8.9 20-20c0-1.3-.1-2.7-.4-3.9z"/>
    <path fill="#FF3D00" d="M6.3 14.7l6.6 4.8C14.5 15.8 18.9 12 24 12c3.1 0 5.8 1.1 7.9 3l5.7-5.7C34.1 6.5 29.3 4 24 4 16.3 4 9.7 8.3 6.3 14.7z"/>
    <path fill="#4CAF50" d="M24 44c5.2 0 9.9-2 13.4-5.2l-6.2-5.2C29.4 35.4 26.8 36 24 36c-5.2 0-9.7-3.3-11.4-8H6.2C9.5 35.5 16.3 44 24 44z"/>
    <path fill="#1976D2" d="M43.6 20.1H42V20H24v8h11.3c-.8 2.2-2.2 4.1-4 5.5l6.2 5.2C41 35.8 44 30.4 44 24c0-1.3-.1-2.7-.4-3.9z"/>
  </svg>
);

const LoginPage = () => {
  const navigate = useNavigate();
  const [form, setForm] = useState({ email: '', password: '' });
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
        setError(data.message || 'Login Google gagal. Coba lagi.');
        return;
      }

      localStorage.setItem('token', data.data.token);
      navigate('/analyze');
    } catch {
      setError('Tidak dapat terhubung ke server.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (window.google) {
      window.google.accounts.id.initialize({
        client_id: '248938643014-g9kuq5abhqt6vk2mu4pak9qrr1cbnnp3.apps.googleusercontent.com',
        callback: handleGoogleCallback,
      });
      window.google.accounts.id.renderButton(
        document.getElementById('google-signin-btn'),
        { theme: 'outline', size: 'large', width: 396 }
      );
    }
  }, []);

  const handleChange = (field) => (e) => {
    setForm((prev) => ({ ...prev, [field]: e.target.value }));
    if (error) setError('');
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    if (!form.email || !form.password) {
      setError('Email dan password wajib diisi.');
      return;
    }

    setLoading(true);
    try {
      const res = await fetch(`${import.meta.env.VITE_API_URL}/api/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(form),
      });

      const data = await res.json();

      if (!res.ok) {
        setError(data.message || 'Login gagal. Coba lagi.');
        return;
      }

      localStorage.setItem('token', data.data.token);
      navigate('/analyze');
    } catch {
      setError('Tidak dapat terhubung ke server.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex flex-col bg-[#F8F9FF]">
      <Navbar actionLabel="Register" actionTo="/register" />

      <main className="flex-1 flex items-center justify-center px-4 py-[72px]">
        <div className="flex flex-col gap-6 w-full max-w-[448px] bg-white border border-black/[0.08] shadow-[0_4px_20px_rgba(30,41,59,0.05)] rounded-xl p-6">

          <div className="flex flex-col items-center gap-2">
            <h1 className="text-3xl font-semibold text-[#0D1C2D] text-center">Welcome Back</h1>
            <p className="text-sm text-[#45474C] text-center">
              Sign in to access your intelligent precision insights.
            </p>
          </div>

          {error && (
            <div className="w-full px-4 py-2.5 bg-red-50 border border-red-200 rounded-lg text-sm text-red-600 text-center">
              {error}
            </div>
          )}

          <form className="flex flex-col gap-6 pb-4" onSubmit={handleSubmit} noValidate>
            <InputField
              id="login-email"
              label="Email Address"
              type="email"
              placeholder="you@gmail.com"
              icon="mail"
              value={form.email}
              onChange={handleChange('email')}
            />
            <InputField
              id="login-password"
              label="Password"
              type="password"
              placeholder="••••••••"
              icon="lock"
              hint="Forgot password?"
              value={form.password}
              onChange={handleChange('password')}
            />
            <Button id="login-submit" type="submit" variant="primary" loading={loading}>
              Login
            </Button>
          </form>

          <Divider />

          <div className="w-full flex justify-center">
            <div id="google-signin-btn" className="w-full max-w-[396px] flex justify-center"></div>
          </div>

          <p className="text-sm text-[#45474C] text-center pt-2">
            Don't have an account?{' '}
            <Link to="/register" className="text-[#0058BE] font-semibold hover:opacity-75 transition-opacity">
              Register
            </Link>
          </p>
        </div>
      </main>

      <Footer />
    </div>
  );
};

export default LoginPage;
