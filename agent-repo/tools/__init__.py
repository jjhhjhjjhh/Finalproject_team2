"""도구 레지스트리.

tools/ 아래 모든 모듈을 import 하고, @tool 이 붙은 함수를 TOOLS 에 모은다.
에이전트는 get_tools() 로 목록을, describe_tools() 로 LLM용 설명서를 받는다.
"""
import importlib
import inspect
import pkgutil

TOOLS = {}


def tool(func):
    """도구 등록 데코레이터."""
    if not func.__doc__:
        raise ValueError(f"도구 '{func.__name__}' 에 docstring 이 없습니다.")
    TOOLS[func.__name__] = func
    return func


_loaded = False


def _load_all():
    global _loaded
    if _loaded:
        return
    _loaded = True
    for mod in pkgutil.iter_modules(__path__):
        if mod.name.startswith("_"):
            continue
        try:
            importlib.import_module(f"{__name__}.{mod.name}")
        except Exception as e:  # 도구 하나가 깨져도 전체는 동작
            print(f"[tools] '{mod.name}' 로드 실패: {e}")


def get_tools():
    _load_all()
    return dict(TOOLS)


def describe_tools():
    """LLM 프롬프트에 넣을 도구 설명서."""
    _load_all()
    lines = []
    for name, fn in TOOLS.items():
        sig = inspect.signature(fn)
        lines.append(f"### {name}{sig}\n{inspect.getdoc(fn)}\n")
    return "\n".join(lines)
