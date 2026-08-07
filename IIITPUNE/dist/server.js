"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
const express_1 = __importDefault(require("express"));
const dotenv_1 = __importDefault(require("dotenv"));
const twilioRoutes_1 = __importDefault(require("./routes/twilioRoutes"));
const mockApiRoutes_1 = __importDefault(require("./routes/mockApiRoutes"));
// Load environment variables
dotenv_1.default.config();
// Ensure keypad handlers are registered before handling routes
require("./services/keypad");
const app = (0, express_1.default)();
const PORT = process.env.PORT || 3000;
// Twilio webhooks send urlencoded data
app.use(express_1.default.urlencoded({ extended: true }));
// Mock API endpoints use JSON payloads
app.use(express_1.default.json());
// Routes
app.use('/twilio', twilioRoutes_1.default);
app.use('/api', mockApiRoutes_1.default);
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
