"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.BackendService = void 0;
const axios_1 = __importDefault(require("axios"));
const dotenv_1 = __importDefault(require("dotenv"));
dotenv_1.default.config();
const BACKEND_API_URL = process.env.BACKEND_API_URL || 'http://localhost:3000/api';
class BackendService {
    /**
     * Sends the user's transcript to the query endpoint.
     */
    static async query(transcript, sessionId) {
        try {
            const response = await axios_1.default.post(`${BACKEND_API_URL}/query`, {
                transcript,
                sessionId,
            });
            return response.data;
        }
        catch (error) {
            console.error('Error calling /api/query:', error);
            throw new Error('AI backend query failed');
        }
    }
    /**
     * Sends the previous response text to the simplify endpoint.
     */
    static async simplify(previousAnswer, sessionId) {
        try {
            const response = await axios_1.default.post(`${BACKEND_API_URL}/simplify`, {
                answer: previousAnswer,
                sessionId,
            });
            return response.data;
        }
        catch (error) {
            console.error('Error calling /api/simplify:', error);
            throw new Error('AI backend simplify failed');
        }
    }
    /**
     * Fetches suggested follow-up questions from the followups endpoint.
     */
    static async getFollowups(sessionId) {
        try {
            const response = await axios_1.default.post(`${BACKEND_API_URL}/followups`, {
                sessionId,
            });
            return response.data;
        }
        catch (error) {
            console.error('Error calling /api/followups:', error);
            throw new Error('AI backend followups failed');
        }
    }
}
exports.BackendService = BackendService;
