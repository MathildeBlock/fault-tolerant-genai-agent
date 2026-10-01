"""Command-line interface for the ticket agent."""

import os

from dotenv import load_dotenv

from .agent import create_configured_agent
from .client import TicketAPIClient


def main() -> None:
    load_dotenv()
    api = TicketAPIClient(os.getenv("TICKET_API_URL", "http://127.0.0.1:8000"))
    agent = create_configured_agent(api)
    print("Ticket agent ready. Type 'exit' to quit.")
    try:
        while True:
            try:
                request = input("you> ").strip()
                if request.lower() in {"exit", "quit"}:
                    break
                if request:
                    print(f"agent> {agent.respond(request)}")
            except (EOFError, KeyboardInterrupt):
                print()
                break
    finally:
        api.close()


if __name__ == "__main__":
    main()