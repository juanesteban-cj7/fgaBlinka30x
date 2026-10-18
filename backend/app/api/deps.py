from dataclasses import dataclass


@dataclass(frozen=True)
class DemoActor:
    id: str
    full_name: str


def get_demo_actor() -> DemoActor:
    return DemoActor(id="demo_user", full_name="Usuario de demostración")

__all__ = ["get_demo_actor"]
