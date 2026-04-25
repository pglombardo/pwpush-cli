from typing import Any

import random
import time
from urllib.parse import urljoin

import requests
import typer
from rich import print as rprint

from pwpush import version as pwpush_version

USER_AGENT = f"pwpush-cli/{pwpush_version}"

# Rate limit handling constants
DEFAULT_MAX_RETRIES = 3
DEFAULT_BASE_DELAY = 1.0  # seconds
MAX_BACKOFF_DELAY = 30.0  # maximum seconds to wait between retries


def _sanitize_headers(headers: dict[str, str]) -> dict[str, str]:
    """Return a copy of headers with sensitive authentication values masked."""
    sanitized = headers.copy()
    sensitive_keys = ["Authorization", "X-User-Token"]
    for key in sensitive_keys:
        if key in sanitized:
            sanitized[key] = "***REDACTED***"
    return sanitized


def is_rate_limit_error(response: requests.Response) -> bool:
    """Check if the response indicates a rate limit error.

    Args:
        response: The HTTP response to check

    Returns:
        True if this is a rate limit error (403 with rate limit message)
    """
    if response.status_code != 403:
        return False

    # Check for common rate limit indicators in the response
    error_text = response.text.lower()
    rate_limit_indicators = [
        "rate limit",
        "rate limit exceeded",
        "too many requests",
        "throttled",
    ]

    # Also check Retry-After header presence
    has_retry_after = "retry-after" in response.headers

    return has_retry_after or any(
        indicator in error_text for indicator in rate_limit_indicators
    )


def get_retry_delay(
    response: requests.Response, attempt: int, base_delay: float = DEFAULT_BASE_DELAY
) -> float:
    """Calculate the delay before the next retry attempt.

    Uses Retry-After header if present, otherwise uses exponential backoff with jitter.

    Args:
        response: The HTTP response containing potential Retry-After header
        attempt: The current retry attempt number (0-indexed)
        base_delay: The base delay in seconds for exponential backoff

    Returns:
        The number of seconds to wait before retrying
    """
    # Check for Retry-After header (can be seconds or HTTP date)
    retry_after = response.headers.get("retry-after")
    if retry_after:
        try:
            # Try parsing as seconds first
            return min(float(retry_after), MAX_BACKOFF_DELAY)
        except (ValueError, TypeError):
            # If not a number, we'll fall back to exponential backoff
            pass

    # Exponential backoff with full jitter: delay = min(max_delay, base * 2^attempt * random(0,1))
    exponential_delay = base_delay * (2**attempt)
    jitter = random.random()  # Random value between 0 and 1
    delay = float(min(exponential_delay * jitter, MAX_BACKOFF_DELAY))

    # Ensure minimum delay of base_delay for predictability
    return float(max(delay, base_delay))


def normalize_base_url(url: str) -> str:
    """Normalize an instance URL for safe path joining."""
    return url.rstrip("/")


def _flatten_form_data(data: dict[str, Any], prefix: str = "") -> dict[str, Any]:
    """Flatten nested dicts to Rails-style form field names.

    Example: {'push': {'payload': 'x'}} becomes {'push[payload]': 'x'}
    """
    result: dict[str, Any] = {}
    for key, value in data.items():
        new_key = f"{prefix}[{key}]" if prefix else key
        if isinstance(value, dict):
            result.update(_flatten_form_data(value, new_key))
        else:
            result[new_key] = value
    return result


def build_auth_headers(email: str, token: str) -> dict[str, str]:
    """Build the full set of supported auth headers."""
    valid_email = bool(email.strip()) and email != "Not Set"
    valid_token = bool(token.strip()) and token != "Not Set"
    if not valid_token:
        return {}

    headers = {"Authorization": f"Bearer {token}"}
    if valid_email:
        headers["X-User-Email"] = email
        headers["X-User-Token"] = token

    return headers


def absolute_url(base_url: str, path: str) -> str:
    """Join base URL + API path safely."""
    return urljoin(normalize_base_url(base_url) + "/", path.lstrip("/"))


def _send_single_request(
    method: str,
    *,
    base_url: str,
    path: str,
    email: str,
    token: str,
    post_data: dict[str, Any] | None = None,
    upload_files: dict[str, Any] | None = None,
    timeout: int = 30,
    debug: bool = False,
    verify: bool = True,
) -> requests.Response:
    """Send a single HTTP request without retry logic."""
    auth_headers = build_auth_headers(email, token)
    headers = {**auth_headers, "User-Agent": USER_AGENT}
    url = absolute_url(base_url, path)

    if debug:
        safe_headers = _sanitize_headers(headers)
        rprint(f"Communicating with {normalize_base_url(base_url)} as user {email}")
        rprint(f"Making {method} request to {url} with headers {safe_headers}")
        if not verify:
            rprint(
                "[yellow]Warning: SSL certificate verification is disabled.[/yellow]"
            )
        if method == "POST":
            rprint(f"Request body: {post_data}")
            if upload_files is not None:
                rprint("Attaching a file to the upload")

    try:
        if method == "GET":
            return requests.get(url, headers=headers, timeout=timeout, verify=verify)
        if method == "POST":
            # When uploading files, use data= instead of json= as they can't be combined
            if upload_files is not None:
                # Flatten nested dicts to Rails-style form field names
                flat_data = _flatten_form_data(post_data) if post_data else {}
                return requests.post(
                    url,
                    headers=headers,
                    data=flat_data,
                    timeout=timeout,
                    files=upload_files,
                    verify=verify,
                )
            return requests.post(
                url,
                headers=headers,
                json=post_data,
                timeout=timeout,
                verify=verify,
            )
        if method == "DELETE":
            return requests.delete(url, headers=headers, timeout=timeout, verify=verify)
    except requests.exceptions.Timeout:
        rprint(
            "[red]Error: Request timed out. Please check your connection and try again.[/red]"
        )
        raise typer.Exit(1)
    except requests.exceptions.ConnectionError:
        rprint(
            f"[red]Error: Could not connect to {normalize_base_url(base_url)}. Please check the URL and your connection.[/red]"
        )
        raise typer.Exit(1)
    except requests.exceptions.RequestException as e:
        rprint(f"[red]Error: Network request failed: {str(e)}[/red]")
        raise typer.Exit(1)

    rprint(f"[red]Error: Unsupported HTTP method '{method}'.[/red]")
    raise typer.Exit(1)


def send_request(
    method: str,
    *,
    base_url: str,
    path: str,
    email: str,
    token: str,
    post_data: dict[str, Any] | None = None,
    upload_files: dict[str, Any] | None = None,
    timeout: int = 30,
    debug: bool = False,
    verify: bool = True,
    max_retries: int = DEFAULT_MAX_RETRIES,
    on_rate_limit_retry: Any | None = None,
) -> requests.Response:
    """Send an HTTP request to the configured instance with rate limit retry support.

    This function will automatically retry on rate limit errors (HTTP 403 with rate limit
    message or Retry-After header) using exponential backoff with jitter.

    Args:
        method: HTTP method (GET, POST, DELETE)
        base_url: Base URL of the Password Pusher instance
        path: API path to request
        email: User email for authentication
        token: API token for authentication
        post_data: Optional POST data dict
        upload_files: Optional files to upload
        timeout: Request timeout in seconds
        debug: Enable debug output
        verify: Verify SSL certificates
        max_retries: Maximum number of retry attempts for rate limits
        on_rate_limit_retry: Optional callback function(attempt, delay, response) called before each retry

    Returns:
        The HTTP response object

    Raises:
        typer.Exit: On network errors or unsupported methods
    """
    last_response = None

    for attempt in range(max_retries + 1):
        response = _send_single_request(
            method,
            base_url=base_url,
            path=path,
            email=email,
            token=token,
            post_data=post_data,
            upload_files=upload_files,
            timeout=timeout,
            debug=debug,
            verify=verify,
        )

        # Check if this is a rate limit error and we have retries left
        if attempt < max_retries and is_rate_limit_error(response):
            delay = get_retry_delay(response, attempt)

            if debug:
                rprint(
                    f"[yellow]Rate limit hit (attempt {attempt + 1}/{max_retries + 1}). "
                    f"Waiting {delay:.1f}s before retry...[/yellow]"
                )

            # Call the optional callback if provided (for UI updates)
            if on_rate_limit_retry is not None:
                on_rate_limit_retry(attempt + 1, delay, response)

            time.sleep(delay)
            last_response = response
            continue  # Retry the request

        # Not a rate limit error or no more retries - return the response
        return response

    # If we exhausted all retries, return the last rate limit response
    # The caller should handle this appropriately
    return last_response if last_response is not None else response
