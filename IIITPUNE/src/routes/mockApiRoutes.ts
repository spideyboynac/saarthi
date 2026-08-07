import { Router, Request, Response } from 'express';

const router = Router();

// POST /api/query
router.post('/query', (req: Request, res: Response) => {
  const { transcript, sessionId } = req.body;
  console.log(`[Mock Backend] Received query from session ${sessionId}: "${transcript}"`);
  
  res.json({
    answer: `This is a placeholder AI response. You asked: "${transcript || 'nothing'}"`,
  });
});

// POST /api/simplify
router.post('/simplify', (req: Request, res: Response) => {
  const { answer, sessionId } = req.body;
  console.log(`[Mock Backend] Received simplify request for session ${sessionId}`);

  res.json({
    answer: `This is a simplified placeholder response. We simplified: "${answer || 'no previous answer'}"`,
  });
});

// POST /api/followups
router.post('/followups', (req: Request, res: Response) => {
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

export default router;
