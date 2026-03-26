# ATLAS Integration UI - Development Guide

## 🏗 Architecture Overview

### Component Hierarchy

```
App
├── Sidebar
├── ConnectionList
├── AddConnectionModal
│   ├── PlatformSelector
│   ├── CredentialsForm
│   └── ConfirmStep
├── MonitoringDashboard
│   ├── MetricsCard (x4)
│   └── LogStream
└── Empty State
```

### Data Flow

```
User Action
    ↓
Component Event
    ↓
Zustand Store Update
    ↓
State Change
    ↓
Component Re-render
    ↓
UI Update
```

### State Management

```
ConnectionStore (Zustand)
├── connections: Connection[]
├── selectedConnectionId: string | null
├── addConnection()
├── removeConnection()
├── updateConnection()
├── selectConnection()
├── addLog()
├── updateConnectionStatus()
└── getSelectedConnection()
```

---

## 📝 Component Details

### App.tsx
**Purpose**: Main application component  
**Responsibilities**:
- Render layout
- Manage modal state
- Handle connection selection
- Render appropriate view

**Key Props**: None  
**State**: `showAddModal`

### Sidebar.tsx
**Purpose**: Navigation sidebar  
**Responsibilities**:
- Display logo
- Show navigation menu
- Quick action buttons
- Settings and help

**Key Props**: `onAddConnection`  
**State**: None

### ConnectionList.tsx
**Purpose**: Display all connections  
**Responsibilities**:
- List all connections
- Show connection status
- Handle selection
- Handle deletion

**Key Props**: None  
**State**: Uses Zustand store

### AddConnectionModal.tsx
**Purpose**: Multi-step connection wizard  
**Responsibilities**:
- Manage wizard steps
- Handle platform selection
- Collect credentials
- Confirm and save

**Key Props**: `onClose`  
**State**: `step`, `selectedPlatform`, `credentials`, `connectionName`, `connectionUrl`

### PlatformSelector.tsx
**Purpose**: Platform selection interface  
**Responsibilities**:
- Display platform cards
- Handle search
- Filter platforms
- Handle selection

**Key Props**: `onSelect`  
**State**: `searchTerm`

### CredentialsForm.tsx
**Purpose**: Dynamic credential form  
**Responsibilities**:
- Generate form fields
- Validate input
- Handle submission
- Show errors

**Key Props**: `platform`, `onSubmit`, `onBack`  
**State**: `connectionName`, `connectionUrl`, `credentials`, `errors`, `isValidating`

### MonitoringDashboard.tsx
**Purpose**: Main monitoring view  
**Responsibilities**:
- Display metrics
- Show logs
- Handle connection
- Update in real-time

**Key Props**: `connection`  
**State**: `isConnecting`, `metrics`

### MetricsCard.tsx
**Purpose**: Individual metric display  
**Responsibilities**:
- Display metric value
- Show trend
- Animate updates
- Color coding

**Key Props**: `icon`, `label`, `value`, `trend`, `color`  
**State**: None

### LogStream.tsx
**Purpose**: Live log viewer  
**Responsibilities**:
- Display logs
- Color code by level
- Auto-scroll
- Handle scrolling

**Key Props**: `logs`  
**State**: None

---

## 🔧 Configuration System

### Platform Configuration

```typescript
interface PlatformConfig {
  id: string                    // Unique identifier
  name: string                  // Display name
  icon: string                  // Emoji icon
  color: string                 // Brand color
  description: string           // Short description
  credentials: CredentialField[] // Required credentials
  defaultPort?: number          // Optional default port
  urlPattern?: string           // Optional URL format
}
```

### Adding a New Platform

1. **Define in `platforms.ts`**:
```typescript
export const PLATFORMS: Record<string, PlatformConfig> = {
  myplatform: {
    id: 'myplatform',
    name: 'My Platform',
    icon: '🚀',
    color: '#FF6B6B',
    description: 'Platform description',
    credentials: [
      {
        name: 'apiKey',
        label: 'API Key',
        type: 'password',
        required: true,
        placeholder: 'Your API key',
        help: 'Get from settings',
      },
    ],
  },
}
```

2. **Update Connection type** (if needed):
```typescript
platform: 'redis' | 'kubernetes' | 'myplatform' // Add here
```

3. **Test in UI**:
- Platform appears in selector
- Form generates correctly
- Connection saves properly

---

## 🎨 Styling System

### Tailwind Configuration

```javascript
// tailwind.config.js
theme: {
  extend: {
    colors: {
      primary: '#0f172a',      // Main background
      secondary: '#1e293b',    // Secondary background
      accent: '#3b82f6',       // Primary accent
      success: '#10b981',      // Success color
      warning: '#f59e0b',      // Warning color
      danger: '#ef4444',       // Error color
    },
  },
}
```

### Color Usage

- **Primary**: Main backgrounds
- **Secondary**: Cards, panels
- **Accent**: Buttons, highlights
- **Success**: Positive states
- **Warning**: Caution states
- **Danger**: Error states

### Custom Classes

```css
/* index.css */
.animate-slide-in { /* Slide animation */ }
.animate-fade-in { /* Fade animation */ }
```

---

## 🔄 State Management Patterns

### Adding a Connection

```typescript
const addConnection = useConnectionStore((state) => state.addConnection)

addConnection({
  name: 'My Redis',
  platform: 'redis',
  url: 'redis://localhost:6379',
  credentials: { host: 'localhost', port: '6379' },
})
```

### Updating Connection Status

```typescript
const updateConnectionStatus = useConnectionStore((state) => state.updateConnectionStatus)

updateConnectionStatus(connectionId, 'connected')
```

### Adding Logs

```typescript
const addLog = useConnectionStore((state) => state.addLog)

addLog(connectionId, {
  timestamp: new Date(),
  level: 'info',
  message: 'Connection established',
  source: 'Redis',
})
```

### Getting Selected Connection

```typescript
const selectedConnection = useConnectionStore((state) => state.getSelectedConnection())
```

---

## 🎬 Animation Patterns

### Framer Motion Usage

```typescript
import { motion, AnimatePresence } from 'framer-motion'

// Fade in
<motion.div
  initial={{ opacity: 0 }}
  animate={{ opacity: 1 }}
  exit={{ opacity: 0 }}
>
  Content
</motion.div>

// Slide in
<motion.div
  initial={{ opacity: 0, x: -20 }}
  animate={{ opacity: 1, x: 0 }}
>
  Content
</motion.div>

// Scale
<motion.button
  whileHover={{ scale: 1.05 }}
  whileTap={{ scale: 0.95 }}
>
  Click me
</motion.button>

// Stagger
<motion.div
  initial={{ opacity: 0 }}
  animate={{ opacity: 1 }}
  transition={{ staggerChildren: 0.1 }}
>
  {items.map((item, i) => (
    <motion.div key={i} initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
      {item}
    </motion.div>
  ))}
</motion.div>
```

---

## 🧪 Testing Patterns

### Component Testing

```typescript
import { render, screen } from '@testing-library/react'
import ConnectionList from './ConnectionList'

test('renders connection list', () => {
  render(<ConnectionList />)
  expect(screen.getByText(/connections/i)).toBeInTheDocument()
})
```

### Store Testing

```typescript
import { useConnectionStore } from './store/connectionStore'

test('adds connection', () => {
  const { result } = renderHook(() => useConnectionStore())
  
  act(() => {
    result.current.addConnection({
      name: 'Test',
      platform: 'redis',
      url: 'redis://localhost',
      credentials: {},
    })
  })
  
  expect(result.current.connections).toHaveLength(1)
})
```

---

## 🚀 Performance Optimization

### Code Splitting

```typescript
const MonitoringDashboard = React.lazy(() => 
  import('./components/MonitoringDashboard')
)

<Suspense fallback={<Loading />}>
  <MonitoringDashboard />
</Suspense>
```

### Memoization

```typescript
const MetricsCard = React.memo(({ icon, label, value }: Props) => {
  return <div>{value}</div>
})

export default MetricsCard
```

### useCallback

```typescript
const handleSelect = useCallback((id: string) => {
  selectConnection(id)
}, [selectConnection])
```

### useMemo

```typescript
const filteredPlatforms = useMemo(() => {
  return platforms.filter(p => 
    p.name.toLowerCase().includes(searchTerm.toLowerCase())
  )
}, [platforms, searchTerm])
```

---

## 🔗 API Integration

### Fetch Metrics

```typescript
useEffect(() => {
  const fetchMetrics = async () => {
    try {
      const response = await fetch(`/api/connections/${connection.id}/metrics`)
      const data = await response.json()
      setMetrics(data)
    } catch (error) {
      console.error('Failed to fetch metrics:', error)
    }
  }
  
  const interval = setInterval(fetchMetrics, 3000)
  return () => clearInterval(interval)
}, [connection.id])
```

### WebSocket Logs

```typescript
useEffect(() => {
  const ws = new WebSocket(`ws://localhost:8000/ws/connections/${connection.id}/logs`)
  
  ws.onopen = () => console.log('Connected')
  
  ws.onmessage = (event) => {
    const log = JSON.parse(event.data)
    addLog(connection.id, log)
  }
  
  ws.onerror = (error) => console.error('WebSocket error:', error)
  
  ws.onclose = () => console.log('Disconnected')
  
  return () => ws.close()
}, [connection.id])
```

### Create Connection

```typescript
const createConnection = async (data: ConnectionData) => {
  try {
    const response = await fetch('/api/connections', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    })
    
    if (!response.ok) throw new Error('Failed to create')
    
    const connection = await response.json()
    addConnection(connection)
  } catch (error) {
    console.error('Error:', error)
  }
}
```

---

## 🐛 Debugging

### React DevTools
- Install React DevTools browser extension
- Inspect component props and state
- Track re-renders

### Zustand DevTools
```typescript
import { devtools } from 'zustand/middleware'

export const useConnectionStore = create<ConnectionStore>(
  devtools((set, get) => ({
    // store implementation
  }))
)
```

### Console Logging
```typescript
console.log('Connection:', connection)
console.log('Metrics:', metrics)
console.log('Logs:', logs)
```

### Network Tab
- Monitor API calls
- Check WebSocket connections
- Verify request/response

---

## 📦 Build & Deployment

### Development Build
```bash
npm run dev
```

### Production Build
```bash
npm run build
```

### Preview Build
```bash
npm run preview
```

### Environment Variables
```
VITE_API_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000
```

---

## 🔐 Security Considerations

### Credential Handling
- Never log credentials
- Use password input type
- Mask in UI display
- Encrypt before sending
- Use HTTPS in production

### API Security
- Validate all inputs
- Use CORS properly
- Implement rate limiting
- Use authentication tokens
- Sanitize outputs

### XSS Prevention
- Use React's built-in escaping
- Avoid dangerouslySetInnerHTML
- Validate user input
- Use Content Security Policy

---

## 📚 Resources

- [React Documentation](https://react.dev)
- [TypeScript Handbook](https://www.typescriptlang.org/docs)
- [Tailwind CSS](https://tailwindcss.com)
- [Framer Motion](https://www.framer.com/motion)
- [Zustand](https://github.com/pmndrs/zustand)
- [Vite](https://vitejs.dev)

---

## ✅ Development Checklist

- [ ] Environment setup
- [ ] Dependencies installed
- [ ] Dev server running
- [ ] Components rendering
- [ ] State management working
- [ ] Animations smooth
- [ ] Responsive design tested
- [ ] Error handling working
- [ ] API integration ready
- [ ] Build successful
- [ ] Production ready

---

**Happy Coding!** 🚀
