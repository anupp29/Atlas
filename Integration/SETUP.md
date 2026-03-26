# ATLAS Integration UI - Setup Guide

## Quick Start

### 1. Install Dependencies

```bash
cd Integration
npm install
```

### 2. Start Development Server

```bash
npm run dev
```

The application will be available at `http://localhost:5174`

### 3. Build for Production

```bash
npm run build
```

## Project Overview

The ATLAS Integration UI is a modern platform connection and monitoring dashboard that allows users to:

1. **Connect to Multiple Platforms** - Redis, Kubernetes, Vercel, Databases, Kafka, etc.
2. **Manage Credentials Securely** - Platform-specific credential forms with encryption
3. **Monitor in Real-Time** - Live metrics, logs, and status tracking
4. **Beautiful UI/UX** - Professional design with smooth animations

## Architecture

### State Management (Zustand)
- Centralized connection store
- Real-time updates
- Persistent state

### Components
- **Sidebar** - Navigation and quick actions
- **ConnectionList** - List of all connections
- **AddConnectionModal** - Multi-step connection wizard
- **MonitoringDashboard** - Real-time metrics and logs
- **MetricsCard** - Individual metric display
- **LogStream** - Live log viewer

### Configuration
- **platforms.ts** - Platform definitions and credential schemas
- **helpers.ts** - Utility functions for formatting and mock data

## Adding a New Platform

### 1. Update `src/config/platforms.ts`

```typescript
export const PLATFORMS: Record<string, PlatformConfig> = {
  // ... existing platforms
  mynewplatform: {
    id: 'mynewplatform',
    name: 'My New Platform',
    icon: '🚀',
    color: '#FF6B6B',
    description: 'Description of the platform',
    defaultPort: 8080,
    urlPattern: 'protocol://host:port',
    credentials: [
      {
        name: 'apiKey',
        label: 'API Key',
        type: 'password',
        required: true,
        placeholder: 'Your API key',
        help: 'Get from platform settings',
      },
      // ... more credentials
    ],
  },
}
```

### 2. The platform will automatically appear in the UI

## Customization

### Colors
Edit `tailwind.config.js` to customize the color scheme:

```javascript
theme: {
  extend: {
    colors: {
      primary: '#0f172a',
      secondary: '#1e293b',
      accent: '#3b82f6',
      // ... customize as needed
    },
  },
}
```

### Animations
Modify animation timings in `src/index.css` or component files using Framer Motion.

### Metrics
Update mock metrics generation in `src/utils/helpers.ts`:

```typescript
export const generateMockMetrics = () => {
  return {
    uptime: Math.floor(Math.random() * 99) + 1,
    requestsPerSecond: Math.floor(Math.random() * 1000) + 100,
    errorRate: (Math.random() * 5).toFixed(2),
    latency: Math.floor(Math.random() * 500) + 10,
  }
}
```

## Integration with ATLAS Backend

### API Endpoints to Implement

```typescript
// POST /api/connections
// Create a new connection
{
  name: string
  platform: string
  url: string
  credentials: Record<string, string>
}

// GET /api/connections
// List all connections

// GET /api/connections/:id
// Get connection details

// DELETE /api/connections/:id
// Delete a connection

// GET /api/connections/:id/metrics
// Get real-time metrics

// WS /ws/connections/:id/logs
// WebSocket for live logs
```

### Example Backend Integration

```typescript
// In MonitoringDashboard.tsx
useEffect(() => {
  const ws = new WebSocket(`ws://localhost:8000/ws/connections/${connection.id}/logs`)
  
  ws.onmessage = (event) => {
    const log = JSON.parse(event.data)
    addLog(connection.id, log)
  }
  
  return () => ws.close()
}, [connection.id])
```

## Performance Optimization

### Code Splitting
The app uses dynamic imports for better performance:

```typescript
const MonitoringDashboard = React.lazy(() => import('./components/MonitoringDashboard'))
```

### Memoization
Components use React.memo and useMemo for optimization:

```typescript
const MetricsCard = React.memo(({ icon, label, value }: MetricsCardProps) => {
  // Component code
})
```

### State Updates
Zustand provides efficient state updates without unnecessary re-renders.

## Troubleshooting

### Port Already in Use
If port 5174 is already in use, modify `vite.config.ts`:

```typescript
server: {
  port: 5175, // Change to available port
}
```

### Module Not Found
Clear node_modules and reinstall:

```bash
rm -rf node_modules package-lock.json
npm install
```

### Build Errors
Check TypeScript errors:

```bash
npx tsc --noEmit
```

## Development Tips

### Hot Module Replacement (HMR)
Changes are automatically reflected in the browser during development.

### React DevTools
Install React DevTools browser extension for debugging.

### Zustand DevTools
Monitor state changes in the browser console:

```typescript
import { devtools } from 'zustand/middleware'
```

## Deployment

### Build
```bash
npm run build
```

### Deploy to Vercel
```bash
vercel
```

### Deploy to Netlify
```bash
netlify deploy --prod --dir=dist
```

### Docker
Create a `Dockerfile`:

```dockerfile
FROM node:18-alpine
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build
EXPOSE 5174
CMD ["npm", "run", "preview"]
```

## Environment Variables

Create a `.env.local` file:

```
VITE_API_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000
```

Access in components:

```typescript
const apiUrl = import.meta.env.VITE_API_URL
```

## Contributing

1. Create a feature branch
2. Make your changes
3. Test thoroughly
4. Submit a pull request

## Support

For issues and questions, refer to the main ATLAS documentation or contact the team.
