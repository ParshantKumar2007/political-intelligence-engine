import re

POLITICAL_INSTITUTIONS = [
    {"code": "PMO", "name": "Prime Minister's Office", "patterns": [r"\bPMO\b", r"\bPrime\s+Minister(?:'s)?\s+Office\b", r"\bNarendra\s+Modi\b", r"\bPM\s+Modi\b"]},
    {"code": "CABINET_CCEA", "name": "Cabinet Committee on Economic Affairs", "patterns": [r"\bCCEA\b", r"\bUnion\s+Cabinet\b", r"\bCabinet\s+approves?\b", r"\bCabinet\s+clears?\b", r"\bCabinet\s+decision\b"]},
    {"code": "FINMIN", "name": "Ministry of Finance", "patterns": [r"\bFinance\s+Ministry\b", r"\bFinMin\b", r"\bNirmala\s+Sitharaman\b", r"\bRevenue\s+Department\b", r"\bCBDT\b", r"\bCBIC\b"]},
    {"code": "DEFMIN", "name": "Ministry of Defence", "patterns": [r"\bDefence\s+Ministry\b", r"\bMoD\b", r"\bRajnath\s+Singh\b", r"\bDAC\s+approves?\b", r"\bDefence\s+Acquisition\s+Council\b"]},
    {"code": "MEA", "name": "Ministry of External Affairs", "patterns": [r"\bExternal\s+Affairs\s+Ministry\b", r"\bMEA\b", r"\bS\s+Jaishankar\b", r"\bdiplomatic\s+talks\b"]},
    {"code": "ECI", "name": "Election Commission of India", "patterns": [r"\bElection\s+Commission\b", r"\bECI\b", r"\bChief\s+Election\s+Commissioner\b", r"\bmodel\s+code\s+of\s+conduct\b"]},
    {"code": "SUPREME_COURT", "name": "Supreme Court of India", "patterns": [r"\bSupreme\s+Court\b", r"\bCJI\b", r"\bapex\s+court\b", r"\bconstitutional\s+bench\b"]},
    {"code": "PARLIAMENT", "name": "Indian Parliament", "patterns": [r"\bLok\s+Sabha\b", r"\bRajya\s+Sabha\b", r"\bParliament\s+session\b", r"\bMonsoon\s+session\b", r"\bWinter\s+session\b", r"\bBudget\s+session\b"]},
    {"code": "WHITE_HOUSE", "name": "US Executive Branch", "patterns": [r"\bWhite\s+House\b", r"\bPresident\s+Trump\b", r"\bDonald\s+Trump\b", r"\bTrump\s+administration\b", r"\bBiden\s+administration\b", r"\bUS\s+President\b"]},
    {"code": "US_CONGRESS", "name": "US Congress / Capitol Hill", "patterns": [r"\bCapitol\s+Hill\b", r"\bUS\s+Congress\b", r"\bUS\s+Senate\b", r"\bHouse\s+of\s+Representatives\b"]},
    {"code": "FED_RESERVE", "name": "Federal Reserve", "patterns": [r"\bFederal\s+Reserve\b", r"\bUS\s+Fed\b", r"\bJerome\s+Powell\b", r"\bFOMC\b"]},
    {"code": "UN_SECURITY", "name": "United Nations", "patterns": [r"\bUN\s+Security\s+Council\b", r"\bUNSC\b", r"\bUnited\s+Nations\b"]}
]

POLITICAL_PARTIES = [
    {"code": "BJP", "name": "Bharatiya Janata Party", "patterns": [r"\bBJP\b", r"\bBharatiya\s+Janata\s+Party\b", r"\bJP\s+Nadda\b"]},
    {"code": "INC", "name": "Indian National Congress", "patterns": [r"\bCongress\s+party\b", r"\bINC\b", r"\bRahul\s+Gandhi\b", r"\bMallikarjun\s+Kharge\b"]},
    {"code": "NDA", "name": "National Democratic Alliance", "patterns": [r"\bNDA\b", r"\bNDA\s+government\b", r"\bNDA\s+alliance\b"]},
    {"code": "INDIA_BLOC", "name": "I.N.D.I.A. Alliance", "patterns": [r"\bINDIA\s+bloc\b", r"\bINDIA\s+alliance\b", r"\bopposition\s+bloc\b"]},
    {"code": "AAP", "name": "Aam Aadmi Party", "patterns": [r"\bAam\s+Aadmi\s+Party\b", r"\bAAP\b", r"\bArvind\s+Kejriwal\b"]},
    {"code": "TMC", "name": "Trinamool Congress", "patterns": [r"\bTrinamool\b", r"\bTMC\b", r"\bMamata\s+Banerjee\b"]},
    {"code": "US_REPUBLICANS", "name": "GOP / Republicans", "patterns": [r"\bRepublicans?\b", r"\bGOP\b"]},
    {"code": "US_DEMOCRATS", "name": "Democratic Party", "patterns": [r"\bDemocrats?\b", r"\bDNC\b"]}
]

EVENT_CATEGORY_RULES = [
    {"category": "ELECTION", "patterns": [r"\belections?\b", r"\bpolls?\b", r"\bvoting\b", r"\bexit\s+polls?\b", r"\bseat\s+share\b", r"\bmajority\b", r"\bvoters?\b", r"\bbypolls?\b"]},
    {"category": "CABINET_DECISION", "patterns": [r"\bcabinet\s+approves?\b", r"\bcabinet\s+clears?\b", r"\bcabinet\s+decision\b", r"\bpolicy\s+clearance\b", r"\bgovt\s+notifies?\b", r"\bcleared\s+by\s+cabinet\b"]},
    {"category": "LEGISLATIVE_BILL", "patterns": [r"\bbill\b", r"\bamendment\b", r"\bpassed\s+in\s+parliament\b", r"\blaw\b", r"\bordinance\b", r"\bact\b", r"\blegislation\b"]},
    {"category": "GEOPOLITICS_CONFLICT", "patterns": [r"\bsanctions?\b", r"\bwar\b", r"\bceasefire\b", r"\bmilitary\s+action\b", r"\bdrone\s+strike\b", r"\btreaty\b", r"\bgeopolitical\b", r"\bborder\s+dispute\b"]},
    {"category": "TRADE_TARIFFS", "patterns": [r"\btariffs?\b", r"\bcustoms\s+duty\b", r"\bimport\s+duty\b", r"\bexport\s+curbs?\b", r"\bexport\s+ban\b", r"\btrade\s+pact\b", r"\btrade\s+war\b", r"\banti-dumping\b"]},
    {"category": "REGULATORY_ENFORCEMENT", "patterns": [r"\bED\s+raid\b", r"\bEnforcement\s+Directorate\b", r"\bCBI\b", r"\banti-corruption\b", r"\bprobe\b", r"\barrest\b", r"\bantitrust\b", r"\bCCI\b"]},
    {"category": "FISCAL_BUDGET", "patterns": [r"\bbudget\b", r"\bfiscal\s+deficit\b", r"\bgst\s+council\b", r"\btax\s+reform\b", r"\bincome\s+tax\b", r"\bsubsid(?:y|ies)\b"]}
]

SECTOR_IMPACT_RULES = [
    {"sector": "DEFENSE", "patterns": [r"\bdefence\b", r"\bmilitary\b", r"\brafale\b", r"\bdrdo\b", r"\barms\s+deal\b", r"\bnavy\b", r"\bsubmarine\b", r"\bhal\b", r"\bbel\b", r"\bmissiles?\b", r"\bartillery\b"]},
    {"sector": "RAILWAYS", "patterns": [r"\brailways?\b", r"\bvande\s+bharat\b", r"\brail\s+corridor\b", r"\bbullet\s+train\b", r"\birctc\b", r"\brail\s+freight\b", r"\blocomotive\b"]},
    {"sector": "ENERGY_OIL", "patterns": [r"\bopec\b", r"\bcrude\s+oil\b", r"\bgas\s+pipeline\b", r"\bwindfall\s+tax\b", r"\bfuel\s+subsidy\b", r"\bethanol\b", r"\bpetroleum\b", r"\benergy\s+security\b"]},
    {"sector": "INFRASTRUCTURE", "patterns": [r"\bhighways?\b", r"\bnhai\b", r"\bexpressways?\b", r"\bsmart\s+cities\b", r"\bport\s+clearance\b", r"\bmetro\s+rail\b", r"\bcapex\b", r"\broad\s+network\b"]},
    {"sector": "BANKING_FINANCE", "patterns": [r"\brbi\b", r"\brepo\s+rate\b", r"\bfiscal\s+deficit\b", r"\bpsu\s+banks?\b", r"\bdisinvestment\b", r"\bsovereign\s+bonds?\b", r"\binsolvency\b", r"\bibc\b"]},
    {"sector": "AGRI_FERTILIZERS", "patterns": [r"\bmsp\b", r"\bfertilizers?\s+subsidy\b", r"\bkisan\b", r"\bsugar\s+export\b", r"\bpaddy\b", r"\bwheat\b", r"\bcrop\s+insurance\b"]},
    {"sector": "TELECOM", "patterns": [r"\b5g\s+spectrum\b", r"\btrai\b", r"\btelecom\s+reform\b", r"\bbroadband\b", r"\bsatellite\s+spectrum\b"]},
    {"sector": "SEMICONDUCTORS_TECH", "patterns": [r"\bsemiconductors?\b", r"\bchip\s+fab\b", r"\bexport\s+controls?\b", r"\bh-1b\b", r"\bai\s+regulation\b", r"\btech\s+curbs?\b"]},
    {"sector": "PHARMA_HEALTHCARE", "patterns": [r"\bdrug\s+price\b", r"\bnppa\b", r"\bus\s+fda\b", r"\bgeneric\s+medicine\b", r"\bpharma\s+pli\b", r"\bayushman\b"]}
]

def analyze_political_headline(text):
    matched_institutions = []
    for inst in POLITICAL_INSTITUTIONS:
        for p in inst["patterns"]:
            if re.search(p, text, re.IGNORECASE):
                matched_institutions.append(inst["code"])
                break

    matched_parties = []
    for party in POLITICAL_PARTIES:
        for p in party["patterns"]:
            if re.search(p, text, re.IGNORECASE):
                matched_parties.append(party["code"])
                break

    matched_events = []
    for ev in EVENT_CATEGORY_RULES:
        for p in ev["patterns"]:
            if re.search(p, text, re.IGNORECASE):
                matched_events.append(ev["category"])
                break

    impacted_sectors = []
    for sec in SECTOR_IMPACT_RULES:
        for p in sec["patterns"]:
            if re.search(p, text, re.IGNORECASE):
                impacted_sectors.append(sec["sector"])
                break

    # Urgency detection
    urgency = "LOW"
    t_low = text.lower()
    if any(w in t_low for w in ["cabinet approves", "election dates", "exit poll", "sanctions", "strike", "emergency", "passed in lok sabha", "war declared", "tariffs imposed"]):
        urgency = "CRITICAL"
    elif matched_events or matched_institutions:
        urgency = "HIGH"

    return {
        "institutions": list(set(matched_institutions)),
        "parties": list(set(matched_parties)),
        "events": list(set(matched_events)) if matched_events else ["GENERAL_POLITICS"],
        "impacted_sectors": list(set(impacted_sectors)),
        "urgency": urgency
    }
