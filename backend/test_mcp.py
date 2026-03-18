"""Teste rápido do MCP Server MedAssist via SSE."""
import asyncio
from mcp.client.sse import sse_client
from mcp import ClientSession


async def main():
    url = "http://localhost:8091/sse"
    print(f"Conectando ao MCP Server em {url}...")

    async with sse_client(url) as streams:
        async with ClientSession(*streams) as session:
            await session.initialize()

            # Listar ferramentas disponíveis
            tools = await session.list_tools()
            print(f"\n=== {len(tools.tools)} ferramentas disponíveis ===")
            for t in tools.tools:
                print(f"  - {t.name}: {t.description[:80]}...")

            # Testar listar pacientes
            print("\n=== Testando listar_pacientes ===")
            result = await session.call_tool("listar_pacientes", {"limite": 5})
            for content in result.content:
                print(content.text[:500])

            # Testar busca por CPF (paciente de teste do seed)
            print("\n=== Testando buscar_paciente_cpf (123.456.789-00) ===")
            result = await session.call_tool("buscar_paciente_cpf", {"cpf": "12345678900"})
            for content in result.content:
                print(content.text[:500])

            # Testar ficha completa
            print("\n=== Testando ficha_completa_paciente ===")
            result = await session.call_tool("ficha_completa_paciente", {"cpf": "12345678900"})
            for content in result.content:
                print(content.text[:1000])

            # Testar resumo atendimento
            print("\n=== Testando resumo_atendimento ===")
            result = await session.call_tool("resumo_atendimento", {"cpf": "12345678900"})
            for content in result.content:
                print(content.text[:1000])

    print("\nTodos os testes concluídos!")


if __name__ == "__main__":
    asyncio.run(main())
