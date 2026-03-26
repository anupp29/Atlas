import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { AtlasLogo } from '@/components/atlas/AtlasLogo';

export default function Login() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!email || !password) { setError('Enter your credentials'); return; }
    setLoading(true);
    setTimeout(() => {
      const success = login(email, password);
      if (success) navigate('/');
      else setError('Invalid credentials');
      setLoading(false);
    }, 400);
  };

  return (
    <div className="min-h-screen flex bg-background">
      {/* Left — Brand panel */}
      <div className="hidden lg:flex lg:w-[480px] bg-primary flex-col justify-between p-10">
        <div>
          <AtlasLogo size="lg" variant="light" />
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
            <AtlasLogo size="md" variant="dark" className="justify-center" />
          </div>

          <div className="bg-card rounded-xl border border-border p-8 shadow-sm">
            <h2 className="text-[18px] font-semibold text-foreground mb-1">Sign in</h2>
            <p className="text-[13px] text-muted-foreground mb-6">Enter your Atos Enterprise credentials</p>

            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="text-[12px] font-medium text-foreground block mb-1.5">Email address</label>
                <Input type="email" value={email} onChange={(e) => { setEmail(e.target.value); setError(''); }} placeholder="name@atos.net" className="h-10 text-[13px]" autoComplete="email" />
              </div>
              <div>
                <label className="text-[12px] font-medium text-foreground block mb-1.5">Password</label>
                <Input type="password" value={password} onChange={(e) => { setPassword(e.target.value); setError(''); }} placeholder="••••••••" className="h-10 text-[13px]" autoComplete="current-password" />
              </div>
              {error && <p className="text-[12px] text-status-critical">{error}</p>}
              <Button type="submit" disabled={loading} className="w-full h-10 bg-accent hover:bg-accent/90 text-accent-foreground font-medium text-[13px]">
                {loading ? 'Authenticating...' : 'Sign in'}
              </Button>
            </form>

            <div className="mt-5 pt-4 border-t border-border">
              <p className="text-[10px] text-muted-foreground text-center leading-relaxed">
                <span className="font-medium text-foreground">Demo Mode</span> — any email/password works
              </p>
              <div className="mt-2 grid grid-cols-2 gap-1.5 text-[9px] text-muted-foreground">
                <span className="bg-muted px-2 py-1 rounded text-center">a.petrov@atos.net → L1</span>
                <span className="bg-muted px-2 py-1 rounded text-center">s.weber@atos.net → L2</span>
                <span className="bg-muted px-2 py-1 rounded text-center">j.nakamura@atos.net → L3</span>
                <span className="bg-muted px-2 py-1 rounded text-center">c.laurent@atos.net → SDM</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
