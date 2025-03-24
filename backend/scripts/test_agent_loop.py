#!/usr/bin/env python3
import asyncio
import os
import sys
from pathlib import Path

# Add the parent directory to the Python path
backend_dir = Path(__file__).parent.parent
sys.path.append(str(backend_dir))

from utils.agents_loop import AIAgentLoop


async def main():
    # Test input content
    test_content = """
    Polizza: TNB123456
    Oggetto: Sinistro avvenuto a Genova il 15 marzo 2024. Danneggiamento imballaggio.
    Merce: 50 kg di motori elettrici. Doc di peso: CMR 884833
    Valore dichiarato: €12.300, Fattura n. 22/3888 del 13/03/2024
    
    Note aggiuntive:
    - Danno riscontrato alla consegna
    - Imballaggio esterno danneggiato sul lato destro
    - Contenuto parzialmente compromesso
    """

    print("🔄 Initializing AI Agent Loop...")
    agent_loop = AIAgentLoop()

    print("\n📝 Generating report with test content...")
    result = await agent_loop.generate_report(test_content)

    print("\n=== 📄 GENERATED REPORT ===")
    print(result["draft"])

    print("\n=== 🔍 FEEDBACK ===")
    print(f"Score: {result['feedback']['score']}")
    print("Suggestions:")
    for suggestion in result["feedback"]["suggestions"]:
        print(f"- {suggestion}")

    print(f"\n✅ Process completed in {result['iterations']} iterations")


if __name__ == "__main__":
    # Ensure required environment variables are set
    required_vars = ["OPENROUTER_API_KEY", "OPENROUTER_API_URL", "DEFAULT_MODEL"]
    missing = [var for var in required_vars if not os.getenv(var)]

    if missing:
        print("❌ Error: Missing required environment variables:")
        for var in missing:
            print(f"  - {var}")
        sys.exit(1)

    asyncio.run(main())
