"""Create individual login IDs and passwords for the coding lab.

Usage (from the repo root):
    python coding_lab/make_logins.py --names participants.csv      # CSV with a "name" column (optional "email")
    python coding_lab/make_logins.py --count 50                    # Participant 01 ... Participant 50
Options: --prefix LD (login ID prefix), --trainers "Nith,Second Trainer"

Creates two files in coding_lab/logins/ (git-ignored, never commit them):
  * participant_logins.csv : login ID + password per person: give each participant ONLY their own row
  * users_for_secrets.toml : paste into the app's Streamlit secrets (contains password hashes, not passwords)
"""
import argparse
import csv
import secrets
import string
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from auth import hash_password  # noqa: E402

OUT = Path(__file__).resolve().parent / "logins"
ALPHABET = "".join(c for c in string.ascii_letters + string.digits if c not in "O0Il1o")


def password(n=10):
    return "".join(secrets.choice(ALPHABET) for _ in range(n))


def toml_str(s):
    return '"' + str(s).replace("\\", "\\\\").replace('"', '\\"') + '"'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--names", help="CSV file with a 'name' column")
    ap.add_argument("--count", type=int, default=0)
    ap.add_argument("--prefix", default="LD")
    ap.add_argument("--trainers", default="Trainer")
    a = ap.parse_args()

    people = []
    if a.names:
        with open(a.names, newline="", encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                name = (row.get("name") or row.get("Name") or "").strip()
                if name:
                    people.append((name, (row.get("email") or row.get("Email") or "").strip()))
    people += [(f"Participant {i:02d}", "") for i in range(1, a.count + 1)]
    if not people:
        sys.exit("Give --names participants.csv or --count N")

    OUT.mkdir(exist_ok=True)
    rows, toml = [], ["# Paste everything below into the Streamlit app's Secrets.", ""]
    width = max(3, len(str(len(people))))
    for i, (name, email) in enumerate(people, 1):
        uid, pw = f"{a.prefix.upper()}{i:0{width}d}", password()
        rows.append({"login_id": uid, "name": name, "email": email, "password": pw, "role": "participant"})
    for j, name in enumerate([n.strip() for n in a.trainers.split(",") if n.strip()], 1):
        rows.append({"login_id": f"TRAINER{j}", "name": name, "email": "", "password": password(12), "role": "trainer"})
    for r in rows:
        toml += [f"[users.{r['login_id']}]", f"name = {toml_str(r['name'])}", f"role = {toml_str(r['role'])}",
                 f"password_hash = {toml_str(hash_password(r['password']))}", ""]
    with open(OUT / "participant_logins.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["login_id", "name", "email", "password", "role"])
        w.writeheader()
        w.writerows(rows)
    (OUT / "users_for_secrets.toml").write_text("\n".join(toml), encoding="utf-8")
    print(f"Created {len(rows)} logins in {OUT}:")
    print("  participant_logins.csv   (passwords: share each row only with that person)")
    print("  users_for_secrets.toml   (paste into Streamlit secrets)")


if __name__ == "__main__":
    main()
