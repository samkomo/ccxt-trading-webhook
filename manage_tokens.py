"""Command-line interface for issuing and revoking webhook tokens."""

import argparse
from app.identity.token_store import issue_token, revoke_token

parser = argparse.ArgumentParser(description="Manage webhook tokens")
subparsers = parser.add_subparsers(dest="command")

issue_parser = subparsers.add_parser("issue", help="Issue a new token")
issue_parser.add_argument("--ttl", type=int, help="Token TTL in seconds", default=None)

revoke_parser = subparsers.add_parser("revoke", help="Revoke an existing token")
revoke_parser.add_argument("token", help="Token to revoke")

args = parser.parse_args()

if args.command == "issue":
    token = issue_token(ttl=args.ttl)
    print(token)
elif args.command == "revoke":
    revoke_token(args.token)
    print("revoked")
else:
    parser.print_help()
