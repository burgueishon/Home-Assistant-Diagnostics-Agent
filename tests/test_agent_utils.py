import types

from agent import DiagnosticAgent


class FakeFunctionCall:
    def __init__(self, name="tool_x", args=None):
        self.name = name
        self.args = args or {}


class FakePart:
    def __init__(self, text=None, function_call=None):
        self.text = text
        self.function_call = function_call


class FakeContent:
    def __init__(self, parts):
        self.parts = parts


class FakeCandidate:
    def __init__(self, parts):
        self.content = FakeContent(parts)


class FakeResponse:
    def __init__(self, parts):
        self.candidates = [FakeCandidate(parts)]


def test_extract_text_with_function_call_only():
    """_extract_text should not raise when there are function_call parts and no text."""
    agent = DiagnosticAgent(api_key="dummy")
    resp = FakeResponse(parts=[FakePart(function_call=FakeFunctionCall())])
    text = agent._extract_text(resp)
    assert isinstance(text, str)
    assert text  # should return fallback text


def test_extract_text_with_text_part():
    agent = DiagnosticAgent(api_key="dummy")
    resp = FakeResponse(parts=[FakePart(text="hello world")])
    text = agent._extract_text(resp)
    assert text == "hello world"
