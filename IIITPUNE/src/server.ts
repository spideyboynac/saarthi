import express from 'express';
import dotenv from 'dotenv';
import twilioRoutes from './routes/twilioRoutes';
import mockApiRoutes from './routes/mockApiRoutes';

// Load environment variables
dotenv.config();

// Ensure keypad handlers are registered before handling routes
import './services/keypad';

const app = express();
const PORT = process.env.PORT || 3000;

// Twilio webhooks send urlencoded data
app.use(express.urlencoded({ extended: true }));

// Mock API endpoints use JSON payloads
app.use(express.json());

// Routes
app.use('/twilio', twilioRoutes);
app.use('/api', mockApiRoutes);

// Health check endpoint
app.get('/health', (req, res) => {
  res.json({ status: 'OK', service: 'NyayaSathi Twilio Voice Gateway' });
});

// Start listening
app.listen(Number(PORT), '0.0.0.0', () => {
  console.log(`====================================================`);
  console.log(` NyayaSathi Twilio Voice Gateway running locally`);
  console.log(` Port: ${PORT}`);
  console.log(` Webhook URL: http://localhost:${PORT}/twilio/incoming`);
  console.log(` Mock AI APIs URL: http://localhost:${PORT}/api`);
  console.log(`====================================================`);
});
