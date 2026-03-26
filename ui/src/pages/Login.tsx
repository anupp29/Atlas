import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Shield, Eye, EyeOff } from 'lucide-react';
import type { UserRole } from '@/types/atlas';

const roleOptions: { value: UserRole; label: string }[] = [
  { value: 'L1', label: 'L1 Engineer' },
  { value: 'L2', label: 'L2 Engineer' },
  { value: 'L3', label: 'L3 / SRE' },
  { value: 'SDM', label: 'Service Delivery Manager' },
  { value: 'CLIENT', label: 'Client Portal' },
];

export default function Login() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [role, setRole] = useState<UserRole | ''>('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!username || !password || !role) {
      setError(!role ? 'Select your role' : 'Enter your credentials');
      return;
    }
    setLoading(true);
    const email = username.includes('@') ? username : `${username}@atos.net`;
    setTimeout(() => {
      const success = login(email, password, role as UserRole);
      if (success) {
        navigate('/');
      } else {
        setError('Invalid credentials');
      }
      setLoading(false);
    }, 400);
  };

  return (
    <div className="min-h-screen flex bg-background">
      {/* Left — Brand */}
      <div className="hidden lg:flex lg:w-[480px] bg-primary flex-col justify-between p-10">
        <div>
          <div className="flex items-center gap-3 mb-8">
            <div className="h-10 w-10 rounded-lg bg-accent flex items-center justify-center">
              <Shield className="h-5 w-5 text-accent-foreground" />
            </div>
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
            <div className="inline-flex items-center justify-center h-10 w-10 rounded-lg bg-accent mb-3">
              <Shield className="h-5 w-5 text-accent-foreground" />
            </div>
            <h1 className="text-[20px] font-bold tracking-[0.2em] text-foreground">ATLAS</h1>
            <p className="text-[11px] text-muted-foreground mt-0.5 tracking-wide uppercase">AIOps Platform</p>
          </div>

          <div className="bg-card rounded-xl border border-border p-8 shadow-sm">
            <h2 className="text-[18px] font-semibold text-foreground mb-1">Sign in</h2>
            <p className="text-[13px] text-muted-foreground mb-6">Enter your Atos Enterprise credentials</p>

            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="text-[12px] font-medium text-foreground block mb-1.5">Username</label>
                <div className="relative">
                  <Input
                    type="text"
                    value={username}
                    onChange={(e) => { setUsername(e.target.value); setError(''); }}
                    placeholder="username"
                    className="h-10 text-[13px] pr-[90px]"
                    autoComplete="username"
                  />
                  <span className="absolute right-3 top-1/2 -translate-y-1/2 text-[12px] text-muted-foreground pointer-events-none">@atos.net</span>
                </div>
              </div>
              <div>
                <label className="text-[12px] font-medium text-foreground block mb-1.5">Password</label>
                <div className="relative">
                  <Input
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
              <div>
                <label className="text-[12px] font-medium text-foreground block mb-1.5">Role</label>
                <Select value={role} onValueChange={(v) => { setRole(v as UserRole); setError(''); }}>
                  <SelectTrigger className="h-10 text-[13px]">
                    <SelectValue placeholder="Select your role" />
                  </SelectTrigger>
                  <SelectContent>
                    {roleOptions.map(r => (
                      <SelectItem key={r.value} value={r.value}>{r.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              {error && <p className="text-[12px] text-status-critical">{error}</p>}
              <Button
                type="submit"
                disabled={loading}
                className="w-full h-10 bg-accent hover:bg-accent/90 text-accent-foreground font-medium text-[13px]"
              >
                {loading ? 'Authenticating...' : 'Sign in'}
              </Button>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
}
