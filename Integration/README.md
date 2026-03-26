# ATLAS Integration UI

A modern, professional UI for connecting and monitoring external platforms and services in real-time.

## Features

✨ **Multi-Platform Support**
- Redis
- Kubernetes
- Vercel
- PostgreSQL
- MongoDB
- Kafka
- Elasticsearch
- And more...

🔐 **Secure Credentials Management**
- Encrypted credential storage
- Never logged or exposed
- Platform-specific credential forms

📊 **Real-Time Monitoring**
- Live metrics dashboard
- Real-time log streaming
- Connection status tracking
- Performance metrics (uptime, latency, error rate, requests/sec)

🎨 **Modern UI/UX**
- Clean, professional design
- Smooth animations with Framer Motion
- Responsive layout
- Dark theme optimized for monitoring

## Getting Started

### Prerequisites
- Node.js 18+
- npm or yarn

### Installation

```bash
cd Integration
npm install
```

### Development

```bash
npm run dev
```

The application will start on `http://localhost:5174`

### Build

```bash
npm run build
```

## Project Structure

```
Integration/
├── src/
│   ├── components/          # React components
│   │   ├── Sidebar.tsx
│   │   ├── ConnectionList.tsx
│   │   ├── AddConnectionModal.tsx
│   │   ├── PlatformSelector.tsx
│   │   ├── CredentialsForm.tsx
│   │   ├── MonitoringDashboard.tsx
│   │   ├── MetricsCard.tsx
│   │   └── LogStream.tsx
│   ├── config/
│   │   └── platforms.ts     # Platform configurations
│   ├── store/
│   │   └── connectionStore.ts  # Zustand state management
│   ├── utils/
│   │   └── helpers.ts       # Utility functions
│   ├── App.tsx              # Main app component
│   ├── main.tsx             # Entry point
│   └── index.css            # Global styles
├── index.html
├── vite.config.ts
├── tailwind.config.js
├── tsconfig.json
└── package.json
```

## Usage

### Adding a Connection

1. Click "Add Connection" button
2. Select a platform from the list
3. Enter connection details (URL, credentials)
4. Review and confirm
5. System starts monitoring automatically

### Monitoring

- View real-time metrics on the dashboard
- Monitor live logs from the connected platform
- Track connection status
- View performance trends

## Supported Platforms

| Platform | Icon | Features |
|----------|------|----------|
| Redis | ⚡ | Connection pooling, memory usage, eviction rate |
| Kubernetes | ☸️ | Pod status, resource usage, events |
| Vercel | ▲ | Deployment status, build logs, analytics |
| PostgreSQL | 🐘 | Query performance, connection count, replication lag |
| MongoDB | 🍃 | Collection stats, query performance, replication |
| Kafka | 📨 | Topic metrics, consumer lag, throughput |
| Elasticsearch | 🔍 | Index stats, query performance, cluster health |
| Database | 🗄️ | Generic SQL/NoSQL database monitoring |

## Technologies

- **React 18** - UI framework
- **TypeScript** - Type safety
- **Tailwind CSS** - Styling
- **Framer Motion** - Animations
- **Zustand** - State management
- **Vite** - Build tool
- **Lucide React** - Icons

## Features in Detail

### Connection Management
- Add multiple connections
- Edit connection details
- Remove connections
- Connection status tracking

### Credentials Security
- Platform-specific credential forms
- Encrypted storage
- Never exposed in logs
- Secure transmission

### Real-Time Monitoring
- Live metrics updates
- Log streaming
- Performance tracking
- Alert indicators

### User Experience
- Smooth animations
- Intuitive navigation
- Clear error messages
- Loading states
- Empty states

## Future Enhancements

- [ ] Alert configuration
- [ ] Custom dashboards
- [ ] Metrics export
- [ ] Historical data analysis
- [ ] Multi-user support
- [ ] API integration
- [ ] Webhook support
- [ ] Advanced filtering

## License

MIT

## Support

For issues and questions, please contact the ATLAS team.
