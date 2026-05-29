import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import LoginPage from './pages/Auth/LoginPage';
import RegisterPage from './pages/Auth/RegisterPage';
import AnalyzePage from './pages/Analyze/AnalyzePage';
import AnalyzingPage from './pages/Analyzing/AnalyzingPage';
import RecommendPage from './pages/Recommend/RecommendPage';
import HistoryPage from './pages/History/HistoryPage';
import HistoryDetailPage from './pages/History/HistoryDetailPage';
import ProtectedRoute from './components/ProtectedRoute/ProtectedRoute';
import './index.css';

const App = () => {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
        
        <Route path="/analyze" element={
          <ProtectedRoute>
            <AnalyzePage />
          </ProtectedRoute>
        } />
        <Route path="/analyzing" element={
          <ProtectedRoute>
            <AnalyzingPage />
          </ProtectedRoute>
        } />
        <Route path="/recommend/:id" element={
          <ProtectedRoute>
            <RecommendPage />
          </ProtectedRoute>
        } />
        <Route path="/history" element={
          <ProtectedRoute>
            <HistoryPage />
          </ProtectedRoute>
        } />
        <Route path="/history/:id" element={
          <ProtectedRoute>
            <HistoryDetailPage />
          </ProtectedRoute>
        } />

        <Route path="*" element={<Navigate to="/analyze" replace />} />
      </Routes>
    </BrowserRouter>
  );
};

export default App;
