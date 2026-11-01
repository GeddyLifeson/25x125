"""Delete a user's account on request (email or letter to support), with the data of organizations they own.

Run: python -m jobs.delete_account person@example.com            (shows what would go, changes nothing)
     python -m jobs.delete_account person@example.com --confirm  (deletes)

Same rules as the account page's delete button (engine.accounts.delete_user): organizations the person owns
are deleted with their deals, outreach log, saved searches, saved edits, invites and audit log, and their
Stripe subscription is canceled when billing is set up. Other members keep their own accounts.
"""

import argparse
import json
import sys

from core.db import connect
from engine.accounts import clean_email, delete_user


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("email")
    ap.add_argument("--confirm", action="store_true", help="delete; without it, only show what would go")
    args = ap.parse_args(argv)
    email = clean_email(args.email)
    with connect() as conn:
        user = conn.execute("select id from account_user where email = %s", (email,)).fetchone()
        if user is None:
            print(f"no account for {email}")
            return 1
        owned = conn.execute(
            """select o.id, o.name, (select count(*) from deal d where d.org_id = o.id),
                      (select count(*) from membership x where x.org_id = o.id) - 1
               from membership m join org o on o.id = m.org_id where m.user_id = %s and m.role = 'owner'""",
            (user[0],),
        ).fetchall()
        for org_id, name, deals, others in owned:
            print(f"organization {name} ({org_id}): {deals} deals, {others} other members lose access")
        if not args.confirm:
            print("nothing deleted; run again with --confirm")
            return 0
        out = delete_user(conn, user[0], "admin")
    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
