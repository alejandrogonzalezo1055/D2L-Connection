from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    # Sondeo de vida para Docker / Kubernetes / el balanceador. Sin lógica: solo "estoy arriba".
    return {"status": "ok"}
