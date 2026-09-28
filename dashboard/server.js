import express from 'express';
import cors from 'cors';
import Database from 'better-sqlite3';
import path from 'path';
import { fileURLToPath } from 'url';
import fs from 'fs';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const app = express();
app.use(cors());
app.use(express.json());

// Ensure user_data dir exists (for local testing without docker compose)
const userDataDir = path.join(__dirname, 'user_data');
if (!fs.existsSync(userDataDir)) {
  fs.mkdirSync(userDataDir, { recursive: true });
}

// Init Database
const db = new Database(path.join(userDataDir, 'dashboard.sqlite'));

// Create tables
db.exec(`
  CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT
  );
  
  CREATE TABLE IF NOT EXISTS portfolio_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    total_balance REAL,
    open_profit REAL,
    closed_profit REAL
  );
`);

// --- API Endpoints ---

// Get all settings
app.get('/api/dashboard/settings', (req, res) => {
  try {
    const rows = db.prepare('SELECT * FROM settings').all();
    const settings = {};
    rows.forEach(row => {
      settings[row.key] = JSON.parse(row.value);
    });
    res.json(settings);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// Save a setting
app.post('/api/dashboard/settings', (req, res) => {
  const { key, value } = req.body;
  if (!key) return res.status(400).json({ error: "Key is required" });
  
  try {
    const stmt = db.prepare('INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value');
    stmt.run(key, JSON.stringify(value));
    res.json({ success: true });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// Get portfolio snapshots
app.get('/api/dashboard/portfolio', (req, res) => {
  try {
    const limit = req.query.limit ? parseInt(req.query.limit) : 100;
    const rows = db.prepare('SELECT * FROM portfolio_snapshots ORDER BY timestamp DESC LIMIT ?').all(limit);
    res.json(rows);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// --- Aggregator Background Job ---
import cron from 'node-cron';

async function fetchFreqtradeData(botUrl, username, password) {
  try {
    const baseUrl = botUrl.replace(/\\/$/, "");
    // Login
    const loginRes = await fetch(`${baseUrl}/api/v1/token/login`, {
      method: "POST",
      headers: { "Authorization": "Basic " + Buffer.from(`${username}:${password}`).toString('base64') }
    });
    if (!loginRes.ok) throw new Error("Login failed");
    const { access_token } = await loginRes.json();
    
    // Fetch balance and profit
    const [balanceRes, profitRes] = await Promise.all([
      fetch(`${baseUrl}/api/v1/balance`, { headers: { "Authorization": "Bearer " + access_token } }),
      fetch(`${baseUrl}/api/v1/profit`, { headers: { "Authorization": "Bearer " + access_token } })
    ]);
    
    const balance = await balanceRes.json();
    const profit = await profitRes.json();
    
    return {
      balance: balance?.total_bot || balance?.total || 0,
      open_profit: profit?.profit_all_coin - profit?.profit_closed_coin || 0,
      closed_profit: profit?.profit_closed_coin || 0
    };
  } catch (err) {
    console.error(`Error polling bot ${botUrl}:`, err.message);
    return null;
  }
}

cron.schedule('0 * * * *', async () => {
  console.log("Running hourly portfolio aggregation...");
  try {
    const row = db.prepare('SELECT value FROM settings WHERE key = ?').get('ft_bots');
    if (!row) return;
    const bots = JSON.parse(row.value);
    
    let totalBal = 0;
    let totalOpenPnl = 0;
    let totalClosedPnl = 0;
    let successCount = 0;

    for (const bot of bots) {
      const data = await fetchFreqtradeData(bot.url, bot.username, bot.password);
      if (data) {
        totalBal += data.balance;
        totalOpenPnl += data.open_profit;
        totalClosedPnl += data.closed_profit;
        successCount++;
      }
    }
    
    if (successCount > 0) {
      const stmt = db.prepare('INSERT INTO portfolio_snapshots (total_balance, open_profit, closed_profit) VALUES (?, ?, ?)');
      stmt.run(totalBal, totalOpenPnl, totalClosedPnl);
      console.log(`Saved snapshot: Bal=${totalBal}, ClosedPnl=${totalClosedPnl}`);
    }
  } catch (err) {
    console.error("Aggregator error:", err);
  }
});


// --- Serve Static Frontend ---
const distPath = path.join(__dirname, 'dist');
if (fs.existsSync(distPath)) {
  app.use(express.static(distPath));
  app.get('*', (req, res) => {
    // Only send index.html if it's not an API request
    if (!req.path.startsWith('/api/')) {
        res.sendFile(path.join(distPath, 'index.html'));
    } else {
        res.status(404).json({error: "API endpoint not found"});
    }
  });
} else {
  app.get('*', (req, res) => {
    res.send("Dashboard frontend is not built yet. Run 'npm run build' in the dashboard directory.");
  });
}

const PORT = process.env.PORT || 80;
app.listen(PORT, '0.0.0.0', () => {
  console.log(`Dashboard backend running on port ${PORT}`);
});
