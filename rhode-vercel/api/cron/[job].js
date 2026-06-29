// Rhode — dispatcher único de crons (consolida recovery/reminder/tier-milestones
// num só endpoint p/ ficar dentro do limite de 12 funções do plano Hobby).
// Os handlers vivem em api/_crons/ (pasta com "_" → Vercel não conta como função).
// Rota dinâmica: /api/cron/<job> → req.query.job. Schedules em vercel.json.
import recovery from '../_crons/recovery.js';
import reminder from '../_crons/reminder.js';
import milestones from '../_crons/milestones.js';

const JOBS = {
  recovery,
  reminder,
  milestones,
  'tier-milestones': milestones,
};

export default async function handler(req, res) {
  const job = (req.query.job || '').toString();
  const fn = JOBS[job];
  if (!fn) return res.status(400).json({ error: `unknown cron job: ${job}` });
  return fn(req, res);
}
