from rest_framework.views import exception_handler


def standard_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is None:
        return response

    detail = response.data
    message = "Une erreur est survenue"

    if isinstance(detail, dict) and "detail" in detail:
        message = str(detail["detail"])

    response.data = {
        "error": {
            "code": response.status_code,
            "message": message,
            "details": detail,
        }
    }
    return response
