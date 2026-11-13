# Sovereign Political & Policy Intelligence Engine 🏛️⚡

Autonomous, high-throughput intelligence engine dedicated strictly to **Sovereign Political, Electoral, Policy, Cabinet & Geopolitical Intelligence**.

Operates 24/7 on dedicated cloud infrastructure under `@ParshantKumar2007`.

---

## 🏛️ Monitored Sovereign & Policy Feeds
1. **PIB Cabinet & Government Decisions** (Press Information Bureau)
2. **PIB Union Cabinet & CCEA Decisions** (Cabinet Committee on Economic Affairs)
3. **PIB Prime Minister Office (PMO)** (Executive Policy & Declarations)
4. **Economic Times Politics & Nation**
5. **Livemint Politics & Governance**
6. **Business Standard Economy & Policy**
7. **The Hindu National Wire**
8. **Google News India Politics**
9. **Politico US Policy & Congress**
10. **Reuters World Politics**
11. **Bloomberg Government & Politics**
12. **The Guardian Politics**
13. **Global Geopolitics & Diplomacy**
14. **BBC World Politics**

---

## ⚡ Architecture & Dual-Account Topology

```mermaid
graph TD
    Account1[Account 1: parshant65-lang] -->|Corporate & Market Intelligence| VaultFin[Financial Vaults: 32+ Lakh Articles]
    Account2[Account 2: ParshantKumar2007] -->|Sovereign & Policy Intelligence| Engine[Political Intelligence Engine]
    
    Engine --> Feeds[14 Verified Policy Feeds]
    Feeds --> EntityTag[Entity Disambiguation & Sector Mapping]
    EntityTag --> BodyParser[2nd Stage Full-Text Article Parser]
    BodyParser --> AutoRollover[Vault Rollover Controller < 450 MB]
    AutoRollover --> Vault1[political-wire-vault-1]
    AutoRollover -.-> Vault2[political-wire-vault-2 (Auto)]
```

- **Account 1 (`parshant65-lang`)**: Strictly Corporate, Dalal Street & Global Financial Intelligence.
- **Account 2 (`ParshantKumar2007`)**: Strictly Sovereign Political, Electoral, Policy, Cabinet & Geopolitical Intelligence.

---

## 🧠 Political Entity Disambiguation & Market Impact
Every incoming political story is parsed and enriched with structured metadata:
- **Political Institutions**: `PMO`, `CABINET_CCEA`, `FINMIN`, `DEFMIN`, `RAILMIN`, `ECI`, `RBI_GOV`, `SUPREME_COURT`, `US_CONGRESS`, `WHITE_HOUSE`, `EU_COMMISSION`.
- **Political Parties**: `BJP`, `INC`, `AAP`, `GOP_REPUBLICAN`, `DEM_DEMOCRAT`.
- **Event Categorization**: `ELECTION`, `CABINET_DECISION`, `POLICY_REFORM`, `BUDGET`, `SANCTION`, `WAR_CONFLICT`, `SUMMIT`.
- **Market Sector Mapping**: Automatically tags equity sectors impacted by policy decisions (`DEFENSE`, `RAILWAYS`, `ENERGY_OIL_GAS`, `BANKING_PSU`, `INFRASTRUCTURE`, `AUTO`, `IT`, `PHARMA`, `AGRI`).
- **Urgency Scoring**: `CRITICAL` (High-impact decisions like Cabinet ratifications, elections, sanctions) vs `STANDARD`.

---

## 🔒 500 MB Sub-Cap Automated Vault Rollover
- Strict boundary at **450 MB** or **400,000 articles**.
- When threshold is reached, current vault is marked `ARCHIVED_FULL`, a new private vault is provisioned via GitHub API, and ingestion seamlessly continues without data loss.
