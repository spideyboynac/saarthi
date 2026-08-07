"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
const express_1 = require("express");
const router = (0, express_1.Router)();
// POST /api/query
router.post('/query', (req, res) => {
    const { transcript, sessionId } = req.body;
    console.log(`[Mock Backend] Received query from session ${sessionId}: "${transcript}"`);
    res.json({
        answer: `This is a placeholder AI response. You asked: "${transcript || 'nothing'}"`,
    });
});
// POST /api/simplify
router.post('/simplify', (req, res) => {
    const { answer, sessionId } = req.body;
    console.log(`[Mock Backend] Received simplify request for session ${sessionId}`);
    res.json({
        answer: `This is a simplified placeholder response. We simplified: "${answer || 'no previous answer'}"`,
    });
});
// POST /api/followups
router.post('/followups', (req, res) => {
    const { sessionId } = req.body;
    console.log(`[Mock Backend] Received followups request for session ${sessionId}`);
    res.json({
        questions: [
            'What are my basic rights when stopped by the police?',
            'How do I file a consumer complaint in India?',
            'What is the procedure to get free legal aid?',
        ],
    });
});
exports.default = router;
