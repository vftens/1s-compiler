# First Clients — Action Plan

> Tactical steps to get from 0 to first $500 MRR.

---

## Who to target (most motivated buyers)

### 1. Ukrainian accounting firms (highest urgency)
- **Why:** Ukrainian law pushes away from Russian software. 1C is Russian.
- **Size:** 1–20 employees, use 1C for client bookkeeping
- **Pain:** $300–1000/year per seat + annual updates + IT support
- **Offer:** $79/month SaaS — cheaper, no IT, Ukrainian support

### 2. Ukrainian small businesses (manufacturing, trade)
- **Why:** They have 1C scripts for warehousing / sales that still work
- **Pain:** 1C renewal cost, fear of sanctions cutting updates
- **Offer:** Migration Audit $199 → "your scripts work, we prove it"

### 3. Freelance 1C developers
- **Why:** They want to offer clients a cheaper stack
- **Pain:** Clients can't afford 1C licenses
- **Offer:** Priority Support $99/month — use 1S runtime, we back you up

---

## Week 1–2 actions (zero budget)

- [ ] Post in **DOU.ua** (Ukrainian dev community) — "Free open-source 1C alternative"
- [ ] Post in **Telegram channels**: `@ua_1c_developers`, `@buhgalter_ua`, `@programmist_1c`
- [ ] Post on **LinkedIn** with a 30-second demo GIF of the Web UI running accounting_uk.1s
- [ ] Submit to **Producthunt** — schedule for Tuesday 12:01 PST
- [ ] Email 5 local accounting firms: "Free 30-min demo, no commitment"

---

## Month 1 goal: 3 pilot clients

| Client type | Offer | Price | Goal |
|-------------|-------|-------|------|
| Accounting firm | SaaS Starter (hosted) | $29/mo | 1 client |
| Small manufacturer | Migration Audit | $199 one-time | 1 client |
| 1C developer | Priority Support Basic | $99/mo | 1 client |

**Total Month 1 MRR target: $128 + $199 one-time = ~$327**

---

## Positioning message (use everywhere)

> **"Run your 1C scripts on open-source Python — free forever, paid if you need hosting or help."**

Ukrainian version:  
> **"Запускайте скрипти 1С на відкритому Python — безкоштовно назавжди, з підтримкою якщо потрібно."**

---

## What to show in demos

1. Open Web UI → Dashboard (scripts list)
2. Click `accounting_uk.1s` → Run → show live output streaming
3. Click Cython tab → show typed `.pyx` code generated automatically
4. Show `examples/erp_sale_uk.1s` output: видаткова накладна + 48.5% margin
5. Ask: "Do you have scripts like this? We can run them here."

---

## 90-day revenue model

| Month | Action | MRR |
|-------|--------|-----|
| 1 | 3 pilots (2 SaaS + 1 support) | ~$128 |
| 2 | 5 more SaaS + 1 migration | ~$395 |
| 3 | 10 SaaS + 2 support + custom dev | ~$900 |

Break-even on VPS hosting (~$20/mo) happens at **Month 1**.

---

## Contact template (cold outreach)

**Subject:** Безкоштовна альтернатива 1С для вашої фірми

> Добрий день!  
> Ми розробили відкритий транспілятор 1S, який запускає скрипти 1С без ліцензії.  
> Пропонуємо безкоштовний 30-хв демо-дзвінок — покажемо, як ваші поточні скрипти  
> запускаються без змін.  
> Репозиторій: https://github.com/vftens/1s-compiler  
> Відповісте?
