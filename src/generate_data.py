"""Synthetic data generator for the Cubed Business Growth Intelligence Lab.
ALL DATA IS FICTIONAL. No real clients, CUNs, ID numbers or account numbers."""
import math
import random
import sqlite3
from datetime import date, timedelta

from src.config import DB_PATH, RANDOM_SEED, NUM_CLIENTS, DATA_IS_SYNTHETIC
from src.create_database import create_database
from src.generate_accounts import generate_accounts_and_holdings
from src.generate_turnover import generate_turnover_and_conduct

assert DATA_IS_SYNTHETIC, "The PoC must only use synthetic data."

rng = random.Random(RANDOM_SEED)
FIRST_NAMES = ["Thabo", "Naledi", "Sipho", "Lerato", "Pieter", "Annelie", "Mandla", "Zanele",
               "Johan", "Fatima", "Kagiso", "Nomsa", "Riaan", "Ayesha", "Bongani", "Palesa",
               "Willem", "Thandi", "Vusi", "Chantelle", "Themba", "Nokuthula", "Sarel", "Priya",
               "Lwazi", "Busisiwe", "Dewald", "Yusuf", "Refilwe", "Hendrik", "Ntombi", "Kobus",
               "Mpho", "Elsie", "Sizwe", "Tumelo", "Marelize", "Ashraf", "Dineo", "Gerhard"]
LAST_NAMES = ["Nkosi", "Dlamini", "Van der Merwe", "Naidoo", "Mokoena", "Botha", "Khumalo",
              "Pillay", "Molefe", "Du Plessis", "Sithole", "Govender", "Mahlangu", "Venter",
              "Zulu", "Maharaj", "Ndlovu", "Joubert", "Tshabalala", "Smit", "Mthembu",
              "Coetzee", "Radebe", "Pretorius", "Moyo", "Jacobs", "Mabaso", "Kruger",
              "Ngcobo", "Fourie", "Cele", "Abrahams", "Modise", "Steyn", "Maseko", "Adams"]


class _Names:
    """Small built-in generator of fictional South African names."""
    def last_name(self):
        return rng.choice(LAST_NAMES)

    def name(self):
        return f"{rng.choice(FIRST_NAMES)} {rng.choice(LAST_NAMES)}"


fake = _Names()

# Share of values deliberately left empty, to test data-quality handling
MISSING = {
    "entity_type": 0.03, "industry_sector": 0.05, "province": 0.04,
    "date_established": 0.06, "employee_count": 0.07,
    "recorded_annual_turnover": 0.08, "segment": 0.05,
    "director_role": 0.03, "id_category": 0.06,
}

PROVINCES = ["Gauteng", "Western Cape", "KwaZulu-Natal", "Eastern Cape", "Limpopo",
             "Mpumalanga", "North West", "Free State", "Northern Cape"]
PROVINCE_WEIGHTS = [34, 18, 17, 8, 6, 6, 4, 4, 3]

ENTITY_TYPES = ["Private Company (Pty) Ltd", "Close Corporation", "Sole Proprietor", "Partnership", "Trust"]
ENTITY_WEIGHTS = [45, 22, 20, 8, 5]

SECTORS = {
    "Retail": ["Traders", "Retail", "Supplies"],
    "Construction": ["Construction", "Builders", "Projects"],
    "Agriculture": ["Farms", "Agri", "Produce"],
    "Transport and Logistics": ["Logistics", "Transport", "Freight"],
    "Professional Services": ["Consulting", "Advisory", "Services"],
    "Hospitality": ["Hospitality", "Lodge", "Catering"],
    "Manufacturing": ["Manufacturing", "Fabrication", "Industries"],
    "Wholesale": ["Wholesalers", "Distributors", "Trading"],
    "Technology": ["Tech", "Digital", "Systems"],
    "Health and Wellness": ["Wellness", "Care", "Health"],
}
PREFIXES = ["Bluegum", "Karoo", "Ubuntu", "Savanna", "Highveld", "Protea", "Baobab", "Marula",
            "Kestrel", "Summit", "Riverbend", "Lionsrock", "Acacia", "Tembo", "Springbok",
            "Coastal", "Northgate", "Eastline", "Sunridge", "Ironwood", "Kopje", "Fynbos",
            "Delta", "Horizon", "Cobalt"]
SUFFIX = {"Private Company (Pty) Ltd": " (Pty) Ltd", "Close Corporation": " CC",
          "Sole Proprietor": "", "Partnership": " & Partners", "Trust": " Trust"}
ID_CATEGORIES = ["South African ID", "Passport", "Other"]
ID_WEIGHTS = [88, 8, 4]
DIRECTOR_ROLES = ["Director", "Member", "Trustee", "Partner"]


def pick_missing(value, rate):
    """Return None for a small share of values (deliberate data gaps)."""
    return None if rng.random() < rate else value


def random_date(start: date, end: date) -> date:
    return start + timedelta(days=rng.randint(0, (end - start).days))


def segment_for(turnover):
    """Illustrative PoC segment bands (not bank policy)."""
    if turnover is None:
        return None
    if turnover < 1_000_000:
        return "Micro"
    if turnover < 10_000_000:
        return "Small"
    if turnover < 50_000_000:
        return "Medium"
    return "Large SME"


def generate_users(conn):
    people = []
    people.append(("sysadmin", "System Admin", None))
    people.append(("compliance1", "Compliance and Audit", None))
    people.append(("productowner1", "Product Owner", None))
    people.append(("mis1", "MIS Analyst", None))
    areas = ["Area 1", "Area 2", "Area 3"]
    for i, area in enumerate(areas, 1):
        people.append((f"areamgr{i}", "Area Manager", area))
    for i in range(1, 13):
        people.append((f"bm{i:02d}", "Business Manager", areas[(i - 1) % 3]))
    for username, role, area in people:
        conn.execute(
            "INSERT INTO users (username, full_name, role, area) VALUES (?,?,?,?)",
            (username, fake.name(), role, area),
        )
    bm_ids = [r[0] for r in conn.execute("SELECT user_id FROM users WHERE role='Business Manager'")]
    return bm_ids


def make_business(sector_name, entity):
    if entity == "Sole Proprietor":
        name = f"{fake.last_name()} {rng.choice(SECTORS[sector_name])}"
    else:
        name = f"{rng.choice(PREFIXES)} {rng.choice(SECTORS[sector_name])}{SUFFIX[entity]}"
    turnover = round(min(max(rng.lognormvariate(math.log(3_500_000), 1.0), 250_000), 120_000_000), -3)
    employees = max(1, int(turnover / rng.uniform(400_000, 900_000)))
    return name, turnover, employees


def generate_clients_businesses_directors(conn, bm_ids):
    today = date(2026, 10, 31)
    for i in range(1, NUM_CLIENTS + 1):
        n_businesses = rng.choices([1, 2, 3], weights=[75, 18, 7])[0]
        businesses = []
        for _ in range(n_businesses):
            entity = rng.choices(ENTITY_TYPES, weights=ENTITY_WEIGHTS)[0]
            sector = rng.choice(list(SECTORS))
            name, turnover, employees = make_business(sector, entity)
            established = random_date(date(1990, 1, 1), date(2024, 12, 31))
            businesses.append({
                "name": name, "entity": entity, "sector": sector,
                "turnover": turnover, "employees": employees, "established": established,
            })

        first = businesses[0]
        rel_start = random_date(max(first["established"], date(2008, 1, 1)), today)
        cur = conn.execute(
            "INSERT INTO client_master (cun, client_name, segment, relationship_start, assigned_bm_id, status) "
            "VALUES (?,?,?,?,?,?)",
            (f"SYN-{i:06d}", first["name"],
             pick_missing(segment_for(first["turnover"]), MISSING["segment"]),
             rel_start.isoformat(), rng.choice(bm_ids),
             rng.choices(["Active", "Dormant"], weights=[96, 4])[0]),
        )
        client_id = cur.lastrowid

        for b in businesses:
            cur = conn.execute(
                "INSERT INTO businesses (client_id, business_name, entity_type, industry_sector, province, "
                "date_established, employee_count, recorded_annual_turnover) VALUES (?,?,?,?,?,?,?,?)",
                (client_id, b["name"],
                 pick_missing(b["entity"], MISSING["entity_type"]),
                 pick_missing(b["sector"], MISSING["industry_sector"]),
                 pick_missing(rng.choices(PROVINCES, weights=PROVINCE_WEIGHTS)[0], MISSING["province"]),
                 pick_missing(b["established"].isoformat(), MISSING["date_established"]),
                 pick_missing(b["employees"], MISSING["employee_count"]),
                 pick_missing(b["turnover"], MISSING["recorded_annual_turnover"])),
            )
            business_id = cur.lastrowid

            if b["entity"] == "Sole Proprietor":
                n_dir, roles = 1, ["Proprietor"]
            elif b["entity"] == "Trust":
                n_dir, roles = rng.randint(2, 3), ["Trustee"] * 3
            else:
                n_dir = rng.choices([1, 2, 3], weights=[35, 45, 20])[0]
                roles = [rng.choice(DIRECTOR_ROLES[:2] if b["entity"] != "Partnership" else ["Partner"])
                         for _ in range(3)]
            for k in range(n_dir):
                conn.execute(
                    "INSERT INTO directors (business_id, full_name, role, id_category) VALUES (?,?,?,?)",
                    (business_id, fake.name(),
                     pick_missing(roles[k], MISSING["director_role"]),
                     pick_missing(rng.choices(ID_CATEGORIES, weights=ID_WEIGHTS)[0], MISSING["id_category"])),
                )


def main():
    create_database(reset=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        bm_ids = generate_users(conn)
        generate_clients_businesses_directors(conn, bm_ids)
        generate_accounts_and_holdings(conn)
        generate_turnover_and_conduct(conn)
        conn.commit()
    finally:
        conn.close()
    print("Synthetic data generated (users, clients, businesses, directors, accounts, product holdings, turnover, conduct).")


if __name__ == "__main__":
    main()
