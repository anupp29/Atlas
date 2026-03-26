# ATLAS Integration UI - Testing Guide

## 🧪 Testing with Dummy Data

This guide explains how to test the Integration UI with pre-populated dummy data.

---

## 📦 What's Included

### 8 Pre-loaded Connections

1. **Production Redis** ⚡
   - Status: Connected
   - URL: redis://redis-prod.example.com:6379
   - Metrics: 99.8% uptime, 1250 req/s
   - Logs: 15 sample logs

2. **Staging Kubernetes** ☸️
   - Status: Connected
   - URL: https://k8s-staging.example.com:6443
   - Metrics: 98.5% uptime, 450 req/s
   - Logs: 12 sample logs

3. **Vercel Production** ▲
   - Status: Connected
   - URL: https://api.vercel.com
   - Metrics: 99.95% uptime, 2340 req/s
   - Logs: 18 sample logs

4. **Main PostgreSQL** 🐘
   - Status: Connected
   - URL: postgresql://db-prod.example.com:5432/maindb
   - Metrics: 99.9% uptime, 890 req/s
   - Logs: 20 sample logs

5. **Analytics MongoDB** 🍃
   - Status: Connected
   - URL: mongodb+srv://analytics.example.com
   - Metrics: 99.7% uptime, 567 req/s
   - Logs: 14 sample logs

6. **Event Kafka Cluster** 📨
   - Status: Connected
   - URL: kafka-broker-1.example.com:9092
   - Metrics: 99.6% uptime, 3450 req/s
   - Logs: 16 sample logs

7. **Elasticsearch Logs** 🔍
   - Status: Connected
   - URL: https://es-prod.example.com:9200
   - Metrics: 99.8% uptime, 1890 req/s
   - Logs: 17 sample logs

8. **Backup Database** 🗄️
   - Status: Connected
   - URL: mysql://backup-db.example.com:3306/backups
   - Metrics: 99.5% uptime, 234 req/s
   - Logs: 13 sample logs

---

## 🚀 How to Use Dummy Data

### Option 1: Automatic Loading (Recommended)

The dummy data loads automatically when you start the app. Just run:

```bash
npm run dev
```

The app will:
1. Load 8 pre-configured connections
2. Display them in the connection list
3. Show real-time metrics updates
4. Stream live logs

### Option 2: Manual Loading

If you want to load dummy data manually, modify `src/App.tsx`:

```typescript
import { useDummyData } from './hooks/useDummyData'

export default function App() {
  useDummyData() // Add this line
  
  // ... rest of component
}
```

### Option 3: Load on Demand

Create a button to load dummy data:

```typescript
import { useDummyDataOnDemand } from './hooks/useDummyData'

export default function MyComponent() {
  const { loadData } = useDummyDataOnDemand()
  
  return (
    <button onClick={loadData}>
      Load Dummy Data
    </button>
  )
}
```

---

## 🧪 Testing Scenarios

### Scenario 1: View All Connections

1. Start the app: `npm run dev`
2. Open http://localhost:5174
3. See 8 connections in the sidebar
4. Each shows platform icon, name, and status

**Expected Result**: All connections visible with green status indicators

### Scenario 2: Select a Connection

1. Click on "Production Redis" in the sidebar
2. View the monitoring dashboard
3. See metrics cards with real values
4. See live logs streaming

**Expected Result**: Dashboard shows metrics and logs for selected connection

### Scenario 3: View Different Platforms

1. Click on each connection in the sidebar
2. Notice different platform icons
3. See different credential types
4. Observe different log messages

**Expected Result**: Each platform displays correctly with appropriate data

### Scenario 4: Monitor Real-Time Updates

1. Select a connection
2. Watch the metrics update every 3 seconds
3. Watch logs appear every 2 seconds
4. Observe smooth animations

**Expected Result**: Metrics and logs update in real-time with animations

### Scenario 5: Add a New Connection

1. Click "+ Add Connection" button
2. Select a platform (e.g., Redis)
3. Enter test credentials
4. Confirm and connect
5. New connection appears in list

**Expected Result**: New connection added and appears in sidebar

### Scenario 6: Delete a Connection

1. Hover over a connection in the sidebar
2. Click the trash icon
3. Connection is removed

**Expected Result**: Connection deleted from list

### Scenario 7: View Different Log Levels

1. Select a connection with logs
2. Scroll through the log stream
3. Notice different colored log levels:
   - Red: ERROR
   - Yellow: WARNING
   - Blue: INFO
   - Gray: DEBUG

**Expected Result**: Logs display with correct color coding

### Scenario 8: Test Responsive Design

1. Open DevTools (F12)
2. Toggle device toolbar
3. Test on different screen sizes
4. Verify layout adapts

**Expected Result**: UI remains usable on all screen sizes

---

## 📊 Dummy Data Structure

### Connection Object

```typescript
{
  id: string                    // Unique identifier
  name: string                  // Display name
  platform: string              // Platform type
  url: string                   // Connection URL
  credentials: Record<string>   // Platform credentials
  status: 'connected' | 'disconnected' | 'connecting' | 'error'
  lastConnected?: Date          // Last connection time
  metrics?: {
    uptime: number              // Percentage
    requestsPerSecond: number   // Requests per second
    errorRate: string           // Percentage
    latency: number             // Milliseconds
  }
  logs: LogEntry[]              // Array of log entries
}
```

### Log Entry Object

```typescript
{
  id: string                    // Unique identifier
  timestamp: Date               // When log was created
  level: 'info' | 'warning' | 'error' | 'debug'
  message: string               // Log message
  source: string                // Source/platform name
}
```

---

## 🔧 Customizing Dummy Data

### Add More Connections

Edit `src/data/dummyData.ts`:

```typescript
export const DUMMY_CONNECTIONS: Connection[] = [
  // ... existing connections
  {
    id: 'conn_custom',
    name: 'My Custom Connection',
    platform: 'redis',
    url: 'redis://custom.example.com:6379',
    credentials: { /* ... */ },
    status: 'connected',
    metrics: { /* ... */ },
    logs: generateDummyLogs(10, 'redis'),
  },
]
```

### Modify Log Messages

Edit the `logMessages` object in `generateDummyLogs()`:

```typescript
const logMessages = {
  redis: [
    'Your custom log message 1',
    'Your custom log message 2',
    // ... more messages
  ],
}
```

### Change Metrics Values

Edit `generateRandomMetrics()`:

```typescript
export const generateRandomMetrics = () => {
  return {
    uptime: 99.9,                    // Change uptime
    requestsPerSecond: 5000,         // Change requests
    errorRate: '0.1',                // Change error rate
    latency: 10,                     // Change latency
  }
}
```

---

## 🎯 Testing Checklist

### UI/UX Testing
- [ ] All connections display correctly
- [ ] Platform icons show correctly
- [ ] Status indicators work
- [ ] Animations are smooth
- [ ] Responsive design works
- [ ] Colors are correct
- [ ] Text is readable

### Functionality Testing
- [ ] Can select connections
- [ ] Can add new connections
- [ ] Can delete connections
- [ ] Metrics update in real-time
- [ ] Logs stream in real-time
- [ ] Modal opens/closes correctly
- [ ] Forms validate correctly

### Data Testing
- [ ] Dummy data loads correctly
- [ ] Metrics have realistic values
- [ ] Logs have appropriate messages
- [ ] Timestamps are correct
- [ ] Status indicators are accurate
- [ ] Credentials are masked

### Performance Testing
- [ ] App loads quickly
- [ ] Animations are smooth
- [ ] No lag when scrolling logs
- [ ] Metrics update smoothly
- [ ] No memory leaks
- [ ] Responsive to interactions

---

## 🐛 Debugging Tips

### View Store State

Open browser console and run:

```javascript
// Get all connections
console.log(useConnectionStore.getState().connections)

// Get selected connection
console.log(useConnectionStore.getState().getSelectedConnection())

// Get specific connection
const conn = useConnectionStore.getState().connections[0]
console.log(conn)
```

### Monitor Real-Time Updates

Open DevTools and watch:
1. Network tab - No API calls (using mock data)
2. Console - No errors
3. React DevTools - Component re-renders
4. Performance - Smooth animations

### Test Different States

Manually change connection status:

```javascript
const store = useConnectionStore.getState()
store.updateConnectionStatus('conn_redis_prod', 'disconnected')
store.updateConnectionStatus('conn_redis_prod', 'connecting')
store.updateConnectionStatus('conn_redis_prod', 'error')
```

---

## 📝 Test Report Template

```
Date: ___________
Tester: ___________
Platform: ___________

PASSED TESTS:
- [ ] Test 1
- [ ] Test 2
- [ ] Test 3

FAILED TESTS:
- [ ] Test 1
- [ ] Test 2

ISSUES FOUND:
1. Issue description
2. Issue description

NOTES:
- Note 1
- Note 2

OVERALL STATUS: ✅ PASS / ❌ FAIL
```

---

## 🚀 Next Steps

After testing with dummy data:

1. **Integrate Backend** - Replace mock data with real API calls
2. **Add Authentication** - Implement user login
3. **Deploy** - Build and deploy to production
4. **Monitor** - Track real connections
5. **Optimize** - Improve performance based on real data

---

## 📞 Support

If you encounter issues:

1. Check the browser console for errors
2. Verify dummy data is loading
3. Check React DevTools for state
4. Review the DEVELOPMENT_GUIDE.md
5. Check the component code

---

## ✅ Testing Complete

Once you've tested all scenarios and verified everything works:

1. ✅ UI displays correctly
2. ✅ Interactions work smoothly
3. ✅ Data updates in real-time
4. ✅ Responsive design works
5. ✅ No console errors

You're ready to integrate with your backend!

---

**Happy Testing!** 🧪
