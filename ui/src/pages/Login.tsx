import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Eye, EyeOff } from 'lucide-react';

const QUICK_SIGN_IN_USERS = [
  { label: 'L1', username: 'alex.l1' },
  { label: 'L2', username: 'nina.l2' },
  { label: 'L3', username: 'omar.l3' },
  { label: 'SDM', username: 'sara.sdm' },
  { label: 'Client', username: 'maria.client' },
] as const;

function toEnterpriseEmail(value: string): string {
  const normalized = value.trim().toLowerCase();
  if (!normalized) return '';
  return normalized.includes('@') ? normalized : `${normalized}@atos.net`;
}

export default function Login() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  const completeSignIn = (identifier: string, secret: string) => {
    setLoading(true);
    const email = toEnterpriseEmail(identifier);
    setTimeout(() => {
      const success = login(email, secret);
      if (success) {
        navigate('/');
      } else {
        setError('Sign in failed. Please try again.');
      }
      setLoading(false);
    }, 250);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!username.trim()) {
      setError('Enter your username or email');
      return;
    }
    completeSignIn(username, password);
  };

  const handleQuickSignIn = (quickUsername: string) => {
    setError('');
    setUsername(quickUsername);
    completeSignIn(quickUsername, '');
  };

  return (
    <div className="min-h-screen flex bg-background">
      {/* Left — Brand */}
      <div className="hidden lg:flex lg:w-[480px] bg-primary flex-col justify-between p-10">
        <div>
          <div className="flex items-center gap-3 mb-8">
            <svg className="h-10 w-10 shrink-0" viewBox="0 0 36 36" fill="none" xmlns="http://www.w3.org/2000/svg">
              <rect width="36" height="36" rx="7" fill="#1a2744"/>
              <path d="M18 26 L10 26 L18 10 L26 26 Z" fill="none" stroke="#0066CC" strokeWidth="1.8" strokeLinejoin="round"/>
              <path d="M18 26 L14 26 L18 18 L22 26 Z" fill="#0066CC"/>
              <circle cx="18" cy="10" r="1.8" fill="#38bdf8"/>
            </svg>
            <div>
              <h1 className="text-[20px] font-bold tracking-[0.2em] text-primary-foreground">ATLAS</h1>
              <p className="text-[10px] text-primary-foreground/50 tracking-[0.1em] uppercase">AIOps Platform</p>
            </div>
          </div>
          <h2 className="text-[28px] font-semibold text-primary-foreground leading-tight mt-16">
            Intelligent IT Operations
          </h2>
          <p className="text-[14px] text-primary-foreground/60 mt-4 leading-relaxed max-w-[340px]">
            Autonomous incident detection, root cause analysis, and resolution for mission-critical enterprise infrastructure.
          </p>
        </div>
        <div className="space-y-4">
          <div className="flex items-center gap-3">
            <div className="h-8 w-8 rounded-full bg-sidebar-accent flex items-center justify-center">
              <span className="text-[10px] font-semibold text-primary-foreground">10×</span>
            </div>
            <p className="text-[12px] text-primary-foreground/50">Faster MTTR than industry average</p>
          </div>
          <div className="flex items-center gap-3">
            <div className="h-8 w-8 rounded-full bg-sidebar-accent flex items-center justify-center">
              <span className="text-[10px] font-semibold text-primary-foreground">70%</span>
            </div>
            <p className="text-[12px] text-primary-foreground/50">Autonomous resolution rate</p>
          </div>
          <div className="flex items-center gap-3">
            <div className="h-8 w-8 rounded-full bg-sidebar-accent flex items-center justify-center">
              <span className="text-[10px] font-semibold text-primary-foreground">94%</span>
            </div>
            <p className="text-[12px] text-primary-foreground/50">Root cause accuracy</p>
          </div>
          <p className="text-[9px] text-primary-foreground/25 mt-6">© {new Date().getFullYear()} Atos SE — Internal Use Only</p>
        </div>
      </div>

      {/* Right — Login */}
      <div className="flex-1 flex items-center justify-center px-4">
        <div className="w-full max-w-[380px]">
          <div className="lg:hidden text-center mb-8">
            <div className="inline-flex items-center justify-center mb-3">
              <svg className="h-10 w-10" viewBox="0 0 36 36" fill="none" xmlns="http://www.w3.org/2000/svg">
                <rect width="36" height="36" rx="7" fill="#1a2744"/>
                <path d="M18 26 L10 26 L18 10 L26 26 Z" fill="none" stroke="#0066CC" strokeWidth="1.8" strokeLinejoin="round"/>
                <path d="M18 26 L14 26 L18 18 L22 26 Z" fill="#0066CC"/>
                <circle cx="18" cy="10" r="1.8" fill="#38bdf8"/>
              </svg>
            </div>
            <h1 className="text-[20px] font-bold tracking-[0.2em] text-foreground">ATLAS</h1>
            <p className="text-[11px] text-muted-foreground mt-0.5 tracking-wide uppercase">AIOps Platform</p>
          </div>

          <div className="bg-card rounded-xl border border-border p-8 shadow-sm">
            <h2 className="text-[18px] font-semibold text-foreground mb-1">Sign in</h2>
            <p className="text-[13px] text-muted-foreground mb-6">Use your enterprise username to continue</p>

            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label htmlFor="atlas-username" className="text-[12px] font-medium text-foreground block mb-1.5">Username or email</label>
                <div className="relative">
                  <Input
                    id="atlas-username"
                    type="text"
                    value={username}
                    onChange={(e) => { setUsername(e.target.value); setError(''); }}
                    placeholder="e.g. alex.l2"
                    className="h-10 text-[13px] pr-[90px]"
                    autoComplete="username"
                    autoFocus
                  />
                  <span className="absolute right-3 top-1/2 -translate-y-1/2 text-[12px] text-muted-foreground pointer-events-none">@atos.net</span>
                </div>
              </div>
              <div>
                <label htmlFor="atlas-password" className="text-[12px] font-medium text-foreground block mb-1.5">Password (optional)</label>
                <div className="relative">
                  <Input
                    id="atlas-password"
                    type={showPassword ? 'text' : 'password'}
                    value={password}
                    onChange={(e) => { setPassword(e.target.value); setError(''); }}
                    placeholder="••••••••"
                    className="h-10 text-[13px] pr-10"
                    autoComplete="current-password"
                  />
                  <button type="button" onClick={() => setShowPassword(!showPassword)} className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground">
                    {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </button>
                </div>
              </div>
              <p className="text-[11px] text-muted-foreground">Press Enter to continue. Role is inferred from your enterprise identity.</p>
              <p className="text-[11px] text-muted-foreground leading-relaxed bg-muted/40 border border-border rounded-md p-2.5">
                Workspace role is assigned from your enterprise identity and cannot be self-selected.
              </p>
              {error && <p className="text-[12px] text-status-critical">{error}</p>}
              <Button
                type="submit"
                disabled={loading}
                className="w-full h-10 bg-accent hover:bg-accent/90 text-accent-foreground font-medium text-[13px]"
              >
                {loading ? 'Signing in...' : 'Continue'}
              </Button>
            </form>

            <div className="mt-5">
              <p className="text-[11px] text-muted-foreground mb-2">Quick sign in</p>
              <div className="grid grid-cols-3 gap-2">
                {QUICK_SIGN_IN_USERS.map((quickUser) => (
                  <Button
                    key={quickUser.label}
                    type="button"
                    variant="outline"
                    disabled={loading}
                    className="h-8 text-[11px]"
                    onClick={() => handleQuickSignIn(quickUser.username)}
                  >
                    {quickUser.label}
                  </Button>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
