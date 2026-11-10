from fastapi import APIRouter, Response, status

from common.schemas import create_response


router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> Response:
    # Sondeo de vida para Docker / Kubernetes / el balanceador. Sin lógica: solo "estoy arriba".
    response_data = {
        "status_code": status.HTTP_200_OK,
        "content": "El servidor esta arriba",
        "cookies": None
    }
    return create_response(response_data)
