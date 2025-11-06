# Step 1: Deploy Your Follower API

## 🎯 What This API Does

Your Follower API is the central hub that:
- ✅ Receives broadcasts from your trading algo
- ✅ Manages user signups (free!)
- ✅ Forwards signals to follower agents
- ✅ Tracks P&L for profit sharing
- ✅ Enforces payment access control

---

## 🚀 Quick Deploy (Railway - Recommended)

### Option A: Deploy to Railway (5 minutes)

**Why Railway:**
- Free tier (500 hours/month)
- Dead simple deployment
- Built-in PostgreSQL if needed later
- Good for APIs

**Steps:**

1. **Create GitHub Repo**
```bash
cd /path/to/your/folder
git init
git add follower_api.py requirements.txt
git commit -m "Nike Rocket Follower API"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/nike-rocket-api.git
git push -u origin main
```

2. **Deploy to Railway**
- Go to https://railway.app
- Click "Start a New Project"
- Choose "Deploy from GitHub repo"
- Select your repo
- Railway auto-detects Python and installs dependencies
- Done!

3. **Set Environment Variables**

In Railway dashboard, go to Variables and add:
```
ADMIN_SECRET_KEY=your-super-secret-admin-key-here
STRIPE_SECRET_KEY=sk_test_your_stripe_key
```

**Generate admin key:**
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

4. **Get Your API URL**

Railway gives you: `https://nike-rocket-api-production.up.railway.app`

**Save this URL!** You'll use it in your algo:
```bash
export FOLLOWER_API_URL="https://nike-rocket-api-production.up.railway.app"
```

---

### Option B: Deploy to Vercel (Alternative)

**Why Vercel:**
- Free tier generous
- Global CDN
- Great for APIs

**Note:** Vercel uses serverless functions, so you'll need to adapt the database from JSON file to something like:
- Vercel PostgreSQL
- MongoDB Atlas (free)
- Supabase (free PostgreSQL)

---

### Option C: Deploy to Render (Alternative)

**Same as Railway, also good!**

---

## 🔧 Local Testing First

Before deploying, test locally:

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export ADMIN_SECRET_KEY="test-admin-key"
export STRIPE_SECRET_KEY="sk_test_..."

# Run API
python follower_api.py
```

**Open:** http://localhost:8000

**Try the docs:** http://localhost:8000/docs

---

## ✅ Test Your API

### Test 1: Health Check
```bash
curl http://localhost:8000/
```

**Expected:**
```json
{
  "service": "Nike Rocket Follower API",
  "status": "operational",
  "version": "1.0.0"
}
```

### Test 2: User Signup
```bash
curl -X POST http://localhost:8000/signup \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com"}'
```

**Expected:**
```json
{
  "message": "Signup successful!",
  "api_key": "NK_abc123...",
  "email": "test@example.com",
  "agent_deploy_url": "https://render.com/deploy?..."
}
```

### Test 3: Signal Broadcast
```bash
curl -X POST http://localhost:8000/signal/broadcast \
  -H "Content-Type: application/json" \
  -d '{
    "signal": {
      "symbol": "ADA/USDT",
      "direction": "SHORT",
      "entry": 0.53517,
      "tp": 0.50460,
      "sl": 0.55370,
      "risk_pct": 2.0,
      "mode": "aggressive"
    },
    "admin_key": "test-admin-key"
  }'
```

**Expected:**
```json
{
  "success": true,
  "sent": 1,
  "blocked": 0,
  "signal": {...}
}
```

---

## 🔗 Connect Your Algo to API

Once API is deployed, update your algo environment variables:

```bash
# On your machine running the algo
export FOLLOWER_API_URL="https://your-api-url.up.railway.app"
export FOLLOWER_ADMIN_KEY="your-admin-key-from-railway"
```

**Or on Windows:**
```cmd
set FOLLOWER_API_URL=https://your-api-url.up.railway.app
set FOLLOWER_ADMIN_KEY=your-admin-key-from-railway
```

---

## 📊 Database

**Current:** Simple JSON file (`users_database.json`)
- ✅ Perfect for MVP (0-100 users)
- ✅ No setup needed
- ✅ Works on Railway

**Later:** Upgrade to PostgreSQL when you have 100+ users
- Railway has built-in PostgreSQL (free tier: 100MB)
- Just change a few lines in the code

---

## 🔐 Security Checklist

Before going live:

- [ ] Change `ADMIN_SECRET_KEY` to strong random value
- [ ] Get real Stripe API keys (not test mode)
- [ ] Add rate limiting (Railway Pro has this)
- [ ] Enable HTTPS (Railway does this automatically)
- [ ] Add webhook signature verification (Stripe)

---

## 📈 Monitoring

**Railway Dashboard shows:**
- CPU usage
- Memory usage
- Request count
- Errors
- Logs

**Check logs:**
```bash
railway logs
```

---

## 💰 Costs

**Railway Free Tier:**
- 500 hours/month
- $5 credit included
- Enough for 100+ users

**When you need to upgrade:**
- 1,000+ users: $10-20/mo
- 10,000+ users: $50-100/mo

---

## 🐛 Troubleshooting

### "Connection refused"
- Check if API is running
- Verify URL is correct
- Check Railway logs

### "Invalid admin key"
- Verify `ADMIN_SECRET_KEY` matches in both places
- Check environment variables are set

### "Database file not found"
- Normal on first run
- API creates it automatically

### Broadcast not working
- Check your algo has correct `FOLLOWER_API_URL`
- Verify `FOLLOWER_ADMIN_KEY` matches
- Check Railway logs for errors

---

## 🎯 Next Steps After API is Live

1. ✅ API deployed and running
2. ⏭️ **Next:** Build follower agent code
3. ⏭️ Create Render deployment template
4. ⏭️ Test with one follower
5. ⏭️ Launch to public!

---

## 📁 Files Needed

You should have:
- `follower_api.py` - Main API code ✅
- `requirements.txt` - Python dependencies ✅
- `.gitignore` - Ignore database file
- `README.md` - Documentation

**Create .gitignore:**
```
users_database.json
__pycache__/
*.pyc
.env
```

---

## 🚀 Quick Deploy Checklist

- [ ] Create GitHub repo
- [ ] Push code to GitHub
- [ ] Sign up for Railway
- [ ] Deploy from GitHub
- [ ] Set environment variables
- [ ] Test API endpoints
- [ ] Connect your algo
- [ ] Verify broadcast works

**Time:** 15 minutes total! ⏱️

---

## ✅ Success Criteria

You'll know it's working when:

1. API health check returns 200 ✅
2. You can signup a test user ✅
3. User gets an API key ✅
4. Your algo broadcasts successfully ✅
5. Logs show "Signal broadcast to X followers" ✅

---

## 🎯 Ready to Deploy?

**Recommended path:**
1. Test locally (5 min)
2. Push to GitHub (2 min)
3. Deploy to Railway (3 min)
4. Set env vars (2 min)
5. Test endpoints (3 min)

**Total:** 15 minutes to live API! 🚀

Need help with any step? I'm here!
