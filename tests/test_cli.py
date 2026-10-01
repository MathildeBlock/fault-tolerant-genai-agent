from agent import cli


def test_cli_handles_keyboard_interrupt_during_response(monkeypatch, capsys):
    class InterruptingAgent:
        def respond(self, request):
            raise KeyboardInterrupt

    monkeypatch.setattr(cli, "create_configured_agent", lambda api: InterruptingAgent())
    monkeypatch.setattr("builtins.input", lambda prompt: "List tickets")

    cli.main()

    assert "Ticket agent ready" in capsys.readouterr().out