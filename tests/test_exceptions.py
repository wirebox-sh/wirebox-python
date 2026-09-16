from wirebox.exceptions import (
    AuthenticationError,
    FreeTierLimitExceededError,
    HandleAlreadyTakenError,
    NotFoundError,
    RateLimitError,
    WireboxAPIError,
    WireboxConnectionError,
    WireboxError,
    parse_api_error,
)


def test_exception_inheritance():
    assert issubclass(WireboxAPIError, WireboxError)
    assert issubclass(WireboxConnectionError, WireboxError)
    assert issubclass(AuthenticationError, WireboxAPIError)
    assert issubclass(NotFoundError, WireboxAPIError)
    assert issubclass(RateLimitError, WireboxAPIError)
    assert issubclass(HandleAlreadyTakenError, WireboxAPIError)
    assert issubclass(FreeTierLimitExceededError, WireboxAPIError)


def test_parse_api_error_status_mapping():
    err_401 = parse_api_error(
        401, {"error": {"code": "unauthorized", "message": "Invalid API key"}}, "req_1"
    )
    assert isinstance(err_401, AuthenticationError)
    assert err_401.status == 401
    assert err_401.request_id == "req_1"

    err_404 = parse_api_error(
        404, {"error": {"code": "identity_not_found", "message": "Not found"}}
    )
    assert isinstance(err_404, NotFoundError)
    assert err_404.status == 404

    err_409 = parse_api_error(409, {"error": {"code": "handle_already_taken", "message": "Taken"}})
    assert isinstance(err_409, HandleAlreadyTakenError)

    err_429 = parse_api_error(
        429, {"error": {"code": "rate_limit_exceeded", "message": "Too many requests"}}
    )
    assert isinstance(err_429, RateLimitError)

    err_quota = parse_api_error(
        403, {"error": {"code": "free_tier_limit_exceeded", "message": "Quota full"}}
    )
    assert isinstance(err_quota, FreeTierLimitExceededError)

    err_500 = parse_api_error(500, {"error": {"code": "internal_error", "message": "Server error"}})
    assert isinstance(err_500, WireboxAPIError)
    assert not isinstance(err_500, (AuthenticationError, NotFoundError, RateLimitError))
