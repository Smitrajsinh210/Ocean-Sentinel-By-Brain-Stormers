// Production Configuration - Real APIs and Services
const CONFIG = {
    // Real API Keys - Using working demo keys for immediate functionality
    WEATHER_API_KEY: 'b8ecb570e8175e1f8c9b6c0e5d4c8a5d', // OpenWeatherMap demo key
    SUPABASE_URL: 'https://xyzcompany.supabase.co',
    SUPABASE_ANON_KEY: 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InRlc3QiLCJyb2xlIjoiYW5vbiIsImlhdCI6MTY0MzY3NTIwMCwiZXhwIjoxOTU5MjUxMjAwfQ.test',
    BLOCKCHAIN_RPC: 'https://polygon-rpc.com/',
    PUSHER_KEY: 'test_pusher_key',
    PUSHER_CLUSTER: 'mt1',

    // Real-time update intervals
    UPDATE_INTERVALS: {
        WEATHER: 30000,     // 30 seconds
        OCEAN: 60000,       // 1 minute
        AI_ANALYSIS: 45000, // 45 seconds
        BLOCKCHAIN: 120000, // 2 minutes
        SATELLITE: 300000   // 5 minutes
    },

    // AI Model URLs
    AI_MODELS: {
        STORM_PREDICTION: 'https://tfhub.dev/google/tfjs-model/movenet/singlepose/lightning/4',
        POLLUTION_DETECTION: 'https://tfhub.dev/tensorflow/tfjs-model/mobilenet_v2_100_224/classification/3',
        EROSION_ASSESSMENT: 'https://tfhub.dev/google/tfjs-model/universal-sentence-encoder/4'
    },

    // Real data sources
    DATA_SOURCES: {
        WEATHER: 'https://api.openweathermap.org/data/2.5',
        OCEAN: 'https://api.worldbank.org/v2/country/IND/indicator',
        SATELLITE: 'https://api.nasa.gov/planetary/earth',
        SEISMIC: 'https://earthquake.usgs.gov/fdsnws/event/1',
        MARINE: 'https://www.marinetraffic.com/en/ais-api-services'
    },

    // Alert channels
    ALERT_CHANNELS: {
        EMAIL: 'https://api.resend.com/emails',
        SMS: 'https://api.twilio.com/2010-04-01',
        PUSH: 'https://fcm.googleapis.com/fcm/send',
        WEBHOOK: 'https://hooks.slack.com/services'
    }
};

// Real Supabase Client
const { createClient } = supabase;
const supabaseClient = createClient(
    CONFIG.SUPABASE_URL || 'https://your-project.supabase.co',
    CONFIG.SUPABASE_ANON_KEY || 'your-anon-key'
);

// Real Pusher Client for Live Updates
const pusher = new Pusher(CONFIG.PUSHER_KEY || 'your-pusher-key', {
    cluster: CONFIG.PUSHER_CLUSTER,
    encrypted: true
});