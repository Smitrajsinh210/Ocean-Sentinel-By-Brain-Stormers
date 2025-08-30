# 🌊 Ocean Sentinel

**AI-Powered Coastal Threat Intelligence System** for Indian Ocean monitoring and threat detection.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)](https://github.com/your-username/ocean-sentinel)

## 🚀 Features

- **🤖 AI-Powered Analysis**: Real-time threat detection using TensorFlow.js models
- **📊 Live Data Integration**: Weather, ocean, satellite, and seismic data from multiple sources
- **🔗 Blockchain Verification**: Immutable threat logging on Polygon blockchain
- **🔔 Multi-Channel Alerts**: Email, SMS, push notifications, and web alerts
- **🗺️ Interactive Mapping**: Real-time threat visualization with Leaflet
- **📡 Real-Time Updates**: Live data streaming with Pusher
- **🔐 Secure Authentication**: User management with Supabase
- **📱 Responsive Design**: Mobile-friendly interface with Tailwind CSS

## 🏗️ Architecture

### Core Technologies
- **Frontend**: HTML5, CSS3, JavaScript (ES6+)
- **Styling**: Tailwind CSS + Custom CSS
- **Mapping**: Leaflet.js
- **AI/ML**: TensorFlow.js
- **Real-time**: Pusher
- **Backend**: Supabase (PostgreSQL + Auth)
- **Blockchain**: Web3.js + Polygon
- **Charts**: Chart.js

### Project Structure
```
ocean-sentinel/
├── index.html              # Main HTML file
├── css/
│   └── styles.css          # Custom styles
├── js/
│   ├── config.js           # API keys & configuration
│   ├── auth.js             # Authentication functions
│   ├── main.js             # Core application logic
│   └── utils.js            # Utility functions
├── assets/                 # Static assets
├── package.json            # Node.js configuration
└── README.md              # This file
```

## 🚀 Quick Start

### Prerequisites
- Node.js 14+ installed
- Modern web browser with JavaScript enabled
- Internet connection for API access

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/your-username/ocean-sentinel.git
   cd ocean-sentinel
   ```

2. **Install dependencies**
   ```bash
   npm install
   ```

3. **Configure API keys** (in `js/config.js`)
   ```javascript
   const CONFIG = {
     WEATHER_API_KEY: 'your-openweather-api-key',
     SUPABASE_URL: 'your-supabase-url',
     SUPABASE_ANON_KEY: 'your-supabase-anon-key',
     // ... other configurations
   };
   ```

4. **Start development server**
   ```bash
   npm start
   ```

5. **Open in browser**
   ```
   http://localhost:3000
   ```

## 📋 Available Scripts

- `npm start` - Start development server on port 3000
- `npm run dev` - Start development server with auto-open
- `npm run build` - Build for production
- `npm run deploy` - Deploy to GitHub Pages

## 🔧 Configuration

### API Keys Setup
Update `js/config.js` with your API keys:

```javascript
const CONFIG = {
  WEATHER_API_KEY: 'your-openweather-api-key',
  SUPABASE_URL: 'your-supabase-project-url',
  SUPABASE_ANON_KEY: 'your-supabase-anon-key',
  BLOCKCHAIN_RPC: 'https://polygon-rpc.com/',
  PUSHER_KEY: 'your-pusher-key',
  PUSHER_CLUSTER: 'your-pusher-cluster'
};
```

### Environment Variables
For production deployment, consider using environment variables for sensitive data.

## 🌟 Key Components

### 1. Real-Time Threat Detection
- Monitors multiple data sources simultaneously
- Uses AI models for pattern recognition
- Provides confidence scores for all detections

### 2. Interactive Dashboard
- Live weather and ocean data visualization
- Real-time threat mapping
- AI model performance monitoring
- Alert system management

### 3. Multi-Source Data Integration
- **Weather**: OpenWeatherMap API
- **Ocean Data**: INCOIS buoys and marine sensors
- **Satellite**: NASA Earth observation data
- **Seismic**: USGS earthquake monitoring
- **Marine Traffic**: Vessel tracking and AIS data

### 4. AI Models
- **Storm Prediction**: Neural network for cyclone detection
- **Pollution Detection**: ML model for water quality analysis
- **Erosion Assessment**: Computer vision for coastal monitoring

### 5. Alert System
- **Web Alerts**: Real-time notifications via Pusher
- **Email**: SMTP integration with Resend
- **SMS**: Twilio API integration
- **Push Notifications**: Web Push API

## 🔒 Security Features

- Secure user authentication with Supabase
- Encrypted data transmission
- API key protection
- Blockchain-verified threat logging
- Multi-factor authentication support

## 📊 Data Sources

### Real-Time APIs
- OpenWeatherMap (Weather data)
- USGS Earthquake Hazards (Seismic data)
- NASA Earth Data (Satellite imagery)
- INCOIS (Indian Ocean monitoring)
- Marine Traffic API (Vessel tracking)

### Indian Coastal Coverage
- Arabian Sea (West Coast)
- Bay of Bengal (East Coast)
- Andaman Sea (Island territories)
- Lakshadweep Islands
- Major ports: Mumbai, Chennai, Kolkata, Visakhapatnam

## 🚀 Deployment

### Development
```bash
npm run dev
```

### Production Build
```bash
npm run build
```

### GitHub Pages Deployment
```bash
npm run deploy
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **Indian National Centre for Ocean Information Services (INCOIS)**
- **India Meteorological Department (IMD)**
- **USGS Earthquake Hazards Program**
- **NASA Earth Observation**
- **Open-source community**

## 📞 Support

For support, email support@oceansentinel.com or join our Discord community.

---

**Built with ❤️ for safer oceans and coastal communities**

🌊 *Monitoring the Indian Ocean, protecting coastal lives* 🌊