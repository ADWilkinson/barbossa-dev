# Barbossa Productization Strategy

## Product Definition

**Product:** Barbossa - Autonomous AI Development Team
**Domain:** barbossa.dev
**Target:** Solo developers who want continuous, autonomous code improvements
**Model:** Self-hosted Docker + License Key + BYOK (Claude Max subscription)

---

## Value Proposition

> "Your autonomous engineering team that never sleeps"

Barbossa is a 5-agent AI pipeline that runs 24/7 on your infrastructure:

| Agent | What It Does | Schedule |
|-------|--------------|----------|
| **Product Manager** | Discovers valuable features from market analysis | Daily |
| **Discovery** | Finds technical debt, TODOs, missing tests | 4x daily |
| **Engineer** | Implements changes, creates PRs | Every 2 hours |
| **Tech Lead** | Reviews PRs with strict quality gates | Every 2 hours |
| **Auditor** | Monitors health, suggests optimizations | Daily |

**Result:** Wake up to PRs. Merge the good ones. Your codebase improves while you sleep.

---

## Distribution Model

### Self-Hosted Docker + License Key

```
┌─────────────────────────────────────────────────────────────────┐
│  1. User signs up at barbossa.dev → gets license key            │
│  2. User has Claude Max subscription → gets session token       │
│  3. User pulls Docker image                                     │
│  4. User creates barbossa.json with license + repos + config    │
│  5. Container validates license on startup                      │
│  6. Runs autonomously on USER's infrastructure                  │
└─────────────────────────────────────────────────────────────────┘
```

**Why This Model:**
- Zero infrastructure cost for you (users host everything)
- Users keep code/credentials local (security)
- Easy updates via `docker pull`
- Current architecture works with minimal changes
- Solo devs are comfortable with Docker

---

## Pricing

### Single Tier: Simple and Clear

```
┌────────────────────────────────────────────────────────────────┐
│  FREE TRIAL          │  14 days, full access, 2 repos          │
├──────────────────────┼─────────────────────────────────────────┤
│  BARBOSSA PRO        │  $49/month                              │
│                      │  • Unlimited repositories               │
│                      │  • All 5 agents                         │
│                      │  • Auto-merge capability                │
│                      │  • Email support                        │
│                      │  • Future updates included              │
└──────────────────────┴─────────────────────────────────────────┘

+ User pays their own Claude Max subscription ($100/month to Anthropic)
```

**Why Single Tier:**
- Solo devs hate complex pricing
- Removes friction ("which tier do I need?")
- Easy to communicate
- Can add tiers later if needed

**Total Cost to User:** ~$149/month ($49 Barbossa + $100 Claude Max)

---

## Prerequisites (User Must Have)

1. **Claude Max Subscription** ($100/month from Anthropic)
   - Provides the session token for Claude CLI
   - User authenticates once: `claude login`

2. **GitHub Account** with Personal Access Token
   - Scopes: `repo`, `workflow`

3. **Docker** installed and running

4. **Git + SSH keys** for private repo access

---

## Configuration: `barbossa.json`

Users create this file in their working directory:

```json
{
  "license_key": "barb_xxxxxxxxxxxxxxxx",
  "owner": "github-username",
  "repositories": [
    {
      "name": "my-saas-app",
      "url": "git@github.com:username/my-saas-app.git",
      "branch": "main",
      "package_manager": "npm",
      "description": "SaaS application built with Next.js",
      "tech_stack": {
        "framework": "Next.js 14",
        "language": "TypeScript",
        "styling": "Tailwind CSS",
        "database": "Prisma + PostgreSQL"
      },
      "design_system": {
        "aesthetic": "Modern minimal",
        "rules": [
          "Use shadcn/ui components",
          "No inline styles",
          "Consistent spacing with Tailwind"
        ]
      },
      "do_not_touch": [
        "src/lib/auth.ts",
        "prisma/migrations/",
        ".env*"
      ],
      "focus_areas": [
        "Improve test coverage",
        "Add loading states",
        "Fix accessibility issues"
      ]
    }
  ],
  "settings": {
    "engineer": {
      "schedule": "every_2_hours",
      "timeout_minutes": 30,
      "max_files_changed": 15
    },
    "tech_lead": {
      "auto_merge": false,
      "auto_merge_threshold": 8,
      "require_tests_for_ui": true,
      "max_lines_without_tests": 50
    },
    "discovery": {
      "enabled": true,
      "max_backlog_issues": 20
    },
    "product_manager": {
      "enabled": true,
      "max_feature_issues": 10
    },
    "auditor": {
      "enabled": true,
      "notify_email": "dev@example.com"
    }
  }
}
```

---

## Setup Guide Outline

### Quick Start (README)

```markdown
## Quick Start

### Prerequisites
- Docker installed
- Claude Max subscription (run `claude login` first)
- GitHub Personal Access Token
- SSH key added to GitHub

### 1. Get Your License
Sign up at https://barbossa.dev and copy your license key.

### 2. Create Configuration
Create `barbossa.json` in your working directory:
[minimal example config]

### 3. Run Barbossa
docker run -d \
  --name barbossa \
  -v $(pwd)/barbossa.json:/app/barbossa.json \
  -v ~/.claude:/root/.claude \
  -v ~/.ssh:/root/.ssh:ro \
  -v ~/.gitconfig:/root/.gitconfig:ro \
  -e GITHUB_TOKEN=ghp_xxxx \
  barbossa/agent:latest

### 4. Check Status
Open http://localhost:8443 (default: barbossa/Galleon6242)

Your first PR should appear within 2 hours!
```

### Full Setup Guide (Docs Site)

```
1. Prerequisites
   ├── Installing Docker
   ├── Claude Max Subscription
   │   ├── Sign up at claude.ai
   │   ├── Subscribe to Max plan ($100/mo)
   │   └── Run `claude login` to authenticate
   ├── GitHub Personal Access Token
   │   ├── Go to GitHub → Settings → Developer settings
   │   ├── Generate token with `repo` and `workflow` scopes
   │   └── Save securely
   └── SSH Keys for Private Repos
       └── Ensure ~/.ssh/id_rsa exists and is added to GitHub

2. License Setup
   ├── Create account at barbossa.dev
   ├── Start free trial or subscribe
   └── Copy license key

3. Configuration
   ├── barbossa.json schema reference
   ├── Repository configuration
   │   ├── Required fields
   │   ├── Tech stack definition
   │   ├── Design system rules
   │   └── Protected files (do_not_touch)
   └── Agent settings
       ├── Schedules
       ├── Auto-merge rules
       └── Quality thresholds

4. Running Barbossa
   ├── Docker run command
   ├── Docker Compose setup
   ├── Volume mounts explained
   └── Environment variables

5. Web Portal
   ├── Accessing the dashboard
   ├── Viewing sessions and logs
   ├── Manual triggers
   └── Tech Lead decisions

6. Troubleshooting
   ├── License validation errors
   ├── Claude authentication issues
   ├── GitHub permission errors
   └── Common agent failures
```

---

## License Validation System

### Architecture

```
┌─────────────────┐                    ┌─────────────────────┐
│  Docker Start   │───── HTTPS ───────▶│  barbossa.dev/api   │
│                 │                    │  /v1/validate       │
│  Read license   │                    └─────────────────────┘
│  from config    │                             │
└─────────────────┘                             │
        │                                       ▼
        │◀─────────────────────────────────────────
        │   {                                   │
        │     "valid": true,                    │
        │     "expires": "2025-02-01",          │
        │     "features": ["all_agents", "auto_merge"]
        │   }                                   │
        ▼
┌─────────────────┐
│  License valid  │
│  Start agents   │
│  Begin cron     │
└─────────────────┘
        │
        │ Hourly heartbeat (usage reporting)
        ▼
┌─────────────────┐                    ┌─────────────────────┐
│  Report:        │───── HTTPS ───────▶│  barbossa.dev/api   │
│  - PRs created  │                    │  /v1/heartbeat      │
│  - Repos active │                    └─────────────────────┘
│  - Merge rate   │
└─────────────────┘
```

### License Key Format

```
barb_[environment]_[random_32_chars]

Examples:
barb_live_a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6
barb_test_x9y8z7w6v5u4t3s2r1q0p9o8n7m6l5k4
```

### Validation Endpoint

```
POST https://barbossa.dev/api/v1/validate
Content-Type: application/json

{
  "license_key": "barb_live_xxxx",
  "machine_id": "hashed-machine-identifier",
  "version": "1.0.0"
}

Response (200 OK):
{
  "valid": true,
  "tier": "pro",
  "expires": "2025-02-01T00:00:00Z",
  "features": {
    "max_repos": -1,
    "all_agents": true,
    "auto_merge": true
  }
}

Response (403 Forbidden):
{
  "valid": false,
  "error": "license_expired",
  "message": "Your license expired on 2025-01-01. Renew at barbossa.dev"
}
```

---

## barbossa.dev Website Structure

### Pages

```
/                     Landing page (hero, features, pricing, CTA)
/pricing              Detailed pricing (single tier + Claude costs explained)
/docs                 Documentation hub
/docs/quickstart      5-minute setup guide
/docs/configuration   Full barbossa.json reference
/docs/agents          How each agent works
/docs/troubleshooting Common issues
/login                Sign in
/signup               Create account + start trial
/dashboard            License management, usage stats
/dashboard/license    View/regenerate license key
/dashboard/billing    Stripe customer portal
```

### Landing Page Sections

```
1. Hero
   - "Your autonomous engineering team"
   - "Wake up to PRs. Ship features while you sleep."
   - [Start Free Trial] button

2. How It Works
   - 3-step visual: Configure → Run → Review PRs

3. The 5 Agents
   - Visual cards for each agent with what they do

4. Demo Video
   - 2-minute video showing real PRs being created

5. Pricing
   - Single tier: $49/month
   - "+ Claude Max subscription required ($100/month)"
   - [Start 14-Day Trial]

6. FAQ
   - "Do I need a Claude subscription?" → Yes, Max plan
   - "Where does my code run?" → Your infrastructure only
   - "What if Barbossa creates bad PRs?" → Don't merge them!

7. Footer
   - Docs, GitHub, Twitter, Contact
```

---

## Tech Stack for barbossa.dev

```
Frontend:
├── Next.js 14 (App Router)
├── Tailwind CSS
├── shadcn/ui
└── Vercel hosting

Backend:
├── Next.js API Routes
├── PostgreSQL (Supabase)
└── Edge functions for validation

Payments:
├── Stripe Subscriptions
├── Stripe Customer Portal
└── Webhook handlers

Auth:
├── Clerk (or NextAuth)
└── GitHub OAuth optional

Email:
└── Resend for transactional
```

---

## Implementation Checklist

### Phase 1: MVP (Week 1-2)

**barbossa.dev Website:**
- [ ] Landing page with value prop
- [ ] Pricing section
- [ ] Signup flow with Stripe
- [ ] License key generation
- [ ] Simple dashboard (show license key)

**License System:**
- [ ] `/api/v1/validate` endpoint
- [ ] `/api/v1/heartbeat` endpoint
- [ ] License key generation on signup
- [ ] Store licenses in Supabase

**Docker Image Updates:**
- [ ] Read `barbossa.json` on startup
- [ ] Validate license before starting agents
- [ ] Heartbeat reporting (hourly)
- [ ] Graceful degradation if license invalid
- [ ] Publish to GitHub Container Registry

**Documentation:**
- [ ] Quick start guide
- [ ] barbossa.json reference
- [ ] Prerequisites page (Claude Max setup)

### Phase 2: Polish (Week 3-4)

- [ ] Onboarding wizard in dashboard
- [ ] Email notifications (welcome, trial ending, expired)
- [ ] Usage analytics in dashboard
- [ ] Full documentation site
- [ ] Troubleshooting guide

### Phase 3: Launch (Week 5)

- [ ] Soft launch to 10 beta users
- [ ] Collect feedback
- [ ] Fix critical issues
- [ ] Public launch announcement
- [ ] Content: "How I shipped 50 PRs while sleeping"

---

## Revenue Model

### Unit Economics

```
Revenue per customer:     $49/month
Infrastructure cost:      $0 (self-hosted)
Stripe fees (2.9%):       $1.42/month
Support cost (estimated): $5/month
────────────────────────────────────
Gross margin:             $42.58/month (87%)
```

### Projections (Conservative)

| Metric | Month 3 | Month 6 | Month 12 |
|--------|---------|---------|----------|
| Trials started | 50 | 150 | 400 |
| Conversion (10%) | 5 | 15 | 40 |
| Cumulative subs | 5 | 35 | 80 |
| Churn (5%/mo) | - | -2 | -4 |
| Active subs | 5 | 33 | 76 |
| MRR | $245 | $1,617 | $3,724 |
| ARR | - | - | $44,688 |

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Users bypass license | Heartbeat monitoring, grace period then disable |
| Claude Max changes pricing | BYOK model - their problem, not yours |
| Bad PR quality perception | Clear docs: "review before merge", quality gates |
| Support overwhelm | Self-serve docs, community Discord |
| Docker too technical | Clear prerequisites, video tutorials |

---

## Success Metrics

**North Star:** Active paying subscribers

**Weekly Metrics:**
- Trial signups
- Trial → Paid conversion rate
- Active containers (heartbeats)
- Churn rate

**Quality Metrics:**
- PRs created per customer (engagement)
- Merge rate (value delivered)
- Support tickets (friction)

---

## Product Defensibility

> See [DEFENSIBILITY_AND_UPDATES.md](./DEFENSIBILITY_AND_UPDATES.md) for full technical details.

### Code Protection (Multi-Layer)

```
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 1: Nuitka Compilation                                   │
│  Python → C → Native binary (no readable source in container)  │
├─────────────────────────────────────────────────────────────────┤
│  LAYER 2: Server-Side Prompts                                  │
│  Agent prompts fetched from barbossa.dev (not in image)        │
├─────────────────────────────────────────────────────────────────┤
│  LAYER 3: License-Gated Execution                              │
│  Every agent run requires valid license + server handshake     │
├─────────────────────────────────────────────────────────────────┤
│  LAYER 4: PyArmor Obfuscation (V2)                             │
│  Additional bytecode encryption and anti-tampering             │
└─────────────────────────────────────────────────────────────────┘
```

**Key principle:** The Docker image contains compiled binaries only. The "secret sauce" (agent prompts, scoring algorithms) lives on barbossa.dev and is fetched at runtime.

### Over-The-Air Updates

**Recommended: Watchtower integration**

Users add Watchtower to their docker-compose.yml:

```yaml
watchtower:
  image: containrrr/watchtower
  volumes:
    - /var/run/docker.sock:/var/run/docker.sock
  command: --interval 3600  # Check hourly
```

Watchtower automatically pulls new `barbossa/agent:latest` images and restarts the container. Zero user intervention.

**Update notifications:**
- Container checks `/api/v1/version` on startup
- Logs message if update available
- Optional email for critical security updates

---

## Next Immediate Actions

1. **Register barbossa.dev domain**
2. **Create Stripe account** with subscription product
3. **Build landing page** (Next.js + Tailwind)
4. **Implement license validation API**
5. **Modify Docker image** to read barbossa.json
6. **Write quick start documentation**
7. **Recruit 5 beta testers**

---

*Version 2.0 - Focused on Solo Dev Self-Hosted Model*
*December 2024*
